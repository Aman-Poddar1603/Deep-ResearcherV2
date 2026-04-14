"""
## Description

Provides the `SearchService` class for unified searching across all content
types in the Deep Researcher application. Queries all databases (workspaces,
chats, researches, scrapes, assets/buckets, search history), merges results
with type classification, supports pagination, and optionally generates
AI-powered summaries via background workers.

## Parameters

None (Module level)

## Returns

None (Module level)

## Side Effects

- Reads from all database managers at query time.
- Schedules background tasks for logging and AI generation.

## Debug Notes

- Search uses the `DBManager.search()` LIKE method across separate databases.
- AI summary generation is non-blocking and dispatched via the scheduler.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Union

from main.src.store.DBManager import (
    main_db_manager,
    chats_db_manager,
    researches_db_manager,
    scrapes_db_manager,
    buckets_db_manager,
    history_db_manager,
)
from main.src.utils.DRLogger import quickLog
from main.src.utils.core.task_schedular import scheduler
from main.sse.event_bus import event_bus

SearchType = Literal["workspace", "chats", "researches", "scrapes", "assets", "history"]

# ── Search target definitions ─────────────────────────────────────────
# Each entry maps a content type to its db manager, table, search columns,
# return columns, and the field to use as the display title.

_SEARCH_TARGETS: List[Dict[str, Any]] = [
    {
        "type": "workspace",
        "manager": main_db_manager,
        "table": "workspaces",
        "search_columns": ["name", "desc"],
        "return_columns": ["id", "name", "desc", "created_at", "updated_at"],
        "title_field": "name",
        "snippet_field": "desc",
    },
    {
        "type": "chats",
        "manager": chats_db_manager,
        "table": "chat_threads",
        "search_columns": ["thread_title"],
        "return_columns": [
            "thread_id",
            "thread_title",
            "workspace_id",
            "created_at",
            "updated_at",
        ],
        "title_field": "thread_title",
        "snippet_field": "thread_title",
    },
    {
        "type": "researches",
        "manager": researches_db_manager,
        "table": "researches",
        "search_columns": ["title", "desc", "prompt"],
        "return_columns": [
            "id",
            "title",
            "desc",
            "prompt",
            "workspace_id",
        ],
        "title_field": "title",
        "snippet_field": "desc",
    },
    {
        "type": "scrapes",
        "manager": scrapes_db_manager,
        "table": "scrapes",
        "search_columns": ["url", "title", "content"],
        "return_columns": [
            "id",
            "url",
            "title",
            "created_at",
            "updated_at",
        ],
        "title_field": "title",
        "snippet_field": "url",
    },
    {
        "type": "assets",
        "manager": buckets_db_manager,
        "table": "bucket_items",
        "search_columns": ["file_name", "summary", "source"],
        "return_columns": [
            "id",
            "bucket_id",
            "file_name",
            "file_format",
            "file_size",
            "summary",
            "created_at",
        ],
        "title_field": "file_name",
        "snippet_field": "summary",
    },
]


def _build_item(
    raw: Dict[str, Any],
    content_type: str,
    title_field: str,
    snippet_field: str,
) -> Dict[str, Any]:
    """
    ## Description

    Normalises a raw DB row into a unified search result item that the
    frontend can easily classify and render.

    ## Parameters

    - `raw` (`dict`)
      - Description: A single row dict from the database.
      - Constraints: Must contain the title_field key at minimum.

    - `content_type` (`str`)
      - Description: The search type tag (workspace, chats, etc.).
      - Constraints: Must be a valid SearchType.

    - `title_field` (`str`)
      - Description: Key in `raw` to use as the display title.
      - Constraints: Must exist in the raw dict.

    - `snippet_field` (`str`)
      - Description: Key in `raw` to use as the content snippet.
      - Constraints: May be absent; falls back to empty string.

    ## Returns

    `dict` — Normalised search result item.
    """
    item_id = raw.get("id") or raw.get("thread_id") or raw.get("message_id") or ""
    title = raw.get(title_field) or "Untitled"
    snippet = raw.get(snippet_field) or ""
    if isinstance(snippet, str) and len(snippet) > 200:
        snippet = snippet[:200] + "…"

    # Build metadata from remaining fields
    metadata = {
        k: v
        for k, v in raw.items()
        if k not in (title_field, snippet_field, "id", "thread_id")
    }

    return {
        "id": item_id,
        "type": content_type,
        "title": title,
        "snippet": snippet,
        "metadata": metadata,
    }


class SearchService:
    """
    ## Description

    Unified search service that queries all content databases, merges
    and paginates results, and optionally triggers background AI summary
    generation.

    ## Parameters

    None (Uses module-level DB managers.)

    ## Returns

    None (Instantiates the service.)
    """

    def search_all(
        self,
        query: str,
        page: int = 1,
        size: int = 10,
        type_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        ## Description

        Searches across all 6 content databases, merges results into a
        unified list with type tags, and returns a paginated response.

        ## Parameters

        - `query` (`str`)
          - Description: The raw search query from the user.
          - Constraints: Must be non-empty.
          - Example: `"deep learning"`

        - `page` (`int`)
          - Description: 1-based page number.
          - Constraints: Must be >= 1.
          - Example: `1`

        - `size` (`int`)
          - Description: Results per page.
          - Constraints: Must be >= 1, max 50.
          - Example: `10`

        - `type_filter` (`Optional[str]`)
          - Description: If set, only search this content type.
          - Constraints: Must be a valid SearchType or None.
          - Example: `"workspace"`

        ## Returns

        `dict`

        Structure:

        ```json
        {
            "total_count": 42,
            "page": 1,
            "size": 10,
            "items": [
                {
                    "id": "...",
                    "type": "workspace",
                    "title": "...",
                    "snippet": "...",
                    "metadata": {}
                }
            ]
        }
        ```
        """
        all_items: List[Dict[str, Any]] = []
        targets = _SEARCH_TARGETS

        if type_filter:
            targets = [t for t in targets if t["type"] == type_filter]

        for target in targets:
            result = target["manager"].search(
                table_name=target["table"],
                query=query,
                num_results=200,
                page=1,
                search_columns=target["search_columns"],
                return_columns=target["return_columns"],
            )
            if result["success"] and result["data"]:
                for raw_item in result["data"]["items"]:
                    all_items.append(
                        _build_item(
                            raw_item,
                            target["type"],
                            target["title_field"],
                            target["snippet_field"],
                        )
                    )

        total_count = len(all_items)

        # Paginate
        start = (page - 1) * size
        end = start + size
        page_items = all_items[start:end]

        return {
            "total_count": total_count,
            "page": page,
            "size": size,
            "items": page_items,
        }

    def get_top_per_type(
        self,
        query: str,
        n: int = 2,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        ## Description

        Returns the top `n` results from each content type for AI context
        building. Used to construct the prompt for the AI summary.

        ## Parameters

        - `query` (`str`)
          - Description: The raw search query.
          - Constraints: Must be non-empty.

        - `n` (`int`)
          - Description: Number of top results per type.
          - Constraints: Must be >= 1. Defaults to 2.

        ## Returns

        `dict` — Keyed by content type, each value is a list of up to `n` items.
        """
        top: Dict[str, List[Dict[str, Any]]] = {}

        for target in _SEARCH_TARGETS:
            result = target["manager"].search(
                table_name=target["table"],
                query=query,
                num_results=n,
                page=1,
                search_columns=target["search_columns"],
                return_columns=target["return_columns"],
            )
            items = []
            if result["success"] and result["data"]:
                for raw_item in result["data"]["items"]:
                    items.append(
                        _build_item(
                            raw_item,
                            target["type"],
                            target["title_field"],
                            target["snippet_field"],
                        )
                    )
            if items:
                top[target["type"]] = items

        return top

    def save_search_record(
        self,
        search_id: str,
        query: str,
        total_results: int,
        results_json: str,
        is_aimode: bool = False,
    ) -> None:
        """
        ## Description

        Persists a search record to the `searches` table in the history DB.
        Designed to be called as a background task via the scheduler.

        ## Parameters

        - `search_id` (`str`)
          - Description: UUID for this search.
          - Constraints: Must be unique.

        - `query` (`str`)
          - Description: The original search query.
          - Constraints: Must be non-empty.

        - `total_results` (`int`)
          - Description: Total number of results found.
          - Constraints: Must be >= 0.

        - `results_json` (`str`)
          - Description: JSON-serialised results summary.
          - Constraints: Must be valid JSON string.

        - `is_aimode` (`bool`)
          - Description: Whether AI mode was enabled.
          - Constraints: Boolean.

        ## Returns

        `None`
        """
        now = datetime.now(timezone.utc).isoformat()
        history_db_manager.insert(
            "searches",
            {
                "id": search_id,
                "query": query,
                "is_aimode": 1 if is_aimode else 0,
                "total_results": total_results,
                "results": results_json,
                "status": "processing" if is_aimode else "done",
                "created_at": now,
                "updated_at": now,
            },
        )

    async def generate_ai_summary(
        self,
        search_id: str,
        query: str,
        top_results: Dict[str, List[Dict[str, Any]]],
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """
        ## Description

        Generates an AI summary: tries Groq first, falls back to Ollama.
        Uses caching to prevent spam calls to Groq API.
        Updates the searches table, records history, and broadcasts via SSE.
        Designed to run as a background task.

        ## Parameters

        - `search_id` (`str`)
          - Description: UUID of the search to update.
          - Constraints: Must exist in the searches table.

        - `query` (`str`)
          - Description: The original search query.
          - Constraints: Must be non-empty.

        - `top_results` (`dict`)
          - Description: Top results per type from `get_top_per_type()`.
          - Constraints: Dict keyed by type string.

        - `workspace_id` (`Optional[str]`)
          - Description: Workspace context for history recording.

        - `user_id` (`Optional[str]`)
          - Description: User context for history recording.

        ## Returns

        `None`

        ## Side Effects

        - Tries Groq API first (with caching), falls back to Ollama.
        - Updates the searches table with the AI summary.
        - Records history in user_usage_history and ai_summaries tables.
        - Broadcasts `search.ai_done` event via SSE EventBus.
        """
        from main.src.research.config import settings
        from main.src.utils.llms.ollama.DROllamaWrapper import (
            getAsyncClient,
            asyncGenerateContent,
        )
        from langchain_groq import ChatGroq
        from langchain_core.messages import HumanMessage, SystemMessage
        import time
        import redis
        import asyncio
        import hashlib

        # ─── QUERY-BASED CACHING: Use query as the cache key ─────────────────────
        # Hash the query to create a stable cache key
        query_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()
        cache_key = f"search_ai_summary:{query_hash}"
        processing_key = f"search_ai_processing:{query_hash}"
        processing_ttl = 300  # 5 minutes lock per query

        r = None
        try:
            redis_url = settings.REDIS_URL or "redis://localhost:6379"
            r = redis.from_url(redis_url, decode_responses=True)

            # Check Redis cache for this query
            cached_summary = r.get(cache_key)
            if cached_summary:
                await scheduler.schedule(
                    quickLog,
                    params={
                        "message": f"AI summary retrieved from Redis cache for query: {query}",
                        "level": "info",
                        "urgency": "none",
                        "module": "DB",
                    },
                )
                # Update current search record with cached summary
                history_db_manager.update(
                    "searches",
                    {"ai_summary": cached_summary, "status": "done"},
                    where={"id": search_id},
                )
                # Broadcast the cached result
                await event_bus.broadcast(
                    {
                        "event": "search.ai_done",
                        "search_id": search_id,
                        "query": query,
                        "ai_mode": {
                            "status": "done",
                            "ai_summary": cached_summary,
                            "model": "cached",
                            "time_taken_sec": 0,
                        },
                    }
                )
                return

            # Check if already being processed for this query
            if r.exists(processing_key):
                await scheduler.schedule(
                    quickLog,
                    params={
                        "message": f"AI summary generation already in progress for query: {query}, skipping duplicate call",
                        "level": "warning",
                        "urgency": "moderate",
                        "module": "DB",
                    },
                )
                return

            # Set processing lock for this query
            r.setex(processing_key, processing_ttl, "1")
        except Exception as redis_error:
            await scheduler.schedule(
                quickLog,
                params={
                    "message": f"Redis cache check failed, proceeding with caution: {redis_error}",
                    "level": "warning",
                    "urgency": "moderate",
                    "module": "DB",
                },
            )

        # Build context from top results
        context_parts: List[str] = []
        for content_type, items in top_results.items():
            context_parts.append(f"=== {content_type.upper()} ===")
            for item in items:
                context_parts.append(f"- [{item['title']}]: {item['snippet']}")
        context_text = "\n".join(context_parts)

        system_prompt = (
            "You are a helpful search assistant for a research application. "
            "The user searched for something and below are the top matching "
            "results from their workspace, chats, researches, scraped pages, "
            "assets, and search history. Provide a concise, informative "
            "summary that helps the user understand what was found and "
            "which results are most relevant. Keep it under 300 words. "
            "Reference specific items by name when relevant."
        )

        user_prompt = (
            f'Search query: "{query}"\n\n'
            f"Top results from the application:\n{context_text}\n\n"
            f"Please summarise what was found and highlight the most "
            f"relevant items for this query."
        )

        ai_summary = None
        model_used = None
        tokens_used = 0
        start_time = time.time()
        status = "failed"

        # Try Groq first
        if settings.GROQ_API_KEY:
            try:
                groq_llm = ChatGroq(
                    model=settings.GROQ_MODEL or "llama-3.3-70b-versatile",
                    api_key=settings.GROQ_API_KEY,
                    temperature=0.3,
                )
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
                response = await groq_llm.ainvoke(messages)
                ai_summary = response.content if response else None
                model_used = "groq"
                status = "done"

                # Extract token count if available
                if hasattr(response, "usage_metadata"):
                    tokens_used = response.usage_metadata.get("output_tokens", 0)

                await scheduler.schedule(
                    quickLog,
                    params={
                        "message": f"AI search summary generated via Groq for query: {query[:50]}",
                        "level": "success",
                        "urgency": "none",
                        "module": "DB",
                    },
                )
            except Exception as groq_error:
                await scheduler.schedule(
                    quickLog,
                    params={
                        "message": f"Groq summary failed, falling back to Ollama: {groq_error}",
                        "level": "warning",
                        "urgency": "moderate",
                        "module": "DB",
                    },
                )

        # Fallback to Ollama if Groq failed
        if not ai_summary:
            try:
                aclient = getAsyncClient()
                ai_summary = await asyncGenerateContent(
                    prompt=user_prompt,
                    system=system_prompt,
                    model="gemma4:e2b",
                    image=None,
                    aclient=aclient,
                )
                model_used = "ollama"
                status = "done"

                await scheduler.schedule(
                    quickLog,
                    params={
                        "message": f"AI search summary generated via Ollama for query: {query[:50]}",
                        "level": "success",
                        "urgency": "none",
                        "module": "DB",
                    },
                )
            except Exception as ollama_error:
                ai_summary = f"AI summary generation failed: {str(ollama_error)}"
                status = "failed"

                await scheduler.schedule(
                    quickLog,
                    params={
                        "message": f"Both Groq and Ollama failed for search summary: {ollama_error}",
                        "level": "error",
                        "urgency": "critical",
                        "module": "DB",
                    },
                )

        time_taken_sec = int(time.time() - start_time)

        # Update the search record
        now = datetime.now(timezone.utc).isoformat()
        history_db_manager.update(
            "searches",
            data={
                "ai_summary": ai_summary,
                "status": "done",
                "updated_at": now,
            },
            where={"id": search_id},
        )

        # Record in ai_summaries table
        ai_summary_id = str(uuid.uuid4())
        history_db_manager.insert(
            "ai_summaries",
            {
                "id": ai_summary_id,
                "workspace_id": workspace_id,
                "prompt": user_prompt[:500],  # Store first 500 chars of prompt
                "model": model_used or "unknown",
                "time_taken_sec": time_taken_sec,
                "status": status,
                "tokens_used": tokens_used,
                "original_test": query[
                    :200
                ],  # Note: column is "original_test" as per schema
                "summary": ai_summary[:1000] if ai_summary else None,
                "created_at": now,
            },
        )

        # Record in user_usage_history table
        history_id = str(uuid.uuid4())
        from main.src.history.history_tracker import compact_preview

        activity_preview = compact_preview(ai_summary or "Summary failed", max_chars=80)
        history_db_manager.insert(
            "user_usage_history",
            {
                "id": history_id,
                "user_id": user_id,
                "workspace_id": workspace_id,
                "activity": f"Generated AI search summary: {query}",
                "type": "ai_summary",
                "created_at": now,
                "last_seen": now,
                "actions": f"search_summary_{model_used}",
                "url": f"/search/{search_id}",
            },
        )

        # Broadcast via SSE
        await event_bus.broadcast(
            {
                "event": "search.ai_done",
                "search_id": search_id,
                "query": query,
                "ai_mode": {
                    "status": "done",
                    "ai_summary": ai_summary,
                    "model": model_used,
                    "time_taken_sec": time_taken_sec,
                },
            }
        )

        # ─── QUERY-BASED CACHING: Store summary in Redis for future searches ─────
        if r is not None and ai_summary:
            try:
                # Cache for 24 hours (86400 seconds)
                cache_ttl = 86400
                r.setex(cache_key, cache_ttl, ai_summary)
                await scheduler.schedule(
                    quickLog,
                    params={
                        "message": f"AI summary cached in Redis for query: {query} (TTL: {cache_ttl}s)",
                        "level": "info",
                        "urgency": "none",
                        "module": "DB",
                    },
                )
            except Exception as cache_error:
                await scheduler.schedule(
                    quickLog,
                    params={
                        "message": f"Failed to cache summary in Redis: {cache_error}",
                        "level": "warning",
                        "urgency": "none",
                        "module": "DB",
                    },
                )

        # ─── CLEANUP: Remove Redis processing lock ──────────────────────────────
        if r is not None:
            try:
                r.delete(processing_key)
            except Exception:
                pass  # Silently fail on cleanup errors

    def get_ai_summary(self, search_id: str) -> Dict[str, Any]:
        """
        ## Description

        Retrieves the AI summary for a given search ID. Returns the
        current status and summary text.

        ## Parameters

        - `search_id` (`str`)
          - Description: UUID of the search record.
          - Constraints: Must be a valid search ID.

        ## Returns

        `dict`

        Structure:

        ```json
        {
            "search_id": "...",
            "status": "processing|done",
            "ai_summary": "...",
            "ai_citations": "..."
        }
        ```
        """
        result = history_db_manager.fetch_one("searches", where={"id": search_id})
        if not result["success"] or not result["data"]:
            return {
                "search_id": search_id,
                "status": "not_found",
                "ai_summary": None,
                "ai_citations": None,
            }

        row = result["data"]
        return {
            "search_id": search_id,
            "status": row.get("status", "done"),
            "ai_summary": row.get("ai_summary"),
            "ai_citations": row.get("ai_citations"),
        }


# Module-level singleton
search_service = SearchService()
