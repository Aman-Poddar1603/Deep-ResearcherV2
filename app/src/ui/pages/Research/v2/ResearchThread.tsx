import { useEffect, memo, useCallback, useState, useRef, useMemo } from 'react'
import type { ReactNode } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { Message, MessageContent, MessageResponse } from '@/components/ai-elements/message'
import {
    Conversation,
    ConversationContent,
    ConversationScrollButton,
} from '@/components/ai-elements/conversation'
import { Reasoning, ReasoningTrigger, ReasoningContent } from '@/components/ai-elements/reasoning'
import {
    Plan, PlanHeader, PlanTitle, PlanDescription, PlanAction, PlanContent, PlanTrigger,
} from '@/components/ai-elements/plan'
import {
    Tool, ToolHeader, ToolContent, ToolInput, ToolOutput,
} from '@/components/ai-elements/tool'
import { Sources, SourcesTrigger, SourcesContent, Source } from '@/components/ai-elements/sources'
import { Task, TaskTrigger, TaskContent, TaskItem } from '@/components/ai-elements/task'
import {
    Confirmation, ConfirmationTitle, ConfirmationRequest,
    ConfirmationActions, ConfirmationAction,
} from '@/components/ai-elements/confirmation'
import {
    Artifact, ArtifactHeader, ArtifactTitle, ArtifactDescription,
    ArtifactActions, ArtifactContent,
} from '@/components/ai-elements/artifact'

import { Shimmer } from '@/components/ai-elements/shimmer'
import { Persona } from '@/components/ai-elements/persona'
import {
    Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription,
} from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import {
    Square, FileText, Clock, Zap, Hash, Database,
    CopyIcon, CheckIcon, ChevronLeft, Sparkles, Youtube, Link as LinkIcon,
    CheckCircle2, Circle, Loader2, Download, ExternalLink,
    ChevronDown, MessageSquare, FileJson, FileType, FileOutput, Share2,
    SendHorizonal, AlertCircle, RotateCcw, Wifi, WifiOff, Briefcase,
} from 'lucide-react'
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem,
    DropdownMenuTrigger, DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu"
import { toast } from "sonner"
import { DEFAULT_SYSTEM_PROMPT } from '../research_response'
import { useResearchSession } from './useResearchSession'
import type { LiveStep, LiveToolCall, QAQuestion } from './research_types'

// ─── Template resolver ────────────────────────────────────────────────────────
function resolveResearchTemplate(key: string): string {
    const templates: Record<string, string> = {
        comprehensive: '# Research Report\n\n## Executive Summary\n\n## Key Findings\n\n## In-Depth Analysis\n\n## Conclusion\n\n## Sources',
        quick: '# Quick Summary\n\n## Key Points\n\n## Sources',
        analytical: '# Analysis Report\n\n## Overview\n\n## Data Analysis\n\n## Insights\n\n## References',
        comparative: '# Comparative Study\n\n## Introduction\n\n## Comparison\n\n## Findings\n\n## Conclusion',
    }
    return templates[key] ?? templates.comprehensive
}

// ─── Reasoning renderer ───────────────────────────────────────────────────────
const ThinkingRenderer = memo(({ step, isLast, isRunning }: { step: LiveStep; isLast: boolean; isRunning: boolean }) => {
    if (!step.thinking && !(isLast && isRunning)) return null
    return (
        <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
            <Reasoning isStreaming={!step.thinkingDone && isLast && isRunning} defaultOpen={isLast && isRunning}>
                <ReasoningTrigger />
                <ReasoningContent>{step.thinking || '…'}</ReasoningContent>
            </Reasoning>
        </div>
    )
})
ThinkingRenderer.displayName = 'ThinkingRenderer'

// ─── Plan renderer (from live steps) ─────────────────────────────────────────
const PlanRenderer = memo(({ plan, steps, isRunning }: {
    plan: string
    steps: LiveStep[]
    isRunning: boolean
}) => {
    const activeIdx = steps.findIndex(s => s.status === 'running')
    const tasks = plan.split('\n').filter(Boolean).map((line, i) => {
        const stepStatus = steps[i]?.status
        const status = stepStatus === 'completed' ? 'complete' as const
            : stepStatus === 'running' ? 'active' as const
            : 'pending' as const
        return { label: line.replace(/^\d+\.\s*/, ''), status }
    })
    return (
        <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
            <Plan isStreaming={activeIdx !== -1 && isRunning} defaultOpen>
                <PlanHeader>
                    <div>
                        <PlanTitle>Research Plan</PlanTitle>
                        <PlanDescription>Step-by-step research execution</PlanDescription>
                    </div>
                    <PlanAction><PlanTrigger /></PlanAction>
                </PlanHeader>
                <PlanContent>
                    <div className="space-y-2 pb-4">
                        {tasks.map((task, i) => (
                            <div key={i} className="flex items-center gap-3 px-1">
                                {task.status === 'complete' ? (
                                    <CheckCircle2 className="size-4 text-green-500 shrink-0" />
                                ) : task.status === 'active' ? (
                                    <Loader2 className="size-4 text-primary animate-spin shrink-0" />
                                ) : (
                                    <Circle className="size-4 text-muted-foreground/40 shrink-0" />
                                )}
                                <span className={cn(
                                    "text-sm transition-all duration-300",
                                    task.status === 'complete' && "text-muted-foreground line-through",
                                    task.status === 'active' && "text-foreground font-medium",
                                    task.status === 'pending' && "text-muted-foreground"
                                )}>{task.label}</span>
                            </div>
                        ))}
                    </div>
                </PlanContent>
            </Plan>
        </div>
    )
})
PlanRenderer.displayName = 'PlanRenderer'

