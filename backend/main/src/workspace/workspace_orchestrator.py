from main.apis.models.workspaces import WorkspaceCreate, WorkspaceOut, WorkspacePatch


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
