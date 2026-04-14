// ─── Cursor / Event IDs ───────────────────────────────────────────────────────
export type EventCursor = string | number | null

// ─── Session Status ───────────────────────────────────────────────────────────
export type ResearchSessionStatus =
    | 'idle'
    | 'connecting'
    | 'connected'
    | 'starting'
    | 'waiting_for_answer'
    | 'waiting_for_approval'
    | 'running'
    | 'stopping'
    | 'stopped'
    | 'completed'
    | 'failed'
    | 'disconnected'
    | 'not_found'

// ─── Token Info ───────────────────────────────────────────────────────────────
export interface TokenInfo {
    input_tokens: number
    output_tokens: number
    total_tokens: number
}

// ─── Tool Call ────────────────────────────────────────────────────────────────
export interface LiveToolCall {
    id: string
    tool_name: string
    createdAt: number
    args?: unknown
    result?: string
    error?: string
    state: 'called' | 'running' | 'done' | 'error'
}

// ─── Research Step (live) ─────────────────────────────────────────────────────
export interface LiveStep {
    index: number
    title: string
    status: 'pending' | 'running' | 'completed' | 'failed'
    summary?: string
    error?: string
    thinking: string
    thinkingDone: boolean
    tools: LiveToolCall[]
}

// ─── QA / Plan pending ───────────────────────────────────────────────────────
export interface QAQuestion {
    question: string
    index: number
}

export interface PendingInput {
    type?: string
    question?: string
    question_index?: number
    plan?: unknown
    [key: string]: unknown
}

// ─── Start payload sent to POST /research/start ───────────────────────────────
export interface ResearchStartPayload {
    prompt: string
    sources: { type: string; value: string; name?: string }[]
    workspace_id: string
    system_prompt?: string
    custom_prompt?: string
    title: string
    description: string
    research_template: string
    ai_personality?: string
    username?: string
}

// ─── Backend response types ───────────────────────────────────────────────────
export interface StartResponse {
    research_id: string
    status?: string
    status_url?: string
    replay_url?: string
    resume_url?: string
    websocket_url?: string
    [key: string]: unknown
}

export interface StatusResponse {
    research_id?: string
    status?: string
    current_step?: number
    total_steps?: number
    token_totals?: unknown
    latest_event_id?: EventCursor
    pending_input?: PendingInput | null
    [key: string]: unknown
}

export interface ResumeBundle extends StatusResponse {
    research_id: string
    resume_schema_version?: string
    prompt?: string
    status_url?: string
    replay_url?: string
    resume_url?: string
    websocket_url?: string
    context?: unknown
    plan?: unknown
    steps?: PredictableStep[]
    artifact?: StructuredArtifact | null
    steps_details?: Array<Record<string, unknown>>
    timeline_events?: Array<Record<string, unknown>>
    timeline_replay_count?: number
    timeline_next_event_id?: EventCursor
}

export interface PredictableStepContent {
    think?: string
    chain_of_thought?: unknown[]
    tool_call?: Array<Record<string, unknown>>
    summary?: string
}

export interface PredictableStep {
    step?: number
    step_index?: number
    title?: string
    description?: string
    status?: string
    content?: PredictableStepContent | null
}

export interface StructuredArtifact {
    type?: string
    content?: string
    complete?: boolean
    tokens_used?: number
    updated_at?: string
}

export interface ReplayResponse {
    events: Array<Record<string, unknown>>
    replay_count?: number
    next_event_id?: EventCursor
    [key: string]: unknown
}

// ─── Full live session state ──────────────────────────────────────────────────
export interface ResearchLiveState {
    status: ResearchSessionStatus
    researchId: string
    steps: LiveStep[]
    questions: QAQuestion[]
    plan: { plan: string } | null
    planApproved: boolean | null
    artifact: string
    artifactDone: boolean
    tokens: TokenInfo
    error: string | null
    progress: number
    progressMsg: string
}

// ─── Stored session record (localStorage) ────────────────────────────────────
export interface ResumeSessionRecord {
    research_id: string
    status_url: string
    replay_url: string
    resume_url: string
    websocket_url: string
    last_known_event_id: EventCursor
    last_status: Record<string, unknown> | null
    pending_input: PendingInput | null
    updated_at: number
}
