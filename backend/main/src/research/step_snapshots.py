from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any

from main.src.store.DBManager import researches_db_manager

logger = logging.getLogger(__name__)

STEP_SNAPSHOT_TABLE = "research_step_snapshots"
_MAX_THINK_CHARS = 20000
_MAX_CHAIN_ITEMS = 800
_MAX_TOOL_CALLS = 200

_SUPPORTED_EVENT_TYPES = {
    "plan.step_started",
    "plan.step_completed",
    "plan.step_failed",
    "think_event",
    "react.reason",
    "chain_of_thought",
    "tool.called",
    "tool_call_query",
    "tool.result",
    "tool_call_output",
    "tool.error",
    "react.done",
}


def _utcnow_iso() -> str:
    return datetime.utcnow().isoformat()


def _safe_json_dump(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=True)
    except (TypeError, ValueError):
        return json.dumps({}, ensure_ascii=True)


def _coerce_step_index(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.lstrip("-").isdigit():
        return int(value)
    return None


def _coerce_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    try:
        return json.dumps(value, ensure_ascii=True)
    except (TypeError, ValueError):
        return str(value)


def _trim_list(items: list[Any], max_items: int) -> list[Any]:
    if len(items) <= max_items:
        return items
    return items[-max_items:]


def _default_content() -> dict[str, Any]:
    return {
        "think": "",
        "chain_of_thought": [],
        "tool_call": [],
        "summary": "",
    }


def _normalize_tool_entry(entry: Any) -> dict[str, Any] | None:
    if not isinstance(entry, dict):
        return None

    tool = _coerce_text(entry.get("tool", "")).strip()
    input_payload = entry.get("input", "")
    output_payload = entry.get("output", "")

    if not tool and input_payload in (None, "") and output_payload in (None, ""):
        return None

    return {
        "tool": tool,
        "input": input_payload,
        "output": output_payload,
    }


def _normalize_chain_item(item: Any) -> str | dict[str, Any] | None:
    if isinstance(item, str):
        text = item.strip()
        if not text:
            return None
        return text

    if isinstance(item, dict):
        return _normalize_tool_entry(item)

    return None


def normalize_step_content(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return _default_content()

    think = _coerce_text(raw.get("think", ""))
    if len(think) > _MAX_THINK_CHARS:
        think = think[-_MAX_THINK_CHARS:]

    chain_raw = raw.get("chain_of_thought", [])
    chain_of_thought: list[str | dict[str, Any]] = []
    if isinstance(chain_raw, list):
        for item in chain_raw:
            normalized = _normalize_chain_item(item)
            if normalized is not None:
                chain_of_thought.append(normalized)

    tool_call_raw = raw.get("tool_call", [])
    tool_call: list[dict[str, Any]] = []
    if isinstance(tool_call_raw, list):
        for item in tool_call_raw:
            normalized = _normalize_tool_entry(item)
            if normalized is not None:
                tool_call.append(normalized)

    summary = _coerce_text(raw.get("summary", "")).strip()

    return {
        "think": think,
        "chain_of_thought": _trim_list(chain_of_thought, _MAX_CHAIN_ITEMS),
        "tool_call": _trim_list(tool_call, _MAX_TOOL_CALLS),
        "summary": summary,
    }


def parse_structured_artifact(raw_artifact: Any) -> dict[str, Any] | None:
    if raw_artifact in (None, ""):
        return None

    parsed: Any = raw_artifact

    if isinstance(raw_artifact, str):
        stripped = raw_artifact.strip()
        if not stripped:
            return None
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            parsed = {"type": "md", "content": raw_artifact, "complete": False}

    if isinstance(parsed, str):
        parsed = {"type": "md", "content": parsed, "complete": False}

    if not isinstance(parsed, dict):
        return None

    content = _coerce_text(parsed.get("content", ""))
    if not content:
        return None

    artifact = {
        "type": _coerce_text(parsed.get("type", "md")) or "md",
        "content": content,
        "complete": bool(parsed.get("complete", False)),
    }

    if "tokens_used" in parsed:
        try:
            artifact["tokens_used"] = int(parsed.get("tokens_used") or 0)
        except (TypeError, ValueError):
            artifact["tokens_used"] = 0

    if "updated_at" in parsed and parsed.get("updated_at"):
        artifact["updated_at"] = _coerce_text(parsed.get("updated_at"))

    return artifact


def _decode_content_json(raw_content: Any) -> dict[str, Any]:
    if isinstance(raw_content, dict):
        return normalize_step_content(raw_content)

    if isinstance(raw_content, str):
        try:
            decoded = json.loads(raw_content)
            return normalize_step_content(decoded)
        except json.JSONDecodeError:
            return _default_content()

    return _default_content()


def _append_think_block(content: dict[str, Any], text: str) -> None:
    text = text.strip()
    if not text:
        return

    existing = _coerce_text(content.get("think", ""))
    merged = f"{existing}\n{text}".strip() if existing else text
    if len(merged) > _MAX_THINK_CHARS:
        merged = merged[-_MAX_THINK_CHARS:]

    content["think"] = merged
    chain = list(content.get("chain_of_thought", []))
    chain.append(text)
    content["chain_of_thought"] = _trim_list(chain, _MAX_CHAIN_ITEMS)


def _append_chain_token(content: dict[str, Any], token: str) -> None:
    token = token.strip()
    if not token:
        return

    chain = list(content.get("chain_of_thought", []))
    chain.append(token)
    content["chain_of_thought"] = _trim_list(chain, _MAX_CHAIN_ITEMS)


def _append_tool_call(
    content: dict[str, Any], tool_name: str, input_payload: Any
) -> None:
    entry = {
        "tool": _coerce_text(tool_name).strip(),
        "input": input_payload,
        "output": "",
    }

    calls = list(content.get("tool_call", []))
    calls.append(entry)
    content["tool_call"] = _trim_list(calls, _MAX_TOOL_CALLS)

    chain = list(content.get("chain_of_thought", []))
    chain.append(entry)
    content["chain_of_thought"] = _trim_list(chain, _MAX_CHAIN_ITEMS)


def _attach_tool_output(
    content: dict[str, Any],
    tool_name: str,
    output_payload: Any,
) -> None:
    calls = list(content.get("tool_call", []))
    normalized_tool = _coerce_text(tool_name).strip()
    resolved_input: Any = ""

    for idx in range(len(calls) - 1, -1, -1):
        entry = calls[idx]
        if not isinstance(entry, dict):
            continue
        if _coerce_text(entry.get("tool", "")).strip() != normalized_tool:
            continue
        if entry.get("output", "") not in ("", None):
            continue

        resolved_input = entry.get("input", "")
        entry["output"] = output_payload
        calls[idx] = entry
        break
    else:
        calls.append(
            {
                "tool": normalized_tool,
                "input": "",
                "output": output_payload,
            }
        )

    content["tool_call"] = _trim_list(calls, _MAX_TOOL_CALLS)

    chain = list(content.get("chain_of_thought", []))
    chain.append(
        {
            "tool": normalized_tool,
            "input": resolved_input,
            "output": output_payload,
        }
    )
    content["chain_of_thought"] = _trim_list(chain, _MAX_CHAIN_ITEMS)


def _fetch_all_rows_sync(research_id: str) -> list[dict[str, Any]]:
    result = researches_db_manager.fetch_all(
        STEP_SNAPSHOT_TABLE,
        where={"research_id": research_id},
    )
    if not result.get("success"):
        return []
    rows = result.get("data") or []
    return [row for row in rows if isinstance(row, dict)]


def _upsert_snapshot_row_sync(
    *,
    research_id: str,
    step_index: int,
    step_title: str,
    step_description: str,
    status: str,
    content: dict[str, Any],
    last_event_id: str,
    started_at: str | None,
    completed_at: str | None,
) -> None:
    now = _utcnow_iso()
    rows = _fetch_all_rows_sync(research_id)
    existing = next(
        (r for r in rows if _coerce_step_index(r.get("step_index")) == step_index), None
    )

    payload = {
        "research_id": research_id,
        "step_index": step_index,
        "step_title": step_title,
        "step_description": step_description,
        "status": status,
        "content_json": _safe_json_dump(normalize_step_content(content)),
        "last_event_id": last_event_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "updated_at": now,
    }

    if existing and existing.get("id"):
        researches_db_manager.update(
            STEP_SNAPSHOT_TABLE,
            data=payload,
            where={"id": existing.get("id")},
        )
        return

    payload["id"] = str(uuid.uuid4())
    payload["created_at"] = now
    researches_db_manager.insert(STEP_SNAPSHOT_TABLE, payload)


def _event_output_payload(payload: dict[str, Any]) -> Any:
    result_payload = payload.get("result_payload")
    if result_payload not in (None, "", []):
        return result_payload

    summary = payload.get("result_summary") or payload.get("summary")
    if summary not in (None, ""):
        return summary

    error = payload.get("error")
    if error not in (None, ""):
        return {"error": _coerce_text(error)}

    return ""


def _apply_event_to_snapshot(
    existing_row: dict[str, Any] | None,
    payload: dict[str, Any],
    event_id: str,
) -> dict[str, Any] | None:
    event_type = _coerce_text(payload.get("event", "")).strip()
    if event_type not in _SUPPORTED_EVENT_TYPES:
        return None

    step_index = _coerce_step_index(payload.get("step_index"))
    if step_index is None:
        return None

    content = _decode_content_json((existing_row or {}).get("content_json"))

    status = _coerce_text((existing_row or {}).get("status", "pending")) or "pending"
    step_title = _coerce_text((existing_row or {}).get("step_title", "")).strip()
    step_description = _coerce_text(
        (existing_row or {}).get("step_description", "")
    ).strip()
    started_at = (
        _coerce_text((existing_row or {}).get("started_at", "")).strip() or None
    )
    completed_at = (
        _coerce_text((existing_row or {}).get("completed_at", "")).strip() or None
    )

    ts = _coerce_text(payload.get("ts", "")).strip() or None

    if event_type == "plan.step_started":
        status = "running"
        step_title = _coerce_text(payload.get("step_title", step_title)).strip()
        if started_at is None:
            started_at = ts

    elif event_type in {"think_event", "react.reason"}:
        thought = payload.get("thought") or payload.get("text") or ""
        _append_think_block(content, _coerce_text(thought))

    elif event_type == "chain_of_thought":
        token = payload.get("token", "")
        _append_chain_token(content, _coerce_text(token))

    elif event_type in {"tool.called", "tool_call_query"}:
        tool_name = payload.get("tool_name", "")
        input_payload = payload.get("args")
        if input_payload is None:
            input_payload = payload.get("input", "")
        _append_tool_call(content, _coerce_text(tool_name), input_payload)

    elif event_type in {"tool.result", "tool_call_output", "tool.error"}:
        tool_name = payload.get("tool_name", "")
        output_payload = _event_output_payload(payload)
        _attach_tool_output(content, _coerce_text(tool_name), output_payload)

    elif event_type == "plan.step_completed":
        status = "completed"
        summary = _coerce_text(payload.get("summary", "")).strip()
        if summary:
            content["summary"] = summary
        completed_at = ts

    elif event_type == "plan.step_failed":
        status = "failed"
        error = _coerce_text(payload.get("error", "")).strip()
        if error:
            content["summary"] = error
        completed_at = ts

    elif event_type == "react.done":
        summary = payload.get("data", {}).get("summary", "")
        summary_text = _coerce_text(summary).strip()
        if summary_text and not _coerce_text(content.get("summary", "")).strip():
            content["summary"] = summary_text

    return {
        "research_id": payload.get("research_id", ""),
        "step_index": step_index,
        "step_title": step_title,
        "step_description": step_description,
        "status": status,
        "content": normalize_step_content(content),
        "last_event_id": event_id,
        "started_at": started_at,
        "completed_at": completed_at,
    }


def _upsert_from_event_sync(
    research_id: str,
    payload: dict[str, Any],
    event_id: str | None,
) -> None:
    rows = _fetch_all_rows_sync(research_id)
    step_index = _coerce_step_index(payload.get("step_index"))
    existing = None
    if step_index is not None:
        existing = next(
            (
                row
                for row in rows
                if _coerce_step_index(row.get("step_index")) == step_index
            ),
            None,
        )

    event_id_value = _coerce_text(event_id or payload.get("event_id") or "")
    snapshot = _apply_event_to_snapshot(existing, payload, event_id_value)
    if not snapshot:
        return

    _upsert_snapshot_row_sync(
        research_id=research_id,
        step_index=int(snapshot["step_index"]),
        step_title=_coerce_text(snapshot.get("step_title", "")),
        step_description=_coerce_text(snapshot.get("step_description", "")),
        status=_coerce_text(snapshot.get("status", "pending")) or "pending",
        content=snapshot.get("content", _default_content()),
        last_event_id=event_id_value,
        started_at=snapshot.get("started_at"),
        completed_at=snapshot.get("completed_at"),
    )


async def upsert_step_snapshot_from_event(
    research_id: str,
    payload: dict[str, Any],
    event_id: str | None = None,
) -> None:
    if not isinstance(payload, dict):
        return

    event_type = _coerce_text(payload.get("event", "")).strip()
    if event_type not in _SUPPORTED_EVENT_TYPES:
        return

    step_index = _coerce_step_index(payload.get("step_index"))
    if step_index is None:
        return

    await asyncio.to_thread(_upsert_from_event_sync, research_id, payload, event_id)


async def seed_step_snapshots_from_plan(
    research_id: str,
    plan: list[dict[str, Any]],
) -> None:
    def _seed_sync() -> None:
        rows = _fetch_all_rows_sync(research_id)
        by_step: dict[int, dict[str, Any]] = {}
        for row in rows:
            idx = _coerce_step_index(row.get("step_index"))
            if idx is not None:
                by_step[idx] = row

        now = _utcnow_iso()
        for i, step in enumerate(plan):
            step_index = _coerce_step_index(step.get("step_index"))
            if step_index is None:
                step_index = i

            title = _coerce_text(step.get("step_title", "")).strip()
            description = _coerce_text(step.get("step_description", "")).strip()

            existing = by_step.get(step_index)
            if existing and existing.get("id"):
                patch: dict[str, Any] = {"updated_at": now}
                if not _coerce_text(existing.get("step_title", "")).strip() and title:
                    patch["step_title"] = title
                if (
                    not _coerce_text(existing.get("step_description", "")).strip()
                    and description
                ):
                    patch["step_description"] = description

                if len(patch) > 1:
                    researches_db_manager.update(
                        STEP_SNAPSHOT_TABLE,
                        data=patch,
                        where={"id": existing.get("id")},
                    )
                continue

            researches_db_manager.insert(
                STEP_SNAPSHOT_TABLE,
                {
                    "id": str(uuid.uuid4()),
                    "research_id": research_id,
                    "step_index": step_index,
                    "step_title": title,
                    "step_description": description,
                    "status": "pending",
                    "content_json": _safe_json_dump(_default_content()),
                    "last_event_id": "",
                    "started_at": None,
                    "completed_at": None,
                    "created_at": now,
                    "updated_at": now,
                },
            )

    await asyncio.to_thread(_seed_sync)


def _plan_step_map(plan: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    mapped: dict[int, dict[str, Any]] = {}
    for i, step in enumerate(plan):
        if not isinstance(step, dict):
            continue
        idx = _coerce_step_index(step.get("step_index"))
        if idx is None:
            idx = i
        mapped[idx] = step
    return mapped


def _snapshot_row_to_step(
    row: dict[str, Any],
    plan_info: dict[str, Any] | None,
) -> dict[str, Any]:
    step_index = _coerce_step_index(row.get("step_index"))
    if step_index is None:
        step_index = -1

    title = _coerce_text(row.get("step_title", "")).strip()
    description = _coerce_text(row.get("step_description", "")).strip()
    status = _coerce_text(row.get("status", "pending")).strip() or "pending"
    content = _decode_content_json(row.get("content_json"))

    if plan_info:
        if not title:
            title = _coerce_text(plan_info.get("step_title", "")).strip()
        if not description:
            description = _coerce_text(plan_info.get("step_description", "")).strip()

    if not description and title:
        description = title
    if not description:
        description = (
            f"Step {step_index + 1}" if step_index >= 0 else f"Step {step_index}"
        )

    return {
        "step": step_index + 1 if step_index >= 0 else step_index,
        "step_index": step_index,
        "title": title,
        "description": description,
        "status": status,
        "content": content,
    }


def predictable_steps_from_step_details(
    step_details: list[dict[str, Any]],
    plan: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    plan_by_step = _plan_step_map(plan)
    predictable: list[dict[str, Any]] = []

    for raw in step_details:
        if not isinstance(raw, dict):
            continue

        step_index = _coerce_step_index(raw.get("step_index"))
        if step_index is None:
            step_index = -1

        plan_info = plan_by_step.get(step_index, {})
        title = (
            _coerce_text(raw.get("step_title", "")).strip()
            or _coerce_text(plan_info.get("step_title", "")).strip()
        )
        description = (
            _coerce_text(raw.get("step_description", "")).strip()
            or _coerce_text(plan_info.get("step_description", "")).strip()
        )

        thinking_blocks = raw.get("thinking_blocks", [])
        think_parts: list[str] = []
        if isinstance(thinking_blocks, list):
            for block in thinking_blocks:
                if isinstance(block, dict):
                    text = _coerce_text(block.get("text", "")).strip()
                    if text:
                        think_parts.append(text)

        chain_tokens = raw.get("chain_of_thought_tokens", [])
        chain_of_thought: list[str | dict[str, Any]] = []
        if isinstance(chain_tokens, list):
            for token in chain_tokens:
                if isinstance(token, dict):
                    text = _coerce_text(token.get("token", "")).strip()
                    if text:
                        chain_of_thought.append(text)

        tool_calls = raw.get("tool_calls", [])
        normalized_tool_calls: list[dict[str, Any]] = []
        if isinstance(tool_calls, list):
            for item in tool_calls:
                if not isinstance(item, dict):
                    continue
                entry = {
                    "tool": _coerce_text(item.get("tool_name", "")).strip(),
                    "input": item.get("args", {}),
                    "output": item.get("result_payload", []),
                }
                if entry["output"] in (None, "", []):
                    entry["output"] = _coerce_text(item.get("summary", "")).strip()
                normalized_tool_calls.append(entry)
                chain_of_thought.append(entry)

        content = normalize_step_content(
            {
                "think": "\n".join(think_parts).strip(),
                "chain_of_thought": chain_of_thought,
                "tool_call": normalized_tool_calls,
                "summary": _coerce_text(raw.get("conclusion", "")).strip(),
            }
        )

        if not description and title:
            description = title
        if not description:
            description = (
                f"Step {step_index + 1}" if step_index >= 0 else f"Step {step_index}"
            )

        predictable.append(
            {
                "step": step_index + 1 if step_index >= 0 else step_index,
                "step_index": step_index,
                "title": title,
                "description": description,
                "status": _coerce_text(raw.get("status", "pending")) or "pending",
                "content": content,
            }
        )

    predictable.sort(key=lambda item: item.get("step_index", -1))
    return predictable


async def load_predictable_steps(
    research_id: str,
    plan: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    def _load_sync() -> list[dict[str, Any]]:
        rows = _fetch_all_rows_sync(research_id)
        if not rows and not plan:
            return []

        plan_by_step = _plan_step_map(plan)
        row_by_step: dict[int, dict[str, Any]] = {}
        for row in rows:
            idx = _coerce_step_index(row.get("step_index"))
            if idx is None:
                continue
            row_by_step[idx] = row

        merged_steps: list[dict[str, Any]] = []

        # Keep plan order first for predictable UI manipulation.
        for step_index, plan_info in sorted(
            plan_by_step.items(), key=lambda item: item[0]
        ):
            row = row_by_step.pop(step_index, None)
            if row is None:
                row = {
                    "step_index": step_index,
                    "step_title": plan_info.get("step_title", ""),
                    "step_description": plan_info.get("step_description", ""),
                    "status": "pending",
                    "content_json": _safe_json_dump(_default_content()),
                }
            merged_steps.append(_snapshot_row_to_step(row, plan_info))

        # Include any out-of-plan rows (e.g., synthesis 99 or preprocess -1).
        for step_index, row in sorted(row_by_step.items(), key=lambda item: item[0]):
            merged_steps.append(_snapshot_row_to_step(row, None))

        return merged_steps

    return await asyncio.to_thread(_load_sync)
