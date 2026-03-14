from typing import Literal, NoReturn

from fastapi import APIRouter, HTTPException, Response, status

from main.apis.models.workspaces import (
    WorkspaceCreate,
    WorkspaceOut,
    WorkspacePatch,
)
from main.src.utils.DRLogger import dr_logger
from main.src.utils.versionManagement import get_raw_version
from main.src.workspace import workspace_orchestrator

# Router only: include this in main server from another file.
router = APIRouter(prefix="/workspace", tags=["workspace"])

workspace_view = workspace_orchestrator.WorkspaceOrchestrator()

# Logger
LOG_SOURCE = "system"


def _log_system_workspace_event(
    message: str,
    level: Literal["success", "error", "warning", "info"] = "info",
    urgency: Literal["none", "moderate", "critical"] = "none",
) -> None:
    dr_logger.log(
        log_type=level,
        message=message,
        origin=LOG_SOURCE,
        urgency=urgency,
        module="API",
        app_version=get_raw_version(),
    )


def _raise_workspace_http_error(action: str, exc: Exception) -> NoReturn:
    if isinstance(exc, HTTPException):
        raise exc

    if isinstance(exc, NotImplementedError):
        _log_system_workspace_event(
            f"{action} is not implemented in WorkspaceOrchestrator",
            level="warning",
            urgency="moderate",
        )
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"{action} is not implemented yet",
        ) from exc

    if isinstance(exc, KeyError):
        message = str(exc).strip("'") or "Workspace not found"
        _log_system_workspace_event(message, level="warning", urgency="moderate")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        ) from exc

    if isinstance(exc, ValueError):
        message = str(exc) or "Invalid workspace request"
        _log_system_workspace_event(message, level="warning", urgency="moderate")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        ) from exc

    _log_system_workspace_event(
        f"{action} failed: {exc}",
        level="error",
        urgency="critical",
    )
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to {action.lower()}",
    ) from exc


@router.get("/", response_model=list[WorkspaceOut], status_code=status.HTTP_200_OK)
def get_all_workspaces() -> list[WorkspaceOut]:
    try:
        _log_system_workspace_event("Fetching all workspaces API invoked", level="info")
        return workspace_view.getAllWorkspaces()
    except Exception as exc:
        _raise_workspace_http_error("Fetch all workspaces", exc)


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceOut,
    status_code=status.HTTP_200_OK,
)
def get_workspace_by_id(workspace_id: str) -> WorkspaceOut:
    try:
        _log_system_workspace_event(
            f"Fetching workspace {workspace_id} API invoked", level="info"
        )
        return workspace_view.getWorkspace(workspace_id)
    except Exception as exc:
        _raise_workspace_http_error(f"Fetch workspace {workspace_id}", exc)


@router.post("/", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
@router.post(
    "/create",
    response_model=WorkspaceOut,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_workspace(payload: WorkspaceCreate) -> WorkspaceOut:
    try:
        _log_system_workspace_event(
            f"Creating workspace {payload.name} API invoked", level="info"
        )
        return workspace_view.createWorkspace(payload)
    except Exception as exc:
        _raise_workspace_http_error("Create workspace", exc)


@router.put(
    "/{workspace_id}",
    response_model=WorkspaceOut,
    status_code=status.HTTP_200_OK,
)
def replace_workspace(
    workspace_id: str,
    payload: WorkspaceCreate,
) -> WorkspaceOut:
    try:
        _log_system_workspace_event(
            f"Replacing workspace {workspace_id} API invoked", level="info"
        )
        return workspace_view.updateWorkspace(workspace_id, payload)
    except Exception as exc:
        _raise_workspace_http_error(f"Replace workspace {workspace_id}", exc)


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceOut,
    status_code=status.HTTP_200_OK,
)
def patch_workspace(
    workspace_id: str,
    payload: WorkspacePatch,
) -> WorkspaceOut:
    try:
        _log_system_workspace_event(
            f"Patching workspace {workspace_id} API invoked", level="info"
        )
        return workspace_view.patchWorkspace(workspace_id, payload)
    except Exception as exc:
        _raise_workspace_http_error(f"Patch workspace {workspace_id}", exc)


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_workspace(workspace_id: str) -> Response:
    try:
        _log_system_workspace_event(
            f"Deleting workspace {workspace_id} API invoked", level="info"
        )
        workspace_view.deleteWorkspace(workspace_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        _raise_workspace_http_error(f"Delete workspace {workspace_id}", exc)
