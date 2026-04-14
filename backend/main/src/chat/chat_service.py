"""
chat_service.py — DB read/write helpers for the RAG chat layer.

All writes are fire-and-forget via scheduler.
Reads are synchronous (called before streaming begins).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from main.src.store.DBManager import chats_db_manager
from main.src.utils.core.task_schedular import scheduler
from main.src.utils.DRLogger import quickLog


async def _log(msg: str, level: str = "info", urgency: str = "none") -> None:
    await scheduler.schedule(quickLog, params={"message": msg, "level": level, "urgency": urgency})

_MSG_TABLE = "chat_messages"
_THREAD_TABLE = "chat_threads"
_ATT_TABLE = "chat_attachments"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid4())


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
    return message_id


async def bg_save_assistant_message(
    thread_id: str,
    content: str,
    seq: int,
    citations: list[str] | None = None,
) -> str:
    message_id = str(uuid4())
    payload = {
        "message_id": message_id,
        "thread_id": thread_id,
        "message_seq": seq,
        "role": "assistant",
        "content": content,
        "citations": json.dumps(citations or []),
        "token_count": len(content.split()),
        "created_at": _now(),
    }
    await scheduler.schedule(
        chats_db_manager.insert,
        params={"table_name": _MSG_TABLE, "data": payload},
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


async def bg_touch_thread(thread_id: str) -> None:
    await scheduler.schedule(
        chats_db_manager.update,
        params={
            "table_name": _THREAD_TABLE,
            "data": {"updated_at": _now()},
            "where": {"thread_id": thread_id},
        },
    )
