"""
Groq clarification Q&A loop.

Asks the user up to MAX_QA_ROUNDS questions over WebSocket to extract
the knowledge needed to build a solid research plan.

Uses ChatGroq with tool access (user may mention URLs the agent can inspect).
Conversation history is accumulated in-process and passed back each round.
"""

import asyncio
import json
import logging
from typing import Any

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from research.config import settings
from research.models import (
    QAPair,
    NextQuestion,
    InputQAQuestionEvent,
)

logger = logging.getLogger(__name__)

_QA_SYSTEM = """You are a research planning assistant talking to {username}.
Your job is to ask clarifying questions to fully understand what the user wants to research.

Research topic: {topic}

Ask ONE focused question at a time. When you have gathered enough information to build a
comprehensive research plan (or after {max_rounds} rounds), respond with:
{{"question": "", "done": true}}

Otherwise respond with:
{{"question": "your question here", "done": false}}

IMPORTANT: "question" must always be a string. Never output null.

Do NOT answer the question yourself. Only ask.
Respond ONLY with the JSON — no markdown, no extra text."""


def _build_qa_llm(tracker) -> ChatGroq:
    return ChatGroq(
        model=settings.GROQ_MODEL,
        temperature=0.3,
        api_key=settings.GROQ_API_KEY,
    ).with_config({"callbacks": [tracker]})


def _preferred_structured_method() -> str:
    model_name = (settings.GROQ_MODEL or "").lower()
    return "function_calling" if "llama" in model_name else "json_mode"


def _ordered_structured_methods() -> list[str]:
    primary = _preferred_structured_method()
    secondary = "json_mode" if primary == "function_calling" else "function_calling"
    return [primary, secondary]


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


def _try_parse_json(text: str) -> Any:
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Empty model response")

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

    first_obj, last_obj = cleaned.find("{"), cleaned.rfind("}")
    if first_obj != -1 and last_obj > first_obj:
        return json.loads(cleaned[first_obj : last_obj + 1])

    raise ValueError("Could not parse JSON from model response")


def _parse_next_question_response(response: Any) -> NextQuestion:
    if isinstance(response, NextQuestion):
        return response

    if isinstance(response, dict):
        parsed = response.get("parsed")
        if parsed is not None:
            if isinstance(parsed, NextQuestion):
                return parsed
            if isinstance(parsed, dict):
                return NextQuestion.model_validate(parsed)

        raw = response.get("raw")
        if raw is not None:
            text = _extract_text_from_raw_message(raw)
            payload = _try_parse_json(text)
            if isinstance(payload, dict):
                return NextQuestion.model_validate(payload)

    if isinstance(response, dict):
        return NextQuestion.model_validate(response)

    raise ValueError(
        f"Unsupported NextQuestion payload type: {type(response).__name__}"
    )


async def _invoke_next_question_with_fallback(
    llm: ChatGroq,
    messages: list,
) -> NextQuestion:
    errors: list[str] = []

    for method in _ordered_structured_methods():
        llm_with_structure = llm.with_structured_output(
            NextQuestion,
            method=method,
            include_raw=True,
        )
        try:
            response = await llm_with_structure.ainvoke(messages)
            result = _parse_next_question_response(response)
            logger.info("[qa_loop] Structured-output method succeeded: %s", method)
            return result
        except Exception as exc:
            errors.append(f"{method}: {exc}")
            logger.warning(
                "[qa_loop] Structured-output method failed (%s): %s", method, exc
            )

    raise RuntimeError(
        "Failed to parse NextQuestion using all structured-output methods: "
        + " | ".join(errors)
    )


async def run_qa_loop(
    cleaned_prompt: str,
    username: str,
    emitter,
    tracker,
    answer_queue: asyncio.Queue,
    mcp_tools: list,
    research_id: str,
) -> list[QAPair]:
    """
    Drives the Q&A loop. Emits InputQAQuestionEvent for each question,
    then awaits user.answer from the WS queue.
    Returns accumulated list of QAPair.
    """
    _ = mcp_tools

    llm = _build_qa_llm(tracker)

    history: list[QAPair] = []
    messages = [
        SystemMessage(
            content=_QA_SYSTEM.format(
                username=username,
                topic=cleaned_prompt,
                max_rounds=settings.MAX_QA_ROUNDS,
            )
        )
    ]

    for round_idx in range(settings.MAX_QA_ROUNDS):
        # Build context from history
        context_str = "\n".join(f"Q: {p.question}\nA: {p.answer}" for p in history)
        messages.append(
            HumanMessage(
                content=f"Conversation so far:\n{context_str or 'None yet.'}\n\nGenerate next question or done."
            )
        )

        result = await _invoke_next_question_with_fallback(llm, messages)

        if result.done or not (result.question or "").strip():
            logger.info("[qa_loop] Done after %d rounds", round_idx)
            break

        # Emit question to frontend
        await emitter.emit(
            InputQAQuestionEvent(
                research_id=research_id,
                question=result.question,
                question_index=round_idx,
            )
        )

        # Await user answer from WS queue until user responds.
        user_answer: str = await answer_queue.get()

        history.append(QAPair(question=result.question, answer=user_answer))
        messages.append(AIMessage(content=f"Question: {result.question}"))
        messages.append(HumanMessage(content=f"Answer: {user_answer}"))

    return history
