import type { EventCursor, TokenInfo, ResumeSessionRecord, PendingInput } from './research_types'

// ─── Config ───────────────────────────────────────────────────────────────────
export const DEFAULT_BACKEND_BASE = 'http://localhost:8000'
export const DEFAULT_REPLAY_LIMIT = 500
const BACKEND_STORAGE_KEY = 'research.backend.base_url.v1'
const SESSION_STORAGE_KEY = 'research.resume.sessions.v1'

// ─── Backend URL helpers ──────────────────────────────────────────────────────
function trimSlashes(v: string) { return v.replace(/\/+$/, '') }
const SCHEME_RE = /^[a-z][a-z\d+.-]*:\/\//i

export function parseBackendBase(value: unknown): string | null {
    if (typeof value !== 'string') return null
    const raw = value.trim()
    if (!raw) return null
    const candidate = SCHEME_RE.test(raw) ? raw : `http://${raw}`
    try {
        const p = new URL(candidate)
        if (!p.hostname) return null
        p.search = ''; p.hash = ''
        return trimSlashes(p.toString())
    } catch { return null }
}

export function readBackendBase(): string {
    try {
        const stored = window.localStorage.getItem(BACKEND_STORAGE_KEY)
        return parseBackendBase(stored) ?? DEFAULT_BACKEND_BASE
    } catch { return DEFAULT_BACKEND_BASE }
}

export function saveBackendBase(value: string): string {
    const parsed = parseBackendBase(value)
    if (!parsed) throw new Error('Invalid server URL')
    try { window.localStorage.setItem(BACKEND_STORAGE_KEY, parsed) } catch { /* ignore */ }
    return parsed
}

// ─── URL normalization ────────────────────────────────────────────────────────
function toCanonicalWs(proto: string): string {
    if (proto === 'https:') return 'wss:'
    if (proto === 'http:') return 'ws:'
    if (proto === 'wss:' || proto === 'ws:') return proto
    return 'ws:'
}

export function toAbsoluteUrl(value: unknown, base = readBackendBase()): string {
    const raw = typeof value === 'string' ? value.trim() : ''
    if (!raw) return ''
    try { return new URL(raw).toString() } catch { /* continue */ }
    try { return new URL(raw, base).toString() } catch { return '' }
}

export function canonicalRuntimeUrls(researchId: string, base = readBackendBase()) {
    const b = new URL(base)
    const rid = encodeURIComponent(researchId)
    const wsBase = new URL(b.toString())
    wsBase.protocol = toCanonicalWs(b.protocol)
    return {
        status_url: new URL(`/research/${rid}/status`, b).toString(),
        replay_url: new URL(`/research/${rid}/events/replay`, b).toString(),
        resume_url: new URL(`/research/${rid}/resume`, b).toString(),
        websocket_url: new URL(`/research/ws/${rid}`, wsBase).toString(),
    }
}

function normalizeWsUrl(value: unknown, rid: string, base = readBackendBase()): string {
    const candidate = toAbsoluteUrl(value, base)
    if (!candidate) return canonicalRuntimeUrls(rid, base).websocket_url
    try {
        const p = new URL(candidate)
        if (p.protocol === 'ws:' || p.protocol === 'wss:') return p.toString()
        if (p.protocol === 'http:' || p.protocol === 'https:') {
            p.protocol = toCanonicalWs(p.protocol)
            return p.toString()
        }
    } catch { /* fall through */ }
    return canonicalRuntimeUrls(rid, base).websocket_url
}

export function normalizeRuntimeUrls(
    researchId: string,
    input: { status_url?: unknown; replay_url?: unknown; resume_url?: unknown; websocket_url?: unknown },
    base = readBackendBase(),
) {
    const c = canonicalRuntimeUrls(researchId, base)
    return {
        status_url: toAbsoluteUrl(input.status_url, base) || c.status_url,
        replay_url: toAbsoluteUrl(input.replay_url, base) || c.replay_url,
        resume_url: toAbsoluteUrl(input.resume_url, base) || c.resume_url,
        websocket_url: normalizeWsUrl(input.websocket_url, researchId, base),
    }
}

// ─── Cursor comparison ────────────────────────────────────────────────────────
function parseCursor(cursor: EventCursor): [bigint, bigint] | null {
    if (typeof cursor === 'number' && Number.isFinite(cursor)) return [BigInt(Math.trunc(cursor)), 0n]
    if (typeof cursor !== 'string') return null
    const raw = cursor.trim()
    if (!raw) return null
    if (/^\d+$/.test(raw)) return [BigInt(raw), 0n]
    const m = raw.match(/^(\d+)-(\d+)$/)
    if (m) return [BigInt(m[1]), BigInt(m[2])]
    return null
}

