"""Final artifact generator.

Primary model: Gemini Flash-Lite (env-configured).
Fallback model: Ollama.

Also performs a late-stage media enrichment pass (YouTube + image tools) so
the final report can embed videos and visuals, while streaming those results
to the frontend in real time as tool/chain-of-thought events.
"""

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urlparse

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - optional dependency
    genai = None
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from research.config import settings
from research.emitter import WSEmitter
from research.layer2.tools import (
    get_mcp_tools,
    parse_tool_output,
    summarise_tool_output,
)
from research.models import (
    ArtifactChunkEvent,
    ArtifactDoneEvent,
    ChainOfThoughtEvent,
    ReactActEvent,
    ReactObserveEvent,
    ReActEvent,
    SystemProgressEvent,
    ToolCalledEvent,
    ToolErrorEvent,
    ToolOutputEvent,
    ToolResultEvent,
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

CRITICAL output rules:
- Report must be mixed-media and useful: blend text analysis with visuals/videos.
- Include relevant YouTube embeds as raw HTML iframe tags in markdown.
- Include relevant images in sequence using markdown image syntax.
- Keep media near the sections where they add value.
- Keep citations accurate; do not fabricate links.

Cite all sources inline using [Source N] notation where N matches the source index.
Append a full source list at the end titled "## Sources".

Base your entire response on the research knowledge below. Do not add information
that isn't supported by the gathered research.

Research topic: {cleaned_prompt}

Synthesis document:
{synthesis_md}

Gathered research knowledge:
{knowledge_summary}

Source list for citations:
{cited_sources}

Citations document:
{citations_md}

Late-stage media context (use where relevant):
{youtube_video_blocks}

{image_blocks}

Write the complete research artifact now."""


def _tool_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").strip().lower())


def _normalize_tool_name(name: str) -> str:
    lowered = (name or "").strip().lower()
    if "::" in lowered:
        lowered = lowered.split("::")[-1]
    if "/" in lowered:
        lowered = lowered.split("/")[-1]
    if "." in lowered:
        lowered = lowered.split(".")[-1]
    return lowered


def _compact_media_payload(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for item in items[:10]:
        if not isinstance(item, dict):
            continue
        compact.append(
            {
                "tool": str(item.get("tool", ""))[:120],
                "url": str(item.get("url", ""))[:900],
                "title": str(item.get("title", ""))[:300],
                "caption": str(item.get("description", ""))[:500],
                "summary": str(item.get("content", ""))[:1000],
            }
        )
    return compact


def _youtube_video_id(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    host = (parsed.netloc or "").lower()
    if "youtu.be" in host:
        return parsed.path.strip("/")
    if "youtube.com" in host:
        query_id = parse_qs(parsed.query).get("v", [""])[0]
        if query_id:
            return query_id
        path_parts = [p for p in parsed.path.split("/") if p]
        if len(path_parts) >= 2 and path_parts[0] in {"embed", "shorts"}:
            return path_parts[1]
    return ""


def _build_youtube_markdown(items: list[dict[str, Any]]) -> str:
    if not items:
        return "No curated YouTube videos were found in the final media pass."

    lines = ["## Video Evidence"]
    for idx, item in enumerate(items[:6], start=1):
        url = str(item.get("url", "")).strip()
        title = str(item.get("title", "")).strip() or f"Video {idx}"
        if not url:
            continue
        vid = _youtube_video_id(url)
        lines.append(f"### Video {idx}: {title}")
        lines.append(f"- Source link: [{title}]({url})")
        if vid:
            lines.append(
                f'<iframe width="560" height="315" src="https://www.youtube.com/embed/{vid}" title="{title}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'
            )
        lines.append("")
    return "\n".join(lines)


def _build_image_markdown(items: list[dict[str, Any]]) -> str:
    if not items:
        return "No curated image references were found in the final media pass."

    lines = ["## Visual Evidence"]
    for idx, item in enumerate(items[:10], start=1):
        url = str(item.get("url", "")).strip()
        title = str(item.get("title", "")).strip() or f"Image {idx}"
        if not url:
            continue
        lines.append(f"### Image {idx}: {title}")
        lines.append(f"![{title}]({url})")
        lines.append("")
    return "\n".join(lines)


def _build_tool_payload(tool: Any, query: str) -> dict[str, Any]:
    args_schema = getattr(tool, "args_schema", None)
    fields = (
        list(getattr(args_schema, "model_fields", {}).keys()) if args_schema else []
    )
    if not fields:
        return {"query": query}

    payload: dict[str, Any] = {}
    for field in fields:
        low = field.lower()
        if low in {
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
        elif "limit" in low or "max" in low or "top_k" in low:
            payload[field] = 6
        elif low == "page":
            payload[field] = 1

    if payload:
        return payload

    if len(fields) == 1:
        return {fields[0]: query}
    return {"query": query}


async def _run_media_enrichment(
    *,
    artifact_context: dict[str, Any],
    emitter: WSEmitter,
    research_id: str,
    step_index: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    query = (
        f"{artifact_context.get('cleaned_prompt', '')}\n"
        f"{artifact_context.get('title', '')}\n"
        "high quality references"
    ).strip()

    mcp_tools = await get_mcp_tools()
    if not mcp_tools:
        return ([], [])

    by_normalized = {
        _normalize_tool_name(getattr(tool, "name", "")): tool
        for tool in mcp_tools
        if getattr(tool, "name", "")
    }

    media_specs = [
        ("youtube_search", "video"),
        ("image_search_tool", "image"),
    ]

    youtube_items: list[dict[str, Any]] = []
    image_items: list[dict[str, Any]] = []

    for tool_name, media_type in media_specs:
        tool = by_normalized.get(tool_name)
        if tool is None:
            continue

        payload = _build_tool_payload(tool, query)
        await emitter.emit(
            ToolCalledEvent(
                research_id=research_id,
                tool_name=tool_name,
                args=payload,
                step_index=step_index,
            )
        )
        await emitter.emit(
            ReactActEvent(
                research_id=research_id,
                step_index=step_index,
                tool_name=tool_name,
            )
        )
        await emitter.emit(
            ReActEvent(
                research_id=research_id,
                step_index=step_index,
                sub_type="act",
                data={"tool_name": tool_name, "args": payload},
            )
        )

        try:
            output = await tool.ainvoke(payload)
            parsed = parse_tool_output(tool_name, output)
            summary = summarise_tool_output(tool_name, output)
            compact = _compact_media_payload(parsed)

            await emitter.emit(
                ToolOutputEvent(
                    research_id=research_id,
                    step_index=step_index,
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
                    step_index=step_index,
                    result_payload=compact,
                )
            )
            await emitter.emit(
                ReactObserveEvent(
                    research_id=research_id,
                    step_index=step_index,
                    observation_summary=summary,
                )
            )
            await emitter.emit(
                ReActEvent(
                    research_id=research_id,
                    step_index=step_index,
                    sub_type="observe",
                    data={"tool_name": tool_name, "summary": summary},
                )
            )

            if media_type == "video":
                filtered = [
                    p
                    for p in parsed
                    if isinstance(p, dict) and str(p.get("url", "")).strip()
                ]
                youtube_items.extend(filtered)
                if filtered:
                    markdown = "### YouTube Findings\n" + "\n".join(
                        f"- [{str(item.get('title') or item.get('url'))}]({str(item.get('url'))})"
                        for item in filtered[:6]
                    )
                    await emitter.emit(
                        ChainOfThoughtEvent(
                            research_id=research_id,
                            step_index=step_index,
                            token=markdown,
                        )
                    )

            if media_type == "image":
                filtered = [
                    p
                    for p in parsed
                    if isinstance(p, dict) and str(p.get("url", "")).strip()
                ]
                image_items.extend(filtered)
                if filtered:
                    markdown = "### Image Findings\n" + "\n".join(
                        f"- ![{str(item.get('title') or f'Image {idx + 1}')} ]({str(item.get('url'))})"
                        for idx, item in enumerate(filtered[:6])
                    )
                    await emitter.emit(
                        ChainOfThoughtEvent(
                            research_id=research_id,
                            step_index=step_index,
                            token=markdown,
                        )
                    )

        except Exception as exc:
            logger.warning("[artifact] Media tool failed (%s): %s", tool_name, exc)
            await emitter.emit(
                ToolErrorEvent(
                    research_id=research_id,
                    step_index=step_index,
                    tool_name=tool_name,
                    error=str(exc),
                )
            )

    return youtube_items, image_items


def _build_artifact_prompt_values(
    artifact_context: dict,
    youtube_items: list[dict[str, Any]],
    image_items: list[dict[str, Any]],
) -> dict:
    """
    ## Description

    Assemble prompt template values for artifact generation.
    In normal mode, truncates large text fields to 12000 chars.
    In extended mode, passes full text without truncation.

    ## Parameters

    - `artifact_context` (`dict`)
      - Description: Context dict returned by orchestrator2 with all synthesis data.
      - Constraints: Must contain keys like synthesis_md, knowledge_summary, cited_sources, etc.

    ## Returns

    `dict`

    Structure:

    ```json
    {
        "system_prompt": "str",
        "ai_personality": "str",
        "username": "str",
        "custom_prompt": "str",
        "research_template": "str",
        "cleaned_prompt": "str",
        "synthesis_md": "str",
        "knowledge_summary": "str",
        "cited_sources": "str",
        "citations_md": "str"
    }
    ```
    """
    extended_mode = artifact_context.get("extended_mode", False)
    citations_md = (artifact_context.get("citations_md") or "").strip()
    citations_text = citations_md or "\n".join(
        f"[Source {c['index']}] {c['title']} — {c['url']}"
        for c in artifact_context.get("cited_sources", [])
    )
    synthesis_md = (artifact_context.get("synthesis_md") or "").strip()
    knowledge_summary = artifact_context.get("knowledge_summary", "")

    if extended_mode:
        trimmed_synthesis = synthesis_md
        trimmed_knowledge = knowledge_summary
        trimmed_citations = citations_md
    else:
        trimmed_synthesis = synthesis_md[:12000]
        trimmed_knowledge = knowledge_summary[:12000]
        trimmed_citations = citations_md[:12000]

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
        "synthesis_md": trimmed_synthesis,
        "knowledge_summary": trimmed_knowledge,
        "cited_sources": citations_text or "No external sources.",
        "citations_md": trimmed_citations,
        "youtube_video_blocks": _build_youtube_markdown(youtube_items),
        "image_blocks": _build_image_markdown(image_items),
    }


async def _estimate_gemini_input_tokens(model: Any, prompt_text: str) -> int:
    try:
        counted = await asyncio.to_thread(model.count_tokens, prompt_text)
    except Exception:
        return 0
    total = getattr(counted, "total_tokens", 0)
    try:
        return int(total or 0)
    except (TypeError, ValueError):
        return 0


async def _stream_with_gemini(
    *,
    prompt_text: str,
    research_id: str,
    emitter: WSEmitter,
    tracker: TokenTracker,
) -> tuple[str, int]:
    if genai is None:
        raise RuntimeError("google-generativeai is not installed")

    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_ARTIFACT_MODEL,
        generation_config=genai.types.GenerationConfig(
            temperature=0.25,
            max_output_tokens=8192,
        ),
    )

    input_tokens = await _estimate_gemini_input_tokens(model, prompt_text)
    if input_tokens > 0:
        await tracker.record_explicit_tokens(input_tokens=input_tokens)

    full_artifact = ""
    output_estimate = 0

    response = await model.generate_content_async(prompt_text, stream=True)
    async for chunk in response:
        token = getattr(chunk, "text", "") or ""
        if not token:
            continue
        full_artifact += token
        await emitter.emit(
            ArtifactChunkEvent(
                research_id=research_id,
                text=token,
            )
        )

        token_est = max(1, len(token.split()))
        output_estimate += token_est
        await tracker.record_explicit_tokens(output_tokens=token_est)

    return full_artifact, max(output_estimate, len(full_artifact.split()))


async def _stream_with_ollama_fallback(
    *,
    prompt_text: str,
    research_id: str,
    emitter: WSEmitter,
) -> tuple[str, int]:
    tracker = TokenTracker(
        emitter=emitter,
        research_id=research_id,
        step_index=999,
        model_type="ollama",
        source=f"ollama/{settings.OLLAMA_MODEL}",
    )

    llm = ChatOllama(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0.25,
        streaming=True,
    ).with_config({"callbacks": [tracker]})

    prompt = ChatPromptTemplate.from_template("{artifact_prompt}")
    chain = prompt | llm

    full_artifact = ""
    async for chunk in chain.astream({"artifact_prompt": prompt_text}):
        token = chunk.content if isinstance(chunk.content, str) else ""
        if not token:
            continue
        full_artifact += token
        await emitter.emit(
            ArtifactChunkEvent(
                research_id=research_id,
                text=token,
            )
        )

    return full_artifact, len(full_artifact.split())


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
            message="Preparing final media context for artifact...",
            percent=93,
        )
    )

    artifact_step_index = int(artifact_context.get("artifact_step_index") or 0)
    youtube_items, image_items = await _run_media_enrichment(
        artifact_context=artifact_context,
        emitter=emitter,
        research_id=research_id,
        step_index=artifact_step_index,
    )

    await emitter.emit(
        SystemProgressEvent(
            research_id=research_id,
            message="Generating final artifact with Gemini Flash-Lite...",
            percent=95,
        )
    )

    prompt_values = _build_artifact_prompt_values(
        artifact_context,
        youtube_items,
        image_items,
    )
    prompt_text = _ARTIFACT_PROMPT.format(**prompt_values)

    full_artifact = ""
    artifact_token_estimate = 0
    gemini_error: Exception | None = None

    if settings.GEMINI_API_KEY.strip():
        tracker = TokenTracker(
            emitter=emitter,
            research_id=research_id,
            step_index=999,
            model_type="gemini",
            source=f"gemini/{settings.GEMINI_ARTIFACT_MODEL}",
        )
        try:
            full_artifact, artifact_token_estimate = await _stream_with_gemini(
                prompt_text=prompt_text,
                research_id=research_id,
                emitter=emitter,
                tracker=tracker,
            )
        except Exception as exc:
            gemini_error = exc
            logger.warning(
                "[artifact] Gemini generation failed, using Ollama fallback: %s", exc
            )
    else:
        gemini_error = ValueError("GEMINI_API_KEY not configured")

    if not full_artifact.strip():
        await emitter.emit(
            SystemProgressEvent(
                research_id=research_id,
                message="Gemini unavailable, switching to Ollama fallback for artifact...",
                percent=96,
            )
        )
        full_artifact, artifact_token_estimate = await _stream_with_ollama_fallback(
            prompt_text=prompt_text,
            research_id=research_id,
            emitter=emitter,
        )

    if not full_artifact.strip() and gemini_error is not None:
        raise RuntimeError(
            f"Artifact generation failed (Gemini + fallback): {gemini_error}"
        )

    await emitter.emit(
        SystemProgressEvent(
            research_id=research_id,
            message="Finalizing and saving artifact...",
            percent=99,
        )
    )

    # Persist via BG worker
    await _persist_artifact(
        research_id,
        workspace_id,
        artifact_context,
        full_artifact,
        artifact_token_estimate,
    )

    await emitter.emit(
        ArtifactDoneEvent(
            research_id=research_id,
            total_tokens_in_artifact=artifact_token_estimate,
        )
    )

    return full_artifact


async def _persist_artifact(
    research_id: str,
    workspace_id: str,
    artifact_context: dict,
    artifact_text: str,
    artifact_token_estimate: int,
) -> None:
    from main.src.utils.core.task_schedular import scheduler
    from main.src.store.DBManager import researches_db_manager, history_db_manager
    from research.session import get_token_totals

    token_totals = await get_token_totals(research_id)

    # Resume-critical write: persist artifact synchronously so resume can always load it.
    artifact_payload = {
        "type": "md",
        "content": artifact_text,
        "complete": True,
        "tokens_used": artifact_token_estimate,
        "updated_at": datetime.utcnow().isoformat(),
        "title": artifact_context.get("title", ""),
        "description": artifact_context.get("description", ""),
    }
    researches_db_manager.update(
        "researches",
        data={"artifacts": json.dumps(artifact_payload, ensure_ascii=True)},
        where={"id": research_id},
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
                "tokens_used": int(token_totals.get("grand_total", 0)),
                "resources_used": 0,
                "time_taken_sec": 0,
                "success": True,
            },
        },
    )
