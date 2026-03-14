import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


def _new_id() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class HistoryType(str, Enum):
    USAGE = "usage"
    RESEARCH = "research"
    CHAT = "chat"
    VERSION = "version"
    TOKEN = "token"
    AI_SUMMARY = "ai_summary"
    BUCKET = "bucket"
    SEARCH = "search"
    EXPORT = "export"
    DOWNLOAD = "download"
    UPLOAD = "upload"
    GENERATION = "generation"


class HistoryActions(str, Enum):
    DELETE = "delete"


class HistoryItem(BaseModel):
    """Generic API shape aligned to `user_usage_history` table."""

    id: str = Field(default_factory=_new_id)
    user_id: str | None = None
    workspace_id: str | None = None
    activity: str | None = None
    type: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    last_seen: datetime = Field(default_factory=_utcnow)
    actions: str | None = None
    url: str | None = None


class HistoryItemPatch(BaseModel):
    user_id: str | None = None
    workspace_id: str | None = None
    activity: str | None = None
    type: str | None = None
    created_at: datetime | None = None
    last_seen: datetime | None = None
    actions: str | None = None
    url: str | None = None


class HistoryItemResponse(BaseModel):
    history_items: list[HistoryItem] = Field(default_factory=list)
    page: int = 1
    total_pages: int = 0
    offset: int = 0


class UserUsageHistoryRecord(HistoryItem):
    pass


class ChatHistoryRecord(BaseModel):
    id: str = Field(default_factory=_new_id)
    chat_thread_id: str | None = None
    workspace_id: str | None = None
    activity: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    last_seen: datetime = Field(default_factory=_utcnow)
    actions: str | None = None
    url: str | None = None


class ResearchHistoryRecord(BaseModel):
    id: str = Field(default_factory=_new_id)
    research_id: str | None = None
    workspace_id: str | None = None
    activity: str | None = None
    status: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    last_seen: datetime = Field(default_factory=_utcnow)
    actions: str | None = None
    url: str | None = None


class VersionHistoryRecord(BaseModel):
    id: str
    version: str
    changes: str
    updated_at: datetime = Field(default_factory=_utcnow)
    created_at: datetime = Field(default_factory=_utcnow)


class TokenCountRecord(BaseModel):
    id: str
    workspace_id: str | None = None
    chat_or_research_id: str | None = None
    chat_or_research_type: str | None = None
    token_type: str | None = None
    count: int | None = None
    updated_at: datetime = Field(default_factory=_utcnow)
    created_at: datetime = Field(default_factory=_utcnow)


class AISummaryRecord(BaseModel):
    id: str
    workspace_id: str | None = None
    prompt: str | None = None
    model: str | None = None
    time_taken_sec: int | None = None
    status: str | None = None
    tokens_used: int | None = None
    original_test: str | None = None
    summary: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)


class BucketHistoryRecord(BaseModel):
    id: str
    workspace_id: str | None = None
    bucket_id: str | None = None
    activity: str | None = None
    file_path: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime | None = None


class SearchRecord(BaseModel):
    id: str
    query: str
    is_aimode: bool = True
    ai_summary: str | None = None
    ai_citations: str | None = None
    total_results: int = 0
    results: str
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
