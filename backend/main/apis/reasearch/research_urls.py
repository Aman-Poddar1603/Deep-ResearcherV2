from __future__ import annotations

import asyncio
import json
import logging
import math
import uuid
from datetime import datetime
from typing import Any, Literal, NoReturn

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from main.apis.models.research import (
    ChainOfThoughtEntry,
    ResearchCreate,
    ResearchListResponse,
    ResearchPatch,
    ResearchReplayEvent,
    ResearchReplayResponse,
    ResearchRecord,
    ResearchResumeResponse,
    ResearchSourceCreate,
    ResearchSourceListResponse,
    ResearchSourcePatch,
    ResearchSourceRecord,
    ResearchStartRequest,
    ResearchStartResponse,
    ResearchStatusResponse,
    ResearchTokenTotals,
    StepDetail,
    StopResearchResponse,
    ThinkingBlock,
    ToolCallDetail,
)
from main.src.research import session_store
from main.src.research.emitter import WSEmitter
from main.src.research.session import (
    init_session,
    get_latest_event_id,
    get_session_state,
    get_streaming_snapshot,
    get_token_totals,
    load_context,
    load_pending_input,
    load_plan,
    replay_events,
    update_session_status,
)
from main.src.research.stop_manager import request_stop
from main.src.store.DBManager import researches_db_manager

router = APIRouter(prefix="/research", tags=["research"])
logger = logging.getLogger(__name__)


