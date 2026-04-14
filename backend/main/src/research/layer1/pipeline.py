"""
Layer 1 pipeline — runs the full input processing flow:
  1. Ingest + clean (Ollama)
  2. Harm / injection guard (Ollama)
  3. Clarification Q&A loop (Groq)
  4. Plan generation (Groq)
  5. User approval loop
  6. Context assembly → saved to Redis

Returns ResearchContext ready for Layer 2.
"""

import asyncio
import logging
import uuid

from research.config import settings
from research.emitter import WSEmitter
from research.models import (
    ResearchStartRequest,
    ResearchContext,
    InputValidatedEvent,
    SystemErrorEvent,
    SystemProgressEvent,
)
from research.session import (
    init_session,
    set_total_steps,
    update_session_status,
    save_context,
    save_plan,
)
from research.step_snapshots import seed_step_snapshots_from_plan
from research.token_tracker import TokenTracker
from research.layer1.cleaner import run_cleaner
from research.layer1.guard import run_guard
from research.layer1.qa_loop import run_qa_loop
from research.layer1.plan_generator import generate_plan
from research.layer1.approval import run_approval_loop
from research.layer2.tools import get_mcp_tools

logger = logging.getLogger(__name__)

_DEFAULT_TOOL_HINTS = [
    "web_search",
    "read_webpages",
    "youtube_search",
    "image_search_tool",
    "understand_images_tool",
    "process_docs",
    "search_urls_tool",
    "scrape_single_url",
]


