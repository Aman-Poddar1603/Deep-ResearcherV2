import { StatusService, ConnectionStatus } from './status-service'

export interface ConnectionState {
    status: ConnectionStatus | null
    isConnected: boolean
    isLoading: boolean
    error: string | null
    lastUpdated: Date | null
}

type StateUpdateCallback = (state: ConnectionState) => void

class ConnectionManager {
    private static instance: ConnectionManager | null = null
    private statusService: StatusService
    private state: ConnectionState
    private stateCallbacks: Set<StateUpdateCallback> = new Set()
    private isInitialized = false
    private unsubscribe: (() => void) | null = null

    private constructor() {
        this.statusService = new StatusService()
        this.state = {
            status: null,
            isConnected: false,
            isLoading: false,
            error: null,
            lastUpdated: null,
        }
    }

    static getInstance(): ConnectionManager {
        if (!ConnectionManager.instance) {
            ConnectionManager.instance = new ConnectionManager()
        }
        return ConnectionManager.instance
    }

    async initialize(): Promise<void> {
        if (this.isInitialized) {
            console.log('[ConnectionManager] Already initialized')
            return
        }

        this.isInitialized = true
        this.updateState({ isLoading: true })

        try {
            console.log('[ConnectionManager] Connecting to status stream...')

            // Connect to SSE stream - it will send initial status and then updates
            this.unsubscribe = this.statusService.connectToStatusStream(
                () => {
                    // Called when connection opens
                    console.log('[ConnectionManager] Connection opened')
                    this.updateState({
                        isConnected: true,
                        isLoading: false,
                    })
                },
                (status) => {
                    // Called when a complete status is received
                    console.log('[ConnectionManager] Initial status received')
                    this.updateState({
                        status,
                        error: null,
                        lastUpdated: new Date(),
                    })
                },
                (update) => {
                    // Called for status updates
                    this.handleStatusUpdate(update)
                }
            )
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Unknown error'
            console.error('[ConnectionManager] Initialization error:', errorMessage)
            this.updateState({
                isConnected: false,
                error: errorMessage,
                isLoading: false,
            })
        }
    }

    async retry(): Promise<void> {
        console.log('[ConnectionManager] Manual retry triggered')
        // Disconnect old SSE connection
        if (this.unsubscribe) {
            this.unsubscribe()
            this.unsubscribe = null
        }
        this.statusService.disconnect()
        this.statusService.clearError()

        // Reset state and reconnect
        this.isInitialized = false
        this.updateState({
            isLoading: true,
            error: null,
        })

        try {
            // Reconnect to SSE stream
            this.unsubscribe = this.statusService.connectToStatusStream(
                () => {
                    // Called when connection opens
                    console.log('[ConnectionManager] Retry - connection opened')
                    this.updateState({
                        isConnected: true,
                        isLoading: false,
                    })
                },
                (status) => {
                    console.log('[ConnectionManager] Retry - status received')
                    this.updateState({
                        status,
                        error: null,
                        lastUpdated: new Date(),
                    })
                },
                (update) => {
                    this.handleStatusUpdate(update)
                }
            )
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Unknown error'
            console.error('[ConnectionManager] Retry error:', errorMessage)
            this.updateState({
                isConnected: false,
                error: errorMessage,
                isLoading: false,
            })
        }
    }

    getIsInitialized(): boolean {
        return this.isInitialized
    }

    getState(): ConnectionState {
        return { ...this.state }
    }

    subscribe(callback: StateUpdateCallback): () => void {
        this.stateCallbacks.add(callback)
        // Immediately call with current state
        callback(this.state)

        // Return unsubscribe function
        return () => {
            this.stateCallbacks.delete(callback)
        }
    }

    disconnect(): void {
        if (this.unsubscribe) {
            this.unsubscribe()
            this.unsubscribe = null
        }
        this.statusService.disconnect()
    }

    private handleStatusUpdate(update: Partial<ConnectionStatus>): void {
        if (!this.state.status) return
        const newStatus: ConnectionStatus = {
            ...this.state.status,
            ...update,
        }
        this.updateState({
            status: newStatus,
            lastUpdated: new Date(),
        })
    }

    private updateState(partial: Partial<ConnectionState>): void {
        this.state = { ...this.state, ...partial }
        this.stateCallbacks.forEach((callback) => {
            callback(this.state)
        })
    }
}

export { ConnectionManager }
