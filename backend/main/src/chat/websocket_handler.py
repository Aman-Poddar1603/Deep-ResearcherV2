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


# Decide agent vs RAG based on env flag or per-request field.
# Defaults to True so MCP tools are always bound — set USE_AGENT=false to revert
# to the plain RAG-only path.
USE_AGENT_DEFAULT = os.getenv("USE_AGENT", "true").lower() != "false"
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
_MAX_SEARCH_RESULT_CHARS = 6000

# Keywords used to detect search intent directly from the user's query.
# The server calls the MCP tool directly — no LLM involvement in the decision.
_YOUTUBE_KEYWORDS: frozenset[str] = frozenset(
    {
        "youtube", "video", "videos", "watch", "channel", "vlog", "vlogs",
        "clip", "clips", "tutorial", "tutorials", "playlist", "stream",
    }
)
_IMAGE_SEARCH_KEYWORDS: frozenset[str] = frozenset(
    {
        "image", "images", "picture", "pictures", "photo", "photos",
        "pic", "pics", "wallpaper", "wallpapers", "artwork", "illustration",
    }
)
_WEB_SEARCH_KEYWORDS: frozenset[str] = frozenset(
    {
        "search", "find", "look up", "lookup", "google", "latest", "news",
        "article", "articles", "trending", "results", "information about",
        "tell me about", "what is", "who is", "where is", "when is",
    }
)
# Phrases that, when detected, bypass the agent and return a live tool listing.
_CAPABILITY_QUERY_PHRASES = (
    "who are you",
    "what are your abilities",
    "what are your capabilities",
    "what can you do",
    "what tools do you have",
    "what tools you have",
    "tools do you have",
    "tools you have",
    "what tools are available",
    "list your tools",
    "list tools",
    "show tools",
    "show your tools",
    "what do you do",
    "what can i ask you",
    "tell me about yourself",
)
# If the query contains ALL keywords in any of these tuples, treat it as a
# capability query regardless of phrasing order.
_CAPABILITY_KEYWORD_COMBOS: tuple[tuple[str, ...], ...] = (
    ("tool", "have"),
    ("tool", "use"),
    ("tool", "access"),
    ("tools", "available"),
    ("what", "tool"),
    ("which", "tool"),
)


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


def _normalize_query_text(query: str) -> str:
    return re.sub(r"\s+", " ", (query or "").strip().lower())


def _is_capability_query(query: str) -> bool:
    normalized = _normalize_query_text(query)
    if not normalized:
        return False

    if any(phrase in normalized for phrase in _CAPABILITY_QUERY_PHRASES):
        return True

    if "abilities" in normalized or "capabilities" in normalized:
        return True

    # Keyword-combo check: if the query contains ALL words in any combo tuple,
    # treat it as a capability query regardless of phrasing order.
    words = set(normalized.split())
    if any(all(kw in words for kw in combo) for combo in _CAPABILITY_KEYWORD_COMBOS):
        return True

    return False


def _summarize_mcp_tool(tool: Any) -> str:
    name = str(getattr(tool, "name", "")).strip() or "unknown"
    description = " ".join(str(getattr(tool, "description", "")).split())

    args_schema = getattr(tool, "args_schema", None)
    fields = list(getattr(args_schema, "model_fields", {}).keys()) if args_schema else []
    if fields:
        input_text = ", ".join(fields)
        if description:
            description = f"{description} Inputs: {input_text}."
        else:
            description = f"Inputs: {input_text}."

    if not description:
        description = "MCP tool."

    description = description.strip()
    if len(description) > 180:
        description = description[:177].rstrip() + "..."

    display_name = name.replace("_", " ")
    return f"- {display_name}: {description}"


async def _build_capability_response() -> str:
    tools = await get_mcp_tools()
    if not tools:
        return (
            "I’m a chat assistant connected to the app’s live MCP server, but I couldn’t "
            "load the tool list right now. I can still help with general questions, and "
            "I’ll use the MCP tools as soon as they are available."
        )

    lines = [
        "I’m a chat assistant connected to the app’s live MCP server.",
        "",
        "These are the tools I can use right now:",
    ]
    lines.extend(_summarize_mcp_tool(tool) for tool in tools)
    lines.append("")
    lines.append(
        "If you want, I can also use these tools to search, read documents, inspect images, or pull live web content for a question."
    )
    return "\n".join(lines)


