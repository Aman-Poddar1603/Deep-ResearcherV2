import { useState, useRef, useCallback, useEffect, useMemo } from 'react'
import { ResearchStreamManager, ResearchApiService, isSessionNotFoundError } from './research_api'
import {
    createTimelineTracker, resetTimelineTracker, parseEventEnvelope,
    shouldApplyEvent, markEventApplied, extractCursorFromMessage,
    appendStreamChunk, finalizeText, normalizeTokenInfo, normalizeRuntimeUrls,
    compareCursor, toPlanText, isTerminalStatus, ResearchSessionStore,
    DEFAULT_REPLAY_LIMIT, readBackendBase, parseBackendBase, eventField,
    eventString, eventNumber, eventBoolean,
} from './research_utils'
import type {
    ResearchSessionStatus, LiveStep, LiveToolCall, QAQuestion, TokenInfo,
    PendingInput, ResumeBundle, EventCursor, ResearchStartPayload,
} from './research_types'

// ─── Internal helpers ─────────────────────────────────────────────────────────
type JO = Record<string, unknown>

function genId() { return crypto.randomUUID() }

function createEmptyStep(index: number, title = `Step ${index + 1}`): LiveStep {
    return { index, title, status: 'running', summary: '', error: '', thinking: '', thinkingDone: false, tools: [] }
}

function toSessionStatus(value: unknown, fallback: ResearchSessionStatus): ResearchSessionStatus {
    if (typeof value !== 'string') return fallback
    const map: Record<string, ResearchSessionStatus> = {
        idle: 'idle', connecting: 'connecting', connected: 'connected', starting: 'starting',
        waiting_for_answer: 'waiting_for_answer', waiting_for_answer2: 'waiting_for_answer',
        waiting_for_approval: 'waiting_for_approval', running: 'running', stopping: 'stopping',
        stopped: 'stopped', completed: 'completed', failed: 'failed', disconnected: 'disconnected',
        not_found: 'not_found', layer1_qa: 'waiting_for_answer', qa: 'waiting_for_answer',
        plan_approval: 'waiting_for_approval', researching: 'running', executing: 'running',
        done: 'completed', error: 'failed', canceled: 'stopped', cancelled: 'stopped', expired: 'not_found',
    }
    return map[value.trim().toLowerCase()] ?? fallback
}

function parseStepIndex(value: unknown): number | null {
    if (typeof value === 'number' && Number.isFinite(value)) return value >= 0 ? Math.floor(value) : null
    if (typeof value !== 'string') return null
    const m = value.trim().match(/[-]?\d+/)
    if (m) {
        const num = Number.parseInt(m[0], 10)
        return num >= 0 ? num : null
    }
    return null
}

function sameToolSig(aName: string, aArgs: unknown, bName: string, bArgs: unknown): boolean {
    const ss = (v: unknown): string => {
        if (v === null || typeof v !== 'object') return JSON.stringify(v)
        if (Array.isArray(v)) return `[${v.map(ss).join(',')}]`
        const keys = Object.keys(v as JO).sort()
        return `{${keys.map(k => `${JSON.stringify(k)}:${ss((v as JO)[k])}`).join(',')}}`
    }
    return aName === bName && ss(aArgs) === ss(bArgs)
}

function progressFromCounts(cur: unknown, tot: unknown, fallback: number): number {
    if (typeof cur !== 'number' || typeof tot !== 'number' || tot <= 0) return fallback
    return Math.max(0, Math.min(100, Math.round((cur / tot) * 100)))
}

function progressLabel(cur: unknown, tot: unknown, fallback: string): string {
    if (typeof cur !== 'number' || typeof tot !== 'number' || tot <= 0) return fallback
    const step = Math.max(1, Math.min(Math.floor(cur) + 1, tot))
    return `Step ${step} of ${tot}`
}

function toPercent(v: unknown): number | null {
    if (typeof v !== 'number' || Number.isNaN(v)) return null
    return v >= 0 && v <= 1 ? Math.round(v * 100) : Math.round(v)
}

function extractPendingQuestion(pending: PendingInput | null): QAQuestion | null {
    if (!pending || pending.type !== 'qa_question') return null

    const payload = pending.payload && typeof pending.payload === 'object'
        ? pending.payload as JO
        : null

    const question = typeof pending.question === 'string'
        ? pending.question.trim()
        : typeof payload?.question === 'string'
            ? payload.question.trim()
            : ''

    if (!question) return null

    const index = typeof pending.question_index === 'number'
        ? pending.question_index
        : typeof payload?.question_index === 'number'
            ? payload.question_index
            : 0

    return { question, index }
}

function extractPendingPlanText(pending: PendingInput | null, fallbackPlan?: unknown): string {
    if (pending?.type === 'plan_approval') {
        const payload = pending.payload && typeof pending.payload === 'object'
            ? pending.payload as JO
            : null
        const fromPending = pending.plan ?? pending.current_plan ?? payload?.plan ?? payload?.current_plan
        return toPlanText(fromPending ?? fallbackPlan)
    }
    return fallbackPlan ? toPlanText(fallbackPlan) : ''
}

