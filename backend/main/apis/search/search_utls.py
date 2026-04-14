"""
## Description

FastAPI router for the universal search API. Provides endpoints for
performing searches across all content types with pagination, AI mode
support, and search history tracking.

## Parameters

None (Module level)

## Returns

None (Module level)

## Side Effects

- Registers API routes under the `/search` prefix.
- Schedules background tasks for logging and AI generation.

## Debug Notes

- All search events are logged under the `["DB"]` module via quickLog.
- AI mode dispatches background work via the scheduler — the response
  is returned immediately with `status: "processing"`.
"""

import json
import uuid

from fastapi import APIRouter, HTTPException, Query, status

from main.src.search.search import search_service
from main.src.utils.DRLogger import quickLog
from main.src.utils.core.task_schedular import scheduler

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/", status_code=status.HTTP_200_OK)
async def search(
    q: str = Query(..., min_length=1, description="Raw search query"),
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=10, ge=1, le=50, description="Results per page"),
    ai_mode: bool = Query(default=False, description="Enable AI summary"),
    type_filter: str | None = Query(
        default=None,
        alias="typeFilter",
        description="Filter by type: workspace, chats, researches, scrapes, assets",
    ),
    workspace_id: str | None = Query(
        default=None,
        alias="workspaceId",
        description="Optional workspace context for history recording",
    ),
    user_id: str | None = Query(
        default=None,
        alias="userId",
        description="Optional user context for history recording",
    ),
) -> dict:
    """
    ## Description

    Main search endpoint. Queries all content databases, returns paginated
    results classified by type. Optionally triggers background AI summary.

    ## Parameters

    - `q` (`str`)
      - Description: The raw search query.
      - Constraints: Must be non-empty.
      - Example: `"deep learning"`

    - `page` (`int`)
      - Description: 1-based page number.
      - Constraints: >= 1. Default 1.

    - `size` (`int`)
      - Description: Results per page.
      - Constraints: 1-50. Default 10.

    - `ai_mode` (`bool`)
      - Description: When true, triggers background AI summary.
      - Constraints: Boolean. Default false.

    - `type_filter` (`str | None`)
      - Description: Filter results to a single content type.
      - Constraints: Must be valid type or None.

    ## Returns

    `dict`

    Structure:

    ```json
    {
        "search_id": "uuid",
        "query": "original query",
        "results": {
            "total_count": 42,
            "page": 1,
            "size": 10,
            "items": [...]
        },
        "ai_mode": {
            "status": "processing|done|disabled",
            "ai_summary": null
        }
    }
    ```
    """
    search_id = uuid.uuid4().hex

    # Log the search (BG)
    await scheduler.schedule(
        quickLog,
        params={
            "message": f"Search query received: '{q}' page={page} ai_mode={ai_mode}",
            "level": "info",
            "module": ["DB"],
        },
    )

    try:
        results = search_service.search_all(
            query=q,
            page=page,
            size=size,
            type_filter=type_filter,
        )
    except Exception as e:
        await scheduler.schedule(
            quickLog,
            params={
                "message": f"Search failed: {e}",
                "level": "error",
                "module": ["DB"],
                "urgency": "critical",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )

    # Build condensed results JSON for history (just type+id+title)
    results_summary = json.dumps(
        [
            {"type": item["type"], "id": item["id"], "title": item["title"]}
            for item in results["items"]
        ],
        ensure_ascii=False,
    )

    # Save search record in background
    await scheduler.schedule(
        search_service.save_search_record,
        params={
            "search_id": search_id,
            "query": q,
            "total_results": results["total_count"],
            "results_json": results_summary,
            "is_aimode": ai_mode,
        },
    )

    # AI mode: schedule background generation
    ai_status = "disabled"
    if ai_mode:
        ai_status = "processing"
        top_results = search_service.get_top_per_type(query=q, n=2)

        await scheduler.schedule(
            search_service.generate_ai_summary,
            params={
                "search_id": search_id,
                "query": q,
                "top_results": top_results,
                "workspace_id": workspace_id,
                "user_id": user_id,
            },
        )

    return {
        "search_id": search_id,
        "query": q,
        "results": results,
        "ai_mode": {
            "status": ai_status,
            "ai_summary": None,
        },
    }


@router.get("/{search_id}/ai", status_code=status.HTTP_200_OK)
async def get_search_ai(
    search_id: str,
    workspace_id: str | None = Query(
        default=None,
        alias="workspaceId",
        description="Optional workspace context for history recording",
    ),
    user_id: str | None = Query(
        default=None,
        alias="userId",
        description="Optional user context for history recording",
    ),
) -> dict:
    """
    ## Description

    Retrieves the AI summary for a previously executed search. If the
    AI generation is still running, returns `status: "processing"`.
    Can also be used to trigger a late AI generation request.

    ## Parameters

    - `search_id` (`str`)
      - Description: UUID of the search record.
      - Constraints: Must be a valid search ID.
      - Example: `"abc123def456"`

    ## Returns

    `dict`

    Structure:

    ```json
    {
        "search_id": "...",
        "status": "processing|done|not_found",
        "ai_summary": "...",
        "ai_citations": "..."
    }
    ```
    """
    await scheduler.schedule(
        quickLog,
        params={
            "message": f"AI summary requested for search: {search_id}",
            "level": "info",
            "module": ["DB"],
        },
    )

    result = search_service.get_ai_summary(search_id)

    if result["status"] == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Search record '{search_id}' not found",
        )

    # If no AI summary yet and status is 'done' (was a non-AI search),
    # trigger late AI generation
    if result["status"] == "done" and result["ai_summary"] is None:
        # Fetch the original query from the search record
        from main.src.store.DBManager import history_db_manager

        record = history_db_manager.fetch_one("searches", where={"id": search_id})
        if record["success"] and record["data"]:
            original_query = record["data"].get("query", "")
            if original_query:
                # Mark as processing
                history_db_manager.update(
                    "searches",
                    data={"status": "processing"},
                    where={"id": search_id},
                )

                top_results = search_service.get_top_per_type(query=original_query, n=2)
                await scheduler.schedule(
                    search_service.generate_ai_summary,
                    params={
                        "search_id": search_id,
                        "query": original_query,
                        "top_results": top_results,
                        "workspace_id": workspace_id,
                        "user_id": user_id,
                    },
                )
                result["status"] = "processing"

    return result