async def _single_chunk_stream(text: str):
    if text:
        yield text


def _select_tool_by_names(
    tools: list[Any],
    candidates: list[str],
) -> Any | None:
    """Select the first matching tool from candidates (priority order)."""
    for candidate in candidates:
        for tool in tools:
            if _normalize_tool_name(getattr(tool, "name", "")) == candidate:
                return tool
    return None


def _build_query_payload(tool: Any, query: str) -> dict[str, Any]:
    """
    Map a plain search query string to the tool's actual argument schema.

    Handles the special case of ``image_search_tool`` which takes
    ``queries: list[tuple[str, int]]`` instead of a plain ``query: str``.
    """
    args_schema = getattr(tool, "args_schema", None)
    fields = (
        list(getattr(args_schema, "model_fields", {}).keys()) if args_schema else []
    )
    lower_to_field = {f.lower(): f for f in fields}

    # image_search_tool uses "queries" which is list[tuple[str, int]]
    if "queries" in lower_to_field:
        return {lower_to_field["queries"]: [[query, 10]]}

    for key in ("query", "q", "search", "term", "keywords"):
        if key in lower_to_field:
            return {lower_to_field[key]: query}
    if fields:
        return {fields[0]: query}
    return {"query": query}




def _detect_search_intent(query: str) -> tuple[str | None, str]:
    """
    Detect YouTube / image / web search intent from the user's plain-text
    query.  Returns (category, cleaned_search_query) where category is
    ``"youtube"``, ``"image"``, or ``None`` if no search intent found.
    """
    normalized = re.sub(r"\s+", " ", (query or "").strip().lower())
    words = set(normalized.split())

    # Strip common request prefixes to get a clean search query
    cleaned = re.sub(
        r"^(search(\s+for)?|find(\s+me)?|can\s+you\s+(search|find)|"
        r"show(\s+me)?|get(\s+me)?|fetch|look(\s+up)?)\s+",
        "",
        normalized,
    ).strip()

    if words & _YOUTUBE_KEYWORDS:
        core = re.sub(
            r"\b(youtube|video|videos|watch|vlog|vlogs|clip|clips|stream|playlist|tutorial|tutorials)\b",
            "",
            cleaned,
        ).strip(" ,-")
        return "youtube", core or cleaned

    if words & _IMAGE_SEARCH_KEYWORDS:
        core = re.sub(
            r"\b(image|images|picture|pictures|photo|photos|pic|pics|wallpaper|wallpapers|artwork|illustration)\b",
            "",
            cleaned,
        ).strip(" ,-")
        return "image", core or cleaned

    return None, cleaned


async def _fetch_search_context(
    query: str,
) -> tuple[str, list[dict[str, str]], str]:
    """
    Detect search intent, select the right MCP tool, call it DIRECTLY
    (server-side, no LLM involvement), and return formatted context.

    Follows the exact same pattern as ``attachment_service.extract_mcp_content``
    and ``_fetch_live_website_context`` — both of which bypass the LLM for
    tool selection and call ``tool.ainvoke()`` directly.

    Returns:
        (context_text, sources, status)
        status: ``"youtube"`` | ``"image"`` | ``"none"`` | ``"failed"``
    """
    tool_category, search_query = _detect_search_intent(query)
    if not tool_category:
        return "", [], "none"

    if not search_query.strip():
        search_query = query

    try:
        tools = await get_mcp_tools()
        if not tools:
            return "", [], "failed"

        if tool_category == "youtube":
            tool = _select_tool_by_names(tools, ["youtube_search", "youtube"])
        else:
            tool = _select_tool_by_names(
                tools, ["image_search_tool", "image_search"]
            )

        if tool is None:
            await _log(
                f"No MCP tool found for search category '{tool_category}'",
                level="warning",
                urgency="none",
            )
            return "", [], "failed"

        payload = _build_query_payload(tool, search_query)
        tool_name = getattr(tool, "name", tool_category)

        raw_output = await tool.ainvoke(payload)
        parsed = parse_tool_output(tool_name, raw_output)

        if not parsed:
            return "", [], "failed"

        sources: list[dict[str, str]] = []
        context_text = ""

        if tool_category == "youtube":
            context_text = _format_youtube_results(search_query, parsed, sources)
        else:
            context_text = _format_image_results(search_query, parsed, sources)

        if not context_text.strip():
            return "", [], "failed"

        if len(context_text) > _MAX_SEARCH_RESULT_CHARS:
            context_text = (
                context_text[:_MAX_SEARCH_RESULT_CHARS] + "\n\n[...truncated]"
            )

        return context_text, sources, tool_category

    except Exception as exc:
        await _log(
            f"_fetch_search_context failed ({tool_category}): {exc}",
            level="warning",
            urgency="moderate",
        )
        return "", [], "failed"