// ─── Tool call renderer ───────────────────────────────────────────────────────
const ToolRenderer = memo(({ tool }: { tool: LiveToolCall }) => {
    const stateMap = { called: 'input-available', running: 'input-available', done: 'output-available', error: 'output-error' } as const
    return (
        <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
            <Tool>
                <ToolHeader
                    title={tool.tool_name}
                    type="dynamic-tool"
                    state={stateMap[tool.state]}
                    toolName={tool.tool_name}
                />
                <ToolContent>
                    {tool.args != null && typeof tool.args === 'object' && !Array.isArray(tool.args) && <ToolInput input={tool.args as Record<string, unknown>} />}
                    {(tool.result || tool.error) && (
                        <ToolOutput
                            output={tool.result ? { result: tool.result } : {}}
                            errorText={tool.state === 'error' ? (tool.error ?? 'Tool execution failed') : undefined}
                        />
                    )}
                </ToolContent>
            </Tool>
        </div>
    )
})
ToolRenderer.displayName = 'ToolRenderer'

// ─── Step renderer (thinking + tools) ────────────────────────────────────────
const StepRenderer = memo(({ step, isLast, isRunning }: { step: LiveStep; isLast: boolean; isRunning: boolean }) => (
    <div className="space-y-3">
        {/* Step header badge */}
        <div className="flex items-center gap-2">
            <div className={cn(
                "flex items-center gap-2 text-xs font-mono px-3 py-1 rounded-full border",
                step.status === 'running' && "bg-primary/10 border-primary/30 text-primary",
                step.status === 'completed' && "bg-green-500/10 border-green-500/30 text-green-500",
                step.status === 'failed' && "bg-red-500/10 border-red-500/30 text-red-500",
                step.status === 'pending' && "bg-muted border-border text-muted-foreground",
            )}>
                {step.status === 'running' && <Loader2 className="size-3 animate-spin" />}
                {step.status === 'completed' && <CheckCircle2 className="size-3" />}
                {step.status === 'failed' && <AlertCircle className="size-3" />}
                {step.status === 'pending' && <Circle className="size-3" />}
                Step {step.index + 1}: {step.title}
            </div>
        </div>

        {/* Thinking / reasoning */}
        <ThinkingRenderer step={step} isLast={isLast} isRunning={isRunning} />

        {/* Tool calls */}
        {step.tools.map(tool => <ToolRenderer key={tool.id} tool={tool} />)}

        {/* Step summary */}
        {step.summary && step.status === 'completed' && (
            <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                <Message from="assistant" className="max-w-full">
                    <MessageContent className="bg-transparent px-0 py-0 w-full">
                        <MessageResponse>{step.summary}</MessageResponse>
                    </MessageContent>
                </Message>
            </div>
        )}
    </div>
))
StepRenderer.displayName = 'StepRenderer'

/** Context from navigation state so the user still sees their brief while answering QA. */
interface QAResearchContext {
    title: string
    description: string
    prompt: string
    workspaceName: string
    customInstructions?: string
}

