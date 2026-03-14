import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _new_id() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChatThreadRecord(BaseModel):
    """Represents `chat_threads` table rows."""

    thread_id: str = Field(default_factory=_new_id)
    thread_title: str | None = None
    workspace_id: str | None = None
    user_id: str | None = None
    metadata: str | None = None
    token_count: int | None = None
    is_pinned: bool | None = None
    pinned_at: datetime | None = None
    pinned_order: int | None = None
    created_by: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ChatThreadCreate(BaseModel):
    thread_id: str = Field(default_factory=_new_id)
    thread_title: str | None = None
    workspace_id: str | None = None
    user_id: str | None = None
    metadata: str | None = None
    token_count: int | None = None
    is_pinned: bool | None = None
    pinned_at: datetime | None = None
    pinned_order: int | None = None
    created_by: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ChatThreadPatch(BaseModel):
    thread_title: str | None = None
    workspace_id: str | None = None
    user_id: str | None = None
    metadata: str | None = None
    token_count: int | None = None
    is_pinned: bool | None = None
    pinned_at: datetime | None = None
    pinned_order: int | None = None
    created_by: str | None = None
    updated_at: datetime | None = None


class ChatMessageRecord(BaseModel):
    """Represents `chat_messages` table rows."""

    message_id: str = Field(default_factory=_new_id)
    thread_id: str | None = None
    message_seq: int | None = None
    parent_id: str | None = None
    role: str | None = None
    content: str | None = None
    citations: str | None = None
    token_count: int | None = None
    attachments: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ChatMessageCreate(BaseModel):
    message_id: str = Field(default_factory=_new_id)
    thread_id: str | None = None
    message_seq: int | None = None
    parent_id: str | None = None
    role: str | None = None
    content: str | None = None
    citations: str | None = None
    token_count: int | None = None
    attachments: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ChatMessagePatch(BaseModel):
    message_seq: int | None = None
    parent_id: str | None = None
    role: str | None = None
    content: str | None = None
    citations: str | None = None
    token_count: int | None = None
    attachments: str | None = None
    updated_at: datetime | None = None


class ChatAttachmentRecord(BaseModel):
    """Represents `chat_attachments` table rows."""

    attachment_id: str = Field(default_factory=_new_id)
    message_id: str | None = None
    attachment_type: str | None = None
    attachment_path: str | None = None
    attachment_size: int | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ChatAttachmentCreate(BaseModel):
    attachment_id: str = Field(default_factory=_new_id)
    message_id: str | None = None
    attachment_type: str | None = None
    attachment_path: str | None = None
    attachment_size: int | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ChatAttachmentPatch(BaseModel):
    attachment_type: str | None = None
    attachment_path: str | None = None
    attachment_size: int | None = None
    updated_at: datetime | None = None


class ChatThreadListResponse(BaseModel):
    items: list[ChatThreadRecord]
    page: int
    size: int
    total_items: int
    total_pages: int
    offset: int


class ChatMessageListResponse(BaseModel):
    items: list[ChatMessageRecord]
    page: int
    size: int
    total_items: int
    total_pages: int
    offset: int


class ChatAttachmentListResponse(BaseModel):
    items: list[ChatAttachmentRecord]
    page: int
    size: int
    total_items: int
    total_pages: int
    offset: int


# Optional compatibility aliases
ChatThread = ChatThreadRecord
ChatMessage = ChatMessageRecord
ChatAttachment = ChatAttachmentRecord