def _format_youtube_results(
    query: str,
    parsed: list[dict[str, Any]],
    sources: list[dict[str, str]],
) -> str:
    """
    Format youtube_search parsed output as a numbered markdown list with
    bold clickable titles, channel, duration, views, and a short description.
    """
    lines: list[str] = [
        f'> **YouTube Search Results for \u201c{query}\u201d** \u2014 '
        f'include these links and details in your answer.\n',
    ]
    for i, item in enumerate(parsed[:8], start=1):
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        title = str(item.get("title") or "Video").strip()
        content = str(item.get("content") or "").strip()
        if not url:
            continue

        # Parse the pre-formatted content block from parse_tool_output:
        # "Title: X\nChannel: Y\nDescription: Z\nViews: N\nDuration: Ds\n..."
        meta: dict[str, str] = {}
        for line in content.splitlines():
            if ": " in line:
                k, _, v = line.partition(": ")
                meta[k.strip().lower()] = v.strip()

        channel = meta.get("channel", "")
        duration_s = meta.get("duration", "")
        views = meta.get("views", "")
        desc = meta.get("description", "")[:200]

        # Build duration string e.g. "12m 34s"
        dur_str = ""
        try:
            secs = int(float(duration_s))
            dur_str = f"{secs // 60}m {secs % 60}s" if secs else ""
        except (ValueError, TypeError):
            dur_str = duration_s

        meta_parts = [p for p in [channel, dur_str, views] if p]
        meta_line = " \u2022 ".join(meta_parts)

        if url:
            sources.append({"href": url, "title": title})

        lines.append(f"{i}. **{title}**")
        lines.append(f"   URL: {url}")
        if meta_line:
            lines.append(f"   {meta_line}")
        if desc:
            lines.append(f"   > {desc}")
        lines.append("")

    return "\n".join(lines)