// ─── QA Question renderer (full-width card; keeps research prompt visible) ───
const QARenderer = memo(({
    question,
    context,
    onSubmit,
}: {
    question: QAQuestion
    context: QAResearchContext
    onSubmit: (answer: string) => void
}) => {
    const [answer, setAnswer] = useState('')
    const textareaRef = useRef<HTMLTextAreaElement>(null)

    useEffect(() => {
        textareaRef.current?.focus()
    }, [])

    const handleSubmit = () => {
        if (!answer.trim()) return
        onSubmit(answer.trim())
        setAnswer('')
    }

    const hasPrompt = Boolean(context.prompt?.trim())
    const hasDescription = Boolean(context.description?.trim())
    const hasCustom = Boolean(context.customInstructions?.trim())

    return (
        <div className="animate-in fade-in slide-in-from-bottom-2 duration-300 w-full max-w-4xl mx-auto px-1">
            <Card className="overflow-hidden border-amber-500/35 bg-linear-to-b from-amber-500/[0.07] via-background to-background shadow-lg shadow-amber-500/5">
                <CardHeader className="space-y-1 pb-2 border-b border-border/50 bg-muted/20">
                    <div className="flex items-center gap-2">
                        <div className="size-9 rounded-xl bg-amber-500/15 flex items-center justify-center border border-amber-500/25">
                            <MessageSquare className="size-4 text-amber-500" />
                        </div>
                        <div>
                            <CardTitle className="text-lg font-semibold tracking-tight">
                                Research assistant needs clarification
                            </CardTitle>
                            <CardDescription>
                                Question {question.index + 1} — your original brief stays below for reference
                            </CardDescription>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="space-y-5 pt-5">
                    {/* Locked context from UI / session */}
                    <div className="rounded-xl border border-border/60 bg-muted/25 p-4 space-y-3">
                        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                            <FileText className="size-3.5 opacity-80" />
                            Your research context
                        </p>
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                            <span className="inline-flex items-center gap-1.5 font-medium text-foreground">
                                <Briefcase className="size-3.5 shrink-0 opacity-70" />
                                {context.workspaceName}
                            </span>
                            {context.title ? (
                                <span className="text-foreground/90 font-medium">{context.title}</span>
                            ) : null}
                        </div>
                        {hasDescription ? (
                            <p className="text-sm text-muted-foreground leading-relaxed border-l-2 border-primary/30 pl-3">
                                {context.description}
                            </p>
                        ) : null}
                        <div className="space-y-1.5">
                            <p className="text-xs font-medium text-muted-foreground">Original prompt</p>
                            {hasPrompt ? (
                                <div className="max-h-[min(28vh,220px)] overflow-y-auto rounded-lg border border-border/70 bg-background/90 px-3 py-2.5 text-sm leading-relaxed text-foreground whitespace-pre-wrap shadow-inner">
                                    {context.prompt}
                                </div>
                            ) : (
                                <p className="text-xs text-muted-foreground italic rounded-lg border border-dashed border-border/60 px-3 py-2">
                                    Original prompt is not in this browser session (e.g. after refresh). Use the title and workspace above for context.
                                </p>
                            )}
                        </div>
                        {hasCustom ? (
                            <details className="text-xs group">
                                <summary className="cursor-pointer text-muted-foreground hover:text-foreground font-medium">
                                    Custom instructions
                                </summary>
                                <pre className="mt-2 max-h-32 overflow-y-auto rounded-md bg-background/80 border border-border/50 p-2 whitespace-pre-wrap font-sans text-muted-foreground">
                                    {context.customInstructions}
                                </pre>
                            </details>
                        ) : null}
                    </div>

                    {/* Current question — primary focus */}
                    <div className="space-y-2">
                        <p className="text-xs font-semibold uppercase tracking-wide text-amber-600 dark:text-amber-400">
                            Question for you
                        </p>
                        <p className="text-base sm:text-lg text-foreground leading-relaxed font-medium">
                            {question.question}
                        </p>
                    </div>

                    {/* Answer composer */}
                    <div className="space-y-2">
                        <label htmlFor={`qa-answer-${question.index}`} className="text-sm font-medium text-foreground">
                            Your answer
                        </label>
                        <Textarea
                            id={`qa-answer-${question.index}`}
                            ref={textareaRef}
                            value={answer}
                            onChange={e => setAnswer(e.target.value)}
                            onKeyDown={e => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault()
                                    handleSubmit()
                                }
                            }}
                            placeholder="Write a clear answer… (Shift+Enter for a new line)"
                            rows={6}
                            className="min-h-[140px] resize-y text-base leading-relaxed bg-background border-border/80 focus-visible:ring-amber-500/30"
                        />
                        <div className="flex flex-col-reverse sm:flex-row sm:items-center sm:justify-between gap-3 pt-1">
                            <p className="text-xs text-muted-foreground">
                                <kbd className="px-1 py-0.5 rounded bg-muted border border-border text-[10px] font-mono">Enter</kbd>
                                {' '}to submit ·{' '}
                                <kbd className="px-1 py-0.5 rounded bg-muted border border-border text-[10px] font-mono">Shift</kbd>
                                +
                                <kbd className="px-1 py-0.5 rounded bg-muted border border-border text-[10px] font-mono">Enter</kbd>
                                {' '}for newline
                            </p>
                            <Button
                                type="button"
                                size="lg"
                                className="w-full sm:w-auto gap-2 shrink-0 h-11 px-6"
                                onClick={handleSubmit}
                                disabled={!answer.trim()}
                            >
                                <SendHorizonal className="size-4" />
                                Submit answer
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
})
QARenderer.displayName = 'QARenderer'

// ─── Plan approval renderer ───────────────────────────────────────────────────
const PlanApprovalRenderer = memo(({ plan, onApprove, onRefactor }: {
    plan: string
    onApprove: () => void
    onRefactor: (feedback: string) => void
}) => {
    const [showRefactor, setShowRefactor] = useState(false)
    const [feedback, setFeedback] = useState('')

    return (
        <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
            <Confirmation
                approval={{ id: 'plan_approval' }}
                state="approval-requested"
            >
                <ConfirmationTitle>
                    <div className="flex items-center gap-2 mb-2">
                        <div className="size-6 rounded-full bg-primary/20 flex items-center justify-center">
                            <Sparkles className="size-3.5 text-primary" />
                        </div>
                        <span className="font-medium">Plan Approval Required</span>
                    </div>
                    <ConfirmationRequest>
                        <div className="mt-2 space-y-1.5">
                            {plan.split('\n').filter(Boolean).map((line, i) => (
                                <p key={i} className="text-sm text-muted-foreground">{line}</p>
                            ))}
                        </div>
                    </ConfirmationRequest>
                </ConfirmationTitle>
                <ConfirmationActions>
                    {showRefactor ? (
                        <div className="w-full space-y-2 pt-2">
                            <Textarea
                                value={feedback}
                                onChange={e => setFeedback(e.target.value)}
                                placeholder="What should be changed in the plan?"
                                className="min-h-20 resize-none"
                                autoFocus
                            />
                            <div className="flex gap-2">
                                <Button size="sm" variant="ghost" onClick={() => { setShowRefactor(false); setFeedback('') }} className="flex-1">
                                    Cancel
                                </Button>
                                <Button size="sm" onClick={() => { onRefactor(feedback); setShowRefactor(false) }} disabled={!feedback.trim()} className="flex-1">
                                    Submit Changes
                                </Button>
                            </div>
                        </div>
                    ) : (
                        <>
                            <ConfirmationAction onClick={onApprove}>
                                <CheckCircle2 className="size-3.5 mr-1.5" />
                                Approve Plan
                            </ConfirmationAction>
                            <ConfirmationAction variant="outline" onClick={() => setShowRefactor(true)}>
                                <RotateCcw className="size-3.5 mr-1.5" />
                                Refactor Plan
                            </ConfirmationAction>
                        </>
                    )}
                </ConfirmationActions>
            </Confirmation>
        </div>
    )
})
PlanApprovalRenderer.displayName = 'PlanApprovalRenderer'

