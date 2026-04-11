"""
Orchestrator 1 — ReAct knowledge gatherer.

Uses LangGraph create_react_agent with:
    - ChatOllama as the reasoner
    - MCP tools for external gathering (RAG not bound here)
  - RedisSaver as the LangGraph checkpointer
  - Full astream_events streaming → WS events

Iterates over every plan step. At each step:
  1. Emits plan.step_started
  2. Runs the ReAct agent streaming think/tool/observe events
  3. Checks stop flag between steps
  4. Emits plan.step_completed
  5. Offloads source persistence to BG worker
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
    PlanStep,
    PlanStepStartedEvent,
    PlanStepCompletedEvent,
    PlanStepFailedEvent,
    PlanAllDoneEvent,
    ThinkChunkEvent,
    ThinkDoneEvent,
    ToolCalledEvent,
    ToolResultEvent,
    ToolErrorEvent,
    ReactReasonEvent,
    ReactActEvent,
    ReactObserveEvent,
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
    parse_tool_output,
    summarise_tool_output,
)
from research.layer2.temp_files import (
    ensure_temp_research_dir,
    append_step_findings,
    step_findings_path,
)

logger = logging.getLogger(__name__)

_GATHERER_SYSTEM = """You are a deep research agent executing a structured research plan.
User: {username}. Personality: {ai_personality}.

You follow the ReAct loop — think step by step, choose a tool, observe the result, reason again.
You must use external MCP tools (web/video/image/document/url tools) to gather evidence.

Wait for the tool output before proceeding. Do not guess or assume results.

Available tools in this step:
{available_tools}

Tool policy:
1. Call at least one MCP tool before finalizing the step.
2. Prefer multiple independent MCP sources for better coverage.
3. Do not skip tool usage.

Always think out loud. Your reasoning trace is shown to the user.

Current plan step ({step_index}/{total_steps}):
Title: {step_title}
Description: {step_description}
Suggested tools: {suggested_tools}

Research topic: {cleaned_prompt}

