import { useEffect, memo, useCallback, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
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
import { Task, TaskTrigger, TaskContent, TaskItem, TaskItemFile } from '@/components/ai-elements/task'
import {
    ChainOfThought, ChainOfThoughtHeader, ChainOfThoughtContent, ChainOfThoughtStep,
    ChainOfThoughtSearchResults, ChainOfThoughtSearchResult, ChainOfThoughtImage,
} from '@/components/ai-elements/chain-of-thought'
import {
    Confirmation, ConfirmationTitle, ConfirmationRequest,
    ConfirmationAccepted, ConfirmationRejected,
    ConfirmationActions, ConfirmationAction,
} from '@/components/ai-elements/confirmation'
import {
    Artifact, ArtifactHeader, ArtifactTitle, ArtifactDescription,
    ArtifactActions, ArtifactAction, ArtifactContent,
} from '@/components/ai-elements/artifact'
import {
    InlineCitation, InlineCitationText,
    InlineCitationCard, InlineCitationCardTrigger, InlineCitationCardBody,
} from '@/components/ai-elements/inline-citation'
import { Shimmer } from '@/components/ai-elements/shimmer'
import { Persona } from '@/components/ai-elements/persona'
import {
    Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription,
} from '@/components/ui/sheet'
import { cn } from '@/lib/utils'
import {
    SearchIcon, Square, Globe, FileText, BookOpen,
    Clock, Zap, Hash, Database, CopyIcon, CheckIcon,
    ChevronLeft, Sparkles, Youtube, Link as LinkIcon,
    CheckCircle2, Circle, Loader2, Download, ExternalLink,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useResearchSimulator } from './useResearchSimulator'
import { DEFAULT_SYSTEM_PROMPT } from './research_response'
import type {
    ResearchStep,
    ReasoningStep as TReasoningStep,
    PlanStep as TPlanStep,
    ToolCallStep as TToolCallStep,
    ContentStep as TContentStep,
    SourcesStep as TSourcesStep,
    TaskStep as TTaskStep,
    ChainOfThoughtStep as TCOTStep,
    ConfirmationStep as TConfirmationStep,
    ArtifactStep as TArtifactStep,
} from './research_response'
import "katex/dist/katex.min.css"

// ─── Step Renderers ───────────────────────────────────────────────────────────

const ReasoningStepRenderer = memo(({ step, isLast, isRunning }: { step: TReasoningStep; isLast: boolean; isRunning: boolean }) => (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
        <Reasoning isStreaming={isLast && isRunning} duration={step.durationSeconds} defaultOpen={isLast && isRunning}>
            <ReasoningTrigger />
            <ReasoningContent>{step.content}</ReasoningContent>
        </Reasoning>
    </div>
))
ReasoningStepRenderer.displayName = 'ReasoningStepRenderer'

const PlanStepRenderer = memo(({ step, isRunning }: { step: TPlanStep; isRunning: boolean }) => {
    const hasActiveTask = step.tasks.some(t => t.status === 'active')
    return (
        <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
            <Plan isStreaming={hasActiveTask && isRunning} defaultOpen>
                <PlanHeader>
                    <div>
                        <PlanTitle>{step.title}</PlanTitle>
                        <PlanDescription>{step.description}</PlanDescription>
                    </div>
                    <PlanAction>
                        <PlanTrigger />
                    </PlanAction>
                </PlanHeader>
                <PlanContent>
                    <div className="space-y-2 pb-4">
                        {step.tasks.map((task, i) => (
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
                                )}>
                                    {task.label}
                                </span>
                            </div>
                        ))}
                    </div>
                </PlanContent>
            </Plan>
        </div>
    )
})
PlanStepRenderer.displayName = 'PlanStepRenderer'

const ToolCallStepRenderer = memo(({ step }: { step: TToolCallStep }) => (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
        <Tool>
            <ToolHeader
                title={step.title}
                type="dynamic-tool"
                state={step.state}
                toolName={step.toolName}
            />
            <ToolContent>
                <ToolInput input={step.input} />
                <ToolOutput output={step.output} errorText={step.state === 'output-error' ? 'Tool execution failed' : undefined} />
            </ToolContent>
        </Tool>
    </div>
))
ToolCallStepRenderer.displayName = 'ToolCallStepRenderer'

