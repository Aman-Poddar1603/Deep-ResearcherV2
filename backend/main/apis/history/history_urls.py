from typing import Literal, NoReturn

from fastapi import APIRouter, HTTPException, Response, status
from main.src.history import history_orchestrator

from main.apis.models.history import (
    HistoryActions,
    HistoryItem,
    HistoryItemResponse,
    HistoryType,
)
from main.src.utils.DRLogger import dr_logger
from main.src.utils.versionManagement import get_raw_version

# Router only: include this in main server from another file.
router = APIRouter(prefix="/history", tags=["history"])

history_view = history_orchestrator.HistoryOrchestrator()

# Logger
LOG_SOURCE = "system"


def _log_system_history_event(
    message: str,
    level: Literal["success", "error", "warning", "info"] = "info",
    urgency: Literal["none", "moderate", "critical"] = "none",
) -> None:
    """
    Internal utility for logging history-related events with structured metadata.
    """
    dr_logger.log(
        log_type=level,
        message=message,
        origin=LOG_SOURCE,
        urgency=urgency,
        module="API",
        app_version=get_raw_version(),
    )


def _raise_history_http_error(action: str, exc: Exception) -> NoReturn:
    if isinstance(exc, HTTPException):
        raise exc

    if isinstance(exc, NotImplementedError):
        _log_system_history_event(
            f"{action} is not implemented in HistoryOrchestrator",
            level="warning",
            urgency="moderate",
        )
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"{action} is not implemented yet",
        ) from exc

    if isinstance(exc, KeyError):
        message = str(exc).strip("'") or "History item not found"
        _log_system_history_event(message, level="warning", urgency="moderate")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        ) from exc

    if isinstance(exc, ValueError):
        message = str(exc) or "Invalid history request"
        _log_system_history_event(message, level="warning", urgency="moderate")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        ) from exc

    _log_system_history_event(
        f"{action} failed: {exc}",
        level="error",
        urgency="critical",
    )
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to {action.lower()}",
    ) from exc


@router.get("/", response_model=HistoryItemResponse, status_code=status.HTTP_200_OK)
def list_history(
    page: int = 1,
    size: int = 10,
    item_type: HistoryType | None = None,
    include_deleted: bool = False,
) -> HistoryItemResponse:
    """
    List history items with simple pagination and optional filtering by type.
    Delegates to HistoryOrchestrator; expected to return a HistoryItemResponse.
    """
    try:
        _log_system_history_event("Fetching history list", level="info")
        result = history_view.get_history(
            page=page, size=size, item_type=item_type, include_deleted=include_deleted
        )
        _log_system_history_event("Fetched history list", level="success")
        return result
    except Exception as exc:
        _raise_history_http_error("Fetch history list", exc)


@router.get(
    "/{history_id}",
    response_model=HistoryItem,
    status_code=status.HTTP_200_OK,
)
def get_history_item(history_id: str) -> HistoryItem:
    """
    Get a single history item by id.
    """
    try:
        _log_system_history_event(f"Fetching history item {history_id}", level="info")
        item = history_view.get_history_item(history_id)
        _log_system_history_event(f"Fetched history item {history_id}", level="success")
        return item
    except Exception as exc:
        _raise_history_http_error(f"Fetch history item {history_id}", exc)


@router.post("/", response_model=HistoryItem, status_code=status.HTTP_201_CREATED)
def create_history_item(payload: HistoryItem) -> HistoryItem:
    """
    Create a new history item. In many apps history items are created internally,
    but the endpoint is provided here for completeness or testing.
    """
    try:
        _log_system_history_event(
            f"Creating history item {payload.title}", level="info"
        )
        created = history_view.create_history_item(payload)
        _log_system_history_event(f"Created history item {created.id}", level="success")
        return created
    except Exception as exc:
        _raise_history_http_error("Create history item", exc)


@router.delete(
    "/{history_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_history_item(history_id: str) -> Response:
    """
    Delete (or mark deleted) a history item.
    """
    try:
        _log_system_history_event(f"Deleting history item {history_id}", level="info")
        history_view.delete_history_item(history_id)
        _log_system_history_event(f"Deleted history item {history_id}", level="success")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        _raise_history_http_error(f"Delete history item {history_id}", exc)


@router.post(
    "/{history_id}/action",
    response_model=HistoryItem,
    status_code=status.HTTP_200_OK,
)
def perform_history_action(history_id: str, action: HistoryActions) -> HistoryItem:
    """
    Perform an action on a history item (e.g. delete). Actions are defined in HistoryActions enum.
    """
    try:
        _log_system_history_event(
            f"Performing action {action} on history item {history_id}", level="info"
        )
        item = history_view.perform_action(history_id, action)
        _log_system_history_event(
            f"Performed action {action} on history item {history_id}", level="success"
        )
        return item
    except Exception as exc:
        _raise_history_http_error(
            f"Perform action {action} on history item {history_id}", exc
        )