def _format_image_results(
    query: str,
    parsed: list[dict[str, Any]],
    sources: list[dict[str, str]],
) -> str:
    """
    Format image_search_tool parsed output as a markdown inline image gallery.
    Images are rendered using ``![alt](url)`` syntax so the frontend displays
    them directly rather than showing raw URLs.  Multiple images appear on the
    same line as a horizontal row.
    """
    image_tags: list[str] = []
    for item in parsed[:12]:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        # Only include likely image URLs (not HTML pages)
        if not url:
            continue
        ext = url.split("?")[0].rsplit(".", 1)[-1].lower()
        if ext not in {"jpg", "jpeg", "png", "webp", "gif", "bmp", "svg"}:
            # Heuristic: include anyway if the URL path looks like an image
            if not any(k in url.lower() for k in ("image", "photo", "img", "pic")):
                continue
        alt = query.replace('"', "")
        image_tags.append(f"![{alt}]({url})")
        sources.append({"href": url, "title": alt})

    if not image_tags:
        return ""

    # Group into rows of 4 images separated by a space (renders inline on most
    # markdown frontends; each group is on its own line so they wrap nicely).
    rows: list[str] = []
    for i in range(0, len(image_tags), 4):
        rows.append(" ".join(image_tags[i : i + 4]))

    header = (
        f'> **Image Search Results for \u201c{query}\u201d** \u2014 '
        "show these images in your answer using the markdown below.\n"
    )
    return header + "\n".join(rows)



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
            try:
                await _process_turn(ws, thread_id, data)
            except Exception as exc:
                # Log the failure but keep the WebSocket open for the next turn.
                asyncio.ensure_future(
                    _log(
                        f"WS turn error thread={thread_id}: {exc}",
                        level="error",
                        urgency="critical",
                    )
                )
                await _send(ws, {"type": "error", "content": str(exc)})
                await _send(ws, {"type": "done"})

    except WebSocketDisconnect:
        asyncio.ensure_future(
            _log(f"WS disconnected thread={thread_id}", level="info")
        )
    except Exception as exc:
        asyncio.ensure_future(
            _log(
                f"WS fatal error thread={thread_id}: {exc}",
                level="error",
                urgency="critical",
            )
        )


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

    history = chat_service.get_recent_history(thread_id, limit=10)

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

    if _is_capability_query(user_query):
        await _send(
            ws,
            {
                "type": "thinking",
                "content": "Fetching live MCP tools...",
            },
        )
        full_response = await _build_capability_response()

        async for token in _single_chunk_stream(full_response):
            await _send(ws, {"type": "token", "content": token})

        await chat_service.bg_save_assistant_message(
            thread_id,
            full_response,
            seq + 1,
            citations={},
        )
        await _maybe_generate_title(ws, thread_id, history, user_query, full_response)
        await _send(ws, {"type": "done"})
        return

    # ── 3. Retrieve RAG chunks + direct search context ────────────────────
    live_web_sources: list[dict[str, str]] = []

    if query_urls:
        first_url = query_urls[0]
        short_url = first_url[:60] + "..." if len(first_url) > 60 else first_url
        extra = f" (+{len(query_urls) - 1} more)" if len(query_urls) > 1 else ""
        await _send(
            ws,
            {
                "type": "thinking",
                "content": f"Fetching page: {short_url}{extra}",
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
                    "content": f"Page loaded. Preparing answer...",
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

    # Server-side MCP search: detect YouTube / image / web intent and call
    # the tool directly.  Emit a descriptive thinking frame BEFORE the call
    # so the user sees what the agent is doing in real time.
    _search_category, _search_query = _detect_search_intent(user_query)
    if _search_category == "youtube":
        await _send(
            ws,
            {
                "type": "thinking",
                "content": f"Searching YouTube videos on '{_search_query}'...",
            },
        )
    elif _search_category == "image":
        await _send(
            ws,
            {
                "type": "thinking",
                "content": f"Searching images of '{_search_query}'...",
            },
        )

    search_context, search_sources, search_status = await _fetch_search_context(
        user_query
    )
    if search_context.strip():
        if search_status == "youtube":
            done_msg = f"Found YouTube results for '{_search_query}'. Preparing answer..."
        elif search_status == "image":
            done_msg = f"Found images for '{_search_query}'. Preparing answer..."
        else:
            done_msg = "Search complete. Preparing answer..."
        await _send(ws, {"type": "thinking", "content": done_msg})
        mcp_content = "\n\n".join(
            part for part in [mcp_content, search_context] if part.strip()
        )
        live_web_sources = _merge_sources(live_web_sources, search_sources)
    elif search_status != "none":
        await _send(
            ws,
            {
                "type": "thinking",
                "content": "Search returned no results. Answering with available context.",
            },
        )

    chunks: list[dict[str, Any]] = []
    should_query_rag = (
        rag_service.should_use_rag(user_query)
        and not query_urls
        and search_status == "none"  # skip RAG when live search already ran
    )
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
        if token.startswith("__THINKING__:"):
            await _send(
                ws,
                {
                    "type": "thinking",
                    "content": token[len("__THINKING__:"):],
                },
            )
            continue
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