// ─── Artifact renderer ────────────────────────────────────────────────────────
const ArtifactRenderer = memo(({ artifact, isStreaming, onOpen }: {
    artifact: string
    isStreaming?: boolean
    onOpen: () => void
}) => {
    const handleDownload = (format: 'md' | 'pdf' | 'docx') => {
        if (format === 'md') {
            const blob = new Blob([artifact], { type: 'text/markdown' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a'); a.href = url; a.download = 'research-report.md'; a.click()
            URL.revokeObjectURL(url)
            toast.success("Markdown report downloaded")
        } else {
            toast.info(`Generating ${format.toUpperCase()} report…`)
            setTimeout(() => {
                const blob = new Blob([artifact], { type: 'text/plain' })
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a'); a.href = url; a.download = `research-report.${format}`; a.click()
                URL.revokeObjectURL(url)
                toast.success(`${format.toUpperCase()} downloaded`)
            }, 1000)
        }
    }

    return (
        <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
            <Artifact className="border-primary/20 bg-linear-to-b from-card to-card/50 shadow-xl overflow-hidden">
                <ArtifactHeader className="border-b border-border/10 bg-muted/5 p-6">
                    <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                            <Badge variant="outline" className="h-5 px-1.5 text-[10px] uppercase tracking-wider font-bold bg-primary/5 border-primary/20 text-primary">
                                Research Artifact
                            </Badge>
                            <span className="text-[10px] text-muted-foreground">•</span>
                            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">
                                {isStreaming ? 'Generating…' : 'Ready'}
                            </span>
                        </div>
                        <ArtifactTitle className="text-xl font-bold tracking-tight">Research Report</ArtifactTitle>
                        <ArtifactDescription className="text-sm text-muted-foreground/80">
                            Generated by Deep Researcher Engine
                        </ArtifactDescription>
                    </div>
                    <ArtifactActions>
                        {!isStreaming && (
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button variant="outline" size="sm" className="h-9 gap-1.5 border-primary/20 bg-background/50 backdrop-blur-sm">
                                        <Download className="size-4" />
                                        Download
                                        <ChevronDown className="size-3.5 opacity-50" />
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end" className="w-48">
                                    <DropdownMenuItem onClick={() => handleDownload('pdf')} className="gap-2">
                                        <FileType className="size-4 text-red-500" /><span>Download PDF</span>
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => handleDownload('docx')} className="gap-2">
                                        <FileType className="size-4 text-blue-500" /><span>Download Word</span>
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => handleDownload('md')} className="gap-2">
                                        <FileText className="size-4 text-primary" /><span>Download Markdown</span>
                                    </DropdownMenuItem>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem className="gap-2">
                                        <FileJson className="size-4 text-amber-500" /><span>Download RAW Data</span>
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        )}
                        <Button variant="default" size="sm" className="h-9 gap-1.5 shadow-lg shadow-primary/20" onClick={onOpen} disabled={isStreaming && !artifact}>
                            <ExternalLink className="size-4" />
                            Open Report
                        </Button>
                    </ArtifactActions>
                </ArtifactHeader>
                <ArtifactContent className="p-0">
                    <div className="group relative cursor-pointer hover:bg-muted/50 transition-all p-8 flex gap-6 items-start" onClick={onOpen}>
                        <div className="w-24 h-32 shrink-0 rounded border border-border/50 bg-background shadow-inner flex flex-col p-2 gap-1 overflow-hidden transition-transform group-hover:scale-105 group-hover:rotate-1">
                            <div className="h-1.5 w-full bg-primary/20 rounded-full" />
                            <div className="h-1 w-2/3 bg-muted rounded-full mt-1" />
                            <div className="mt-2 space-y-1">
                                {[1, 1, 0.75, 1, 0.5].map((w, i) => (
                                    <div key={i} className="h-0.5 bg-border rounded-full" style={{ width: `${w * 100}%` }} />
                                ))}
                            </div>
                            <div className="mt-auto h-8 w-full bg-muted/20 rounded flex items-center justify-center">
                                <FileText className="size-3 text-muted-foreground" />
                            </div>
                        </div>
                        <div className="flex-1 min-w-0">
                            <h4 className="font-semibold text-foreground mb-2 group-hover:text-primary transition-colors">Executive Summary</h4>
                            {isStreaming && !artifact ? (
                                <div className="space-y-2">
                                    <Shimmer className="text-sm">Generating report…</Shimmer>
                                </div>
                            ) : (
                                <p className="text-sm text-muted-foreground leading-relaxed line-clamp-3 italic font-serif">
                                    "{artifact.slice(0, 300).replace(/[#*_[\]]/g, '')}…"
                                </p>
                            )}
                            <div className="flex items-center gap-3 mt-4">
                                <span className="text-[10px] font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded">PDF v1.0</span>
                                <span className="text-[10px] font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded">Markdown</span>
                                <span className="text-[10px] font-bold text-primary ml-auto group-hover:translate-x-1 transition-transform">
                                    Click to read full report →
                                </span>
                            </div>
                        </div>
                    </div>
                </ArtifactContent>
            </Artifact>
        </div>
    )
})
ArtifactRenderer.displayName = 'ArtifactRenderer'

