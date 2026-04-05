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


def build_cleaner_chain(tracker):
    llm = ChatOllama(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0,
        reasoning=False,
        keep_alive=True,
    ).with_config({"callbacks": [tracker]})

    structured_llm = llm.with_structured_output(CleanedInput)

    prompt = ChatPromptTemplate.from_template(_CLEANER_PROMPT)
    return prompt | structured_llm


async def run_cleaner(
    raw_prompt: str,
    provided_title: str,
    provided_description: str,
    tracker,
) -> CleanedInput:
    chain = build_cleaner_chain(tracker)
    result = await chain.ainvoke(
        {
            "raw_prompt": raw_prompt,
            "provided_title": provided_title or "",
            "provided_description": provided_description or "",
        }
    )
    logger.info("[cleaner] Cleaned prompt: %s", result.cleaned_prompt[:80])
    return result
