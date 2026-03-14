import uuid
from datetime import datetime, timezone
from typing import Literal

from main.apis.models.workspaces import WorkspaceCreate, WorkspaceOut, WorkspacePatch
from main.src.store.DBManager import main_db_manager
from main.src.utils.DRLogger import dr_logger
from main.src.utils.version_constants import get_raw_version

# Logger
LOG_SOURCE = "system"


def _nullish_to_none(value: object) -> object:
    if isinstance(value, str) and value.strip().lower() in {"", "null", "none"}:
        return None
    return value


def _log_system_workspace_event(
    message: str,
    level: Literal["success", "error", "warning", "info"] = "info",
    urgency: Literal["none", "moderate", "critical"] = "none",
) -> None:
    """
    ## Description

    metadata. Ensures all secret-related operations are tracked with appropriate
    Internal utility function for logging secret management events with structured
    urgency levels and log sources.

    ## Parameters

    - `level` (`Literal["success", "error", "warning", "info"]`)
      - Description: Log severity level indicating the nature of the event.
      - Constraints: Must be one of: "success", "error", "warning", "info".
      - Example: "error"

    - `message` (`str`)
      - Description: Human-readable description of the secret event.
      - Constraints: Must be non-empty. Should not contain sensitive data (API keys, tokens).
      - Example: ".env file not found at /path/to/.env"

    - `urgency` (`Literal["none", "moderate", "critical"]`, optional)
      - Description: Priority indicator for the logged event.
      - Constraints: Must be one of: "none", "moderate", "critical".
      - Default: "none"
      - Example: "critical"

    ## Returns

    `None`

    ## Side Effects

    - Writes log entry to the DRLogger system.
    - Includes application version in all log entries.
    - Tags all events with "SECRETS_MANAGEMENT" for filtering.

    ## Debug Notes

    - Ensure messages do NOT contain sensitive information (API keys, tokens).
    - Use appropriate urgency levels: "critical" for missing keys, "moderate" for fallbacks.
    - Check logger output in application logs directory.

    ## Customization

    To change log source or tags globally, modify the module-level constants:
    - `LOG_SOURCE`: Change from "system" to custom value
    """
    dr_logger.log(
        log_type=level,
        message=message,
        origin=LOG_SOURCE,
        urgency=urgency,
        module="MAIN",
        app_version=get_raw_version(),
    )


