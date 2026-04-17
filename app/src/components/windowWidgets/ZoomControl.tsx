import React, { useState, useEffect } from 'react'
import { ZoomIn, ZoomOut, RotateCcw } from 'lucide-react'
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
import { cn } from '@/lib/utils'

const ZoomControl: React.FC = () => {
    const [zoomLevel, setZoomLevel] = useState(0)

    // Initialize zoom level
    useEffect(() => {
        window.electron.getZoomLevel().then((level: number) => {
            setZoomLevel(level)
        })
    }, [])

    // Subscribe to zoom changes
    useEffect(() => {
        const unsubscribe = window.electron.subscribeZoomLevel((level: number) => {
            setZoomLevel(level)
        })
        return () => unsubscribe()
    }, [])

    // Handle keyboard shortcuts
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // Ctrl/Cmd + +
            if ((e.ctrlKey || e.metaKey) && e.key === '+') {
                e.preventDefault()
                window.electron.zoomIn()
            }
            // Ctrl/Cmd + -
            if ((e.ctrlKey || e.metaKey) && e.key === '-') {
                e.preventDefault()
                window.electron.zoomOut()
            }
            // Ctrl/Cmd + 0
            if ((e.ctrlKey || e.metaKey) && e.key === '0') {
                e.preventDefault()
                window.electron.resetZoom()
            }
        }

        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [])

    const zoomPercentage = Math.round((zoomLevel + 1) * 100)
    const isDefault = zoomLevel === 0

    return (
        <TooltipProvider disableHoverableContent>
            <Popover>
                <Tooltip delayDuration={700}>
                    <TooltipTrigger asChild>
                        <PopoverTrigger asChild>
                            <button
                                className="h-10 px-3 hover:bg-muted transition-colors flex items-center justify-center gap-2 group rounded-md"
                                aria-label="Zoom control"
                            >
                                <span className="text-xs text-muted-foreground font-medium">
                                    {zoomPercentage}%
                                </span>
                            </button>
                        </PopoverTrigger>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" showArrow={false}>
                        <p>Zoom (Ctrl +/-)</p>
                    </TooltipContent>
                </Tooltip>

                <PopoverContent className="w-48" side="bottom" align="start">
                    <div className="space-y-4">
                        {/* Header */}
                        <div className="flex items-center justify-between">
                            <h3 className="text-sm font-semibold">Zoom</h3>
                            <span className="text-xs text-muted-foreground">
                                {zoomPercentage}%
                            </span>
                        </div>

                        {/* Controls */}
                        <div className="flex gap-2">
                            <Button
                                size="sm"
                                variant="outline"
                                className="flex-1"
                                onClick={() => window.electron.zoomOut()}
                            >
                                <ZoomOut className="w-4 h-4" />
                            </Button>
                            <Button
                                size="sm"
                                variant="outline"
                                className="flex-1"
                                onClick={() => window.electron.zoomIn()}
                            >
                                <ZoomIn className="w-4 h-4" />
                            </Button>
                        </div>

                        {/* Reset Button */}
                        <Button
                            size="sm"
                            variant="outline"
                            className={cn(
                                'w-full gap-2',
                                isDefault ? 'opacity-50 cursor-not-allowed' : ''
                            )}
                            onClick={() => window.electron.resetZoom()}
                            disabled={isDefault}
                        >
                            <RotateCcw className="w-3 h-3" />
                            Reset to Default
                        </Button>
                    </div>
                </PopoverContent>
            </Popover>
        </TooltipProvider>
    )
}

export default ZoomControl
