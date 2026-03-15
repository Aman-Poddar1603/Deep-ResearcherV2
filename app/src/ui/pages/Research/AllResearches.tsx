import { useState, useMemo, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  Message,
  MessageContent,
  MessageResponse,
} from '@/components/ai-elements/message'
import { cn } from '@/lib/utils'
import {
  Search,
  FlaskConical,
  Clock,
  Calendar,
  ChevronDown,
  ChevronRight,
  Eye,
  Plus,
  TrendingUp,
  Users,
  Briefcase,
  GraduationCap,
  ArrowUpDown,
  X,
  type LucideIcon,
  ChevronLeft,
  Filter,
  LayoutGrid,
  List,
  Loader2,
} from 'lucide-react'
import { toast } from 'sonner'
import {
  listResearchRecords,
  getAllWorkspaces,
  type ResearchRecord,
  type WorkspaceOut,
} from '@/lib/apis'

// ─── Accent Color System ──────────────────────────────────────────────────────
const getAccentClasses = (color: string) => {
  const classMap: Record<string, {
    text: string; bg: string; border: string; dot: string; cardBorder: string; strip: string;
  }> = {
    'purple-400': { text: 'text-purple-400', bg: 'bg-purple-400/10', border: 'border-purple-400/30', dot: 'bg-purple-400', cardBorder: 'border-l-purple-400', strip: 'bg-purple-400' },
    'blue-400':   { text: 'text-blue-400',   bg: 'bg-blue-400/10',   border: 'border-blue-400/30',   dot: 'bg-blue-400',   cardBorder: 'border-l-blue-400',   strip: 'bg-blue-400' },
    'green-400':  { text: 'text-green-400',  bg: 'bg-green-400/10',  border: 'border-green-400/30',  dot: 'bg-green-400',  cardBorder: 'border-l-green-400',  strip: 'bg-green-400' },
    'pink-400':   { text: 'text-pink-400',   bg: 'bg-pink-400/10',   border: 'border-pink-400/30',   dot: 'bg-pink-400',   cardBorder: 'border-l-pink-400',   strip: 'bg-pink-400' },
    'orange-400': { text: 'text-orange-400', bg: 'bg-orange-400/10', border: 'border-orange-400/30', dot: 'bg-orange-400', cardBorder: 'border-l-orange-400', strip: 'bg-orange-400' },
  }
  return classMap[color] ?? classMap['purple-400']
}

// ─── Constants ────────────────────────────────────────────────────────────────
const WORKSPACE_COLORS = ['blue-400', 'purple-400', 'green-400', 'pink-400', 'orange-400'] as const
const WORKSPACE_ICONS: LucideIcon[] = [TrendingUp, Users, Briefcase, GraduationCap]

// ─── Types ────────────────────────────────────────────────────────────────────
interface Research {
  id: string
  title: string
  summary: string
  status: 'completed' | 'in-progress' | 'pending'
  workspaceId: string | null
  createdAt: string
  updatedAt: string
  sourceCount: number
  artifacts: string | null
  chatAccess: boolean
}