class WorkspaceOrchestrator:
    def __init__(self):
        self.table_name = "workspaces"

    def _format_row_to_workspace_out(self, row: dict) -> WorkspaceOut:
        """Helper to convert a DB row dictionary to a WorkspaceOut Pydantic model"""
        # Keep compatibility with legacy records that may have unexpected ai_config values.
        allowed_ai_config = {"auto", "local", "online"}
        ai_config_value = row.get("ai_config")
        if not isinstance(ai_config_value, str):
            row["ai_config"] = "auto"
        else:
            normalized_ai_config = ai_config_value.strip().lower()
            row["ai_config"] = (
                normalized_ai_config
                if normalized_ai_config in allowed_ai_config
                else "auto"
            )

        # Boolean mapping from SQLite 0/1
        row["workspace_research_agents"] = bool(
            row.get("workspace_research_agents", True)
        )
        row["workspace_chat_agents"] = bool(row.get("workspace_chat_agents", True))

        return WorkspaceOut(**row)

    def createWorkspace(self, workspace_data: WorkspaceCreate) -> WorkspaceOut:
        _log_system_workspace_event(
            f"Attempting to create workspace: {workspace_data.name}"
        )

        # Prepare data for insertion (Pydantic model dump)
        db_data = workspace_data.model_dump(exclude_unset=True)

        # Normalize null-like payload values coming from UI/swagger clients.
        db_data["id"] = _nullish_to_none(db_data.get("id"))
        db_data["connected_bucket_id"] = _nullish_to_none(
            db_data.get("connected_bucket_id")
        )
        db_data["workspace_resources_id"] = _nullish_to_none(
            db_data.get("workspace_resources_id")
        )

        # Generate essential IDs if not set by the model defaults
        if not db_data.get("id"):
            db_data["id"] = str(uuid.uuid4())

        # Add timestamps
        now = datetime.now(timezone.utc).isoformat()
        db_data["created_at"] = now
        db_data["updated_at"] = now

        result = main_db_manager.insert(self.table_name, db_data)

        if not result.get("success"):
            _log_system_workspace_event(
                f"Failed to create workspace: {result.get('message')}",
                level="error",
                urgency="critical",
            )
            raise ValueError(f"Failed to create workspace: {result.get('message')}")

        _log_system_workspace_event(
            f"Successfully created workspace {db_data['id']}", level="success"
        )
        created_workspace_id = db_data.get("id")
        if not isinstance(created_workspace_id, str):
            raise ValueError("Workspace id generation failed")
        return self.getWorkspace(created_workspace_id)

    def getWorkspace(self, workspace_id: str) -> WorkspaceOut:
        _log_system_workspace_event(f"Fetching workspace {workspace_id}")

        result = main_db_manager.fetch_one(self.table_name, {"id": workspace_id})

        if not result.get("success") or not result.get("data"):
            _log_system_workspace_event(
                f"Workspace {workspace_id} not found",
                level="warning",
                urgency="moderate",
            )
            raise KeyError(f"Workspace {workspace_id} not found")

        _log_system_workspace_event(
            f"Successfully fetched workspace {workspace_id}", level="success"
        )
        return self._format_row_to_workspace_out(result["data"])

    def getAllWorkspaces(self) -> list[WorkspaceOut]:
        _log_system_workspace_event("Fetching all workspaces")

        result = main_db_manager.fetch_all(self.table_name)

        if not result.get("success"):
            _log_system_workspace_event(
                f"Failed to fetch workspaces: {result.get('message')}",
                level="error",
                urgency="critical",
            )
            raise ValueError(f"Failed to fetch workspaces: {result.get('message')}")

        workspaces = [
            self._format_row_to_workspace_out(row) for row in result.get("data", [])
        ]
        _log_system_workspace_event(
            f"Successfully fetched {len(workspaces)} workspaces", level="success"
        )

        return workspaces

    def updateWorkspace(
        self, workspace_id: str, workspace_data: WorkspaceCreate
    ) -> WorkspaceOut:
        _log_system_workspace_event(
            f"Attempting to completely update workspace {workspace_id}"
        )

        # Verify exists
        self.getWorkspace(workspace_id)

        update_data = workspace_data.model_dump(exclude_unset=True)
        update_data["id"] = _nullish_to_none(update_data.get("id"))
        update_data["connected_bucket_id"] = _nullish_to_none(
            update_data.get("connected_bucket_id")
        )
        update_data["workspace_resources_id"] = _nullish_to_none(
            update_data.get("workspace_resources_id")
        )

        # Prevent primary-key changes when replacing a workspace record.
        update_data.pop("id", None)

        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        result = main_db_manager.update(
            self.table_name, update_data, {"id": workspace_id}
        )

        if not result.get("success"):
            _log_system_workspace_event(
                f"Failed to update workspace {workspace_id}: {result.get('message')}",
                level="error",
                urgency="critical",
            )
            raise ValueError(f"Failed to update workspace: {result.get('message')}")

        _log_system_workspace_event(
            f"Successfully updated workspace {workspace_id}", level="success"
        )
        return self.getWorkspace(workspace_id)

    def patchWorkspace(
        self, workspace_id: str, workspace_data: WorkspacePatch
    ) -> WorkspaceOut:
        _log_system_workspace_event(f"Attempting to patch workspace {workspace_id}")

        # Verify exists
        self.getWorkspace(workspace_id)

        patch_data = workspace_data.model_dump(exclude_unset=True)
        if not patch_data:
            return self.getWorkspace(workspace_id)

        patch_data["connected_bucket_id"] = _nullish_to_none(
            patch_data.get("connected_bucket_id")
        )
        patch_data["workspace_resources_id"] = _nullish_to_none(
            patch_data.get("workspace_resources_id")
        )

        patch_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        result = main_db_manager.update(
            self.table_name, patch_data, {"id": workspace_id}
        )

        if not result.get("success"):
            _log_system_workspace_event(
                f"Failed to patch workspace {workspace_id}: {result.get('message')}",
                level="error",
                urgency="critical",
            )
            raise ValueError(f"Failed to patch workspace: {result.get('message')}")

        _log_system_workspace_event(
            f"Successfully patched workspace {workspace_id}", level="success"
        )
        return self.getWorkspace(workspace_id)

    def deleteWorkspace(self, workspace_id: str) -> None:
        _log_system_workspace_event(
            f"Attempting to delete workspace {workspace_id}", urgency="moderate"
        )

        # Verify exists
        self.getWorkspace(workspace_id)

        result = main_db_manager.delete(self.table_name, {"id": workspace_id})

        if not result.get("success"):
            _log_system_workspace_event(
                f"Failed to delete workspace {workspace_id}: {result.get('message')}",
                level="error",
                urgency="critical",
            )
            raise ValueError(f"Failed to delete workspace: {result.get('message')}")

        _log_system_workspace_event(
            f"Successfully deleted workspace {workspace_id}", level="success"
        )
