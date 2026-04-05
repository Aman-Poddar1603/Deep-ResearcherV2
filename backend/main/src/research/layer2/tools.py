"""
MCP tool loader.

Connects to the remote MCP server (MCP_SERVER_URL env) via HTTP transport
and returns a list of LangChain BaseTool instances ready to bind to agents.

Tools are cached at module level after first load.

MCP tool output formats (as documented):
  web_search        → {"results": [{success, url, content, scrape_duration, datetime_Scrape, metadata{title,...}}]}
  read_webpages     → {"results": [{success, url, content, scrape_duration, datetime_Scrape, metadata{title,...}}]}
  scrape_single_url → {"results": [{success, url, content, scrape_duration, datetime_Scrape, metadata{title,...}}]}
  youtube_search    → {query, total_results, scrape_time, videos:[{title, url, description, channel, duration, views, upload_date, thumbnail}]}
  image_search_tool → {<query>: [url, url, ...], <query2>: [...]}
  understand_images → {total_files, succeed, total_tokens_used, total_time_taken, content:{filename:{title,desc,tokens,time,stored_at}}}
  process_docs      → {total_files, succeed, total_tokens_used, total_time_taken, content:{filename: "summary string"}}
  search_urls_tool  → ["url1", "url2", ...]
"""

import json
import logging
import shlex
from datetime import timedelta
from typing import Any
from urllib.parse import urlparse, urlunparse

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from research.config import settings

logger = logging.getLogger(__name__)

_cached_tools: list[BaseTool] | None = None

# Use very large transport timeouts so long-running tools (web crawling, scraping,
# doc processing) are not interrupted by client-side defaults.
_MCP_HTTP_TIMEOUT = timedelta(hours=24)
_MCP_SSE_READ_TIMEOUT = timedelta(hours=24)


def _normalize_mcp_url(url: str) -> str:
    """Ensure MCP streamable-http URL points to an actual MCP endpoint path."""
    parsed = urlparse(url)
    path = parsed.path or ""

    # Most FastMCP streamable-http servers expose the MCP endpoint at /mcp.
    # If the user provides only host:port (or /), default to /mcp.
    if path in ("", "/"):
        parsed = parsed._replace(path="/mcp")

    return urlunparse(parsed)


def _candidate_mcp_urls(url: str) -> list[str]:
    """Build MCP URL candidates across common endpoint styles."""
    parsed = urlparse(url)
    path = parsed.path or ""

    candidates: list[str] = []

    def _add(candidate: str) -> None:
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    normalized = _normalize_mcp_url(url)
    _add(normalized)
    _add(url)

    # Some servers expose SSE endpoints at /sse instead of /mcp.
    if path.endswith("/mcp"):
        _add(urlunparse(parsed._replace(path=f"{path[:-4]}/sse")))
    elif path.endswith("/sse"):
        _add(urlunparse(parsed._replace(path=f"{path[:-4]}/mcp")))

    return candidates


async def get_mcp_tools() -> list[BaseTool]:
    global _cached_tools
    if _cached_tools is not None:
        return _cached_tools

    configured_url = settings.MCP_SERVER_URL
    urls_to_try = _candidate_mcp_urls(configured_url)
    stdio_command = settings.MCP_SERVER_COMMAND.strip()

    connection_variants: list[dict[str, Any]] = [
        {
            "transport": "http",
            "timeout": _MCP_HTTP_TIMEOUT,
            "sse_read_timeout": _MCP_SSE_READ_TIMEOUT,
        },
        {
            "transport": "sse",
            "timeout": _MCP_HTTP_TIMEOUT.total_seconds(),
            "sse_read_timeout": _MCP_SSE_READ_TIMEOUT.total_seconds(),
        },
    ]

    errors: list[str] = []

    # Optional stdio mode for servers started with FastMCP.run() default transport.
    if stdio_command:
        stdio_connection: dict[str, Any] = {
            "transport": "stdio",
            "command": stdio_command,
            "args": (
                shlex.split(settings.MCP_SERVER_ARGS.strip())
                if settings.MCP_SERVER_ARGS.strip()
                else []
            ),
        }
        stdio_cwd = settings.MCP_SERVER_CWD.strip()
        if stdio_cwd:
            stdio_connection["cwd"] = stdio_cwd

        logger.info(
            "[mcp] Connecting to MCP server via stdio command: %s", stdio_command
        )
        try:
            connections: Any = {"research_tools": stdio_connection}
            client = MultiServerMCPClient(connections=connections)  # type: ignore[arg-type]
            tools = await client.get_tools()
            _cached_tools = tools
            logger.info(
                "[mcp] Loaded %d tools from MCP server (transport=stdio)", len(tools)
            )
            return tools
        except Exception as exc:
            errors.append(f"stdio ({stdio_command}): {exc}")

    for candidate_url in urls_to_try:
        for variant in connection_variants:
            transport = variant["transport"]
            logger.info(
                "[mcp] Connecting to MCP server at %s (transport=%s)",
                candidate_url,
                transport,
            )
            try:
                connections: Any = {
                    "research_tools": {
                        "url": candidate_url,
                        **variant,
                    }
                }
                client = MultiServerMCPClient(connections=connections)  # type: ignore[arg-type]
                tools = await client.get_tools()
                _cached_tools = tools
                logger.info(
                    "[mcp] Loaded %d tools from MCP server (transport=%s)",
                    len(tools),
                    transport,
                )
                return tools
            except Exception as exc:
                errors.append(f"{candidate_url} ({transport}): {exc}")

    logger.warning(
        "[mcp] Failed to load tools from MCP server. Attempts: %s. Proceeding without MCP tools.",
        " | ".join(errors),
    )
    _cached_tools = []
    return []