Gather comprehensive, high-quality knowledge for this step. Use multiple sources.
When done, summarise what you found in a clear paragraph."""


def _build_system_message(
    ctx: ResearchContext,
    step: PlanStep,
    total: int,
    available_tools: list[str],
) -> str:
    return _GATHERER_SYSTEM.format(
        username=ctx.username,
        ai_personality=ctx.ai_personality,
        step_index=step.step_index + 1,
        total_steps=total,
        step_title=step.step_title,
        step_description=step.step_description,
        suggested_tools=", ".join(step.suggested_tools) or "any",
        cleaned_prompt=ctx.cleaned_prompt,
        available_tools=", ".join(available_tools) or "none",
    )


def _compact_tool_payload(
    parsed: list[dict[str, Any]],
    extended_mode: bool = False,
) -> list[dict[str, Any]]:
    """
    ## Description

    Compact parsed tool output for WS event payloads.
    In normal mode, limits items and truncates fields.
    In extended mode, passes everything through without truncation.

    ## Parameters

    - `parsed` (`list[dict[str, Any]]`)
      - Description: Parsed source dicts from `parse_tool_output`.
      - Constraints: Each dict should have tool/url/title/description/content keys.

    - `extended_mode` (`bool`)
      - Description: When True, removes all item caps and content truncation.
      - Constraints: Must be a boolean.
      - Example: True

    ## Returns

    `list[dict[str, Any]]`

    Structure:

    ```json
    [{"tool": "str", "url": "str", "title": "str", "description": "str", "content": "str"}]
    ```
    """
    items_to_process = parsed if extended_mode else parsed[:8]
    compact: list[dict[str, Any]] = []
    for item in items_to_process:
        if not isinstance(item, dict):
            continue

        if extended_mode:
            compact_item = {
                "tool": str(item.get("tool", "")),
                "url": str(item.get("url", "")),
                "title": str(item.get("title", "")),
                "description": str(item.get("description", "")),
                "content": str(item.get("content", "")),
            }
        else:
            compact_item = {
                "tool": str(item.get("tool", ""))[:120],
                "url": str(item.get("url", ""))[:700],
                "title": str(item.get("title", ""))[:300],
                "description": str(item.get("description", ""))[:1200],
                "content": str(item.get("content", ""))[:2000],
            }
        compact.append(compact_item)
    return compact


async def run_orchestrator1(
    context: ResearchContext,
    emitter: WSEmitter,
    gathered_sources: list[dict],
) -> list[dict]:
    """
    Runs all plan steps. gathered_sources is mutated in-place.
    Returns the list of gathered source dicts for Orc2.
    """
    research_id = context.research_id
    total_steps = len(context.plan)
    temp_dir = ensure_temp_research_dir(research_id, context.temp_dir)
    context.temp_dir = temp_dir

    # ── LangGraph checkpointer (Redis) ────────────────────────────────────────
    redis_conn = await get_redis()
    checkpointer = AsyncRedisSaver(redis_client=redis_conn)
    await checkpointer.setup()
    base_thread_id = f"orc1_{research_id}"

    # ── MCP tools (external gathering) ───────────────────────────────────────
    mcp_tools = await get_mcp_tools()
    if not mcp_tools:
        raise RuntimeError(
            "No MCP tools loaded from remote server. Aborting to avoid rag-only research."
        )

    # ── LLM ───────────────────────────────────────────────────────────────────
    step_tracker = TokenTracker(
        emitter=emitter,
        research_id=research_id,
        step_index=0,
        model_type="ollama",
        source=f"ollama/{settings.OLLAMA_MODEL}",
    )

    llm = ChatOllama(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0.1,
    )

    # ── Iterate steps ─────────────────────────────────────────────────────────
    for step in context.plan:
        # Stop check before each step
        if await is_stop_requested(research_id):
            logger.info("[orc1] Stop flag detected before step %d", step.step_index)
            break

        step_idx = step.step_index
        current_tracker = step_tracker.clone(step_idx)

        await update_session_status(research_id, "researching", current_step=step_idx)
        await emitter.emit(
            PlanStepStartedEvent(
                research_id=research_id,
                step_index=step_idx,
                step_title=step.step_title,
                total_steps=total_steps,
            )
        )

        try:
            step_tools = list(mcp_tools)

            available_tool_names = [
                getattr(tool, "name", "")
                for tool in step_tools
                if getattr(tool, "name", "")
            ]

            step_sources = await _run_step(
                step=step,
                context=context,
                total_steps=total_steps,
                step_tools=step_tools,
                available_tool_names=available_tool_names,
                llm=llm,
                checkpointer=checkpointer,
                thread_id=f"{base_thread_id}_step_{step_idx}_{uuid.uuid4().hex[:8]}",
                emitter=emitter,
                tracker=current_tracker,
                research_id=research_id,
                extended_mode=context.extended_mode,
            )

            try:
                append_step_findings(
                    temp_dir=temp_dir,
                    step_index=step_idx,
                    sources=step_sources,
                    extended_mode=context.extended_mode,
                )
            except Exception as exc:
                logger.warning(
                    "[orc1] Failed writing step findings markdown for step %s: %s",
                    step_idx,
                    exc,
                )

            gathered_sources.extend(step_sources)

            # Persist sources via BG worker
            await _persist_step_sources(
                research_id,
                context.workspace_id,
                step_idx,
                step_sources,
                temp_dir,
                extended_mode=context.extended_mode,
            )

            summary = (
                step_sources[-1].get("summary", f"Completed {step.step_title}")
                if step_sources
                else f"Completed {step.step_title}"
            )
            await emitter.emit(
                PlanStepCompletedEvent(
                    research_id=research_id,
                    step_index=step_idx,
                    step_title=step.step_title,
                    summary=summary,
                )
            )

            progress_pct = 60 + int((step_idx + 1) / total_steps * 25)
            await emitter.emit(
                SystemProgressEvent(
                    research_id=research_id,
                    message=f"Step {step_idx + 1}/{total_steps} complete: {step.step_title}",
                    percent=progress_pct,
                )
            )

        except Exception as exc:
            logger.exception("[orc1] Step %d failed: %s", step_idx, exc)
            await emitter.emit(
                PlanStepFailedEvent(
                    research_id=research_id,
                    step_index=step_idx,
                    error=str(exc),
                )
            )

    await emitter.emit(
        PlanAllDoneEvent(
            research_id=research_id,
            total_steps=total_steps,
            sources_count=len(gathered_sources),
        )
    )

    return gathered_sources


async def _run_step(
    step: PlanStep,
    context: ResearchContext,
    total_steps: int,
    step_tools: list,
    available_tool_names: list[str],
    llm: ChatOllama,
    checkpointer,
    thread_id: str,
    emitter: WSEmitter,
    tracker: TokenTracker,
    research_id: str,
    extended_mode: bool = False,
) -> list[dict]:
    """Run a single ReAct step. Returns list of source dicts collected."""
    system_msg = _build_system_message(
        context,
        step,
        total_steps,
        available_tool_names,
    )

    tool_node = ToolNode(step_tools, handle_tool_errors=True)

    agent = create_react_agent(
        model=llm,
        tools=tool_node,
        checkpointer=checkpointer,
    )

    step_graph_config: RunnableConfig = {
        "configurable": {"thread_id": thread_id},
        "callbacks": [tracker],
    }

    inputs = {
        "messages": [
            SystemMessage(content=system_msg),
            HumanMessage(
                content=f"Execute plan step: {step.step_title}\n\n{step.step_description}"
            ),
        ]
    }

    step_sources: list[dict] = []
    final_summary = ""

    async for event in agent.astream_events(
        inputs,
        config=step_graph_config,
        version="v2",
    ):
        # Stop check inside step too
        if await is_stop_requested(research_id):
            logger.info("[orc1] Stop flag detected mid-step %d", step.step_index)
            break

        kind = event["event"]
        name = event.get("name", "")

        if kind == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if chunk and chunk.content:
                token = chunk.content if isinstance(chunk.content, str) else ""
                if token:
                    await emitter.emit(
                        ThinkChunkEvent(
                            research_id=research_id,
                            text=token,
                            step_index=step.step_index,
                        )
                    )
                    # await emitter.emit(
                    #     ReactReasonEvent(
                    #         research_id=research_id,
                    #         step_index=step.step_index,
                    #         thought=token,
                    #     )
                    # )

        elif kind == "on_tool_start":
            tool_name = name
            tool_args = event["data"].get("input", {})
            await emitter.emit(
                ToolCalledEvent(
                    research_id=research_id,
                    tool_name=tool_name,
                    args=(
                        tool_args
                        if isinstance(tool_args, dict)
                        else {"input": str(tool_args)}
                    ),
                    step_index=step.step_index,
                )
            )
            # await emitter.emit(
            #     ReactActEvent(
            #         research_id=research_id,
            #         step_index=step.step_index,
            #         tool_name=tool_name,
            #     )
            # )

        elif kind == "on_tool_end":
            tool_name = name
            output = event["data"].get("output")

            # Extract tokens from tools that use Ollama internally
            tool_tokens = extract_tool_token_count(tool_name, output)
            if tool_tokens > 0:
                await tracker.record_tool_tokens(tool_tokens)

            summary = summarise_tool_output(tool_name, output)
            parsed = parse_tool_output(tool_name, output)

            await emitter.emit(
                ToolResultEvent(
                    research_id=research_id,
                    tool_name=tool_name,
                    result_summary=summary,
                    step_index=step.step_index,
                    result_payload=_compact_tool_payload(parsed, extended_mode=extended_mode),
                )
            )
            # await emitter.emit(
            #     ReactObserveEvent(
            #         research_id=research_id,
            #         step_index=step.step_index,
            #         observation_summary=summary,
            #     )
            # )

            # Collect normalised sources — one entry per parsed item
            for item in parsed:
                step_sources.append(
                    {
                        "tool": item.get("tool", tool_name),
                        "url": item["url"],
                        "content": item["content"],
                        "title": item["title"],
                        "description": item["description"],
                        "summary": summary,
                        "step_index": step.step_index,
                    }
                )

        elif kind == "on_chain_end" and "agent" in name.lower():
            messages = event["data"].get("output", {}).get("messages", [])
            if messages:
                last = messages[-1]
                final_summary = getattr(last, "content", "") or ""
            await emitter.emit(
                ThinkDoneEvent(
                    research_id=research_id,
                    step_index=step.step_index,
                )
            )

    # Ensure at least one external MCP source exists for this step.
    if not any(
        s.get("tool") not in ("agent_summary", "rag_search") for s in step_sources
    ):
        fallback_sources = await _force_single_mcp_call(
            tools=step_tools,
            step=step,
            context=context,
            emitter=emitter,
            research_id=research_id,
        )
        step_sources.extend(fallback_sources)

    if final_summary:
        step_sources.append(
            {
                "summary": final_summary,
                "step_index": step.step_index,
                "tool": "agent_summary",
            }
        )

    return step_sources


def _tool_input_payload(tool: Any, step: PlanStep, context: ResearchContext) -> Any:
    """Build a robust payload for MCP tools using args schema when available."""
    query = (
        f"{context.cleaned_prompt}\n"
        f"Focus: {step.step_title}\n"
        f"Task: {step.step_description}"
    )
    primary_url = context.sources[0] if context.sources else ""

    args_schema = getattr(tool, "args_schema", None)
    fields = (
        list(getattr(args_schema, "model_fields", {}).keys()) if args_schema else []
    )
    if not fields:
        return {"query": query}

    if len(fields) == 1:
        return {fields[0]: query}

    payload: dict[str, Any] = {}
    for field in fields:
        key = field.lower()
        if key in {
            "query",
            "q",
            "search_query",
            "search",
            "topic",
            "prompt",
            "question",
            "text",
            "input",
            "keyword",
            "keywords",
        }:
            payload[field] = query
        elif "url" in key:
            payload[field] = primary_url
        elif "limit" in key or "max" in key or "top_k" in key:
            payload[field] = 5
        elif key == "page":
            payload[field] = 1

    if payload:
        return payload

    # Last-resort fallback: map query into first field.
    return {fields[0]: query}


async def _force_single_mcp_call(
    tools: list,
    step: PlanStep,
    context: ResearchContext,
    emitter: WSEmitter,
    research_id: str,
) -> list[dict]:
    """Fallback: run one MCP tool directly if the LLM skipped tool calls."""
    if not tools:
        return []

    preferred = [
        "web_search",
        "read_webpages",
        "search_urls_tool",
        "youtube_search",
        "image_search_tool",
        "scrape_single_url",
    ]

    selected = tools[0]
    selected_from_suggestion = False
    suggested = [s.strip() for s in step.suggested_tools if s.strip()]
    for name in suggested:
        match = next((t for t in tools if getattr(t, "name", "") == name), None)
        if match is not None:
            selected = match
            selected_from_suggestion = True
            break

    if not selected_from_suggestion:
        for name in preferred:
            match = next((t for t in tools if getattr(t, "name", "") == name), None)
            if match is not None:
                selected = match
                break

    tool_name = getattr(selected, "name", "mcp_tool")
    payload = _tool_input_payload(selected, step, context)

    await emitter.emit(
        ToolCalledEvent(
            research_id=research_id,
            tool_name=tool_name,
            args=payload if isinstance(payload, dict) else {"input": str(payload)},
            step_index=step.step_index,
        )
    )

    try:
        output = await selected.ainvoke(payload)
        summary = summarise_tool_output(tool_name, output)
        parsed = parse_tool_output(tool_name, output)

        await emitter.emit(
            ToolResultEvent(
                research_id=research_id,
                tool_name=tool_name,
                result_summary=summary,
                step_index=step.step_index,
            )
        )

        items: list[dict] = []
        for item in parsed:
            items.append(
                {
                    "tool": item.get("tool", tool_name),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "summary": summary,
                    "step_index": step.step_index,
                }
            )
        return items

    except Exception as exc:
        await emitter.emit(
            ToolErrorEvent(
                research_id=research_id,
                tool_name=tool_name,
                error=str(exc),
                step_index=step.step_index,
            )
        )
        logger.warning("[orc1] Forced MCP call failed for %s: %s", tool_name, exc)
        return []


async def _persist_step_sources(
    research_id: str,
    workspace_id: str,
    step_index: int,
    sources: list[dict],
    temp_dir: str,
    extended_mode: bool = False,
) -> None:
    """
    ## Description

    Offload all source persistence to BG workers.
    Sources are already normalised dicts.
    In extended mode, stores full content without truncation.

    ## Parameters

    - `research_id` (`str`)
      - Description: Unique research session identifier.
      - Constraints: Must be non-empty.

    - `workspace_id` (`str`)
      - Description: Workspace identifier.
      - Constraints: Must be non-empty.

    - `step_index` (`int`)
      - Description: Current plan step index.
      - Constraints: Must be >= 0.

    - `sources` (`list[dict]`)
      - Description: Normalised source dicts from tool parsing.
      - Constraints: Each dict should have tool/url/content keys.

    - `temp_dir` (`str`)
      - Description: Path to temp research directory.
      - Constraints: Must be a valid directory path.

    - `extended_mode` (`bool`)
      - Description: When True, stores full content without the 4000 char limit.
      - Constraints: Must be a boolean.

    ## Returns

    `None`

    ## Side Effects

    - Schedules background tasks to insert rows into research_sources table.
    """
    from main.src.utils.core.task_schedular import scheduler

    step_file_path = step_findings_path(temp_dir, step_index)

    for source in sources:
        tool = source.get("tool", "")
        url = source.get("url", "")
        content = source.get("content", "")
        if not content and not url:
            continue

        persisted_content = content if extended_mode else content[:4000]

        await scheduler.schedule(
            _insert_research_source_row,
            params={
                "research_id": research_id,
                "source_type": tool,
                "source_url": url,
                "source_content": persisted_content,
                "step_index": step_index,
                "step_file_path": step_file_path,
            },
        )


def _insert_research_source_row(
    research_id: str,
    source_type: str,
    source_url: str,
    source_content: str,
    step_index: int,
    step_file_path: str,
) -> None:
    """Insert source row with graceful fallback for older DB schemas."""
    from main.src.store.DBManager import researches_db_manager

    full_data = {
        "id": str(uuid.uuid4()),
        "research_id": research_id,
        "source_type": source_type,
        "source_url": source_url,
        "source_content": source_content,
        "source_citations": "",
        "source_vector_id": "",
        "step_index": step_index,
        "temp_file_path": step_file_path,
    }

    result = researches_db_manager.insert("research_sources", full_data)
    if result.get("success"):
        return

    # Older DBs may not yet have tracking columns; retry without them.
    message = str(result.get("message", ""))
    if "no column named" in message and (
        "step_index" in message or "temp_file_path" in message
    ):
        legacy_data = {
            "id": full_data["id"],
            "research_id": research_id,
            "source_type": source_type,
            "source_url": source_url,
            "source_content": source_content,
            "source_citations": "",
            "source_vector_id": "",
        }
        legacy_result = researches_db_manager.insert("research_sources", legacy_data)
        if legacy_result.get("success"):
            logger.warning(
                "[orc1] Inserted research source without tracking columns (legacy schema)."
            )
            return

    logger.warning("[orc1] Failed to persist research source: %s", message)
