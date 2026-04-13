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
    SynthesisAnalysisStartedEvent,
    SynthesisAnalysisProgressEvent,
    ThinkChunkEvent,
    ThinkDoneEvent,
    ToolCalledEvent,
    ToolResultEvent,
    ReactReasonEvent,
    ReactActEvent,
    ReactObserveEvent,
    ReActEvent,
    ChainOfThoughtEvent,
    ThinkEvent,
    StreamEvent,
    ToolQueryEvent,
    ToolOutputEvent,
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
    parse_tool_output,
    summarise_tool_output,
)
from research.layer2.rag import (
    retrieve_for_coverage_check,
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
    knowledge_summary = _build_knowledge_summary(
        unique_sources, extended_mode=context.extended_mode
    )

    system_msg = _SYNTHESIZER_SYSTEM.format(
        username=context.username,
        ai_personality=context.ai_personality,
        cleaned_prompt=context.cleaned_prompt,
        plan_steps=plan_steps_str,
        knowledge_summary=(
            knowledge_summary if context.extended_mode else knowledge_summary[:6000]
        ),
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
    _synth_thought: list[str] = []
    _synth_in_tool: bool = False

    async for event in agent.astream_events(inputs, config=graph_config, version="v2"):
        if await is_stop_requested(research_id):
            break

        kind = event["event"]
        name = event.get("name", "")
        synth_step = 99  # synthesis phase marker

        if kind == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if chunk and chunk.content:
                token = chunk.content if isinstance(chunk.content, str) else ""
                if not token:
                    continue
                _synth_thought.append(token)
                if _synth_in_tool:
                    await emitter.emit(
                        ChainOfThoughtEvent(
                            research_id=research_id,
                            step_index=synth_step,
                            token=token,
                        )
                    )
                    await emitter.emit(
                        ReActEvent(
                            research_id=research_id,
                            step_index=synth_step,
                            sub_type="reason",
                            data={"token": token},
                        )
                    )
                else:
                    await emitter.emit(
                        StreamEvent(
                            research_id=research_id,
                            step_index=synth_step,
                            token=token,
                        )
                    )
                    await emitter.emit(
                        ThinkChunkEvent(
                            research_id=research_id,
                            text=token,
                            step_index=synth_step,
                        )
                    )

        elif kind == "on_tool_start":
            _synth_in_tool = True
            tool_name = name
            tool_args = event["data"].get("input", {})
            safe_args = (
                tool_args if isinstance(tool_args, dict) else {"input": str(tool_args)}
            )

            if _synth_thought:
                full_thought = "".join(_synth_thought)
                await emitter.emit(
                    ThinkEvent(
                        research_id=research_id,
                        step_index=synth_step,
                        thought=full_thought,
                    )
                )
                await emitter.emit(
                    ReactReasonEvent(
                        research_id=research_id,
                        step_index=synth_step,
                        thought=full_thought,
                    )
                )
                _synth_thought.clear()

            await emitter.emit(
                ToolQueryEvent(
                    research_id=research_id,
                    step_index=synth_step,
                    tool_name=tool_name,
                    args=safe_args,
                )
            )
            await emitter.emit(
                ToolCalledEvent(
                    research_id=research_id,
                    tool_name=tool_name,
                    args=safe_args,
                    step_index=synth_step,
                )
            )
            await emitter.emit(
                ReactActEvent(
                    research_id=research_id,
                    step_index=synth_step,
                    tool_name=tool_name,
                )
            )
            await emitter.emit(
                ReActEvent(
                    research_id=research_id,
                    step_index=synth_step,
                    sub_type="act",
                    data={"tool_name": tool_name, "args": safe_args},
                )
            )

        elif kind == "on_tool_end":
            _synth_in_tool = False
            tool_name = name
            output = event["data"].get("output")
            tool_tokens = extract_tool_token_count(tool_name, output)
            if tool_tokens > 0:
                await tracker.record_tool_tokens(tool_tokens)

            summary = summarise_tool_output(tool_name, output)
            parsed = parse_tool_output(tool_name, output)
            compact = [
                {
                    "tool": str(i.get("tool", ""))[:120],
                    "url": str(i.get("url", ""))[:700],
                    "title": str(i.get("title", ""))[:300],
                    "summary": str(i.get("description", ""))[:600],
                }
                for i in parsed[:6]
            ]

            await emitter.emit(
                ToolOutputEvent(
                    research_id=research_id,
                    step_index=synth_step,
                    tool_name=tool_name,
                    summary=summary,
                    result_payload=compact,
                )
            )
            await emitter.emit(
                ToolResultEvent(
                    research_id=research_id,
                    tool_name=tool_name,
                    result_summary=summary,
                    step_index=synth_step,
                    result_payload=compact,
                )
            )
            await emitter.emit(
                ReactObserveEvent(
                    research_id=research_id,
                    step_index=synth_step,
                    observation_summary=summary,
                )
            )
            await emitter.emit(
                ReActEvent(
                    research_id=research_id,
                    step_index=synth_step,
                    sub_type="observe",
                    data={"tool_name": tool_name, "summary": summary},
                )
            )

        elif kind == "on_chain_end" and "agent" in name.lower():
            messages = event["data"].get("output", {}).get("messages", [])
            if messages:
                last = messages[-1]
                synthesis_text = getattr(last, "content", "") or ""
            await emitter.emit(
                ThinkDoneEvent(
                    research_id=research_id,
                    step_index=synth_step,
                )
            )
            await emitter.emit(
                ReActEvent(
                    research_id=research_id,
                    step_index=synth_step,
                    sub_type="done",
                    data={"summary": synthesis_text[:500] if synthesis_text else ""},
                )
            )

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
    await _persist_metadata(context, unique_sources)

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
