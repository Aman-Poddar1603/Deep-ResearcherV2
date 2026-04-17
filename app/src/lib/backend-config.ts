export const BACKEND_PORT = 8000
export const DEFAULT_BACKEND_HOST = 'localhost'
export const BACKEND_HOST_STORAGE_KEY = 'dr_backend.host.v1'
export const LEGACY_BACKEND_BASE_STORAGE_KEY = 'research.backend.base_url.v1'

const SCHEME_RE = /^[a-z][a-z\d+.-]*:\/\//i
const IPV4_RE = /^(25[0-5]|2[0-4]\d|1?\d?\d)(\.(25[0-5]|2[0-4]\d|1?\d?\d)){3}$/
const HOSTNAME_RE = /^(?=.{1,253}$)(?!-)(?:[a-z\d](?:[a-z\d-]{0,61}[a-z\d])?\.)*[a-z\d](?:[a-z\d-]{0,61}[a-z\d])$/i

const ENV_BACKEND_URL = (import.meta.env.VITE_BACKEND_URL as string | undefined) ?? null

function safeGetLocalStorage(key: string): string | null {
    try {
        return window.localStorage.getItem(key)
    } catch {
        return null
    }
}

function safeSetLocalStorage(key: string, value: string): void {
    try {
        window.localStorage.setItem(key, value)
    } catch {
        // ignore write failures
    }
}

function safeRemoveLocalStorage(key: string): void {
    try {
        window.localStorage.removeItem(key)
    } catch {
        // ignore write failures
    }
}

function isHostLike(value: string): boolean {
    if (value === DEFAULT_BACKEND_HOST) return true
    if (IPV4_RE.test(value)) return true
    return HOSTNAME_RE.test(value)
}

function extractHost(rawValue: string): string | null {
    const raw = rawValue.trim()
    if (!raw) return null

    if (SCHEME_RE.test(raw)) {
        try {
            return new URL(raw).hostname.toLowerCase()
        } catch {
            return null
        }
    }

    try {
        return new URL(`http://${raw}`).hostname.toLowerCase()
    } catch {
        const withoutPath = raw.split(/[/?#]/, 1)[0]?.trim() ?? ''
        if (!withoutPath) return null
        const withoutPort = withoutPath.replace(/:\d+$/, '')
        return withoutPort.replace(/^\[/, '').replace(/\]$/, '').toLowerCase()
    }
}

export function normalizeBackendHost(value: unknown): string | null {
    if (typeof value !== 'string') return null
    const host = extractHost(value)
    if (!host) return null
    return isHostLike(host) ? host : null
}

export function buildBackendBaseUrl(hostOrValue?: string): string {
    const normalizedHost = normalizeBackendHost(hostOrValue ?? readBackendHost()) ?? DEFAULT_BACKEND_HOST
    return `http://${normalizedHost}:${BACKEND_PORT}`
}

export function getRuntimeBackendBaseUrl(): string {
    return buildBackendBaseUrl(readBackendHost())
}

export function getRuntimeBackendWsBaseUrl(): string {
    return getRuntimeBackendBaseUrl().replace(/^http:\/\//i, 'ws://').replace(/^https:\/\//i, 'wss://')
}

export function readBackendHost(): string {
    const storedHost = normalizeBackendHost(safeGetLocalStorage(BACKEND_HOST_STORAGE_KEY))
    if (storedHost) return storedHost

    const legacyHost = normalizeBackendHost(safeGetLocalStorage(LEGACY_BACKEND_BASE_STORAGE_KEY))
    if (legacyHost) {
        safeSetLocalStorage(BACKEND_HOST_STORAGE_KEY, legacyHost)
        return legacyHost
    }

    const envHost = normalizeBackendHost(ENV_BACKEND_URL)
    return envHost ?? DEFAULT_BACKEND_HOST
}

export function saveBackendHost(value: string): string {
    const normalizedHost = normalizeBackendHost(value)
    if (!normalizedHost) throw new Error('Invalid backend host')
    safeSetLocalStorage(BACKEND_HOST_STORAGE_KEY, normalizedHost)
    // Keep the legacy key in sync for existing Research v2 consumers.
    safeSetLocalStorage(LEGACY_BACKEND_BASE_STORAGE_KEY, buildBackendBaseUrl(normalizedHost))
    return normalizedHost
}

export function clearBackendHost(): void {
    safeRemoveLocalStorage(BACKEND_HOST_STORAGE_KEY)
    safeRemoveLocalStorage(LEGACY_BACKEND_BASE_STORAGE_KEY)
}
