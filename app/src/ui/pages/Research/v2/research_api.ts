import {
    readBackendBase, parseBackendBase, normalizeRuntimeUrls, toAbsoluteUrl, DEFAULT_REPLAY_LIMIT,
} from './research_utils'
import type { EventCursor, StartResponse, ResumeBundle, ReplayResponse, StatusResponse } from './research_types'

// ─── Stream Manager ───────────────────────────────────────────────────────────
type StreamCallbacks = {
    onMessage: (event: MessageEvent<string>) => void
    onOpen?: () => void
    onError?: () => void
    onClose?: () => void
    onReconnectAttempt?: (attempt: number, delayMs: number) => void
    shouldReconnect?: () => boolean
}

export class ResearchStreamManager {
    private ws: WebSocket | null = null
    private reconnectTimer: number | null = null
    private reconnectAttempt = 0
    private manualClose = false
    private current: { researchId: string; websocketUrl: string; lastEventId: EventCursor; replayLimit: number } | null = null
    private callbacks: StreamCallbacks

    constructor(callbacks: StreamCallbacks) {
        this.callbacks = callbacks
    }

    connect(input: { researchId: string; websocketUrl: string; lastEventId: EventCursor; replayLimit?: number }) {
        this.current = { ...input, replayLimit: input.replayLimit ?? DEFAULT_REPLAY_LIMIT }
        this.manualClose = false
        this.clearTimer()
        this.openSocket()
    }

    updateCursor(cursor: EventCursor) {
        if (this.current) this.current = { ...this.current, lastEventId: cursor }
    }

    updateWebsocketUrl(url: string) {
        if (this.current) this.current = { ...this.current, websocketUrl: url }
    }

    send(payload: unknown) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(typeof payload === 'string' ? payload : JSON.stringify(payload))
        }
    }

    disconnect(manual = true) {
        this.manualClose = manual
        this.clearTimer()
        if (this.ws) {
            const ws = this.ws; this.ws = null; ws.close()
        }
    }

    isOpen() { return this.ws?.readyState === WebSocket.OPEN }

    private openSocket() {
        if (!this.current) return
        if (this.ws) { const ws = this.ws; this.ws = null; ws.close() }

        let wsUrl = ''
        try { wsUrl = this.buildUrl(this.current) } catch {
            this.callbacks.onError?.()
            if (!this.manualClose && (!this.callbacks.shouldReconnect || this.callbacks.shouldReconnect())) {
                this.queueReconnect()
            }
            return
        }

        const ws = new WebSocket(wsUrl)
        ws.onopen = () => {
            this.reconnectAttempt = 0
            this.clearTimer()
            this.callbacks.onOpen?.()
        }
        ws.onmessage = this.callbacks.onMessage
        ws.onerror = () => this.callbacks.onError?.()
        ws.onclose = () => {
            this.ws = null
            this.callbacks.onClose?.()
            if (this.manualClose) return
            if (this.callbacks.shouldReconnect && !this.callbacks.shouldReconnect()) return
            this.queueReconnect()
        }
        this.ws = ws
    }

    private buildUrl(input: typeof this.current): string {
        const url = new URL(input!.websocketUrl)
        if (input!.lastEventId !== null && input!.lastEventId !== undefined && String(input!.lastEventId).length > 0) {
            url.searchParams.set('last_event_id', String(input!.lastEventId))
        }
        url.searchParams.set('replay_limit', String(input!.replayLimit))
        return url.toString()
    }

    private queueReconnect() {
        const delay = Math.round(Math.min(8000, 500 * 2 ** this.reconnectAttempt) * (1 + Math.random() * 0.2))
        this.reconnectAttempt++
        this.callbacks.onReconnectAttempt?.(this.reconnectAttempt, delay)
        this.reconnectTimer = window.setTimeout(() => this.openSocket(), delay)
    }

    private clearTimer() {
        if (this.reconnectTimer !== null) { window.clearTimeout(this.reconnectTimer); this.reconnectTimer = null }
    }
}

// ─── API Service ──────────────────────────────────────────────────────────────
class ApiError extends Error {
    status: number; payload: unknown
    constructor(message: string, status: number, payload: unknown) {
        super(message); this.name = 'ApiError'; this.status = status; this.payload = payload
    }
}

export function isSessionNotFoundError(err: unknown): boolean {
    if (err instanceof ApiError) {
        if (err.status === 404) return true
        const payload = err.payload
        if (payload && typeof payload === 'object') {
            const detail = (payload as Record<string, unknown>).detail
            if (typeof detail === 'string') {
                const low = detail.toLowerCase()
                return low.includes('session not found') || low.includes('stale')
            }
        }
        return false
    }
    if (err instanceof Error) {
        const low = err.message.toLowerCase()
        return low.includes('session not found') || low.includes('stale')
    }
    return false
}

async function doFetch<T>(url: string, init?: RequestInit): Promise<T> {
    const res = await fetch(url, init)
    const payload = await res.json().catch(() => null)
    if (!res.ok) throw new ApiError(`Request failed (${res.status})`, res.status, payload)
    return payload as T
}

