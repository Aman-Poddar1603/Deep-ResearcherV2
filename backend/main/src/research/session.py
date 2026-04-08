"""
Redis session manager.

Key namespace: research:{research_id}:*
  :state            Hash  — status, current_step, total_steps, created_at
  :plan             str   — JSON plan array
  :context          str   — JSON ResearchContext
    :pending_input    str   — JSON payload for waiting user interaction
  :stop_flag        str   — "1" if stop requested
  :tokens:grand_total     int
  :tokens:model:ollama    int
  :tokens:model:groq      int
  :tokens:step:{N}        int
    :events                 pub/sub channel (compat/live fanout)
    :events:stream          Redis stream (durable replay)
    :events:cursor          Hash of client_id -> last event id
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
_EVENT_STREAM_MAXLEN = 5000
_MAX_REPLAY_LIMIT = 2000
_MAX_SNAPSHOT_TAIL_LIMIT = _EVENT_STREAM_MAXLEN
_MAX_REASONING_PER_STEP_CHARS = 8000


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


def _events_channel_key(research_id: str) -> str:
    return _key(research_id, "events")


def _events_stream_key(research_id: str) -> str:
    return _key(research_id, "events", "stream")


def _events_cursor_key(research_id: str) -> str:
    return _key(research_id, "events", "cursor")


def _pending_input_key(research_id: str) -> str:
    return _key(research_id, "pending_input")


# ─── Session lifecycle ────────────────────────────────────────────────────────


async def init_session(
    research_id: str, workspace_id: str, total_steps: int = 0
) -> None:
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
            "latest_event_id": "",
            "events_count": 0,
        },
    )
    logger.info("[session] Initialized session %s", research_id)


async def update_session_status(
    research_id: str,
    status: str,
    current_step: int | None = None,
    total_steps: int | None = None,
) -> None:
    r = await get_redis()
    mapping: dict[str, Any] = {
        "status": status,
        "updated_at": datetime.utcnow().isoformat(),
    }
    if current_step is not None:
        mapping["current_step"] = current_step
    if total_steps is not None:
        mapping["total_steps"] = total_steps
    await r.hset(_key(research_id, "state"), mapping=mapping)


async def set_total_steps(research_id: str, total_steps: int) -> None:
    r = await get_redis()
    await r.hset(
        _key(research_id, "state"),
        mapping={
            "total_steps": total_steps,
            "updated_at": datetime.utcnow().isoformat(),
        },
    )


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


async def save_pending_input(
    research_id: str,
    input_type: str,
    payload: dict[str, Any],
) -> None:
    r = await get_redis()
    await r.set(
        _pending_input_key(research_id),
        json.dumps(
            {
                "type": input_type,
                "payload": payload,
                "updated_at": datetime.utcnow().isoformat(),
            }
        ),
    )


async def load_pending_input(research_id: str) -> dict | None:
    r = await get_redis()
    raw = await r.get(_pending_input_key(research_id))
    return json.loads(raw) if raw else None


async def clear_pending_input(research_id: str) -> None:
    r = await get_redis()
    await r.delete(_pending_input_key(research_id))


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
    input_delta: int | None = None,
    output_delta: int | None = None,
) -> dict:
    """Atomically increment all three token counter levels. Returns new totals."""
    if input_delta is None and output_delta is None:
        input_delta = 0
        output_delta = delta
    elif input_delta is None:
        input_delta = max(0, delta - int(output_delta or 0))
    elif output_delta is None:
        output_delta = max(0, delta - int(input_delta or 0))

    input_delta = max(0, int(input_delta or 0))
    output_delta = max(0, int(output_delta or 0))

    if input_delta + output_delta != delta:
        output_delta = max(0, delta - input_delta)

    r = await get_redis()
    pipe = r.pipeline()
    pipe.incrby(_key(research_id, "tokens", "grand_total"), delta)
    pipe.incrby(_key(research_id, "tokens", "input_total"), input_delta)
    pipe.incrby(_key(research_id, "tokens", "output_total"), output_delta)

    pipe.incrby(_key(research_id, "tokens", "model", model_type), delta)
    pipe.incrby(_key(research_id, "tokens", "model", model_type, "input"), input_delta)
    pipe.incrby(
        _key(research_id, "tokens", "model", model_type, "output"), output_delta
    )

    pipe.incrby(_key(research_id, "tokens", "step", str(step_index)), delta)
    pipe.incrby(
        _key(research_id, "tokens", "step", str(step_index), "input"), input_delta
    )
    pipe.incrby(
        _key(research_id, "tokens", "step", str(step_index), "output"), output_delta
    )
    await pipe.execute()
    return await get_token_totals(research_id)


async def get_token_totals(research_id: str) -> dict:
    r = await get_redis()
    grand = int(await r.get(_key(research_id, "tokens", "grand_total")) or 0)
    input_total = int(await r.get(_key(research_id, "tokens", "input_total")) or 0)
    output_total = int(await r.get(_key(research_id, "tokens", "output_total")) or 0)

    ollama = int(await r.get(_key(research_id, "tokens", "model", "ollama")) or 0)
    groq = int(await r.get(_key(research_id, "tokens", "model", "groq")) or 0)
    ollama_input = int(
        await r.get(_key(research_id, "tokens", "model", "ollama", "input")) or 0
    )
    ollama_output = int(
        await r.get(_key(research_id, "tokens", "model", "ollama", "output")) or 0
    )
    groq_input = int(
        await r.get(_key(research_id, "tokens", "model", "groq", "input")) or 0
    )
    groq_output = int(
        await r.get(_key(research_id, "tokens", "model", "groq", "output")) or 0
    )

    # Collect all step total keys (exclude step:{n}:input/output)
    pattern = _key(research_id, "tokens", "step", "*")
    step_keys = [k async for k in r.scan_iter(pattern)]
    by_step: dict[str, int] = {}
    by_step_direction: dict[str, dict[str, int]] = {}
    if step_keys:

        def _is_int_step_label(label: str) -> bool:
            return label.lstrip("-").isdigit()

        filtered_step_keys = [
            k for k in step_keys if _is_int_step_label(k.split(":")[-1])
        ]
        if filtered_step_keys:
            vals = await r.mget(*filtered_step_keys)
        else:
            vals = []

        for k, v in zip(filtered_step_keys, vals):
            step_label = k.split(":")[-1]
            by_step[f"step_{step_label}"] = int(v or 0)

            step_input = int(
                await r.get(_key(research_id, "tokens", "step", step_label, "input"))
                or 0
            )
            step_output = int(
                await r.get(_key(research_id, "tokens", "step", step_label, "output"))
                or 0
            )
            by_step_direction[f"step_{step_label}"] = {
                "input": step_input,
                "output": step_output,
            }

    return {
        "grand_total": grand,
        "by_direction": {"input": input_total, "output": output_total},
        "by_model": {"ollama": ollama, "groq": groq},
        "by_model_direction": {
            "ollama": {"input": ollama_input, "output": ollama_output},
            "groq": {"input": groq_input, "output": groq_output},
        },
        "by_step": by_step,
        "by_step_direction": by_step_direction,
    }


# ─── Pub/sub ──────────────────────────────────────────────────────────────────


async def publish_event(research_id: str, event_dict: dict) -> None:
    r = await get_redis()
    await r.publish(_events_channel_key(research_id), json.dumps(event_dict))


async def append_event(research_id: str, event_dict: dict) -> str:
    r = await get_redis()
    payload_json = json.dumps(event_dict, ensure_ascii=True)
    entry_id = await r.xadd(
        _events_stream_key(research_id),
        {
            "event": str(event_dict.get("event", "unknown")),
            "ts": str(event_dict.get("ts", "")),
            "payload": payload_json,
        },
        maxlen=_EVENT_STREAM_MAXLEN,
        approximate=True,
    )

    await r.hincrby(_key(research_id, "state"), "events_count", 1)
    await r.hset(
        _key(research_id, "state"),
        mapping={
            "latest_event_id": entry_id,
            "updated_at": datetime.utcnow().isoformat(),
        },
    )
    return entry_id


async def get_latest_event_id(research_id: str) -> str | None:
    r = await get_redis()
    entries = await r.xrevrange(_events_stream_key(research_id), count=1)
    if not entries:
        return None
    return str(entries[0][0])


async def replay_events(
    research_id: str,
    from_event_id: str = "0-0",
    limit: int = 200,
) -> list[dict[str, Any]]:
    r = await get_redis()
    bounded_limit = max(1, min(limit, _MAX_REPLAY_LIMIT))
    start_id = from_event_id.strip() if from_event_id else "0-0"
    min_id = "-" if start_id in ("0", "0-0") else f"({start_id}"

    entries = await r.xrange(
        _events_stream_key(research_id),
        min=min_id,
        max="+",
        count=bounded_limit,
    )

    replay_payload: list[dict[str, Any]] = []
    for entry_id, fields in entries:
        payload = _decode_stream_payload(research_id, fields)

        replay_payload.append(
            {
                "id": str(entry_id),
                "payload": payload,
            }
        )

    return replay_payload


def _decode_stream_payload(research_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    raw_payload = fields.get("payload") or "{}"
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        payload = {
            "event": "system.error",
            "research_id": research_id,
            "message": "Corrupted event payload in replay stream",
            "recoverable": True,
        }

    if not isinstance(payload, dict):
        return {
            "event": "system.error",
            "research_id": research_id,
            "message": "Unexpected non-object event payload in replay stream",
            "recoverable": True,
        }
    return payload


def _coerce_event_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        chunks: list[str] = []
        for item in value:
            if isinstance(item, str):
                chunks.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    chunks.append(text)
        return "".join(chunks)
    return ""


def _coerce_step_label(raw_step_index: Any) -> str:
    if isinstance(raw_step_index, int):
        return f"step_{raw_step_index}"
    if isinstance(raw_step_index, float):
        return f"step_{int(raw_step_index)}"
    if isinstance(raw_step_index, str) and raw_step_index.lstrip("-").isdigit():
        return f"step_{raw_step_index}"
    return "step_-1"


async def _collect_reasoning_by_step(
    r: aioredis.Redis,
    research_id: str,
) -> dict[str, str]:
    entries = await r.xrange(
        _events_stream_key(research_id),
        min="-",
        max="+",
        count=_EVENT_STREAM_MAXLEN,
    )

    reasoning_by_step: dict[str, str] = {}
    for _, fields in entries:
        payload = _decode_stream_payload(research_id, fields)
        if str(payload.get("event", "")) != "think.chunk":
            continue

        chunk = _coerce_event_text(payload.get("text", ""))
        if not chunk:
            continue

        step_label = _coerce_step_label(payload.get("step_index", -1))
        merged = reasoning_by_step.get(step_label, "") + chunk
        if len(merged) > _MAX_REASONING_PER_STEP_CHARS:
            merged = merged[-_MAX_REASONING_PER_STEP_CHARS:]
        reasoning_by_step[step_label] = merged

    return reasoning_by_step


async def get_streaming_snapshot(
    research_id: str,
    tail_limit: int = 600,
) -> dict[str, Any]:
    """
    Build a compact, UI-ready snapshot of in-progress streamed content and recent
    tool outputs from the event stream tail.
    """
    r = await get_redis()
    bounded_limit = max(50, min(tail_limit, _MAX_SNAPSHOT_TAIL_LIMIT))
    tail_entries = await r.xrevrange(
        _events_stream_key(research_id), count=bounded_limit
    )

    artifact_text = ""
    recent_tool_results: list[dict[str, Any]] = []

    # xrevrange returns newest->oldest; process oldest->newest for natural accumulation.
    for entry_id, fields in reversed(tail_entries):
        payload = _decode_stream_payload(research_id, fields)
        event_type = str(payload.get("event", ""))

        if event_type == "artifact.chunk":
            chunk = _coerce_event_text(payload.get("text", ""))
            if chunk:
                artifact_text += chunk
                if len(artifact_text) > 16000:
                    artifact_text = artifact_text[-16000:]

        elif event_type == "tool.result":
            recent_tool_results.append(
                {
                    "event_id": str(entry_id),
                    "tool_name": payload.get("tool_name", ""),
                    "step_index": payload.get("step_index", -1),
                    "result_summary": payload.get("result_summary", ""),
                    "result_payload": payload.get("result_payload", []),
                }
            )
            if len(recent_tool_results) > 20:
                recent_tool_results = recent_tool_results[-20:]

    reasoning_by_step = await _collect_reasoning_by_step(r, research_id)
    latest_event_id = str(tail_entries[0][0]) if tail_entries else None
    return {
        "latest_event_id": latest_event_id,
        "artifact_text": artifact_text,
        "thinking_by_step": reasoning_by_step,
        "recent_tool_results": recent_tool_results,
    }


async def get_event_cursor(research_id: str, client_id: str) -> str | None:
    r = await get_redis()
    cursor = await r.hget(_events_cursor_key(research_id), client_id)
    return str(cursor) if cursor else None


async def set_event_cursor(research_id: str, client_id: str, event_id: str) -> None:
    r = await get_redis()
    await r.hset(_events_cursor_key(research_id), client_id, event_id)


async def get_pubsub(research_id: str):
    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(_events_channel_key(research_id))
    return pubsub
