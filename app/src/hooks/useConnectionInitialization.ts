import { useEffect } from 'react'
import { ConnectionManager } from '@/lib/services/connection-manager'

export function useConnectionInitialization() {
    useEffect(() => {
        const connectionManager = ConnectionManager.getInstance()

        // Only initialize if not already initialized
        if (!connectionManager.getIsInitialized()) {
            connectionManager.initialize().catch((error) => {
                console.error('[useConnectionInitialization] Error during initialization:', error)
            })
        }

        // Cleanup on unmount
        return () => {
            // Don't disconnect on unmount, keep connection alive
        }
    }, [])
}
