"""
Query module — async wrapper around the LLM query pre-processor.

Exposes `run_query_validation` as an async generator that:
  1. Validates the query for safety (injection, harmful content).
  2. Preprocesses and sanitizes the query via Gemini.
  3. Yields SSE-friendly dicts at each stage (progress, result, error).
  4. Logs every step through the task scheduler + quickLog.
  5. Broadcasts live status updates via the event bus.
"""

import asyncio
from typing import Any, AsyncIterator, Dict, Optional

from sse.event_bus import event_bus
from utils.logger.AgentLogger import quickLog
from utils.task_scheduler import scheduler
from query.LLMPreProcessStrategy import validateQuery, QueryValidationResult


async def run_query_validation(
    query: str,
    api_key: str,
    *,
    origin_research_id: Optional[str] = None,
) -> AsyncIterator[Dict[str, Any]]:
    """
    Validate and pre-process a user query for safety and sanitization.

    Args:
        query: The raw user query.
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
            "message": f"Query validation started for: {query[:80]} src:query",
            "module": ["AGENTS", "AI"],
            "urgency": "none",
        },
    )
    await event_bus.broadcast(
        message={"msg": "Validating your query..."}
    )

    yield {
        "success": True,
        "type": "progress",
        "message": "Query validation in progress...",
    }

    # ── 2. Run the (sync) validator in a thread so we don't block the loop ──
    try:
        result: QueryValidationResult = await asyncio.to_thread(
            validateQuery, query=query, api_key=api_key
        )
    except Exception as e:
        await scheduler.schedule(
            quickLog,
            params={
                "level": "error",
                "message": f"Query validation failed: {e} src:query",
                "module": ["AGENTS", "AI"],
                "urgency": "critical",
            },
        )
        await event_bus.broadcast(
            message={"msg": "Query validation failed."}
        )
        yield {
            "success": False,
            "type": "error",
            "message": str(e),
        }
        return

    # ── 3. Yield the result ──
    is_safe = result.get("is_safe", False)
    log_level = "success" if is_safe else "warning"
    status_msg = "Query is safe." if is_safe else "Query flagged as unsafe."

    await scheduler.schedule(
        quickLog,
        params={
            "level": log_level,
            "message": f"Query validation complete — {status_msg} src:query",
            "module": ["AGENTS", "AI"],
            "urgency": "none" if is_safe else "moderate",
        },
    )
    await event_bus.broadcast(
        message={"msg": status_msg}
    )

    yield {
        "success": True,
        "type": "result",
        "query": result.get("query", query),
        "is_safe": is_safe,
        "issue": result.get("issue", []),
        "summary": result.get("summary"),
        "safe_prompt": result.get("safe_prompt"),
        "origin_research_id": origin_research_id,
    }