export function compareCursor(a: EventCursor, b: EventCursor): number | null {
    const pa = parseCursor(a), pb = parseCursor(b)
    if (!pa || !pb) return null
    if (pa[0] > pb[0]) return 1
    if (pa[0] < pb[0]) return -1
    if (pa[1] > pb[1]) return 1
    if (pa[1] < pb[1]) return -1
    return 0
}

export function isCursorLike(value: unknown): boolean {
    if (typeof value === 'number' && Number.isFinite(value)) return true
    if (typeof value !== 'string') return false
    const raw = value.trim()
    return /^\d+$/.test(raw) || /^\d+-\d+$/.test(raw)
}

// ─── Streaming chunk dedup (boundary-aware) ───────────────────────────────────
export function appendStreamChunk(current: string, incoming: string): string {
    if (!incoming) return current
    if (!current) return incoming
    if (incoming.startsWith(current)) return incoming       // backend sent full snapshot
    if (current.startsWith(incoming)) return current       // reconnect replay
    const maxOverlap = Math.min(64, current.length, incoming.length)
    for (let overlap = maxOverlap; overlap > 0; overlap--) {
        if (current.slice(-overlap) === incoming.slice(0, overlap)) {
            return current + incoming.slice(overlap)
        }
    }
    return current + incoming
}

export function finalizeText(current: string, final: string): string {
    if (!final) return current
    if (!current) return final
    if (final.length >= current.length && (final.startsWith(current) || final.includes(current))) return final
    return appendStreamChunk(current, final)
}

// ─── Token normalization ──────────────────────────────────────────────────────
type JO = Record<string, unknown>

export function normalizeTokenInfo(tokens?: unknown): TokenInfo {
    const r: JO = (tokens && typeof tokens === 'object' ? tokens : {}) as JO
    const n = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null)
    const byDir = (r.by_direction && typeof r.by_direction === 'object' ? r.by_direction : {}) as JO
    const byStep = (r.by_step_direction && typeof r.by_step_direction === 'object' ? r.by_step_direction : {}) as JO
    const sumStep = (key: 'input' | 'output') => {
        let total = 0, found = false
        for (const v of Object.values(byStep)) {
            if (!v || typeof v !== 'object') continue
            const num = n((v as JO)[key])
            if (num != null) { total += num; found = true }
        }
        return found ? total : null
    }
    const i = n(r.input_tokens) ?? n(r.inputTokens) ?? n(byDir.input) ?? n(byDir.in) ?? sumStep('input') ?? 0
    const o = n(r.output_tokens) ?? n(r.outputTokens) ?? n(byDir.output) ?? n(byDir.out) ?? sumStep('output') ?? 0
    const t = n(r.total_tokens) ?? n(r.totalTokens) ?? n(r.grand_total) ?? n(r.total) ?? i + o
    return { input_tokens: i, output_tokens: o, total_tokens: t }
}

// ─── Event dedup tracker ──────────────────────────────────────────────────────
const VOLATILE_KEYS = new Set([
    'event_id', 'eventId', 'latest_event_id', 'latestEventId',
    'next_event_id', 'nextEventId', 'timeline_next_event_id', 'ts', 'timestamp',
])

const SEMANTIC_DEDUP_EVENTS = new Set([
    'input.qa_question', 'input.plan_ready', 'input.approved',
    'plan.step_started', 'plan.step_completed', 'plan.step_failed',
    'plan.all_done', 'stop.requested', 'stop.flushing', 'stop.saved',
])

function stableStringify(v: unknown): string {
    if (v === null || typeof v !== 'object') return JSON.stringify(v)
    if (Array.isArray(v)) return `[${v.map(stableStringify).join(',')}]`
    const keys = Object.keys(v as JO).sort()
    return `{${keys.map(k => `${JSON.stringify(k)}:${stableStringify((v as JO)[k])}`).join(',')}}`
}

function stripVolatile(v: unknown): unknown {
    if (v === null || typeof v !== 'object') return v
    if (Array.isArray(v)) return v.map(stripVolatile)
    const out: JO = {}
    for (const k of Object.keys(v as JO)) {
        if (!VOLATILE_KEYS.has(k)) out[k] = stripVolatile((v as JO)[k])
    }
    return out
}

const TOOL_ALIASES: Record<string, string> = {
    'tool.call': 'tool.called', 'tool.started': 'tool.called', 'tool.invoke': 'tool.called',
    'tool.completed': 'tool.result', 'tool.done': 'tool.result', 'tool.success': 'tool.result',
    'tool.failed': 'tool.error',
}

