from datetime import datetime, timezone
import math
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field


# Router only: include this in main server from another file.
router = APIRouter(prefix="/research", tags=["research"])


class ResearchBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    query: str = Field(..., min_length=2)
    source_urls: list[str] = Field(default_factory=list)
    status: str = Field(default="pending")


class ResearchCreate(ResearchBase):
    pass


class ResearchPut(ResearchBase):
    pass


class ResearchPatch(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    query: str | None = Field(default=None, min_length=2)
    source_urls: list[str] | None = None
    status: str | None = None


class ResearchOut(ResearchBase):
    id: int
    created_at: datetime
    updated_at: datetime


class ResearchSourceUrlOut(BaseModel):
    research_id: int
    research_title: str
    url: str
    status: str
    created_at: datetime
    updated_at: datetime


class ResearchSourceUrlsResponse(BaseModel):
    items: list[ResearchSourceUrlOut]
    page: int
    size: int
    total_items: int
    total_pages: int
    offset: int
    has_next: bool
    has_prev: bool
    research_id: int | None = None


# Basic in-memory template store. Replace with DBManager/service layer later.
_research_store: dict[int, ResearchOut] = {}
_next_id = 1


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_or_404(research_id: int) -> ResearchOut:
    item = _research_store.get(research_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research item {research_id} not found",
        )
    return item


@router.get("/", response_model=list[ResearchOut])
def get_all_research() -> list[ResearchOut]:
    return list(_research_store.values())


@router.get("/urls", response_model=ResearchSourceUrlsResponse)
@router.get(
    "/sources", response_model=ResearchSourceUrlsResponse, include_in_schema=False
)
def get_research_source_urls(
    research_id: int | None = Query(default=None, alias="researchId", ge=1),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    created_from: datetime | None = Query(default=None, alias="createdFrom"),
    created_to: datetime | None = Query(default=None, alias="createdTo"),
    updated_from: datetime | None = Query(default=None, alias="updatedFrom"),
    updated_to: datetime | None = Query(default=None, alias="updatedTo"),
    status_filter: str | None = Query(default=None, alias="status"),
    title_contains: str | None = Query(default=None, alias="titleContains"),
    url_contains: str | None = Query(default=None, alias="urlContains"),
    sort_by: Literal[
        "created_at", "updated_at", "research_id", "research_title", "url"
    ] = Query(default="created_at", alias="sortBy"),
    sort_order: Literal["asc", "desc"] = Query(default="desc", alias="sortOrder"),
) -> ResearchSourceUrlsResponse:
    if research_id is not None:
        target = _research_store.get(research_id)
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Research item {research_id} not found",
            )
        research_items = [target]
    else:
        # Keep ordering deterministic for easier UI reconciliation.
        research_items = sorted(_research_store.values(), key=lambda item: item.id)

    if created_from is not None:
        research_items = [
            item for item in research_items if item.created_at >= created_from
        ]

    if created_to is not None:
        research_items = [
            item for item in research_items if item.created_at <= created_to
        ]

    if updated_from is not None:
        research_items = [
            item for item in research_items if item.updated_at >= updated_from
        ]

    if updated_to is not None:
        research_items = [
            item for item in research_items if item.updated_at <= updated_to
        ]

    if status_filter:
        normalized_status = status_filter.strip().lower()
        research_items = [
            item
            for item in research_items
            if item.status.strip().lower() == normalized_status
        ]

    if title_contains:
        title_term = title_contains.strip().lower()
        research_items = [
            item for item in research_items if title_term in item.title.lower()
        ]

    flattened: list[ResearchSourceUrlOut] = []
    for item in research_items:
        for source_url in item.source_urls:
            if url_contains and url_contains.strip().lower() not in source_url.lower():
                continue

            flattened.append(
                ResearchSourceUrlOut(
                    research_id=item.id,
                    research_title=item.title,
                    url=source_url,
                    status=item.status,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
            )

    reverse_order = sort_order == "desc"

    if sort_by == "research_id":
        flattened.sort(
            key=lambda row: (row.research_id, row.url.lower()), reverse=reverse_order
        )
    elif sort_by == "research_title":
        flattened.sort(
            key=lambda row: (row.research_title.lower(), row.url.lower()),
            reverse=reverse_order,
        )
    elif sort_by == "url":
        flattened.sort(key=lambda row: row.url.lower(), reverse=reverse_order)
    elif sort_by == "updated_at":
        flattened.sort(
            key=lambda row: (row.updated_at, row.research_id, row.url.lower()),
            reverse=reverse_order,
        )
    else:
        flattened.sort(
            key=lambda row: (row.created_at, row.research_id, row.url.lower()),
            reverse=reverse_order,
        )

    total_items = len(flattened)
    total_pages = math.ceil(total_items / size) if total_items > 0 else 0
    offset = (page - 1) * size
    page_items = flattened[offset : offset + size]

    return ResearchSourceUrlsResponse(
        items=page_items,
        page=page,
        size=size,
        total_items=total_items,
        total_pages=total_pages,
        offset=offset,
        has_next=page < total_pages,
        has_prev=page > 1,
        research_id=research_id,
    )


@router.get("/{research_id}", response_model=ResearchOut)
def get_research_by_id(research_id: int) -> ResearchOut:
    return _get_or_404(research_id)


@router.post("/", response_model=ResearchOut, status_code=status.HTTP_201_CREATED)
def create_research(payload: ResearchCreate) -> ResearchOut:
    global _next_id

    now = _utcnow()
    item = ResearchOut(
        id=_next_id, created_at=now, updated_at=now, **payload.model_dump()
    )
    _research_store[_next_id] = item
    _next_id += 1
    return item


@router.put("/{research_id}", response_model=ResearchOut)
def replace_research(research_id: int, payload: ResearchPut) -> ResearchOut:
    current = _get_or_404(research_id)
    updated = ResearchOut(
        id=current.id,
        created_at=current.created_at,
        updated_at=_utcnow(),
        **payload.model_dump(),
    )
    _research_store[research_id] = updated
    return updated


@router.patch("/{research_id}", response_model=ResearchOut)
def update_research(research_id: int, payload: ResearchPatch) -> ResearchOut:
    current = _get_or_404(research_id)
    patch_data = payload.model_dump(exclude_unset=True)

    merged = current.model_dump()
    merged.update(patch_data)
    merged["updated_at"] = _utcnow()

    updated = ResearchOut(**merged)
    _research_store[research_id] = updated
    return updated
