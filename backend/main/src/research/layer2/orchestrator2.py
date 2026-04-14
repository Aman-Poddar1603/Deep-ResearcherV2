"""Orchestrator 2 — fast artifact context builder.

Responsibilities:
    1. Filter + deduplicate gathered sources
    2. Chunk + embed into ChromaDB (via BG worker)
    3. Build a concise synthesis context without a second long LLM pass
    4. Return artifact-ready context immediately
"""

import json
import logging
import time
import uuid
from typing import Any

from research.config import settings
from research.emitter import WSEmitter
from research.models import (
    ResearchContext,
    SystemProgressEvent,
    SynthesisAnalysisStartedEvent,
    SynthesisAnalysisProgressEvent,
)
from research.session import (
    update_session_status,
    is_stop_requested,
)
from research.layer2.rag import (
    chunk_and_index,
)
from research.layer2.temp_files import (
    ensure_temp_research_dir,
    init_synthesis_file,
    append_synthesis_entry,
    read_synthesis_md,
    write_citations_md,
    read_citations_md,
)

logger = logging.getLogger(__name__)


async def run_orchestrator2(
    context: ResearchContext,
    gathered_sources: list[dict],
    emitter: WSEmitter,
) -> dict:
    """
    Build artifact context from gathered sources and return it for final artifact generation.
    """
    research_id = context.research_id
    synth_started_at = time.monotonic()

    await update_session_status(research_id, "synthesizing")
    await emitter.emit(
        SystemProgressEvent(
            research_id=research_id,
            message="Synthesizing gathered knowledge...",
            percent=86,
        )
    )

    # ── Dedup sources ─────────────────────────────────────────────────────────
    unique_sources = _dedup_sources(gathered_sources)
    logger.info("[orc2] Unique sources after dedup: %d", len(unique_sources))

    temp_dir = ensure_temp_research_dir(research_id, context.temp_dir)
    context.temp_dir = temp_dir

    total_sources = len(unique_sources)
    await emitter.emit(
        SynthesisAnalysisStartedEvent(
            research_id=research_id,
            total_sources=total_sources,
        )
    )
    await emitter.emit(
        SystemProgressEvent(
            research_id=research_id,
            message="Analyzing gathered sources and creating context...",
            percent=87,
        )
    )

    init_synthesis_file(temp_dir=temp_dir, total_sources=total_sources)
    if total_sources > 0:
        for idx, source in enumerate(unique_sources, start=1):
            append_synthesis_entry(
                temp_dir=temp_dir,
                source=source,
                analyzed_count=idx,
                total_sources=total_sources,
                extended_mode=context.extended_mode,
            )

            should_emit_progress = (
                idx % max(1, settings.SYNTHESIS_UPDATE_INTERVAL) == 0
                or idx == total_sources
            )
            if should_emit_progress:
                progress_pct = 87 + int((idx / total_sources) * 3)
                await emitter.emit(
                    SynthesisAnalysisProgressEvent(
                        research_id=research_id,
                        sources_analyzed=idx,
                        total_sources=total_sources,
                        percent=min(progress_pct, 90),
                        synthesis_preview=read_synthesis_md(temp_dir)[
                            -settings.SYNTHESIS_PREVIEW_CHARS :
                        ],
                    )
                )

    # ── Index to ChromaDB via BG worker ───────────────────────────────────────
    await _schedule_chroma_indexing(research_id, unique_sources)

    await emitter.emit(
        SystemProgressEvent(
            research_id=research_id,
            message="Knowledge indexed. Preparing direct artifact context...",
            percent=88,
        )
    )

    knowledge_summary = _build_knowledge_summary(
        unique_sources, extended_mode=context.extended_mode
    )
    synthesis_text = knowledge_summary

    # ── Coverage notes (fast path, no second LLM pass) ───────────────────────
    coverage_notes = [
        f"Step {step.step_index + 1} ({step.step_title}): included from gathered sources"
        for step in context.plan
    ]

    logger.info("[orc2] Fast coverage notes prepared for %d steps", len(context.plan))

    # ── Build cited sources ───────────────────────────────────────────────────
    cited_sources = _build_citations(unique_sources)
    write_citations_md(temp_dir=temp_dir, citations=cited_sources)
    synthesis_md = read_synthesis_md(temp_dir)
    citations_md = read_citations_md(temp_dir)

    await emitter.emit(
        SystemProgressEvent(
            research_id=research_id,
            message="Synthesis complete. Generating artifact...",
            percent=92,
        )
    )

    # ── Persist research metadata via BG worker ───────────────────────────────
    elapsed_seconds = max(0, int(time.monotonic() - synth_started_at))
    await _persist_metadata(context, unique_sources, elapsed_seconds)

    return {
        "username": context.username,
        "ai_personality": context.ai_personality,
        "system_prompt": context.system_prompt,
        "custom_prompt": context.custom_prompt,
        "research_template": context.research_template,
        "cleaned_prompt": context.cleaned_prompt,
        "cited_sources": cited_sources,
        "synthesis_md": synthesis_md,
        "citations_md": citations_md,
        "temp_dir": temp_dir,
        "knowledge_summary": synthesis_text or knowledge_summary,
        "coverage_notes": "\n".join(coverage_notes),
        "title": context.title,
        "description": context.description,
        "extended_mode": context.extended_mode,
        "artifact_step_index": max(0, len(context.plan) - 1),
    }


