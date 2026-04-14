"""
attachment_service.py — Save chat attachments and extract content via MCP tools.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from main.src.bucket.bucket_orchestrator import BucketOrchestrator
from main.src.bucket.bucket_store import bucket_store
from main.src.research.layer2.tools import get_mcp_tools, parse_tool_output
from main.src.store.DBManager import main_db_manager
from main.src.utils.core.task_schedular import scheduler
from main.src.utils.DRLogger import quickLog
from main.src.workspace.workspace_links import link_resource_to_connected_bucket


async def _log(msg: str, level: str = "info", urgency: str = "none") -> None:
    await scheduler.schedule(
        quickLog, params={"message": msg, "level": level, "urgency": urgency}
    )


_CHAT_BUCKET_ID = os.getenv("CHAT_BUCKET_ID", "chat-attachments")
_BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000")
_IMAGE_FORMATS = {"png", "jpg", "jpeg", "webp", "gif", "bmp", "svg", "tiff"}
_WORKSPACE_TABLE = "workspaces"

_bucket_view = BucketOrchestrator()


def save_attachment_to_bucket(
    file_name: str,
    file_format: str,
    content: bytes,
) -> str:
    """
    Write bytes to the chat bucket subfolder.
    Returns stored relative path.
    """
    rel_path = bucket_store.save_file(_CHAT_BUCKET_ID, file_format, file_name, content)
    return rel_path


def build_attachment_url(rel_path: str) -> str:
    return bucket_store.build_asset_url(rel_path)


def _to_absolute_asset_url(file_url: str) -> str:
    if file_url.startswith("http://") or file_url.startswith("https://"):
        return file_url
    base = _BACKEND_PUBLIC_URL.rstrip("/")
    path = file_url if file_url.startswith("/") else f"/{file_url}"
    return f"{base}{path}"


def _normalize_file_format(file_format: str) -> str:
    fmt = (file_format or "").strip().lower().lstrip(".")
    if fmt.startswith("image/"):
        return fmt.split("/", 1)[1]
    return fmt


def _normalize_tool_name(tool_name: str) -> str:
    name = (tool_name or "").strip().lower()
    if not name:
        return ""
    if "::" in name:
        name = name.split("::")[-1]
    if "/" in name:
        name = name.split("/")[-1]
    if "." in name:
        name = name.split(".")[-1]
    for prefix in ("research_tools_", "mcp_", "tool_"):
        if name.startswith(prefix):
            name = name[len(prefix) :]
    return name


def _select_tool(file_format: str, tools: list[Any]) -> Any | None:
    normalized_format = _normalize_file_format(file_format)
    preferred = (
        ["understand_images_tool", "understand_images"]
        if normalized_format in _IMAGE_FORMATS
        else ["process_docs"]
    )

    def find_by_names(candidates: list[str]) -> Any | None:
        for candidate in candidates:
            for tool in tools:
                normalized = _normalize_tool_name(getattr(tool, "name", ""))
                if normalized == candidate:
                    return tool
        return None

    selected = find_by_names(preferred)
    if selected is not None:
        return selected

    # Fallback to any supported content-analysis tool if preferred one is missing.
    return find_by_names(
        ["process_docs", "understand_images_tool", "understand_images"]
    )


def _build_tool_payload(tool: Any, absolute_url: str, file_name: str) -> dict[str, Any]:
    args_schema = getattr(tool, "args_schema", None)
    fields = (
        list(getattr(args_schema, "model_fields", {}).keys()) if args_schema else []
    )
    lower_to_field = {field.lower(): field for field in fields}

    if "paths" in lower_to_field:
        return {lower_to_field["paths"]: [absolute_url]}
    if "urls" in lower_to_field:
        return {lower_to_field["urls"]: [absolute_url]}
    if "path" in lower_to_field:
        return {lower_to_field["path"]: absolute_url}
    if "url" in lower_to_field:
        return {lower_to_field["url"]: absolute_url}
    if "file_url" in lower_to_field:
        return {lower_to_field["file_url"]: absolute_url}
    if "file_urls" in lower_to_field:
        return {lower_to_field["file_urls"]: [absolute_url]}

    if fields:
        only = fields[0]
        only_low = only.lower()
        if only_low in {"paths", "urls", "file_urls"}:
            return {only: [absolute_url]}
        return {only: absolute_url}

    return {"paths": [absolute_url], "file_name": file_name}


def _extract_text(parsed: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in parsed:
        content = str(item.get("content", "")).strip()
        if content:
            parts.append(content)
    return "\n\n".join(parts)


async def extract_mcp_content(
    file_url: str,
    file_name: str = "",
    file_format: str = "",
) -> tuple[str, str, str]:
    """
    Analyze stored file URL through MCP tool transport.

    Returns:
        extracted_text, analysis_status, tool_name
    """
    tool_name = ""
    try:
        tools = await get_mcp_tools()
        if not tools:
            return "", "unavailable", tool_name

        tool = _select_tool(file_format, tools)
        if tool is None:
            return "", "unsupported", tool_name

        tool_name = getattr(tool, "name", "")
        absolute_url = _to_absolute_asset_url(file_url)
        payload = _build_tool_payload(tool, absolute_url, file_name)

        output = await tool.ainvoke(payload)
        parsed = parse_tool_output(tool_name, output)
        text = _extract_text(parsed)
        if text:
            return text, "completed", tool_name
        return "", "empty", tool_name
    except Exception as exc:
        asyncio.ensure_future(
            _log(
                f"MCP extraction failed for {file_url} via tool '{tool_name or 'unknown'}': {exc}",
                level="warning",
                urgency="moderate",
            )
        )
        return "", "failed", tool_name


async def process_attachments(
    raw_files: list[tuple[str, str, bytes]],  # (file_name, file_format, content)
    workspace_id: str | None = None,
    connected_bucket_id: str | None = None,
    created_by: str = "chat-user",
) -> tuple[list[dict], str]:
    """
    Upload each file to bucket, request MCP extraction.

    Returns:
        saved_meta: list of {file_name, rel_path, url, size}
        combined_mcp_text: concatenated extracted text
    """
    saved_meta: list[dict] = []
    mcp_texts: list[str] = []

    workspace = (workspace_id or "").strip()
    bucket_id = (connected_bucket_id or "").strip()
    actor = (created_by or "chat-user").strip() or "chat-user"

    if workspace and not bucket_id:
        workspace_result = main_db_manager.fetch_one(
            _WORKSPACE_TABLE,
            where={"id": workspace},
        )
        workspace_row = (
            workspace_result.get("data") if workspace_result.get("success") else None
        )
        if isinstance(workspace_row, dict):
            bucket_id = str(workspace_row.get("connected_bucket_id") or "").strip()

    if workspace and not bucket_id:
        raise ValueError(
            f"No connected bucket is configured for workspace '{workspace}'."
        )

    if workspace and bucket_id:
        uploaded_records = _bucket_view.uploadFilesToWorkspaceBucket(
            workspace_id=workspace,
            bucket_id=bucket_id,
            files=raw_files,
            created_by=actor,
            source="chat_attachment",
        )
        uploaded_files = [
            (
                record.file_name or "file",
                record.file_format or "other",
                record.file_size or 0,
                record.file_path,
                record.id,
            )
            for record in uploaded_records
        ]
    else:
        uploaded_files = []
        for file_name, file_format, content in raw_files:
            rel_path = save_attachment_to_bucket(file_name, file_format, content)
            uploaded_files.append((file_name, file_format, len(content), rel_path, ""))

    for file_name, file_format, size, rel_path, resource_id in uploaded_files:
        url = build_attachment_url(rel_path)

        extracted_text, analysis_status, analysis_tool = await extract_mcp_content(
            url,
            file_name=file_name,
            file_format=file_format,
        )

        if workspace and bucket_id and resource_id:
            try:
                link_resource_to_connected_bucket(
                    connected_bucket_id=bucket_id,
                    resource_id=resource_id,
                    workspace_id=workspace,
                )
            except Exception as exc:
                asyncio.ensure_future(
                    _log(
                        f"Failed linking chat attachment resource '{resource_id}' to workspace '{workspace}': {exc}",
                        level="warning",
                        urgency="moderate",
                    )
                )

        saved_meta.append(
            {
                "file_name": file_name,
                "rel_path": rel_path,
                "url": url,
                "absolute_url": _to_absolute_asset_url(url),
                "size": int(size),
                "file_format": file_format,
                "resource_id": resource_id,
                "bucket_id": bucket_id,
                "workspace_id": workspace,
                "analysis_status": analysis_status,
                "analysis_tool": analysis_tool,
            }
        )
        if extracted_text:
            mcp_texts.append(f"[{file_name}]\n{extracted_text}")

    return saved_meta, "\n\n".join(mcp_texts)
