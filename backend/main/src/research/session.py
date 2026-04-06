"""
Redis session manager.

Key namespace: research:{research_id}:*
  :state            Hash  — status, current_step, total_steps, created_at
  :plan             str   — JSON plan array
  :context          str   — JSON ResearchContext
  :stop_flag        str   — "1" if stop requested
  :tokens:grand_total     int
  :tokens:model:ollama    int
  :tokens:model:groq      int
  :tokens:step:{N}        int
  :events                 pub/sub channel
  :langgraph:*            managed by RedisSaver
"""
import json
import logging
from datetime import datetime
from typing import Any

import redis.asyncio as aioredis

from research.config import settings

logger = logging.getLogger(__name__)

_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_pool


# ─── Key builders ─────────────────────────────────────────────────────────────

def _key(research_id: str, *parts: str) -> str:
    return f"research:{research_id}:{':'.join(parts)}"


# ─── Session lifecycle ────────────────────────────────────────────────────────

async def init_session(research_id: str, workspace_id: str, total_steps: int = 0) -> None:
    r = await get_redis()
    await r.hset(
        _key(research_id, "state"),
        mapping={
            "status": "initializing",
            "current_step": 0,
            "total_steps": total_steps,
            "workspace_id": workspace_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        },
    )
    logger.info("[session] Initialized session %s", research_id)


async def update_session_status(research_id: str, status: str, current_step: int | None = None) -> None:
    r = await get_redis()
    mapping: dict[str, Any] = {
        "status": status,
        "updated_at": datetime.utcnow().isoformat(),
    }
    if current_step is not None:
        mapping["current_step"] = current_step
    await r.hset(_key(research_id, "state"), mapping=mapping)


async def get_session_state(research_id: str) -> dict | None:
    r = await get_redis()
    state = await r.hgetall(_key(research_id, "state"))
    return state if state else None


async def save_context(research_id: str, context: dict) -> None:
    r = await get_redis()
    await r.set(_key(research_id, "context"), json.dumps(context))


async def load_context(research_id: str) -> dict | None:
    r = await get_redis()
    raw = await r.get(_key(research_id, "context"))
    return json.loads(raw) if raw else None


async def save_plan(research_id: str, plan: list[dict]) -> None:
    r = await get_redis()
    await r.set(_key(research_id, "plan"), json.dumps(plan))


async def load_plan(research_id: str) -> list[dict] | None:
    r = await get_redis()
    raw = await r.get(_key(research_id, "plan"))
    return json.loads(raw) if raw else None


# ─── Stop flag ────────────────────────────────────────────────────────────────

async def set_stop_flag(research_id: str) -> None:
    r = await get_redis()
    await r.set(_key(research_id, "stop_flag"), "1")
    logger.info("[session] Stop flag set for %s", research_id)


async def is_stop_requested(research_id: str) -> bool:
    r = await get_redis()
    return await r.exists(_key(research_id, "stop_flag")) == 1


async def clear_stop_flag(research_id: str) -> None:
    r = await get_redis()
    await r.delete(_key(research_id, "stop_flag"))


# ─── Token counters ───────────────────────────────────────────────────────────

async def increment_tokens(
    research_id: str,
    delta: int,
    model_type: str,
    step_index: int,
) -> dict:
    """Atomically increment all three token counter levels. Returns new totals."""
    r = await get_redis()
    pipe = r.pipeline()
    pipe.incrby(_key(research_id, "tokens", "grand_total"), delta)
    pipe.incrby(_key(research_id, "tokens", "model", model_type), delta)
    pipe.incrby(_key(research_id, "tokens", "step", str(step_index)), delta)
    await pipe.execute()
    return await get_token_totals(research_id)


async def get_token_totals(research_id: str) -> dict:
    r = await get_redis()
    grand = int(await r.get(_key(research_id, "tokens", "grand_total")) or 0)
    ollama = int(await r.get(_key(research_id, "tokens", "model", "ollama")) or 0)
    groq = int(await r.get(_key(research_id, "tokens", "model", "groq")) or 0)

    # Collect all step keys
    pattern = _key(research_id, "tokens", "step", "*")
    step_keys = [k async for k in r.scan_iter(pattern)]
    by_step: dict[str, int] = {}
    if step_keys:
        vals = await r.mget(*step_keys)
        for k, v in zip(step_keys, vals):
            step_label = k.split(":")[-1]
            by_step[f"step_{step_label}"] = int(v or 0)

    return {
        "grand_total": grand,
        "by_model": {"ollama": ollama, "groq": groq},
        "by_step": by_step,
    }


# ─── Pub/sub ──────────────────────────────────────────────────────────────────

async def publish_event(research_id: str, event_dict: dict) -> None:
    r = await get_redis()
    await r.publish(_key(research_id, "events"), json.dumps(event_dict))


async def get_pubsub(research_id: str):
    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(_key(research_id, "events"))
    return pubsub