class ResearchOrchestrator:
    def __init__(self) -> None:
        self.research_table = "researches"
        self.source_table = "research_sources"

    @staticmethod
    def _db_payload(data: dict[str, Any]) -> dict[str, Any]:
        payload = dict(data)
        for key, value in list(payload.items()):
            if isinstance(value, datetime):
                payload[key] = value.isoformat()
        return payload

    @staticmethod
    def _parse_datetime(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return datetime.min
        return datetime.min

    @staticmethod
    def _paginate(items: list[Any], page: int, size: int) -> tuple[list[Any], int, int]:
        total_items = len(items)
        total_pages = math.ceil(total_items / size) if total_items else 0
        offset = (page - 1) * size
        return items[offset : offset + size], total_pages, offset

    def getAllResearch(
        self,
        page: int = 1,
        size: int = 20,
        workspace_id: str | None = None,
        title_contains: str | None = None,
        desc_contains: str | None = None,
        prompt_contains: str | None = None,
        chat_access: bool | None = None,
        background_processing: bool | None = None,
        sort_by: Literal["id", "title", "workspace_id"] = "id",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> ResearchListResponse:
        result = researches_db_manager.fetch_all(self.research_table)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to list research items")

        items = [
            ResearchRecord.model_validate(item) for item in (result.get("data") or [])
        ]

        if workspace_id is not None:
            items = [item for item in items if item.workspace_id == workspace_id]
        if title_contains:
            term = title_contains.strip().lower()
            items = [item for item in items if term in (item.title or "").lower()]
        if desc_contains:
            term = desc_contains.strip().lower()
            items = [item for item in items if term in (item.desc or "").lower()]
        if prompt_contains:
            term = prompt_contains.strip().lower()
            items = [item for item in items if term in (item.prompt or "").lower()]
        if chat_access is not None:
            items = [item for item in items if item.chat_access is chat_access]
        if background_processing is not None:
            items = [
                item
                for item in items
                if item.background_processing is background_processing
            ]

        reverse_order = sort_order == "desc"
        if sort_by == "title":
            items.sort(
                key=lambda item: (item.title or "").lower(), reverse=reverse_order
            )
        elif sort_by == "workspace_id":
            items.sort(
                key=lambda item: (item.workspace_id or "").lower(),
                reverse=reverse_order,
            )
        else:
            items.sort(key=lambda item: item.id or "", reverse=reverse_order)

        page_items, total_pages, offset = self._paginate(items, page, size)
        return ResearchListResponse(
            items=page_items,
            page=page,
            size=size,
            total_items=len(items),
            total_pages=total_pages,
            offset=offset,
        )

    def getResearch(self, research_id: str) -> ResearchRecord:
        result = researches_db_manager.fetch_one(
            self.research_table, where={"id": research_id}
        )
        if not result.get("success"):
            raise ValueError(
                result.get("message") or f"Failed to fetch research {research_id}"
            )

        row = result.get("data")
        if row is None:
            raise KeyError(f"Research {research_id} not found")
        return ResearchRecord.model_validate(row)

    def createResearch(self, payload: ResearchCreate) -> ResearchRecord:
        data = self._db_payload(payload.model_dump(mode="python"))
        result = researches_db_manager.insert(self.research_table, data)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to create research")
        return self.getResearch(data["id"])

    def updateResearch(
        self, research_id: str, payload: ResearchCreate
    ) -> ResearchRecord:
        self.getResearch(research_id)
        data = self._db_payload(payload.model_dump(mode="python"))
        data["id"] = research_id
        result = researches_db_manager.update(
            self.research_table, data=data, where={"id": research_id}
        )
        if not result.get("success"):
            raise ValueError(
                result.get("message") or f"Failed to replace research {research_id}"
            )
        return self.getResearch(research_id)

    def patchResearch(self, research_id: str, payload: ResearchPatch) -> ResearchRecord:
        self.getResearch(research_id)
        patch_data = self._db_payload(
            payload.model_dump(exclude_unset=True, mode="python")
        )
        if not patch_data:
            return self.getResearch(research_id)
        result = researches_db_manager.update(
            self.research_table,
            data=patch_data,
            where={"id": research_id},
        )
        if not result.get("success"):
            raise ValueError(
                result.get("message") or f"Failed to patch research {research_id}"
            )
        return self.getResearch(research_id)

    def deleteResearch(self, research_id: str) -> None:
        self.getResearch(research_id)
        result = researches_db_manager.delete(
            self.research_table, where={"id": research_id}
        )
        if not result.get("success"):
            raise ValueError(
                result.get("message") or f"Failed to delete research {research_id}"
            )

    def getResearchSourceUrls(
        self,
        research_id: str | None = None,
        page: int = 1,
        size: int = 20,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        source_type: str | None = None,
        url_contains: str | None = None,
        sort_by: Literal[
            "created_at", "updated_at", "research_id", "source_type", "source_url"
        ] = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> ResearchSourceListResponse:
        result = researches_db_manager.fetch_all(self.source_table)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to list research sources")

        items = [
            ResearchSourceRecord.model_validate(item)
            for item in (result.get("data") or [])
        ]

        if research_id is not None:
            items = [item for item in items if item.research_id == research_id]
        if source_type is not None:
            items = [item for item in items if item.source_type == source_type]
        if url_contains:
            term = url_contains.strip().lower()
            items = [item for item in items if term in (item.source_url or "").lower()]
        if created_from is not None:
            items = [
                item
                for item in items
                if self._parse_datetime(item.created_at) >= created_from
            ]
        if created_to is not None:
            items = [
                item
                for item in items
                if self._parse_datetime(item.created_at) <= created_to
            ]
        if updated_from is not None:
            items = [
                item
                for item in items
                if self._parse_datetime(item.updated_at) >= updated_from
            ]
        if updated_to is not None:
            items = [
                item
                for item in items
                if self._parse_datetime(item.updated_at) <= updated_to
            ]

        reverse_order = sort_order == "desc"
        if sort_by == "updated_at":
            items.sort(
                key=lambda item: self._parse_datetime(item.updated_at),
                reverse=reverse_order,
            )
        elif sort_by == "research_id":
            items.sort(
                key=lambda item: (item.research_id or "").lower(), reverse=reverse_order
            )
        elif sort_by == "source_type":
            items.sort(
                key=lambda item: (item.source_type or "").lower(), reverse=reverse_order
            )
        elif sort_by == "source_url":
            items.sort(
                key=lambda item: (item.source_url or "").lower(), reverse=reverse_order
            )
        else:
            items.sort(
                key=lambda item: self._parse_datetime(item.created_at),
                reverse=reverse_order,
            )

        page_items, total_pages, offset = self._paginate(items, page, size)
        return ResearchSourceListResponse(
            items=page_items,
            page=page,
            size=size,
            total_items=len(items),
            total_pages=total_pages,
            offset=offset,
        )

    def getResearchSource(self, source_id: str) -> ResearchSourceRecord:
        result = researches_db_manager.fetch_one(
            self.source_table, where={"id": source_id}
        )
        if not result.get("success"):
            raise ValueError(
                result.get("message") or f"Failed to fetch research source {source_id}"
            )

        row = result.get("data")
        if row is None:
            raise KeyError(f"Research source {source_id} not found")
        return ResearchSourceRecord.model_validate(row)

    def createResearchSource(
        self, payload: ResearchSourceCreate
    ) -> ResearchSourceRecord:
        data = self._db_payload(payload.model_dump(mode="python"))
        result = researches_db_manager.insert(self.source_table, data)
        if not result.get("success"):
            raise ValueError(
                result.get("message") or "Failed to create research source"
            )
        return self.getResearchSource(data["id"])

    def patchResearchSource(
        self,
        source_id: str,
        payload: ResearchSourcePatch,
    ) -> ResearchSourceRecord:
        self.getResearchSource(source_id)
        patch_data = self._db_payload(
            payload.model_dump(exclude_unset=True, mode="python")
        )
        if not patch_data:
            return self.getResearchSource(source_id)
        result = researches_db_manager.update(
            self.source_table,
            data=patch_data,
            where={"id": source_id},
        )
        if not result.get("success"):
            raise ValueError(
                result.get("message") or f"Failed to patch research source {source_id}"
            )
        return self.getResearchSource(source_id)

    def deleteResearchSource(self, source_id: str) -> None:
        self.getResearchSource(source_id)
        result = researches_db_manager.delete(
            self.source_table, where={"id": source_id}
        )
        if not result.get("success"):
            raise ValueError(
                result.get("message") or f"Failed to delete research source {source_id}"
            )


research_view = ResearchOrchestrator()


def _raise_research_http_error(action: str, exc: Exception) -> NoReturn:
    if isinstance(exc, HTTPException):
        raise exc
    if isinstance(exc, KeyError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc).strip("'"),
        ) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc) or f"Invalid request for {action.lower()}",
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to {action.lower()}",
    ) from exc


