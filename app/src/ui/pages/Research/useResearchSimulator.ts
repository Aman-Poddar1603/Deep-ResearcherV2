import { useState, useRef, useCallback, useEffect } from 'react'
import {
    SIMULATED_RESEARCH_STEPS,
    type ResearchStep,
    type ResearchStats,
} from './research_response'

export interface UseResearchSimulatorReturn {
    steps: ResearchStep[]
    stats: ResearchStats
    isRunning: boolean
    elapsedSeconds: number
    stopResearch: () => void
    startResearch: () => void
}

export function useResearchSimulator(): UseResearchSimulatorReturn {
    const [steps, setSteps] = useState<ResearchStep[]>([])
    const [isRunning, setIsRunning] = useState(false)
    const [elapsedSeconds, setElapsedSeconds] = useState(0)
    const [stats, setStats] = useState<ResearchStats>({
        tokensUsed: 0,
        filesReferenced: 0,
        websitesVisited: 0,
        docsRead: 0,
        contextTokens: 0,
    })

    const stopRef = useRef(false)
    const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

    // Elapsed time counter
    useEffect(() => {
        if (isRunning) {
            timerRef.current = setInterval(() => {
                setElapsedSeconds((prev) => prev + 1)
            }, 1000)
        } else if (timerRef.current) {
            clearInterval(timerRef.current)
            timerRef.current = null
        }

        return () => {
            if (timerRef.current) {
                clearInterval(timerRef.current)
            }
        }
    }, [isRunning])

    const startResearch = useCallback(async () => {
        stopRef.current = false
        setIsRunning(true)
        setSteps([])
        setElapsedSeconds(0)
        setStats({
            tokensUsed: 0,
            filesReferenced: 0,
            websitesVisited: 0,
            docsRead: 0,
            contextTokens: 0,
        })

        for (let i = 0; i < SIMULATED_RESEARCH_STEPS.length; i++) {
            if (stopRef.current) break

            const step = SIMULATED_RESEARCH_STEPS[i]

            // Wait for the step's delay
            await new Promise((resolve) => setTimeout(resolve, step.delay))

            if (stopRef.current) break

            // Add step to the list
            setSteps((prev) => [...prev, step])

            // Update stats if the step has statsUpdate
            if ('statsUpdate' in step && step.statsUpdate) {
                const update = step.statsUpdate
                setStats((prev) => ({
                    tokensUsed: update.tokensUsed ?? prev.tokensUsed,
                    filesReferenced: update.filesReferenced ?? prev.filesReferenced,
                    websitesVisited: update.websitesVisited ?? prev.websitesVisited,
                    docsRead: update.docsRead ?? prev.docsRead,
                    contextTokens: update.contextTokens ?? prev.contextTokens,
                }))
            }

            // For content steps, simulate streaming by adding characters progressively
            if (step.type === 'content' && step.content.length > 100) {
                const fullContent = step.content
                const chunkSize = Math.max(20, Math.floor(fullContent.length / 15))

                for (let c = chunkSize; c < fullContent.length; c += chunkSize) {
                    if (stopRef.current) break
                    await new Promise((resolve) => setTimeout(resolve, 80))

                    setSteps((prev) => {
                        const updated = [...prev]
                        const lastIdx = updated.length - 1
                        if (updated[lastIdx]?.type === 'content') {
                            updated[lastIdx] = {
                                ...updated[lastIdx],
                                content: fullContent.slice(0, c),
                                isStreaming: true,
                            } as ResearchStep
                        }
                        return updated
                    })
                }

                // Final full content
                if (!stopRef.current) {
                    setSteps((prev) => {
                        const updated = [...prev]
                        const lastIdx = updated.length - 1
                        if (updated[lastIdx]?.type === 'content') {
                            updated[lastIdx] = {
                                ...updated[lastIdx],
                                content: fullContent,
                                isStreaming: false,
                            } as ResearchStep
                        }
                        return updated
                    })
                }
            }

            // For confirmation steps, wait for auto-approve delay
            if (step.type === 'confirmation') {
                await new Promise((resolve) => setTimeout(resolve, step.autoApproveDelay))
            }
        }

        if (!stopRef.current) {
            setIsRunning(false)
        }
    }, [])

    const stopResearch = useCallback(() => {
        stopRef.current = true
        setIsRunning(false)
    }, [])

    return {
        steps,
        stats,
        isRunning,
        elapsedSeconds,
        stopResearch,
        startResearch,
    }
}
