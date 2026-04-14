import math
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from main.apis.models.chats import (
    ChatAttachmentCreate,
    ChatAttachmentListResponse,
    ChatAttachmentPatch,
    ChatAttachmentRecord,
    ChatMessageCreate,
    ChatMessageListResponse,
    ChatMessagePatch,
    ChatMessageRecord,
    ChatThreadCreate,
    ChatThreadListResponse,
    ChatThreadPatch,
    ChatThreadRecord,
)
from main.src.bucket.bucket_store import bucket_store
from main.src.store.DBManager import chats_db_manager
from main.src.utils.DRLogger import quickLog


class ChatOrchestrator:
    def __init__(self):
        self.thread_table = "chat_threads"
        self.message_table = "chat_messages"
        self.attachment_table = "chat_attachments"

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

    def _normalize_timestamps(self, row: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(row)
        created_at = normalized.get("created_at")
        updated_at = normalized.get("updated_at")
        if created_at is None and updated_at is None:
            created_at = self._utcnow_iso()
        if created_at is None:
            created_at = updated_at
        if updated_at is None:
            updated_at = created_at
        normalized["created_at"] = created_at
        normalized["updated_at"] = updated_at
        return normalized

    def _attachment_url(self, attachment_path: str | None) -> str | None:
        if not attachment_path:
            return None
        if attachment_path.startswith("http://") or attachment_path.startswith("https://"):
            return attachment_path
        return bucket_store.build_asset_url(attachment_path)

    def _attachment_item(self, row: dict[str, Any]) -> dict[str, Any]:
        path = row.get("attachment_path")
        file_name = Path(path).name if isinstance(path, str) and path else None
        return {
            "attachment_id": row.get("attachment_id"),
            "message_id": row.get("message_id"),
            "attachment_type": row.get("attachment_type"),
            "attachment_path": path,
            "attachment_size": row.get("attachment_size"),
            "file_name": file_name,
            "url": self._attachment_url(path),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }

    def _attachment_item_from_payload(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        attachment_id = payload.get("attachment_id") or payload.get("id")
        message_id = payload.get("message_id")
        attachment_type = payload.get("attachment_type") or payload.get("type")
        attachment_path = payload.get("attachment_path") or payload.get("path")
        attachment_size = payload.get("attachment_size") or payload.get("size")
        file_name = payload.get("file_name") or payload.get("filename")
        direct_url = payload.get("url")

        if not file_name and isinstance(attachment_path, str) and attachment_path:
            file_name = Path(attachment_path).name

        # Skip malformed attachment payload entries that have no usable locator.
        if not attachment_id and not attachment_path and not direct_url:
            return None

        return {
            "attachment_id": attachment_id,
            "message_id": message_id,
            "attachment_type": attachment_type,
            "attachment_path": attachment_path,
            "attachment_size": attachment_size,
            "file_name": file_name,
            "url": direct_url or self._attachment_url(attachment_path),
            "created_at": payload.get("created_at"),
            "updated_at": payload.get("updated_at"),
        }

    def _parse_attachments_payload(
        self,
        value: Any,
    ) -> tuple[list[str], list[dict[str, Any]]]:
        if value is None:
            return [], []

        payload: Any = value
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return [], []
            try:
                payload = json.loads(raw)
            except Exception:
                # Legacy storage fallback: either one ID or a comma-separated ID list.
                ids = [part.strip() for part in raw.split(",") if part.strip()]
                return ids, []

        candidate_items: list[Any]
        if isinstance(payload, list):
            candidate_items = payload
        elif isinstance(payload, dict):
            candidate_items = [payload]
        else:
            return [], []

        ids: list[str] = []
        inline_items: list[dict[str, Any]] = []
        for item in candidate_items:
            if isinstance(item, str):
                item_id = item.strip()
                if item_id:
                    ids.append(item_id)
                continue
            if not isinstance(item, dict):
                continue

            item_id = item.get("attachment_id") or item.get("id")
            if isinstance(item_id, str) and item_id.strip():
                ids.append(item_id.strip())

            inline_item = self._attachment_item_from_payload(item)
            if inline_item:
                inline_items.append(inline_item)

        # Preserve order while removing duplicate IDs.
        seen: set[str] = set()
        deduped_ids: list[str] = []
        for item_id in ids:
            if item_id in seen:
                continue
            seen.add(item_id)
            deduped_ids.append(item_id)

        return deduped_ids, inline_items

    def _append_unique_attachment_item(
        self,
        items: list[dict[str, Any]],
        item: dict[str, Any],
        seen_ids: set[str],
        seen_paths: set[str],
    ) -> None:
        attachment_id = item.get("attachment_id")
        key_path = item.get("attachment_path") or item.get("url")

        if isinstance(attachment_id, str) and attachment_id:
            if attachment_id in seen_ids:
                return
            seen_ids.add(attachment_id)

        if isinstance(key_path, str) and key_path:
            if key_path in seen_paths:
                return
            seen_paths.add(key_path)

        items.append(item)

    def _hydrate_message_row(
        self,
        row: dict[str, Any],
        attachment_rows: list[dict[str, Any]],
        attachment_rows_by_id: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        normalized = self._normalize_timestamps(row)
        items: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        seen_paths: set[str] = set()

        for attachment_row in attachment_rows:
            self._append_unique_attachment_item(
                items,
                self._attachment_item(attachment_row),
                seen_ids,
                seen_paths,
            )

        stored_attachment_ids, inline_attachment_items = self._parse_attachments_payload(
            normalized.get("attachments")
        )

        if attachment_rows_by_id:
            for attachment_id in stored_attachment_ids:
                matched_row = attachment_rows_by_id.get(attachment_id)
                if not matched_row:
                    continue
                self._append_unique_attachment_item(
                    items,
                    self._attachment_item(matched_row),
                    seen_ids,
                    seen_paths,
                )

        for inline_attachment in inline_attachment_items:
            self._append_unique_attachment_item(
                items,
                inline_attachment,
                seen_ids,
                seen_paths,
            )

        if items:
            normalized["attachments"] = json.dumps(
                [
                    item.get("attachment_id")
                    for item in items
                    if isinstance(item.get("attachment_id"), str) and item.get("attachment_id")
                ],
                ensure_ascii=True,
            )
        normalized["attachment_items"] = items
        return normalized

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
        result = chats_db_manager.fetch_one(table_name, where=where)
        if not result.get("success"):
            raise ValueError(result.get("message") or f"Failed to fetch {table_name}")

        row = result.get("data")
        if row is None:
            raise KeyError(not_found)
        return row

    def listThreads(
        self,
        page: int = 1,
        size: int = 20,
        workspace_id: str | None = None,
        user_id: str | None = None,
        created_by: str | None = None,
        is_pinned: bool | None = None,
        thread_title_contains: str | None = None,
        sort_by: Literal[
            "updated_at", "created_at", "thread_title", "pinned_order"
        ] = "updated_at",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> ChatThreadListResponse:
        quickLog("Fetching chat threads", level="info", module="API")
        where: dict[str, Any] = {}
        if workspace_id is not None:
            where["workspace_id"] = workspace_id
        if user_id is not None:
            where["user_id"] = user_id
        if created_by is not None:
            where["created_by"] = created_by
        if is_pinned is not None:
            where["is_pinned"] = is_pinned

        result = chats_db_manager.fetch_all(self.thread_table, where=where)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to list chat threads")

        rows = [
            ChatThreadRecord.model_validate(self._normalize_timestamps(item))
            for item in (result.get("data") or [])
        ]

        if thread_title_contains:
            term = thread_title_contains.strip().lower()
            rows = [row for row in rows if term in (row.thread_title or "").lower()]

        reverse_order = sort_order == "desc"
        if sort_by == "created_at":
            rows.sort(
                key=lambda row: self._parse_datetime(row.created_at),
                reverse=reverse_order,
            )
        elif sort_by == "thread_title":
            rows.sort(
                key=lambda row: (row.thread_title or "").lower(), reverse=reverse_order
            )
        elif sort_by == "pinned_order":
            rows.sort(
                key=lambda row: (row.pinned_order is None, row.pinned_order or 0),
                reverse=reverse_order,
            )
        else:
            rows.sort(
                key=lambda row: self._parse_datetime(row.updated_at or row.created_at),
                reverse=reverse_order,
            )

        page_items, total_items, total_pages, offset = self._paginate(rows, page, size)
        return ChatThreadListResponse(
            items=page_items,
            page=page,
            size=size,
            total_items=total_items,
            total_pages=total_pages,
            offset=offset,
        )

    def getThread(self, thread_id: str) -> ChatThreadRecord:
        row = self._fetch_one(
            self.thread_table,
            {"thread_id": thread_id},
            f"Chat thread {thread_id} not found",
        )
        return ChatThreadRecord.model_validate(self._normalize_timestamps(row))

    def createThread(self, payload: ChatThreadCreate) -> ChatThreadRecord:
        workspace_id = (payload.workspace_id or "").strip()
        if not workspace_id:
            raise ValueError("workspace_id is required to start a chat thread")

        data = self._db_payload(payload.model_dump(mode="python"))
        data["workspace_id"] = workspace_id
        result = chats_db_manager.insert(self.thread_table, data)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to create chat thread")
        return self.getThread(data["thread_id"])

    def updateThread(
        self, thread_id: str, payload: ChatThreadCreate
    ) -> ChatThreadRecord:
        self.getThread(thread_id)
        data = self._db_payload(payload.model_dump(mode="python"))
        data["thread_id"] = thread_id
        data["updated_at"] = self._utcnow_iso()
        result = chats_db_manager.update(
            self.thread_table,
            data=data,
            where={"thread_id": thread_id},
        )
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to update chat thread")
        return self.getThread(thread_id)

    def patchThread(self, thread_id: str, payload: ChatThreadPatch) -> ChatThreadRecord:
        quickLog(f"Patching chat thread {thread_id}", level="info", module="API")
        self.getThread(thread_id)
        patch_data = self._db_payload(
            payload.model_dump(exclude_unset=True, mode="python")
        )
        if not patch_data:
            return self.getThread(thread_id)
        patch_data["updated_at"] = self._utcnow_iso()
        result = chats_db_manager.update(
            self.thread_table,
            data=patch_data,
            where={"thread_id": thread_id},
        )
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to patch chat thread")
        return self.getThread(thread_id)

    def deleteThread(self, thread_id: str) -> None:
        quickLog(
            f"Deleting chat thread {thread_id}",
            level="warning",
            urgency="moderate",
            module="API",
        )
        self.getThread(thread_id)
        result = chats_db_manager.delete(
            self.thread_table, where={"thread_id": thread_id}
        )
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to delete chat thread")

    def listMessages(
        self,
        page: int = 1,
        size: int = 20,
        thread_id: str | None = None,
        role: str | None = None,
        parent_id: str | None = None,
        content_contains: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        sort_by: Literal["message_seq", "created_at", "updated_at"] = "message_seq",
        sort_order: Literal["asc", "desc"] = "asc",
    ) -> ChatMessageListResponse:
        quickLog("Fetching chat messages", level="info", module="API")
        where: dict[str, Any] = {}
        if thread_id is not None:
            where["thread_id"] = thread_id
        if role is not None:
            where["role"] = role
        if parent_id is not None:
            where["parent_id"] = parent_id

        result = chats_db_manager.fetch_all(self.message_table, where=where)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to list chat messages")

        raw_rows = result.get("data") or []
        message_ids = {
            row.get("message_id")
            for row in raw_rows
            if row.get("message_id")
        }
        attachment_map: dict[str, list[dict[str, Any]]] = {}
        attachment_rows_by_id: dict[str, dict[str, Any]] = {}
        if message_ids:
            attachments_result = chats_db_manager.fetch_all(self.attachment_table)
            if attachments_result.get("success"):
                for attachment in attachments_result.get("data") or []:
                    attachment_id = attachment.get("attachment_id")
                    if attachment_id:
                        attachment_rows_by_id[attachment_id] = attachment
                    message_id_key = attachment.get("message_id")
                    if message_id_key in message_ids:
                        attachment_map.setdefault(message_id_key, []).append(attachment)

        rows = [
            ChatMessageRecord.model_validate(
                self._hydrate_message_row(
                    item,
                    attachment_map.get(item.get("message_id"), []),
                    attachment_rows_by_id,
                )
            )
            for item in raw_rows
        ]

        if content_contains:
            term = content_contains.strip().lower()
            rows = [row for row in rows if term in (row.content or "").lower()]
        if created_from is not None:
            rows = [
                row
                for row in rows
                if self._parse_datetime(row.created_at) >= created_from
            ]
        if created_to is not None:
            rows = [
                row
                for row in rows
                if self._parse_datetime(row.created_at) <= created_to
            ]

        reverse_order = sort_order == "desc"
        if sort_by == "created_at":
            rows.sort(
                key=lambda row: self._parse_datetime(row.created_at),
                reverse=reverse_order,
            )
        elif sort_by == "updated_at":
            rows.sort(
                key=lambda row: self._parse_datetime(row.updated_at or row.created_at),
                reverse=reverse_order,
            )
        else:
            rows.sort(
                key=lambda row: (
                    row.message_seq or 0,
                    self._parse_datetime(row.created_at),
                ),
                reverse=reverse_order,
            )

        page_items, total_items, total_pages, offset = self._paginate(rows, page, size)
        return ChatMessageListResponse(
            items=page_items,
            page=page,
            size=size,
            total_items=total_items,
            total_pages=total_pages,
            offset=offset,
        )

    def getMessage(self, message_id: str) -> ChatMessageRecord:
        row = self._fetch_one(
            self.message_table,
            {"message_id": message_id},
            f"Chat message {message_id} not found",
        )
        attachments_result = chats_db_manager.fetch_all(
            self.attachment_table,
            where={"message_id": message_id},
        )
        attachment_rows = (
            attachments_result.get("data") or []
            if attachments_result.get("success")
            else []
        )
        attachment_rows_by_id: dict[str, dict[str, Any]] = {}
        if attachment_rows:
            for attachment_row in attachment_rows:
                attachment_id = attachment_row.get("attachment_id")
                if attachment_id:
                    attachment_rows_by_id[attachment_id] = attachment_row
        else:
            all_attachments_result = chats_db_manager.fetch_all(self.attachment_table)
            if all_attachments_result.get("success"):
                for attachment_row in all_attachments_result.get("data") or []:
                    attachment_id = attachment_row.get("attachment_id")
                    if attachment_id:
                        attachment_rows_by_id[attachment_id] = attachment_row
        return ChatMessageRecord.model_validate(
            self._hydrate_message_row(row, attachment_rows, attachment_rows_by_id)
        )

    def createMessage(self, payload: ChatMessageCreate) -> ChatMessageRecord:
        data = self._db_payload(payload.model_dump(mode="python"))
        result = chats_db_manager.insert(self.message_table, data)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to create chat message")
        return self.getMessage(data["message_id"])

    def patchMessage(
        self, message_id: str, payload: ChatMessagePatch
    ) -> ChatMessageRecord:
        self.getMessage(message_id)
        patch_data = self._db_payload(
            payload.model_dump(exclude_unset=True, mode="python")
        )
        if not patch_data:
            return self.getMessage(message_id)
        patch_data["updated_at"] = self._utcnow_iso()
        result = chats_db_manager.update(
            self.message_table,
            data=patch_data,
            where={"message_id": message_id},
        )
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to patch chat message")
        return self.getMessage(message_id)

    def deleteMessage(self, message_id: str) -> None:
        quickLog(
            f"Deleting chat message {message_id}",
            level="warning",
            urgency="moderate",
            module="API",
        )
        self.getMessage(message_id)
        result = chats_db_manager.delete(
            self.message_table, where={"message_id": message_id}
        )
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to delete chat message")

    def listAttachments(
        self,
        page: int = 1,
        size: int = 20,
        message_id: str | None = None,
        attachment_type: str | None = None,
        min_attachment_size: int | None = None,
        max_attachment_size: int | None = None,
        path_contains: str | None = None,
        sort_by: Literal["created_at", "updated_at", "attachment_size"] = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> ChatAttachmentListResponse:
        quickLog("Fetching chat attachments", level="info", module="API")
        where: dict[str, Any] = {}
        if message_id is not None:
            where["message_id"] = message_id
        if attachment_type is not None:
            where["attachment_type"] = attachment_type

        result = chats_db_manager.fetch_all(self.attachment_table, where=where)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to list chat attachments")
        rows = [
            ChatAttachmentRecord.model_validate(self._normalize_timestamps(item))
            for item in (result.get("data") or [])
        ]

        if min_attachment_size is not None:
            rows = [
                row for row in rows if (row.attachment_size or 0) >= min_attachment_size
            ]
        if max_attachment_size is not None:
            rows = [
                row for row in rows if (row.attachment_size or 0) <= max_attachment_size
            ]
        if path_contains:
            term = path_contains.strip().lower()
            rows = [row for row in rows if term in (row.attachment_path or "").lower()]

        reverse_order = sort_order == "desc"
        if sort_by == "updated_at":
            rows.sort(
                key=lambda row: self._parse_datetime(row.updated_at or row.created_at),
                reverse=reverse_order,
            )
        elif sort_by == "attachment_size":
            rows.sort(key=lambda row: row.attachment_size or 0, reverse=reverse_order)
        else:
            rows.sort(
                key=lambda row: self._parse_datetime(row.created_at),
                reverse=reverse_order,
            )

        page_items, total_items, total_pages, offset = self._paginate(rows, page, size)
        return ChatAttachmentListResponse(
            items=page_items,
            page=page,
            size=size,
            total_items=total_items,
            total_pages=total_pages,
            offset=offset,
        )

    def getAttachment(self, attachment_id: str) -> ChatAttachmentRecord:
        row = self._fetch_one(
            self.attachment_table,
            {"attachment_id": attachment_id},
            f"Chat attachment {attachment_id} not found",
        )
        return ChatAttachmentRecord.model_validate(self._normalize_timestamps(row))

    def createAttachment(self, payload: ChatAttachmentCreate) -> ChatAttachmentRecord:
        data = self._db_payload(payload.model_dump(mode="python"))
        result = chats_db_manager.insert(self.attachment_table, data)
        if not result.get("success"):
            raise ValueError(
                result.get("message") or "Failed to create chat attachment"
            )
        return self.getAttachment(data["attachment_id"])

    def patchAttachment(
        self, attachment_id: str, payload: ChatAttachmentPatch
    ) -> ChatAttachmentRecord:
        self.getAttachment(attachment_id)
        patch_data = self._db_payload(
            payload.model_dump(exclude_unset=True, mode="python")
        )
        if not patch_data:
            return self.getAttachment(attachment_id)
        patch_data["updated_at"] = self._utcnow_iso()
        result = chats_db_manager.update(
            self.attachment_table,
            data=patch_data,
            where={"attachment_id": attachment_id},
        )
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to patch chat attachment")
        return self.getAttachment(attachment_id)

    def deleteAttachment(self, attachment_id: str) -> None:
        quickLog(
            f"Deleting chat attachment {attachment_id}",
            level="warning",
            urgency="moderate",
            module="API",
        )
        self.getAttachment(attachment_id)
        result = chats_db_manager.delete(
            self.attachment_table,
            where={"attachment_id": attachment_id},
        )
        if not result.get("success"):
            raise ValueError(
                result.get("message") or "Failed to delete chat attachment"
            )
