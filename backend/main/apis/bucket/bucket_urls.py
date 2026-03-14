from typing import NoReturn

from fastapi import APIRouter, HTTPException, Query, Response, status

from main.apis.models.bucket import (
    BucketCreate,
    BucketItemCreate,
    BucketItemListResponse,
    BucketItemPatch,
    BucketItemRecord,
    BucketListResponse,
    BucketPatch,
    BucketRecord,
)
from main.src.bucket import bucket_orchestrator

router = APIRouter(prefix="/bucket", tags=["bucket"])

bucket_view = bucket_orchestrator.BucketOrchestrator()


def _raise_bucket_http_error(action: str, exc: Exception) -> NoReturn:
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


@router.get("/", response_model=BucketListResponse)
def list_buckets(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    created_by: str | None = Query(default=None, alias="createdBy"),
) -> BucketListResponse:
    try:
        return bucket_view.listBuckets(page=page, size=size, created_by=created_by)
    except Exception as exc:
        _raise_bucket_http_error("List buckets", exc)


@router.get("/{bucket_id}", response_model=BucketRecord)
def get_bucket(bucket_id: str) -> BucketRecord:
    try:
        return bucket_view.getBucket(bucket_id)
    except Exception as exc:
        _raise_bucket_http_error(f"Fetch bucket {bucket_id}", exc)


@router.post("/", response_model=BucketRecord, status_code=status.HTTP_201_CREATED)
def create_bucket(payload: BucketCreate) -> BucketRecord:
    try:
        return bucket_view.createBucket(payload)
    except Exception as exc:
        _raise_bucket_http_error("Create bucket", exc)


@router.put("/{bucket_id}", response_model=BucketRecord)
def replace_bucket(bucket_id: str, payload: BucketCreate) -> BucketRecord:
    try:
        return bucket_view.updateBucket(bucket_id, payload)
    except Exception as exc:
        _raise_bucket_http_error(f"Replace bucket {bucket_id}", exc)


@router.patch("/{bucket_id}", response_model=BucketRecord)
def patch_bucket(bucket_id: str, payload: BucketPatch) -> BucketRecord:
    try:
        return bucket_view.patchBucket(bucket_id, payload)
    except Exception as exc:
        _raise_bucket_http_error(f"Patch bucket {bucket_id}", exc)


@router.delete("/{bucket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bucket(bucket_id: str) -> Response:
    try:
        bucket_view.deleteBucket(bucket_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        _raise_bucket_http_error(f"Delete bucket {bucket_id}", exc)


@router.get("/items", response_model=BucketItemListResponse)
def list_bucket_items(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    bucket_id: str | None = Query(default=None, alias="bucketId"),
) -> BucketItemListResponse:
    try:
        return bucket_view.listBucketItems(page=page, size=size, bucket_id=bucket_id)
    except Exception as exc:
        _raise_bucket_http_error("List bucket items", exc)


@router.get("/items/{item_id}", response_model=BucketItemRecord)
def get_bucket_item(item_id: str) -> BucketItemRecord:
    try:
        return bucket_view.getBucketItem(item_id)
    except Exception as exc:
        _raise_bucket_http_error(f"Fetch bucket item {item_id}", exc)


@router.post(
    "/items", response_model=BucketItemRecord, status_code=status.HTTP_201_CREATED
)
def create_bucket_item(payload: BucketItemCreate) -> BucketItemRecord:
    try:
        return bucket_view.createBucketItem(payload)
    except Exception as exc:
        _raise_bucket_http_error("Create bucket item", exc)


@router.put("/items/{item_id}", response_model=BucketItemRecord)
def replace_bucket_item(item_id: str, payload: BucketItemCreate) -> BucketItemRecord:
    try:
        return bucket_view.updateBucketItem(item_id, payload)
    except Exception as exc:
        _raise_bucket_http_error(f"Replace bucket item {item_id}", exc)


@router.patch("/items/{item_id}", response_model=BucketItemRecord)
def patch_bucket_item(item_id: str, payload: BucketItemPatch) -> BucketItemRecord:
    try:
        return bucket_view.patchBucketItem(item_id, payload)
    except Exception as exc:
        _raise_bucket_http_error(f"Patch bucket item {item_id}", exc)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bucket_item(item_id: str) -> Response:
    try:
        bucket_view.deleteBucketItem(item_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        _raise_bucket_http_error(f"Delete bucket item {item_id}", exc)
