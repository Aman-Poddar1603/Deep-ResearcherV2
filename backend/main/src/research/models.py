from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Optional, Any, Dict
from datetime import datetime

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class ResearchStage(str, Enum):
    VALIDATING = "validating_query"
    PLANNING = "generating_research_plan"
    SEARCHING = "searching_sources"
    SCRAPING = "scraping_content"
    SUMMARIZING = "summarizing_findings"
    ANALYZING = "analyzing_data"
    ARTIFACT_GEN = "generating_artifact"
    FINALIZING = "finalizing_output"

class RedisEvent(BaseModel):
    job_id: str
    stage: str
    status: JobStatus
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class ResearchStep(BaseModel):
    id: str
    description: str
    status: str = "pending"
    result: Optional[str] = None

class ResearchPlan(BaseModel):
    title: str
    steps: List[ResearchStep]

class ArtifactSection(BaseModel):
    heading: str
    content: str

class Artifact(BaseModel):
    title: str
    type: str
    summary: str
    key_insights: List[str]
    detailed_sections: List[ArtifactSection]
    actionable_steps: List[str]
    sources: List[str]
    videos: List[Dict[str, str]] = [] # {title, url}
    images: List[Dict[str, str]] = [] # {alt, url}
    highlights: List[str] = []
    markdown_content: Optional[str] = None
    confidence_score: str