interface WorkspaceOption {
  id: string
  name: string
  icon: LucideIcon
  color: string
  researchCount: number
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
const deriveStatus = (record: ResearchRecord): Research['status'] => {
  if (record.artifacts) return 'completed'
  if (record.background_processing) return 'in-progress'
  return 'pending'
}

const parseSourceCount = (sources: string | null): number => {
  if (!sources) return 0
  try {
    const parsed = JSON.parse(sources)
    if (Array.isArray(parsed)) return parsed.length
  } catch { /* not JSON */ }
  return sources.split(',').filter((s) => s.trim()).length
}

const formatDate = (value?: string | null): string => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

const mapResearch = (record: ResearchRecord): Research => ({
  id: record.id,
  title: record.title ?? 'Untitled Research',
  summary: record.desc ?? 'No description provided.',
  status: deriveStatus(record),
  workspaceId: record.workspace_id ?? null,
  createdAt: formatDate(record.created_at),
  updatedAt: formatDate(record.updated_at),
  sourceCount: parseSourceCount(record.sources),
  artifacts: record.artifacts ?? null,
  chatAccess: record.chat_access,
})

const mapWorkspace = (ws: WorkspaceOut, index: number, researchCount: number): WorkspaceOption => ({
  id: ws.id,
  name: ws.name,
  icon: WORKSPACE_ICONS[index % WORKSPACE_ICONS.length],
  color: WORKSPACE_COLORS[index % WORKSPACE_COLORS.length],
  researchCount,
})

// ─── Status config ────────────────────────────────────────────────────────────
const STATUS_CONFIG = {
  'completed':   { label: 'Completed',   className: 'bg-emerald-500/15 text-emerald-500 border-emerald-500/20' },
  'in-progress': { label: 'In Progress', className: 'bg-amber-500/15 text-amber-500 border-amber-500/20' },
  'pending':     { label: 'Pending',     className: 'bg-slate-500/15 text-slate-400 border-slate-500/20' },
}

type SortOption = 'latest' | 'oldest' | 'name-az'
type ViewMode = 'grid' | 'list'
const ITEMS_PER_PAGE_OPTIONS = [6, 12, 24]

// ─── Component ────────────────────────────────────────────────────────────────
const AllResearches = () => {
  const navigate = useNavigate()

  const [searchQuery, setSearchQuery] = useState('')
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null)
  const [selectedStatus, setSelectedStatus] = useState<string>('all')
  const [sortBy, setSortBy] = useState<SortOption>('latest')
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [currentPage, setCurrentPage] = useState(1)
  const [itemsPerPage, setItemsPerPage] = useState(12)
  const [collapsedWorkspaces, setCollapsedWorkspaces] = useState<Set<string>>(new Set())
  const [previewResearch, setPreviewResearch] = useState<Research | null>(null)

  const [researches, setResearches] = useState<Research[]>([])
  const [workspaces, setWorkspaces] = useState<WorkspaceOption[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const loadData = useCallback(async () => {
    setIsLoading(true)
    try {
      const [researchResponse, workspaceList] = await Promise.all([
        listResearchRecords({ page: 1, size: 500, sortBy: 'id', sortOrder: 'desc' }),
        getAllWorkspaces(),
      ])

      const mappedResearches = researchResponse.items.map(mapResearch)

      const countByWs: Record<string, number> = {}
      mappedResearches.forEach((r) => {
        if (r.workspaceId) countByWs[r.workspaceId] = (countByWs[r.workspaceId] ?? 0) + 1
      })

      const mappedWorkspaces = (workspaceList as WorkspaceOut[]).map((ws, i) =>
        mapWorkspace(ws, i, countByWs[ws.id] ?? 0)
      )

      setResearches(mappedResearches)
      setWorkspaces(mappedWorkspaces)
    } catch (err) {
      console.error('Failed to load research data', err)
      toast.error('Failed to load researches')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => { void loadData() }, [loadData])

  const filteredResearches = useMemo(() => {
    let results = [...researches]

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      results = results.filter((r) =>
        r.title.toLowerCase().includes(q) || r.summary.toLowerCase().includes(q)
      )
    }

    if (selectedWorkspaceId) {
      results = results.filter((r) => r.workspaceId === selectedWorkspaceId)
    }

    if (selectedStatus !== 'all') {
      results = results.filter((r) => r.status === selectedStatus)
    }

    switch (sortBy) {
      case 'oldest': results.reverse(); break
      case 'name-az': results.sort((a, b) => a.title.localeCompare(b.title)); break
    }

    return results
  }, [researches, searchQuery, selectedWorkspaceId, selectedStatus, sortBy])

  const groupedResearches = useMemo(() => {
    const groups: Record<string, Research[]> = {}
    filteredResearches.forEach((r) => {
      const key = r.workspaceId ?? '__none__'
      if (!groups[key]) groups[key] = []
      groups[key].push(r)
    })
    return groups
  }, [filteredResearches])

  const totalItems = filteredResearches.length
  const totalPages = Math.max(1, Math.ceil(totalItems / itemsPerPage))

  const paginatedResearches = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage
    return filteredResearches.slice(start, start + itemsPerPage)
  }, [filteredResearches, currentPage, itemsPerPage])

  const paginatedGroups = useMemo(() => {
    const groups: Record<string, Research[]> = {}
    paginatedResearches.forEach((r) => {
      const key = r.workspaceId ?? '__none__'
      if (!groups[key]) groups[key] = []
      groups[key].push(r)
    })
    return groups
  }, [paginatedResearches])

  const toggleWorkspaceCollapse = (wsId: string) => {
    setCollapsedWorkspaces((prev) => {
      const next = new Set(prev)
      next.has(wsId) ? next.delete(wsId) : next.add(wsId)
      return next
    })
  }