async def run_layer1(
    request: ResearchStartRequest,
    research_id: str,
    emitter: WSEmitter,
    answer_queue: asyncio.Queue,
    approval_queue: asyncio.Queue,
) -> ResearchContext | None:
    """
    Runs Layer 1. Returns ResearchContext or None if blocked by guard.

    answer_queue   — fed by WS router on user.answer messages
    approval_queue — fed by WS router on user.approval messages
    """
    # ── Init session ──────────────────────────────────────────────────────────
    await init_session(research_id, request.workspace_id)
    await update_session_status(research_id, "layer1_cleaning")

    # ── Step 0 progress ───────────────────────────────────────────────────────
    await emitter.emit(
        SystemProgressEvent(
            research_id=research_id,
            message="Processing your prompt...",
            percent=5,
        )
    )

    # ── Token tracker for Ollama (step -1 = pre-plan) ────────────────────────
    ollama_tracker = TokenTracker(
        emitter=emitter,
        research_id=research_id,
        step_index=-1,
        model_type="ollama",
        source=f"ollama/{settings.OLLAMA_MODEL}",
    )
    groq_tracker = TokenTracker(
        emitter=emitter,
        research_id=research_id,
        step_index=-1,
        model_type="groq",
        source=f"groq/{settings.GROQ_MODEL}",
    )

    # ── 1. Clean prompt ───────────────────────────────────────────────────────
    cleaned = await run_cleaner(
        raw_prompt=request.prompt,
        provided_title=request.title or "",
        provided_description=request.description or "",
        tracker=ollama_tracker,
    )

    await emitter.emit(
        InputValidatedEvent(
            research_id=research_id,
            title=cleaned.title,
            description=cleaned.description,
            cleaned_prompt=cleaned.cleaned_prompt,
        )
    )
    await emitter.emit(
        SystemProgressEvent(
            research_id=research_id,
            message="Prompt cleaned and validated.",
            percent=12,
        )
    )

    # ── 2. Harm guard ─────────────────────────────────────────────────────────
    await update_session_status(research_id, "layer1_guard")
    guard = await run_guard(cleaned.cleaned_prompt, ollama_tracker)

    if not guard.safe:
        await emitter.emit(
            SystemErrorEvent(
                research_id=research_id,
                message=f"Research blocked: {guard.reason}",
                recoverable=False,
            )
        )
        await update_session_status(research_id, "blocked")
        return None

    await emitter.emit(
        SystemProgressEvent(
            research_id=research_id,
            message="Safety check passed.",
            percent=18,
        )
    )

    # ── 3. Load MCP tools (used in orchestration stages) ─────────────────────
    mcp_tools = await get_mcp_tools()
    available_tools = sorted(
        {
            getattr(tool, "name", "").strip()
            for tool in mcp_tools
            if getattr(tool, "name", "").strip()
        }
    )
    if not available_tools:
        available_tools = list(_DEFAULT_TOOL_HINTS)

    # ── 4. Clarification Q&A loop ─────────────────────────────────────────────
    await update_session_status(research_id, "layer1_qa")
    await emitter.emit(
        SystemProgressEvent(
            research_id=research_id,
            message="Starting clarification questions...",
            percent=25,
        )
    )

    qa_history = await run_qa_loop(
        cleaned_prompt=cleaned.cleaned_prompt,
        username=request.username,
        emitter=emitter,
        tracker=groq_tracker,
        answer_queue=answer_queue,
        mcp_tools=mcp_tools,
        research_id=research_id,
    )

    await emitter.emit(
        SystemProgressEvent(
            research_id=research_id,
            message="Clarification complete. Generating research plan...",
            percent=45,
        )
    )

    # ── 5. Plan generation ────────────────────────────────────────────────────
    await update_session_status(research_id, "layer1_planning")
    plan = await generate_plan(
        cleaned_prompt=cleaned.cleaned_prompt,
        username=request.username,
        ai_personality=request.ai_personality,
        qa_history=qa_history,
        sources=request.sources,
        research_template=request.research_template,
        available_tools=available_tools,
        tracker=groq_tracker,
    )

    await emitter.emit(
        SystemProgressEvent(
            research_id=research_id,
            message="Plan ready. Waiting for your approval...",
            percent=55,
        )
    )

    # ── 6. User approval loop ─────────────────────────────────────────────────
    await update_session_status(research_id, "layer1_approval")
    approved_plan = await run_approval_loop(
        plan=plan,
        research_id=research_id,
        emitter=emitter,
        tracker=groq_tracker,
        approval_queue=approval_queue,
        cleaned_prompt=cleaned.cleaned_prompt,
        username=request.username,
        ai_personality=request.ai_personality,
        qa_history=qa_history,
        sources=request.sources,
        research_template=request.research_template,
        available_tools=available_tools,
    )
    await set_total_steps(research_id, len(approved_plan.steps))

    # ── 7. Build context ──────────────────────────────────────────────────────
    context = ResearchContext(
        research_id=research_id,
        cleaned_prompt=cleaned.cleaned_prompt,
        title=cleaned.title,
        description=cleaned.description,
        plan=approved_plan.steps,
        qa_history=qa_history,
        sources=request.sources,
        workspace_id=request.workspace_id,
        system_prompt=request.system_prompt,
        custom_prompt=request.custom_prompt,
        research_template=request.research_template,
        ai_personality=request.ai_personality,
        username=request.username,
        extended_mode=request.extended_mode,
    )

    # Save to Redis as reconnect restore point
    await save_context(research_id, context.model_dump())
    await save_plan(research_id, [s.model_dump() for s in approved_plan.steps])
    await seed_step_snapshots_from_plan(
        research_id,
        [s.model_dump() for s in approved_plan.steps],
    )

    # Save parent records synchronously to avoid FK race with research_sources inserts.
    from main.src.utils.core.task_schedular import scheduler
    from main.src.store.DBManager import researches_db_manager

    research_row = researches_db_manager.insert(
        table_name="researches",
        data={
            "id": research_id,
            "title": cleaned.title,
            "desc": cleaned.description,
            "prompt": cleaned.cleaned_prompt,
            "sources": ",".join(request.sources),
            "workspace_id": request.workspace_id,
            "research_template_id": None,
            "custom_instructions": request.custom_prompt,
            "prompt_order": "",
        },
    )
    if not research_row.get("success"):
        await emitter.emit(
            SystemErrorEvent(
                research_id=research_id,
                message=f"Failed to persist research row: {research_row.get('message', 'unknown error')}",
                recoverable=False,
            )
        )
        await update_session_status(research_id, "error")
        return None

    await scheduler.schedule(
        researches_db_manager.insert,
        params={
            "table_name": "research_plans",
            "data": {
                "id": str(uuid.uuid4()),
                "plan": str([s.model_dump() for s in approved_plan.steps]),
                "workspace_id": request.workspace_id,
                "research_template_id": None,
                "prompt_order": "",
            },
        },
    )

    await update_session_status(
        research_id,
        "layer1_done",
        current_step=0,
        total_steps=len(approved_plan.steps),
    )
    await emitter.emit(
        SystemProgressEvent(
            research_id=research_id,
            message="Plan approved. Starting research...",
            percent=60,
        )
    )

    return context
