"""
Summarizer module — async wrapper around the SummarizerAgent.

Exposes `run_summarizer` as an async generator that:
  1. Validates & preprocesses the query via the LLM pre-processor.
  2. Summarizes the supplied content using Gemini.
  3. Yields SSE-friendly dicts at each stage (progress, result, error).
  4. Logs every step through the task scheduler + quickLog.
  5. Broadcasts live status updates via the event bus.
"""

import asyncio
from typing import Any, AsyncIterator, Dict, Optional

from sse.event_bus import event_bus
from utils.logger.AgentLogger import quickLog
from utils.task_scheduler import scheduler
from summarizer.agent import summarize, SummarizerResult


async def run_summarizer(
    query: str,
    content: str,
    api_key: str,
    *,
    origin_research_id: Optional[str] = None,
) -> AsyncIterator[Dict[str, Any]]:
    """
    Summarize the given content with respect to the query.

    Args:
        query: The user's research query.
        content: The scraped/raw text content to summarize.
        api_key: Gemini API key.
        origin_research_id: Optional research session ID for traceability.

    Yields:
        Dicts suitable for SSE streaming (type: progress | result | error).
    """

    # ── 1. Log & broadcast: starting ──
    await scheduler.schedule(
        quickLog,
        params={
            "level": "info",
            "message": f"Summarizer started for query: {query[:80]} src:summarizer",
            "module": ["AGENTS", "AI"],
            "urgency": "none",
        },
    )
    await event_bus.broadcast(
        message={"msg": "Summarizing the content..."}
    )

    yield {
        "success": True,
        "type": "progress",
        "message": "Summarizer is processing your query...",
    }

    # ── 2. Run the (sync) summarizer in a thread so we don't block the loop ──
    try:
        result: SummarizerResult = await asyncio.to_thread(
            summarize, query=query, api_key=api_key
        )
    except Exception as e:
        await scheduler.schedule(
            quickLog,
            params={
                "level": "error",
                "message": f"Summarizer failed: {e} src:summarizer",
                "module": ["AGENTS", "AI"],
                "urgency": "critical",
            },
        )
        await event_bus.broadcast(
            message={"msg": "Summarization failed."}
        )
        yield {
            "success": False,
            "type": "error",
            "message": str(e),
        }
        return

    # ── 3. Yield the result ──
    await scheduler.schedule(
        quickLog,
        params={
            "level": "success",
            "message": f"Summarizer completed for query: {query[:80]} src:summarizer",
            "module": ["AGENTS", "AI"],
            "urgency": "none",
        },
    )
    await event_bus.broadcast(
        message={"msg": "Summarization complete."}
    )

    yield {
        "success": True,
        "type": "result",
        "query": result.get("query", query),
        "summary": result.get("summary", ""),
        "origin_research_id": origin_research_id,
    }
