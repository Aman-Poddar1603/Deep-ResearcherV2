"""
Orchestrator 2 — ReAct knowledge synthesizer.

Responsibilities:
  1. Filter + deduplicate gathered sources
  2. Chunk + embed into ChromaDB (via BG worker)
  3. Verify plan coverage via RAG retrieval
  4. Build the final artifact context prompt
"""

import json
import logging
import uuid
from typing import Any

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.prebuilt import ToolNode, create_react_agent
from langgraph.checkpoint.redis.aio import AsyncRedisSaver

from research.config import settings
from research.emitter import WSEmitter
from research.models import (
    ResearchContext,
    SystemProgressEvent,
)
from research.session import (
    update_session_status,
    is_stop_requested,
    get_redis,
)
from research.token_tracker import TokenTracker
from research.layer2.tools import (
    get_mcp_tools,
    extract_tool_token_count,
)
from research.layer2.rag import (
    retrieve_for_coverage_check,
    chunk_and_index,
)

logger = logging.getLogger(__name__)

_SYNTHESIZER_SYSTEM = """You are a knowledge synthesizer for a deep research project.
User: {username}. Personality: {ai_personality}.

Use the available MCP tools when you need fresh external evidence.
Wait for the tool output before proceeding. Do not guess or assume results.

Research topic: {cleaned_prompt}

Your tasks:
1. Analyse the gathered knowledge from all research steps.
2. Identify gaps, contradictions, or areas needing more information.
3. Use tools if needed to fill gaps.
4. Produce a clean, comprehensive synthesis of all knowledge.
5. Ensure every plan step is addressed.

Plan steps to cover:
{plan_steps}

Gathered knowledge summary:
{knowledge_summary}

Produce a final synthesis that will be used to write the research artifact."""


async def run_orchestrator2(
    context: ResearchContext,
    gathered_sources: list[dict],
    emitter: WSEmitter,
) -> dict:
    """
    Synthesizes gathered sources. Returns artifact_context dict for Groq artifact gen.
    """
    research_id = context.research_id

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

    # ── Index to ChromaDB via BG worker ───────────────────────────────────────
    await _schedule_chroma_indexing(research_id, unique_sources)

    await emitter.emit(
        SystemProgressEvent(
            research_id=research_id,
            message="Knowledge indexed. Running synthesis agent...",
            percent=88,
        )
    )

    # ── Setup agent ───────────────────────────────────────────────────────────
    redis_conn = await get_redis()
    checkpointer = AsyncRedisSaver(redis_client=redis_conn)
    await checkpointer.setup()
    graph_config: RunnableConfig = {
        "configurable": {"thread_id": f"orc2_{research_id}_{uuid.uuid4().hex[:8]}"},
        "callbacks": [],
    }

    mcp_tools = await get_mcp_tools()
    all_tools = list(mcp_tools)

    tracker = TokenTracker(
        emitter=emitter,
        research_id=research_id,
        step_index=99,
        model_type="ollama",
        source=f"ollama/{settings.OLLAMA_MODEL}",
    )

    llm = ChatOllama(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0.1,
    )

    tool_node = ToolNode(all_tools, handle_tool_errors=True)

    agent = create_react_agent(
        model=llm,
        tools=tool_node,
        checkpointer=checkpointer,
    )

    graph_config["callbacks"] = [tracker]

    plan_steps_str = "\n".join(
        f"- Step {s.step_index + 1}: {s.step_title}" for s in context.plan
    )
    knowledge_summary = _build_knowledge_summary(unique_sources)

    system_msg = _SYNTHESIZER_SYSTEM.format(
        username=context.username,
        ai_personality=context.ai_personality,
        cleaned_prompt=context.cleaned_prompt,
        plan_steps=plan_steps_str,
        knowledge_summary=knowledge_summary[:6000],
    )

    inputs = {
        "messages": [
            SystemMessage(content=system_msg),
            HumanMessage(
                content="Synthesize the gathered research and produce a comprehensive knowledge summary."
            ),
        ]
    }

    synthesis_text = ""
    async for event in agent.astream_events(inputs, config=graph_config, version="v2"):
        if await is_stop_requested(research_id):
            break

        kind = event["event"]
        name = event.get("name", "")

        if kind == "on_tool_end":
            tool_tokens = extract_tool_token_count(name, event["data"].get("output"))
            if tool_tokens > 0:
                await tracker.record_tool_tokens(tool_tokens)

        elif kind == "on_chain_end" and "agent" in name.lower():
            messages = event["data"].get("output", {}).get("messages", [])
            if messages:
                last = messages[-1]
                synthesis_text = getattr(last, "content", "") or ""

    # ── Coverage check ────────────────────────────────────────────────────────
    coverage_notes = []
    for step in context.plan:
        docs = retrieve_for_coverage_check(research_id, step.step_description)
        if docs:
            coverage_notes.append(
                f"Step {step.step_index + 1} ({step.step_title}): covered ({len(docs)} chunks)"
            )
        else:
            coverage_notes.append(
                f"Step {step.step_index + 1} ({step.step_title}): limited coverage"
            )

    logger.info("[orc2] Coverage check:\n%s", "\n".join(coverage_notes))

    # ── Build cited sources ───────────────────────────────────────────────────
    cited_sources = _build_citations(unique_sources)

    await emitter.emit(
        SystemProgressEvent(
            research_id=research_id,
            message="Synthesis complete. Generating artifact...",
            percent=92,
        )
    )

    # ── Persist research metadata via BG worker ───────────────────────────────
    await _persist_metadata(context, unique_sources)

    return {
        "username": context.username,
        "ai_personality": context.ai_personality,
        "system_prompt": context.system_prompt,
        "custom_prompt": context.custom_prompt,
        "research_template": context.research_template,
        "cleaned_prompt": context.cleaned_prompt,
        "cited_sources": cited_sources,
        "knowledge_summary": synthesis_text or knowledge_summary,
        "coverage_notes": "\n".join(coverage_notes),
        "title": context.title,
        "description": context.description,
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


def _build_knowledge_summary(sources: list[dict]) -> str:
    parts = []
    for i, s in enumerate(sources[:30]):
        tool = s.get("tool", "")
        if tool in ("agent_summary",):
            continue
        title = s.get("title", "")
        content = s.get("content", "")
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


async def _persist_metadata(context: ResearchContext, sources: list[dict]) -> None:
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

    await scheduler.schedule(
        researches_db_manager.insert,
        params={
            "table_name": "research_metadata",
            "data": {
                "id": str(uuid.uuid4()),
                "models": json.dumps(
                    {
                        "preprocess_ollama": settings.OLLAMA_MODEL,
                        "reasoner_groq": settings.GROQ_MODEL,
                        "embedding_primary_ollama": settings.OLLAMA_EMBED_MODEL,
                        "embedding_fallback_gemini": (
                            settings.GEMINI_EMBED_MODEL
                            if settings.GEMINI_API_KEY.strip()
                            else ""
                        ),
                    }
                ),
                "workspace_id": context.workspace_id,
                "research_id": context.research_id,
                "connected_bucket": "",
                "time_taken_sec": 0,
                "token_count": int(token_totals.get("grand_total", 0)),
                "num_api_calls": len(sources),
                "source_count": len(sources),
                "websites_count": len(website_sources),
                "file_count": len(file_sources),
                "citations": json.dumps(_build_citations(sources)),
                "exported": "",
                "status": True,
                "chats_referenced": "",
            },
        },
    )