def _register_runtime_session(research_id: str, payload: ResearchStartRequest) -> None:
    session_store._active_sessions[research_id] = {
        "emitter": WSEmitter(research_id=research_id),
        "answer_q": asyncio.Queue(),
        "approval_q": asyncio.Queue(),
        "gathered_sources": [],
        "request": payload,
        "started": False,
    }
    logger.info(
        "[research_urls] Session registered: %s, total sessions: %s",
        research_id,
        list(session_store._active_sessions.keys()),
    )


def _runtime_urls(request: Request, research_id: str) -> dict[str, str]:
    http_base = str(request.base_url).rstrip("/")
    if http_base.startswith("https://"):
        ws_base = "wss://" + http_base[len("https://") :]
    elif http_base.startswith("http://"):
        ws_base = "ws://" + http_base[len("http://") :]
    else:
        ws_base = http_base

    return {
        "status_url": f"{http_base}/research/{research_id}/status",
        "replay_url": f"{http_base}/research/{research_id}/events/replay",
        "resume_url": f"{http_base}/research/{research_id}/resume",
        "websocket_url": f"{ws_base}/research/ws/{research_id}",
    }


@router.post("/start", response_model=ResearchStartResponse)
async def start_research_session(
    request: Request,
    payload: ResearchStartRequest,
) -> ResearchStartResponse:
    research_id = str(uuid.uuid4())
    _register_runtime_session(research_id, payload)

    try:
        await init_session(research_id, payload.workspace_id, total_steps=0)
        await update_session_status(
            research_id,
            status="ready",
            current_step=0,
            total_steps=0,
        )
    except Exception as exc:
        logger.warning(
            "[research_urls] Failed to pre-persist session state for %s: %s",
            research_id,
            exc,
        )

    urls = _runtime_urls(request, research_id)
    return ResearchStartResponse(
        research_id=research_id,
        status="ready",
        status_url=urls["status_url"],
        replay_url=urls["replay_url"],
        resume_url=urls["resume_url"],
        websocket_url=urls["websocket_url"],
    )


