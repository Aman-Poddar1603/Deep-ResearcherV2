"""
chat_service.py — DB read/write helpers for the RAG chat layer.

All writes are fire-and-forget via scheduler.
Reads are synchronous (called before streaming begins).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

from main.src.history.history_tracker import (
    compact_preview,
    record_history_event,
    resolve_message_thread_id,
    resolve_thread_context,
)
from main.src.store.DBManager import chats_db_manager, main_db_manager
from main.src.utils.core.task_schedular import scheduler
from main.src.utils.DRLogger import quickLog


async def _log(msg: str, level: str = "info", urgency: str = "none") -> None:
    await scheduler.schedule(
        quickLog, params={"message": msg, "level": level, "urgency": urgency}
    )


_MSG_TABLE = "chat_messages"
_THREAD_TABLE = "chat_threads"
_ATT_TABLE = "chat_attachments"
_WORKSPACE_TABLE = "workspaces"
_SETTINGS_TABLE = "settings"

_DEFAULT_USER_LOCATION = os.getenv("DEFAULT_USER_LOCATION", "Ranchi, Jharkhand, India")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid4())


def _first_non_empty(*values: object) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _derive_location_from_settings(settings_row: dict[str, object] | None) -> str:
    row = settings_row or {}
    return _first_non_empty(
        row.get("user_location"),
        row.get("location"),
        _DEFAULT_USER_LOCATION,
    )


def get_thread_runtime_context(thread_id: str) -> dict[str, str]:
    """
    Resolve runtime context for a chat thread used by websocket processing.

    Includes workspace linkage, connected bucket, and user profile fields from
    settings so they can be injected into model context and attachment flows.
    """
    thread_result = chats_db_manager.fetch_one(
        _THREAD_TABLE, where={"thread_id": thread_id}
    )
    thread_row = thread_result.get("data") if thread_result.get("success") else None
    thread = thread_row or {}

    workspace_id = _first_non_empty(thread.get("workspace_id"))
    workspace_name = ""
    connected_bucket_id = ""
    if workspace_id:
        workspace_result = main_db_manager.fetch_one(
            _WORKSPACE_TABLE,
            where={"id": workspace_id},
        )
        workspace_row = (
            workspace_result.get("data") if workspace_result.get("success") else None
        )
        if isinstance(workspace_row, dict):
            workspace_name = _first_non_empty(workspace_row.get("name"))
            connected_bucket_id = _first_non_empty(
                workspace_row.get("connected_bucket_id")
            )

    settings_row: dict[str, object] | None = None
    settings_result = main_db_manager.fetch_all(_SETTINGS_TABLE)
    if settings_result.get("success"):
        rows = settings_result.get("data") or []
        if rows and isinstance(rows[0], dict):
            settings_row = rows[0]

    settings_user_name = _first_non_empty((settings_row or {}).get("user_name"))
    user_name = _first_non_empty(
        settings_user_name,
        thread.get("user_id"),
        thread.get("created_by"),
        "User",
    )

    return {
        "workspace_id": workspace_id,
        "workspace_name": workspace_name,
        "connected_bucket_id": connected_bucket_id,
        "user_name": user_name,
        "user_location": _derive_location_from_settings(settings_row),
        "created_by": _first_non_empty(
            thread.get("created_by"),
            thread.get("user_id"),
            settings_user_name,
            "chat-user",
        ),
    }


# ──────────────────────────────────────────── reads (sync, pre-stream) ────────


def get_recent_history(thread_id: str, limit: int = 10) -> list[dict]:
    """Return last `limit` messages for a thread, oldest-first."""
    result = chats_db_manager.fetch_all(_MSG_TABLE, where={"thread_id": thread_id})
    rows = result.get("data") or []
    rows.sort(key=lambda r: (r.get("message_seq") or 0, r.get("created_at") or ""))
    return rows[-limit:]


def get_next_seq(thread_id: str) -> int:
    result = chats_db_manager.fetch_all(_MSG_TABLE, where={"thread_id": thread_id})
    rows = result.get("data") or []
    if not rows:
        return 1
    return max(r.get("message_seq") or 0 for r in rows) + 1


def save_user_message_now(
    thread_id: str,
    content: str,
    seq: int,
    attachment_ids: list[str] | None = None,
    attachment_payload: list[dict] | None = None,
    message_id: str | None = None,
) -> str:
    message_id = message_id or new_id()
    attachments_value = (
        json.dumps(attachment_payload)
        if attachment_payload is not None
        else json.dumps(attachment_ids or [])
    )
    payload = {
        "message_id": message_id,
        "thread_id": thread_id,
        "message_seq": seq,
        "role": "user",
        "content": content,
        "attachments": attachments_value,
        "token_count": len(content.split()),
        "created_at": _now(),
    }
    result = chats_db_manager.insert(_MSG_TABLE, payload)
    if not result.get("success"):
        raise ValueError(result.get("message") or "Failed to insert user message")

    workspace_id, user_id = resolve_thread_context(thread_id)
    preview = compact_preview(content, max_chars=90) or "(empty)"
    record_history_event(
        activity=f"Chat user: {preview}",
        item_type="chat",
        workspace_id=workspace_id,
        user_id=user_id,
        actions="create_message",
        url=f"/chats/threads/{thread_id}",
    )
    return message_id


def save_attachment_now(
    message_id: str,
    attachment_type: str,
    attachment_path: str,
    attachment_size: int,
    attachment_id: str | None = None,
) -> str:
    attachment_id = attachment_id or new_id()
    payload = {
        "attachment_id": attachment_id,
        "message_id": message_id,
        "attachment_type": attachment_type,
        "attachment_path": attachment_path,
        "attachment_size": attachment_size,
        "created_at": _now(),
    }
    result = chats_db_manager.insert(_ATT_TABLE, payload)
    if not result.get("success"):
        raise ValueError(result.get("message") or "Failed to insert attachment")

    thread_id = resolve_message_thread_id(message_id)
    workspace_id, user_id = resolve_thread_context(thread_id or "")
    record_history_event(
        activity=f"Attached file to chat: {attachment_path}",
        item_type="upload",
        workspace_id=workspace_id,
        user_id=user_id,
        actions="create_attachment",
        url=f"/chats/threads/{thread_id}" if thread_id else None,
    )
    return attachment_id


# ──────────────────────────────────────────── background writes ────────────────


async def bg_save_user_message(
    thread_id: str,
    content: str,
    seq: int,
    attachment_ids: list[str] | None = None,
    attachment_payload: list[dict] | None = None,
    message_id: str | None = None,
) -> str:
    message_id = message_id or new_id()
    attachments_value = (
        json.dumps(attachment_payload)
        if attachment_payload is not None
        else json.dumps(attachment_ids or [])
    )
    payload = {
        "message_id": message_id,
        "thread_id": thread_id,
        "message_seq": seq,
        "role": "user",
        "content": content,
        "attachments": attachments_value,
        "token_count": len(content.split()),
        "created_at": _now(),
    }
    await scheduler.schedule(
        chats_db_manager.insert,
        params={"table_name": _MSG_TABLE, "data": payload},
    )

    workspace_id, user_id = resolve_thread_context(thread_id)
    preview = compact_preview(content, max_chars=90) or "(empty)"
    record_history_event(
        activity=f"Chat user: {preview}",
        item_type="chat",
        workspace_id=workspace_id,
        user_id=user_id,
        actions="create_message",
        url=f"/chats/threads/{thread_id}",
    )
    return message_id


async def bg_save_assistant_message(
    thread_id: str,
    content: str,
    seq: int,
    citations: dict[str, str] | None = None,
) -> str:
    message_id = str(uuid4())
    payload = {
        "message_id": message_id,
        "thread_id": thread_id,
        "message_seq": seq,
        "role": "assistant",
        "content": content,
        "citations": json.dumps(citations or {}, ensure_ascii=True),
        "token_count": len(content.split()),
        "created_at": _now(),
    }
    await scheduler.schedule(
        chats_db_manager.insert,
        params={"table_name": _MSG_TABLE, "data": payload},
    )

    workspace_id, user_id = resolve_thread_context(thread_id)
    preview = compact_preview(content, max_chars=90) or "(empty)"
    record_history_event(
        activity=f"Chat assistant: {preview}",
        item_type="chat",
        workspace_id=workspace_id,
        user_id=user_id,
        actions="assistant_message",
        url=f"/chats/threads/{thread_id}",
    )
    return message_id


async def bg_save_attachment(
    message_id: str,
    attachment_type: str,
    attachment_path: str,
    attachment_size: int,
    attachment_id: str | None = None,
) -> str:
    attachment_id = attachment_id or new_id()
    payload = {
        "attachment_id": attachment_id,
        "message_id": message_id,
        "attachment_type": attachment_type,
        "attachment_path": attachment_path,
        "attachment_size": attachment_size,
        "created_at": _now(),
    }
    await scheduler.schedule(
        chats_db_manager.insert,
        params={"table_name": _ATT_TABLE, "data": payload},
    )

    thread_id = resolve_message_thread_id(message_id)
    workspace_id, user_id = resolve_thread_context(thread_id or "")
    record_history_event(
        activity=f"Attached file to chat: {attachment_path}",
        item_type="upload",
        workspace_id=workspace_id,
        user_id=user_id,
        actions="create_attachment",
        url=f"/chats/threads/{thread_id}" if thread_id else None,
    )
    return attachment_id


async def bg_update_message_attachments(
    message_id: str,
    attachment_ids: list[str],
) -> None:
    await scheduler.schedule(
        chats_db_manager.update,
        params={
            "table_name": _MSG_TABLE,
            "data": {
                "attachments": json.dumps(attachment_ids),
                "updated_at": _now(),
            },
            "where": {"message_id": message_id},
        },
    )


async def bg_update_thread_title(thread_id: str, title: str) -> None:
    await scheduler.schedule(
        chats_db_manager.update,
        params={
            "table_name": _THREAD_TABLE,
            "data": {"thread_title": title, "updated_at": _now()},
            "where": {"thread_id": thread_id},
        },
    )
    workspace_id, user_id = resolve_thread_context(thread_id)
    record_history_event(
        activity=f"Updated chat title: {compact_preview(title, max_chars=70)}",
        item_type="chat",
        workspace_id=workspace_id,
        user_id=user_id,
        actions="update_thread_title",
        url=f"/chats/threads/{thread_id}",
    )


async def bg_touch_thread(thread_id: str) -> None:
    await scheduler.schedule(
        chats_db_manager.update,
        params={
            "table_name": _THREAD_TABLE,
            "data": {"updated_at": _now()},
            "where": {"thread_id": thread_id},
        },
    )
