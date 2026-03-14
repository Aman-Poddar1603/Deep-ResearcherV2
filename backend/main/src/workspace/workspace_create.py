from main.src.store.DBManager import main_db_manager
from main.src.utils.DRLogger import dr_logger


class WorkspaceCreate:
    def __init__(self):
        self.db_manager = main_db_manager
        self.logger = dr_logger

    def create_workspace(self, workspace_data):
        pass