@router.post("/{research_id}/start", response_model=ResearchStartResponse)
async def start_research_runtime(
    research_id: str,
    request: Request,
    payload: ResearchStartRequest,
) -> ResearchStartResponse:
    _register_runtime_session(research_id, payload)

    try:
        await init_session(research_id, payload.workspace_id, total_steps=0)
        await update_session_status(
            research_id,
            status="ready",
            current_step=0,
            total_steps=0,
        )
    except Exception as exc:
        logger.warning(
            "[research_urls] Failed to pre-persist session state for %s: %s",
            research_id,
            exc,
        )

    urls = _runtime_urls(request, research_id)
    return ResearchStartResponse(
        research_id=research_id,
        status="ready",
        status_url=urls["status_url"],
        replay_url=urls["replay_url"],
        resume_url=urls["resume_url"],
        websocket_url=urls["websocket_url"],
    )


@router.post("/{research_id}/stop", response_model=StopResearchResponse)
async def stop_research_runtime(research_id: str) -> StopResearchResponse:
    session = session_store._active_sessions.get(research_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Research session not found"
        )

    emitter = session["emitter"]
    await request_stop(research_id, emitter)
    return StopResearchResponse(research_id=research_id, status="stop_requested")


@router.get("/{research_id}/status", response_model=ResearchStatusResponse)
async def get_research_status(research_id: str) -> ResearchStatusResponse:
    latest_event_id = await get_latest_event_id(research_id)
    pending_input = await load_pending_input(research_id)

    # First check active sessions
    session = session_store._active_sessions.get(research_id)
    if session:
        state = await get_session_state(research_id)
        token_totals = ResearchTokenTotals.model_validate(
            await get_token_totals(research_id)
        )

        if state:
            return ResearchStatusResponse(
                research_id=research_id,
                status=str(state.get("status", "running")),
                current_step=int(state.get("current_step", 0)),
                total_steps=int(state.get("total_steps", 0)),
                created_at=state.get("created_at"),
                updated_at=state.get("updated_at"),
                token_totals=token_totals,
                latest_event_id=latest_event_id,
                pending_input=pending_input,
            )

        # Session is active but not yet initialized in Redis.
        status_str = "running" if session.get("started") else "ready"
        return ResearchStatusResponse(
            research_id=research_id,
            status=status_str,
            current_step=0,
            total_steps=0,
            created_at=None,
            updated_at=None,
            token_totals=token_totals,
            latest_event_id=latest_event_id,
            pending_input=pending_input,
        )

    # Check persisted state
    state = await get_session_state(research_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Research session not found"
        )

    token_totals = ResearchTokenTotals.model_validate(
        await get_token_totals(research_id)
    )
    return ResearchStatusResponse(
        research_id=research_id,
        status=str(state.get("status", "unknown")),
        current_step=int(state.get("current_step", 0)),
        total_steps=int(state.get("total_steps", 0)),
        created_at=state.get("created_at"),
        updated_at=state.get("updated_at"),
        token_totals=token_totals,
        latest_event_id=latest_event_id,
        pending_input=pending_input,
    )


@router.get("/{research_id}/events/replay", response_model=ResearchReplayResponse)
async def replay_research_events(
    research_id: str,
    from_event_id: str = Query(default="0-0", alias="fromEventId"),
    limit: int = Query(default=200, ge=1, le=2000),
) -> ResearchReplayResponse:
    state = await get_session_state(research_id)
    if state is None and research_id not in session_store._active_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research session not found. The id may be stale or never started.",
        )

    replay_rows = await replay_events(
        research_id=research_id,
        from_event_id=from_event_id,
        limit=limit,
    )
    events = [ResearchReplayEvent.model_validate(row) for row in replay_rows]
    next_event_id = events[-1].id if events else from_event_id
    return ResearchReplayResponse(
        research_id=research_id,
        from_event_id=from_event_id,
        replay_count=len(events),
        next_event_id=next_event_id,
        events=events,
    )


