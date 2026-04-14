"""
websocket_handler.py — WebSocket endpoint for RAG + Agent chat.

Client contract (matches existing frontend useChatSimulator):
  server → client:
    {"type": "token",    "content": "<chunk>"}
    {"type": "thinking", "content": "<status>"}
        {"type": "sources",  "sources": [{"href": "...", "title": "..."}], "count": N}
    {"type": "title",    "content": "<title>"}
    {"type": "done"}
    {"type": "error",    "content": "<message>"}

  client → server:  plain JSON message payload (see _parse_client_message)
"""

from __future__ import annotations

import asyncio
import base64
import html
import json
import os
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import WebSocket, WebSocketDisconnect

from main.src.research.layer2.tools import get_mcp_tools, parse_tool_output
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
_URL_PATTERN = re.compile(r"https?://[^\s<>()\[\]\{\}\"']+", flags=re.IGNORECASE)
_SCRIPT_STYLE_PATTERN = re.compile(
    r"<\s*(script|style)\b[^>]*>.*?<\s*/\s*\1\s*>",
    flags=re.IGNORECASE | re.DOTALL,
)
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_WEB_TOOL_PREFERENCES = ("read_webpages", "scrape_single_url", "web_search")
_MAX_WEB_SOURCE_ITEMS = 3
_MAX_WEB_SOURCE_CHARS = 4500


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


def _extract_urls(text: str) -> list[str]:
    found = _URL_PATTERN.findall(text or "")
    urls: list[str] = []
    seen: set[str] = set()
    for raw in found:
        candidate = raw.rstrip(".,;:!?)]}")
        if not candidate:
            continue
        parsed = urlsplit(candidate)
        if parsed.scheme.lower() not in {"http", "https"}:
            continue
        normalized = str(urlunsplit(parsed))
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        urls.append(normalized)
    return urls


def _normalize_tool_name(tool_name: str) -> str:
    name = (tool_name or "").strip().lower()
    if not name:
        return ""
    if "::" in name:
        name = name.split("::")[-1]
    if "/" in name:
        name = name.split("/")[-1]
    if "." in name:
        name = name.split(".")[-1]
    for prefix in ("research_tools_", "mcp_", "tool_"):
        if name.startswith(prefix):
            name = name[len(prefix) :]
    return name


def _select_web_tool(tools: list[Any]) -> Any | None:
    for preferred in _WEB_TOOL_PREFERENCES:
        for tool in tools:
            normalized = _normalize_tool_name(getattr(tool, "name", ""))
            if normalized == preferred:
                return tool
    return None


def _build_web_tool_payload(tool: Any, urls: list[str]) -> dict[str, Any]:
    args_schema = getattr(tool, "args_schema", None)
    fields = (
        list(getattr(args_schema, "model_fields", {}).keys()) if args_schema else []
    )
    lower_to_field = {field.lower(): field for field in fields}

    for list_key in ("urls", "links", "websites", "website_urls"):
        if list_key in lower_to_field:
            return {lower_to_field[list_key]: urls}

    for single_key in ("url", "link", "website"):
        if single_key in lower_to_field:
            return {lower_to_field[single_key]: urls[0]}

    if "query" in lower_to_field:
        return {lower_to_field["query"]: " ".join(urls)}

    if fields:
        first = fields[0]
        if first.lower().endswith("s"):
            return {first: urls}
        return {first: urls[0]}

    return {"urls": urls}


def _html_to_text(raw_html: str) -> str:
    if not raw_html:
        return ""
    no_script = _SCRIPT_STYLE_PATTERN.sub(" ", raw_html)
    no_tags = _HTML_TAG_PATTERN.sub(" ", no_script)
    unescaped = html.unescape(no_tags)
    return _WHITESPACE_PATTERN.sub(" ", unescaped).strip()


def _merge_sources(
    primary: list[dict[str, str]],
    secondary: list[dict[str, str]],
) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for item in [*primary, *secondary]:
        href = str(item.get("href") or "").strip()
        title = str(item.get("title") or href or "Source").strip()
        if not href and not title:
            continue
        key = (href.lower(), title.lower())
        if key in seen:
            continue
        seen.add(key)
        merged.append({"href": href, "title": title})

    return merged


async def _fetch_webpages_direct(
    urls: list[str],
) -> tuple[str, list[dict[str, str]], str]:
    snippets: list[str] = []
    sources: list[dict[str, str]] = []

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as client:
            for url in urls[:_MAX_WEB_SOURCE_ITEMS]:
                response = await client.get(
                    url,
                    headers={"User-Agent": "DeepResearcherChat/2.0"},
                )
                response.raise_for_status()

                body_text = _html_to_text(response.text)
                if not body_text:
                    continue

                content = body_text[:_MAX_WEB_SOURCE_CHARS]
                snippets.append(
                    "\n".join(
                        [
                            f"URL: {url}",
                            "Extracted content:",
                            content,
                        ]
                    )
                )
                sources.append({"href": url, "title": url})
    except Exception as exc:
        await _log(
            f"Direct webpage fetch failed: {exc}",
            level="warning",
            urgency="moderate",
        )
        return "", [], "failed"

    if not snippets:
        return "", [], "empty"

    context_text = "### Live Website Content\n" + "\n\n".join(snippets)
    return context_text, sources, "completed"


