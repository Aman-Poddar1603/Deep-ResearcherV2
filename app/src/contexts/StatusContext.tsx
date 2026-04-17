import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { ConnectionManager, ConnectionState } from '@/lib/services/connection-manager'

interface StatusContextType {
    state: ConnectionState
    retry: () => Promise<void>
}

const StatusContext = createContext<StatusContextType | undefined>(undefined)

export function StatusProvider({ children }: { children: ReactNode }) {
    const [state, setState] = useState<ConnectionState>({
        status: null,
        isConnected: false,
        isLoading: false,
        error: null,
        lastUpdated: null,
    })

    const connectionManager = ConnectionManager.getInstance()

    useEffect(() => {
        const unsubscribe = connectionManager.subscribe((newState) => {
            setState(newState)
        })

        return () => {
            unsubscribe()
        }
    }, [])

    const retry = async () => {
        await connectionManager.retry()
    }

    return (
        <StatusContext.Provider value={{ state, retry }}>
            {children}
        </StatusContext.Provider>
    )
}

export function useStatus(): StatusContextType {
    const context = useContext(StatusContext)
    if (context === undefined) {
        throw new Error('useStatus must be used within a StatusProvider')
    }
    return context
}
