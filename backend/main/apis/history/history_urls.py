from datetime import datetime
from typing import Literal, NoReturn

from fastapi import APIRouter, HTTPException, Query, Response, status

from main.apis.models.history import (
    HistoryActions,
    HistoryItem,
    HistoryItemPatch,
    HistoryItemResponse,
    HistoryType,
)
from main.src.history import history_orchestrator

router = APIRouter(prefix="/history", tags=["history"])

history_view = history_orchestrator.HistoryOrchestrator()


def _raise_history_http_error(action: str, exc: Exception) -> NoReturn:
    if isinstance(exc, HTTPException):
        raise exc
    if isinstance(exc, KeyError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc).strip("'"),
        ) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc) or f"Invalid request for {action.lower()}",
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to {action.lower()}",
    ) from exc


@router.get("/", response_model=HistoryItemResponse, status_code=status.HTTP_200_OK)
def list_history(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=200),
    item_type: HistoryType | None = Query(default=None, alias="itemType"),
    workspace_id: str | None = Query(default=None, alias="workspaceId"),
    user_id: str | None = Query(default=None, alias="userId"),
    include_deleted: bool = False,
    activity_contains: str | None = Query(default=None, alias="activityContains"),
    url_contains: str | None = Query(default=None, alias="urlContains"),
    created_from: datetime | None = Query(default=None, alias="createdFrom"),
    created_to: datetime | None = Query(default=None, alias="createdTo"),
    last_seen_from: datetime | None = Query(default=None, alias="lastSeenFrom"),
    last_seen_to: datetime | None = Query(default=None, alias="lastSeenTo"),
    sort_by: Literal["last_seen", "created_at", "activity", "type"] = Query(
        default="last_seen", alias="sortBy"
    ),
    sort_order: Literal["asc", "desc"] = Query(default="desc", alias="sortOrder"),
) -> HistoryItemResponse:
    try:
        return history_view.get_history(
            page=page,
            size=size,
            item_type=item_type,
            include_deleted=include_deleted,
            workspace_id=workspace_id,
            user_id=user_id,
            activity_contains=activity_contains,
            url_contains=url_contains,
            created_from=created_from,
            created_to=created_to,
            last_seen_from=last_seen_from,
            last_seen_to=last_seen_to,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as exc:
        _raise_history_http_error("List history items", exc)


@router.get("/{history_id}", response_model=HistoryItem, status_code=status.HTTP_200_OK)
def get_history_item(history_id: str) -> HistoryItem:
    try:
        return history_view.get_history_item(history_id)
    except Exception as exc:
        _raise_history_http_error(f"Fetch history item {history_id}", exc)


@router.post("/", response_model=HistoryItem, status_code=status.HTTP_201_CREATED)
def create_history_item(payload: HistoryItem) -> HistoryItem:
    try:
        return history_view.create_history_item(payload)
    except Exception as exc:
        _raise_history_http_error("Create history item", exc)


@router.put("/{history_id}", response_model=HistoryItem, status_code=status.HTTP_200_OK)
def replace_history_item(history_id: str, payload: HistoryItem) -> HistoryItem:
    try:
        return history_view.update_history_item(history_id, payload)
    except Exception as exc:
        _raise_history_http_error(f"Replace history item {history_id}", exc)


@router.patch(
    "/{history_id}", response_model=HistoryItem, status_code=status.HTTP_200_OK
)
def patch_history_item(history_id: str, payload: HistoryItemPatch) -> HistoryItem:
    try:
        return history_view.patch_history_item(history_id, payload)
    except Exception as exc:
        _raise_history_http_error(f"Patch history item {history_id}", exc)


@router.delete("/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history_item(history_id: str) -> Response:
    try:
        history_view.delete_history_item(history_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        _raise_history_http_error(f"Delete history item {history_id}", exc)


@router.post(
    "/{history_id}/action", response_model=HistoryItem, status_code=status.HTTP_200_OK
)
def perform_history_action(history_id: str, action: HistoryActions) -> HistoryItem:
    try:
        return history_view.perform_action(history_id, action)
    except Exception as exc:
        _raise_history_http_error(
            f"Perform action {action.value} on history item {history_id}", exc
        )
