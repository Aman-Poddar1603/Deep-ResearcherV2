import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_serializer


WorkspaceAIConfig = Literal["auto", "local", "online"]
IST_TZ = timezone(timedelta(hours=5, minutes=30), name="IST")


class WorkspaceBase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=2, max_length=100)
    desc: str = Field(..., min_length=2, max_length=500)
    icon: str | None = Field(default=None, max_length=200)
    accent_clr: str | None = Field(default=None, max_length=20)
    banner_img: str | None = Field(default=None, max_length=200)
    connected_bucket_id: str | None = None
    ai_config: WorkspaceAIConfig = Field(default="auto")
    workspace_resources_id: str | None = Field(default=None)
    workspace_research_agents: bool = Field(default=True)
    workspace_chat_agents: bool = Field(default=True)


class WorkspacePatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    desc: str | None = Field(default=None, min_length=2, max_length=500)
    icon: str | None = Field(default=None, max_length=200)
    accent_clr: str | None = Field(default=None, max_length=20)
    banner_img: str | None = Field(default=None, max_length=200)
    ai_config: WorkspaceAIConfig | None = Field(default=None)
    connected_bucket_id: str | None = None
    workspace_resources_id: str | None = Field(default=None)


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceOut(WorkspaceBase):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_serializer("created_at", "updated_at", when_used="json")
    def _serialize_timestamps_to_ist_12h(self, value: datetime) -> str:
        # DB values remain UTC; only API JSON output is localized and reformatted.
        dt = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return dt.astimezone(IST_TZ).strftime("%Y-%m-%d %I:%M:%S %p")


class WorkspaceConnectedResearch(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str
    research_ids: str  # comma-separated or JSON string
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkspaceConnectedChats(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str
    chat_session_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkspaceConnectedResources(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    connected_bucket_id: str
    resource_ids: str  # comma-separated or JSON string
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
