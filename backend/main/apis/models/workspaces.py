from pydantic import BaseModel, Field
import uuid
from datetime import datetime, timezone

# Pdantic models for request/response validation and documentation


class WorkspaceBase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ai_config: dict = Field(default_factory=dict)
    bucket_id: str | None = Field(default=None, max_length=512)


class WorkspaceCreate(WorkspaceBase):
    name: str = Field(..., min_length=2, max_length=100)
    short_desc: str = Field(..., min_length=2, max_length=500)
    icon: str | None = Field(default=None, max_length=200)
    accent_clr: str | None = Field(default=None, max_length=20)
    banner_img: str | None = Field(default=None, max_length=200)
    tags: str | None = Field(default=None, max_length=200)


class WorkspaceResources(BaseModel):
    resource_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=2, max_length=500)
    desc: str | None = Field(default=None, max_length=500)
    upload_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    url: str | None = Field(default=None, max_length=300)
    tags: list[str] | None = Field(default=None, max_length=200)
    bucket_id: str | None = Field(default=None, max_length=512)


class WorkspacePatch(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    desc: str | None = Field(default=None, min_length=2)
    tags: list[str] | None = None


class WorkspaceList(WorkspaceBase):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=10, ge=1, le=100)
    wykspcs: list[WorkspaceCreate] = Field(default_factory=list)


class WorkspaceOut(WorkspaceList):
    created_at: datetime
    updated_at: datetime