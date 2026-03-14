from typing import Literal

from main.apis.models.workspaces import WorkspaceCreate, WorkspaceOut, WorkspacePatch
from main.src.utils.DRLogger import dr_logger
from main.src.utils.version_constants import get_raw_version

# Logger
LOG_SOURCE = "system"


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
        pass

    def createWorkspace(self, workspace_data: WorkspaceCreate) -> WorkspaceOut:
        # Implement logic to create a workspace, e.g., save to DB
        raise NotImplementedError

    def getWorkspace(self, workspace_id: str) -> WorkspaceOut:
        # Implement logic to retrieve a workspace by ID, e.g., query from DB
        raise NotImplementedError

    def getAllWorkspaces(self) -> list[WorkspaceOut]:
        # Implement logic to retrieve all workspaces, e.g., query from DB
        raise NotImplementedError

    def updateWorkspace(
        self, workspace_id: str, workspace_data: WorkspaceCreate
    ) -> WorkspaceOut:
        # Implement logic to update a workspace, e.g., update in DB
        raise NotImplementedError

    def patchWorkspace(
        self, workspace_id: str, workspace_data: WorkspacePatch
    ) -> WorkspaceOut:
        # Implement logic to patch a workspace, e.g., update in DB
        raise NotImplementedError

    def deleteWorkspace(self, workspace_id: str) -> None:
        # Implement logic to delete a workspace, e.g., remove from DB
        raise NotImplementedError
