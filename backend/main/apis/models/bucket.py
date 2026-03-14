import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _new_id() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BucketRecord(BaseModel):
    """Represents `buckets` table rows."""

    id: str = Field(default_factory=_new_id)
    name: str = Field(..., min_length=2, max_length=100)
    allowed_file_types: str = Field(..., min_length=1)
    description: str | None = None
    deletable: bool = True
    status: bool = True
    total_files: int = 0
    total_size: int = 0
    created_by: str = Field(..., min_length=1)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class BucketCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    allowed_file_types: str = Field(..., min_length=1)
    description: str | None = None
    deletable: bool = True
    status: bool = True
    total_files: int = 0
    total_size: int = 0
    created_by: str = Field(..., min_length=1)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class BucketPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    allowed_file_types: str | None = None
    description: str | None = None
    deletable: bool | None = None
    status: bool | None = None
    total_files: int | None = None
    total_size: int | None = None
    created_by: str | None = None
    updated_at: datetime | None = None


class BucketItemRecord(BaseModel):
    """Represents `bucket_items` table rows."""

    id: str = Field(default_factory=_new_id)
    bucket_id: str
    connected_workspace_ids: str | None = None
    source: str | None = None
    file_name: str
    file_path: str
    file_format: str
    file_size: int
    summary: str | None = None
    is_deleted: bool = False
    created_by: str
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class BucketItemCreate(BaseModel):
    bucket_id: str
    connected_workspace_ids: str | None = None
    source: str | None = None
    file_name: str
    file_path: str
    file_format: str
    file_size: int
    summary: str | None = None
    is_deleted: bool = False
    created_by: str
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class BucketItemPatch(BaseModel):
    connected_workspace_ids: str | None = None
    source: str | None = None
    file_name: str | None = None
    file_path: str | None = None
    file_format: str | None = None
    file_size: int | None = None
    summary: str | None = None
    is_deleted: bool | None = None
    updated_at: datetime | None = None


class BucketListResponse(BaseModel):
    items: list[BucketRecord]
    page: int
    size: int
    total_items: int
    total_pages: int
    offset: int


class BucketItemListResponse(BaseModel):
    items: list[BucketItemRecord]
    page: int
    size: int
    total_items: int
    total_pages: int
    offset: int


# Backward-compatible aliases (legacy API naming)
Assets = BucketItemRecord
GetBucket = BucketRecord


class GetBuckets(BaseModel):
    buckets: list[BucketRecord] = Field(default_factory=list)
    offset: int = 0
    limit: int = 10
    page: int = 1
    total_buckets: int = 0


class createBucket(BucketCreate):
    pass


class updateBucket(BucketPatch):
    pass


class deleteBucket(BaseModel):
    bucket_id: str
