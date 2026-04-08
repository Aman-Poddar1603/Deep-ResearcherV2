"""
Prompt cleaner — ChatOllama chain that:
  - Removes noise / stopwords
  - Compresses the prompt semantically
  - Generates title + description if not provided
"""

import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from research.config import settings
from research.models import CleanedInput

logger = logging.getLogger(__name__)

_CLEANER_PROMPT = """You are a research assistant pre-processor.

Given the user's raw research prompt, you must:
1. Remove filler words, stopwords, and noise while preserving all meaningful intent.
2. Compress the prompt into a clear, dense research query.
3. Generate a concise title (5–10 words) for this research.
4. Generate a 1–2 sentence description summarising what this research will cover.

If a title or description is already provided, improve them slightly but keep their meaning.

Provided title (may be empty): {provided_title}
Provided description (may be empty): {provided_description}

Raw prompt:
{raw_prompt}

Respond ONLY with a JSON object — no markdown, no explanation:
{{
  "cleaned_prompt": "...",
  "title": "...",
  "description": "..."
}}"""


def _fallback_title(raw_prompt: str, provided_title: str) -> str:
    if (provided_title or "").strip():
        return provided_title.strip()

    words = [w.strip(" ,.;:!?") for w in (raw_prompt or "").split()]
    words = [w for w in words if w]
    if not words:
        return "Research Analysis"

    return " ".join(words[:8])[:80]


def _fallback_description(
    cleaned_prompt: str,
    provided_description: str,
) -> str:
    if (provided_description or "").strip():
        return provided_description.strip()

    base = (cleaned_prompt or "").strip()
    if not base:
        return "Research requested by the user."

    if len(base) > 220:
        base = base[:217].rstrip() + "..."
    return f"This research covers: {base}"


def _normalize_cleaned_input(
    result: CleanedInput,
    raw_prompt: str,
    provided_title: str,
    provided_description: str,
) -> CleanedInput:
    cleaned_prompt = (result.cleaned_prompt or raw_prompt or "").strip()
    title = (result.title or "").strip() or _fallback_title(raw_prompt, provided_title)
    description = (result.description or "").strip() or _fallback_description(
        cleaned_prompt,
        provided_description,
    )

    return CleanedInput(
        cleaned_prompt=cleaned_prompt,
        title=title,
        description=description,
    )


def build_cleaner_chain():
    llm = ChatOllama(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0,
        reasoning=False,
        keep_alive=True,
    )

    structured_llm = llm.with_structured_output(CleanedInput)

    prompt = ChatPromptTemplate.from_template(_CLEANER_PROMPT)
    return prompt | structured_llm


async def run_cleaner(
    raw_prompt: str,
    provided_title: str,
    provided_description: str,
    tracker,
) -> CleanedInput:
    chain = build_cleaner_chain()
    try:
        result = await chain.ainvoke(
            {
                "raw_prompt": raw_prompt,
                "provided_title": provided_title or "",
                "provided_description": provided_description or "",
            },
            config={"callbacks": [tracker]},
        )
    except Exception as exc:
        logger.warning(
            "[cleaner] Structured parse failed, using deterministic fallback: %s",
            exc,
        )
        fallback_prompt = (raw_prompt or "").strip()
        return CleanedInput(
            cleaned_prompt=fallback_prompt,
            title=_fallback_title(raw_prompt, provided_title),
            description=_fallback_description(fallback_prompt, provided_description),
        )

    normalized = _normalize_cleaned_input(
        result=result,
        raw_prompt=raw_prompt,
        provided_title=provided_title,
        provided_description=provided_description,
    )
    logger.info("[cleaner] Cleaned prompt: %s", normalized.cleaned_prompt[:80])
    return normalized