// ─── Stats bar ────────────────────────────────────────────────────────────────
const formatTime = (s: number) => { const m = Math.floor(s / 60); return m > 0 ? `${m}m ${s % 60}s` : `${s}s` }

const StatsBar = memo(({ tokens, elapsedSeconds, isRunning }: {
    tokens: { input_tokens: number; output_tokens: number; total_tokens: number }
    elapsedSeconds: number
    isRunning: boolean
}) => (
    <div className={cn("flex items-center gap-4 flex-wrap text-xs text-muted-foreground font-mono transition-opacity", isRunning ? "opacity-100" : "opacity-70")}>
        <div className="flex items-center gap-1.5"><Clock className="size-3.5" /><span>{formatTime(elapsedSeconds)}</span></div>
        <div className="flex items-center gap-1.5"><Zap className="size-3.5 text-amber-500" /><span>{tokens.total_tokens.toLocaleString()} tokens</span></div>
        <div className="flex items-center gap-1.5"><Database className="size-3.5 text-purple-500" />{tokens.input_tokens.toLocaleString()} in / {tokens.output_tokens.toLocaleString()} out</div>
    </div>
))
StatsBar.displayName = 'StatsBar'

// ─── Connection status indicator ──────────────────────────────────────────────
const ConnectionBadge = memo(({ status }: { status: string }) => {
    const cfg: Record<string, { icon: ReactNode; color: string; label: string }> = {
        connected: { icon: <Wifi className="size-3" />, color: 'text-green-500', label: 'Connected' },
        connecting: { icon: <Loader2 className="size-3 animate-spin" />, color: 'text-amber-500', label: 'Connecting' },
        disconnected: { icon: <WifiOff className="size-3" />, color: 'text-red-500', label: 'Disconnected' },
        running: { icon: <Wifi className="size-3" />, color: 'text-green-500', label: 'Live' },
        stopping: { icon: <Loader2 className="size-3 animate-spin" />, color: 'text-amber-500', label: 'Stopping' },
    }
    const c = cfg[status]
    if (!c) return null
    return (
        <div className={cn("flex items-center gap-1 text-xs font-mono", c.color)}>
            {c.icon}<span>{c.label}</span>
        </div>
    )
})
ConnectionBadge.displayName = 'ConnectionBadge'

// ─── Navigation state from NewResearch ───────────────────────────────────────
interface ResearchNavigationState {
    title: string
    description: string
    prompt: string
    workspaceId: string
    workspaceName: string
    preferences: { enableChat: boolean; allowBackendResearch: boolean; template: string; customInstructions: string }
    sources: { type: string; value: string; name?: string }[]
}

// ─── Main Component ───────────────────────────────────────────────────────────
const NEW_RESEARCH_ROUTE_ID = 'new'
const RESEARCH_BRIEF_STORAGE_KEY = 'dr.research.active_brief.v1'

