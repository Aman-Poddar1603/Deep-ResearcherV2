"""
history_tracker.py — central user_usage_history recorder.

This module provides a single write path for history events across workspace,
chat, and bucket flows. It prefers scheduler-based async writes when the
scheduler is running and safely falls back to direct inserts otherwise.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from datetime import datetime, timezone
from typing import Any, Coroutine
from uuid import uuid4

from main.src.store.DBManager import chats_db_manager, history_db_manager
from main.src.utils.core.task_schedular import scheduler
from main.src.utils.DRLogger import quickLog

_HISTORY_TABLE = "user_usage_history"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_text(value: object, max_len: int = 1200) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _clean_optional(value: object) -> str | None:
    text = _clean_text(value, max_len=600)
    return text or None


async def _schedule_log(
    msg: str, level: str = "info", urgency: str = "none"
) -> None:
    """Schedule a logging call through the scheduler."""
    await scheduler.schedule(
        quickLog,
        params={"message": msg, "level": level, "urgency": urgency, "module": "DB"},
    )


def _schedule_log_from_sync(
    msg: str, level: str = "info", urgency: str = "none"
) -> None:
    """Schedule a logging call from sync context via thread-safe enqueue."""
    target_loop = getattr(scheduler, "loop", None)
    if target_loop is None or not target_loop.is_running():
        return

    try:
        future = asyncio.run_coroutine_threadsafe(
            _schedule_log(msg, level, urgency),
            target_loop,
        )
        future.add_done_callback(
            lambda f: f.result() if not f.cancelled() else None
        )
    except Exception:
        pass


def _on_async_task_done(task: asyncio.Task[Any]) -> None:
    try:
        task.result()
    except Exception as exc:
        _schedule_log_from_sync(
            f"History insert task failed: {exc}",
            level="error",
            urgency="critical",
        )


def _on_threadsafe_future_done(
    future: concurrent.futures.Future[Any],
) -> None:
    try:
        future.result()
    except Exception as exc:
        _schedule_log_from_sync(
            f"History threadsafe insert failed: {exc}",
            level="error",
            urgency="critical",
        )


def _schedule_coro(payload: dict[str, Any]) -> Coroutine[Any, Any, None]:
    return scheduler.schedule(
        history_db_manager.insert,
        params={"table_name": _HISTORY_TABLE, "data": payload},
    )


def _schedule_from_sync_context(payload: dict[str, Any]) -> bool:
    target_loop = getattr(scheduler, "loop", None)
    if not getattr(scheduler, "started", False):
        return False
    if target_loop is None or not target_loop.is_running():
        return False

    try:
        future = asyncio.run_coroutine_threadsafe(
            _schedule_coro(payload),
            target_loop,
        )
        future.add_done_callback(_on_threadsafe_future_done)
        return True
    except Exception as exc:
        _schedule_log_from_sync(
            f"Failed to enqueue sync history insert: {exc}",
            level="error",
            urgency="critical",
        )
        return False


def _schedule_insert(payload: dict[str, Any]) -> bool:
    """Queue insert on scheduler for both async and sync call paths."""
    if not getattr(scheduler, "started", False):
        return False

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return _schedule_from_sync_context(payload)

    if not loop.is_running():
        return _schedule_from_sync_context(payload)

    try:
        task = loop.create_task(_schedule_coro(payload))
        task.add_done_callback(_on_async_task_done)
        return True
    except Exception as exc:
        _schedule_log_from_sync(
            f"Failed to create async history insert task: {exc}",
            level="error",
            urgency="critical",
        )
        return _schedule_from_sync_context(payload)


def _direct_insert(payload: dict[str, Any]) -> None:
    result = history_db_manager.insert(_HISTORY_TABLE, payload)
    if result.get("success"):
        return

    _schedule_log_from_sync(
        f"Direct history insert failed: {result.get('message', 'Unknown error')}",
        level="error",
        urgency="critical",
    )


def record_history_event(
    *,
    activity: str,
    item_type: str = "usage",
    workspace_id: str | None = None,
    user_id: str | None = None,
    actions: str | None = None,
    url: str | None = None,
) -> None:
    """Persist one history row to user_usage_history."""
    activity_text = _clean_text(activity)
    if not activity_text:
        return

    now = _now_iso()
    payload: dict[str, Any] = {
        "id": str(uuid4()),
        "user_id": _clean_optional(user_id),
        "workspace_id": _clean_optional(workspace_id),
        "activity": activity_text,
        "type": _clean_optional(item_type) or "usage",
        "created_at": now,
        "last_seen": now,
        "actions": _clean_optional(actions),
        "url": _clean_optional(url),
    }

    if _schedule_insert(payload):
        return
    _direct_insert(payload)


def resolve_thread_context(thread_id: str) -> tuple[str | None, str | None]:
    """Return (workspace_id, user_id) for a chat thread."""
    if not str(thread_id or "").strip():
        return None, None

    result = chats_db_manager.fetch_one("chat_threads", where={"thread_id": thread_id})
    row = result.get("data") if result.get("success") else None
    if not isinstance(row, dict):
        return None, None

    workspace_id = str(row.get("workspace_id") or "").strip() or None
    user_id = str(row.get("user_id") or row.get("created_by") or "").strip() or None
    return workspace_id, user_id


def resolve_message_thread_id(message_id: str) -> str | None:
    """Resolve thread_id for chat message rows."""
    if not str(message_id or "").strip():
        return None

    result = chats_db_manager.fetch_one(
        "chat_messages",
        where={"message_id": message_id},
    )
    row = result.get("data") if result.get("success") else None
    if not isinstance(row, dict):
        return None

    return str(row.get("thread_id") or "").strip() or None


def compact_preview(text: str, max_chars: int = 80) -> str:
    """One-line preview text used for activity labels."""
    flat = " ".join(str(text or "").split())
    if len(flat) <= max_chars:
        return flat
    return flat[: max_chars - 3] + "..."
