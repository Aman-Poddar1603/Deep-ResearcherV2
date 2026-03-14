import math
from datetime import datetime, timezone
from typing import Any, Literal

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
from main.src.store.bucket.bucket_store import bucket_store


class BucketOrchestrator:
    def __init__(self):
        self.bucket_table = "buckets"
        self.item_table = "bucket_items"

    def _utcnow_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _paginate(
        self, items: list[Any], page: int, size: int
    ) -> tuple[list[Any], int, int, int]:
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

    def _parse_datetime(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            normalized = value.replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(normalized)
            except ValueError:
                pass
        return datetime.min

    def _fetch_one(
        self, table_name: str, where: dict[str, Any], not_found: str
    ) -> dict[str, Any]:
        result = buckets_db_manager.fetch_one(table_name, where=where)
        if not result.get("success"):
            raise ValueError(result.get("message") or f"Failed to fetch {table_name}")
        row = result.get("data")
        if row is None:
            raise KeyError(not_found)
        return row

    def _sync_bucket_stats(self, bucket_id: str) -> None:
        """Sync total_files and total_size on the bucket record from disk."""
        total_files = bucket_store.get_file_count(bucket_id)
        total_size = bucket_store.get_bucket_size(bucket_id)
        buckets_db_manager.update(
            self.bucket_table,
            data={
                "total_files": total_files,
                "total_size": total_size,
                "updated_at": self._utcnow_iso(),
            },
            where={"id": bucket_id},
        )

    def listBuckets(
        self,
        page: int = 1,
        size: int = 20,
        created_by: str | None = None,
        name_contains: str | None = None,
        status: bool | None = None,
        deletable: bool | None = None,
        min_total_files: int | None = None,
        max_total_files: int | None = None,
        min_total_size: int | None = None,
        max_total_size: int | None = None,
        sort_by: Literal[
            "updated_at", "created_at", "name", "total_files", "total_size"
        ] = "updated_at",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> BucketListResponse:
        where: dict[str, Any] = {}
        if created_by is not None:
            where["created_by"] = created_by
        if status is not None:
            where["status"] = status
        if deletable is not None:
            where["deletable"] = deletable

        result = buckets_db_manager.fetch_all(self.bucket_table, where=where)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to list buckets")
        rows = [
            BucketRecord.model_validate(item) for item in (result.get("data") or [])
        ]

        if name_contains:
            term = name_contains.strip().lower()
            rows = [row for row in rows if term in (row.name or "").lower()]
        if min_total_files is not None:
            rows = [row for row in rows if (row.total_files or 0) >= min_total_files]
        if max_total_files is not None:
            rows = [row for row in rows if (row.total_files or 0) <= max_total_files]
        if min_total_size is not None:
            rows = [row for row in rows if (row.total_size or 0) >= min_total_size]
        if max_total_size is not None:
            rows = [row for row in rows if (row.total_size or 0) <= max_total_size]

        reverse_order = sort_order == "desc"
        if sort_by == "created_at":
            rows.sort(
                key=lambda row: self._parse_datetime(row.created_at),
                reverse=reverse_order,
            )
        elif sort_by == "name":
            rows.sort(key=lambda row: (row.name or "").lower(), reverse=reverse_order)
        elif sort_by == "total_files":
            rows.sort(key=lambda row: row.total_files or 0, reverse=reverse_order)
        elif sort_by == "total_size":
            rows.sort(key=lambda row: row.total_size or 0, reverse=reverse_order)
        else:
            rows.sort(
                key=lambda row: self._parse_datetime(row.updated_at),
                reverse=reverse_order,
            )

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
        row = self._fetch_one(
            self.bucket_table, {"id": bucket_id}, f"Bucket {bucket_id} not found"
        )
        return BucketRecord.model_validate(row)

    def createBucket(self, payload: BucketCreate) -> BucketRecord:
        record = BucketRecord(**payload.model_dump(mode="python"))
        data = self._db_payload(record.model_dump(mode="python"))
        result = buckets_db_manager.insert(self.bucket_table, data)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to create bucket")
        # Create physical directory tree in src/store/bucket/<id>/
        bucket_store.create_bucket_directory(record.id)
        return self.getBucket(data["id"])

    def updateBucket(self, bucket_id: str, payload: BucketCreate) -> BucketRecord:
        self.getBucket(bucket_id)
        record = BucketRecord(id=bucket_id, **payload.model_dump(mode="python"))
        data = self._db_payload(record.model_dump(mode="python"))
        data["updated_at"] = self._utcnow_iso()
        result = buckets_db_manager.update(
            self.bucket_table, data=data, where={"id": bucket_id}
        )
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to update bucket")
        return self.getBucket(bucket_id)

    def patchBucket(self, bucket_id: str, payload: BucketPatch) -> BucketRecord:
        self.getBucket(bucket_id)
        patch_data = self._db_payload(
            payload.model_dump(exclude_unset=True, mode="python")
        )
        if not patch_data:
            return self.getBucket(bucket_id)
        patch_data["updated_at"] = self._utcnow_iso()
        result = buckets_db_manager.update(
            self.bucket_table, data=patch_data, where={"id": bucket_id}
        )
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to patch bucket")
        return self.getBucket(bucket_id)

    def deleteBucket(self, bucket_id: str) -> None:
        self.getBucket(bucket_id)
        # Remove all child items from DB first
        buckets_db_manager.delete(self.item_table, where={"bucket_id": bucket_id})
        # Remove the bucket record
        result = buckets_db_manager.delete(self.bucket_table, where={"id": bucket_id})
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to delete bucket")
        # Remove physical files from src/store/bucket/<id>/
        bucket_store.delete_bucket_directory(bucket_id)

    def listBucketItems(
        self,
        page: int = 1,
        size: int = 20,
        bucket_id: str | None = None,
        file_format: str | None = None,
        source: str | None = None,
        created_by: str | None = None,
        is_deleted: bool | None = None,
        min_file_size: int | None = None,
        max_file_size: int | None = None,
        file_name_contains: str | None = None,
        file_path_contains: str | None = None,
        sort_by: Literal[
            "updated_at", "created_at", "file_name", "file_size"
        ] = "updated_at",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> BucketItemListResponse:
        where: dict[str, Any] = {}
        if bucket_id is not None:
            where["bucket_id"] = bucket_id
        if file_format is not None:
            where["file_format"] = file_format
        if source is not None:
            where["source"] = source
        if created_by is not None:
            where["created_by"] = created_by
        if is_deleted is not None:
            where["is_deleted"] = is_deleted

        result = buckets_db_manager.fetch_all(self.item_table, where=where)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to list bucket items")
        rows = [
            BucketItemRecord.model_validate(item) for item in (result.get("data") or [])
        ]

        if min_file_size is not None:
            rows = [row for row in rows if (row.file_size or 0) >= min_file_size]
        if max_file_size is not None:
            rows = [row for row in rows if (row.file_size or 0) <= max_file_size]
        if file_name_contains:
            term = file_name_contains.strip().lower()
            rows = [row for row in rows if term in (row.file_name or "").lower()]
        if file_path_contains:
            term = file_path_contains.strip().lower()
            rows = [row for row in rows if term in (row.file_path or "").lower()]

        reverse_order = sort_order == "desc"
        if sort_by == "created_at":
            rows.sort(
                key=lambda row: self._parse_datetime(row.created_at),
                reverse=reverse_order,
            )
        elif sort_by == "file_name":
            rows.sort(
                key=lambda row: (row.file_name or "").lower(), reverse=reverse_order
            )
        elif sort_by == "file_size":
            rows.sort(key=lambda row: row.file_size or 0, reverse=reverse_order)
        else:
            rows.sort(
                key=lambda row: self._parse_datetime(row.updated_at),
                reverse=reverse_order,
            )

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
        row = self._fetch_one(
            self.item_table, {"id": item_id}, f"Bucket item {item_id} not found"
        )
        return BucketItemRecord.model_validate(row)

    def createBucketItem(self, payload: BucketItemCreate) -> BucketItemRecord:
        record = BucketItemRecord(**payload.model_dump(mode="python"))
        data = self._db_payload(record.model_dump(mode="python"))
        result = buckets_db_manager.insert(self.item_table, data)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to create bucket item")
        self._sync_bucket_stats(record.bucket_id)
        return self.getBucketItem(data["id"])

    def uploadFile(
        self,
        bucket_id: str,
        file_name: str,
        file_format: str,
        content: bytes,
        created_by: str,
        source: str | None = None,
        summary: str | None = None,
        connected_workspace_ids: str | None = None,
    ) -> BucketItemRecord:
        """Save a file to src/store/bucket/ and register it as a bucket item."""
        self.getBucket(bucket_id)
        rel_path = bucket_store.save_file(bucket_id, file_format, file_name, content)
        payload = BucketItemCreate(
            bucket_id=bucket_id,
            file_name=file_name,
            file_path=rel_path,
            file_format=file_format,
            file_size=len(content),
            created_by=created_by,
            source=source,
            summary=summary,
            connected_workspace_ids=connected_workspace_ids,
        )
        return self.createBucketItem(payload)

    def uploadFiles(
        self,
        bucket_id: str,
        files: list[tuple[str, str, bytes]],
        created_by: str,
        source: str | None = None,
        summary: str | None = None,
        connected_workspace_ids: str | None = None,
    ) -> list[BucketItemRecord]:
        """
        Upload multiple files in one call.
        `files` is a list of (file_name, file_format, content) tuples.
        Returns a list of created BucketItemRecords.
        """
        self.getBucket(bucket_id)
        created: list[BucketItemRecord] = []
        for file_name, file_format, content in files:
            rel_path = bucket_store.save_file(
                bucket_id, file_format, file_name, content
            )
            payload = BucketItemCreate(
                bucket_id=bucket_id,
                file_name=file_name,
                file_path=rel_path,
                file_format=file_format,
                file_size=len(content),
                created_by=created_by,
                source=source,
                summary=summary,
                connected_workspace_ids=connected_workspace_ids,
            )
            record = BucketItemRecord(**payload.model_dump(mode="python"))
            data = self._db_payload(record.model_dump(mode="python"))
            result = buckets_db_manager.insert(self.item_table, data)
            if not result.get("success"):
                raise ValueError(
                    result.get("message") or f"Failed to insert {file_name}"
                )
            created.append(self.getBucketItem(data["id"]))
        # Sync stats once after all inserts
        self._sync_bucket_stats(bucket_id)
        return created

    def updateBucketItem(
        self, item_id: str, payload: BucketItemCreate
    ) -> BucketItemRecord:
        self.getBucketItem(item_id)
        record = BucketItemRecord(id=item_id, **payload.model_dump(mode="python"))
        data = self._db_payload(record.model_dump(mode="python"))
        data["updated_at"] = self._utcnow_iso()
        result = buckets_db_manager.update(
            self.item_table, data=data, where={"id": item_id}
        )
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to update bucket item")
        return self.getBucketItem(item_id)

    def patchBucketItem(
        self, item_id: str, payload: BucketItemPatch
    ) -> BucketItemRecord:
        self.getBucketItem(item_id)
        patch_data = self._db_payload(
            payload.model_dump(exclude_unset=True, mode="python")
        )
        if not patch_data:
            return self.getBucketItem(item_id)
        patch_data["updated_at"] = self._utcnow_iso()
        result = buckets_db_manager.update(
            self.item_table, data=patch_data, where={"id": item_id}
        )
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to patch bucket item")
        return self.getBucketItem(item_id)

    def deleteBucketItem(self, item_id: str) -> None:
        item = self.getBucketItem(item_id)
        result = buckets_db_manager.delete(self.item_table, where={"id": item_id})
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to delete bucket item")
        # Remove the physical file (silently ignored if the path is a URL or already gone)
        bucket_store.delete_file(item.file_path)
        self._sync_bucket_stats(item.bucket_id)
