"""
Groq plan generator.

Produces a structured ResearchPlan.
"""

import json
import logging
import re
from typing import Any

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from research.config import settings
from research.models import PlanStep, ResearchPlan, QAPair

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
- Do not make every step web_search-only; distribute tools based on step goals.

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
            return _normalize_plan_payload(payload)
        if isinstance(payload.get("plan"), list):
            return _normalize_plan_payload({"steps": payload["plan"]})

    raise ValueError(f"Unsupported ResearchPlan payload type: {type(payload).__name__}")


def _normalize_plan_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize schema variants from LLM output to strict ResearchPlan fields."""
    raw_steps = payload.get("steps")
    if not isinstance(raw_steps, list):
        raise ValueError("Research plan payload must include a steps list")

    normalized_steps: list[dict[str, Any]] = []
    for i, item in enumerate(raw_steps):
        if not isinstance(item, dict):
            continue

        raw_index = item.get("step_index", item.get("index", i))
        if isinstance(raw_index, int):
            step_index = raw_index
        elif isinstance(raw_index, float):
            step_index = int(raw_index)
        elif isinstance(raw_index, str) and raw_index.strip().lstrip("-").isdigit():
            step_index = int(raw_index.strip())
        else:
            step_index = i

        step_title = (
            item.get("step_title")
            or item.get("title")
            or item.get("step_name")
            or item.get("name")
            or f"Step {step_index + 1}"
        )
        step_description = (
            item.get("step_description")
            or item.get("description")
            or item.get("details")
            or item.get("objective")
            or ""
        )

        suggested_tools = item.get("suggested_tools", item.get("tools", []))
        if isinstance(suggested_tools, str):
            suggested_tools = [
                token.strip() for token in suggested_tools.split(",") if token.strip()
            ]
        if not isinstance(suggested_tools, list):
            suggested_tools = []
        suggested_tools = [
            str(tool).strip() for tool in suggested_tools if str(tool).strip()
        ]

        complexity = (
            str(item.get("estimated_complexity", item.get("complexity", "medium")))
            .strip()
            .lower()
        )
        if complexity not in {"low", "medium", "high"}:
            complexity = "medium"

        normalized_steps.append(
            {
                "step_index": step_index,
                "step_title": str(step_title).strip() or f"Step {step_index + 1}",
                "step_description": str(step_description).strip(),
                "suggested_tools": suggested_tools,
                "estimated_complexity": complexity,
            }
        )

    if not normalized_steps:
        raise ValueError("No valid plan steps were produced by the model")

    return {"steps": normalized_steps}


_TOOL_ALIASES = {
    "websearch": "web_search",
    "web": "web_search",
    "readwebpage": "read_webpages",
    "readwebpages": "read_webpages",
    "searchurls": "search_urls_tool",
    "searchurlstool": "search_urls_tool",
    "urlsearch": "search_urls_tool",
    "youtube": "youtube_search",
    "video": "youtube_search",
    "youtubesearch": "youtube_search",
    "imagesearch": "image_search_tool",
    "imagesearchtool": "image_search_tool",
    "image": "image_search_tool",
    "images": "image_search_tool",
    "scrape": "scrape_single_url",
    "scrapesingleurl": "scrape_single_url",
    "document": "process_docs",
    "documents": "process_docs",
    "pdf": "process_docs",
}


def _tool_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").strip().lower())


def _resolve_tool_names(
    requested: list[str],
    available_tools: list[str],
) -> list[str]:
    if not requested or not available_tools:
        return []

    available_exact = {
        tool.strip(): tool for tool in available_tools if isinstance(tool, str)
    }
    available_by_key = {
        _tool_key(tool): tool for tool in available_tools if isinstance(tool, str)
    }

    resolved: list[str] = []
    for raw in requested:
        candidate = (raw or "").strip()
        if not candidate:
            continue

        matched = available_exact.get(candidate)
        if matched is None:
            key = _tool_key(candidate)
            alias = _TOOL_ALIASES.get(key)
            matched = available_by_key.get(key)
            if matched is None and alias:
                matched = available_exact.get(alias) or available_by_key.get(
                    _tool_key(alias)
                )

        if matched and matched not in resolved:
            resolved.append(matched)

    return resolved


def _infer_tools_for_step(step: PlanStep, available_tools: list[str]) -> list[str]:
    text = f"{step.step_title} {step.step_description}".lower()
    inferred: list[str] = []

    def add(tool_name: str) -> None:
        if tool_name in available_tools and tool_name not in inferred:
            inferred.append(tool_name)

    if any(token in text for token in ("youtube", "video", "podcast", "interview")):
        add("youtube_search")
    if any(
        token in text
        for token in ("image", "photo", "visual", "diagram", "infographic")
    ):
        add("image_search_tool")
    if any(token in text for token in ("document", "pdf", "file", "report")):
        add("process_docs")
    if any(token in text for token in ("url", "link", "website list", "directory")):
        add("search_urls_tool")
    if any(token in text for token in ("scrape", "crawl", "extract", "webpage")):
        add("read_webpages")

    if not inferred:
        for fallback in ("web_search", "read_webpages", "search_urls_tool"):
            if fallback in available_tools:
                inferred.append(fallback)
                break

    return inferred


def _normalize_plan_tool_suggestions(
    plan: ResearchPlan,
    available_tools: list[str],
) -> ResearchPlan:
    tools = [
        tool.strip()
        for tool in available_tools
        if isinstance(tool, str) and tool.strip()
    ]
    if not tools:
        return plan

    normalized_steps: list[PlanStep] = []
    web_only_count = 0

    for step in plan.steps:
        resolved = _resolve_tool_names(step.suggested_tools, tools)
        if not resolved:
            resolved = _infer_tools_for_step(step, tools)
        if not resolved:
            resolved = [tools[0]]

        if len(resolved) == 1 and resolved[0] == "web_search":
            web_only_count += 1

        normalized_steps.append(step.model_copy(update={"suggested_tools": resolved}))

    non_web_candidates = [
        tool
        for tool in (
            "read_webpages",
            "search_urls_tool",
            "youtube_search",
            "image_search_tool",
            "process_docs",
            "scrape_single_url",
        )
        if tool in tools and tool != "web_search"
    ]

    if (
        normalized_steps
        and web_only_count == len(normalized_steps)
        and non_web_candidates
    ):
        diversified: list[PlanStep] = []
        for idx, step in enumerate(normalized_steps):
            alt = non_web_candidates[idx % len(non_web_candidates)]
            suggestions = [alt]
            if "web_search" in tools and alt != "web_search":
                suggestions.append("web_search")
            diversified.append(step.model_copy(update={"suggested_tools": suggestions}))
        normalized_steps = diversified

    return ResearchPlan(steps=normalized_steps)


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


def _extract_failed_generation_json(error_text: str) -> Any | None:
    """Extract JSON payload embedded in tool_use_failed error strings."""
    if not error_text:
        return None

    patterns = [
        r"failed_generation':\s*'(?P<body>\{.*\})'",
        r'failed_generation":\s*"(?P<body>\{.*\})"',
    ]
    for pattern in patterns:
        match = re.search(pattern, error_text, flags=re.DOTALL)
        if not match:
            continue

        body = match.group("body")
        # Errors often carry escaped JSON; decode and parse both shapes.
        decoded = body.encode("utf-8").decode("unicode_escape")
        for candidate in (decoded, body):
            try:
                return _try_parse_json(candidate)
            except Exception:
                continue

    # Final fallback: try to parse any top-level object in the error string.
    try:
        return _try_parse_json(error_text)
    except Exception:
        return None


def _parse_research_plan_response(response: Any) -> ResearchPlan:
    """Parse structured output with fallback for Groq json_mode edge-cases."""
    if isinstance(response, ResearchPlan):
        return response

    if isinstance(response, dict):
        parsed = response.get("parsed")
        if parsed is not None:
            try:
                payload = _coerce_plan_payload(parsed)
                return ResearchPlan.model_validate(payload)
            except Exception:
                # Continue into raw fallback below.
                pass

        raw = response.get("raw")
        if raw is not None:
            text = _extract_text_from_raw_message(raw)
            try:
                payload = _coerce_plan_payload(_try_parse_json(text))
                return ResearchPlan.model_validate(payload)
            except Exception:
                pass

        failed_generation = response.get("failed_generation")
        if isinstance(failed_generation, str):
            payload = _coerce_plan_payload(_try_parse_json(failed_generation))
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

            # Recover directly from tool_use_failed payload if present.
            recovered = _extract_failed_generation_json(str(exc))
            if recovered is not None:
                try:
                    payload = _coerce_plan_payload(recovered)
                    result = ResearchPlan.model_validate(payload)
                    logger.info(
                        "[plan_gen] Recovered plan from failed_generation using method: %s",
                        method,
                    )
                    return result
                except Exception as recovery_exc:
                    errors.append(f"{method}.failed_generation: {recovery_exc}")

    # Final fallback: invoke plain model output, then parse JSON manually.
    try:
        raw_response = await (prompt | llm).ainvoke(
            payload,
            config={"callbacks": [tracker]},
        )
        text = _extract_text_from_raw_message(raw_response)
        parsed = _try_parse_json(text)
        result = ResearchPlan.model_validate(_coerce_plan_payload(parsed))
        logger.info("[plan_gen] Plain JSON fallback succeeded")
        return result
    except Exception as exc:
        errors.append(f"plain_json_fallback: {exc}")

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
    result = _normalize_plan_tool_suggestions(result, available_tools)

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
    result = _normalize_plan_tool_suggestions(result, available_tools)

    logger.info("[plan_gen] Refined to %d steps", len(result.steps))
    return result
