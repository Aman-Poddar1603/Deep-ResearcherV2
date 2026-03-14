import math
from datetime import datetime, timezone
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
from main.src.store.DBManager import chats_db_manager


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
            ChatThreadRecord.model_validate(item) for item in (result.get("data") or [])
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
        return ChatThreadRecord.model_validate(row)

    def createThread(self, payload: ChatThreadCreate) -> ChatThreadRecord:
        data = self._db_payload(payload.model_dump(mode="python"))
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
        rows = [
            ChatMessageRecord.model_validate(item)
            for item in (result.get("data") or [])
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
        return ChatMessageRecord.model_validate(row)

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
        where: dict[str, Any] = {}
        if message_id is not None:
            where["message_id"] = message_id
        if attachment_type is not None:
            where["attachment_type"] = attachment_type

        result = chats_db_manager.fetch_all(self.attachment_table, where=where)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to list chat attachments")
        rows = [
            ChatAttachmentRecord.model_validate(item)
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
        return ChatAttachmentRecord.model_validate(row)

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
        self.getAttachment(attachment_id)
        result = chats_db_manager.delete(
            self.attachment_table,
            where={"attachment_id": attachment_id},
        )
        if not result.get("success"):
            raise ValueError(
                result.get("message") or "Failed to delete chat attachment"
            )
