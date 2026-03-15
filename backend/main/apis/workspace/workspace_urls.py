from pathlib import Path
from typing import Literal, NoReturn

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)

from main.apis.models.bucket import BucketItemRecord
from main.apis.models.workspaces import (
    WorkspaceCreate,
    WorkspaceOut,
    WorkspacePatch,
)
from main.src.bucket import bucket_orchestrator as _bucket_orch
from main.src.utils.DRLogger import dr_logger
from main.src.utils.versionManagement import get_raw_version
from main.src.workspace import workspace_orchestrator

# Router only: include this in main server from another file.
router = APIRouter(prefix="/workspace", tags=["workspace"])

workspace_view = workspace_orchestrator.WorkspaceOrchestrator()
bucket_view = _bucket_orch.BucketOrchestrator()

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
def get_all_workspaces(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=200, ge=1, le=500),
    name_contains: str | None = Query(default=None, alias="nameContains"),
    desc_contains: str | None = Query(default=None, alias="descContains"),
    ai_config: Literal["auto", "local", "online"] | None = Query(
        default=None, alias="aiConfig"
    ),
    connected_bucket_id: str | None = Query(default=None, alias="connectedBucketId"),
    sort_by: Literal["updated_at", "created_at", "name"] = Query(
        default="updated_at", alias="sortBy"
    ),
    sort_order: Literal["asc", "desc"] = Query(default="desc", alias="sortOrder"),
) -> list[WorkspaceOut]:
    try:
        _log_system_workspace_event("Fetching all workspaces API invoked", level="info")
        return workspace_view.getAllWorkspaces(
            page=page,
            size=size,
            name_contains=name_contains,
            desc_contains=desc_contains,
            ai_config=ai_config,
            connected_bucket_id=connected_bucket_id,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as exc:
        _raise_workspace_http_error("Fetch all workspaces", exc)


@router.post(
    "/{workspace_id}/resources/upload",
    response_model=BucketItemRecord,
    status_code=status.HTTP_201_CREATED,
)
async def upload_workspace_resource(
    workspace_id: str,
    file: UploadFile = File(...),
    created_by: str = Query(..., alias="createdBy"),
    source: str | None = Query(default=None),
    summary: str | None = Query(default=None),
) -> BucketItemRecord:
    """
    Upload a single resource file to the workspace's connected bucket.
    The file type is validated against the bucket's allowed_file_types before saving.
    """
    try:
        _log_system_workspace_event(
            f"Uploading resource to workspace {workspace_id} bucket", level="info"
        )
        workspace = workspace_view.getWorkspace(workspace_id)
        if not workspace.connected_bucket_id:
            raise ValueError(
                "Workspace has no connected bucket. "
                "Assign a bucket before uploading resources."
            )
        content = await file.read()
        file_name = file.filename or "resource.bin"
        file_format = Path(file_name).suffix.lstrip(".").lower() or "bin"
        return bucket_view.uploadFileToWorkspaceBucket(
            workspace_id=workspace_id,
            bucket_id=workspace.connected_bucket_id,
            file_name=file_name,
            file_format=file_format,
            content=content,
            created_by=created_by,
            source=source,
            summary=summary,
        )
    except Exception as exc:
        _raise_workspace_http_error(f"Upload resource to workspace {workspace_id}", exc)


@router.post(
    "/{workspace_id}/resources/upload/bulk",
    response_model=list[BucketItemRecord],
    status_code=status.HTTP_201_CREATED,
)
async def upload_workspace_resources_bulk(
    workspace_id: str,
    files: list[UploadFile] = File(...),
    created_by: str = Query(..., alias="createdBy"),
    source: str | None = Query(default=None),
    summary: str | None = Query(default=None),
) -> list[BucketItemRecord]:
    """
    Upload multiple resource files to the workspace's connected bucket.
    ALL file types are validated against the bucket's allowed_file_types BEFORE
    any file is written to disk (all-or-nothing).
    """
    try:
        _log_system_workspace_event(
            f"Bulk uploading resources to workspace {workspace_id} bucket", level="info"
        )
        workspace = workspace_view.getWorkspace(workspace_id)
        if not workspace.connected_bucket_id:
            raise ValueError(
                "Workspace has no connected bucket. "
                "Assign a bucket before uploading resources."
            )
        file_tuples: list[tuple[str, str, bytes]] = []
        for upload in files:
            content = await upload.read()
            file_name = upload.filename or "resource.bin"
            file_format = Path(file_name).suffix.lstrip(".").lower() or "bin"
            file_tuples.append((file_name, file_format, content))
        return bucket_view.uploadFilesToWorkspaceBucket(
            workspace_id=workspace_id,
            bucket_id=workspace.connected_bucket_id,
            files=file_tuples,
            created_by=created_by,
            source=source,
            summary=summary,
        )
    except Exception as exc:
        _raise_workspace_http_error(
            f"Bulk upload resources to workspace {workspace_id}", exc
        )


@router.post(
    "/{workspace_id}/upload/banner",
    response_model=WorkspaceOut,
    status_code=status.HTTP_200_OK,
)
async def upload_workspace_banner(
    workspace_id: str,
    file: UploadFile = File(...),
) -> WorkspaceOut:
    try:
        _log_system_workspace_event(
            f"Uploading banner for workspace {workspace_id}",
            level="info",
        )
        content = await file.read()
        file_name = file.filename or "banner.bin"
        return workspace_view.uploadWorkspaceBanner(
            workspace_id=workspace_id,
            file_name=file_name,
            content=content,
        )
    except Exception as exc:
        _raise_workspace_http_error(f"Upload banner for workspace {workspace_id}", exc)


@router.post(
    "/{workspace_id}/upload/icon",
    response_model=WorkspaceOut,
    status_code=status.HTTP_200_OK,
)
async def upload_workspace_icon(
    workspace_id: str,
    file: UploadFile = File(...),
) -> WorkspaceOut:
    try:
        _log_system_workspace_event(
            f"Uploading icon for workspace {workspace_id}",
            level="info",
        )
        content = await file.read()
        file_name = file.filename or "icon.bin"
        return workspace_view.uploadWorkspaceIcon(
            workspace_id=workspace_id,
            file_name=file_name,
            content=content,
        )
    except Exception as exc:
        _raise_workspace_http_error(f"Upload icon for workspace {workspace_id}", exc)


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


@router.post(
    "/create-with-assets",
    response_model=WorkspaceOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace_with_assets(
    name: str = Form(...),
    desc: str = Form(...),
    icon: str | None = Form(default=None),
    accent_clr: str | None = Form(default=None),
    banner_img: str | None = Form(default=None),
    connected_bucket_id: str | None = Form(default=None),
    ai_config: Literal["auto", "local", "online"] = Form(default="auto"),
    workspace_resources_id: str | None = Form(default=None),
    workspace_research_agents: bool = Form(default=True),
    workspace_chat_agents: bool = Form(default=True),
    banner_file: UploadFile | None = File(default=None),
    icon_file: UploadFile | None = File(default=None),
    resource_files: list[UploadFile] | None = File(default=None),
    resource_created_by: str = Form(default="system"),
    resource_source: str | None = Form(default=None),
    resource_summary: str | None = Form(default=None),
) -> WorkspaceOut:
    """
    Create a workspace and optionally upload banner, icon, and resource files
    in the same multipart request.

    Resource files are stored in the workspace's connected_bucket_id bucket.
    Each file type is validated against the bucket's allowed_file_types before
    any file is written to disk.  If connected_bucket_id is not provided the
    resource_files field is silently ignored.
    """
    try:
        payload = WorkspaceCreate(
            name=name,
            desc=desc,
            icon=icon,
            accent_clr=accent_clr,
            banner_img=banner_img,
            connected_bucket_id=connected_bucket_id,
            ai_config=ai_config,
            workspace_resources_id=workspace_resources_id,
            workspace_research_agents=workspace_research_agents,
            workspace_chat_agents=workspace_chat_agents,
        )
        workspace = workspace_view.createWorkspace(payload)

        if banner_file is not None:
            banner_content = await banner_file.read()
            if banner_content:
                workspace = workspace_view.uploadWorkspaceBanner(
                    workspace_id=workspace.id,
                    file_name=banner_file.filename or "banner.bin",
                    content=banner_content,
                )

        if icon_file is not None:
            icon_content = await icon_file.read()
            if icon_content:
                workspace = workspace_view.uploadWorkspaceIcon(
                    workspace_id=workspace.id,
                    file_name=icon_file.filename or "icon.bin",
                    content=icon_content,
                )

        if resource_files and workspace.connected_bucket_id:
            file_tuples: list[tuple[str, str, bytes]] = []
            for upload in resource_files:
                content = await upload.read()
                file_name = upload.filename or "resource.bin"
                file_format = Path(file_name).suffix.lstrip(".").lower() or "bin"
                file_tuples.append((file_name, file_format, content))
            if file_tuples:
                bucket_view.uploadFilesToWorkspaceBucket(
                    workspace_id=workspace.id,
                    bucket_id=workspace.connected_bucket_id,
                    files=file_tuples,
                    created_by=resource_created_by,
                    source=resource_source,
                    summary=resource_summary,
                )

        return workspace
    except Exception as exc:
        _raise_workspace_http_error("Create workspace with assets", exc)


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
