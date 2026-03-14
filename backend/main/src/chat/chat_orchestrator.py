import math
from datetime import datetime, timezone
from typing import Any

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
        self, page: int = 1, size: int = 20, workspace_id: str | None = None
    ) -> ChatThreadListResponse:
        where = {"workspace_id": workspace_id} if workspace_id else None
        result = chats_db_manager.fetch_all(self.thread_table, where=where)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to list chat threads")

        rows = [
            ChatThreadRecord.model_validate(item) for item in (result.get("data") or [])
        ]
        rows.sort(key=lambda row: row.updated_at or row.created_at, reverse=True)
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
        self, page: int = 1, size: int = 20, thread_id: str | None = None
    ) -> ChatMessageListResponse:
        where = {"thread_id": thread_id} if thread_id else None
        result = chats_db_manager.fetch_all(self.message_table, where=where)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to list chat messages")
        rows = [
            ChatMessageRecord.model_validate(item)
            for item in (result.get("data") or [])
        ]
        rows.sort(key=lambda row: (row.message_seq or 0, row.created_at), reverse=False)
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
        self, page: int = 1, size: int = 20, message_id: str | None = None
    ) -> ChatAttachmentListResponse:
        where = {"message_id": message_id} if message_id else None
        result = chats_db_manager.fetch_all(self.attachment_table, where=where)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to list chat attachments")
        rows = [
            ChatAttachmentRecord.model_validate(item)
            for item in (result.get("data") or [])
        ]
        rows.sort(key=lambda row: row.created_at, reverse=True)
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
