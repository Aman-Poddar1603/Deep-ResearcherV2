import { useState, useRef, useCallback, useEffect } from 'react'
import {
    SIMULATED_RESEARCH_STEPS,
    type ResearchStep,
    type ResearchStats,
    type PlanStep,
} from './research_response'

export interface UseResearchSimulatorReturn {
    steps: ResearchStep[]
    stats: ResearchStats
    isRunning: boolean
    elapsedSeconds: number
    /** True when waiting for user to approve a confirmation step */
    isPendingConfirmation: boolean
    /** The current confirmation step, if any */
    pendingConfirmationStep: ResearchStep | null
    /** Call to approve the current confirmation step */
    approveConfirmation: (value: string) => void
    /** Call to reject the current confirmation step */
    rejectConfirmation: (reason?: string) => void
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
    const [isPendingConfirmation, setIsPendingConfirmation] = useState(false)
    const [pendingConfirmationStep, setPendingConfirmationStep] = useState<ResearchStep | null>(null)

    const stopRef = useRef(false)
    const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
    const confirmResolverRef = useRef<((v: { approved: boolean; value?: string; reason?: string }) => void) | null>(null)

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

    const approveConfirmation = useCallback((value: string) => {
        if (confirmResolverRef.current) {
            confirmResolverRef.current({ approved: true, value })
            confirmResolverRef.current = null
        }
        setIsPendingConfirmation(false)
        setPendingConfirmationStep(null)
    }, [])

    const rejectConfirmation = useCallback((reason?: string) => {
        if (confirmResolverRef.current) {
            confirmResolverRef.current({ approved: false, reason })
            confirmResolverRef.current = null
        }
        setIsPendingConfirmation(false)
        setPendingConfirmationStep(null)
    }, [])

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

            // ── Handle plan-update by mutating the existing plan step ────────────
            if (step.type === 'plan-update') {
                setSteps((prev) => {
                    const updated = [...prev]
                    // Find the plan step index
                    const planIdx = updated.findIndex((s) => s.type === 'plan')
                    if (planIdx === -1) return updated

                    const planStep = updated[planIdx] as PlanStep
                    const updatedTasks = planStep.tasks.map((task, idx) => {
                        if (step.completeIndices.includes(idx)) {
                            return { ...task, status: 'complete' as const }
                        }
                        if (idx === step.activeIndex) {
                            return { ...task, status: 'active' as const }
                        }
                        // Reset previously active to pending if not completed
                        if (task.status === 'active' && !step.completeIndices.includes(idx)) {
                            return { ...task, status: 'pending' as const }
                        }
                        return task
                    })

                    updated[planIdx] = { ...planStep, tasks: updatedTasks }
                    return updated
                })
                continue
            }

            // ── Handle confirmation with manual approval ────────────────────────
            if (step.type === 'confirmation') {
                // Add the step so it renders
                setSteps((prev) => [...prev, step])
                setIsPendingConfirmation(true)
                setPendingConfirmationStep(step)

                // Pause execution until user approves or rejects
                const result = await new Promise<{ approved: boolean; value?: string; reason?: string }>((resolve) => {
                    confirmResolverRef.current = resolve
                })

                if (!result.approved || stopRef.current) {
                    // If rejected, stop the simulation
                    if (!result.approved) {
                        stopRef.current = true
                        setIsRunning(false)
                    }
                    break
                }
                // Continue after approval
                continue
            }

            // ── Normal step — add to list ───────────────────────────────────────
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

            // ── Content streaming simulation ────────────────────────────────────
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
        }

        if (!stopRef.current) {
            setIsRunning(false)
        }
    }, [])

    const stopResearch = useCallback(() => {
        stopRef.current = true
        setIsRunning(false)
        // Also resolve any pending confirmation
        if (confirmResolverRef.current) {
            confirmResolverRef.current({ approved: false, reason: 'stopped' })
            confirmResolverRef.current = null
        }
        setIsPendingConfirmation(false)
        setPendingConfirmationStep(null)
    }, [])

    return {
        steps,
        stats,
        isRunning,
        elapsedSeconds,
        isPendingConfirmation,
        pendingConfirmationStep,
        approveConfirmation,
        rejectConfirmation,
        stopResearch,
        startResearch,
    }
}