function buildResumeSteps(planSource: unknown, currentStep: unknown, totalSteps: unknown, status: ResearchSessionStatus): LiveStep[] {
    const planRows = Array.isArray(planSource)
        ? planSource.filter((r): r is JO => !!r && typeof r === 'object') : []
    const current = parseStepIndex(currentStep)
    const total = typeof totalSteps === 'number' && totalSteps > 0 ? totalSteps : planRows.length
    const count = Math.max(total, planRows.length)
    if (count <= 0) return []
    const runningLike = ['running', 'starting', 'connected', 'connecting', 'stopping'].includes(status)
    return Array.from({ length: count }, (_, idx) => {
        const planItem = planRows.find(r => parseStepIndex(r.step_index) === idx)
        const title = (planItem && typeof planItem.step_title === 'string' ? planItem.step_title.trim() : '')
            || (planItem && typeof planItem.step_name === 'string' ? planItem.step_name.trim() : '')
            || `Step ${idx + 1}`
        let stepStatus: LiveStep['status'] = 'pending'
        if (status === 'completed') stepStatus = 'completed'
        else if (status === 'failed' && current !== null && idx === current) stepStatus = 'failed'
        else if (current !== null) {
            if (idx < current) stepStatus = 'completed'
            else if (idx === current && runningLike) stepStatus = 'running'
        } else if (idx === 0 && runningLike) stepStatus = 'running'
        return { ...createEmptyStep(idx, title), status: stepStatus }
    })
}

// ─── Hook return type ─────────────────────────────────────────────────────────
export interface UseResearchSessionReturn {
    // State
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
    isRunning: boolean
    isPendingQuestion: boolean
    isPendingApproval: boolean
    context: Partial<ResearchStartPayload>

    // Actions
    startResearch: (payload: ResearchStartPayload) => Promise<void>
    resumeSession: (researchId: string) => Promise<void>
    stopResearch: () => Promise<void>
    submitAnswer: (answer: string) => void
    approvePlan: () => void
    refactorPlan: (feedback: string) => void
    disconnect: () => void
}

