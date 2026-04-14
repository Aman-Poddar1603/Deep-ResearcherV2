"""
websocket_handler.py — WebSocket endpoint for RAG + Agent chat.

Client contract (matches existing frontend useChatSimulator):
  server → client:
    {"type": "token",    "content": "<chunk>"}
    {"type": "thinking", "content": "<chunk>"}  # reserved, not yet used
    {"type": "title",    "content": "<title>"}
    {"type": "done"}
    {"type": "error",    "content": "<message>"}

  client → server:  plain JSON message payload (see _parse_client_message)
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from main.src.utils.core.task_schedular import scheduler
from main.src.utils.DRLogger import quickLog

from . import attachment_service, chat_service, rag_service, agent_service


async def _log(msg: str, level: str = "info", urgency: str = "none") -> None:
    await scheduler.schedule(
        quickLog, params={"message": msg, "level": level, "urgency": urgency}
    )


# Decide agent vs RAG based on env flag or per-request field
USE_AGENT_DEFAULT = os.getenv("USE_AGENT", "false").lower() == "true"
_IMAGE_FORMATS = {"png", "jpg", "jpeg", "webp", "gif", "bmp"}


# ── helpers ───────────────────────────────────────────────────────────────────


def _parse_client_message(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except Exception:
        return {"content": raw}


async def _send(ws: WebSocket, payload: dict) -> None:
    try:
        await ws.send_json(payload)
    except Exception:
        pass  # client disconnected mid-stream


# ── main handler ──────────────────────────────────────────────────────────────


async def handle_chat_websocket(ws: WebSocket, thread_id: str) -> None:
    await ws.accept()
    asyncio.ensure_future(_log(f"WS connected thread={thread_id}", level="info"))

    try:
        while True:
            raw = await ws.receive_text()
            data = _parse_client_message(raw)
            await _process_turn(ws, thread_id, data)

    except WebSocketDisconnect:
        asyncio.ensure_future(_log(f"WS disconnected thread={thread_id}", level="info"))
    except Exception as exc:
        asyncio.ensure_future(
            _log(
                f"WS error thread={thread_id}: {exc}", level="error", urgency="critical"
            )
        )
        await _send(ws, {"type": "error", "content": str(exc)})


async def _process_turn(
    ws: WebSocket,
    thread_id: str,
    data: dict[str, Any],
) -> None:
    user_query: str = (data.get("content") or "").strip()
    raw_files: list[tuple[str, str, bytes]] = _decode_attachments(data)
    image_attachments = _extract_image_attachments(raw_files)
    use_agent: bool = bool(data.get("use_agent", USE_AGENT_DEFAULT))

    if not user_query and not raw_files:
        return

    # ── 1. Save user message (bg) ──────────────────────────────────────────
    seq = chat_service.get_next_seq(thread_id)
    user_msg_id = chat_service.new_id()
    attachment_ids: list[str] = []
    attachment_payload: list[dict[str, Any]] = []
    await chat_service.bg_touch_thread(thread_id)

    # ── 2. Process attachments ─────────────────────────────────────────────
    mcp_content = ""
    saved_meta: list[dict] = []
    if raw_files:
        saved_meta, mcp_content = await attachment_service.process_attachments(
            raw_files
        )
        for meta in saved_meta:
            attachment_id = chat_service.new_id()
            attachment_ids.append(attachment_id)
            attachment_payload.append(
                {
                    "attachment_id": attachment_id,
                    "message_id": user_msg_id,
                    "attachment_type": meta["file_format"],
                    "attachment_path": meta["rel_path"],
                    "attachment_size": meta["size"],
                    "file_name": meta.get("file_name", ""),
                    "url": meta.get("url", ""),
                }
            )

    # Persist user message synchronously so attachment rows can safely reference it.
    chat_service.save_user_message_now(
        thread_id,
        user_query,
        seq,
        attachment_ids=attachment_ids,
        attachment_payload=attachment_payload if attachment_payload else None,
        message_id=user_msg_id,
    )

    for attachment_meta in attachment_payload:
        try:
            chat_service.save_attachment_now(
                message_id=user_msg_id,
                attachment_type=str(attachment_meta.get("attachment_type") or ""),
                attachment_path=str(attachment_meta.get("attachment_path") or ""),
                attachment_size=int(attachment_meta.get("attachment_size") or 0),
                attachment_id=str(attachment_meta.get("attachment_id") or ""),
            )
        except Exception as exc:
            asyncio.ensure_future(
                _log(
                    f"Attachment persistence failed for message={user_msg_id}: {exc}",
                    level="warning",
                    urgency="moderate",
                )
            )

        await _send(
            ws,
            {
                "type": "attachment_status",
                "attachment_id": attachment_meta.get("attachment_id", ""),
                "file_name": attachment_meta.get("file_name", ""),
                "status": "completed",
                "tool": "",
                "url": attachment_meta.get("url", ""),
            },
        )

    # Preserve detailed tool analysis statuses from attachment processing.
    if saved_meta:
        for index, meta in enumerate(saved_meta):
            attachment_id = (
                attachment_payload[index].get("attachment_id", "")
                if index < len(attachment_payload)
                else ""
            )
            await _send(
                ws,
                {
                    "type": "attachment_status",
                    "attachment_id": attachment_id,
                    "file_name": meta.get("file_name", ""),
                    "status": meta.get("analysis_status", "unknown"),
                    "tool": meta.get("analysis_tool", ""),
                    "url": meta.get("url", ""),
                },
            )

    # ── 3. Retrieve RAG chunks ─────────────────────────────────────────────
    history = chat_service.get_recent_history(thread_id, limit=10)
    chunks = await rag_service.retrieve_chunks(user_query)

    # ── 4. Stream response ─────────────────────────────────────────────────
    full_response = ""

    if use_agent:
        context = rag_service.build_context(history, chunks, mcp_content)
        stream = agent_service.stream_agent_response(user_query, context)
    else:
        stream = rag_service.stream_rag_response(
            user_query,
            history,
            chunks,
            mcp_content,
            image_attachments=image_attachments,
        )

    async for token in stream:
        full_response += token
        await _send(ws, {"type": "token", "content": token})

    full_response_with_sources = rag_service.ensure_sources_section(full_response, chunks)
    if full_response_with_sources != full_response:
        appendix = full_response_with_sources[len(full_response) :]
        if appendix:
            await _send(ws, {"type": "token", "content": appendix})
        full_response = full_response_with_sources

    # ── 5. Save assistant message (bg) ─────────────────────────────────────
    await chat_service.bg_save_assistant_message(thread_id, full_response, seq + 1)

    # ── 6. Generate + broadcast thread title (before done so client receives it) ─
    await _maybe_generate_title(ws, thread_id, history, user_query, full_response)

    # ── 7. Finish stream ────────────────────────────────────────────────────
    await _send(ws, {"type": "done"})


async def _maybe_generate_title(
    ws: WebSocket,
    thread_id: str,
    history: list[dict],
    user_query: str,
    assistant_reply: str,
) -> None:
    """Generate title only for the first exchange (no prior history)."""
    if len(history) > 1:
        return
    try:
        snippet = f"User: {user_query}\nAssistant: {assistant_reply[:300]}"
        title = await rag_service.generate_thread_title(snippet)
        await _send(ws, {"type": "title", "content": title})
        await chat_service.bg_update_thread_title(thread_id, title)
    except Exception as exc:
        asyncio.ensure_future(
            _log(f"Title gen failed: {exc}", level="warning", urgency="none")
        )


# ── attachment decoding ───────────────────────────────────────────────────────


def _decode_attachments(data: dict) -> list[tuple[str, str, bytes]]:
    """
    Expect data["attachments"] = [
        {"file_name": "x.pdf", "file_format": "pdf", "data": "<base64>"}
    ]
    """
    raw: list[dict] = data.get("attachments") or []
    result: list[tuple[str, str, bytes]] = []
    for item in raw:
        try:
            name = item.get("file_name", "file")
            fmt = item.get("file_format", "other")
            b64 = item.get("data", "")
            if isinstance(b64, str) and b64.startswith("data:") and "," in b64:
                b64 = b64.split(",", 1)[1]
            content = base64.b64decode(b64)
            result.append((name, fmt, content))
        except Exception as exc:
            asyncio.ensure_future(
                _log(f"Attachment decode error: {exc}", level="warning", urgency="none")
            )
    return result


def _extract_image_attachments(
    raw_files: list[tuple[str, str, bytes]],
) -> list[dict[str, str]]:
    images: list[dict[str, str]] = []
    for file_name, file_format, content in raw_files:
        normalized_format = _normalize_file_format(file_format)
        if normalized_format not in _IMAGE_FORMATS:
            continue
        images.append(
            {
                "file_name": file_name,
                "file_format": normalized_format,
                "data": base64.b64encode(content).decode("ascii"),
            }
        )
    return images


def _normalize_file_format(file_format: str) -> str:
    fmt = (file_format or "").strip().lower().lstrip(".")
    if fmt.startswith("image/"):
        return fmt.split("/", 1)[1]
    return fmt