def _dedup_sources(sources: list[dict]) -> list[dict]:
    """
    Sources are already normalised dicts from parse_tool_output:
    {url, content, title, description, tool, step_index, summary}
    Dedup by url then by content hash.
    """
    seen_urls: set[str] = set()
    seen_hashes: set[int] = set()
    unique = []
    for s in sources:
        url = s.get("url", "")
        content_hash = hash(s.get("content", "")[:500])
        if url and url in seen_urls:
            continue
        if content_hash in seen_hashes:
            continue
        if url:
            seen_urls.add(url)
        seen_hashes.add(content_hash)
        unique.append(s)
    return unique


def _build_knowledge_summary(
    sources: list[dict],
    extended_mode: bool = False,
) -> str:
    """
    ## Description

    Build a textual knowledge summary from gathered sources.
    In normal mode, limits to 30 sources and 400 chars per content snippet.
    In extended mode, includes all sources with full content.

    ## Parameters

    - `sources` (`list[dict]`)
      - Description: Deduplicated source dicts.
      - Constraints: Each dict should have tool/title/content/description/url keys.

    - `extended_mode` (`bool`)
      - Description: When True, removes all source count and content length limits.
      - Constraints: Must be a boolean.

    ## Returns

    `str` — Concatenated knowledge summary text.
    """
    parts = []
    source_list = sources if extended_mode else sources[:30]
    for i, s in enumerate(source_list):
        tool = s.get("tool", "")
        if tool in ("agent_summary",):
            continue
        title = s.get("title", "")
        content = s.get("content", "")
        if extended_mode:
            snippet = content if content else s.get("description", "")
        else:
            snippet = content[:400] if content else s.get("description", "")[:400]
        if snippet:
            label = title or s.get("url", f"source {i+1}")
            parts.append(f"[Source {i+1}] {label}\n{snippet}")
    return "\n\n".join(parts)


def _build_citations(sources: list[dict]) -> list[dict]:
    citations = []
    idx = 1
    seen: set[str] = set()
    for s in sources:
        url = s.get("url", "")
        tool = s.get("tool", "")
        # Skip image URLs and agent summaries in citations
        if not url or tool in ("image_search_tool", "agent_summary"):
            continue
        if url in seen:
            continue
        seen.add(url)
        citations.append(
            {
                "index": idx,
                "url": url,
                "title": s.get("title", url),
            }
        )
        idx += 1
    return citations


async def _schedule_chroma_indexing(research_id: str, sources: list[dict]) -> None:
    """Schedule ChromaDB indexing for all sources via BG worker."""
    from main.src.utils.core.task_schedular import scheduler

    for s in sources:
        tool = s.get("tool", "")
        content = s.get("content", "")
        url = s.get("url", "source")
        step_index = s.get("step_index", 0)

        # Skip image URLs — no text content to embed
        if tool == "image_search_tool":
            continue
        if not content or len(content) < 50:
            continue

        await scheduler.schedule(
            chunk_and_index,
            params={
                "research_id": research_id,
                "text": content,
                "source_url": url,
                "step_index": step_index,
                "partial": False,
            },
        )


async def _persist_metadata(
    context: ResearchContext,
    sources: list[dict],
    elapsed_seconds: int,
) -> None:
    from main.src.utils.core.task_schedular import scheduler
    from main.src.store.DBManager import researches_db_manager
    from research.session import get_token_totals

    website_tools = {
        "web_search",
        "read_webpages",
        "scrape_single_url",
        "search_urls_tool",
        "youtube_search",
    }
    file_tools = {"process_docs"}

    website_sources = [s for s in sources if s.get("tool") in website_tools]
    file_sources = [s for s in sources if s.get("tool") in file_tools]
    token_totals = await get_token_totals(context.research_id)

    tool_invocation_count = len(
        [s for s in sources if s.get("tool") not in ("", "agent_summary")]
    )

    metadata_payload = {
        "models": json.dumps(
            {
                "preprocess_ollama": settings.OLLAMA_MODEL,
                "reasoner_groq": settings.GROQ_MODEL,
                "artifact_primary_gemini": (
                    settings.GEMINI_ARTIFACT_MODEL
                    if settings.GEMINI_API_KEY.strip()
                    else ""
                ),
                "artifact_fallback_ollama": settings.OLLAMA_MODEL,
                "embedding_primary_ollama": settings.OLLAMA_EMBED_MODEL,
                "embedding_fallback_gemini": (
                    settings.GEMINI_EMBED_MODEL
                    if settings.GEMINI_API_KEY.strip()
                    else ""
                ),
            },
            ensure_ascii=True,
        ),
        "workspace_id": context.workspace_id,
        "research_id": context.research_id,
        "connected_bucket": "",
        "time_taken_sec": max(0, int(elapsed_seconds)),
        "token_count": int(token_totals.get("grand_total", 0)),
        "num_api_calls": tool_invocation_count,
        "source_count": len(sources),
        "websites_count": len(website_sources),
        "file_count": len(file_sources),
        "citations": json.dumps(_build_citations(sources), ensure_ascii=True),
        "exported": "false",
        "status": True,
        "chats_referenced": "[]",
    }

    existing = researches_db_manager.fetch_one(
        "research_metadata",
        where={"research_id": context.research_id},
    )
    existing_row = existing.get("data") if existing.get("success") else None

    if existing_row and existing_row.get("id"):
        await scheduler.schedule(
            researches_db_manager.update,
            params={
                "table_name": "research_metadata",
                "data": metadata_payload,
                "where": {"id": existing_row.get("id")},
            },
        )
        return

    await scheduler.schedule(
        researches_db_manager.insert,
        params={
            "table_name": "research_metadata",
            "data": {
                "id": str(uuid.uuid4()),
                **metadata_payload,
            },
        },
    )