// ─── Hook ─────────────────────────────────────────────────────────────────────
export function useResearchSession(options?: {
    researchId?: string
    backendBase?: string
    onNavigateToSession?: (id: string, replace?: boolean) => void
}): UseResearchSessionReturn {

    type StepState = {
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
        context: Partial<ResearchStartPayload>
    }

    const [state, setState] = useState<StepState>({
        status: 'idle', researchId: options?.researchId ?? '',
        steps: [], questions: [], plan: null, planApproved: null,
        artifact: '', artifactDone: false, tokens: normalizeTokenInfo(),
        error: null, progress: 0, progressMsg: '',
        context: {},
    })

    // Refs that don't trigger re-renders
    const optionsRef = useRef(options)
    useEffect(() => { optionsRef.current = options }, [options])

    const stateRef = useRef(state)
    const cursorRef = useRef<EventCursor>(null)
    const cursorSourceRef = useRef<'timeline' | 'stream' | 'status'>('status')
    const manualDisconnectRef = useRef(false)
    const statusUrlRef = useRef('')
    const replayUrlRef = useRef('')
    const resumeUrlRef = useRef('')
    const websocketUrlRef = useRef('')
    const pendingInputRef = useRef<PendingInput | null>(null)
    const outboundQueueRef = useRef<unknown[]>([])
    const backendBaseRef = useRef(parseBackendBase(options?.backendBase) ?? readBackendBase())
    const streamManagerRef = useRef<ResearchStreamManager | null>(null)
    const timelineTracker = useRef(createTimelineTracker())
    const apiService = useMemo(() => new ResearchApiService(backendBaseRef.current), [])

    useEffect(() => { stateRef.current = state }, [state])

    const s = useCallback((fn: (prev: StepState) => StepState) => setState(fn), [])

    const applyPendingSnapshot = useCallback((base: StepState, pending: PendingInput | null, planFallback?: unknown): StepState => {
        const pendingQuestion = extractPendingQuestion(pending)
        if (pendingQuestion) {
            return {
                ...base,
                status: 'waiting_for_answer',
                questions: [pendingQuestion],
            }
        }

        const pendingPlanText = extractPendingPlanText(pending, planFallback)
        if (pending?.type === 'plan_approval' && pendingPlanText) {
            return {
                ...base,
                status: 'waiting_for_approval',
                planApproved: null,
                plan: { plan: pendingPlanText },
            }
        }

        return base
    }, [])

    const flushOutboundQueue = useCallback(() => {
        const manager = streamManagerRef.current
        if (!manager?.isOpen()) return
        if (outboundQueueRef.current.length === 0) return

        const queued = [...outboundQueueRef.current]
        outboundQueueRef.current = []
        for (const payload of queued) manager.send(payload)
    }, [])

    const sendOrQueue = useCallback((payload: unknown): boolean => {
        const manager = streamManagerRef.current
        if (manager?.isOpen()) {
            manager.send(payload)
            return true
        }

        outboundQueueRef.current.push(payload)
        if (outboundQueueRef.current.length > 20) {
            outboundQueueRef.current = outboundQueueRef.current.slice(-20)
        }
        return false
    }, [])

    // ── Cursor management ────────────────────────────────────────────────────
    const PRIORITY = { timeline: 3, stream: 2, status: 1 } as const

    const setCursor = useCallback((cursor: EventCursor, source: 'timeline' | 'stream' | 'status', rid?: string) => {
        if (cursor === null || cursor === undefined) return
        if (typeof cursor === 'string' && cursor.trim().length === 0) return
        const current = cursorRef.current
        if (current !== null) {
            const cmp = compareCursor(cursor, current)
            if (cmp === null) {
                if (PRIORITY[source] < PRIORITY[cursorSourceRef.current]) return
            } else if (cmp <= 0) return
        }
        cursorRef.current = cursor
        cursorSourceRef.current = source
        streamManagerRef.current?.updateCursor(cursor)
        const researchId = rid ?? stateRef.current.researchId
        if (researchId) ResearchSessionStore.upsert({ research_id: researchId, last_known_event_id: cursor })
    }, [])

    // ── Persist to localStorage ──────────────────────────────────────────────
    const persist = useCallback((rid: string, patch?: Partial<{
        status_url: string; replay_url: string; resume_url: string; websocket_url: string
        last_known_event_id: EventCursor; last_status: JO | null; pending_input: PendingInput | null
    }>) => {
        if (!rid) return
        ResearchSessionStore.upsert({
            research_id: rid,
            status_url: patch?.status_url ?? statusUrlRef.current,
            replay_url: patch?.replay_url ?? replayUrlRef.current,
            resume_url: patch?.resume_url ?? resumeUrlRef.current,
            websocket_url: patch?.websocket_url ?? websocketUrlRef.current,
            last_known_event_id: patch?.last_known_event_id ?? cursorRef.current,
            pending_input: patch?.pending_input ?? pendingInputRef.current,
        })
    }, [])

    // ── Reset state for a new run ────────────────────────────────────────────
    const resetRunState = useCallback((rid?: string, status: ResearchSessionStatus = 'starting') => {
        resetTimelineTracker(timelineTracker.current)
        cursorRef.current = null
        cursorSourceRef.current = 'status'
        pendingInputRef.current = null
        outboundQueueRef.current = []
        streamManagerRef.current?.updateCursor(null)
        s(prev => ({
            ...prev,
            researchId: rid ?? prev.researchId,
            status, steps: [], questions: [], plan: null, planApproved: null,
            artifact: '', artifactDone: false, progress: 0, progressMsg: '',
            error: null, tokens: normalizeTokenInfo(),
            context: {},
        }))
    }, [])

    // ── Core event applier ───────────────────────────────────────────────────
    const applyMessage = useCallback((msg: JO) => {
        const envelope = parseEventEnvelope(msg)
        if (!envelope) return
        const incomingRid = eventString(msg, 'research_id') ?? ''
        const activeRid = stateRef.current.researchId
        if (incomingRid && activeRid && incomingRid !== activeRid) return
        if (!shouldApplyEvent(timelineTracker.current, envelope)) return
        markEventApplied(timelineTracker.current, envelope)

        const evt = envelope.event
        const cursor = extractCursorFromMessage(msg)
        if (cursor !== null) setCursor(cursor, 'stream', incomingRid || activeRid)

        s(prev => {
            const rid = incomingRid || prev.researchId
            const next = { ...prev, researchId: rid }

            const ensureStep = (steps: LiveStep[], idx: number, title?: string): LiveStep[] => {
                const arr = [...steps]
                if (!arr[idx]) arr[idx] = createEmptyStep(idx, title)
                return arr
            }

            switch (evt) {
                case 'system.connected':
                case 'system.reconnected':
                    return {
                        ...next,
                        status: toSessionStatus(eventField(msg, 'status'), 'connected'),
                        error: null,
                        tokens: evt === 'system.reconnected'
                            ? normalizeTokenInfo(eventField(msg, 'token_totals') ?? next.tokens)
                            : next.tokens,
                    }

                case 'system.progress': {
                    const pct = toPercent(eventField(msg, 'progress') ?? eventField(msg, 'percent'))
                    return { ...next, progress: pct ?? next.progress, progressMsg: eventString(msg, 'message') ?? next.progressMsg }
                }

                case 'system.error': {
                    const recoverable = eventBoolean(msg, 'recoverable')
                    return {
                        ...next,
                        status: recoverable ? next.status : 'failed',
                        error: eventString(msg, 'message') ?? 'Backend error',
                    }
                }

                case 'input.qa_question': {
                    const question = eventString(msg, 'question') ?? ''
                    if (!question) return next
                    const indexFromEvent = eventNumber(msg, 'question_index')
                    const index = indexFromEvent ?? (next.questions.length > 0 ? Math.max(...next.questions.map(q => q.index)) + 1 : 0)
                    const questions = [...next.questions.filter(q => q.index !== index), { question, index }].sort((a, b) => a.index - b.index)
                    pendingInputRef.current = { type: 'qa_question', question, question_index: index }
                    return { ...next, status: 'waiting_for_answer', questions }
                }

                case 'input.plan_ready': {
                    const planValue = eventField(msg, 'plan')
                    pendingInputRef.current = { type: 'plan_approval', plan: planValue }
                    return { ...next, status: 'waiting_for_approval', planApproved: null, plan: { plan: toPlanText(planValue) } }
                }

                case 'input.approved': {
                    const confirmed = eventBoolean(msg, 'confirmed')
                    pendingInputRef.current = null
                    return { ...next, status: 'running', planApproved: confirmed ?? true }
                }

                case 'plan.step_started': {
                    const idx = eventNumber(msg, 'step_index') ?? 0
                    const stepName = eventString(msg, 'step_name', 'step_title') ?? undefined
                    const totalSteps = eventNumber(msg, 'total_steps')
                    const steps = ensureStep(next.steps, idx, stepName)
                    steps[idx] = { ...steps[idx], status: 'running', title: stepName || steps[idx].title }
                    return {
                        ...next, status: 'running', steps,
                        progressMsg: totalSteps !== null ? progressLabel(idx, totalSteps, next.progressMsg) : next.progressMsg,
                    }
                }

                case 'plan.step_completed': {
                    const idx = eventNumber(msg, 'step_index') ?? 0
                    const steps = [...next.steps]
                    if (steps[idx]) {
                        const raw = eventField(msg, 'summary') ?? eventField(msg, 'result')
                        steps[idx] = { ...steps[idx], status: 'completed', summary: typeof raw === 'string' ? raw : 'Step completed' }
                    }
                    return { ...next, steps }
                }

                case 'plan.step_failed': {
                    const idx = eventNumber(msg, 'step_index') ?? 0
                    const steps = [...next.steps]
                    if (steps[idx]) steps[idx] = { ...steps[idx], status: 'failed', error: eventString(msg, 'error') ?? 'Step failed' }
                    return { ...next, steps }
                }

                case 'plan.all_done':
                    return { ...next, progress: 100, status: 'completed', progressMsg: 'Research complete' }

                case 'react.reason':
                case 'think.chunk': {
                    const idx = eventNumber(msg, 'step_index') ?? Math.max(0, next.steps.length - 1)
                    const steps = ensureStep(next.steps, idx)
                    const rawChunk = eventString(msg, 'chunk', 'reasoning', 'thought', 'text') ?? ''
                    if (!rawChunk) return next
                    steps[idx] = { ...steps[idx], thinking: appendStreamChunk(steps[idx].thinking, rawChunk) }
                    return { ...next, steps }
                }

                case 'think.done': {
                    const idx = eventNumber(msg, 'step_index') ?? Math.max(0, next.steps.length - 1)
                    const steps = [...next.steps]
                    if (steps[idx]) {
                        const full = eventString(msg, 'full_thought') ?? ''
                        steps[idx] = {
                            ...steps[idx],
                            thinking: full ? finalizeText(steps[idx].thinking, full) : steps[idx].thinking,
                            thinkingDone: true,
                        }
                    }
                    return { ...next, steps }
                }

                case 'tool.called': {
                    const idx = eventNumber(msg, 'step_index') ?? 0
                    const steps = ensureStep(next.steps, idx)
                    const toolName = eventString(msg, 'tool_name', 'name') ?? 'tool'
                    const toolId = eventString(msg, 'tool_id', 'tool_call_id', 'call_id', 'toolCallId', 'toolId', 'callId')
                    const toolArgs = eventField(msg, 'args') ?? eventField(msg, 'arguments')
                    if (toolId && steps[idx].tools.some(t => t.id === toolId)) return next
                    if (!toolId && steps[idx].tools.some(t => sameToolSig(t.tool_name, t.args, toolName, toolArgs))) return next
                    const tool: LiveToolCall = { id: toolId ?? genId(), tool_name: toolName, createdAt: Date.now(), args: toolArgs, state: 'called' }
                    steps[idx] = { ...steps[idx], tools: [...steps[idx].tools, tool] }
                    return { ...next, status: 'running', steps }
                }

                case 'tool.result': {
                    const idx = eventNumber(msg, 'step_index') ?? 0
                    const steps = [...next.steps]
                    if (steps[idx]) {
                        const tools = [...steps[idx].tools]
                        const toolId = eventString(msg, 'tool_id', 'tool_call_id', 'call_id', 'toolCallId', 'toolId', 'callId')
                        const toolName = eventString(msg, 'tool_name', 'name')
                        const args = eventField(msg, 'args') ?? eventField(msg, 'arguments')
                        const raw = eventField(msg, 'result_summary') ?? eventField(msg, 'result') ?? eventField(msg, 'output')
                        const result = typeof raw === 'string' ? raw : raw != null ? JSON.stringify(raw, null, 2) : ''
                        const ti = toolId ? tools.findIndex(t => t.id === toolId)
                            : tools.findIndex(t => toolName && sameToolSig(t.tool_name, t.args, toolName, args) && (t.state === 'called' || t.state === 'running'))
                        if (ti !== -1) {
                            tools[ti] = { ...tools[ti], tool_name: toolName ?? tools[ti].tool_name, args: args ?? tools[ti].args, result: result || tools[ti].result, state: 'done' }
                        } else {
                            tools.push({ id: toolId ?? genId(), tool_name: toolName ?? 'tool', createdAt: Date.now(), args, result, state: 'done' })
                        }
                        steps[idx] = { ...steps[idx], tools }
                    }
                    return { ...next, steps }
                }

                case 'tool.error': {
                    const idx = eventNumber(msg, 'step_index') ?? 0
                    const steps = [...next.steps]
                    if (steps[idx]) {
                        const tools = [...steps[idx].tools]
                        const toolId = eventString(msg, 'tool_id', 'tool_call_id', 'call_id')
                        const toolName = eventString(msg, 'tool_name', 'name')
                        const args = eventField(msg, 'args') ?? eventField(msg, 'arguments')
                        const errorText = eventString(msg, 'error', 'message') ?? 'Tool error'
                        const ti = toolId ? tools.findIndex(t => t.id === toolId)
                            : tools.findIndex(t => toolName && sameToolSig(t.tool_name, t.args, toolName, args))
                        if (ti !== -1) tools[ti] = { ...tools[ti], error: errorText, state: 'error' }
                        else tools.push({ id: toolId ?? genId(), tool_name: toolName ?? 'tool', createdAt: Date.now(), args, error: errorText, state: 'error' })
                        steps[idx] = { ...steps[idx], tools }
                    }
                    return { ...next, steps }
                }

                case 'tokens.update':
                    return { ...next, tokens: normalizeTokenInfo(eventField(msg, 'token_totals') ?? msg) }

                case 'artifact.chunk': {
                    const rawChunk = eventString(msg, 'chunk', 'text') ?? ''
                    if (!rawChunk) return next
                    return { ...next, artifact: appendStreamChunk(next.artifact, rawChunk) }
                }

                case 'artifact.done': {
                    const art = eventField(msg, 'artifact')
                    const artText = typeof art === 'string' ? art : next.artifact
                    return { ...next, artifact: finalizeText(next.artifact, artText), artifactDone: true, status: 'completed' }
                }

                case 'stop.requested': return { ...next, status: 'stopping' }
                case 'stop.flushing': return { ...next, status: 'stopping', progressMsg: eventString(msg, 'message') ?? next.progressMsg }
                case 'stop.saved': return { ...next, status: 'stopped' }

                default: return next
            }
        })

        persist(stateRef.current.researchId)
    }, [setCursor, persist, s])

    // ── Open WebSocket ───────────────────────────────────────────────────────
    const openSocket = useCallback((rid: string, options?: { websocketUrl?: string; lastEventId?: EventCursor; replayLimit?: number }) => {
        const urls = normalizeRuntimeUrls(rid, {
            status_url: statusUrlRef.current,
            replay_url: replayUrlRef.current,
            resume_url: resumeUrlRef.current,
            websocket_url: options?.websocketUrl || websocketUrlRef.current,
        }, backendBaseRef.current)
        statusUrlRef.current = urls.status_url
        replayUrlRef.current = urls.replay_url
        resumeUrlRef.current = urls.resume_url
        websocketUrlRef.current = urls.websocket_url

        if (options?.lastEventId !== undefined) setCursor(options.lastEventId, 'timeline', rid)
        manualDisconnectRef.current = false
        s(prev => ({ ...prev, status: 'connecting', researchId: rid, error: null }))
        streamManagerRef.current?.connect({
            researchId: rid,
            websocketUrl: urls.websocket_url,
            lastEventId: cursorRef.current,
            replayLimit: options?.replayLimit ?? DEFAULT_REPLAY_LIMIT,
        })
        persist(rid, { status_url: urls.status_url, replay_url: urls.replay_url, resume_url: urls.resume_url, websocket_url: urls.websocket_url })
    }, [setCursor, persist])

    // ── Hydrate from resume bundle ───────────────────────────────────────────
    const hydrateBundle = useCallback((bundle: ResumeBundle, rid: string) => {
        const urls = normalizeRuntimeUrls(rid, bundle, backendBaseRef.current)
        statusUrlRef.current = urls.status_url
        replayUrlRef.current = urls.replay_url
        resumeUrlRef.current = urls.resume_url
        websocketUrlRef.current = urls.websocket_url

        const snapshot = bundle.streaming_snapshot && typeof bundle.streaming_snapshot === 'object'
            ? bundle.streaming_snapshot as JO : null

        if (bundle.latest_event_id != null) {
            setCursor(bundle.latest_event_id as EventCursor, 'status', rid)
        } else if (snapshot) {
            const ssCursor = extractCursorFromMessage(snapshot)
            if (ssCursor !== null) setCursor(ssCursor, 'status', rid)
        }

        pendingInputRef.current = bundle.pending_input ?? null
        const planSource = bundle.plan
        const planText = toPlanText(planSource)
        const tokens = normalizeTokenInfo(bundle.token_totals)
        const snapshotArtifact = snapshot && typeof snapshot.artifact_text === 'string' ? snapshot.artifact_text : ''

        const recoveredContext = (bundle.context && typeof bundle.context === 'object' && !Array.isArray(bundle.context))
            ? bundle.context as Partial<ResearchStartPayload>
            : (snapshot?.context && typeof snapshot.context === 'object' && !Array.isArray(snapshot.context))
                ? snapshot.context as Partial<ResearchStartPayload>
                : {}

        

        s(prev => {
            const baseStatus = toSessionStatus(bundle.status, prev.status)
            const hydratedSteps = buildResumeSteps(planSource, bundle.current_step, bundle.total_steps, baseStatus)
            let steps = hydratedSteps.length > 0 ? [...hydratedSteps] : [...prev.steps]
            const currentStepIndex = typeof bundle.current_step === 'number' ? bundle.current_step : null
            const runningLike = ['running', 'starting', 'connected', 'connecting', 'stopping'].includes(baseStatus)

            const ensureAt = (idx: number) => {
                if (!steps[idx]) {
                    let st: LiveStep['status'] = 'pending'
                    if (baseStatus === 'completed') st = 'completed'
                    else if (currentStepIndex !== null) {
                        if (idx < currentStepIndex) st = 'completed'
                        else if (idx === currentStepIndex && runningLike) st = 'running'
                    }
                    steps[idx] = { ...createEmptyStep(idx), status: st }
                }
                return steps[idx]
            }

            // Restore thinking per step
            if (snapshot?.thinking_by_step && typeof snapshot.thinking_by_step === 'object') {
                for (const [rawKey, rawVal] of Object.entries(snapshot.thinking_by_step as JO)) {
                    if (typeof rawVal !== 'string') continue
                    const idx = parseStepIndex(rawKey)
                    if (idx === null) continue
                    const existing = ensureAt(idx)
                    const done = currentStepIndex !== null ? idx < currentStepIndex : false
                    steps[idx] = { ...existing, thinking: finalizeText(existing.thinking, rawVal.trim()), thinkingDone: existing.thinkingDone || done }
                }
            }

            // Restore tool results
            if (Array.isArray(snapshot?.recent_tool_results)) {
                for (const rowVal of snapshot.recent_tool_results as unknown[]) {
                    if (!rowVal || typeof rowVal !== 'object') continue
                    const row = rowVal as JO
                    const idx = parseStepIndex(row.step_index) ?? currentStepIndex ?? 0
                    const existing = ensureAt(idx)
                    const toolName = (typeof row.tool_name === 'string' && row.tool_name.trim()) ? row.tool_name.trim() : 'tool'
                    const eventId = typeof row.event_id === 'string' ? row.event_id.trim() : null
                    const resultSummary = typeof row.result_summary === 'string' ? row.result_summary.trim() : ''
                    const args = row.result_payload ?? undefined
                    const resultText = resultSummary || (row.result_payload != null ? JSON.stringify(row.result_payload, null, 2) : '')
                    const dup = existing.tools.some(t => (eventId && t.id === eventId) || (sameToolSig(t.tool_name, t.args, toolName, args) && t.result === resultText))
                    if (dup) continue
                    const tool: LiveToolCall = { id: eventId ?? genId(), tool_name: toolName, createdAt: Date.now(), args, result: resultText, state: 'done' }
                    steps[idx] = { ...existing, tools: [...existing.tools, tool] }
                }
            }

            const pending = bundle.pending_input ?? null

            const finalStatus = pending?.type === 'qa_question'
                ? 'waiting_for_answer'
                : pending?.type === 'plan_approval'
                    ? 'waiting_for_approval'
                    : baseStatus

            const base: StepState = {
                ...prev,
                researchId: rid,
                status: finalStatus,
                progress: progressFromCounts(bundle.current_step, bundle.total_steps, prev.progress),
                progressMsg: progressLabel(bundle.current_step, bundle.total_steps, prev.progressMsg),
                tokens: (tokens.input_tokens > 0 || tokens.output_tokens > 0) ? tokens : prev.tokens,
                steps,
                plan: planText ? { plan: planText } : prev.plan,
                artifact: snapshotArtifact ? finalizeText(prev.artifact, snapshotArtifact) : prev.artifact,
                artifactDone: snapshotArtifact ? isTerminalStatus(baseStatus) : prev.artifactDone,
                planApproved: pending?.type === 'plan_approval' ? null : prev.planApproved,
                error: null,
                context: { ...prev.context, ...recoveredContext },
            }

            return applyPendingSnapshot(base, pending, planSource)
        })

        persist(rid, { ...urls, last_known_event_id: cursorRef.current, pending_input: pendingInputRef.current })
    }, [setCursor, persist, applyPendingSnapshot])

    // ── Replay missed events ─────────────────────────────────────────────────
    const replayMissed = useCallback(async (rid: string, fromCursor: EventCursor) => {
        if (!fromCursor) return
        let cursor = fromCursor
        for (let pass = 0; pass < 20; pass++) {
            const response = await apiService.replay(rid, cursor, DEFAULT_REPLAY_LIMIT, replayUrlRef.current || undefined)
            for (const ev of response.events) applyMessage(ev as JO)
            const nextCursor = response.next_event_id ?? cursor
            if (nextCursor) { cursor = nextCursor; setCursor(nextCursor, 'timeline', rid) }
            const count = typeof response.replay_count === 'number' ? response.replay_count : response.events.length
            if (count < DEFAULT_REPLAY_LIMIT || !response.next_event_id) break
        }
    }, [apiService, applyMessage, setCursor])

    // ── WebSocket lifecycle ──────────────────────────────────────────────────
    useEffect(() => {
        const manager = new ResearchStreamManager({
            onMessage: (event: MessageEvent<string>) => {
                try { applyMessage(JSON.parse(event.data) as JO) } catch { /* ignore */ }
            },
            onOpen: () => {
                s(prev => {
                    const live = ['starting', 'running', 'waiting_for_answer', 'waiting_for_approval', 'stopping'].includes(prev.status)
                    return { ...prev, status: live ? prev.status : 'connected', error: null }
                })
                flushOutboundQueue()
            },
            onError: () => s(prev => ({ ...prev, status: 'disconnected', error: 'Connection error' })),
            onClose: () => {
                s(prev => {
                    if (manualDisconnectRef.current) return { ...prev, status: 'idle' }
                    if (isTerminalStatus(prev.status)) return prev
                    return { ...prev, status: 'disconnected' }
                })
            },
            shouldReconnect: () => !manualDisconnectRef.current && !isTerminalStatus(stateRef.current.status),
        })
        streamManagerRef.current = manager
        return () => { manualDisconnectRef.current = true; manager.disconnect(true); streamManagerRef.current = null }
    }, [applyMessage, flushOutboundQueue])

    // ── 5-second polling safety-net (spec §14.8) ──────────────────────────
    const POLL_ACTIVE_STATUSES = new Set([
        'connecting', 'starting', 'connected', 'running',
        'waiting_for_answer', 'waiting_for_approval', 'stopping', 'disconnected',
    ])

    useEffect(() => {
        let timer: number | null = null
        let stopped = false

        const poll = async () => {
            if (stopped) return
            const currentState = stateRef.current
            if (!currentState.researchId || !POLL_ACTIVE_STATUSES.has(currentState.status)) return
            try {
                const statusResp = await apiService.status(
                    currentState.researchId,
                    statusUrlRef.current || undefined,
                )
                if (stopped) return

                // Cursor advance from status
                const evId = statusResp.latest_event_id ?? null
                if (evId !== null) setCursor(evId, 'status', currentState.researchId)

                const polledPending = statusResp.pending_input !== undefined
                    ? statusResp.pending_input ?? null
                    : pendingInputRef.current
                pendingInputRef.current = polledPending

                // Persist snapshot
                persist(currentState.researchId, {
                    last_known_event_id: evId ?? cursorRef.current,
                    last_status: statusResp as Record<string, unknown>,
                    pending_input: polledPending,
                })

                s(prev => {
                    const newStatus = toSessionStatus(statusResp.status, prev.status)
                    const tokens = normalizeTokenInfo(statusResp.token_totals)
                    const base: StepState = {
                        ...prev,
                        status: newStatus,
                        progress: progressFromCounts(statusResp.current_step, statusResp.total_steps, prev.progress),
                        progressMsg: progressLabel(statusResp.current_step, statusResp.total_steps, prev.progressMsg),
                        tokens: (tokens.input_tokens > 0 || tokens.output_tokens > 0) ? tokens : prev.tokens,
                    }

                    return applyPendingSnapshot(base, polledPending)
                })

                // session-not-found on 404 comes from isSessionNotFoundError thrown before here
            } catch (err) {
                if (stopped) return
                if (isSessionNotFoundError(err)) {
                    ResearchSessionStore.remove(stateRef.current.researchId)
                    manualDisconnectRef.current = true
                    streamManagerRef.current?.disconnect(true)
                    s(prev => ({ ...prev, status: 'not_found', error: 'This session is no longer available.' }))
                }
                // non-fatal: other errors are ignored for loop continuity (spec §14.8)
            } finally {
                if (!stopped) {
                    timer = window.setTimeout(poll, 5000)
                }
            }
        }

        // Start polling loop
        timer = window.setTimeout(poll, 5000)
        return () => {
            stopped = true
            if (timer !== null) window.clearTimeout(timer)
        }
    // We intentionally omit fast-changing deps; the ref pattern lets us
    // always read the latest values inside the async closure.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [apiService, setCursor, persist, applyPendingSnapshot])



    // ── Public actions ───────────────────────────────────────────────────────
    const startResearch = useCallback(async (payload: ResearchStartPayload) => {
        manualDisconnectRef.current = true
        streamManagerRef.current?.disconnect(true)
        manualDisconnectRef.current = false
        resetRunState('', 'starting')

        const started = await apiService.start(payload as unknown as Record<string, unknown>)
        const rid = started.research_id
        if (!rid) throw new Error('Backend response missing research_id')

        const urls = normalizeRuntimeUrls(rid, started, backendBaseRef.current)
        statusUrlRef.current = urls.status_url
        replayUrlRef.current = urls.replay_url
        resumeUrlRef.current = urls.resume_url
        websocketUrlRef.current = urls.websocket_url

        s(prev => ({ ...prev, researchId: rid, status: toSessionStatus(started.status, 'starting') }))
        persist(rid, { ...urls })
        optionsRef.current?.onNavigateToSession?.(rid, true)
        openSocket(rid, { websocketUrl: urls.websocket_url, lastEventId: cursorRef.current })
    }, [apiService, openSocket, persist, resetRunState])

    const resumeSession = useCallback(async (researchIdInput: string) => {
        const rid = researchIdInput.trim()
        if (!rid) { s(prev => ({ ...prev, status: 'failed', error: 'Invalid research ID' })); return }

        manualDisconnectRef.current = false
        streamManagerRef.current?.disconnect(true)
        resetRunState(rid, 'connecting')

        const localSession = ResearchSessionStore.get(rid)
        if (localSession) {
            const localUrls = normalizeRuntimeUrls(rid, localSession, backendBaseRef.current)
            statusUrlRef.current = localUrls.status_url
            replayUrlRef.current = localUrls.replay_url
            resumeUrlRef.current = localUrls.resume_url
            websocketUrlRef.current = localUrls.websocket_url
            if (localSession.last_known_event_id !== null) setCursor(localSession.last_known_event_id, 'status', rid)
        }

        try {
            const replayFrom = localSession?.last_known_event_id ?? '0-0'
            const bundle = await apiService.resume(rid, {
                resumeUrl: resumeUrlRef.current || localSession?.resume_url,
                includeTimeline: true,
                fromEventId: replayFrom,
                timelineLimit: 1000,
            })
            hydrateBundle(bundle, rid)

            for (const ev of bundle.timeline_events ?? []) applyMessage(ev as JO)

            const tlNextCursor = bundle.timeline_next_event_id
            const latestCursor = bundle.latest_event_id
            if (tlNextCursor != null) setCursor(tlNextCursor, 'timeline', rid)
            else if (latestCursor != null) setCursor(latestCursor, 'status', rid)

            const tlCount = typeof bundle.timeline_replay_count === 'number' ? bundle.timeline_replay_count : (bundle.timeline_events?.length ?? 0)
            if (tlCount >= 1000 && tlNextCursor != null) await replayMissed(rid, tlNextCursor)

            optionsRef.current?.onNavigateToSession?.(rid, true)

            const bundleStatus = toSessionStatus(bundle.status, 'connected')
            if (!isTerminalStatus(bundleStatus)) {
                openSocket(rid, { websocketUrl: websocketUrlRef.current, lastEventId: cursorRef.current, replayLimit: DEFAULT_REPLAY_LIMIT })
            } else {
                manualDisconnectRef.current = true
                streamManagerRef.current?.disconnect(true)
            }
        } catch (err) {
            if (isSessionNotFoundError(err)) {
                ResearchSessionStore.remove(rid)
                s(prev => ({ ...prev, researchId: rid, status: 'not_found', error: 'This session is no longer available.' }))
                return
            }
            s(prev => ({ ...prev, status: 'failed', error: String(err) }))
        }
    }, [apiService, hydrateBundle, applyMessage, replayMissed, openSocket, resetRunState, s, setCursor])

    const stopResearch = useCallback(async () => {
        streamManagerRef.current?.send({ type: 'stop.request' })
        s(prev => ({ ...prev, status: 'stopping' }))
        await apiService.stop(stateRef.current.researchId)
    }, [apiService])

    const submitAnswer = useCallback((answer: string) => {
        const a = answer.trim()
        if (!a) return
        const wasSent = sendOrQueue({ type: 'user.answer', answer: a })
        pendingInputRef.current = null
        s(prev => {
            const remaining = prev.questions.slice(1)
            return { ...prev, questions: remaining, status: remaining.length > 0 ? 'waiting_for_answer' : 'running' }
        })
        if (!wasSent) {
            const rid = stateRef.current.researchId
            if (rid && !manualDisconnectRef.current && !isTerminalStatus(stateRef.current.status)) {
                openSocket(rid, { websocketUrl: websocketUrlRef.current, lastEventId: cursorRef.current, replayLimit: DEFAULT_REPLAY_LIMIT })
            }
        }
    }, [openSocket, sendOrQueue])

    const approvePlan = useCallback(() => {
        const wasSent = sendOrQueue({ type: 'user.approval', action: 'approve' })
        pendingInputRef.current = null
        s(prev => ({ ...prev, status: 'running', planApproved: true }))
        if (!wasSent) {
            const rid = stateRef.current.researchId
            if (rid && !manualDisconnectRef.current && !isTerminalStatus(stateRef.current.status)) {
                openSocket(rid, { websocketUrl: websocketUrlRef.current, lastEventId: cursorRef.current, replayLimit: DEFAULT_REPLAY_LIMIT })
            }
        }
    }, [openSocket, sendOrQueue])

    const refactorPlan = useCallback((feedback: string) => {
        const wasSent = sendOrQueue({ type: 'user.approval', action: 'refactor', feedback })
        pendingInputRef.current = { type: 'plan_approval', plan: stateRef.current.plan?.plan }
        s(prev => ({ ...prev, status: 'waiting_for_approval', planApproved: null }))
        if (!wasSent) {
            const rid = stateRef.current.researchId
            if (rid && !manualDisconnectRef.current && !isTerminalStatus(stateRef.current.status)) {
                openSocket(rid, { websocketUrl: websocketUrlRef.current, lastEventId: cursorRef.current, replayLimit: DEFAULT_REPLAY_LIMIT })
            }
        }
    }, [openSocket, sendOrQueue])

    const disconnect = useCallback(() => {
        manualDisconnectRef.current = true
        outboundQueueRef.current = []
        streamManagerRef.current?.disconnect(true)
        s(prev => ({ ...prev, status: 'idle' }))
    }, [])

    // ── Auto-resume if researchId was provided ───────────────────────────────
    useEffect(() => {
        if (options?.researchId) {
            void resumeSession(options.researchId)
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [options?.researchId, resumeSession])

    const isRunning = state.status === 'running' || state.status === 'starting' || state.status === 'connecting' || state.status === 'stopping'

    return {
        ...state,
        isRunning,
        isPendingQuestion: state.status === 'waiting_for_answer',
        isPendingApproval: state.status === 'waiting_for_approval',
        startResearch,
        resumeSession,
        stopResearch,
        submitAnswer,
        approvePlan,
        refactorPlan,
        disconnect,
    }
}
