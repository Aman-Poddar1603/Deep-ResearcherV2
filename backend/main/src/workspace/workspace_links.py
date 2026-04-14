from __future__ import annotations

import json
from datetime import datetime, timezone

from main.apis.models.workspaces import (
    WorkspaceConnectedChats,
    WorkspaceConnectedResearch,
    WorkspaceConnectedResources,
)
from main.src.store.DBManager import main_db_manager


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_storage_payload(record: object) -> dict:
    payload = record.model_dump(mode="python")
    for key, value in list(payload.items()):
        if isinstance(value, datetime):
            payload[key] = value.isoformat()
    return payload


def _parse_id_list(value: object) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return []

    raw = value.strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None

    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    if isinstance(parsed, str):
        return [item.strip() for item in parsed.split(",") if item.strip()]

    return [item.strip() for item in raw.split(",") if item.strip()]


def _merge_ids(existing: object, new_id: str) -> str:
    ids = _parse_id_list(existing)
    if new_id not in ids:
        ids.append(new_id)
    return json.dumps(ids, separators=(",", ":"))


def _resolve_workspace_connection_key(
    connected_bucket_id: str, workspace_id: str | None = None
) -> str:
    bucket_id = (connected_bucket_id or "").strip()
    workspace = (workspace_id or "").strip()
    if not bucket_id:
        return ""

    # Prefer explicit workspace id when provided; this matches current FK shape
    # where workspace_connected_resources.connected_bucket_id references workspaces.id.
    if workspace:
        return workspace

    direct_workspace = main_db_manager.fetch_one(
        "workspaces", where={"id": bucket_id}
    )
    if direct_workspace.get("success") and direct_workspace.get("data"):
        return bucket_id

    mapped_workspace = main_db_manager.fetch_one(
        "workspaces", where={"connected_bucket_id": bucket_id}
    )
    if mapped_workspace.get("success") and mapped_workspace.get("data"):
        return str(mapped_workspace["data"].get("id") or "").strip()

    return bucket_id


def link_chat_to_workspace(workspace_id: str, chat_session_id: str) -> None:
    workspace = (workspace_id or "").strip()
    chat_session = (chat_session_id or "").strip()
    if not workspace or not chat_session:
        return

    existing = main_db_manager.fetch_one(
        "workspace_connected_chats",
        where={"workspace_id": workspace, "chat_session_id": chat_session},
    )
    if existing.get("success") and existing.get("data"):
        return

    record = WorkspaceConnectedChats(
        workspace_id=workspace,
        chat_session_id=chat_session,
    )
    payload = _to_storage_payload(record)
    result = main_db_manager.insert("workspace_connected_chats", payload)
    if not result.get("success"):
        raise ValueError(
            result.get("message") or "Failed to persist workspace_connected_chats link"
        )


def link_research_to_workspace(workspace_id: str, research_id: str) -> None:
    workspace = (workspace_id or "").strip()
    research = (research_id or "").strip()
    if not workspace or not research:
        return

    existing = main_db_manager.fetch_all(
        "workspace_connected_research",
        where={"workspace_id": workspace},
    )
    if not existing.get("success"):
        raise ValueError(
            existing.get("message")
            or "Failed to read workspace_connected_research rows"
        )

    rows = existing.get("data") or []
    if rows:
        row = rows[0]
        merged_ids = _merge_ids(row.get("research_ids"), research)
        if merged_ids == (row.get("research_ids") or ""):
            return

        update_result = main_db_manager.update(
            "workspace_connected_research",
            data={"research_ids": merged_ids, "updated_at": _utcnow_iso()},
            where={"id": row.get("id")},
        )
        if not update_result.get("success"):
            raise ValueError(
                update_result.get("message")
                or "Failed to update workspace_connected_research"
            )
        return

    record = WorkspaceConnectedResearch(
        workspace_id=workspace,
        research_ids=json.dumps([research], separators=(",", ":")),
    )
    payload = _to_storage_payload(record)
    result = main_db_manager.insert("workspace_connected_research", payload)
    if not result.get("success"):
        raise ValueError(
            result.get("message")
            or "Failed to persist workspace_connected_research link"
        )


def link_resource_to_connected_bucket(
    connected_bucket_id: str, resource_id: str, workspace_id: str | None = None
) -> None:
    bucket_id = (connected_bucket_id or "").strip()
    resource = (resource_id or "").strip()
    if not bucket_id or not resource:
        return

    connection_key = _resolve_workspace_connection_key(bucket_id, workspace_id)
    if not connection_key:
        return

    existing = main_db_manager.fetch_all(
        "workspace_connected_resources",
        where={"connected_bucket_id": connection_key},
    )
    if not existing.get("success"):
        raise ValueError(
            existing.get("message")
            or "Failed to read workspace_connected_resources rows"
        )

    rows = existing.get("data") or []
    if rows:
        row = rows[0]
        merged_ids = _merge_ids(row.get("resource_ids"), resource)
        if merged_ids == (row.get("resource_ids") or ""):
            return

        update_result = main_db_manager.update(
            "workspace_connected_resources",
            data={"resource_ids": merged_ids, "updated_at": _utcnow_iso()},
            where={"id": row.get("id")},
        )
        if not update_result.get("success"):
            raise ValueError(
                update_result.get("message")
                or "Failed to update workspace_connected_resources"
            )
        return

    record = WorkspaceConnectedResources(
        connected_bucket_id=connection_key,
        resource_ids=json.dumps([resource], separators=(",", ":")),
    )
    payload = _to_storage_payload(record)
    result = main_db_manager.insert("workspace_connected_resources", payload)
    if not result.get("success"):
        raise ValueError(
            result.get("message")
            or "Failed to persist workspace_connected_resources link"
        )
