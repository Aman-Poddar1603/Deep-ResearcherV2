"""
TokenTracker — LangChain BaseCallbackHandler that intercepts every LLM response,
extracts token usage, atomically updates Redis, and fires a tokens.update WS event.

Attach to every LLM chain via:
    chain.with_config({"callbacks": [TokenTracker(...)]})
"""

import asyncio
import logging
from typing import Any

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult

from research.models import TokensUpdateEvent
from research.session import increment_tokens

logger = logging.getLogger(__name__)


class TokenTracker(AsyncCallbackHandler):
    def __init__(
        self,
        emitter,  # WSEmitter instance
        research_id: str,
        step_index: int,
        model_type: str,  # "ollama" or "groq"
        source: str,  # e.g. "ollama/gemma4:e2b"
    ):
        self.emitter = emitter
        self.research_id = research_id
        self.step_index = step_index
        self.model_type = model_type
        self.source = source

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        delta = self._extract_delta(response)
        if delta <= 0:
            return
        await self._record(delta)

    async def record_tool_tokens(self, token_count: int) -> None:
        """Call this after any MCP tool that returns its own token_count."""
        if token_count > 0:
            await self._record(token_count)

    async def _record(self, delta: int) -> None:
        try:
            totals = await increment_tokens(
                self.research_id, delta, self.model_type, self.step_index
            )
            event = TokensUpdateEvent(
                research_id=self.research_id,
                delta=delta,
                grand_total=totals["grand_total"],
                by_model=totals["by_model"],
                by_step=totals["by_step"],
                source=self.source,
                step_index=self.step_index,
            )
            await self.emitter.emit(event)
        except Exception as exc:
            logger.warning("[token_tracker] Failed to record tokens: %s", exc)

    @staticmethod
    def _extract_delta(response: LLMResult) -> int:
        # LangChain Groq / Ollama both populate llm_output["token_usage"]
        usage = (response.llm_output or {}).get("token_usage", {})
        total = usage.get("total_tokens", 0)
        if total:
            return int(total)
        # Fallback: sum prompt + completion
        return int(usage.get("prompt_tokens", 0)) + int(
            usage.get("completion_tokens", 0)
        )

    def clone(self, step_index: int) -> "TokenTracker":
        """Return a fresh tracker for a new step index."""
        return TokenTracker(
            emitter=self.emitter,
            research_id=self.research_id,
            step_index=step_index,
            model_type=self.model_type,
            source=self.source,
        )
