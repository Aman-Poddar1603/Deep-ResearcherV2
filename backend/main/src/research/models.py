import uuid
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


# ─── Input ────────────────────────────────────────────────────────────────────


class ResearchStartRequest(BaseModel):
    prompt: str
    sources: list[str] = []
    workspace_id: str
    system_prompt: str = ""
    custom_prompt: str = ""
    title: str | None = None
    description: str | None = None
    research_template: str = ""
    ai_personality: str = "professional research analyst"
    username: str


# ─── Plan ─────────────────────────────────────────────────────────────────────


class PlanStep(BaseModel):
    step_index: int
    step_title: str
    step_description: str
    suggested_tools: list[str] = []
    estimated_complexity: Literal["low", "medium", "high"] = "medium"


class ResearchPlan(BaseModel):
    steps: list[PlanStep]


# ─── Cleaner output ───────────────────────────────────────────────────────────


class CleanedInput(BaseModel):
    cleaned_prompt: str
    title: str = ""
    description: str = ""


# ─── Guard output ─────────────────────────────────────────────────────────────


class GuardResult(BaseModel):
    safe: bool
    reason: str = ""


# ─── Q&A ─────────────────────────────────────────────────────────────────────


class QAPair(BaseModel):
    question: str
    answer: str


class NextQuestion(BaseModel):
    question: str | None = None
    done: bool = False


# ─── Layer 1 context passed to Layer 2 ───────────────────────────────────────


class ResearchContext(BaseModel):
    research_id: str
    cleaned_prompt: str
    title: str
    description: str
    plan: list[PlanStep]
    qa_history: list[QAPair] = []
    sources: list[str] = []
    workspace_id: str
    system_prompt: str = ""
    custom_prompt: str = ""
    research_template: str = ""
    ai_personality: str = "professional research analyst"
    username: str


# ─── Token tracking ───────────────────────────────────────────────────────────


class TokenCounts(BaseModel):
    grand_total: int = 0
    by_model: dict[str, int] = Field(default_factory=lambda: {"ollama": 0, "groq": 0})
    by_step: dict[str, int] = Field(default_factory=dict)


# ─── WS events (typed payloads) ───────────────────────────────────────────────


class WSEvent(BaseModel):
    event: str
    research_id: str
    ts: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class InputValidatedEvent(WSEvent):
    event: str = "input.validated"
    title: str
    description: str
    cleaned_prompt: str


class InputQAQuestionEvent(WSEvent):
    event: str = "input.qa_question"
    question: str
    question_index: int


class InputPlanReadyEvent(WSEvent):
    event: str = "input.plan_ready"
    plan: list[dict]


class InputApprovedEvent(WSEvent):
    event: str = "input.approved"
    confirmed: bool


class PlanStepStartedEvent(WSEvent):
    event: str = "plan.step_started"
    step_index: int
    step_title: str
    total_steps: int
    status: str = "running"


class PlanStepCompletedEvent(WSEvent):
    event: str = "plan.step_completed"
    step_index: int
    step_title: str
    summary: str


class PlanStepFailedEvent(WSEvent):
    event: str = "plan.step_failed"
    step_index: int
    error: str


class PlanAllDoneEvent(WSEvent):
    event: str = "plan.all_done"
    total_steps: int
    sources_count: int


class ToolCalledEvent(WSEvent):
    event: str = "tool.called"
    tool_name: str
    args: dict
    step_index: int


class ToolResultEvent(WSEvent):
    event: str = "tool.result"
    tool_name: str
    result_summary: str
    step_index: int
    result_payload: list[dict[str, Any]] = Field(default_factory=list)


class ToolErrorEvent(WSEvent):
    event: str = "tool.error"
    tool_name: str
    error: str
    step_index: int = -1


class ThinkChunkEvent(WSEvent):
    event: str = "think.chunk"
    text: str
    step_index: int


class ThinkDoneEvent(WSEvent):
    event: str = "think.done"
    step_index: int


class ArtifactChunkEvent(WSEvent):
    event: str = "artifact.chunk"
    text: str


class ArtifactDoneEvent(WSEvent):
    event: str = "artifact.done"
    total_tokens_in_artifact: int


class TokensUpdateEvent(WSEvent):
    event: str = "tokens.update"
    delta: int
    input_delta: int = 0
    output_delta: int = 0
    grand_total: int
    by_direction: dict[str, int] = Field(
        default_factory=lambda: {"input": 0, "output": 0}
    )
    by_model: dict[str, int]
    by_step: dict[str, int]
    source: str
    step_index: int


class StopRequestedEvent(WSEvent):
    event: str = "stop.requested"


class StopFlushingEvent(WSEvent):
    event: str = "stop.flushing"
    message: str


class StopSavedEvent(WSEvent):
    event: str = "stop.saved"
    partial_sources_count: int
    chroma_vectors_saved: int


class SystemProgressEvent(WSEvent):
    event: str = "system.progress"
    message: str
    percent: int


class SystemErrorEvent(WSEvent):
    event: str = "system.error"
    message: str
    recoverable: bool


class SystemReconnectedEvent(WSEvent):
    event: str = "system.reconnected"
    last_step: int
    status: str
    token_totals: dict


class SystemConnectedEvent(WSEvent):
    event: str = "system.connected"
    status: str


class ReactReasonEvent(WSEvent):
    event: str = "react.reason"
    step_index: int
    thought: str


class ReactActEvent(WSEvent):
    event: str = "react.act"
    step_index: int
    tool_name: str


class ReactObserveEvent(WSEvent):
    event: str = "react.observe"
    step_index: int
    observation_summary: str
