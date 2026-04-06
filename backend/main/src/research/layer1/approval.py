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

        # Await approval or refactor until user responds.
        msg: dict = await approval_queue.get()

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

    return current_plan
