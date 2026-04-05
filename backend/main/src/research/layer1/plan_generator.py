"""
Groq plan generator.

Produces a structured ResearchPlan (JSON array of PlanStep objects).
Uses .with_structured_output() — no string parsing.
"""
import logging

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

Generate a comprehensive step-by-step research plan. Each step should:
- Be independently executable by a research agent using web/document/image tools
- Directly map to sections of the research template above
- Specify which tools are most appropriate (web_search, read_webpages, youtube_search,
  image_search_tool, understand_images_tool, process_docs, search_urls_tool, scrape_single_url)
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

Update the plan based on the feedback. Return the same JSON structure."""


def _build_plan_llm(tracker) -> ChatGroq:
    return ChatGroq(
        model=settings.GROQ_MODEL,
        temperature=0,
        api_key=settings.GROQ_API_KEY,
    ).with_config({"callbacks": [tracker]})


async def generate_plan(
    cleaned_prompt: str,
    username: str,
    ai_personality: str,
    qa_history: list[QAPair],
    sources: list[str],
    research_template: str,
    tracker,
) -> ResearchPlan:
    llm = _build_plan_llm(tracker)
    structured_llm = llm.with_structured_output(ResearchPlan)
    prompt = ChatPromptTemplate.from_template(_PLAN_PROMPT)
    chain = prompt | structured_llm

    qa_context = "\n".join(
        f"Q: {p.question}\nA: {p.answer}" for p in qa_history
    ) or "No clarifications provided."

    result: ResearchPlan = await chain.ainvoke({
        "username": username,
        "cleaned_prompt": cleaned_prompt,
        "ai_personality": ai_personality,
        "qa_context": qa_context,
        "sources": ", ".join(sources) or "None",
        "research_template": research_template or "No template provided — use best judgment.",
    })

    logger.info("[plan_gen] Generated %d steps", len(result.steps))
    return result


async def refine_plan(
    current_plan: ResearchPlan,
    feedback: str,
    tracker,
) -> ResearchPlan:
    llm = _build_plan_llm(tracker)
    structured_llm = llm.with_structured_output(ResearchPlan)
    prompt = ChatPromptTemplate.from_template(_REFINE_PROMPT)
    chain = prompt | structured_llm

    import json
    result: ResearchPlan = await chain.ainvoke({
        "current_plan": json.dumps([s.model_dump() for s in current_plan.steps], indent=2),
        "feedback": feedback,
    })
    logger.info("[plan_gen] Refined to %d steps", len(result.steps))
    return result