def invalidate_tool_cache() -> None:
    global _cached_tools
    _cached_tools = None


def _parse_raw(output: Any) -> Any:
    """If the MCP tool returned a JSON string, parse it first."""
    if isinstance(output, str):
        try:
            return json.loads(output)
        except (json.JSONDecodeError, ValueError):
            return output
    return output


def extract_tool_token_count(tool_name: str, output: Any) -> int:
    """
    Extract LLM token count from tools that use Ollama internally.
    Only understand_images_tool and process_docs use an LLM.
    """
    data = _parse_raw(output)
    if not isinstance(data, dict):
        return 0
    return int(data.get("total_tokens_used", 0))


def parse_tool_output(tool_name: str, output: Any) -> list[dict]:
    """
    Normalise raw MCP tool output into a flat list of source dicts:
        [{"url": str, "content": str, "title": str, "description": str, "tool": str}, ...]

    Each caller (orchestrator1 _persist_step_sources, orchestrator2
    _build_citations / _schedule_chroma_indexing) iterates this list —
    no tool-specific branching needed outside this module.
    """
    data = _parse_raw(output)
    tool = tool_name

    # ── web_search / read_webpages / scrape_single_url ──────────────────────
    # {"results": [{success, url, content, scrape_duration, metadata{title}}]}
    if tool in ("web_search", "read_webpages", "scrape_single_url"):
        if not isinstance(data, dict):
            return []
        items = []
        for r in data.get("results", []):
            if not isinstance(r, dict) or not r.get("success"):
                continue
            meta = r.get("metadata", {}) or {}
            items.append(
                {
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                    "title": meta.get("title", r.get("url", "")),
                    "description": meta.get("description", ""),
                    "tool": tool,
                }
            )
        return items

    # ── youtube_search ───────────────────────────────────────────────────────
    # {query, total_results, scrape_time, videos:[{title,url,description,...}]}
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

    # ── image_search_tool ────────────────────────────────────────────────────
    # {<query>: ["url1", "url2", ...], ...}
    if tool == "image_search_tool":
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

    # ── understand_images_tool ───────────────────────────────────────────────
    # {total_files, succeed, total_tokens_used, total_time_taken,
    #  content: {filename: {title, desc, tokens, time, stored_at}}}
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

    # ── process_docs ─────────────────────────────────────────────────────────
    # {total_files, succeed, total_tokens_used, total_time_taken,
    #  content: {filename: "summary string"}}
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

    # ── search_urls_tool ─────────────────────────────────────────────────────
    # ["url1", "url2", ...]
    if tool == "search_urls_tool":
        if not isinstance(data, list):
            return []
        return [
            {"url": url, "content": url, "title": url, "description": "", "tool": tool}
            for url in data
            if isinstance(url, str) and url
        ]

    # ── fallback ─────────────────────────────────────────────────────────────
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

    items = parse_tool_output(tool_name, output)
    if not items:
        return "No results returned"

    tool = tool_name
    if tool in ("web_search", "read_webpages", "scrape_single_url"):
        titles = [i["title"] or i["url"] for i in items[:3]]
        return f"{len(items)} page(s) scraped — {', '.join(titles)}"
    if tool == "youtube_search":
        titles = [i["title"] for i in items[:3]]
        return f"{len(items)} video(s) found — {', '.join(titles)}"
    if tool == "image_search_tool":
        return f"{len(items)} image URL(s) found"
    if tool == "understand_images_tool":
        titles = [i["title"] for i in items[:3]]
        return f"{len(items)} image(s) analysed — {', '.join(titles)}"
    if tool == "process_docs":
        return f"{len(items)} document(s) processed — {', '.join(i['title'] for i in items[:3])}"
    if tool == "search_urls_tool":
        return f"{len(items)} URL(s) found"
    return f"{len(items)} result(s) from {tool_name}"