def _aggregate_step_details(
    timeline_events: list[ResearchReplayEvent],
    plan: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Parse timeline events into comprehensive step-wise granular data."""
    from main.apis.models.research import (
        ChainOfThoughtEntry,
        StepDetail,
        ThinkingBlock,
        ToolCallDetail,
    )

    # Index plan by step
    plan_by_step: dict[int, dict[str, Any]] = {
        s.get("step_index", i): s for i, s in enumerate(plan)
    }

    # Group events by step
    steps_map: dict[int, dict[str, Any]] = {}
    current_step = -1

    for event in timeline_events:
        payload = event.payload or {}
        event_type = payload.get("event", "")
        step_idx = payload.get("step_index", -1)

        # Track which step we're in
        if "plan.step_started" in event_type:
            current_step = step_idx
            if current_step not in steps_map:
                plan_info = plan_by_step.get(current_step, {})
                steps_map[current_step] = {
                    "step_index": current_step,
                    "step_title": plan_info.get(
                        "step_title", f"Step {current_step + 1}"
                    ),
                    "step_description": plan_info.get("step_description", ""),
                    "status": "running",
                    "thinking_blocks": [],
                    "chain_of_thought_tokens": [],
                    "tool_calls": [],
                    "response_tokens": [],
                    "conclusion": "",
                    "sources_found": 0,
                    "tokens_used": 0,
                    "started_at": payload.get("ts"),
                }

        # Aggregate event data into current step
        if current_step >= 0 and current_step in steps_map:
            step_data = steps_map[current_step]

            # Thinking/reasoning
            if "think.chunk" in event_type or "chain_of_thought" in event_type:
                step_data["chain_of_thought_tokens"].append(
                    ChainOfThoughtEntry(
                        token=payload.get("text") or payload.get("token", ""),
                        timestamp=payload.get("ts"),
                    ).model_dump()
                )

            # Full thinking block
            elif "think_event" in event_type or "react.reason" in event_type:
                step_data["thinking_blocks"].append(
                    ThinkingBlock(
                        text=payload.get("thought", ""),
                        timestamp=payload.get("ts"),
                    ).model_dump()
                )

            # Tool calls
            elif "tool.called" in event_type or "tool_call_query" in event_type:
                step_data["tool_calls"].append(
                    ToolCallDetail(
                        tool_name=payload.get("tool_name", ""),
                        args=payload.get("args", {}),
                        timestamp=payload.get("ts"),
                    ).model_dump()
                )

            # Tool results
            elif "tool.result" in event_type or "tool_call_output" in event_type:
                if step_data["tool_calls"]:
                    last_tool = step_data["tool_calls"][-1]
                    last_tool["summary"] = payload.get("result_summary") or payload.get(
                        "summary", ""
                    )
                    last_tool["result_payload"] = payload.get("result_payload", [])

            # Response/final tokens
            elif "stream_event" in event_type:
                step_data["response_tokens"].append(payload.get("token", ""))

            # Conclusions
            elif "plan.step_completed" in event_type or "react.done" in event_type:
                step_data["conclusion"] = payload.get("summary", "")
                step_data["status"] = "completed"
                step_data["completed_at"] = payload.get("ts")

            elif "plan.step_failed" in event_type:
                step_data["status"] = "failed"
                step_data["completed_at"] = payload.get("ts")

    # Convert to list and fill in missing steps from plan
    result = []
    for step_num, plan_info in plan_by_step.items():
        if step_num in steps_map:
            result.append(steps_map[step_num])
        else:
            # Placeholder for steps not yet started
            result.append(
                {
                    "step_index": step_num,
                    "step_title": plan_info.get("step_title", f"Step {step_num + 1}"),
                    "step_description": plan_info.get("step_description", ""),
                    "status": "pending",
                    "thinking_blocks": [],
                    "chain_of_thought_tokens": [],
                    "tool_calls": [],
                    "response_tokens": [],
                    "conclusion": "",
                    "sources_found": 0,
                    "tokens_used": 0,
                }
            )

    return sorted(result, key=lambda x: x.get("step_index", -1))


@router.get("/{research_id}/resume", response_model=ResearchResumeResponse)
async def get_research_resume(
    research_id: str,
    request: Request,
    from_event_id: str = Query(default="0-0", alias="fromEventId"),
    timeline_limit: int = Query(default=1000, ge=1, le=2000, alias="timelineLimit"),
    include_timeline: bool = Query(default=True, alias="includeTimeline"),
    snapshot_tail: int = Query(default=600, ge=50, le=4000, alias="snapshotTail"),
) -> ResearchResumeResponse:
    state = await get_session_state(research_id)
    active_session = session_store._active_sessions.get(research_id)

    if state is None and active_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research session not found. The id may be stale or never started.",
        )

    token_totals = ResearchTokenTotals.model_validate(
        await get_token_totals(research_id)
    )
    latest_event_id = await get_latest_event_id(research_id)
    pending_input = await load_pending_input(research_id)
    context = await load_context(research_id)
    plan = await load_plan(research_id) or []
    urls = _runtime_urls(request, research_id)

    replay_rows: list[dict[str, Any]] = []
    if include_timeline:
        replay_rows = await replay_events(
            research_id=research_id,
            from_event_id=from_event_id,
            limit=timeline_limit,
        )
    timeline_events = [ResearchReplayEvent.model_validate(row) for row in replay_rows]
    timeline_next_event_id = (
        timeline_events[-1].id if timeline_events else latest_event_id or from_event_id
    )
    streaming_snapshot = await get_streaming_snapshot(
        research_id,
        tail_limit=snapshot_tail,
    )

    # Parse all events into step-wise granular details
    steps_details = _aggregate_step_details(timeline_events, plan)

    if state is None:
        status_str = (
            "running" if active_session and active_session.get("started") else "ready"
        )
        return ResearchResumeResponse(
            research_id=research_id,
            status=status_str,
            current_step=0,
            total_steps=0,
            created_at=None,
            updated_at=None,
            token_totals=token_totals,
            latest_event_id=latest_event_id,
            pending_input=pending_input,
            context=context,
            plan=plan,
            status_url=urls["status_url"],
            replay_url=urls["replay_url"],
            resume_url=urls["resume_url"],
            websocket_url=urls["websocket_url"],
            timeline_from_event_id=from_event_id,
            timeline_next_event_id=timeline_next_event_id,
            timeline_replay_count=len(timeline_events),
            timeline_events=timeline_events,
            streaming_snapshot=streaming_snapshot,
            steps_details=steps_details,
        )

    return ResearchResumeResponse(
        research_id=research_id,
        status=str(state.get("status", "unknown")),
        current_step=int(state.get("current_step", 0)),
        total_steps=int(state.get("total_steps", 0)),
        created_at=state.get("created_at"),
        updated_at=state.get("updated_at"),
        token_totals=token_totals,
        latest_event_id=latest_event_id,
        pending_input=pending_input,
        context=context,
        plan=plan,
        status_url=urls["status_url"],
        replay_url=urls["replay_url"],
        resume_url=urls["resume_url"],
        websocket_url=urls["websocket_url"],
        timeline_from_event_id=from_event_id,
        timeline_next_event_id=timeline_next_event_id,
        timeline_replay_count=len(timeline_events),
        timeline_events=timeline_events,
        streaming_snapshot=streaming_snapshot,
        steps_details=steps_details,
    )


@router.get("/", response_model=ResearchListResponse)
def get_all_research(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    workspace_id: str | None = Query(default=None, alias="workspaceId"),
    title_contains: str | None = Query(default=None, alias="titleContains"),
    desc_contains: str | None = Query(default=None, alias="descContains"),
    prompt_contains: str | None = Query(default=None, alias="promptContains"),
    chat_access: bool | None = Query(default=None, alias="chatAccess"),
    background_processing: bool | None = Query(
        default=None, alias="backgroundProcessing"
    ),
    sort_by: Literal["id", "title", "workspace_id"] = Query(
        default="id", alias="sortBy"
    ),
    sort_order: Literal["asc", "desc"] = Query(default="desc", alias="sortOrder"),
) -> ResearchListResponse:
    try:
        return research_view.getAllResearch(
            page=page,
            size=size,
            workspace_id=workspace_id,
            title_contains=title_contains,
            desc_contains=desc_contains,
            prompt_contains=prompt_contains,
            chat_access=chat_access,
            background_processing=background_processing,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as exc:
        _raise_research_http_error("List research items", exc)


@router.get("/urls", response_model=ResearchSourceListResponse)
@router.get(
    "/sources", response_model=ResearchSourceListResponse, include_in_schema=False
)
def get_research_source_urls(
    research_id: str | None = Query(default=None, alias="researchId"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    created_from: datetime | None = Query(default=None, alias="createdFrom"),
    created_to: datetime | None = Query(default=None, alias="createdTo"),
    updated_from: datetime | None = Query(default=None, alias="updatedFrom"),
    updated_to: datetime | None = Query(default=None, alias="updatedTo"),
    source_type: str | None = Query(default=None, alias="sourceType"),
    url_contains: str | None = Query(default=None, alias="urlContains"),
    sort_by: Literal[
        "created_at", "updated_at", "research_id", "source_type", "source_url"
    ] = Query(default="created_at", alias="sortBy"),
    sort_order: Literal["asc", "desc"] = Query(default="desc", alias="sortOrder"),
) -> ResearchSourceListResponse:
    try:
        return research_view.getResearchSourceUrls(
            research_id=research_id,
            page=page,
            size=size,
            created_from=created_from,
            created_to=created_to,
            updated_from=updated_from,
            updated_to=updated_to,
            source_type=source_type,
            url_contains=url_contains,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as exc:
        _raise_research_http_error("List research source urls", exc)


@router.get("/{research_id}", response_model=ResearchRecord)
def get_research_by_id(research_id: str) -> ResearchRecord:
    try:
        return research_view.getResearch(research_id)
    except Exception as exc:
        _raise_research_http_error(f"Fetch research {research_id}", exc)


@router.post("/", response_model=ResearchRecord, status_code=status.HTTP_201_CREATED)
def create_research(payload: ResearchCreate) -> ResearchRecord:
    try:
        return research_view.createResearch(payload)
    except Exception as exc:
        _raise_research_http_error("Create research", exc)


@router.put("/{research_id}", response_model=ResearchRecord)
def replace_research(research_id: str, payload: ResearchCreate) -> ResearchRecord:
    try:
        return research_view.updateResearch(research_id, payload)
    except Exception as exc:
        _raise_research_http_error(f"Replace research {research_id}", exc)


@router.patch("/{research_id}", response_model=ResearchRecord)
def update_research(research_id: str, payload: ResearchPatch) -> ResearchRecord:
    try:
        return research_view.patchResearch(research_id, payload)
    except Exception as exc:
        _raise_research_http_error(f"Patch research {research_id}", exc)


@router.delete("/{research_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_research(research_id: str) -> Response:
    try:
        research_view.deleteResearch(research_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        _raise_research_http_error(f"Delete research {research_id}", exc)


@router.get("/sources/{source_id}", response_model=ResearchSourceRecord)
def get_research_source(source_id: str) -> ResearchSourceRecord:
    try:
        return research_view.getResearchSource(source_id)
    except Exception as exc:
        _raise_research_http_error(f"Fetch research source {source_id}", exc)


@router.post(
    "/sources",
    response_model=ResearchSourceRecord,
    status_code=status.HTTP_201_CREATED,
)
def create_research_source(payload: ResearchSourceCreate) -> ResearchSourceRecord:
    try:
        return research_view.createResearchSource(payload)
    except Exception as exc:
        _raise_research_http_error("Create research source", exc)


@router.patch("/sources/{source_id}", response_model=ResearchSourceRecord)
def patch_research_source(
    source_id: str,
    payload: ResearchSourcePatch,
) -> ResearchSourceRecord:
    try:
        return research_view.patchResearchSource(source_id, payload)
    except Exception as exc:
        _raise_research_http_error(f"Patch research source {source_id}", exc)


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_research_source(source_id: str) -> Response:
    try:
        research_view.deleteResearchSource(source_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        _raise_research_http_error(f"Delete research source {source_id}", exc)
