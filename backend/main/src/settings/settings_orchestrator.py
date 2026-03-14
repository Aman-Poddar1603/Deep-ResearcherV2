from enum import Enum
from typing import Any

from main.apis.models.settings import SettingsPatch, SettingsRecord
from main.src.store.DBManager import main_db_manager


class SettingsOrchestrator:
    def _serialize_value(self, value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        return value

    def _normalize_payload(self, data: dict[str, Any]) -> dict[str, Any]:
        return {key: self._serialize_value(value) for key, value in data.items()}

    def _get_first_row(self) -> dict[str, Any] | None:
        result = main_db_manager.fetch_all("settings")
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to fetch settings")
        rows = result.get("data") or []
        return rows[0] if rows else None

    def _insert_row(self, payload: dict[str, Any]) -> None:
        result = main_db_manager.insert("settings", payload)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to insert settings")

    def _replace_singleton_row(self, payload: dict[str, Any]) -> None:
        delete_result = main_db_manager.delete_all("settings")
        if not delete_result.get("success"):
            raise ValueError(delete_result.get("message") or "Failed to clear settings")
        self._insert_row(payload)

    def getSettings(self) -> SettingsRecord:
        row = self._get_first_row()
        if row is None:
            return SettingsRecord()
        return SettingsRecord.model_validate(row)

    def createSettings(self, payload: SettingsRecord) -> SettingsRecord:
        row = self._get_first_row()
        if row is not None:
            raise ValueError("Settings row already exists. Use PUT or PATCH to modify.")
        self._insert_row(self._normalize_payload(payload.model_dump(mode="python")))
        return self.getSettings()

    def updateSettings(self, payload: SettingsRecord) -> SettingsRecord:
        data = self._normalize_payload(payload.model_dump(mode="python"))
        self._replace_singleton_row(data)
        return self.getSettings()

    def patchSettings(self, payload: SettingsPatch) -> SettingsRecord:
        current = self._get_first_row()
        patch_data = payload.model_dump(exclude_unset=True, mode="python")
        if not patch_data:
            if current is None:
                return SettingsRecord()
            return SettingsRecord.model_validate(current)
        patch_data = self._normalize_payload(patch_data)
        if current is None:
            base = SettingsRecord().model_dump(mode="python")
            base.update(patch_data)
            self._insert_row(self._normalize_payload(base))
        else:
            base = dict(current)
            base.update(patch_data)
            self._replace_singleton_row(self._normalize_payload(base))
        return self.getSettings()

    def deleteSettings(self) -> None:
        result = main_db_manager.delete_all("settings")
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to delete settings")