function normalizeEventName(name: string): string {
    return TOOL_ALIASES[name.trim().toLowerCase()] ?? name.trim().toLowerCase()
}

function shouldSemantic(event: string): boolean {
    return SEMANTIC_DEDUP_EVENTS.has(event) || event.startsWith('tool.')
}

export interface TimelineTracker {
    seenEventIds: Set<string>
    seenFingerprints: Set<string>
    seenSemanticFingerprints: Set<string>
    eventIdQueue: string[]
    fingerprintQueue: string[]
    semanticQueue: string[]
}

export function createTimelineTracker(): TimelineTracker {
    return {
        seenEventIds: new Set(),
        seenFingerprints: new Set(),
        seenSemanticFingerprints: new Set(),
        eventIdQueue: [],
        fingerprintQueue: [],
        semanticQueue: [],
    }
}

export function resetTimelineTracker(t: TimelineTracker) {
    t.seenEventIds.clear(); t.seenFingerprints.clear(); t.seenSemanticFingerprints.clear()
    t.eventIdQueue = []; t.fingerprintQueue = []; t.semanticQueue = []
}

function evictQueue(set: Set<string>, queue: string[], max: number) {
    while (queue.length > max) {
        const old = queue.shift()!
        set.delete(old)
    }
}

export interface ParsedEvent {
    event: string
    ts: string
    data: JO
    eventId: string | null
    fingerprint: string
    semanticFingerprint: string | null
}

export function parseEventEnvelope(input: unknown): ParsedEvent | null {
    if (!input || typeof input !== 'object' || Array.isArray(input)) return null
    const data = input as JO
    const payload = (data.payload && typeof data.payload === 'object' && !Array.isArray(data.payload))
        ? data.payload as JO : null

    const event =
        typeof data.event === 'string' ? data.event
        : typeof data.event_type === 'string' ? data.event_type
        : typeof data.type === 'string' && (data.type as string).includes('.') ? data.type as string
        : payload && typeof payload.event === 'string' ? payload.event
        : null

    if (!event) return null
    const normalizedEvent = normalizeEventName(event)
    const ts = typeof data.ts === 'string' ? data.ts : new Date().toISOString()
    const eventId = extractEventId(data, normalizedEvent)
    const fingerprint = `${ts}|${normalizedEvent}|${stableStringify(data)}`
    const semanticFingerprint = shouldSemantic(normalizedEvent)
        ? `${normalizedEvent}|${stableStringify(stripVolatile(data))}`
        : null

    return { event: normalizedEvent, ts, data, eventId, fingerprint, semanticFingerprint }
}

function extractEventId(data: JO, eventName: string): string | null {
    const payload = (data.payload && typeof data.payload === 'object' && !Array.isArray(data.payload))
        ? data.payload as JO : null
    const candidates = [
        data.id, data.stream_id, data.event_id, data.eventId,
        data.latest_event_id, data.next_event_id,
        payload?.id, payload?.event_id, payload?.latest_event_id,
    ]
    for (const c of candidates) {
        if (isCursorLike(c)) return String(c).trim()
    }
    if (eventName.startsWith('tool.')) {
        const idCandidates = [
            data.tool_id, data.tool_call_id, data.call_id,
            payload?.tool_id, payload?.tool_call_id,
        ]
        for (const c of idCandidates) {
            if (typeof c === 'string' && c.trim()) return `tool:${eventName}:${c.trim()}`
        }
    }
    return null
}

export function shouldApplyEvent(tracker: TimelineTracker, evt: ParsedEvent): boolean {
    if (evt.eventId && tracker.seenEventIds.has(evt.eventId)) return false
    if (evt.semanticFingerprint && tracker.seenSemanticFingerprints.has(evt.semanticFingerprint)) return false
    if (!evt.eventId && tracker.seenFingerprints.has(evt.fingerprint)) return false
    return true
}

export function markEventApplied(tracker: TimelineTracker, evt: ParsedEvent) {
    if (evt.eventId) {
        tracker.seenEventIds.add(evt.eventId)
        tracker.eventIdQueue.push(evt.eventId)
        evictQueue(tracker.seenEventIds, tracker.eventIdQueue, 8000)
    }
    tracker.seenFingerprints.add(evt.fingerprint)
    tracker.fingerprintQueue.push(evt.fingerprint)
    evictQueue(tracker.seenFingerprints, tracker.fingerprintQueue, 4000)
    if (evt.semanticFingerprint) {
        tracker.seenSemanticFingerprints.add(evt.semanticFingerprint)
        tracker.semanticQueue.push(evt.semanticFingerprint)
        evictQueue(tracker.seenSemanticFingerprints, tracker.semanticQueue, 6000)
    }
}