async function withRetry<T>(fn: () => Promise<T>, maxAttempts: number, baseDelay = 300): Promise<T> {
    let attempt = 0, delay = baseDelay
    while (attempt < maxAttempts) {
        try { return await fn() } catch (err) {
            attempt++
            if (attempt >= maxAttempts) throw err
            const shouldRetry = err instanceof ApiError ? err.status >= 500 : err instanceof TypeError
            if (!shouldRetry) throw err
            await new Promise<void>(r => window.setTimeout(r, delay))
            delay = Math.min(2500, delay * 2)
        }
    }
    throw new Error('Unreachable')
}

export class ResearchApiService {
    private backendBase: string

    constructor(backendBase?: string) {
        this.backendBase = parseBackendBase(backendBase) ?? readBackendBase()
    }

    setBase(base: string) {
        this.backendBase = parseBackendBase(base) ?? readBackendBase()
    }

    async start(payload: Record<string, unknown>): Promise<StartResponse> {
        const base = this.backendBase
        const data = await doFetch<Record<string, unknown>>(new URL('/research/start', base).toString(), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        })
        const researchId = String(data.research_id ?? data.id ?? '')
        const urls = normalizeRuntimeUrls(researchId, data, base)
        return { ...data, research_id: researchId, ...urls } as StartResponse
    }

    async resume(researchId: string, options?: {
        resumeUrl?: string
        includeTimeline?: boolean
        fromEventId?: EventCursor
        timelineLimit?: number
    }): Promise<ResumeBundle> {
        const base = this.backendBase
        const urls = normalizeRuntimeUrls(researchId, { resume_url: options?.resumeUrl }, base)
        const buildUrl = (resumeUrl: string) => {
            const u = new URL(resumeUrl)
            u.searchParams.set('includeTimeline', String(options?.includeTimeline ?? true))
            u.searchParams.set('fromEventId', String(options?.fromEventId ?? '0-0'))
            u.searchParams.set('timelineLimit', String(options?.timelineLimit ?? 1000))
            return u.toString()
        }
        const primaryUrl = buildUrl(urls.resume_url)
        let data: Record<string, unknown>
        try {
            data = await withRetry(() => doFetch<Record<string, unknown>>(primaryUrl), 3)
        } catch (err) {
            const fallbackUrls = normalizeRuntimeUrls(researchId, {}, base)
            const fallbackUrl = buildUrl(fallbackUrls.resume_url)
            if (fallbackUrl === primaryUrl) throw err
            data = await withRetry(() => doFetch<Record<string, unknown>>(fallbackUrl), 2)
        }
        const resolvedUrls = normalizeRuntimeUrls(researchId, data, base)
        const timelineEvents = Array.isArray(data.timeline_events)
            ? data.timeline_events.filter((e): e is Record<string, unknown> => !!e && typeof e === 'object')
            : []
        return {
            ...data,
            research_id: String(data.research_id ?? researchId),
            ...resolvedUrls,
            timeline_events: timelineEvents,
            timeline_replay_count: typeof data.timeline_replay_count === 'number' ? data.timeline_replay_count : timelineEvents.length,
            timeline_next_event_id: (typeof data.timeline_next_event_id === 'string' || typeof data.timeline_next_event_id === 'number')
                ? data.timeline_next_event_id as EventCursor : null,
        } as ResumeBundle
    }

    async status(researchId: string, statusUrl?: string): Promise<StatusResponse> {
        const base = this.backendBase
        const url = toAbsoluteUrl(statusUrl, base) || normalizeRuntimeUrls(researchId, {}, base).status_url
        const data = await doFetch<Record<string, unknown>>(url)
        return {
            ...data,
            research_id: typeof data.research_id === 'string' ? data.research_id : researchId,
            status: typeof data.status === 'string' ? data.status : undefined,
            current_step: typeof data.current_step === 'number' ? data.current_step : undefined,
            total_steps: typeof data.total_steps === 'number' ? data.total_steps : undefined,
            latest_event_id: (typeof data.latest_event_id === 'string' || typeof data.latest_event_id === 'number')
                ? data.latest_event_id as EventCursor : null,
            pending_input: (data.pending_input ?? null) as StatusResponse['pending_input'],
        }
    }

    async replay(researchId: string, fromEventId: EventCursor, limit = DEFAULT_REPLAY_LIMIT, replayUrl?: string): Promise<ReplayResponse> {
        const base = this.backendBase
        const baseUrl = toAbsoluteUrl(replayUrl, base) || normalizeRuntimeUrls(researchId, {}, base).replay_url
        const u = new URL(baseUrl)
        if (fromEventId !== null && fromEventId !== undefined && String(fromEventId).length > 0) {
            u.searchParams.set('fromEventId', String(fromEventId))
        }
        u.searchParams.set('limit', String(limit))
        const data = await doFetch<Record<string, unknown>>(u.toString())
        const events = Array.isArray(data.events)
            ? data.events.filter((e): e is Record<string, unknown> => !!e && typeof e === 'object')
            : []
        return {
            ...data,
            events,
            replay_count: typeof data.replay_count === 'number' ? data.replay_count : events.length,
            next_event_id: (typeof data.next_event_id === 'string' || typeof data.next_event_id === 'number')
                ? data.next_event_id as EventCursor : null,
        }
    }

    async stop(researchId: string): Promise<void> {
        const base = this.backendBase
        const url = new URL(`/research/${encodeURIComponent(researchId)}/stop`, base).toString()
        await fetch(url, { method: 'POST' })
    }
}
