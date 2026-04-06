"""
Artifact generator — Groq streams the final long-form artifact.

Applies: username, ai_personality, system_prompt, custom_prompt,
research_template skeleton, cited sources, knowledge summary.
"""

import json
import logging
import uuid

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from research.config import settings
from research.emitter import WSEmitter
from research.models import (
    ArtifactChunkEvent,
    ArtifactDoneEvent,
    SystemProgressEvent,
)
from research.session import update_session_status
from research.token_tracker import TokenTracker

logger = logging.getLogger(__name__)

_ARTIFACT_PROMPT = """{system_prompt}

You are {ai_personality}.
The user's name is {username}. Address them naturally by name where appropriate.

{custom_prompt}

You MUST structure your entire response following this template exactly:
{research_template}

If no template is provided, use clear headings, subheadings, and well-organized sections.

Cite all sources inline using [Source N] notation where N matches the source index.
Append a full source list at the end titled "## Sources".

Base your entire response on the research knowledge below. Do not add information
that isn't supported by the gathered research.

Research topic: {cleaned_prompt}

Gathered research knowledge:
{knowledge_summary}

Source list for citations:
{cited_sources}

Write the complete research artifact now."""


def _build_artifact_prompt_values(artifact_context: dict) -> dict:
    citations_text = "\n".join(
        f"[Source {c['index']}] {c['title']} — {c['url']}"
        for c in artifact_context.get("cited_sources", [])
    )
    return {
        "system_prompt": artifact_context.get("system_prompt")
        or "You are a professional research assistant.",
        "ai_personality": artifact_context.get(
            "ai_personality", "professional research analyst"
        ),
        "username": artifact_context.get("username", ""),
        "custom_prompt": artifact_context.get("custom_prompt") or "",
        "research_template": artifact_context.get("research_template")
        or "Use well-structured headings and sections.",
        "cleaned_prompt": artifact_context.get("cleaned_prompt", ""),
        "knowledge_summary": artifact_context.get("knowledge_summary", "")[:12000],
        "cited_sources": citations_text or "No external sources.",
    }


async def run_artifact_generation(
    artifact_context: dict,
    research_id: str,
    workspace_id: str,
    emitter: WSEmitter,
) -> str:
    """
    Streams the artifact to the frontend token by token.
    Returns the full artifact text.
    """
    await update_session_status(research_id, "generating_artifact")
    await emitter.emit(
        SystemProgressEvent(
            research_id=research_id,
            message="Generating research artifact...",
            percent=93,
        )
    )

    tracker = TokenTracker(
        emitter=emitter,
        research_id=research_id,
        step_index=999,
        model_type="groq",
        source=f"groq/{settings.GROQ_MODEL}",
    )

    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        temperature=0.4,
        streaming=True,
        api_key=settings.GROQ_API_KEY,
    ).with_config({"callbacks": [tracker]})

    prompt = ChatPromptTemplate.from_template(_ARTIFACT_PROMPT)
    chain = prompt | llm

    prompt_values = _build_artifact_prompt_values(artifact_context)

    full_artifact = ""
    async for chunk in chain.astream(prompt_values):
        token = chunk.content if isinstance(chunk.content, str) else ""
        if token:
            full_artifact += token
            await emitter.emit(
                ArtifactChunkEvent(
                    research_id=research_id,
                    text=token,
                )
            )

    # Approximate token count from artifact length
    artifact_token_estimate = len(full_artifact.split())

    await emitter.emit(
        ArtifactDoneEvent(
            research_id=research_id,
            total_tokens_in_artifact=artifact_token_estimate,
        )
    )
    await emitter.emit(
        SystemProgressEvent(
            research_id=research_id,
            message="Artifact complete.",
            percent=100,
        )
    )

    # Persist via BG worker
    await _persist_artifact(research_id, workspace_id, artifact_context, full_artifact)

    return full_artifact


async def _persist_artifact(
    research_id: str,
    workspace_id: str,
    artifact_context: dict,
    artifact_text: str,
) -> None:
    from main.src.utils.core.task_schedular import scheduler
    from main.src.store.DBManager import researches_db_manager, history_db_manager

    # Update researches table with artifact
    await scheduler.schedule(
        researches_db_manager.update,
        params={
            "table_name": "researches",
            "data": {"artifacts": artifact_text},
            "where": {"id": research_id},
        },
    )

    # Save to history
    await scheduler.schedule(
        history_db_manager.insert,
        params={
            "table_name": "research_history",
            "data": {
                "id": str(uuid.uuid4()),
                "research_id": research_id,
                "workspace_id": workspace_id,
                "activity": "artifact_generated",
                "status": "completed",
                "url": "",
            },
        },
    )

    # Save workflow record
    await scheduler.schedule(
        history_db_manager.insert,
        params={
            "table_name": "research_workflow",
            "data": {
                "id": str(uuid.uuid4()),
                "workspace_id": workspace_id,
                "research_id": research_id,
                "workflow": "layer1→orc1→orc2→artifact",
                "steps": 0,
                "tokens_used": 0,
                "resources_used": 0,
                "time_taken_sec": 0,
                "success": True,
            },
        },
    )
