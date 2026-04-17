import { getRuntimeBackendBaseUrl } from '@/lib/backend-config'

export type ConnectionStatusKey =
    | 'internet'
    | 'backend.server'
    | 'backend.bg_workers'
    | 'mcp.server'
    | 'mcp.client'
    | 'db.vector'
    | 'db.sqlite'
    | 'ai.ollama'
    | 'ai.gemini'
    | 'ai.groq'
    | 'docker.redis'
    | 'docker.searxng'

export interface ConnectionStatus {
    internet: boolean
    'backend.server': boolean
    'backend.bg_workers': boolean
    'mcp.server': boolean
    'mcp.client': boolean
    'db.vector': boolean
    'db.sqlite': boolean
    'ai.ollama': boolean
    'ai.gemini': boolean
    'ai.groq': boolean
    'docker.redis': boolean
    'docker.searxng': boolean
}

export type StatusUpdateCallback = (status: Partial<ConnectionStatus>) => void

export class StatusService {
    private eventSource: EventSource | null = null
    private isConnected = false
    private lastError: string | null = null

    connectToStatusStream(onConnectionOpen: () => void, onStatusReceived: (status: ConnectionStatus) => void, onUpdate: StatusUpdateCallback): () => void {
        try {
            // Convert HTTP to WebSocket URL for SSE
            const baseUrl = getRuntimeBackendBaseUrl()
            const streamUrl = baseUrl.replace(/^http:/, 'http:').replace(/^https:/, 'https:') + '/events/frontend_monitor'

            console.log('[StatusService] Connecting to SSE stream:', streamUrl)

            this.eventSource = new EventSource(streamUrl)

            this.eventSource.onopen = () => {
                console.log('[StatusService] SSE connection opened')
                this.isConnected = true
                this.lastError = null
                onConnectionOpen()
            }

            this.eventSource.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data)
                    console.log('[StatusService] Received message:', message)

                    // Extract the actual data from the wrapper
                    if (message.success === 'true' && message.data) {
                        const statusData = message.data as ConnectionStatus
                        
                        // Check if it's a full status (has internet property)
                        if (statusData.internet !== undefined) {
                            onStatusReceived(statusData)
                        } else {
                            // Otherwise treat as partial update
                            onUpdate(statusData as Partial<ConnectionStatus>)
                        }
                    }
                } catch (e) {
                    console.error('[StatusService] Failed to parse SSE message:', e)
                }
            }

            this.eventSource.onerror = (error) => {
                console.error('[StatusService] SSE connection error:', error)
                this.isConnected = false
                this.lastError = 'SSE connection lost'
                this.eventSource?.close()
                this.eventSource = null
            }

            // Return unsubscribe function
            return () => {
                this.disconnect()
            }
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error'
            this.lastError = `Failed to connect to stream: ${errorMessage}`
            console.error('[StatusService] Connection error:', errorMessage)
            return () => { }
        }
    }

    disconnect(): void {
        if (this.eventSource) {
            this.eventSource.close()
            this.eventSource = null
            this.isConnected = false
            console.log('[StatusService] Disconnected')
        }
    }

    getIsConnected(): boolean {
        return this.isConnected
    }

    getLastError(): string | null {
        return this.lastError
    }

    clearError(): void {
        this.lastError = null
    }
}