// ─── Extract cursor from any event message ────────────────────────────────────
export function extractCursorFromMessage(data: JO): EventCursor {
    const payload = (data.payload && typeof data.payload === 'object' && !Array.isArray(data.payload))
        ? data.payload as JO : null
    const candidates = [
        data.id, data.stream_id, data.event_id, data.eventId,
        data.latest_event_id, data.next_event_id, data.timeline_next_event_id,
        payload?.id, payload?.event_id, payload?.latest_event_id, payload?.next_event_id,
    ]
    for (const c of candidates) {
        if (isCursorLike(c)) return c as EventCursor
    }
    return null
}

// ─── Event field accessor (checks top-level and payload) ─────────────────────
export function eventField(msg: JO, key: string): unknown {
    if (msg[key] !== undefined) return msg[key]
    const p = msg.payload && typeof msg.payload === 'object' && !Array.isArray(msg.payload)
        ? msg.payload as JO : null
    return p?.[key]
}

export function eventString(msg: JO, ...keys: string[]): string | null {
    for (const k of keys) {
        const v = eventField(msg, k)
        if (typeof v === 'string') { const t = v.trim(); if (t) return t }
    }
    return null
}

export function eventNumber(msg: JO, ...keys: string[]): number | null {
    for (const k of keys) {
        const v = eventField(msg, k)
        if (typeof v === 'number' && !Number.isNaN(v)) return v
    }
    return null
}

export function eventBoolean(msg: JO, ...keys: string[]): boolean | null {
    for (const k of keys) {
        const v = eventField(msg, k)
        if (typeof v === 'boolean') return v
    }
    return null
}

// ─── Plan text normalizer ─────────────────────────────────────────────────────
export function toPlanText(plan: unknown): string {
    if (typeof plan === 'string') return plan
    if (Array.isArray(plan)) {
        return plan.map((item, i) => {
            if (item && typeof item === 'object') {
                const row = item as JO
                const title = typeof row.step_title === 'string' ? row.step_title
                    : typeof row.step_name === 'string' ? row.step_name : `Step ${i + 1}`
                const desc = typeof row.step_description === 'string' ? ` — ${row.step_description}` : ''
                return `${i + 1}. ${title}${desc}`
            }
            return `${i + 1}. ${String(item)}`
        }).join('\n')
    }
    if (plan && typeof plan === 'object') return JSON.stringify(plan, null, 2)
    return ''
}

// ─── Terminal status check ────────────────────────────────────────────────────
export function isTerminalStatus(status: string | undefined): boolean {
    return status === 'completed' || status === 'stopped' || status === 'failed' || status === 'not_found'
}

// ─── Session Store (localStorage) ────────────────────────────────────────────
type SessionMap = Record<string, ResumeSessionRecord>

function readSessionMap(): SessionMap {
    try {
        const raw = window.localStorage.getItem(SESSION_STORAGE_KEY)
        if (!raw) return {}
        const parsed = JSON.parse(raw)
        return (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) ? parsed as SessionMap : {}
    } catch { return {} }
}

function writeSessionMap(map: SessionMap) {
    try { window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(map)) } catch { /* ignore */ }
}

export const ResearchSessionStore = {
    list(): ResumeSessionRecord[] {
        const map = readSessionMap()
        return Object.values(map).sort((a, b) => b.updated_at - a.updated_at)
    },
    get(id: string): ResumeSessionRecord | null {
        return readSessionMap()[id] ?? null
    },
    upsert(input: {
        research_id: string
        status_url?: string; replay_url?: string; resume_url?: string; websocket_url?: string
        last_known_event_id?: EventCursor
        last_status?: Record<string, unknown> | null
        pending_input?: PendingInput | null
    }): ResumeSessionRecord {
        const map = readSessionMap()
        const prev = map[input.research_id]
        const urls = normalizeRuntimeUrls(input.research_id, {
            status_url: input.status_url ?? prev?.status_url,
            replay_url: input.replay_url ?? prev?.replay_url,
            resume_url: input.resume_url ?? prev?.resume_url,
            websocket_url: input.websocket_url ?? prev?.websocket_url,
        })
        const next: ResumeSessionRecord = {
            research_id: input.research_id,
            ...urls,
            last_known_event_id: input.last_known_event_id ?? prev?.last_known_event_id ?? null,
            last_status: input.last_status ?? prev?.last_status ?? null,
            pending_input: input.pending_input ?? prev?.pending_input ?? null,
            updated_at: Date.now(),
        }
        map[input.research_id] = next
        writeSessionMap(map)
        return next
    },
    remove(id: string) {
        const map = readSessionMap()
        if (!(id in map)) return
        delete map[id]
        writeSessionMap(map)
    },
}
