"""
Stop manager.

Sets the Redis stop flag, then on flush:
  - Saves partial gathered sources to ChromaDB (marked partial=True)
  - Saves partial research record to DB
  - Updates session status to "stopped"
  - Emits stop.saved WS event
"""

import logging
import uuid

from research.emitter import WSEmitter
from research.models import (
    StopRequestedEvent,
    StopFlushingEvent,
    StopSavedEvent,
)
from research.session import (
    set_stop_flag,
    update_session_status,
    load_context,
)
from research.layer2.rag import chunk_and_index

logger = logging.getLogger(__name__)


async def request_stop(research_id: str, emitter: WSEmitter) -> None:
    """
    Called by the WS router when the frontend sends stop.request.
    Sets the Redis stop flag — the running agent loops will detect it.
    """
    await set_stop_flag(research_id)
    await emitter.emit(StopRequestedEvent(research_id=research_id))
    logger.info("[stop] Stop requested for %s", research_id)


async def flush_partial_research(
    research_id: str,
    gathered_sources: list[dict],
    emitter: WSEmitter,
) -> None:
    """
    Called when a stop is detected after the agent loop exits.
    Persists whatever was gathered so it can be reused in future researches.
    """
    await emitter.emit(
        StopFlushingEvent(
            research_id=research_id,
            message="Saving partial research data...",
        )
    )

    context = await load_context(research_id)
    workspace_id = (context or {}).get("workspace_id", "")

    vectors_saved = 0
    sources_saved = 0

    from main.src.utils.core.task_schedular import scheduler
    from main.src.store.DBManager import research_db_manager, history_db_manager

    for s in gathered_sources:
        tool = s.get("tool", "unknown")
        url = s.get("url", "")
        content = s.get("content", "")
        step_index = s.get("step_index", 0)

        # Skip image URLs — no text to embed
        if tool == "image_search_tool":
            sources_saved += 1
            continue

        if content and len(content) > 50:
            n = chunk_and_index(
                research_id=research_id,
                text=content,
                source_url=url or "partial",
                step_index=step_index,
                partial=True,
            )
            vectors_saved += n

        await scheduler.schedule(
            research_db_manager.insert,
            params={
                "table": "research_sources",
                "data": {
                    "id": str(uuid.uuid4()),
                    "research_id": research_id,
                    "source_type": tool,
                    "source_url": url,
                    "source_content": content[:4000],
                    "source_citations": "",
                    "source_vector_id": "",
                },
            },
        )
        sources_saved += 1

    # Mark research as stopped in DB
    await scheduler.schedule(
        history_db_manager.insert,
        params={
            "table": "research_history",
            "data": {
                "id": str(uuid.uuid4()),
                "research_id": research_id,
                "workspace_id": workspace_id,
                "activity": "research_stopped",
                "status": "stopped",
                "url": "",
            },
        },
    )

    await update_session_status(research_id, "stopped")
    await emitter.emit(
        StopSavedEvent(
            research_id=research_id,
            partial_sources_count=sources_saved,
            chroma_vectors_saved=vectors_saved,
        )
    )
    logger.info(
        "[stop] Partial flush complete — %d sources, %d vectors for %s",
        sources_saved,
        vectors_saved,
        research_id,
    )
