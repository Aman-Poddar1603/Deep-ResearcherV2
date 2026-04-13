from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status

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
from main.src.research_static.research_static_orchestrator import (
    ResearchStaticOrchestrator,
)
from main.src.utils.DRLogger import quickLog
from main.src.utils.core.task_schedular import scheduler

router = APIRouter(prefix="/research-static", tags=["research-static"])
static_orch = ResearchStaticOrchestrator()


def _handle_error(e: Exception) -> None:
    if isinstance(e, KeyError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e).strip("'")
        )
    if isinstance(e, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
    )

# Static routes must come before dynamic parameter routes like /{research_id}

@router.get("/", response_model=ResearchStaticListResponse)
async def list_researches(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    workspace_id: str | None = Query(None, alias="workspaceId"),
    sort_by: Literal["title", "created_at"] = Query("created_at", alias="sortBy"),
    sort_order: Literal["asc", "desc"] = Query("desc", alias="sortOrder"),
):
    try:
        return static_orch.get_all_researches(
            page=page,
            size=size,
            workspace_id=workspace_id,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as e:
        _handle_error(e)

@router.get("/plans", response_model=ResearchPlanListResponse)
async def list_plans(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    workspace_id: str | None = Query(None, alias="workspaceId"),
):
    try:
        return static_orch.get_research_plans(
            page=page, size=size, workspace_id=workspace_id
        )
    except Exception as e:
        _handle_error(e)

@router.get("/plans/{plan_id}", response_model=ResearchPlanRecord)
async def get_plan(plan_id: str):
    try:
        return static_orch.get_research_plan_by_id(plan_id)
    except Exception as e:
        _handle_error(e)

@router.get("/templates", response_model=ResearchTemplateListResponse)
async def list_templates(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    try:
        return static_orch.get_research_templates(page=page, size=size)
    except Exception as e:
        _handle_error(e)

@router.get("/templates/{template_id}", response_model=ResearchTemplateRecord)
async def get_template(template_id: str):
    try:
        return static_orch.get_research_template_by_id(template_id)
    except Exception as e:
        _handle_error(e)

@router.get("/sources/{source_id}", response_model=ResearchSourceStaticRecord)
async def get_source(source_id: str):
    try:
        return static_orch.get_research_source_by_id(source_id)
    except Exception as e:
        _handle_error(e)

@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(source_id: str):
    try:
        static_orch.delete_research_source(source_id)
        await scheduler.schedule(
            quickLog,
            params={
                "message": f"Successfully deleted research source {source_id} from API",
                "level": "warning",
                "urgency": "moderate",
                "module": ["API"],
            },
        )
        return
    except Exception as e:
        _handle_error(e)

@router.get("/{research_id}/sources", response_model=ResearchSourceStaticListResponse)
async def list_research_sources(
    research_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    try:
        return static_orch.get_research_sources(research_id, page=page, size=size)
    except Exception as e:
        _handle_error(e)

@router.get("/{research_id}/metadata", response_model=ResearchMetadataRecord)
async def get_research_metadata(research_id: str):
    try:
        return static_orch.get_research_metadata(research_id)
    except Exception as e:
        _handle_error(e)

@router.get("/{research_id}", response_model=ResearchStaticRecord)
async def get_research(research_id: str):
    try:
        return static_orch.get_research_by_id(research_id)
    except Exception as e:
        _handle_error(e)

@router.delete("/{research_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_research(research_id: str):
    try:
        static_orch.delete_research(research_id)
        await scheduler.schedule(
            quickLog,
            params={
                "message": f"Successfully deleted research {research_id} from API",
                "level": "warning",
                "urgency": "moderate",
                "module": ["API"],
            },
        )
        return
    except Exception as e:
        _handle_error(e)
