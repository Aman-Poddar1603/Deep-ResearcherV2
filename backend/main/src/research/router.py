"""
FastAPI WebSocket router.

Endpoints:
    WS /ws/research/{research_id} — main bidirectional channel

The WS handler:
  1. Accepts the connection and attaches to the emitter.
    2. On reconnect → restores state from Redis and replays stream events.
    3. Starts the background pipeline task on first connection.
    4. Runs receive loop for user answers/approval messages.

The pipeline task:
       - _run_pipeline()  → Layer 1 → Layer 2 → artifact
Routes incoming WS messages to the correct asyncio.Queue.
"""

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from research.emitter import WSEmitter
from research.models import (
    ResearchStartRequest,
    SystemReconnectedEvent,
    SystemErrorEvent,
    SystemConnectedEvent,
)
from research.session import (
    get_latest_event_id,
    get_session_state,
    get_token_totals,
    is_stop_requested,
    replay_events,
    update_session_status,
)
from research.stop_manager import request_stop, flush_partial_research
from research.layer1.pipeline import run_layer1
from research.layer2.orchestrator1 import run_orchestrator1
from research.layer2.orchestrator2 import run_orchestrator2
from research.layer2.artifact import run_artifact_generation

logger = logging.getLogger(__name__)
router = APIRouter(tags=["research"])

from main.src.research import session_store


# ─── WebSocket handler ────────────────────────────────────────────────────────


def _parse_replay_limit(raw_value: str | None) -> int:
    try:
        value = int(raw_value or "300")
    except (TypeError, ValueError):
        return 300
    return max(1, min(value, 2000))