  const clearFilters = () => {
    setSearchQuery('')
    setSelectedWorkspaceId(null)
    setSelectedStatus('all')
    setSortBy('latest')
    setCurrentPage(1)
  }

  const hasActiveFilters = Boolean(searchQuery || selectedWorkspaceId || selectedStatus !== 'all' || sortBy !== 'latest')

  const getWorkspaceFor = (wsId: string | null) => workspaces.find((w) => w.id === wsId)

  return (
    <div className="flex flex-col h-full w-full overflow-hidden animate-in fade-in duration-500">
      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="shrink-0 border-b border-border/50 bg-background/50 backdrop-blur-sm sticky top-0 z-30">
        <div className="w-full px-8 py-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="size-11 rounded-2xl bg-linear-to-br from-primary/20 via-primary/10 to-transparent border border-primary/20 flex items-center justify-center animate-in fade-in zoom-in duration-500">
                <FlaskConical className="size-5 text-primary" />
              </div>
              <div>
                <h1 className="text-xl font-semibold tracking-tight animate-in fade-in slide-in-from-bottom-2 duration-500 fill-mode-both" style={{ animationDelay: '100ms' }}>
                  All Researches
                </h1>
                <p className="text-sm text-muted-foreground animate-in fade-in slide-in-from-bottom-2 duration-500 fill-mode-both" style={{ animationDelay: '150ms' }}>
                  {isLoading
                    ? 'Loading…'
                    : `${totalItems} research${totalItems !== 1 ? 'es' : ''} across ${Object.keys(groupedResearches).length} workspace${Object.keys(groupedResearches).length !== 1 ? 's' : ''}`}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 animate-in fade-in slide-in-from-right-4 duration-500 fill-mode-both" style={{ animationDelay: '200ms' }}>
              <div className="flex items-center border border-border/50 rounded-lg p-0.5 bg-muted/30">
                <Button variant={viewMode === 'grid' ? 'secondary' : 'ghost'} size="sm" className="h-7 w-7 p-0" onClick={() => setViewMode('grid')}>
                  <LayoutGrid className="size-3.5" />
                </Button>
                <Button variant={viewMode === 'list' ? 'secondary' : 'ghost'} size="sm" className="h-7 w-7 p-0" onClick={() => setViewMode('list')}>
                  <List className="size-3.5" />
                </Button>
              </div>
              <Button size="sm" className="gap-2" onClick={() => navigate('/researches/new')}>
                <Plus className="size-4" />
                New Research
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* ── Filters ─────────────────────────────────────────────────── */}
      <div className="shrink-0 px-8 py-3 border-b border-border/30 bg-background/30 backdrop-blur-sm">
        <div className="flex items-center gap-3 flex-wrap animate-in fade-in slide-in-from-bottom-2 duration-500 fill-mode-both" style={{ animationDelay: '250ms' }}>
          <div className="relative flex-1 min-w-50 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1) }}
              placeholder="Search researches…"
              className="pl-9 h-9 bg-background border-border/50"
            />
          </div>

          <Separator orientation="vertical" className="h-6 bg-border/50" />

          {/* Workspace pills */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <Filter className="size-3.5 text-muted-foreground mr-1" />
            <button
              onClick={() => { setSelectedWorkspaceId(null); setCurrentPage(1) }}
              className={cn(
                "px-2.5 py-1 rounded-full text-xs font-medium transition-all",
                !selectedWorkspaceId
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              All
            </button>
            {workspaces.map((ws) => {
              const accent = getAccentClasses(ws.color)
              const isActive = selectedWorkspaceId === ws.id
              return (
                <Tooltip key={ws.id}>
                  <TooltipTrigger asChild>
                    <button
                      onClick={() => { setSelectedWorkspaceId(isActive ? null : ws.id); setCurrentPage(1) }}
                      className={cn(
                        "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all",
                        isActive
                          ? cn(accent.bg, accent.text, 'border', accent.border)
                          : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
                      )}
                    >
                      <span className={cn("size-2 rounded-full shrink-0", accent.dot)} />
                      <span className="hidden sm:inline truncate max-w-25">{ws.name}</span>
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>{ws.name} — {ws.researchCount} research{ws.researchCount !== 1 ? 'es' : ''}</TooltipContent>
                </Tooltip>
              )
            })}
          </div>

          <Separator orientation="vertical" className="h-6 bg-border/50" />

          <Select value={selectedStatus} onValueChange={(v) => { setSelectedStatus(v); setCurrentPage(1) }}>
            <SelectTrigger className="w-32.5 h-9 bg-background border-border/50 text-xs">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="in-progress">In Progress</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
            </SelectContent>
          </Select>

          <Select value={sortBy} onValueChange={(v) => setSortBy(v as SortOption)}>
            <SelectTrigger className="w-35 h-9 bg-background border-border/50 text-xs">
              <ArrowUpDown className="size-3 mr-1" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="latest">Latest First</SelectItem>
              <SelectItem value="oldest">Oldest First</SelectItem>
              <SelectItem value="name-az">Name A→Z</SelectItem>
            </SelectContent>
          </Select>

          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters} className="h-9 px-2 text-xs text-muted-foreground hover:text-foreground gap-1">
              <X className="size-3" />
              Clear
            </Button>
          )}
        </div>
      </div>