const ContentStepRenderer = memo(({ step, isLast, isRunning }: { step: TContentStep; isLast: boolean; isRunning: boolean }) => {
    const streaming = (isLast && isRunning) || step.isStreaming
    return (
        <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
            <Message from="assistant" className="max-w-full">
                <MessageContent className="bg-transparent px-0 py-0 w-full text-justify">
                    <MessageResponse
                        isAnimating={streaming}
                        className={cn(streaming && "streaming-text-fade")}
                    >
                        {step.content}
                    </MessageResponse>

                    {/* Inline citation markers */}
                    {step.citations && step.citations.length > 0 && !streaming && (
                        <div className="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-border/30">
                            {step.citations.map((cit, i) => (
                                <InlineCitation key={i}>
                                    <InlineCitationCard>
                                        <InlineCitationCardTrigger>
                                            <InlineCitationText>
                                                <Badge variant="secondary" className="text-[10px] gap-1 cursor-pointer hover:bg-primary/10 transition-colors">
                                                    <ExternalLink className="size-2.5" />
                                                    {cit.sources[0]?.title.slice(0, 40)}...
                                                </Badge>
                                            </InlineCitationText>
                                        </InlineCitationCardTrigger>
                                        <InlineCitationCardBody>
                                            <div className="space-y-2 p-3">
                                                {cit.sources.map((src, si) => (
                                                    <div key={si} className="space-y-1">
                                                        <a
                                                            href={src.url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="text-sm font-medium text-primary hover:underline"
                                                        >
                                                            {src.title}
                                                        </a>
                                                        <p className="text-xs text-muted-foreground">{src.description}</p>
                                                    </div>
                                                ))}
                                            </div>
                                        </InlineCitationCardBody>
                                    </InlineCitationCard>
                                </InlineCitation>
                            ))}
                        </div>
                    )}
                </MessageContent>
            </Message>
        </div>
    )
})
ContentStepRenderer.displayName = 'ContentStepRenderer'

const SourcesStepRenderer = memo(({ step }: { step: TSourcesStep }) => (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
        <Sources>
            <SourcesTrigger count={step.items.length} />
            <SourcesContent>
                {step.items.map((s, i) => (
                    <Source key={i} href={s.href} title={s.title} />
                ))}
            </SourcesContent>
        </Sources>
    </div>
))
SourcesStepRenderer.displayName = 'SourcesStepRenderer'

const TaskStepRenderer = memo(({ step }: { step: TTaskStep }) => (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
        <Task defaultOpen>
            <TaskTrigger title={step.title} />
            <TaskContent>
                {step.items.map((item, i) => (
                    <TaskItem key={i}>
                        <span>{item.label}</span>
                        {item.file && (
                            <TaskItemFile className="ml-2">
                                <FileText className="size-3" />
                                {item.file}
                            </TaskItemFile>
                        )}
                    </TaskItem>
                ))}
            </TaskContent>
        </Task>
    </div>
))
TaskStepRenderer.displayName = 'TaskStepRenderer'

const COTStepRenderer = memo(({ step }: { step: TCOTStep }) => (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
        <div className="bg-accent/50 rounded-2xl border border-border/50 overflow-hidden">
            <ChainOfThought className="p-4 pb-0 w-full" defaultOpen>
                <ChainOfThoughtHeader className="w-full" />
                <ChainOfThoughtContent className="w-full pr-4">
                    {step.steps.map((s, i) => (
                        <ChainOfThoughtStep
                            key={i}
                            icon={SearchIcon}
                            label={s.label}
                            status={s.status}
                        >
                            <MessageResponse className="text-muted-foreground mt-2 mb-2 w-full">
                                {s.content}
                            </MessageResponse>

                            {/* Search results as badges */}
                            {s.searchResults && s.searchResults.length > 0 && (
                                <ChainOfThoughtSearchResults className="mb-2">
                                    {s.searchResults.map((sr, sri) => (
                                        <ChainOfThoughtSearchResult key={sri}>
                                            {sr.url ? (
                                                <a href={sr.url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                                                    {sr.label}
                                                </a>
                                            ) : sr.label}
                                        </ChainOfThoughtSearchResult>
                                    ))}
                                </ChainOfThoughtSearchResults>
                            )}

                            {/* Image within thought step */}
                            {s.image && (
                                <ChainOfThoughtImage
                                    src={s.image.src}
                                    alt={s.image.caption}
                                    caption={s.image.caption}
                                    className="mb-4"
                                />
                            )}
                        </ChainOfThoughtStep>
                    ))}
                </ChainOfThoughtContent>
            </ChainOfThought>
        </div>
    </div>
))
COTStepRenderer.displayName = 'COTStepRenderer'

const ConfirmationStepRenderer = memo(({
    step,
    isPending,
    onApprove,
    onReject,
}: {
    step: TConfirmationStep
    isPending: boolean
    onApprove: (value: string) => void
    onReject: (reason?: string) => void
}) => (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
        <Confirmation
            state={isPending ? 'approval-requested' : 'approved'}
        >
            <ConfirmationTitle>
                <div className="flex items-center gap-2">
                    <div className="size-6 rounded-full bg-primary/20 flex items-center justify-center">
                        <Sparkles className="size-3.5 text-primary" />
                    </div>
                    Approval Required
                </div>
            </ConfirmationTitle>
            <ConfirmationRequest>{step.question}</ConfirmationRequest>

            {isPending ? (
                <ConfirmationActions>
                    {step.actions.map((action, i) => (
                        <ConfirmationAction
                            key={i}
                            onClick={() => onApprove(action.value)}
                        >
                            {action.label}
                        </ConfirmationAction>
                    ))}
                    <ConfirmationAction
                        variant="outline"
                        onClick={() => onReject('User declined')}
                    >
                        Decline
                    </ConfirmationAction>
                </ConfirmationActions>
            ) : (
                <ConfirmationAccepted>
                    <div className="flex items-center gap-1.5 text-xs text-green-600">
                        <CheckCircle2 className="size-3" />
                        Approved — proceeding with detailed analysis
                    </div>
                </ConfirmationAccepted>
            )}

            <ConfirmationRejected>
                <div className="flex items-center gap-1.5 text-xs text-destructive">
                    Research stopped by user
                </div>
            </ConfirmationRejected>
        </Confirmation>
    </div>
))
ConfirmationStepRenderer.displayName = 'ConfirmationStepRenderer'

const ArtifactStepRenderer = memo(({
    step,
    onOpenArtifact,
}: {
    step: TArtifactStep
    onOpenArtifact: () => void
}) => (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
        <Artifact>
            <ArtifactHeader>
                <div className="flex-1">
                    <ArtifactTitle>{step.title}</ArtifactTitle>
                    <ArtifactDescription>{step.description}</ArtifactDescription>
                </div>
                <ArtifactActions>
                    <ArtifactAction label="View Report" onClick={onOpenArtifact}>
                        <ExternalLink className="size-4" />
                    </ArtifactAction>
                    <ArtifactAction label="Download" onClick={() => {
                        const blob = new Blob([step.content], { type: 'text/markdown' })
                        const url = URL.createObjectURL(blob)
                        const a = document.createElement('a')
                        a.href = url
                        a.download = `${step.title.replace(/[^a-zA-Z0-9]/g, '_')}.md`
                        a.click()
                        URL.revokeObjectURL(url)
                    }}>
                        <Download className="size-4" />
                    </ArtifactAction>
                </ArtifactActions>
            </ArtifactHeader>
            <ArtifactContent>
                <div
                    className="cursor-pointer hover:bg-accent/50 transition-colors rounded-lg p-3"
                    onClick={onOpenArtifact}
                >
                    <p className="text-sm text-muted-foreground line-clamp-3">
                        {step.content.slice(0, 250).replace(/[#*_\[\]]/g, '')}...
                    </p>
                    <span className="text-xs text-primary mt-2 inline-block font-medium">
                        Click to view full report →
                    </span>
                </div>
            </ArtifactContent>
        </Artifact>
    </div>
))
ArtifactStepRenderer.displayName = 'ArtifactStepRenderer'

// ─── Step Dispatcher ──────────────────────────────────────────────────────────

const ResearchStepItem = memo(({
    step, isLast, isRunning,
    isPendingConfirmation, onApprove, onReject,
    onOpenArtifact,
}: {
    step: ResearchStep
    isLast: boolean
    isRunning: boolean
    isPendingConfirmation: boolean
    onApprove: (value: string) => void
    onReject: (reason?: string) => void
    onOpenArtifact: () => void
}) => {
    switch (step.type) {
        case 'reasoning': return <ReasoningStepRenderer step={step} isLast={isLast} isRunning={isRunning} />
        case 'plan': return <PlanStepRenderer step={step} isRunning={isRunning} />
        case 'tool-call': return <ToolCallStepRenderer step={step} />
        case 'content': return <ContentStepRenderer step={step} isLast={isLast} isRunning={isRunning} />
        case 'sources': return <SourcesStepRenderer step={step} />
        case 'task': return <TaskStepRenderer step={step} />
        case 'chain-of-thought': return <COTStepRenderer step={step} />
        case 'confirmation': return (
            <ConfirmationStepRenderer
                step={step}
                isPending={isPendingConfirmation && isLast}
                onApprove={onApprove}
                onReject={onReject}
            />
        )
        case 'artifact': return <ArtifactStepRenderer step={step} onOpenArtifact={onOpenArtifact} />
        default: return null
    }
})
ResearchStepItem.displayName = 'ResearchStepItem'

// ─── Stats Bar ────────────────────────────────────────────────────────────────

const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return m > 0 ? `${m}m ${s}s` : `${s}s`
}

const StatsBar = memo(({ stats, elapsedSeconds, isRunning }: {
    stats: { tokensUsed: number; filesReferenced: number; websitesVisited: number; docsRead: number; contextTokens: number }
    elapsedSeconds: number
    isRunning: boolean
}) => (
    <div className={cn(
        "flex items-center gap-4 flex-wrap text-xs text-muted-foreground font-mono transition-opacity",
        isRunning ? "opacity-100" : "opacity-70"
    )}>
        <div className="flex items-center gap-1.5">
            <Clock className="size-3.5" />
            <span>{formatTime(elapsedSeconds)}</span>
        </div>
        <div className="flex items-center gap-1.5">
            <Zap className="size-3.5 text-amber-500" />
            <span>{stats.tokensUsed.toLocaleString()} tokens</span>
        </div>
        <div className="flex items-center gap-1.5">
            <Globe className="size-3.5 text-blue-500" />
            <span>{stats.websitesVisited} sites</span>
        </div>
        <div className="flex items-center gap-1.5">
            <FileText className="size-3.5 text-orange-500" />
            <span>{stats.filesReferenced} files</span>
        </div>
        <div className="flex items-center gap-1.5">
            <BookOpen className="size-3.5 text-green-500" />
            <span>{stats.docsRead} docs</span>
        </div>
        <div className="flex items-center gap-1.5">
            <Database className="size-3.5 text-purple-500" />
            <span>~{stats.contextTokens.toLocaleString()} ctx</span>
        </div>
    </div>
))
StatsBar.displayName = 'StatsBar'

// ─── Main Component ───────────────────────────────────────────────────────────

interface ResearchNavigationState {
    title: string
    description: string
    prompt: string
    workspaceId: string
    workspaceName: string
    preferences: {
        enableChat: boolean
        allowBackendResearch: boolean
        template: string
        customInstructions: string
    }
    sources: { type: string; value: string; name?: string }[]
}

const ResearchThread = () => {
    const location = useLocation()
    const navigate = useNavigate()
    const state = location.state as ResearchNavigationState | null
    const {
        steps, stats, isRunning, elapsedSeconds,
        isPendingConfirmation, approveConfirmation, rejectConfirmation,
        stopResearch, startResearch,
    } = useResearchSimulator()
    const [copyStatus, setCopyStatus] = useState<'idle' | 'loading' | 'success'>('idle')
    const [artifactOpen, setArtifactOpen] = useState(false)

    // Find the artifact step for the sheet content
    const artifactStep = steps.find((s): s is ResearchStep & { type: 'artifact' } => s.type === 'artifact') as
        | (ResearchStep & { type: 'artifact'; title: string; description: string; content: string })
        | undefined

    // Auto-start on mount
    useEffect(() => {
        const timer = setTimeout(() => {
            startResearch()
        }, 800)
        return () => clearTimeout(timer)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    const handleCopyAll = useCallback(async () => {
        setCopyStatus('loading')
        const allContent = steps
            .filter((s): s is TContentStep => s.type === 'content')
            .map(s => s.content)
            .join('\n\n')
        try {
            await navigator.clipboard.writeText(allContent)
            setCopyStatus('success')
            setTimeout(() => setCopyStatus('idle'), 2000)
        } catch {
            setCopyStatus('idle')
        }
    }, [steps])

    const researchTitle = state?.title || 'AI Impact on Healthcare'
    const workspaceName = state?.workspaceName || 'Research Workspace'
    const userPrompt = state?.prompt || 'Analyze the impact of AI on the healthcare industry, focusing on diagnostics, drug discovery, and patient outcomes. Include recent data from 2023-2025.'
    const userSources = state?.sources || []

    return (
        <div className="flex flex-col h-full w-full text-foreground animate-in fade-in duration-500 overflow-hidden relative">
            {/* Floating Header */}
            <header className="absolute top-4 left-6 right-6 z-30 pointer-events-none">
                <div className="pointer-events-auto backdrop-blur-xl bg-background/80 border border-border/50 rounded-2xl px-6 py-3 shadow-lg shadow-black/5 animate-in fade-in slide-in-from-top-2 duration-500 flex items-center gap-3 w-fit">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="size-7 shrink-0"
                        onClick={() => navigate(-1)}
                    >
                        <ChevronLeft className="size-4" />
                    </Button>
                    {isRunning && (
                        <Persona
                            state={steps.length > 0 && steps[steps.length - 1]?.type === 'content' ? 'speaking' : 'thinking'}
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
                </div>
            </header>

            {/* Conversation Area */}
            <Conversation className="flex-1 w-full">
                <ConversationContent className="max-w-4xl mx-auto pt-20 pb-48 space-y-6">

                    {/* ── System Prompt (collapsed) ────────────────────────────────── */}
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

                    {/* ── User Prompt Bubble ───────────────────────────────────────── */}
                    <div className="animate-in fade-in slide-in-from-bottom-2 duration-500 delay-200">
                        <Message from="user" className="pl-12 ml-auto max-w-full">
                            <MessageContent className="shadow-sm text-foreground">
                                <MessageResponse>{userPrompt}</MessageResponse>

                                {/* Attached sources */}
                                {userSources.length > 0 && (
                                    <div className="mt-3 pt-3 border-t border-border/30 space-y-2">
                                        <span className="text-xs font-medium text-muted-foreground">Attached Sources</span>
                                        <div className="flex flex-wrap gap-2">
                                            {userSources.map((source, i) => (
                                                <Badge key={i} variant="secondary" className="gap-1.5 text-xs">
                                                    {source.type === 'youtube' ? (
                                                        <Youtube className="size-3 text-red-500" />
                                                    ) : source.type === 'file' ? (
                                                        <FileText className="size-3 text-orange-500" />
                                                    ) : (
                                                        <LinkIcon className="size-3 text-blue-500" />
                                                    )}
                                                    {source.name || source.value}
                                                </Badge>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Preferences summary */}
                                {state?.preferences && (
                                    <div className="mt-2 flex flex-wrap gap-1.5">
                                        <Badge variant="outline" className="text-[10px] gap-1">
                                            <Hash className="size-2.5" />
                                            {state.preferences.template}
                                        </Badge>
                                        {state.preferences.allowBackendResearch && (
                                            <Badge variant="outline" className="text-[10px] gap-1">
                                                <Zap className="size-2.5" />
                                                Backend Research
                                            </Badge>
                                        )}
                                    </div>
                                )}
                            </MessageContent>
                        </Message>
                    </div>

                    {/* ── Research Steps ───────────────────────────────────────────── */}
                    {steps.map((step, idx) => (
                        <ResearchStepItem
                            key={idx}
                            step={step}
                            isLast={idx === steps.length - 1}
                            isRunning={isRunning}
                            isPendingConfirmation={isPendingConfirmation}
                            onApprove={approveConfirmation}
                            onReject={rejectConfirmation}
                            onOpenArtifact={() => setArtifactOpen(true)}
                        />
                    ))}

                    {/* ── Thinking shimmer when running with no new step ───────────── */}
                    {isRunning && steps.length > 0 && !isPendingConfirmation && (
                        <div className="flex items-center gap-2 animate-in fade-in duration-300">
                            <Persona state="thinking" className="size-5" variant="glint" />
                            <Shimmer className="text-sm font-medium">Researching...</Shimmer>
                        </div>
                    )}
                </ConversationContent>
                <ConversationScrollButton />
            </Conversation>

            {/* ── Footer: Stats + Stop ────────────────────────────────────────── */}
            <footer className="shrink-0 border-t border-border/50 bg-background/80 backdrop-blur-sm z-20">
                <div className="max-w-4xl mx-auto px-6 py-3 flex items-center justify-between gap-4">
                    <StatsBar stats={stats} elapsedSeconds={elapsedSeconds} isRunning={isRunning} />

                    <div className="flex items-center gap-2">
                        {/* Copy all content */}
                        {!isRunning && steps.length > 0 && (
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 gap-1.5 text-xs"
                                onClick={handleCopyAll}
                                disabled={copyStatus !== 'idle'}
                            >
                                {copyStatus === 'success' ? (
                                    <><CheckIcon className="size-3.5 text-green-500" /> Copied</>
                                ) : copyStatus === 'loading' ? (
                                    <><Loader2 className="size-3.5 animate-spin" /> Copying...</>
                                ) : (
                                    <><CopyIcon className="size-3.5" /> Copy Report</>
                                )}
                            </Button>
                        )}

                        {/* Stop button */}
                        {isRunning && (
                            <Button
                                onClick={stopResearch}
                                variant="destructive"
                                size="sm"
                                className="h-9 px-5 gap-2 shadow-lg shadow-destructive/20 animate-in fade-in zoom-in-95 duration-200"
                            >
                                <Square className="size-3.5 fill-current" />
                                Stop Research
                            </Button>
                        )}
                    </div>
                </div>

                {/* Research complete message */}
                {!isRunning && steps.length > 0 && (
                    <div className="text-center pb-3">
                        <p className="text-[10px] text-muted-foreground/50 font-medium">
                            Research completed in {formatTime(elapsedSeconds)} • {stats.tokensUsed.toLocaleString()} tokens used
                        </p>
                    </div>
                )}
            </footer>

            {/* ── Artifact Sheet ───────────────────────────────────────────────── */}
            <Sheet open={artifactOpen} onOpenChange={setArtifactOpen}>
                <SheetContent side="right" className="w-full sm:max-w-2xl overflow-y-auto">
                    <SheetHeader>
                        <SheetTitle>{artifactStep?.title || 'Research Report'}</SheetTitle>
                        <SheetDescription>{artifactStep?.description || ''}</SheetDescription>
                    </SheetHeader>
                    <div className="px-4 pb-8">
                        <Message from="assistant" className="max-w-full">
                            <MessageContent className="bg-transparent px-0 py-0 w-full">
                                <MessageResponse>
                                    {artifactStep?.content || ''}
                                </MessageResponse>
                            </MessageContent>
                        </Message>
                    </div>
                </SheetContent>
            </Sheet>
        </div>
    )
}

export default ResearchThread