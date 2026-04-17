import React, { useMemo } from 'react'
import { RefreshCw, AlertCircle } from 'lucide-react'
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from '@/components/ui/popover'
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from '@/components/ui/tooltip'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { useStatus } from '@/contexts/StatusContext'
import { ConnectionStatus } from '@/lib/services/status-service'
import { cn } from '@/lib/utils'

interface ServiceCategory {
    name: string
    services: {
        key: keyof ConnectionStatus
        label: string
    }[]
}

const SERVICE_CATEGORIES: ServiceCategory[] = [
    {
        name: 'Infrastructure',
        services: [
            { key: 'docker.redis', label: 'Docker: Redis' },
            { key: 'docker.searxng', label: 'Docker: SearXNG' },
        ],
    },
    {
        name: 'Backend',
        services: [
            { key: 'backend.server', label: 'Backend Server' },
            { key: 'backend.bg_workers', label: 'BG Workers' },
        ],
    },
    {
        name: 'AI Models',
        services: [
            { key: 'ai.ollama', label: 'AI: Ollama' },
            { key: 'ai.gemini', label: 'AI: Gemini' },
            { key: 'ai.groq', label: 'AI: Groq' },
        ],
    },
    {
        name: 'Storage',
        services: [
            { key: 'db.vector', label: 'Database (Vector)' },
            { key: 'db.sqlite', label: 'Database (SQLite)' },
        ],
    },
    {
        name: 'External',
        services: [
            { key: 'internet', label: 'Internet' },
            { key: 'mcp.server', label: 'MCP Server' },
            { key: 'mcp.client', label: 'MCP Client' },
        ],
    },
]

function getIndicatorColor(
    isLoading: boolean,
    isConnected: boolean,
    status: ConnectionStatus | null
): string {
    if (isLoading) return 'bg-gray-400'
    if (!isConnected) return 'bg-red-500'

    if (!status) return 'bg-gray-400'

    // If backend is down, it's critical
    if (status['backend.server'] === false) return 'bg-red-500'

    // Check if all are green
    const allGreen = Object.values(status).every((v) => v === true)
    if (allGreen) return 'bg-green-500'

    // Some are down
    return 'bg-yellow-500'
}

function getStatusLabel(
    isLoading: boolean,
    isConnected: boolean,
    status: ConnectionStatus | null
): string {
    if (isLoading) return 'Connecting'
    if (!isConnected) return 'Disconnected'

    if (!status) return 'Connecting'

    // If backend is down, it's critical
    if (status['backend.server'] === false) return 'Disconnected'

    // Check if all are green
    const allGreen = Object.values(status).every((v) => v === true)
    if (allGreen) return 'Connected'

    // Some are down
    return 'Connected: Limited'
}

function getStatusDot(isOn: boolean | null): React.ReactNode {
    if (isOn === null) return <div className="w-1.5 h-1.5 rounded-full bg-gray-400" />
    return (
        <div
            className={cn('w-1.5 h-1.5 rounded-full', isOn ? 'bg-green-500' : 'bg-red-500')}
        />
    )
}

const StatusPopover: React.FC = () => {
    const { state, retry } = useStatus()
    const { status, isConnected, isLoading, error, lastUpdated } = state

    const indicatorColor = useMemo(
        () => getIndicatorColor(isLoading, isConnected, status),
        [isLoading, isConnected, status]
    )

    const statusLabel = useMemo(
        () => getStatusLabel(isLoading, isConnected, status),
        [isLoading, isConnected, status]
    )

    const tooltipText = useMemo(() => {
        if (isLoading) return 'Connecting...'
        if (!isConnected) return 'Disconnected'
        if (status?.['backend.server'] === false) return 'Backend Error'
        if (Object.values(status || {}).every((v) => v === true))
            return 'All Connected'
        return 'Limited Connection'
    }, [isLoading, isConnected, status])

    return (
        <TooltipProvider disableHoverableContent>
            <Popover>
                <Tooltip delayDuration={700}>
                    <TooltipTrigger asChild>
                        <PopoverTrigger asChild>
                            <button
                                className="h-10 px-3 hover:bg-muted transition-colors flex items-center justify-center gap-2 group rounded-md"
                                aria-label="Connection status"
                            >
                                <div
                                    className={cn(
                                        'w-2.5 h-2.5 rounded-full transition-colors shrink-0',
                                        indicatorColor
                                    )}
                                />
                                <span className="text-xs text-muted-foreground font-medium">
                                    {statusLabel}
                                </span>
                            </button>
                        </PopoverTrigger>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" showArrow={false}>
                        <p>{tooltipText}</p>
                    </TooltipContent>
                </Tooltip>

                <PopoverContent className="w-80" side="bottom" align="start">
                    <div className="space-y-4">
                        {/* Header */}
                        <div className="flex items-center justify-between">
                            <h3 className="text-sm font-semibold">Connection Status</h3>
                            <span className="text-xs text-muted-foreground">
                                {lastUpdated
                                    ? `Updated ${new Date(lastUpdated).toLocaleTimeString()}`
                                    : 'Initializing...'}
                            </span>
                        </div>

                        {/* Error or Loading State */}
                        {isLoading && (
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                <div className="w-4 h-4 rounded-full border-2 border-muted-foreground border-t-foreground animate-spin" />
                                Connecting...
                            </div>
                        )}

                        {error && !isLoading && (
                            <div className="flex items-center gap-2 p-2 bg-destructive/10 text-destructive rounded-md text-sm">
                                <AlertCircle className="w-4 h-4 shrink-0" />
                                <span>{error}</span>
                            </div>
                        )}

                        {/* Status Categories */}
                        {status && isConnected && (
                            <div className="space-y-3">
                                {SERVICE_CATEGORIES.map((category, idx) => (
                                    <div key={category.name}>
                                        <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-tight">
                                            {category.name}
                                        </p>
                                        <div className="space-y-1.5">
                                            {category.services.map((service) => (
                                                <div
                                                    key={service.key}
                                                    className="flex items-center justify-between text-sm"
                                                >
                                                    <div className="flex items-center gap-2">
                                                        {getStatusDot(status[service.key])}
                                                        <span className="text-foreground">
                                                            {service.label}
                                                        </span>
                                                    </div>
                                                    <span
                                                        className={cn(
                                                            'text-xs',
                                                            status[service.key]
                                                                ? 'text-green-600 dark:text-green-400'
                                                                : 'text-red-600 dark:text-red-400'
                                                        )}
                                                    >
                                                        {status[service.key] ? 'OK' : 'Down'}
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                        {idx < SERVICE_CATEGORIES.length - 1 && (
                                            <Separator className="mt-3 bg-border/40" />
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Retry Button */}
                        {(error || !isConnected) && !isLoading && (
                            <Button
                                size="sm"
                                variant="outline"
                                className="w-full gap-2 text-xs"
                                onClick={() => void retry()}
                            >
                                <RefreshCw className="w-3 h-3" />
                                Retry Connection
                            </Button>
                        )}
                    </div>
                </PopoverContent>
            </Popover>
        </TooltipProvider>
    )
}

export default StatusPopover
