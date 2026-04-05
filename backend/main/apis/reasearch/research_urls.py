from __future__ import annotations

import asyncio
import json
import logging
import math
import uuid
from datetime import datetime
from typing import Any, Literal, NoReturn

from fastapi import APIRouter, HTTPException, Query, Response, WebSocket, status

from main.apis.models.research import (
    ResearchCreate,
    ResearchListResponse,
    ResearchPatch,
    ResearchRecord,
    ResearchSourceCreate,
    ResearchSourceListResponse,
    ResearchSourcePatch,
    ResearchSourceRecord,
    ResearchStartRequest,
    ResearchStartResponse,
    ResearchStatusResponse,
    ResearchTokenTotals,
    StopResearchResponse,
)
from main.src.research import session_store
from main.src.research import router as research_runtime_router
from main.src.research.emitter import WSEmitter
from main.src.research.session import get_session_state, get_token_totals
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


@router.post("/start", response_model=ResearchStartResponse)
async def start_research_session(
    payload: ResearchStartRequest,
) -> ResearchStartResponse:
    research_id = str(uuid.uuid4())
    _register_runtime_session(research_id, payload)
    return ResearchStartResponse(research_id=research_id, status="ready")


@router.post("/{research_id}/start", response_model=ResearchStartResponse)
async def start_research_runtime(
    research_id: str,
    payload: ResearchStartRequest,
) -> ResearchStartResponse:
    _register_runtime_session(research_id, payload)
    return ResearchStartResponse(research_id=research_id, status="ready")


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
    # First check active sessions
    session = session_store._active_sessions.get(research_id)
    if session:
        # Session is active but not yet saved to Redis
        token_totals = ResearchTokenTotals.model_validate(
            await get_token_totals(research_id)
        )
        status_str = "running" if session.get("started") else "ready"
        return ResearchStatusResponse(
            research_id=research_id,
            status=status_str,
            current_step=0,
            total_steps=0,
            created_at=None,
            updated_at=None,
            token_totals=token_totals,
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
