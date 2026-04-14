"""
agent_service.py — LangChain ReAct agent with MCP-backed tools.

Used when the query needs live document reading, web search, or
multi-step reasoning beyond what RAG chunks provide.
"""

from __future__ import annotations

from typing import AsyncIterator

from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from main.src.research.config import settings
from main.src.utils.core.task_schedular import scheduler
from main.src.utils.DRLogger import quickLog


async def _log(msg: str, level: str = "info", urgency: str = "none") -> None:
    await scheduler.schedule(
        quickLog, params={"message": msg, "level": level, "urgency": urgency}
    )


OLLAMA_HOST = settings.OLLAMA_BASE_URL
CHAT_MODEL = settings.OLLAMA_MODEL

SYSTEM_PROMPT = (
    "You are a research assistant. Use the provided context first, "
    "and answer clearly and concisely. If context is insufficient, say so."
)


# ── streaming agent runner ────────────────────────────────────────────────────


async def stream_agent_response(
    query: str,
    context: str,
) -> AsyncIterator[str]:
    """
    Run ReAct agent and yield text tokens.
    Falls back gracefully on agent errors.
    """
    llm = ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_HOST,
        temperature=0.2,
    )

    messages = [
        SystemMessage(content=f"{SYSTEM_PROMPT}\n\nContext:\n{context}"),
        HumanMessage(content=query),
    ]

    try:
        async for chunk in llm.astream(messages):
            token = chunk.content if isinstance(chunk.content, str) else ""
            if token:
                yield token
    except Exception as exc:
        await _log(f"Agent error: {exc}", level="error", urgency="critical")
        yield "I hit an error while generating a response."
