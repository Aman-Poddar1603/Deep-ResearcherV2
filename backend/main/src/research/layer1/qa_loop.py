"""
Groq clarification Q&A loop.

Asks the user up to MAX_QA_ROUNDS questions over WebSocket to extract
the knowledge needed to build a solid research plan.

Uses ChatGroq with tool access (user may mention URLs the agent can inspect).
Conversation history is accumulated in-process and passed back each round.
"""

import asyncio
import logging

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate

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
{{"question": null, "done": true}}

Otherwise respond with:
{{"question": "your question here", "done": false}}

Do NOT answer the question yourself. Only ask.
Respond ONLY with the JSON — no markdown, no extra text."""


def _build_qa_llm(tracker) -> ChatGroq:
    return ChatGroq(
        model=settings.GROQ_MODEL,
        temperature=0.3,
        api_key=settings.GROQ_API_KEY,
    ).with_config({"callbacks": [tracker]})


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
    # Keep QA generation in strict structured-output mode.
    # Binding external tools here can conflict with Groq's function-calling and
    # produce tool_use_failed errors for the NextQuestion schema.
    # MCP tools are still used in later research orchestration stages.
    llm_with_tools = llm.with_structured_output(NextQuestion)

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

        result: NextQuestion = await llm_with_tools.ainvoke(messages)

        if result.done or result.question is None:
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

        # Await user answer from WS queue (with timeout)
        try:
            user_answer: str = await asyncio.wait_for(answer_queue.get(), timeout=300)
        except asyncio.TimeoutError:
            logger.warning(
                "[qa_loop] Timeout waiting for answer on round %d", round_idx
            )
            break

        history.append(QAPair(question=result.question, answer=user_answer))
        messages.append(AIMessage(content=f"Question: {result.question}"))
        messages.append(HumanMessage(content=f"Answer: {user_answer}"))

    return history
