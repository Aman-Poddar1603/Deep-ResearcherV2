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
from typing import Any

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from research.config import settings

logger = logging.getLogger(__name__)

_cached_tools: list[BaseTool] | None = None


async def get_mcp_tools() -> list[BaseTool]:
    global _cached_tools
    if _cached_tools is not None:
        return _cached_tools

    logger.info("[mcp] Connecting to MCP server at %s", settings.MCP_SERVER_URL)
    try:
        client = MultiServerMCPClient(
            {
                "research_tools": {
                    "url": settings.MCP_SERVER_URL,
                    "transport": "http",
                }
            }
        )
        tools = await client.get_tools()
        _cached_tools = tools
        logger.info("[mcp] Loaded %d tools from MCP server", len(tools))
        return tools
    except Exception as exc:
        logger.warning(
            "[mcp] Failed to connect to MCP server at %s: %s. Proceeding without MCP tools.",
            settings.MCP_SERVER_URL,
            exc,
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
    if tool == "understand_images_tool":
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
