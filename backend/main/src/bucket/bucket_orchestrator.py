import math
from datetime import datetime, timezone
from typing import Any

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
from main.src.store.DBManager import buckets_db_manager


class BucketOrchestrator:
    def __init__(self):
        self.bucket_table = "buckets"
        self.item_table = "bucket_items"

    def _utcnow_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _paginate(self, items: list[Any], page: int, size: int) -> tuple[list[Any], int, int, int]:
        total_items = len(items)
        total_pages = math.ceil(total_items / size) if total_items > 0 else 0
        offset = (page - 1) * size
        return items[offset : offset + size], total_items, total_pages, offset

    def _db_payload(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = dict(data)
        for key, value in list(payload.items()):
            if isinstance(value, datetime):
                payload[key] = value.isoformat()
        return payload

    def _fetch_one(self, table_name: str, where: dict[str, Any], not_found: str) -> dict[str, Any]:
        result = buckets_db_manager.fetch_one(table_name, where=where)
        if not result.get("success"):
            raise ValueError(result.get("message") or f"Failed to fetch {table_name}")
        row = result.get("data")
        if row is None:
            raise KeyError(not_found)
        return row

    def listBuckets(
        self, page: int = 1, size: int = 20, created_by: str | None = None
    ) -> BucketListResponse:
        where = {"created_by": created_by} if created_by else None
        result = buckets_db_manager.fetch_all(self.bucket_table, where=where)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to list buckets")
        rows = [BucketRecord.model_validate(item) for item in (result.get("data") or [])]
        rows.sort(key=lambda row: row.updated_at, reverse=True)
        page_items, total_items, total_pages, offset = self._paginate(rows, page, size)
        return BucketListResponse(
            items=page_items,
            page=page,
            size=size,
            total_items=total_items,
            total_pages=total_pages,
            offset=offset,
        )

    def getBucket(self, bucket_id: str) -> BucketRecord:
        row = self._fetch_one(self.bucket_table, {"id": bucket_id}, f"Bucket {bucket_id} not found")
        return BucketRecord.model_validate(row)

    def createBucket(self, payload: BucketCreate) -> BucketRecord:
        record = BucketRecord(**payload.model_dump(mode="python"))
        data = self._db_payload(record.model_dump(mode="python"))
        result = buckets_db_manager.insert(self.bucket_table, data)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to create bucket")
        return self.getBucket(data["id"])

    def updateBucket(self, bucket_id: str, payload: BucketCreate) -> BucketRecord:
        self.getBucket(bucket_id)
        record = BucketRecord(id=bucket_id, **payload.model_dump(mode="python"))
        data = self._db_payload(record.model_dump(mode="python"))
        data["updated_at"] = self._utcnow_iso()
        result = buckets_db_manager.update(self.bucket_table, data=data, where={"id": bucket_id})
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to update bucket")
        return self.getBucket(bucket_id)

    def patchBucket(self, bucket_id: str, payload: BucketPatch) -> BucketRecord:
        self.getBucket(bucket_id)
        patch_data = self._db_payload(payload.model_dump(exclude_unset=True, mode="python"))
        if not patch_data:
            return self.getBucket(bucket_id)
        patch_data["updated_at"] = self._utcnow_iso()
        result = buckets_db_manager.update(self.bucket_table, data=patch_data, where={"id": bucket_id})
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to patch bucket")
        return self.getBucket(bucket_id)

    def deleteBucket(self, bucket_id: str) -> None:
        self.getBucket(bucket_id)
        result = buckets_db_manager.delete(self.bucket_table, where={"id": bucket_id})
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to delete bucket")

    def listBucketItems(
        self, page: int = 1, size: int = 20, bucket_id: str | None = None
    ) -> BucketItemListResponse:
        where = {"bucket_id": bucket_id} if bucket_id else None
        result = buckets_db_manager.fetch_all(self.item_table, where=where)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to list bucket items")
        rows = [BucketItemRecord.model_validate(item) for item in (result.get("data") or [])]
        rows.sort(key=lambda row: row.updated_at, reverse=True)
        page_items, total_items, total_pages, offset = self._paginate(rows, page, size)
        return BucketItemListResponse(
            items=page_items,
            page=page,
            size=size,
            total_items=total_items,
            total_pages=total_pages,
            offset=offset,
        )

    def getBucketItem(self, item_id: str) -> BucketItemRecord:
        row = self._fetch_one(self.item_table, {"id": item_id}, f"Bucket item {item_id} not found")
        return BucketItemRecord.model_validate(row)

    def createBucketItem(self, payload: BucketItemCreate) -> BucketItemRecord:
        record = BucketItemRecord(**payload.model_dump(mode="python"))
        data = self._db_payload(record.model_dump(mode="python"))
        result = buckets_db_manager.insert(self.item_table, data)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to create bucket item")
        return self.getBucketItem(data["id"])

    def updateBucketItem(self, item_id: str, payload: BucketItemCreate) -> BucketItemRecord:
        self.getBucketItem(item_id)
        record = BucketItemRecord(id=item_id, **payload.model_dump(mode="python"))
        data = self._db_payload(record.model_dump(mode="python"))
        data["updated_at"] = self._utcnow_iso()
        result = buckets_db_manager.update(self.item_table, data=data, where={"id": item_id})
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to update bucket item")
        return self.getBucketItem(item_id)

    def patchBucketItem(self, item_id: str, payload: BucketItemPatch) -> BucketItemRecord:
        self.getBucketItem(item_id)
        patch_data = self._db_payload(payload.model_dump(exclude_unset=True, mode="python"))
        if not patch_data:
            return self.getBucketItem(item_id)
        patch_data["updated_at"] = self._utcnow_iso()
        result = buckets_db_manager.update(self.item_table, data=patch_data, where={"id": item_id})
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to patch bucket item")
        return self.getBucketItem(item_id)

    def deleteBucketItem(self, item_id: str) -> None:
        self.getBucketItem(item_id)
        result = buckets_db_manager.delete(self.item_table, where={"id": item_id})
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to delete bucket item")
