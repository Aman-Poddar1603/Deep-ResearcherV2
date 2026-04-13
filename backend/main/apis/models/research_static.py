"""
## Description

Pydantic models for the Research Static API endpoints.
These schemas map directly to the `researches`, `research_sources`,
`research_metadata`, `research_plans`, and `research_templates` tables
defined in `migrations.py`. Only read and delete operations are exposed
through this module — creation is handled exclusively by the research engine.

## Parameters

None (Module level)

## Returns

None (Module level)

## Side Effects

- Registers Pydantic models for FastAPI request/response validation.

## Debug Notes

- If a field is missing from the DB row, Pydantic will use the default
  value (typically `None`). Ensure migrations have been run.

## Customization

- Add new fields here when new columns are added to the corresponding
  migration table schemas.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════
# RESEARCHES
# ═══════════════════════════════════════════════════


class ResearchStaticRecord(BaseModel):
    """
    ## Description

    Represents a single research record from the `researches` table.
    Read-only view — the research engine handles creation and updates.

    ## Parameters

    - `id` (`str`)
      - Description: Unique identifier for the research.
      - Constraints: Primary key. Always non-null.

    - `title` (`Optional[str]`)
      - Description: Human-readable title of the research.

    - `desc` (`Optional[str]`)
      - Description: Description or summary of the research.

    - `prompt` (`Optional[str]`)
      - Description: The original user prompt that initiated the research.

    - `sources` (`Optional[str]`)
      - Description: JSON-encoded list of source references.

    - `workspace_id` (`Optional[str]`)
      - Description: ID of the workspace this research belongs to.

    - `artifacts` (`Optional[str]`)
      - Description: JSON-encoded artifact references produced by the research.

    - `chat_access` (`Optional[bool]`)
      - Description: Whether chat agents can access this research.

    - `background_processing` (`Optional[bool]`)
      - Description: Whether background processing is enabled.

    - `research_template_id` (`Optional[str]`)
      - Description: FK to the research template used, if any.

    - `custom_instructions` (`Optional[str]`)
      - Description: Custom instructions provided for the research workflow.

    - `prompt_order` (`Optional[str]`)
      - Description: JSON-encoded prompt ordering configuration.

    ## Returns

    `ResearchStaticRecord` — Pydantic model instance.
    """

    id: str
    title: Optional[str] = None
    desc: Optional[str] = None
    prompt: Optional[str] = None
    sources: Optional[str] = None
    workspace_id: Optional[str] = None
    artifacts: Optional[str] = None
    chat_access: Optional[bool] = None
    background_processing: Optional[bool] = None
    research_template_id: Optional[str] = None
    custom_instructions: Optional[str] = None
    prompt_order: Optional[str] = None

    model_config = {"from_attributes": True}


class ResearchStaticListResponse(BaseModel):
    """
    ## Description

    Paginated list response for research records.

    ## Parameters

    - `items` (`list[ResearchStaticRecord]`)
      - Description: Page slice of research records.

    - `page` (`int`)
      - Description: Current page number (1-indexed).

    - `size` (`int`)
      - Description: Requested page size.

    - `total_items` (`int`)
      - Description: Total number of items matching the query.

    - `total_pages` (`int`)
      - Description: Total number of pages.

    - `offset` (`int`)
      - Description: Zero-based offset of the first item on this page.

    ## Returns

    `ResearchStaticListResponse` — Pydantic model instance.
    """

    items: list[ResearchStaticRecord] = Field(default_factory=list)
    page: int = 1
    size: int = 20
    total_items: int = 0
    total_pages: int = 0
    offset: int = 0


# ═══════════════════════════════════════════════════
# RESEARCH SOURCES
# ═══════════════════════════════════════════════════


class ResearchSourceStaticRecord(BaseModel):
    """
    ## Description

    Represents a single research source record from the `research_sources` table.

    ## Parameters

    - `id` (`str`)
      - Description: Unique identifier for the research source.

    - `research_id` (`Optional[str]`)
      - Description: FK to the parent research.

    - `source_type` (`Optional[str]`)
      - Description: Type of source (e.g. "web", "file", "api").

    - `source_url` (`Optional[str]`)
      - Description: URL of the source.

    - `source_content` (`Optional[str]`)
      - Description: Raw content scraped/extracted from the source.

    - `source_citations` (`Optional[str]`)
      - Description: JSON-encoded citation metadata.

    - `source_vector_id` (`Optional[str]`)
      - Description: Vector store ID for the embedded content.

    - `step_index` (`Optional[int]`)
      - Description: Step index in the research workflow.

    - `temp_file_path` (`Optional[str]`)
      - Description: Temporary file path used during research.

    - `created_at` (`Optional[str]`)
      - Description: ISO 8601 timestamp of creation.

    - `updated_at` (`Optional[str]`)
      - Description: ISO 8601 timestamp of last update.

    ## Returns

    `ResearchSourceStaticRecord` — Pydantic model instance.
    """

    id: str
    research_id: Optional[str] = None
    source_type: Optional[str] = None
    source_url: Optional[str] = None
    source_content: Optional[str] = None
    source_citations: Optional[str] = None
    source_vector_id: Optional[str] = None
    step_index: Optional[int] = None
    temp_file_path: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


class ResearchSourceStaticListResponse(BaseModel):
    """
    ## Description

    Paginated list response for research source records.

    ## Parameters

    - `items` (`list[ResearchSourceStaticRecord]`)
      - Description: Page slice of source records.

    - `page` (`int`)
      - Description: Current page number.

    - `size` (`int`)
      - Description: Requested page size.

    - `total_items` (`int`)
      - Description: Total matching items.

    - `total_pages` (`int`)
      - Description: Total pages.

    - `offset` (`int`)
      - Description: Zero-based offset.

    ## Returns

    `ResearchSourceStaticListResponse` — Pydantic model instance.
    """

    items: list[ResearchSourceStaticRecord] = Field(default_factory=list)
    page: int = 1
    size: int = 20
    total_items: int = 0
    total_pages: int = 0
    offset: int = 0


# ═══════════════════════════════════════════════════
# RESEARCH METADATA
# ═══════════════════════════════════════════════════


class ResearchMetadataRecord(BaseModel):
    """
    ## Description

    Represents a single research metadata record from the `research_metadata` table.

    ## Parameters

    - `id` (`str`)
      - Description: Unique identifier for the metadata record.

    - `models` (`Optional[str]`)
      - Description: JSON-encoded list of models used.

    - `workspace_id` (`Optional[str]`)
      - Description: Workspace this metadata belongs to.

    - `research_id` (`Optional[str]`)
      - Description: FK to parent research.

    - `connected_bucket` (`Optional[str]`)
      - Description: Bucket ID connected to this research.

    - `time_taken_sec` (`Optional[int]`)
      - Description: Total time taken in seconds.

    - `token_count` (`Optional[int]`)
      - Description: Total tokens consumed.

    - `num_api_calls` (`Optional[int]`)
      - Description: Number of external API calls made.

    - `source_count` (`Optional[int]`)
      - Description: Total sources discovered.

    - `websites_count` (`Optional[int]`)
      - Description: Number of websites crawled.

    - `file_count` (`Optional[int]`)
      - Description: Number of files processed.

    - `citations` (`Optional[str]`)
      - Description: JSON-encoded citation metadata.

    - `exported` (`Optional[str]`)
      - Description: Export status or path.

    - `status` (`Optional[bool]`)
      - Description: Whether the metadata record is active.

    - `chats_referenced` (`Optional[str]`)
      - Description: JSON-encoded list of chat thread IDs referenced.

    - `created_at` (`Optional[str]`)
      - Description: ISO 8601 timestamp.

    - `updated_at` (`Optional[str]`)
      - Description: ISO 8601 timestamp.

    ## Returns

    `ResearchMetadataRecord` — Pydantic model instance.
    """

    id: str
    models: Optional[str] = None
    workspace_id: Optional[str] = None
    research_id: Optional[str] = None
    connected_bucket: Optional[str] = None
    time_taken_sec: Optional[int] = None
    token_count: Optional[int] = None
    num_api_calls: Optional[int] = None
    source_count: Optional[int] = None
    websites_count: Optional[int] = None
    file_count: Optional[int] = None
    citations: Optional[str] = None
    exported: Optional[str] = None
    status: Optional[Any] = None
    chats_referenced: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════
# RESEARCH PLANS
# ═══════════════════════════════════════════════════


class ResearchPlanRecord(BaseModel):
    """
    ## Description

    Represents a single research plan record from the `research_plans` table.

    ## Parameters

    - `id` (`str`)
      - Description: Unique identifier for the plan.

    - `title` (`Optional[str]`)
      - Description: Plan title.

    - `desc` (`Optional[str]`)
      - Description: Plan description.

    - `plan` (`Optional[str]`)
      - Description: JSON-encoded plan structure.

    - `workflow` (`Optional[str]`)
      - Description: JSON-encoded workflow definition.

    - `workspace_id` (`Optional[str]`)
      - Description: Workspace this plan belongs to.

    - `research_template_id` (`Optional[str]`)
      - Description: FK to the template used.

    - `prompt_order` (`Optional[str]`)
      - Description: JSON-encoded prompt ordering.

    ## Returns

    `ResearchPlanRecord` — Pydantic model instance.
    """

    id: str
    title: Optional[str] = None
    desc: Optional[str] = None
    plan: Optional[str] = None
    workflow: Optional[str] = None
    workspace_id: Optional[str] = None
    research_template_id: Optional[str] = None
    prompt_order: Optional[str] = None

    model_config = {"from_attributes": True}


class ResearchPlanListResponse(BaseModel):
    """
    ## Description

    Paginated list response for research plan records.

    ## Parameters

    - `items` (`list[ResearchPlanRecord]`)
      - Description: Page slice of plan records.

    - `page` (`int`)
      - Description: Current page number.

    - `size` (`int`)
      - Description: Requested page size.

    - `total_items` (`int`)
      - Description: Total matching items.

    - `total_pages` (`int`)
      - Description: Total pages.

    - `offset` (`int`)
      - Description: Zero-based offset.

    ## Returns

    `ResearchPlanListResponse` — Pydantic model instance.
    """

    items: list[ResearchPlanRecord] = Field(default_factory=list)
    page: int = 1
    size: int = 20
    total_items: int = 0
    total_pages: int = 0
    offset: int = 0


# ═══════════════════════════════════════════════════
# RESEARCH TEMPLATES
# ═══════════════════════════════════════════════════


class ResearchTemplateRecord(BaseModel):
    """
    ## Description

    Represents a single research template record from the `research_templates` table.

    ## Parameters

    - `id` (`str`)
      - Description: Unique identifier for the template.

    - `title` (`Optional[str]`)
      - Description: Template title.

    - `desc` (`Optional[str]`)
      - Description: Template description.

    - `template` (`Optional[str]`)
      - Description: JSON-encoded template body.

    - `total_researches` (`Optional[int]`)
      - Description: Count of researches using this template.

    - `created_at` (`Optional[str]`)
      - Description: ISO 8601 timestamp.

    - `updated_at` (`Optional[str]`)
      - Description: ISO 8601 timestamp.

    ## Returns

    `ResearchTemplateRecord` — Pydantic model instance.
    """

    id: str
    title: Optional[str] = None
    desc: Optional[str] = None
    template: Optional[str] = None
    total_researches: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


class ResearchTemplateListResponse(BaseModel):
    """
    ## Description

    Paginated list response for research template records.

    ## Parameters

    - `items` (`list[ResearchTemplateRecord]`)
      - Description: Page slice of template records.

    - `page` (`int`)
      - Description: Current page number.

    - `size` (`int`)
      - Description: Requested page size.

    - `total_items` (`int`)
      - Description: Total matching items.

    - `total_pages` (`int`)
      - Description: Total pages.

    - `offset` (`int`)
      - Description: Zero-based offset.

    ## Returns

    `ResearchTemplateListResponse` — Pydantic model instance.
    """

    items: list[ResearchTemplateRecord] = Field(default_factory=list)
    page: int = 1
    size: int = 20
    total_items: int = 0
    total_pages: int = 0
    offset: int = 0
