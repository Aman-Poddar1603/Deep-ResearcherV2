from pathlib import Path
from typing import Literal, NoReturn

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse

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
from main.src.bucket.bucket_store import bucket_store

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
    name_contains: str | None = Query(default=None, alias="nameContains"),
    status_filter: bool | None = Query(default=None, alias="status"),
    deletable: bool | None = Query(default=None),
    min_total_files: int | None = Query(default=None, alias="minTotalFiles", ge=0),
    max_total_files: int | None = Query(default=None, alias="maxTotalFiles", ge=0),
    min_total_size: int | None = Query(default=None, alias="minTotalSize", ge=0),
    max_total_size: int | None = Query(default=None, alias="maxTotalSize", ge=0),
    sort_by: Literal[
        "updated_at", "created_at", "name", "total_files", "total_size"
    ] = Query(default="updated_at", alias="sortBy"),
    sort_order: Literal["asc", "desc"] = Query(default="desc", alias="sortOrder"),
) -> BucketListResponse:
    try:
        return bucket_view.listBuckets(
            page=page,
            size=size,
            created_by=created_by,
            name_contains=name_contains,
            status=status_filter,
            deletable=deletable,
            min_total_files=min_total_files,
            max_total_files=max_total_files,
            min_total_size=min_total_size,
            max_total_size=max_total_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as exc:
        _raise_bucket_http_error("List buckets", exc)


@router.get("/assets/{asset_path:path}")
def get_asset(asset_path: str) -> FileResponse:
    """Serve files stored under src/store/bucket using relative asset paths."""
    try:
        resolved_path = bucket_store.resolve_asset_path(asset_path)
        if not resolved_path.exists() or not resolved_path.is_file():
            raise KeyError(f"Asset {asset_path} not found")
        return FileResponse(path=resolved_path)
    except Exception as exc:
        _raise_bucket_http_error(f"Fetch asset {asset_path}", exc)


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


@router.post(
    "/{bucket_id}/upload",
    response_model=BucketItemRecord,
    status_code=status.HTTP_201_CREATED,
)
async def upload_file_to_bucket(
    bucket_id: str,
    file: UploadFile = File(...),
    created_by: str = Query(...),
    source: str | None = Query(default=None),
    summary: str | None = Query(default=None),
    connected_workspace_ids: str | None = Query(
        default=None, alias="connectedWorkspaceIds"
    ),
) -> BucketItemRecord:
    """Upload a single file, save it to bucket storage, and record its path in the DB."""
    try:
        content = await file.read()
        file_name = file.filename or "unnamed"
        file_format = Path(file_name).suffix.lstrip(".") or "bin"
        return bucket_view.uploadFile(
            bucket_id=bucket_id,
            file_name=file_name,
            file_format=file_format,
            content=content,
            created_by=created_by,
            source=source,
            summary=summary,
            connected_workspace_ids=connected_workspace_ids,
        )
    except Exception as exc:
        _raise_bucket_http_error(f"Upload file to bucket {bucket_id}", exc)


@router.post(
    "/{bucket_id}/upload/bulk",
    response_model=list[BucketItemRecord],
    status_code=status.HTTP_201_CREATED,
)
async def upload_files_to_bucket(
    bucket_id: str,
    files: list[UploadFile] = File(...),
    created_by: str = Query(...),
    source: str | None = Query(default=None),
    summary: str | None = Query(default=None),
    connected_workspace_ids: str | None = Query(
        default=None, alias="connectedWorkspaceIds"
    ),
) -> list[BucketItemRecord]:
    """Upload multiple files at once, save them to bucket storage, and record each path in the DB."""
    try:
        file_tuples: list[tuple[str, str, bytes]] = []
        for upload in files:
            content = await upload.read()
            file_name = upload.filename or "unnamed"
            file_format = Path(file_name).suffix.lstrip(".") or "bin"
            file_tuples.append((file_name, file_format, content))
        return bucket_view.uploadFiles(
            bucket_id=bucket_id,
            files=file_tuples,
            created_by=created_by,
            source=source,
            summary=summary,
            connected_workspace_ids=connected_workspace_ids,
        )
    except Exception as exc:
        _raise_bucket_http_error(f"Bulk upload to bucket {bucket_id}", exc)


@router.get("/items", response_model=BucketItemListResponse)
def list_bucket_items(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    bucket_id: str | None = Query(default=None, alias="bucketId"),
    file_format: str | None = Query(default=None, alias="fileFormat"),
    source: str | None = Query(default=None),
    created_by: str | None = Query(default=None, alias="createdBy"),
    is_deleted: bool | None = Query(default=None, alias="isDeleted"),
    min_file_size: int | None = Query(default=None, alias="minFileSize", ge=0),
    max_file_size: int | None = Query(default=None, alias="maxFileSize", ge=0),
    file_name_contains: str | None = Query(default=None, alias="fileNameContains"),
    file_path_contains: str | None = Query(default=None, alias="filePathContains"),
    sort_by: Literal["updated_at", "created_at", "file_name", "file_size"] = Query(
        default="updated_at", alias="sortBy"
    ),
    sort_order: Literal["asc", "desc"] = Query(default="desc", alias="sortOrder"),
) -> BucketItemListResponse:
    try:
        return bucket_view.listBucketItems(
            page=page,
            size=size,
            bucket_id=bucket_id,
            file_format=file_format,
            source=source,
            created_by=created_by,
            is_deleted=is_deleted,
            min_file_size=min_file_size,
            max_file_size=max_file_size,
            file_name_contains=file_name_contains,
            file_path_contains=file_path_contains,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as exc:
        _raise_bucket_http_error("List bucket items", exc)


@router.get("/items/{item_id}", response_model=BucketItemRecord)
def get_bucket_item(item_id: str) -> BucketItemRecord:
    try:
        return bucket_view.getBucketItem(item_id)
    except Exception as exc:
        _raise_bucket_http_error(f"Fetch bucket item {item_id}", exc)


@router.get("/items/{item_id}/asset")
def get_bucket_item_asset(item_id: str) -> FileResponse:
    """Serve an uploaded bucket file directly by item id."""
    try:
        item = bucket_view.getBucketItem(item_id)
        resolved_path = bucket_store.resolve_asset_path(item.file_path)
        if not resolved_path.exists() or not resolved_path.is_file():
            raise KeyError(f"Asset for bucket item {item_id} not found")
        return FileResponse(path=resolved_path)
    except Exception as exc:
        _raise_bucket_http_error(f"Fetch asset for bucket item {item_id}", exc)


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
