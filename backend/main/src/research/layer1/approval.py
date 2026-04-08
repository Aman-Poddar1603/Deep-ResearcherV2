"""
User approval loop.

Emits input.plan_ready, then waits for user.approval message.
If 'refactor' → sends plan + feedback to plan_generator and repeats.
Max MAX_PLAN_REFACTOR_ROUNDS cycles.
"""

import asyncio
import logging

from research.config import settings
from research.models import (
    ResearchPlan,
    QAPair,
    InputPlanReadyEvent,
    InputApprovedEvent,
    SystemErrorEvent,
)
from research.session import (
    clear_pending_input,
    is_stop_requested,
    save_pending_input,
)

logger = logging.getLogger(__name__)


async def run_approval_loop(
    plan: ResearchPlan,
    research_id: str,
    emitter,
    tracker,
    approval_queue: asyncio.Queue,
    cleaned_prompt: str,
    username: str,
    ai_personality: str,
    qa_history: list[QAPair],
    sources: list[str],
    research_template: str,
    available_tools: list[str],
) -> ResearchPlan:
    """
    Returns the approved ResearchPlan (possibly refined).

    approval_queue receives dicts: {"action": "approve"} or
    {"action": "refactor", "feedback": "..."}
    """
    from research.layer1.plan_generator import refine_plan

    current_plan = plan

    for attempt in range(settings.MAX_PLAN_REFACTOR_ROUNDS + 1):
        # Emit plan to frontend
        await emitter.emit(
            InputPlanReadyEvent(
                research_id=research_id,
                plan=[step.model_dump() for step in current_plan.steps],
            )
        )
        await save_pending_input(
            research_id,
            input_type="plan_approval",
            payload={
                "attempt": attempt,
                "max_attempts": settings.MAX_PLAN_REFACTOR_ROUNDS,
                "plan": [step.model_dump() for step in current_plan.steps],
            },
        )

        # Await approval/refactor with no hard timeout, still stop-aware.
        msg = await _wait_for_user_approval(
            approval_queue=approval_queue,
            research_id=research_id,
            timeout_seconds=None,
        )
        if msg is None:
            if not await is_stop_requested(research_id):
                await emitter.emit(
                    SystemErrorEvent(
                        research_id=research_id,
                        message="Waiting for plan approval was interrupted.",
                        recoverable=True,
                    )
                )
            await emitter.emit(
                InputApprovedEvent(
                    research_id=research_id,
                    confirmed=False,
                )
            )
            break

        await clear_pending_input(research_id)

        action = msg.get("action", "approve")

        if action == "approve":
            logger.info("[approval] Plan approved on attempt %d", attempt)
            await emitter.emit(
                InputApprovedEvent(
                    research_id=research_id,
                    confirmed=True,
                )
            )
            break

        if action == "refactor" and attempt < settings.MAX_PLAN_REFACTOR_ROUNDS:
            feedback = msg.get("feedback", "")
            logger.info("[approval] Refactoring plan: %s", feedback[:80])
            current_plan = await refine_plan(
                current_plan,
                feedback,
                available_tools,
                tracker,
            )
        else:
            # Max refactors reached — accept current plan
            logger.warning(
                "[approval] Max refactor rounds reached — accepting current plan"
            )
            await emitter.emit(
                InputApprovedEvent(
                    research_id=research_id,
                    confirmed=True,
                )
            )
            break

    await clear_pending_input(research_id)
    return current_plan


async def _wait_for_user_approval(
    approval_queue: asyncio.Queue,
    research_id: str,
    timeout_seconds: int | None,
    poll_interval_seconds: float = 1.0,
) -> dict | None:
    loop = asyncio.get_running_loop()
    started_at = loop.time()

    while True:
        if await is_stop_requested(research_id):
            return None

        if timeout_seconds is None:
            wait_timeout = poll_interval_seconds
        else:
            elapsed = loop.time() - started_at
            remaining = timeout_seconds - elapsed
            if remaining <= 0:
                return None
            wait_timeout = min(poll_interval_seconds, remaining)

        try:
            msg = await asyncio.wait_for(
                approval_queue.get(),
                timeout=wait_timeout,
            )
        except asyncio.TimeoutError:
            continue

        if isinstance(msg, dict):
            return msg
        return {"action": "approve"}
