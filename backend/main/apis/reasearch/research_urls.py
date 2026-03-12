from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
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
