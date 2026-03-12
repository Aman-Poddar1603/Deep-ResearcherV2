from datetime import datetime, timezone
import uuid
from typing import Literal, cast

from pydantic import BaseModel, Field, field_validator


BUCKET_ITEM_TYPE: tuple[str, ...] = (
    "image",
    "video",
    "files",
    "audio",
    "others",
)

BucketItemType = Literal["image", "video", "files", "audio", "others"]


def _new_id() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _clean_text_list(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()

    for value in values:
        item = value.strip()
        if not item:
            continue

        normalized = item.casefold()
        if normalized in seen:
            continue

        seen.add(normalized)
        cleaned.append(item)

    return cleaned


class Assets(BaseModel):
    asset_id: str = Field(default_factory=_new_id, description="Unique asset ID")
    bucket_id: str = Field(..., description="ID of the bucket this asset belongs to")
    asset_type: BucketItemType = Field(
        ...,
        description="Type of asset stored in this record",
        examples=["image"],
    )
    name: str = Field(..., min_length=2, max_length=500)
    desc: str | None = Field(default=None, max_length=500)
    upload_time: datetime = Field(default_factory=_utcnow)
    url: str | None = Field(default=None, max_length=300)
    tags: list[str] = Field(
        default_factory=list,
        max_length=50,
        description="Tags attached to this asset",
    )
    created_at: datetime = Field(
        default_factory=_utcnow,
        description="Timestamp when the asset was created",
    )
    updated_at: datetime = Field(
        default_factory=_utcnow,
        description="Timestamp when the asset was last updated",
    )

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        return _clean_text_list(value)


class GetBucketAsset(BaseModel):
    bucket_id: str = Field(
        ...,
        description="ID of the bucket this container summary belongs to",
    )
    bucket_container_type: BucketItemType = Field(
        ...,
        description="Type of assets tracked by this bucket container",
        examples=["image"],
    )
    bucket_container_items: int = Field(
        default=0,
        ge=0,
        description="Number of items in the bucket container",
    )
    bucket_container_size: int = Field(
        default=0,
        ge=0,
        description="Size of the bucket container in megabytes",
    )


class GetBucket(BaseModel):
    bucket_id: str = Field(default_factory=_new_id)
    bucket_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Name of the bucket",
    )
    bucket_desc: str | None = Field(
        default=None,
        max_length=500,
        description="Description of the bucket",
    )
    bucket_icon: str | None = Field(
        default=None,
        max_length=200,
        description="Bucket icon name",
    )
    bucket_assets: list[str] = Field(
        default_factory=list,
        description="List of asset IDs in the bucket",
    )
    bucket_total_assets: int = Field(
        default=0,
        ge=0,
        description="Total number of assets in the bucket",
    )
    bucket_size: int = Field(
        default=0,
        ge=0,
        description="Size of the bucket in megabytes",
    )
    bucket_tags: list[str] = Field(
        default_factory=list,
        max_length=50,
        description="List of tags for the bucket",
    )
    bucket_container_types: list[BucketItemType] = Field(
        default_factory=list,
        max_length=len(BUCKET_ITEM_TYPE),
        description="Allowed asset container types for the bucket",
        examples=[["image", "files"]],
    )
    bucket_containers: list[GetBucketAsset] = Field(
        default_factory=list,
        description="Per-container asset summary for the bucket",
    )
    bucket_created_at: datetime = Field(
        default_factory=_utcnow,
        description="Timestamp when the bucket was created",
    )
    bucket_updated_at: datetime = Field(
        default_factory=_utcnow,
        description="Timestamp when the bucket was last updated",
    )

    @field_validator("bucket_tags")
    @classmethod
    def validate_bucket_tags(cls, value: list[str]) -> list[str]:
        return _clean_text_list(value)

    @field_validator("bucket_container_types")
    @classmethod
    def validate_bucket_container_types(
        cls, value: list[BucketItemType]
    ) -> list[BucketItemType]:
        cleaned = _clean_text_list(list(value))
        return [cast(BucketItemType, item) for item in cleaned]


class GetBuckets(BaseModel):
    buckets: list[GetBucket] = Field(
        default_factory=list,
        description="List of buckets",
    )
    offset: int = Field(default=0, ge=0, description="Pagination offset")
    limit: int = Field(default=10, ge=1, le=100, description="Pagination limit")
    page: int = Field(default=1, ge=1, description="Current page number")
    total_buckets: int = Field(
        default=0,
        ge=0,
        description="Total number of buckets available",
    )


class createBucket(BaseModel):
    bucket_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Name of the bucket",
    )
    bucket_desc: str | None = Field(
        default=None,
        max_length=500,
        description="Description of the bucket",
    )
    bucket_icon: str | None = Field(
        default=None,
        max_length=200,
        description="Bucket icon name",
    )
    bucket_tags: list[str] = Field(
        default_factory=list,
        max_length=50,
        description="List of tags for the bucket",
    )
    bucket_container_types: list[BucketItemType] = Field(
        ...,
        min_length=1,
        max_length=len(BUCKET_ITEM_TYPE),
        description="Supported asset types for the bucket",
        examples=[["image", "files"]],
    )

    @field_validator("bucket_tags")
    @classmethod
    def validate_bucket_tags(cls, value: list[str]) -> list[str]:
        return _clean_text_list(value)

    @field_validator("bucket_container_types")
    @classmethod
    def validate_bucket_container_types(
        cls, value: list[BucketItemType]
    ) -> list[BucketItemType]:
        cleaned = _clean_text_list(list(value))
        return [cast(BucketItemType, item) for item in cleaned]


class updateBucket(BaseModel):
    bucket_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        description="Name of the bucket",
    )
    bucket_desc: str | None = Field(
        default=None,
        max_length=500,
        description="Description of the bucket",
    )
    bucket_icon: str | None = Field(
        default=None,
        max_length=200,
        description="Bucket icon name",
    )
    bucket_tags: list[str] | None = Field(
        default=None,
        max_length=50,
        description="List of tags for the bucket",
    )
    bucket_container_types: list[BucketItemType] | None = Field(
        default=None,
        min_length=1,
        max_length=len(BUCKET_ITEM_TYPE),
        description="Updated supported asset types for the bucket",
        examples=[["image", "video"]],
    )

    @field_validator("bucket_tags")
    @classmethod
    def validate_bucket_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _clean_text_list(value)

    @field_validator("bucket_container_types")
    @classmethod
    def validate_bucket_container_types(
        cls, value: list[BucketItemType] | None
    ) -> list[BucketItemType] | None:
        if value is None:
            return None
        cleaned = _clean_text_list(list(value))
        return [cast(BucketItemType, item) for item in cleaned]


class deleteBucket(BaseModel):
    bucket_id: str = Field(..., description="ID of the bucket to be deleted")
