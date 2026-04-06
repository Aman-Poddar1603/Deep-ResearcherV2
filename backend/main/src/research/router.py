"""
FastAPI WebSocket router.

Endpoints:
  WS  /ws/research/{research_id}   — main bidirectional channel
  POST /research/start              — kick off a new research session
  POST /research/{research_id}/stop — request graceful stop

The WS handler:
  1. Accepts the connection and attaches to the emitter.
  2. On reconnect → restores state from Redis and resumes pub/sub relay.
  3. Spawns two concurrent tasks:
       - _run_pipeline()  → Layer 1 → Layer 2 → artifact
       - _relay_pubsub()  → Redis pub/sub → WS (for reconnect continuity)
  4. Routes incoming WS messages to the correct asyncio.Queue.
"""

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse

from research.config import settings
from research.emitter import WSEmitter
from research.models import (
    ResearchStartRequest,
    SystemReconnectedEvent,
    SystemErrorEvent,
    SystemConnectedEvent,
)
from research.session import (
    get_session_state,
    get_token_totals,
    load_context,
    update_session_status,
    is_stop_requested,
    get_pubsub,
)
from research.stop_manager import request_stop, flush_partial_research
from research.layer1.pipeline import run_layer1
from research.layer2.orchestrator1 import run_orchestrator1
from research.layer2.orchestrator2 import run_orchestrator2
from research.layer2.artifact import run_artifact_generation

logger = logging.getLogger(__name__)
router = APIRouter(tags=["research"])

from main.src.research import session_store


# ─── Start endpoint ───────────────────────────────────────────────────────────


@router.post("/start")
async def start_research(request: ResearchStartRequest):
    """
    Allocates a research_id and returns it.
    The frontend should immediately open WS /ws/research/{research_id}.
    The pipeline starts automatically once the WS connects.
    """
    research_id = str(uuid.uuid4())
    # Pre-register so WS handler can find it
    session_store._active_sessions[research_id] = {
        "emitter": WSEmitter(research_id=research_id),
        "answer_q": asyncio.Queue(),
        "approval_q": asyncio.Queue(),
        "gathered_sources": [],
        "request": request,
        "started": False,
    }
    logger.info("[router] New research allocated: %s", research_id)
    return JSONResponse({"research_id": research_id, "status": "ready"})


# ─── Stop endpoint ────────────────────────────────────────────────────────────


@router.post("/{research_id}/stop")
async def stop_research(research_id: str):
    session = session_store._active_sessions.get(research_id)
    if not session:
        raise HTTPException(status_code=404, detail="Research session not found")
    emitter: WSEmitter = session["emitter"]
    await request_stop(research_id, emitter)
    return JSONResponse({"status": "stop_requested"})


# ─── WebSocket handler ────────────────────────────────────────────────────────


@router.websocket("/ws/{research_id}")
async def research_websocket(websocket: WebSocket, research_id: str):
    await websocket.accept()
    logger.info("[ws] Client connected: %s", research_id)
    logger.info("[ws] Active sessions: %s", list(session_store._active_sessions.keys()))

    # ── Session lookup / reconnect ────────────────────────────────────────────
    session = session_store._active_sessions.get(research_id)
    is_reconnect = False

    if session is None:
        logger.warning("[ws] Session not found in active sessions for %s", research_id)
        # Client reconnecting after server restart — try Redis restore
        state = await get_session_state(research_id)
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

    emitter: WSEmitter = session["emitter"]
    emitter.attach(websocket)

    # Send connected event
    await emitter.emit(
        SystemConnectedEvent(research_id=research_id, status="connected")
    )

    answer_q: asyncio.Queue = session["answer_q"]
    approval_q: asyncio.Queue = session["approval_q"]

    # ── Reconnect restore ─────────────────────────────────────────────────────
    if is_reconnect:
        state = await get_session_state(research_id)
        token_totals = await get_token_totals(research_id)
        await emitter.emit(
            SystemReconnectedEvent(
                research_id=research_id,
                last_step=int(state.get("current_step", 0)),
                status=state.get("status", "unknown"),
                token_totals=token_totals,
            )
        )
        # Just relay pub/sub — pipeline is still running in background
        await _relay_pubsub(research_id, websocket, answer_q, approval_q)
        return

    # ── First connection — start pipeline ─────────────────────────────────────
    if not session.get("started"):
        session["started"] = True
        pipeline_task = asyncio.create_task(
            _run_pipeline(
                research_id=research_id,
                request=session["request"],
                emitter=emitter,
                answer_q=answer_q,
                approval_q=approval_q,
                gathered_sources=session["gathered_sources"],
            ),
            name=f"pipeline_{research_id}",
        )
        session["pipeline_task"] = pipeline_task

    # ── Concurrent: relay pub/sub + read incoming WS messages ─────────────────
    relay_task = asyncio.create_task(
        _relay_pubsub(research_id, websocket, answer_q, approval_q),
        name=f"relay_{research_id}",
    )
    recv_task = asyncio.create_task(
        _recv_loop(websocket, answer_q, approval_q, research_id, emitter),
        name=f"recv_{research_id}",
    )

    try:
        done, pending = await asyncio.wait(
            [relay_task, recv_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    except WebSocketDisconnect:
        logger.info("[ws] Client disconnected: %s", research_id)
        relay_task.cancel()
        recv_task.cancel()
    finally:
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
                session = _active_sessions.get(research_id)
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


# ─── Redis pub/sub relay ──────────────────────────────────────────────────────


async def _relay_pubsub(
    research_id: str,
    websocket: WebSocket,
    answer_q: asyncio.Queue,
    approval_q: asyncio.Queue,
) -> None:
    """
    Subscribes to Redis pub/sub channel and relays events to the WS.
    This keeps the reconnected client in sync even if they missed events.
    """
    pubsub = await get_pubsub(research_id)
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    await websocket.send_text(message["data"])
                except Exception:
                    break
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe()
        await pubsub.aclose()


# ─── Cleanup ──────────────────────────────────────────────────────────────────


def _cleanup_session(research_id: str) -> None:
    """Remove from active sessions map. Redis state persists for reconnects."""
    _active_sessions.pop(research_id, None)
    logger.info("[router] Session cleaned up: %s", research_id)
