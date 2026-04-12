"""
MCP tool loader.

Connects to the remote MCP server via streamable-http using direct MCP
sessions (not langchain-mcp-adapters), then exposes LangChain-compatible
BaseTool wrappers.

Tools are cached at module level after first successful load.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from contextlib import AsyncExitStack
from typing import Any, cast
from urllib.parse import urlparse, urlunparse

import httpx
from langchain_core.tools import BaseTool
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, create_model

from main.src.research.config import settings

logger = logging.getLogger(__name__)

_cached_tools: list[BaseTool] | None = None


def _normalize_mcp_url(url: str) -> str:
    """Ensure streamable-http MCP URL points to an MCP endpoint path."""
    parsed = urlparse(url)
    path = parsed.path or ""

    # Most streamable-http MCP servers expose endpoint at /mcp.
    if path in ("", "/"):
        parsed = parsed._replace(path="/mcp")

    return urlunparse(parsed)


def _candidate_mcp_urls(url: str) -> list[str]:
    """Build streamable-http URL candidates in safe order."""
    candidates: list[str] = []

    def _add(candidate: str) -> None:
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    _add(_normalize_mcp_url(url))
    _add(url)
    return candidates


def _json_schema_to_python_type(schema: Any) -> Any:
    """Map JSON-Schema primitive types to Python annotations."""
    if not isinstance(schema, dict):
        return Any

    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        non_null = [t for t in schema_type if t != "null"]
        if len(non_null) == 1:
            return _json_schema_to_python_type({**schema, "type": non_null[0]})
        return Any

    if schema_type == "string":
        return str
    if schema_type == "integer":
        return int
    if schema_type == "number":
        return float
    if schema_type == "boolean":
        return bool
    if schema_type == "array":
        item_type = _json_schema_to_python_type(schema.get("items", {}))
        if item_type is Any:
            return list[Any]
        return list[item_type]
    if schema_type == "object":
        return dict[str, Any]
    return Any


def _make_args_schema(tool_name: str, input_schema: Any) -> type[BaseModel]:
    """Create best-effort Pydantic args schema from MCP inputSchema."""
    if not isinstance(input_schema, dict):
        input_schema = {}

    properties = input_schema.get("properties") or {}
    required = set(input_schema.get("required") or [])
    model_config = ConfigDict(extra="allow")

    safe_name = re.sub(r"[^0-9a-zA-Z_]", "_", tool_name).strip("_") or "mcp_tool"
    if safe_name[0].isdigit():
        safe_name = f"tool_{safe_name}"
    model_name = "".join(part.capitalize() for part in safe_name.split("_")) + "Args"

    if not isinstance(properties, dict) or not properties:
        return create_model(model_name, __config__=model_config)

    field_defs: dict[str, Any] = {}
    for name, schema in properties.items():
        if not isinstance(name, str) or not name.isidentifier():
            continue

        annotation = _json_schema_to_python_type(schema)
        is_required = name in required
        if not is_required and annotation is not Any:
            annotation = annotation | None

        description = schema.get("description", "") if isinstance(schema, dict) else ""
        default = ... if is_required else None
        if description:
            field_defs[name] = (
                annotation,
                Field(default=default, description=description),
            )
        else:
            field_defs[name] = (annotation, default)

    if not field_defs:
        return create_model(model_name, __config__=model_config)

    return create_model(
        model_name,
        __config__=model_config,
        **cast(dict[str, Any], field_defs),
    )


def _normalize_tool_result_content(result: Any) -> Any:
    """Normalize MCP call result into str/dict/list for downstream parsing."""
    if isinstance(result, (str, dict, list)):
        return result

    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return structured

    content = getattr(result, "content", None)
    if content is not None:
        text_parts: list[str] = []
        for item in content:
            text = getattr(item, "text", None)
            if isinstance(text, str):
                text_parts.append(text)
                continue

            model_dump = getattr(item, "model_dump", None)
            if callable(model_dump):
                try:
                    text_parts.append(json.dumps(model_dump(), ensure_ascii=True))
                except (TypeError, ValueError):
                    text_parts.append(str(item))
            else:
                text_parts.append(str(item))

        if len(text_parts) == 1:
            return text_parts[0]

        if text_parts:
            joined = "\n".join(text_parts)
            try:
                return json.loads(joined)
            except (json.JSONDecodeError, ValueError):
                return joined

    model_dump = getattr(result, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            if dumped.get("structuredContent") is not None:
                return dumped["structuredContent"]
            if dumped.get("content") is not None:
                return dumped["content"]
        return dumped

    return str(result)


class _MCPRuntime:
    """Direct MCP runtime using short-lived sessions per operation."""

    def __init__(self, urls: list[str]):
        self._urls = urls
        self._lock = asyncio.Lock()
        self._connected_url: str | None = None
        self._tools: list[Any] = []

    def _ordered_urls(self) -> list[str]:
        urls: list[str] = []
        if self._connected_url:
            urls.append(self._connected_url)
        for url in self._urls:
            if url not in urls:
                urls.append(url)
        return urls

    async def _run_with_session(
        self, url: str, operation: str, tool_name: str = ""
    ) -> Any:
        async with AsyncExitStack() as stack:
            # Disable all HTTP/SSE read time limits so long-running MCP tools can complete.
            http_client = await stack.enter_async_context(
                httpx.AsyncClient(follow_redirects=True, timeout=None)
            )
            read, write, get_session_id = await stack.enter_async_context(
                streamable_http_client(
                    url,
                    http_client=http_client,
                    terminate_on_close=False,
                )
            )
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()

            session_id: str | None = None
            if callable(get_session_id):
                try:
                    value = get_session_id()
                    session_id = str(value) if value is not None else None
                except Exception:
                    session_id = None

            logger.info(
                "[mcp] session_opened session_id=%s url=%s op=%s tool=%s",
                session_id or "unknown",
                url,
                operation,
                tool_name or "-",
            )

            if operation == "list_tools":
                response = await session.list_tools()
                self._connected_url = url
                return list(getattr(response, "tools", []) or [])

            if operation == "call_tool":
                raise RuntimeError("Missing tool execution callback")

            raise RuntimeError(f"Unsupported MCP operation: {operation}")

    async def list_tools(self) -> list[Any]:
        async with self._lock:
            if not self._tools:
                errors: list[str] = []
                for url in self._ordered_urls():
                    try:
                        logger.info(
                            "[mcp] Connecting directly to MCP server at %s", url
                        )
                        self._tools = await self._run_with_session(
                            url, operation="list_tools"
                        )
                        logger.info(
                            "[mcp] Connected to %s with %d tool(s)",
                            self._connected_url,
                            len(self._tools),
                        )
                        break
                    except Exception as exc:
                        errors.append(f"{url}: {exc}")

                if not self._tools and errors:
                    raise RuntimeError(
                        "Failed to connect to MCP server via streamable-http. Attempts: "
                        + " | ".join(errors)
                    )

            return list(self._tools)

    async def call_tool(
        self, name: str, arguments: dict[str, Any] | None = None
    ) -> Any:
        payload = arguments or {}
        errors: list[str] = []

        async with self._lock:
            for url in self._ordered_urls():
                try:
                    logger.info("[mcp] Connecting directly to MCP server at %s", url)
                    async with AsyncExitStack() as stack:
                        http_client = await stack.enter_async_context(
                            httpx.AsyncClient(follow_redirects=True, timeout=None)
                        )
                        read, write, get_session_id = await stack.enter_async_context(
                            streamable_http_client(
                                url,
                                http_client=http_client,
                                terminate_on_close=False,
                            )
                        )
                        session = await stack.enter_async_context(
                            ClientSession(read, write)
                        )
                        await session.initialize()

                        session_id: str | None = None
                        if callable(get_session_id):
                            try:
                                value = get_session_id()
                                session_id = str(value) if value is not None else None
                            except Exception:
                                session_id = None

                        logger.info(
                            "[mcp] session_opened session_id=%s url=%s op=call_tool tool=%s",
                            session_id or "unknown",
                            url,
                            name,
                        )

                        result = await session.call_tool(name, arguments=payload)

                    self._connected_url = url
                    return _normalize_tool_result_content(result)
                except Exception as exc:
                    errors.append(f"{url}: {exc}")

        raise RuntimeError(
            f"MCP tool call failed for {name}. Attempts: " + " | ".join(errors)
        )

    async def close(self) -> None:
        # Runtime uses short-lived sessions; nothing persistent to close.
        return


class _DirectMCPTool(BaseTool):
    """LangChain tool wrapper that proxies to direct MCP call_tool."""

    name: str = ""
    description: str = ""

    _runtime: _MCPRuntime = PrivateAttr()
    _tool_name: str = PrivateAttr()

    def __init__(
        self,
        *,
        runtime: _MCPRuntime,
        tool_name: str,
        description: str,
        input_schema: Any,
    ):
        super().__init__(
            name=tool_name,
            description=description or f"MCP tool: {tool_name}",
            args_schema=_make_args_schema(tool_name, input_schema),
        )
        self._runtime = runtime
        self._tool_name = tool_name

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("Direct MCP tools are async-only; use async invoke")

    async def _arun(
        self,
        *args: Any,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> Any:
        _ = run_manager

        payload: dict[str, Any]
        if kwargs:
            payload = dict(kwargs)
            if (
                len(payload) == 1
                and "input" in payload
                and isinstance(payload["input"], dict)
            ):
                payload = payload["input"]
        elif len(args) == 1 and isinstance(args[0], dict):
            payload = args[0]
        elif len(args) == 1:
            payload = {"input": args[0]}
        else:
            payload = {}

        return await self._runtime.call_tool(self._tool_name, payload)


_mcp_runtime: _MCPRuntime | None = None


async def get_mcp_tools() -> list[BaseTool]:
    global _cached_tools, _mcp_runtime
    if _cached_tools is not None:
        return _cached_tools

    configured_url = settings.MCP_SERVER_URL
    urls_to_try = _candidate_mcp_urls(configured_url)

    transport_pref = settings.MCP_TRANSPORT.strip().lower()
    if transport_pref and transport_pref not in ("http", "auto"):
        logger.warning(
            "[mcp] MCP_TRANSPORT=%s requested, but direct MCP client uses streamable-http.",
            transport_pref,
        )

    if _mcp_runtime is None:
        _mcp_runtime = _MCPRuntime(urls=urls_to_try)

    try:
        server_tools = await _mcp_runtime.list_tools()
    except Exception as exc:
        logger.warning(
            "[mcp] Failed to load tools from MCP server. Error: %s. Proceeding without MCP tools.",
            exc,
        )
        _mcp_runtime = None
        return []

    tools: list[BaseTool] = []
    for tool in server_tools:
        name = getattr(tool, "name", "")
        if not name:
            continue

        tools.append(
            _DirectMCPTool(
                runtime=_mcp_runtime,
                tool_name=name,
                description=getattr(tool, "description", "") or "",
                input_schema=getattr(tool, "inputSchema", {}) or {},
            )
        )

    _cached_tools = tools
    return tools


def invalidate_tool_cache() -> None:
    global _cached_tools, _mcp_runtime
    _cached_tools = None

    runtime = _mcp_runtime
    _mcp_runtime = None
    if runtime is None:
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    loop.create_task(runtime.close())


async def shutdown_mcp_runtime() -> None:
    """Close persistent MCP runtime once during full app shutdown."""
    global _cached_tools, _mcp_runtime

    runtime = _mcp_runtime
    _mcp_runtime = None
    _cached_tools = None

    if runtime is None:
        return

    await runtime.close()


def _parse_raw(output: Any) -> Any:
    """If the MCP tool returned a JSON string, parse it first."""
    if hasattr(output, "artifact") and getattr(output, "artifact") is not None:
        output = getattr(output, "artifact")
    elif hasattr(output, "content") and not isinstance(output, type):
        output = getattr(output, "content")

    if isinstance(output, str):
        try:
            return json.loads(output)
        except (json.JSONDecodeError, ValueError):
            return output
    return output


def _normalize_tool_name(tool_name: str) -> str:
    """Normalize tool names so parser works with namespaced wrappers too."""
    name = (tool_name or "").strip().lower()
    if not name:
        return ""

    if "::" in name:
        name = name.split("::")[-1]
    if "/" in name:
        name = name.split("/")[-1]
    if "." in name:
        name = name.split(".")[-1]

    name = re.sub(r"^(research_tools_|mcp_|tool_)", "", name)
    return name


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=True)
        except (TypeError, ValueError):
            return str(value)
    return str(value)


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _extract_usage_total(payload: Any) -> int:
    if not isinstance(payload, dict):
        return 0

    for total_key in ("total_tokens_used", "total_tokens", "total"):
        total = _to_int(payload.get(total_key))
        if total > 0:
            return total

    for prompt_key, completion_key in (
        ("prompt_tokens", "completion_tokens"),
        ("input_tokens", "output_tokens"),
        ("prompt_eval_count", "eval_count"),
    ):
        prompt = _to_int(payload.get(prompt_key))
        completion = _to_int(payload.get(completion_key))
        if prompt > 0 or completion > 0:
            return prompt + completion

    for nested_key in ("usage", "token_usage", "usage_metadata", "metadata"):
        nested = _extract_usage_total(payload.get(nested_key))
        if nested > 0:
            return nested

    return 0


def extract_tool_token_count(tool_name: str, output: Any) -> int:
    """
    Extract LLM token count from tools that use Ollama internally.
    Only understand_images_tool and process_docs use an LLM.
    """
    _ = tool_name
    data = _parse_raw(output)
    return _extract_usage_total(data)


def parse_tool_output(tool_name: str, output: Any) -> list[dict]:
    """
    Normalise raw MCP tool output into a flat list of source dicts:
        [{"url": str, "content": str, "title": str, "description": str, "tool": str}, ...]

    Each caller (orchestrator1 _persist_step_sources, orchestrator2
    _build_citations / _schedule_chroma_indexing) iterates this list.
    """
    data = _parse_raw(output)
    raw_tool = tool_name
    tool = _normalize_tool_name(tool_name)

    # web_search / read_webpages / scrape_single_url
    if tool in ("web_search", "read_webpages", "scrape_single_url"):
        if not isinstance(data, dict):
            return []
        items = []
        for r in data.get("results", []):
            if not isinstance(r, dict):
                continue
            meta = r.get("metadata", {}) or {}
            items.append(
                {
                    "url": r.get("url", ""),
                    "content": _to_text(r.get("content", "")),
                    "title": meta.get("title", r.get("url", "")),
                    "description": meta.get("description", ""),
                    "tool": tool,
                }
            )
        return items

    # youtube_search
    if tool == "youtube_search":
        if not isinstance(data, dict):
            return []
        items = []
        for v in data.get("videos", []):
            if not isinstance(v, dict):
                continue
            content = (
                f"Title: {v.get('title', '')}\n"
                f"Channel: {v.get('channel', '')}\n"
                f"Description: {v.get('description', '')}\n"
                f"Views: {v.get('views', '')}\n"
                f"Duration: {v.get('duration', '')}s\n"
                f"Upload date: {v.get('upload_date', '')}"
            )
            items.append(
                {
                    "url": v.get("url", ""),
                    "content": content,
                    "title": v.get("title", ""),
                    "description": v.get("description", ""),
                    "tool": tool,
                }
            )
        return items

    # image_search_tool
    if tool in ("image_search_tool", "image_search"):
        if not isinstance(data, dict):
            return []
        items = []
        for query_key, urls in data.items():
            if not isinstance(urls, list):
                continue
            for url in urls:
                if isinstance(url, str) and url:
                    items.append(
                        {
                            "url": url,
                            "content": f"Image result for query: {query_key}",
                            "title": f"Image: {query_key}",
                            "description": "",
                            "tool": tool,
                        }
                    )
        return items

    # understand_images_tool
    if tool in ("understand_images_tool", "understand_images"):
        if not isinstance(data, dict):
            return []
        items = []
        for filename, info in data.get("content", {}).items():
            if not isinstance(info, dict):
                continue
            items.append(
                {
                    "url": info.get("stored_at", filename),
                    "content": f"{info.get('title', '')}\n{info.get('desc', '')}",
                    "title": info.get("title", filename),
                    "description": info.get("desc", ""),
                    "tool": tool,
                }
            )
        return items

    # process_docs
    if tool == "process_docs":
        if not isinstance(data, dict):
            return []
        items = []
        for filename, summary in data.get("content", {}).items():
            items.append(
                {
                    "url": filename,
                    "content": str(summary),
                    "title": filename,
                    "description": str(summary)[:200],
                    "tool": tool,
                }
            )
        return items

    # search_urls_tool
    if tool in ("search_urls_tool", "search_urls"):
        if not isinstance(data, list):
            return []
        return [
            {"url": url, "content": url, "title": url, "description": "", "tool": tool}
            for url in data
            if isinstance(url, str) and url
        ]

    # generic dict fallback
    if isinstance(data, dict):
        results = data.get("results")
        if isinstance(results, list):
            items = []
            for i, r in enumerate(results):
                if isinstance(r, dict):
                    url = _to_text(r.get("url") or r.get("link") or "")
                    content = _to_text(
                        r.get("content") or r.get("text") or r.get("summary") or r
                    )
                    title = _to_text(
                        r.get("title") or url or f"{raw_tool} result {i + 1}"
                    )
                    if content:
                        items.append(
                            {
                                "url": url,
                                "content": content,
                                "title": title,
                                "description": content[:200],
                                "tool": tool or raw_tool,
                            }
                        )
            if items:
                return items

        url = _to_text(data.get("url") or data.get("link") or "")
        content = _to_text(data.get("content") or data.get("text") or data)
        title = _to_text(data.get("title") or url or raw_tool)
        if content:
            return [
                {
                    "url": url,
                    "content": content,
                    "title": title,
                    "description": content[:200],
                    "tool": tool or raw_tool,
                }
            ]

    # generic list fallback
    if isinstance(data, list):
        items = []
        for i, entry in enumerate(data):
            if isinstance(entry, dict):
                url = _to_text(entry.get("url") or entry.get("link") or "")
                content = _to_text(entry.get("content") or entry.get("text") or entry)
                title = _to_text(
                    entry.get("title") or url or f"{raw_tool} result {i + 1}"
                )
            else:
                url = ""
                content = _to_text(entry)
                title = f"{raw_tool} result {i + 1}"
            if content:
                items.append(
                    {
                        "url": url,
                        "content": content,
                        "title": title,
                        "description": content[:200],
                        "tool": tool or raw_tool,
                    }
                )
        if items:
            return items

    if isinstance(data, str) and data.strip():
        return [
            {
                "url": "",
                "content": data,
                "title": raw_tool,
                "description": data[:200],
                "tool": tool or raw_tool,
            }
        ]

    return []


def summarise_tool_output(tool_name: str, output: Any) -> str:
    """
    Produce a short human-readable summary for WS tool.result events.
    Uses the parsed source list so the logic is exact per tool.
    """
    parsed_raw = _parse_raw(output)
    if isinstance(parsed_raw, str):
        raw_text = parsed_raw.strip()
        if raw_text.lower().startswith("error"):
            return raw_text.splitlines()[0][:280]

    print(
        f"Debug: summarise_tool_output for tool '{tool_name}' with raw output: {str(output)[:50]}"
    )

    items = parse_tool_output(tool_name, output)
    if not items:
        return "No results returned"

    tool = _normalize_tool_name(tool_name)
    if tool in ("web_search", "read_webpages", "scrape_single_url"):
        titles = [i["title"] or i["url"] for i in items[:3]]
        return f"{len(items)} page(s) scraped - {', '.join(titles)}"
    if tool == "youtube_search":
        titles = [i["title"] for i in items[:3]]
        return f"{len(items)} video(s) found - {', '.join(titles)}"
    if tool == "image_search_tool":
        return f"{len(items)} image URL(s) found"
    if tool == "understand_images_tool":
        titles = [i["title"] for i in items[:3]]
        return f"{len(items)} image(s) analysed - {', '.join(titles)}"
    if tool == "process_docs":
        return f"{len(items)} document(s) processed - {', '.join(i['title'] for i in items[:3])}"
    if tool == "search_urls_tool":
        return f"{len(items)} URL(s) found"
    return f"{len(items)} result(s) from {tool or tool_name}"