      {/* ── Content ─────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto">
        <div className="w-full max-w-7xl mx-auto px-8 py-5 pb-6 space-y-4">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-20 gap-4">
              <Loader2 className="size-8 text-primary animate-spin" />
              <p className="text-sm text-muted-foreground">Loading researches…</p>
            </div>
          ) : totalItems === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 gap-4 text-center animate-in fade-in duration-500">
              <div className="size-16 rounded-2xl bg-muted/50 border border-border/50 flex items-center justify-center">
                <FlaskConical className="size-7 text-muted-foreground/50" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-foreground">No researches found</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {hasActiveFilters ? 'Try adjusting your filters or search query.' : 'Start a new research to get going.'}
                </p>
              </div>
              {hasActiveFilters ? (
                <Button variant="outline" size="sm" onClick={clearFilters} className="gap-2 mt-2">
                  <X className="size-3.5" />Clear all filters
                </Button>
              ) : (
                <Button size="sm" className="gap-2 mt-2" onClick={() => navigate('/researches/new')}>
                  <Plus className="size-4" />New Research
                </Button>
              )}
            </div>
          ) : (
            Object.entries(paginatedGroups).map(([wsId, groupResearches], groupIdx) => {
              const ws = wsId === '__none__' ? undefined : getWorkspaceFor(wsId)
              const accent = getAccentClasses(ws?.color ?? 'purple-400')
              const isCollapsed = collapsedWorkspaces.has(wsId)
              const WsIcon = ws?.icon ?? FlaskConical
              const wsName = ws?.name ?? 'Unassigned'

              return (
                <div
                  key={wsId}
                  className="animate-in fade-in slide-in-from-bottom-3 duration-500 fill-mode-both"
                  style={{ animationDelay: `${groupIdx * 100}ms` }}
                >
                  <button
                    onClick={() => toggleWorkspaceCollapse(wsId)}
                    className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl transition-colors hover:bg-muted/50 group"
                  >
                    <span className={cn("size-2.5 rounded-full shrink-0", accent.dot)} />
                    <WsIcon className={cn("size-4 shrink-0", accent.text)} />
                    <span className={cn("text-sm font-semibold", accent.text)}>{wsName}</span>
                    <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-5">{groupResearches.length}</Badge>
                    <div className="flex-1" />
                    {isCollapsed
                      ? <ChevronRight className="size-4 text-muted-foreground group-hover:text-foreground transition-colors" />
                      : <ChevronDown  className="size-4 text-muted-foreground group-hover:text-foreground transition-colors" />
                    }
                  </button>

                  {!isCollapsed && (
                    <div className={cn(
                      "mt-1.5 mb-4",
                      viewMode === 'grid'
                        ? "grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 pl-4"
                        : "flex flex-col gap-2 pl-4"
                    )}>
                      {groupResearches.map((research, rIdx) =>
                        viewMode === 'grid'
                          ? <ResearchGridCard key={research.id} research={research} accent={accent} delay={rIdx * 50} onPreview={() => setPreviewResearch(research)} />
                          : <ResearchListCard key={research.id} research={research} accent={accent} delay={rIdx * 50} onPreview={() => setPreviewResearch(research)} />
                      )}
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>

        {/* ── Pagination ───────────────────────────────────────────── */}
        {!isLoading && totalItems > 0 && (
          <div className="sticky bottom-0 border-t border-border/30 bg-background/80 backdrop-blur-sm px-8 py-3">
            <div className="flex items-center justify-between max-w-7xl mx-auto">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>Showing {Math.min((currentPage - 1) * itemsPerPage + 1, totalItems)}–{Math.min(currentPage * itemsPerPage, totalItems)} of {totalItems}</span>
                <Separator orientation="vertical" className="h-4 bg-border/50" />
                <Select value={String(itemsPerPage)} onValueChange={(v) => { setItemsPerPage(Number(v)); setCurrentPage(1) }}>
                  <SelectTrigger className="w-20 h-7 text-xs bg-background border-border/50">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ITEMS_PER_PAGE_OPTIONS.map((n) => (
                      <SelectItem key={n} value={String(n)}>{n} / page</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center gap-1">
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0" disabled={currentPage <= 1} onClick={() => setCurrentPage((p) => p - 1)}>
                  <ChevronLeft className="size-4" />
                </Button>
                {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => i + 1).map((page) => (
                  <Button
                    key={page}
                    variant={currentPage === page ? 'secondary' : 'ghost'}
                    size="sm"
                    className={cn("h-8 w-8 p-0 text-xs", currentPage === page && "font-bold")}
                    onClick={() => setCurrentPage(page)}
                  >
                    {page}
                  </Button>
                ))}
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0" disabled={currentPage >= totalPages} onClick={() => setCurrentPage((p) => p + 1)}>
                  <ChevronRight className="size-4" />
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Preview Sheet ────────────────────────────────────────────── */}
      <Sheet open={!!previewResearch} onOpenChange={(open) => { if (!open) setPreviewResearch(null) }}>
        <SheetContent className="w-full sm:w-1/2 sm:max-w-none border-l border-border/50 bg-card/95 backdrop-blur-xl p-0 flex flex-col overflow-hidden">
          {previewResearch && (() => {
            const ws = getWorkspaceFor(previewResearch.workspaceId)
            const accent = getAccentClasses(ws?.color ?? 'purple-400')
            const statusCfg = STATUS_CONFIG[previewResearch.status]

            return (
              <>
                <div className="flex-1 overflow-y-auto px-8 pt-8 pb-32">
                  <SheetHeader className="space-y-4 p-0">
                    <div className="flex items-start gap-4">
                      <div className={cn("size-12 rounded-2xl border flex items-center justify-center shrink-0", accent.bg, accent.border)}>
                        <FlaskConical className={cn("size-5", accent.text)} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <SheetTitle className="text-xl font-bold pr-8">{previewResearch.title}</SheetTitle>
                        <SheetDescription className="text-sm mt-1">{previewResearch.summary}</SheetDescription>
                      </div>
                    </div>
                  </SheetHeader>

                  <div className="flex flex-wrap items-center gap-3 mt-5">
                    <span className={cn("text-xs font-medium px-2.5 py-1 rounded-full border", statusCfg.className)}>
                      {statusCfg.label}
                    </span>
                    {ws && (
                      <span className={cn("flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border", accent.bg, accent.text, accent.border)}>
                        <span className={cn("size-2 rounded-full", accent.dot)} />
                        {ws.name}
                      </span>
                    )}
                    <span className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Calendar className="size-3" />{previewResearch.createdAt}
                    </span>
                    <span className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Clock className="size-3" />{previewResearch.updatedAt}
                    </span>
                    {previewResearch.sourceCount > 0 && (
                      <span className="text-xs text-muted-foreground">
                        {previewResearch.sourceCount} source{previewResearch.sourceCount !== 1 ? 's' : ''}
                      </span>
                    )}
                  </div>

                  {previewResearch.artifacts ? (
                    <>
                      <Separator className="my-6 bg-border/50" />
                      <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">Research Artifact</h4>
                      <div className="rounded-2xl border border-border bg-background p-6 shadow-sm">
                        <Message from="assistant" className="max-w-none w-full">
                          <MessageContent className="max-w-none w-full bg-transparent p-0 text-base leading-relaxed">
                            <MessageResponse>{previewResearch.artifacts}</MessageResponse>
                          </MessageContent>
                        </Message>
                      </div>
                    </>
                  ) : (
                    <div className="mt-6 p-6 rounded-xl border border-border/50 bg-muted/20 text-center">
                      <FlaskConical className="size-8 text-muted-foreground/40 mx-auto mb-2" />
                      <p className="text-sm text-muted-foreground">No artifact generated yet.</p>
                    </div>
                  )}
                </div>

                <div className="shrink-0 p-6 border-t bg-background/50 backdrop-blur-xl flex items-center justify-between gap-4 absolute bottom-0 left-0 right-0">
                  <Button variant="ghost" className="text-muted-foreground hover:text-foreground" onClick={() => setPreviewResearch(null)}>
                    Close
                  </Button>
                  <Button className="gap-2 shadow-lg shadow-primary/20" onClick={() => navigate(`/researches/${previewResearch.id}`)}>
                    <Eye className="size-4" />
                    Open Full Research
                  </Button>
                </div>
              </>
            )
          })()}
        </SheetContent>
      </Sheet>
    </div>
  )
}

// ─── Grid Card ────────────────────────────────────────────────────────────────
function ResearchGridCard({
  research, accent, delay, onPreview,
}: {
  research: Research
  accent: ReturnType<typeof getAccentClasses>
  delay: number
  onPreview: () => void
}) {
  const statusCfg = STATUS_CONFIG[research.status]
  return (
    <div
      className={cn(
        "group relative rounded-xl border border-border/50 bg-card hover:bg-muted/30 transition-all cursor-pointer overflow-hidden border-l-[3px]",
        accent.cardBorder,
        "animate-in fade-in slide-in-from-bottom-2 duration-300 fill-mode-both"
      )}
      style={{ animationDelay: `${delay}ms` }}
      onClick={onPreview}
    >
      <div className="p-4 space-y-3">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-sm font-semibold text-foreground line-clamp-1 group-hover:text-primary transition-colors flex-1">
            {research.title}
          </h3>
          <span className={cn("text-[10px] font-medium px-2 py-0.5 rounded-full border shrink-0", statusCfg.className)}>
            {statusCfg.label}
          </span>
        </div>

        <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">{research.summary}</p>

        {research.sourceCount > 0 && (
          <p className="text-[10px] text-muted-foreground/70">
            {research.sourceCount} source{research.sourceCount !== 1 ? 's' : ''}
          </p>
        )}

        <Separator className="bg-border/30" />

        <div className="flex items-center justify-between text-[10px] text-muted-foreground">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1"><Calendar className="size-3" />{research.createdAt}</span>
            <span className="flex items-center gap-1"><Clock className="size-3" />{research.updatedAt}</span>
          </div>
          {research.chatAccess && (
            <Tooltip>
              <TooltipTrigger asChild>
                <span className={cn("text-[9px] font-medium", accent.text)}>Chat</span>
              </TooltipTrigger>
              <TooltipContent>Chat access enabled</TooltipContent>
            </Tooltip>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── List Card ────────────────────────────────────────────────────────────────
function ResearchListCard({
  research, accent, delay, onPreview,
}: {
  research: Research
  accent: ReturnType<typeof getAccentClasses>
  delay: number
  onPreview: () => void
}) {
  const statusCfg = STATUS_CONFIG[research.status]
  return (
    <div
      className={cn(
        "group flex items-center gap-4 px-4 py-3 rounded-xl border border-border/50 bg-card hover:bg-muted/30 transition-all cursor-pointer overflow-hidden border-l-[3px]",
        accent.cardBorder,
        "animate-in fade-in slide-in-from-bottom-2 duration-300 fill-mode-both"
      )}
      style={{ animationDelay: `${delay}ms` }}
      onClick={onPreview}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-foreground truncate group-hover:text-primary transition-colors">
            {research.title}
          </h3>
          <span className={cn("text-[10px] font-medium px-2 py-0.5 rounded-full border shrink-0", statusCfg.className)}>
            {statusCfg.label}
          </span>
        </div>
        <p className="text-xs text-muted-foreground truncate mt-0.5">{research.summary}</p>
      </div>

      {research.sourceCount > 0 && (
        <span className="hidden md:block text-[10px] text-muted-foreground shrink-0">
          {research.sourceCount} src
        </span>
      )}

      <div className="hidden lg:flex items-center gap-1 text-[10px] text-muted-foreground shrink-0">
        <Clock className="size-3" />{research.updatedAt}
      </div>

      <ChevronRight className="size-4 text-muted-foreground/50 group-hover:text-foreground transition-colors shrink-0" />
    </div>
  )
}

export default AllResearches