const ResearchThread = () => {
    const location = useLocation()
    const navigate = useNavigate()
    const { id: urlResearchId } = useParams<{ id: string }>()
    const state = location.state as ResearchNavigationState | null

    /** `/researches/new` is a launcher route; real IDs resume existing sessions. */
    const sessionResearchId =
        urlResearchId &&
        urlResearchId !== NEW_RESEARCH_ROUTE_ID &&
        urlResearchId.trim() !== ''
            ? urlResearchId
            : undefined

    const [copyStatus, setCopyStatus] = useState<'idle' | 'loading' | 'success'>('idle')
    const [artifactOpen, setArtifactOpen] = useState(false)
    const [elapsedSeconds, setElapsedSeconds] = useState(0)
    const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

    const {
        status, researchId, steps, questions, plan,
        artifact, artifactDone, tokens, error, progress, progressMsg,
        isRunning, isPendingQuestion, isPendingApproval, context,
        startResearch, resumeSession, stopResearch, submitAnswer, approvePlan, refactorPlan,
    } = useResearchSession({
        researchId: sessionResearchId,
        onNavigateToSession: (id, replace) => navigate(`/researches/${encodeURIComponent(id)}`, { replace: !!replace }),
    })

    // Elapsed timer
    useEffect(() => {
        if (isRunning) {
            timerRef.current = setInterval(() => setElapsedSeconds(p => p + 1), 1000)
        } else {
            if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null }
        }
        return () => { if (timerRef.current) clearInterval(timerRef.current) }
    }, [isRunning])

    // Auto-start when opened as /researches/new with navigation state (from NewResearch on /researches/create)
    useEffect(() => {
        const isLauncher =
            !urlResearchId ||
            urlResearchId === NEW_RESEARCH_ROUTE_ID ||
            urlResearchId.trim() === ''
        if (!isLauncher || !state?.prompt?.trim() || !state?.workspaceId) return

        void startResearch({
            prompt: state.prompt,
            title: state.title || 'Research Task',
            description: state.description || '',
            workspace_id: state.workspaceId,
            sources: state.sources ?? [],
            system_prompt: '',
            research_template: resolveResearchTemplate(state.preferences?.template ?? 'comprehensive'),
            custom_prompt: state.preferences?.customInstructions ?? '',
            ai_personality: 'professional research analyst',
            username: 'Pixel',
        }).catch((err: unknown) => {
            toast.error(
                err instanceof Error ? err.message : 'Failed to start research. Is the backend running?',
            )
        })
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    const handleCopyAll = useCallback(async () => {
        setCopyStatus('loading')
        try {
            const text = artifact || steps.map(s => s.summary).filter(Boolean).join('\n\n')
            await navigator.clipboard.writeText(text)
            setCopyStatus('success')
            setTimeout(() => setCopyStatus('idle'), 2000)
        } catch { setCopyStatus('idle') }
    }, [artifact, steps])

    const recoveredContext = context || {}
    const researchTitle = state?.title || recoveredContext.title || 'Deep Research'
    const workspaceName = state?.workspaceName || recoveredContext.workspace_id || 'Research Workspace'
    const userPrompt = state?.prompt || recoveredContext.prompt || ''
    const userSources = state?.sources || recoveredContext.sources || []
    const hasContent = steps.length > 0 || artifact

    // Persist brief for QA UI if user refreshes mid-session
    useEffect(() => {
        if (!state?.workspaceId && !state?.prompt?.trim()) return
        try {
            sessionStorage.setItem(
                RESEARCH_BRIEF_STORAGE_KEY,
                JSON.stringify({
                    title: state?.title ?? '',
                    description: state?.description ?? '',
                    prompt: state?.prompt ?? '',
                    workspaceName: state?.workspaceName ?? '',
                    customInstructions: state?.preferences?.customInstructions ?? '',
                }),
            )
        } catch {
            /* ignore quota */
        }
    }, [state])

    const qaContext = useMemo((): QAResearchContext => {
        let cached: Partial<QAResearchContext> = {}
        try {
            const raw = sessionStorage.getItem(RESEARCH_BRIEF_STORAGE_KEY)
            if (raw) cached = JSON.parse(raw) as Partial<QAResearchContext>
        } catch {
            /* ignore */
        }
        return {
            title: state?.title ?? recoveredContext.title ?? cached.title ?? researchTitle,
            description: state?.description ?? recoveredContext.description ?? cached.description ?? '',
            prompt: (state?.prompt ?? recoveredContext.prompt ?? cached.prompt ?? userPrompt) || '',
            workspaceName:
                state?.workspaceName ?? recoveredContext.workspace_id ?? cached.workspaceName ?? workspaceName,
            customInstructions:
                state?.preferences?.customInstructions ?? recoveredContext.custom_prompt ?? cached.customInstructions,
        }
    }, [state, researchTitle, workspaceName, userPrompt, recoveredContext])

    // All tools flat for sidebar
    const allTools = steps.flatMap(s => s.tools)

    return (
        <div className="flex flex-col h-full w-full text-foreground animate-in fade-in duration-500 overflow-hidden relative">
            {/* Floating Header */}
            <header className="absolute top-4 left-6 right-6 z-30 pointer-events-none">
                <div className="pointer-events-auto backdrop-blur-xl bg-background/80 border border-border/50 rounded-2xl px-6 py-3 shadow-lg shadow-black/5 animate-in fade-in slide-in-from-top-2 duration-500 flex items-center gap-3 w-fit">
                    <Button variant="ghost" size="icon" className="size-7 shrink-0" onClick={() => navigate(-1)}>
                        <ChevronLeft className="size-4" />
                    </Button>
                    {isRunning && (
                        <Persona
                            state={steps.length > 0 && steps[steps.length - 1]?.status === 'running' ? 'thinking' : 'speaking'}
                            className="size-5"
                            variant="glint"
                        />
                    )}
                    <div className="flex flex-col">
                        <h2 className="text-sm font-semibold bg-linear-to-r from-foreground to-foreground/70 bg-clip-text text-transparent leading-none">
                            {researchTitle}
                        </h2>
                        <p className="text-[10px] text-muted-foreground/60 mt-1 font-medium">
                            {workspaceName} • {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                        </p>
                    </div>
                    <ConnectionBadge status={status} />
                    {progress > 0 && progress < 100 && (
                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-mono">
                            <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                                <div className="h-full bg-primary rounded-full transition-all duration-500" style={{ width: `${progress}%` }} />
                            </div>
                            <span>{progress}%</span>
                        </div>
                    )}
                </div>
            </header>

            {/* Error banner */}
            {error && (
                <div className="absolute top-20 left-6 right-6 z-20 animate-in fade-in slide-in-from-top-2 duration-300">
                    <div className="backdrop-blur-xl bg-destructive/10 border border-destructive/30 rounded-xl px-4 py-3 flex items-center gap-3">
                        <AlertCircle className="size-4 text-destructive shrink-0" />
                        <p className="text-sm text-destructive flex-1">{error}</p>
                        {researchId && (
                            <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive" onClick={() => void resumeSession(researchId)}>
                                <RotateCcw className="size-3.5 mr-1.5" />Retry
                            </Button>
                        )}
                    </div>
                </div>
            )}

            {/* Conversation Area */}
            <Conversation className="flex-1 w-full">
                <ConversationContent className="max-w-4xl mx-auto pt-20 pb-48 space-y-6">

                    {/* System Prompt */}
                    <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
                        <Message from="assistant" className="max-w-full">
                            <MessageContent className="bg-transparent px-0 py-0 w-full">
                                <Task defaultOpen={false}>
                                    <TaskTrigger title="System Prompt Loaded" />
                                    <TaskContent>
                                        <TaskItem>
                                            <pre className="text-xs text-muted-foreground whitespace-pre-wrap font-mono leading-relaxed">
                                                {DEFAULT_SYSTEM_PROMPT}
                                            </pre>
                                        </TaskItem>
                                    </TaskContent>
                                </Task>
                            </MessageContent>
                        </Message>
                    </div>

                    {/* User Prompt (use qaContext.prompt so cached brief still shows after refresh) */}
                    {qaContext.prompt && (
                        <div className="animate-in fade-in slide-in-from-bottom-2 duration-500 delay-200">
                            <Message from="user" className="pl-12 ml-auto max-w-full">
                                <MessageContent className="shadow-sm text-foreground">
                                    <MessageResponse>{qaContext.prompt}</MessageResponse>
                                    {userSources.length > 0 && (
                                        <div className="mt-3 pt-3 border-t border-border/30 space-y-2">
                                            <span className="text-xs font-medium text-muted-foreground">Attached Sources</span>
                                            <div className="flex flex-wrap gap-2">
                                                {userSources.map((source, i) => (
                                                    <Badge key={i} variant="secondary" className="gap-1.5 text-xs">
                                                        {source.type === 'youtube' ? <Youtube className="size-3 text-red-500" />
                                                            : source.type === 'file' ? <FileText className="size-3 text-orange-500" />
                                                            : <LinkIcon className="size-3 text-blue-500" />}
                                                        {source.name || source.value}
                                                    </Badge>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                    {state?.preferences && (
                                        <div className="mt-2 flex flex-wrap gap-1.5">
                                            <Badge variant="outline" className="text-[10px] gap-1">
                                                <Hash className="size-2.5" />{state.preferences.template}
                                            </Badge>
                                            {state.preferences.allowBackendResearch && (
                                                <Badge variant="outline" className="text-[10px] gap-1">
                                                    <Zap className="size-2.5" />Backend Research
                                                </Badge>
                                            )}
                                        </div>
                                    )}
                                </MessageContent>
                            </Message>
                        </div>
                    )}

                    {/* Plan */}
                    {plan && (
                        <PlanRenderer plan={plan.plan} steps={steps} isRunning={isRunning} />
                    )}

                    {/* Steps */}
                    {steps.map((step, idx) => (
                        <StepRenderer
                            key={`step-${step.index}`}
                            step={step}
                            isLast={idx === steps.length - 1}
                            isRunning={isRunning}
                        />
                    ))}

                    {/* Sources panel (from tool results that are URLs) */}
                    {allTools.length > 0 && (
                        <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                            <Sources>
                                <SourcesTrigger count={allTools.length} />
                                <SourcesContent>
                                    {allTools.map((tool, i) => (
                                        <Source key={i} href="#" title={`${tool.tool_name}: ${(JSON.stringify(tool.args) || '').slice(0, 60)}`} />
                                    ))}
                                </SourcesContent>
                            </Sources>
                        </div>
                    )}

                    {/* Plan approval */}
                    {isPendingApproval && plan && (
                        <PlanApprovalRenderer
                            plan={plan.plan}
                            onApprove={approvePlan}
                            onRefactor={refactorPlan}
                        />
                    )}

                    {/* QA Questions */}
                    {isPendingQuestion && questions.map(q => (
                        <QARenderer
                            key={`qa-${q.index}`}
                            question={q}
                            context={qaContext}
                            onSubmit={submitAnswer}
                        />
                    ))}

                    {/* Artifact streaming or done */}
                    {artifact && (
                        <ArtifactRenderer
                            artifact={artifact}
                            isStreaming={!artifactDone}
                            onOpen={() => setArtifactOpen(true)}
                        />
                    )}

                    {/* Thinking shimmer */}
                    {isRunning && hasContent && !isPendingQuestion && !isPendingApproval && !artifact && (
                        <div className="flex items-center gap-2 animate-in fade-in duration-300">
                            <Persona state="thinking" className="size-5" variant="glint" />
                            <Shimmer className="text-sm font-medium">
                                {progressMsg || 'Researching…'}
                            </Shimmer>
                        </div>
                    )}

                    {/* Not started yet shimmer */}
                    {(status === 'connecting' || status === 'starting') && steps.length === 0 && (
                        <div className="flex items-center gap-2 animate-in fade-in duration-300">
                            <Persona state="thinking" className="size-5" variant="glint" />
                            <Shimmer className="text-sm font-medium">Initializing research pipeline…</Shimmer>
                        </div>
                    )}

                    {/* Finish state */}
                    {!isRunning && hasContent && (
                        <div className="flex justify-center pt-8 pb-12 animate-in fade-in slide-in-from-bottom-4 duration-1000 delay-500">
                            <div className="p-8 rounded-3xl border border-primary/20 bg-linear-to-b from-primary/5 to-transparent flex flex-col items-center text-center max-w-lg w-full">
                                <div className="size-12 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
                                    <MessageSquare className="size-6 text-primary" />
                                </div>
                                <h3 className="text-xl font-bold mb-2">Research Completed</h3>
                                <p className="text-sm text-muted-foreground mb-6">
                                    The research has been synthesized into the final artifact. Dive deeper or share.
                                </p>
                                <div className="flex items-center gap-3 w-full">
                                    <Button className="flex-1 gap-2 h-11 text-base shadow-lg shadow-primary/20">
                                        <MessageSquare className="size-4" />
                                        Chat on Research
                                    </Button>
                                    <Button variant="outline" className="flex-1 gap-2 h-11 text-base">
                                        <Share2 className="size-4" />
                                        Share Report
                                    </Button>
                                </div>
                            </div>
                        </div>
                    )}
                </ConversationContent>
                <ConversationScrollButton />
            </Conversation>

            {/* Footer */}
            <footer className="shrink-0 border-t border-border/50 bg-background/80 backdrop-blur-sm z-20">
                <div className="max-w-4xl mx-auto px-6 py-3 flex items-center justify-between gap-4">
                    <StatsBar tokens={tokens} elapsedSeconds={elapsedSeconds} isRunning={isRunning} />
                    <div className="flex items-center gap-2">
                        {!isRunning && hasContent && (
                            <Button variant="ghost" size="sm" className="h-8 gap-1.5 text-xs" onClick={handleCopyAll} disabled={copyStatus !== 'idle'}>
                                {copyStatus === 'success' ? <><CheckIcon className="size-3.5 text-green-500" />Copied</>
                                    : copyStatus === 'loading' ? <><Loader2 className="size-3.5 animate-spin" />Copying…</>
                                    : <><CopyIcon className="size-3.5" />Copy Report</>}
                            </Button>
                        )}
                        {isRunning && (
                            <Button onClick={() => void stopResearch()} variant="destructive" size="sm" className="h-9 px-5 gap-2 shadow-lg shadow-destructive/20 animate-in fade-in zoom-in-95 duration-200">
                                <Square className="size-3.5 fill-current" />
                                Stop Research
                            </Button>
                        )}
                    </div>
                </div>
                {!isRunning && hasContent && (
                    <div className="text-center pb-3">
                        <p className="text-[10px] text-muted-foreground/50 font-medium">
                            Completed in {formatTime(elapsedSeconds)} • {tokens.total_tokens.toLocaleString()} tokens used
                        </p>
                    </div>
                )}
            </footer>

            {/* Artifact Sheet */}
            <Sheet open={artifactOpen} onOpenChange={setArtifactOpen}>
                <SheetContent side="right" className="w-full sm:w-1/2 sm:max-w-none border-l border-border/50 bg-card/95 backdrop-blur-xl p-0 flex flex-col overflow-hidden">
                    <div className="flex-1 overflow-y-auto px-8 pt-8 pb-32">
                        <SheetHeader className="space-y-4 p-0">
                            <div className="flex items-center gap-4">
                                <div className="size-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center">
                                    <FileText className="size-7 text-primary" />
                                </div>
                                <div>
                                    <SheetTitle className="text-2xl font-bold tracking-tight">Research Report</SheetTitle>
                                    <SheetDescription className="text-base">Generated by Deep Researcher Engine</SheetDescription>
                                </div>
                            </div>
                        </SheetHeader>
                        <div className="mt-12 bg-background rounded-3xl border border-border/50 shadow-sm p-8 max-w-none">
                            <Message from="assistant" className="max-w-none w-full">
                                <MessageContent className="bg-transparent px-0 py-0 w-full text-base leading-relaxed">
                                    <MessageResponse>{artifact}</MessageResponse>
                                </MessageContent>
                            </Message>
                        </div>
                    </div>
                    <div className="shrink-0 p-8 border-t bg-background/50 backdrop-blur-xl flex items-center justify-between gap-4 absolute bottom-0 left-0 right-0">
                        <Button variant="ghost" className="text-muted-foreground hover:text-foreground" onClick={() => setArtifactOpen(false)}>
                            Close Report
                        </Button>
                        <div className="flex items-center gap-3">
                            <Button variant="outline" className="gap-2 border-primary/20">
                                <FileOutput className="size-4" />Export JSON
                            </Button>
                            <Button className="gap-2 shadow-lg shadow-primary/20" onClick={() => {
                                const blob = new Blob([artifact], { type: 'text/markdown' })
                                const url = URL.createObjectURL(blob)
                                const a = document.createElement('a'); a.href = url; a.download = 'research-report.md'; a.click()
                            }}>
                                <Download className="size-4" />Download Markdown
                            </Button>
                        </div>
                    </div>
                </SheetContent>
            </Sheet>
        </div>
    )
}

export default ResearchThread
