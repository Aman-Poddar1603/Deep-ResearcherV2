import math
from datetime import datetime
from typing import Any, Literal

from main.apis.models.research import (
    ResearchCreate,
    ResearchListResponse,
    ResearchPatch,
    ResearchRecord,
    ResearchSourceCreate,
    ResearchSourceListResponse,
    ResearchSourcePatch,
    ResearchSourceRecord,
)
from main.src.store.DBManager import researches_db_manager


class ResearchOrchestrator:
    def __init__(self):
        self.research_table = "researches"
        self.source_table = "research_sources"

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

    def _db_payload(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = dict(data)
        for key, value in list(payload.items()):
            if isinstance(value, datetime):
                payload[key] = value.isoformat()
        return payload

    def _paginate(
        self, items: list[Any], page: int, size: int
    ) -> tuple[list[Any], int, int, int]:
        total_items = len(items)
        total_pages = math.ceil(total_items / size) if total_items > 0 else 0
        offset = (page - 1) * size
        return items[offset : offset + size], total_items, total_pages, offset

    def _fetch_one(
        self, table_name: str, where: dict[str, Any], not_found: str
    ) -> dict[str, Any]:
        result = researches_db_manager.fetch_one(table_name, where=where)
        if not result.get("success"):
            raise ValueError(result.get("message") or f"Failed to fetch {table_name}")
        row = result.get("data")
        if row is None:
            raise KeyError(not_found)
        return row

    def getAllResearch(
        self,
        page: int = 1,
        size: int = 20,
        workspace_id: str | None = None,
        title_contains: str | None = None,
        sort_by: Literal["id", "title"] = "id",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> ResearchListResponse:
        where = {"workspace_id": workspace_id} if workspace_id else None
        result = researches_db_manager.fetch_all(self.research_table, where=where)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to list research items")

        rows = [
            ResearchRecord.model_validate(item) for item in (result.get("data") or [])
        ]
        if title_contains:
            term = title_contains.strip().lower()
            rows = [row for row in rows if term in (row.title or "").lower()]

        reverse_order = sort_order == "desc"
        if sort_by == "title":
            rows.sort(key=lambda row: (row.title or "").lower(), reverse=reverse_order)
        else:
            rows.sort(key=lambda row: row.id, reverse=reverse_order)

        page_items, total_items, total_pages, offset = self._paginate(rows, page, size)
        return ResearchListResponse(
            items=page_items,
            page=page,
            size=size,
            total_items=total_items,
            total_pages=total_pages,
            offset=offset,
        )

    def getResearch(self, research_id: str) -> ResearchRecord:
        row = self._fetch_one(
            self.research_table,
            {"id": research_id},
            f"Research item {research_id} not found",
        )
        return ResearchRecord.model_validate(row)

    def createResearch(self, payload: ResearchCreate) -> ResearchRecord:
        data = self._db_payload(payload.model_dump(mode="python"))
        result = researches_db_manager.insert(self.research_table, data)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to create research")
        return self.getResearch(data["id"])

    def updateResearch(
        self, research_id: str, payload: ResearchCreate
    ) -> ResearchRecord:
        self.getResearch(research_id)
        data = self._db_payload(payload.model_dump(mode="python"))
        data["id"] = research_id
        result = researches_db_manager.update(
            self.research_table,
            data=data,
            where={"id": research_id},
        )
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to update research")
        return self.getResearch(research_id)

    def patchResearch(self, research_id: str, payload: ResearchPatch) -> ResearchRecord:
        self.getResearch(research_id)
        patch_data = self._db_payload(
            payload.model_dump(exclude_unset=True, mode="python")
        )
        if not patch_data:
            return self.getResearch(research_id)
        result = researches_db_manager.update(
            self.research_table,
            data=patch_data,
            where={"id": research_id},
        )
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to patch research")
        return self.getResearch(research_id)

    def deleteResearch(self, research_id: str) -> None:
        self.getResearch(research_id)
        result = researches_db_manager.delete(
            self.research_table, where={"id": research_id}
        )
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to delete research")

    def getResearchSourceUrls(
        self,
        research_id: str | None = None,
        page: int = 1,
        size: int = 20,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        source_type: str | None = None,
        url_contains: str | None = None,
        sort_by: Literal[
            "created_at", "updated_at", "research_id", "source_type", "source_url"
        ] = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> ResearchSourceListResponse:
        where = {"research_id": research_id} if research_id else None
        result = researches_db_manager.fetch_all(self.source_table, where=where)
        if not result.get("success"):
            raise ValueError(
                result.get("message") or "Failed to list research source urls"
            )

        rows = [
            ResearchSourceRecord.model_validate(item)
            for item in (result.get("data") or [])
        ]

        if created_from is not None:
            rows = [
                row
                for row in rows
                if self._parse_datetime(row.created_at) >= created_from
            ]
        if created_to is not None:
            rows = [
                row
                for row in rows
                if self._parse_datetime(row.created_at) <= created_to
            ]
        if updated_from is not None:
            rows = [
                row
                for row in rows
                if self._parse_datetime(row.updated_at) >= updated_from
            ]
        if updated_to is not None:
            rows = [
                row
                for row in rows
                if self._parse_datetime(row.updated_at) <= updated_to
            ]
        if source_type:
            source_type_term = source_type.strip().lower()
            rows = [
                row
                for row in rows
                if source_type_term == (row.source_type or "").strip().lower()
            ]
        if url_contains:
            url_term = url_contains.strip().lower()
            rows = [row for row in rows if url_term in (row.source_url or "").lower()]

        reverse_order = sort_order == "desc"
        if sort_by == "updated_at":
            rows.sort(
                key=lambda row: self._parse_datetime(row.updated_at),
                reverse=reverse_order,
            )
        elif sort_by == "research_id":
            rows.sort(key=lambda row: row.research_id or "", reverse=reverse_order)
        elif sort_by == "source_type":
            rows.sort(
                key=lambda row: (row.source_type or "").lower(), reverse=reverse_order
            )
        elif sort_by == "source_url":
            rows.sort(
                key=lambda row: (row.source_url or "").lower(), reverse=reverse_order
            )
        else:
            rows.sort(
                key=lambda row: self._parse_datetime(row.created_at),
                reverse=reverse_order,
            )

        page_items, total_items, total_pages, offset = self._paginate(rows, page, size)
        return ResearchSourceListResponse(
            items=page_items,
            page=page,
            size=size,
            total_items=total_items,
            total_pages=total_pages,
            offset=offset,
        )

    def getResearchSource(self, source_id: str) -> ResearchSourceRecord:
        row = self._fetch_one(
            self.source_table,
            {"id": source_id},
            f"Research source {source_id} not found",
        )
        return ResearchSourceRecord.model_validate(row)

    def createResearchSource(
        self, payload: ResearchSourceCreate
    ) -> ResearchSourceRecord:
        data = self._db_payload(payload.model_dump(mode="python"))
        result = researches_db_manager.insert(self.source_table, data)
        if not result.get("success"):
            raise ValueError(
                result.get("message") or "Failed to create research source"
            )
        return self.getResearchSource(data["id"])

    def patchResearchSource(
        self, source_id: str, payload: ResearchSourcePatch
    ) -> ResearchSourceRecord:
        self.getResearchSource(source_id)
        patch_data = self._db_payload(
            payload.model_dump(exclude_unset=True, mode="python")
        )
        if not patch_data:
            return self.getResearchSource(source_id)
        patch_data["updated_at"] = datetime.now().isoformat()
        result = researches_db_manager.update(
            self.source_table,
            data=patch_data,
            where={"id": source_id},
        )
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to patch research source")
        return self.getResearchSource(source_id)

    def deleteResearchSource(self, source_id: str) -> None:
        self.getResearchSource(source_id)
        result = researches_db_manager.delete(
            self.source_table, where={"id": source_id}
        )
        if not result.get("success"):
            raise ValueError(
                result.get("message") or "Failed to delete research source"
            )
