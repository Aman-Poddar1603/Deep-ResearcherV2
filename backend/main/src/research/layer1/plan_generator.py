"""
Groq plan generator.

Produces a structured ResearchPlan.
"""

import json
import logging
from typing import Any

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from research.config import settings
from research.models import ResearchPlan, QAPair

logger = logging.getLogger(__name__)

_PLAN_PROMPT = """You are an expert research strategist.

User: {username}
Research topic: {cleaned_prompt}
AI personality: {ai_personality}

Clarification Q&A gathered:
{qa_context}

User-provided sources to incorporate: {sources}

Research template structure (the artifact must follow this):
{research_template}

Live MCP tools available to the researcher (use these exact names):
{available_tools}

Planning policy:
- Build the plan for multimodal research (web pages, YouTube, images, documents, URLs), not only retrieval.
- For evidence-collection steps, prioritize MCP tools before rag_search.
- Every step must include at least one live MCP tool in suggested_tools.
- Use exact tool names from the list above; do not invent tool names.
- Only suggest rag_search for synthesis/coverage steps after external sources are gathered.

Generate a comprehensive step-by-step research plan. Each step should:
- Be independently executable by a research agent using web/document/image tools
- Directly map to sections of the research template above
- Specify which tools are most appropriate from the live MCP tool list above
- Have realistic complexity (low/medium/high)

Return a JSON object with a "steps" array. Each step:
{{
  "step_index": 0,
  "step_title": "...",
  "step_description": "...",
  "suggested_tools": ["web_search", "..."],
  "estimated_complexity": "medium"
}}

Aim for 5–10 steps. No more than 12."""

_REFINE_PROMPT = """The user wants to refine the research plan.

Current plan: {current_plan}
User feedback: {feedback}

Live MCP tools available to the researcher (use these exact names):
{available_tools}

Keep the plan multimodal. For evidence collection, prioritize MCP tools before rag_search.
Each step must keep at least one live MCP tool in suggested_tools.

Update the plan based on the feedback.

IMPORTANT OUTPUT FORMAT:
- Return a JSON object with top-level key "steps".
- Never return a bare JSON array.
- No markdown, no prose, no code fences.
"""


def _extract_text_from_raw_message(raw_message: Any) -> str:
    content = getattr(raw_message, "content", "")
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, str):
                chunks.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    chunks.append(text)
                else:
                    chunks.append(str(item))
            else:
                chunks.append(str(item))
        return "\n".join(chunks)

    return str(content)


def _coerce_plan_payload(payload: Any) -> dict[str, Any]:
    """Normalize model payloads into {'steps': [...]} shape."""
    if isinstance(payload, ResearchPlan):
        return payload.model_dump()

    if isinstance(payload, list):
        return {"steps": payload}

    if isinstance(payload, dict):
        if isinstance(payload.get("steps"), list):
            return payload
        if isinstance(payload.get("plan"), list):
            return {"steps": payload["plan"]}

    raise ValueError(f"Unsupported ResearchPlan payload type: {type(payload).__name__}")


def _try_parse_json(text: str) -> Any:
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Empty model response")

    # Handle optional fenced JSON output.
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Last-resort: extract the first JSON object/array found in surrounding text.
    first_obj, last_obj = cleaned.find("{"), cleaned.rfind("}")
    if first_obj != -1 and last_obj > first_obj:
        try:
            return json.loads(cleaned[first_obj : last_obj + 1])
        except json.JSONDecodeError:
            pass

    first_arr, last_arr = cleaned.find("["), cleaned.rfind("]")
    if first_arr != -1 and last_arr > first_arr:
        return json.loads(cleaned[first_arr : last_arr + 1])

    raise ValueError("Could not parse JSON from model response")


