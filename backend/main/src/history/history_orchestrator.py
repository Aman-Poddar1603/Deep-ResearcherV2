import math
from datetime import datetime
from typing import Any

from main.apis.models.history import (
    HistoryActions,
    HistoryItem,
    HistoryItemPatch,
    HistoryItemResponse,
    HistoryType,
)
from main.src.store.DBManager import history_db_manager


class HistoryOrchestrator:
    def __init__(self):
        self.table_name = "user_usage_history"

    def _db_payload(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = dict(data)
        for key, value in list(payload.items()):
            if isinstance(value, datetime):
                payload[key] = value.isoformat()
        return payload

    def _parse_datetime(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            normalized = value.replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(normalized)
            except ValueError:
                pass
        return datetime.min

    def get_history(
        self,
        page: int = 1,
        size: int = 10,
        item_type: HistoryType | None = None,
        include_deleted: bool = False,
        workspace_id: str | None = None,
        user_id: str | None = None,
    ) -> HistoryItemResponse:
        del include_deleted

        where: dict[str, Any] = {}
        if item_type is not None:
            where["type"] = item_type.value
        if workspace_id is not None:
            where["workspace_id"] = workspace_id
        if user_id is not None:
            where["user_id"] = user_id

        result = history_db_manager.fetch_all(self.table_name, where=where or None)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to list history items")

        items = [
            HistoryItem.model_validate(item) for item in (result.get("data") or [])
        ]
        items.sort(key=lambda item: self._parse_datetime(item.last_seen), reverse=True)

        total_items = len(items)
        total_pages = math.ceil(total_items / size) if total_items > 0 else 0
        offset = (page - 1) * size
        page_items = items[offset : offset + size]

        return HistoryItemResponse(
            history_items=page_items,
            page=page,
            total_pages=total_pages,
            offset=offset,
        )

    def get_history_item(self, history_id: str) -> HistoryItem:
        result = history_db_manager.fetch_one(self.table_name, where={"id": history_id})
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to fetch history item")

        row = result.get("data")
        if row is None:
            raise KeyError(f"History item {history_id} not found")
        return HistoryItem.model_validate(row)

    def create_history_item(self, payload: HistoryItem) -> HistoryItem:
        data = self._db_payload(payload.model_dump(mode="python"))
        result = history_db_manager.insert(self.table_name, data)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to create history item")
        return self.get_history_item(data["id"])

    def update_history_item(self, history_id: str, payload: HistoryItem) -> HistoryItem:
        self.get_history_item(history_id)
        data = self._db_payload(payload.model_dump(mode="python"))
        data["id"] = history_id
        result = history_db_manager.update(
            self.table_name, data=data, where={"id": history_id}
        )
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to update history item")
        return self.get_history_item(history_id)

    def patch_history_item(
        self, history_id: str, payload: HistoryItemPatch
    ) -> HistoryItem:
        self.get_history_item(history_id)
        patch_data = self._db_payload(
            payload.model_dump(exclude_unset=True, mode="python")
        )
        if not patch_data:
            return self.get_history_item(history_id)
        result = history_db_manager.update(
            self.table_name, data=patch_data, where={"id": history_id}
        )
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to patch history item")
        return self.get_history_item(history_id)

    def delete_history_item(self, history_id: str) -> None:
        self.get_history_item(history_id)
        result = history_db_manager.delete(self.table_name, where={"id": history_id})
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to delete history item")

    def perform_action(self, history_id: str, action: HistoryActions) -> HistoryItem:
        item = self.get_history_item(history_id)
        if action is HistoryActions.DELETE:
            self.delete_history_item(history_id)
            return item
        raise ValueError(f"Unsupported history action: {action.value}")
