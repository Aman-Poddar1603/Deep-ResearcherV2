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
        model_type: str,  # "ollama", "groq", or "gemini"
        source: str,  # e.g. "ollama/gemma4:e2b"
    ):
        self.emitter = emitter
        self.research_id = research_id
        self.step_index = step_index
        self.model_type = model_type
        self.source = source
        # Some providers may invoke both chat/llm end callbacks for one run.
        self._seen_run_ids: set[str] = set()
        self._seen_run_ids_lock = asyncio.Lock()

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        await self._record_if_new_run(response, **kwargs)

    async def on_chat_model_end(self, response: LLMResult, **kwargs: Any) -> None:
        await self._record_if_new_run(response, **kwargs)

    async def record_tool_tokens(self, token_count: int) -> None:
        """Call this after any MCP tool that returns its own token_count."""
        if token_count > 0:
            await self._record(token_count, input_delta=0, output_delta=token_count)

    async def record_explicit_tokens(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        """Record explicit input/output deltas when provider callbacks are unavailable."""
        input_delta = max(0, int(input_tokens or 0))
        output_delta = max(0, int(output_tokens or 0))
        delta = input_delta + output_delta
        if delta <= 0:
            return
        await self._record(delta, input_delta=input_delta, output_delta=output_delta)

    async def _record(
        self,
        delta: int,
        input_delta: int | None = None,
        output_delta: int | None = None,
    ) -> None:
        try:
            totals = await increment_tokens(
                self.research_id,
                delta,
                self.model_type,
                self.step_index,
                input_delta=input_delta,
                output_delta=output_delta,
            )
            event = TokensUpdateEvent(
                research_id=self.research_id,
                delta=delta,
                input_delta=(input_delta if input_delta is not None else 0),
                output_delta=(
                    output_delta
                    if output_delta is not None
                    else max(0, delta - int(input_delta or 0))
                ),
                grand_total=totals["grand_total"],
                by_direction=totals.get(
                    "by_direction", {"input": 0, "output": totals["grand_total"]}
                ),
                by_model=totals["by_model"],
                by_step=totals["by_step"],
                source=self.source,
                step_index=self.step_index,
            )
            await self.emitter.emit(event)
        except Exception as exc:
            logger.warning("[token_tracker] Failed to record tokens: %s", exc)

    async def _record_if_new_run(self, response: LLMResult, **kwargs: Any) -> None:
        run_id = kwargs.get("run_id")
        if run_id is not None:
            run_id_str = str(run_id)
            async with self._seen_run_ids_lock:
                if run_id_str in self._seen_run_ids:
                    return
                if len(self._seen_run_ids) >= 512:
                    self._seen_run_ids.clear()
                self._seen_run_ids.add(run_id_str)

        delta, input_delta, output_delta = self._extract_usage(response)
        if delta > 0:
            await self._record(
                delta,
                input_delta=input_delta,
                output_delta=output_delta,
            )

    @staticmethod
    def _to_int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @classmethod
    def _usage_total(cls, payload: Any) -> int:
        if not isinstance(payload, dict):
            return 0

        for total_key in ("total_tokens", "total_token_count", "total"):
            total = cls._to_int(payload.get(total_key))
            if total > 0:
                return total

        for prompt_key, completion_key in (
            ("prompt_tokens", "completion_tokens"),
            ("input_tokens", "output_tokens"),
            ("prompt_eval_count", "eval_count"),
            ("input_token_count", "output_token_count"),
            ("prompt_tokens", "output_tokens"),
        ):
            prompt = cls._to_int(payload.get(prompt_key))
            completion = cls._to_int(payload.get(completion_key))
            if prompt > 0 or completion > 0:
                return prompt + completion

        for single_key in ("completion_tokens", "output_tokens", "eval_count"):
            value = cls._to_int(payload.get(single_key))
            if value > 0:
                return value

        for nested_key in (
            "token_usage",
            "usage",
            "usage_metadata",
            "usageMetadata",
            "metadata",
        ):
            nested_total = cls._usage_total(payload.get(nested_key))
            if nested_total > 0:
                return nested_total

        return 0

    @classmethod
    def _usage_breakdown(cls, payload: Any) -> tuple[int, int, int]:
        if not isinstance(payload, dict):
            return (0, 0, 0)

        input_tokens = 0
        output_tokens = 0

        for key in (
            "prompt_tokens",
            "input_tokens",
            "prompt_eval_count",
            "input_token_count",
        ):
            value = cls._to_int(payload.get(key))
            if value > 0:
                input_tokens = max(input_tokens, value)

        for key in (
            "completion_tokens",
            "output_tokens",
            "eval_count",
            "output_token_count",
        ):
            value = cls._to_int(payload.get(key))
            if value > 0:
                output_tokens = max(output_tokens, value)

        total_tokens = 0
        for key in ("total_tokens", "total_token_count", "total"):
            value = cls._to_int(payload.get(key))
            if value > 0:
                total_tokens = max(total_tokens, value)

        if total_tokens == 0 and (input_tokens > 0 or output_tokens > 0):
            total_tokens = input_tokens + output_tokens

        # If only total is known, allocate to output bucket for accounting visibility.
        if total_tokens > 0 and input_tokens == 0 and output_tokens == 0:
            output_tokens = total_tokens

        if total_tokens > 0:
            return (total_tokens, input_tokens, output_tokens)

        for nested_key in (
            "token_usage",
            "usage",
            "usage_metadata",
            "usageMetadata",
            "metadata",
        ):
            nested = cls._usage_breakdown(payload.get(nested_key))
            if nested[0] > 0:
                return nested

        return (0, 0, 0)

    @classmethod
    def _extract_usage(cls, response: LLMResult) -> tuple[int, int, int]:
        # Provider-level output (OpenAI/Groq style).
        usage = cls._usage_breakdown(response.llm_output or {})
        if usage[0] > 0:
            return usage

        # Generation-level output (ChatOllama/ChatGroq usage_metadata patterns).
        for generation_group in response.generations or []:
            for generation in generation_group:
                usage = cls._usage_breakdown(
                    getattr(generation, "generation_info", None)
                )
                if usage[0] > 0:
                    return usage

                message = getattr(generation, "message", None)
                if message is None:
                    continue

                usage = cls._usage_breakdown(getattr(message, "usage_metadata", None))
                if usage[0] > 0:
                    return usage

                usage = cls._usage_breakdown(
                    getattr(message, "response_metadata", None)
                )
                if usage[0] > 0:
                    return usage

        return (0, 0, 0)

    def clone(self, step_index: int) -> "TokenTracker":
        """Return a fresh tracker for a new step index."""
        return TokenTracker(
            emitter=self.emitter,
            research_id=self.research_id,
            step_index=step_index,
            model_type=self.model_type,
            source=self.source,
        )