def _parse_research_plan_response(response: Any) -> ResearchPlan:
    """Parse structured output with fallback for Groq json_mode edge-cases."""
    if isinstance(response, ResearchPlan):
        return response

    if isinstance(response, dict):
        parsed = response.get("parsed")
        if parsed is not None:
            payload = _coerce_plan_payload(parsed)
            return ResearchPlan.model_validate(payload)

        raw = response.get("raw")
        if raw is not None:
            text = _extract_text_from_raw_message(raw)
            payload = _coerce_plan_payload(_try_parse_json(text))
            return ResearchPlan.model_validate(payload)

    payload = _coerce_plan_payload(response)
    return ResearchPlan.model_validate(payload)


def _build_plan_llm() -> ChatGroq:
    return ChatGroq(
        model=settings.GROQ_MODEL,
        temperature=0,
        api_key=settings.GROQ_API_KEY,
    )


def _preferred_structured_method() -> str:
    model_name = (settings.GROQ_MODEL or "").lower()
    return "function_calling" if "llama" in model_name else "json_mode"


def _ordered_structured_methods() -> list[str]:
    primary = _preferred_structured_method()
    secondary = "json_mode" if primary == "function_calling" else "function_calling"
    return [primary, secondary]


async def _invoke_plan_with_fallback(
    llm: ChatGroq,
    prompt: ChatPromptTemplate,
    payload: dict[str, Any],
    tracker,
) -> ResearchPlan:
    errors: list[str] = []

    for method in _ordered_structured_methods():
        structured_llm = llm.with_structured_output(
            ResearchPlan,
            method=method,
            include_raw=True,
        )
        chain = prompt | structured_llm

        try:
            response = await chain.ainvoke(
                payload,
                config={"callbacks": [tracker]},
            )
            result = _parse_research_plan_response(response)
            logger.info("[plan_gen] Structured-output method succeeded: %s", method)
            return result
        except Exception as exc:
            errors.append(f"{method}: {exc}")
            logger.warning(
                "[plan_gen] Structured-output method failed (%s): %s", method, exc
            )

    raise RuntimeError(
        "Failed to parse ResearchPlan using all structured-output methods: "
        + " | ".join(errors)
    )


async def generate_plan(
    cleaned_prompt: str,
    username: str,
    ai_personality: str,
    qa_history: list[QAPair],
    sources: list[str],
    research_template: str,
    available_tools: list[str],
    tracker,
) -> ResearchPlan:
    llm = _build_plan_llm()
    prompt = ChatPromptTemplate.from_template(_PLAN_PROMPT)

    qa_context = (
        "\n".join(f"Q: {p.question}\nA: {p.answer}" for p in qa_history)
        or "No clarifications provided."
    )

    result = await _invoke_plan_with_fallback(
        llm=llm,
        prompt=prompt,
        payload={
            "username": username,
            "cleaned_prompt": cleaned_prompt,
            "ai_personality": ai_personality,
            "qa_context": qa_context,
            "sources": ", ".join(sources) or "None",
            "research_template": research_template
            or "No template provided — use best judgment.",
            "available_tools": (
                ", ".join(available_tools)
                if available_tools
                else "No MCP tools detected"
            ),
        },
        tracker=tracker,
    )

    logger.info("[plan_gen] Generated %d steps", len(result.steps))
    return result


async def refine_plan(
    current_plan: ResearchPlan,
    feedback: str,
    available_tools: list[str],
    tracker,
) -> ResearchPlan:
    llm = _build_plan_llm()
    prompt = ChatPromptTemplate.from_template(_REFINE_PROMPT)
    result = await _invoke_plan_with_fallback(
        llm=llm,
        prompt=prompt,
        payload={
            "current_plan": json.dumps(
                {"steps": [s.model_dump() for s in current_plan.steps]},
                indent=2,
            ),
            "feedback": feedback,
            "available_tools": (
                ", ".join(available_tools)
                if available_tools
                else "No MCP tools detected"
            ),
        },
        tracker=tracker,
    )

    logger.info("[plan_gen] Refined to %d steps", len(result.steps))
    return result