@router.websocket("/ws/{research_id}")
async def research_websocket(websocket: WebSocket, research_id: str):
    await websocket.accept()
    requested_last_event_id = websocket.query_params.get("last_event_id")
    replay_limit = _parse_replay_limit(websocket.query_params.get("replay_limit"))

    logger.info("[ws] Client connected: %s", research_id)
    logger.info("[ws] Active sessions: %s", list(session_store._active_sessions.keys()))

    # ── Session lookup / reconnect ────────────────────────────────────────────
    session = session_store._active_sessions.get(research_id)
    is_reconnect = False
    state = await get_session_state(research_id)

    if session is None:
        logger.warning("[ws] Session not found in active sessions for %s", research_id)
        # Try Redis restore for reconnect/read-only replay sessions.
        if state:
            is_reconnect = True
            session = {
                "emitter": WSEmitter(research_id=research_id),
                "answer_q": asyncio.Queue(),
                "approval_q": asyncio.Queue(),
                "gathered_sources": [],
                "request": None,
                "started": True,
            }
            session_store._active_sessions[research_id] = session
        else:
            await websocket.send_text(
                json.dumps(
                    {
                        "event": "system.error",
                        "research_id": research_id,
                        "message": "Unknown research session.",
                        "recoverable": False,
                    }
                )
            )
            await websocket.close()
            return

    # If client doesn't send cursor on reconnect, default to latest to avoid
    # replaying the full history and duplicating already-rendered UI timelines.
    if requested_last_event_id is None and session.get("started"):
        last_event_id = (await get_latest_event_id(research_id)) or "0-0"
    else:
        last_event_id = (requested_last_event_id or "0-0").strip()

    emitter: WSEmitter = session["emitter"]
    # We relay events to this websocket from Redis stream only.
    # Keep emitter detached to avoid replay/live double-send races.
    emitter.detach()

    answer_q: asyncio.Queue = session["answer_q"]
    approval_q: asyncio.Queue = session["approval_q"]

    relay_task = asyncio.create_task(
        _relay_stream_events(
            research_id=research_id,
            websocket=websocket,
            start_event_id=last_event_id or "0-0",
            replay_limit=replay_limit,
        ),
        name=f"stream_relay_{research_id}",
    )

    await emitter.emit(
        SystemConnectedEvent(research_id=research_id, status="connected")
    )

    if is_reconnect and state:
        token_totals = await get_token_totals(research_id)
        await emitter.emit(
            SystemReconnectedEvent(
                research_id=research_id,
                last_step=int(state.get("current_step", 0)),
                status=state.get("status", "unknown"),
                token_totals=token_totals,
            )
        )

    # ── First connection — start pipeline ─────────────────────────────────────
    if not session.get("started"):
        request = session.get("request")
        if request is None:
            await emitter.emit(
                SystemErrorEvent(
                    research_id=research_id,
                    message="Research request payload unavailable; cannot start pipeline.",
                    recoverable=False,
                )
            )
            await websocket.close()
            return

        session["started"] = True
        pipeline_task = asyncio.create_task(
            _run_pipeline(
                research_id=research_id,
                request=request,
                emitter=emitter,
                answer_q=answer_q,
                approval_q=approval_q,
                gathered_sources=session["gathered_sources"],
            ),
            name=f"pipeline_{research_id}",
        )
        session["pipeline_task"] = pipeline_task

    try:
        recv_task = asyncio.create_task(
            _recv_loop(websocket, answer_q, approval_q, research_id, emitter),
            name=f"recv_{research_id}",
        )
        done, pending = await asyncio.wait(
            [relay_task, recv_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    except WebSocketDisconnect:
        logger.info("[ws] Client disconnected: %s", research_id)
    finally:
        relay_task.cancel()
        emitter.detach()
        logger.info(
            "[ws] Emitter detached for %s (pipeline continues in background)",
            research_id,
        )


# ─── Pipeline runner (background task) ───────────────────────────────────────


async def _run_pipeline(
    research_id: str,
    request: ResearchStartRequest,
    emitter: WSEmitter,
    answer_q: asyncio.Queue,
    approval_q: asyncio.Queue,
    gathered_sources: list,
) -> None:
    """
    Full research pipeline. Runs as a background asyncio task so it survives
    WS disconnects. State is checkpointed to Redis at every meaningful step.
    """
    try:
        # ── Layer 1 ───────────────────────────────────────────────────────────
        context = await run_layer1(
            request=request,
            research_id=research_id,
            emitter=emitter,
            answer_queue=answer_q,
            approval_queue=approval_q,
        )

        if context is None:
            # Blocked by guard — session already marked + error event sent
            _cleanup_session(research_id)
            return

        # Check stop before Layer 2
        if await is_stop_requested(research_id):
            await flush_partial_research(research_id, gathered_sources, emitter)
            _cleanup_session(research_id)
            return

        # ── Layer 2 — Orchestrator 1 (gather) ─────────────────────────────────
        await run_orchestrator1(
            context=context,
            emitter=emitter,
            gathered_sources=gathered_sources,
        )

        # Check stop between orchestrators
        if await is_stop_requested(research_id):
            await flush_partial_research(research_id, gathered_sources, emitter)
            _cleanup_session(research_id)
            return

        # ── Layer 2 — Orchestrator 2 (synthesize) ─────────────────────────────
        artifact_context = await run_orchestrator2(
            context=context,
            gathered_sources=gathered_sources,
            emitter=emitter,
        )

        if await is_stop_requested(research_id):
            await flush_partial_research(research_id, gathered_sources, emitter)
            _cleanup_session(research_id)
            return

        # ── Artifact generation ────────────────────────────────────────────────
        await run_artifact_generation(
            artifact_context=artifact_context,
            research_id=research_id,
            workspace_id=request.workspace_id,
            emitter=emitter,
        )

        await update_session_status(research_id, "completed")
        logger.info("[pipeline] Research %s completed successfully", research_id)

    except asyncio.CancelledError:
        logger.info("[pipeline] Pipeline task cancelled for %s", research_id)
    except Exception as exc:
        logger.exception(
            "[pipeline] Unhandled error in pipeline %s: %s", research_id, exc
        )
        await emitter.emit(
            SystemErrorEvent(
                research_id=research_id,
                message=f"Pipeline error: {str(exc)}",
                recoverable=False,
            )
        )
        await update_session_status(research_id, "error")
    finally:
        _cleanup_session(research_id)


# ─── Incoming WS message router ──────────────────────────────────────────────


async def _recv_loop(
    websocket: WebSocket,
    answer_q: asyncio.Queue,
    approval_q: asyncio.Queue,
    research_id: str,
    emitter: WSEmitter,
) -> None:
    """
    Reads incoming WS messages and routes them to the correct queue.

    Expected message shapes:
      {"type": "user.answer",   "answer": "..."}
      {"type": "user.approval", "action": "approve"}
      {"type": "user.approval", "action": "refactor", "feedback": "..."}
      {"type": "stop.request"}
    """
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("[ws] Invalid JSON from client: %s", raw[:100])
                continue

            msg_type = msg.get("type", "")

            if msg_type == "user.answer":
                await answer_q.put(msg.get("answer", ""))

            elif msg_type == "user.approval":
                await approval_q.put(
                    {
                        "action": msg.get("action", "approve"),
                        "feedback": msg.get("feedback", ""),
                    }
                )

            elif msg_type == "stop.request":
                await request_stop(research_id, emitter)
                session = session_store._active_sessions.get(research_id)
                if session:
                    await flush_partial_research(
                        research_id,
                        session.get("gathered_sources", []),
                        emitter,
                    )

            else:
                logger.warning("[ws] Unknown message type: %s", msg_type)

    except WebSocketDisconnect:
        logger.info("[ws] recv_loop: client disconnected %s", research_id)
    except asyncio.CancelledError:
        pass


async def _relay_stream_events(
    research_id: str,
    websocket: WebSocket,
    start_event_id: str,
    replay_limit: int,
) -> None:
    """
    Stream events to websocket from the Redis event stream using an event cursor.
    This single path handles both replay and live delivery without duplicate races.
    """
    cursor = start_event_id or "0-0"
    try:
        while True:
            replay_rows = await replay_events(
                research_id=research_id,
                from_event_id=cursor,
                limit=replay_limit,
            )
            if not replay_rows:
                await asyncio.sleep(0.25)
                continue

            for row in replay_rows:
                payload = dict(row.get("payload") or {})
                payload.setdefault("event_id", row.get("id"))
                try:
                    await websocket.send_text(json.dumps(payload))
                except Exception:
                    return
                cursor = row.get("id") or cursor
    except asyncio.CancelledError:
        pass


# ─── Cleanup ──────────────────────────────────────────────────────────────────


def _cleanup_session(research_id: str) -> None:
    """Remove from active sessions map. Redis state persists for reconnects."""
    session_store._active_sessions.pop(research_id, None)
    logger.info("[router] Session cleaned up: %s", research_id)
