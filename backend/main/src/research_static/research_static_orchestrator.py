import math
from typing import Any, Literal
from uuid import UUID

from main.apis.models.research_static import (
    ResearchMetadataRecord,
    ResearchPlanListResponse,
    ResearchPlanRecord,
    ResearchSourceStaticListResponse,
    ResearchSourceStaticRecord,
    ResearchStaticListResponse,
    ResearchStaticRecord,
    ResearchTemplateListResponse,
    ResearchTemplateRecord,
)
from main.src.store.DBManager import history_db_manager, researches_db_manager
from main.src.utils.DRLogger import quickLog


class ResearchStaticOrchestrator:
    """
    ## Description

    Core business logic for handling read and delete operations on research
    data. This module is strictly isolated from the runtime research engine
    and is only responsible for querying and cleaning up persisted research DB records.

    ## Rules

    - Uses `quickLog` on all boundary points.
    - Operates primarily on `researches_db_manager`.
    - Cross-DB delete logic implemented for `research_workflow` in `history_db_manager`.
    """

    def _paginate(
        self, items: list[Any], page: int, size: int
    ) -> tuple[list[Any], int, int, int]:
        total_items = len(items)
        total_pages = math.ceil(total_items / size) if total_items > 0 else 0
        offset = (page - 1) * size
        return items[offset : offset + size], total_items, total_pages, offset

    # ═══════════════════════════════════════════════════
    # RESEARCHES
    # ═══════════════════════════════════════════════════

    def get_all_researches(
        self,
        page: int = 1,
        size: int = 20,
        workspace_id: str | None = None,
        sort_by: Literal["title", "created_at"] = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> ResearchStaticListResponse:
        quickLog(
            f"Fetching all research-static records. page={page}, size={size}",
            level="info",
            module="API",
        )
        
        where: dict[str, Any] = {}
        if workspace_id:
            where["workspace_id"] = workspace_id

        result = researches_db_manager.fetch_all("researches", where=where or None)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to list research records")

        rows = result.get("data") or []
        items = [ResearchStaticRecord.model_validate(row) for row in rows]
        
        reverse_order = sort_order == "desc"
        if sort_by == "title":
            items.sort(
                key=lambda item: (item.title or "").lower(), reverse=reverse_order
            )
        else:
            # We don't have created_at mapped yet in the schemas (and DB), so fallback sorting by ID 
            # if we wanted created_at. Usually IDs are sequential or UUIDs.
            items.sort(key=lambda item: item.id, reverse=reverse_order)

        paged_items, total, pages, offset = self._paginate(items, page, size)

        return ResearchStaticListResponse(
            items=paged_items,
            page=page,
            size=size,
            total_items=total,
            total_pages=pages,
            offset=offset,
        )

    def get_research_by_id(self, research_id: str) -> ResearchStaticRecord:
        quickLog(
            f"Fetching research-static record {research_id}",
            level="info",
            module="API",
        )
        result = researches_db_manager.fetch_one(
            "researches", where={"id": research_id}
        )
        
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to fetch research record")
            
        row = result.get("data")
        if not row:
            raise KeyError(f"Research with ID {research_id} not found")
            
        return ResearchStaticRecord.model_validate(row)

    def delete_research(self, research_id: str) -> None:
        quickLog(
            f"Deleting research {research_id} and all related static assets",
            level="warning",
            urgency="moderate",
            module="API",
        )
        # Verify exists first
        self.get_research_by_id(research_id)
        
        # 1. DELETE FROM researches (Cascades to sources and metadata via SQLite FKs)
        # Note: We rely on SQLite PRAGMA foreign_keys = ON in migrations.py
        result = researches_db_manager.delete("researches", where={"id": research_id})
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to delete research")
            
        # 2. CROSS-DB DELETE (research_workflow)
        # Must be handled manually because history.db and researches.db are separate files
        workflow_delete = history_db_manager.delete(
            "research_workflow", where={"research_id": research_id}
        )
        if not workflow_delete.get("success"):
            # Don't fail the whole request, but log heavily
            quickLog(
                f"Cross-DB delete failed for research_workflow {research_id}: {workflow_delete.get('message')}",
                level="error",
                urgency="critical",
                module="API",
            )
            
        quickLog(
            f"Successfully deleted research {research_id}",
            level="success",
            module="API",
        )

    # ═══════════════════════════════════════════════════
    # SOURCES
    # ═══════════════════════════════════════════════════

    def get_research_sources(
        self, research_id: str, page: int = 1, size: int = 20
    ) -> ResearchSourceStaticListResponse:
        quickLog(
            f"Fetching research sources for research {research_id}",
            level="info",
            module="API",
        )
        result = researches_db_manager.fetch_all(
            "research_sources", where={"research_id": research_id}
        )
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to list research sources")
            
        rows = result.get("data") or []
        items = [ResearchSourceStaticRecord.model_validate(row) for row in rows]
        
        # Sort by step index or created_at
        items.sort(key=lambda item: item.step_index or 0)
        
        paged_items, total, pages, offset = self._paginate(items, page, size)

        return ResearchSourceStaticListResponse(
            items=paged_items,
            page=page,
            size=size,
            total_items=total,
            total_pages=pages,
            offset=offset,
        )

    def get_research_source_by_id(self, source_id: str) -> ResearchSourceStaticRecord:
        result = researches_db_manager.fetch_one(
            "research_sources", where={"id": source_id}
        )
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to fetch source")
        row = result.get("data")
        if not row:
            raise KeyError(f"Source {source_id} not found")
        return ResearchSourceStaticRecord.model_validate(row)

    def delete_research_source(self, source_id: str) -> None:
        quickLog(
            f"Deleting research source {source_id}",
            level="warning",
            urgency="moderate",
            module="API",
        )
        self.get_research_source_by_id(source_id)
        
        result = researches_db_manager.delete(
            "research_sources", where={"id": source_id}
        )
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to delete source")

        quickLog(f"Source {source_id} deleted successfully", level="success", module="API")

    # ═══════════════════════════════════════════════════
    # METADATA
    # ═══════════════════════════════════════════════════

    def get_research_metadata(self, research_id: str) -> ResearchMetadataRecord:
        quickLog(
            f"Fetching metadata for research {research_id}",
            level="info",
            module="API",
        )
        result = researches_db_manager.fetch_one(
            "research_metadata", where={"research_id": research_id}
        )
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to fetch metadata")
        row = result.get("data")
        if not row:
            raise KeyError(f"Metadata for research {research_id} not found")
        return ResearchMetadataRecord.model_validate(row)

    # ═══════════════════════════════════════════════════
    # PLANS & TEMPLATES
    # ═══════════════════════════════════════════════════

    def get_research_plans(
        self, page: int = 1, size: int = 20, workspace_id: str | None = None
    ) -> ResearchPlanListResponse:
        quickLog("Fetching research plans", level="info", module="API")
        where: dict[str, Any] = {}
        if workspace_id:
            where["workspace_id"] = workspace_id
            
        result = researches_db_manager.fetch_all("research_plans", where=where or None)
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to list plans")
            
        items = [
            ResearchPlanRecord.model_validate(row) for row in (result.get("data") or [])
        ]
        paged_items, total, pages, offset = self._paginate(items, page, size)

        return ResearchPlanListResponse(
            items=paged_items,
            page=page,
            size=size,
            total_items=total,
            total_pages=pages,
            offset=offset,
        )

    def get_research_plan_by_id(self, plan_id: str) -> ResearchPlanRecord:
        result = researches_db_manager.fetch_one(
            "research_plans", where={"id": plan_id}
        )
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to fetch plan")
        row = result.get("data")
        if not row:
            raise KeyError(f"Plan {plan_id} not found")
        return ResearchPlanRecord.model_validate(row)

    def get_research_templates(
        self, page: int = 1, size: int = 20
    ) -> ResearchTemplateListResponse:
        quickLog("Fetching research templates", level="info", module="API")
        result = researches_db_manager.fetch_all("research_templates")
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to list templates")
            
        items = [
            ResearchTemplateRecord.model_validate(row)
            for row in (result.get("data") or [])
        ]
        paged_items, total, pages, offset = self._paginate(items, page, size)

        return ResearchTemplateListResponse(
            items=paged_items,
            page=page,
            size=size,
            total_items=total,
            total_pages=pages,
            offset=offset,
        )

    def get_research_template_by_id(self, template_id: str) -> ResearchTemplateRecord:
        result = researches_db_manager.fetch_one(
            "research_templates", where={"id": template_id}
        )
        if not result.get("success"):
            raise ValueError(result.get("message") or "Failed to fetch template")
        row = result.get("data")
        if not row:
            raise KeyError(f"Template {template_id} not found")
        return ResearchTemplateRecord.model_validate(row)