async def _fetch_live_website_context(
    query: str,
) -> tuple[str, list[dict[str, str]], str]:
    urls = _extract_urls(query)
    if not urls:
        return "", [], "none"

    try:
        tools = await get_mcp_tools()
        tool = _select_web_tool(tools)
        if tool is not None:
            payload = _build_web_tool_payload(tool, urls)
            output = await tool.ainvoke(payload)
            parsed = parse_tool_output(getattr(tool, "name", ""), output)

            snippets: list[str] = []
            sources: list[dict[str, str]] = []
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                url = str(item.get("url") or "").strip()
                content = str(item.get("content") or "").strip()
                title = str(item.get("title") or url or "Web Source").strip()
                if not content:
                    continue

                if url:
                    sources.append({"href": url, "title": title or url})

                snippets.append(
                    "\n".join(
                        [
                            f"Title: {title}",
                            f"URL: {url}" if url else "URL: not provided",
                            "Extracted content:",
                            content[:_MAX_WEB_SOURCE_CHARS],
                        ]
                    )
                )

                if len(snippets) >= _MAX_WEB_SOURCE_ITEMS:
                    break

            if snippets:
                context_text = "### Live Website Content\n" + "\n\n".join(snippets)
                normalized_sources = _merge_sources(sources, [])
                return context_text, normalized_sources, "mcp"
    except Exception as exc:
        await _log(
            f"MCP webpage fetch failed: {exc}",
            level="warning",
            urgency="moderate",
        )

    # Fallback keeps chat useful if MCP is unavailable or returns empty.
    return await _fetch_webpages_direct(urls)


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
    query_urls = _extract_urls(user_query)
    raw_files: list[tuple[str, str, bytes]] = _decode_attachments(data)
    image_attachments = _extract_image_attachments(raw_files)
    use_agent: bool = bool(data.get("use_agent", USE_AGENT_DEFAULT))

    if not user_query and not raw_files:
        return

    runtime_context = chat_service.get_thread_runtime_context(thread_id)
    workspace_id = str(runtime_context.get("workspace_id") or "").strip()
    connected_bucket_id = str(runtime_context.get("connected_bucket_id") or "").strip()
    created_by = str(runtime_context.get("created_by") or "chat-user").strip() or "chat-user"
    user_name = str(runtime_context.get("user_name") or "").strip()
    user_location = str(runtime_context.get("user_location") or "").strip()
    workspace_name = str(runtime_context.get("workspace_name") or "").strip()

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
        try:
            saved_meta, mcp_content = await attachment_service.process_attachments(
                raw_files,
                workspace_id=workspace_id,
                connected_bucket_id=connected_bucket_id,
                created_by=created_by,
            )
        except ValueError as exc:
            await _send(ws, {"type": "error", "content": str(exc)})
            return

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
    live_web_sources: list[dict[str, str]] = []

    if query_urls:
        await _send(
            ws,
            {
                "type": "thinking",
                "content": "Fetching live website content...",
            },
        )
        web_context, live_web_sources, web_status = await _fetch_live_website_context(
            user_query
        )
        if web_context.strip():
            mcp_content = "\n\n".join(
                part for part in [mcp_content, web_context] if part.strip()
            )
            await _send(
                ws,
                {
                    "type": "thinking",
                    "content": "Read website content. Preparing answer...",
                },
            )
        else:
            await _send(
                ws,
                {
                    "type": "thinking",
                    "content": (
                        "Could not fetch website content live. "
                        "Answering with available context."
                    ),
                },
            )
            await _log(
                f"Live website fetch returned no content (status={web_status})",
                level="warning",
                urgency="none",
            )

    chunks: list[dict[str, Any]] = []
    should_query_rag = rag_service.should_use_rag(user_query) and not query_urls
    if should_query_rag:
        await _send(
            ws,
            {
                "type": "thinking",
                "content": "Searching workspace knowledge base...",
            },
        )
        chunks = await rag_service.retrieve_chunks(user_query)

    # ── 4. Stream response ─────────────────────────────────────────────────
    full_response = ""

    if use_agent:
        context = rag_service.build_context(
            history,
            chunks,
            mcp_content,
            user_name=user_name,
            user_location=user_location,
            workspace_name=workspace_name,
        )
        stream = agent_service.stream_agent_response(user_query, context)
    else:
        stream = rag_service.stream_rag_response(
            user_query,
            history,
            chunks,
            mcp_content,
            image_attachments=image_attachments,
            user_name=user_name,
            user_location=user_location,
            workspace_name=workspace_name,
        )

    async for token in stream:
        full_response += token
        await _send(ws, {"type": "token", "content": token})

    rag_sources = rag_service.build_sources_payload(full_response, chunks)
    sources = _merge_sources(live_web_sources, rag_sources)

    citations = rag_service.build_citations_dict(full_response, chunks)
    for source in live_web_sources:
        href = str(source.get("href") or "").strip()
        if not href:
            continue
        title = str(source.get("title") or href).strip() or href
        if title not in citations:
            citations[title] = href

    if sources:
        await _send(
            ws,
            {
                "type": "sources",
                "sources": sources,
                "count": len(sources),
            },
        )

    # ── 5. Save assistant message (bg) ─────────────────────────────────────
    await chat_service.bg_save_assistant_message(
        thread_id,
        full_response,
        seq + 1,
        citations=citations,
    )

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
