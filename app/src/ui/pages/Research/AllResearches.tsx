import { useState, useMemo } from 'react'
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
  Globe,
  Image,
  Video,
  Music,
  FileText,
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
  Database,
  ExternalLink,
  LucideIcon,
  ChevronLeft,
  Filter,
  LayoutGrid,
  List,
} from 'lucide-react'

// ─── Accent Color System (matches ViewWorkspace.tsx) ──────────────────────────
const getAccentClasses = (color: string) => {
  const classMap: Record<string, {
    text: string
    bg: string
    border: string
    dot: string
    cardBorder: string
    strip: string
  }> = {
    'purple-400': {
      text: 'text-purple-400',
      bg: 'bg-purple-400/10',
      border: 'border-purple-400/30',
      dot: 'bg-purple-400',
      cardBorder: 'border-l-purple-400',
      strip: 'bg-purple-400',
    },
    'blue-400': {
      text: 'text-blue-400',
      bg: 'bg-blue-400/10',
      border: 'border-blue-400/30',
      dot: 'bg-blue-400',
      cardBorder: 'border-l-blue-400',
      strip: 'bg-blue-400',
    },
    'green-400': {
      text: 'text-green-400',
      bg: 'bg-green-400/10',
      border: 'border-green-400/30',
      dot: 'bg-green-400',
      cardBorder: 'border-l-green-400',
      strip: 'bg-green-400',
    },
    'pink-400': {
      text: 'text-pink-400',
      bg: 'bg-pink-400/10',
      border: 'border-pink-400/30',
      dot: 'bg-pink-400',
      cardBorder: 'border-l-pink-400',
      strip: 'bg-pink-400',
    },
    'orange-400': {
      text: 'text-orange-400',
      bg: 'bg-orange-400/10',
      border: 'border-orange-400/30',
      dot: 'bg-orange-400',
      cardBorder: 'border-l-orange-400',
      strip: 'bg-orange-400',
    },
  }
  return classMap[color] || classMap['purple-400']
}

// ─── Types ────────────────────────────────────────────────────────────────────
interface SourceCounts {
  web: number
  images: number
  videos: number
  audio: number
  documents: number
}

interface Research {
  id: string
  title: string
  summary: string
  status: 'completed' | 'in-progress' | 'failed'
  workspaceId: string
  createdAt: string
  updatedAt: string
  sources: SourceCounts
  bucketName: string | null
  artifactMarkdown: string
}

interface Workspace {
  id: string
  name: string
  icon: LucideIcon
  color: string
  researchCount: number
}

// ─── Dummy Data ───────────────────────────────────────────────────────────────
const mockWorkspaces: Workspace[] = [
  { id: 'ws-1', name: 'Market Analysis 2024', icon: TrendingUp, color: 'blue-400', researchCount: 4 },
  { id: 'ws-2', name: 'Competitor Tracking', icon: Users, color: 'purple-400', researchCount: 3 },
  { id: 'ws-3', name: 'Academic Research', icon: GraduationCap, color: 'green-400', researchCount: 2 },
  { id: 'ws-4', name: 'Product Strategy', icon: Briefcase, color: 'pink-400', researchCount: 2 },
]

const ARTIFACT_SAMPLE = `# 🌐 Research Report: AI Market Trends Q1 2024

A comprehensive analysis of the AI market landscape heading into 2024, synthesized from 42 verified sources across research papers, industry reports, and expert interviews.

---

## 📊 Executive Summary

The global AI market is projected to reach **$407 billion by 2027**, growing at a CAGR of 36.2%. Key drivers include enterprise adoption of generative AI, regulatory frameworks, and advances in multi-modal models.

### Key Findings
- **Enterprise AI Adoption** has surged by 72% year-over-year
- **LLM costs** decreased by 90% since GPT-3 launch
- **Open-source models** now match proprietary performance on 60% of benchmarks

---

## 🏢 Competitive Landscape

| Company | Market Share | Key Product | YoY Growth |
|---------|-------------|-------------|------------|
| OpenAI | 31.2% | GPT-4 Turbo | +145% |
| Google | 24.8% | Gemini Pro | +89% |
| Anthropic | 12.1% | Claude 3 | +312% |
| Meta | 8.4% | Llama 3 | +67% |
| Mistral | 5.2% | Mixtral 8x7B | +520% |

---

## 📈 Investment Trends

Private funding in AI startups reached **$52.8 billion** in 2024, with infrastructure and tooling companies receiving the largest share.

### Funding Distribution
- **Infrastructure & Compute:** 34%
- **Enterprise Applications:** 28%
- **Healthcare AI:** 15%
- **Autonomous Vehicles:** 12%
- **Other Verticals:** 11%

---

## 🔮 Predictions for 2025

1. **Multi-modal AI** will become the default for enterprise deployments
2. **AI regulation** in the EU will standardize compliance requirements
3. **On-device AI** will gain 40% market share in mobile applications
4. **AI agents** will handle 30% of routine business processes

---

## 📚 Sources & References

This report synthesized information from:
- **Research Papers:** 12 peer-reviewed papers from arXiv, Nature, and Science
- **Industry Reports:** Gartner, McKinsey, Forrester, CB Insights
- **Expert Interviews:** 8 CTO-level conversations
- **Financial Filings:** SEC filings from top 10 AI companies
- **News Sources:** TechCrunch, The Verge, Wired, MIT Technology Review

---

*Report generated by Deep Researcher AI Engine using the Comprehensive template.*
*Last verified: February 14, 2026*`

const mockResearches: Research[] = [
  {
    id: 'r-1',
    title: 'AI Market Trends Q1 2024',
    summary: 'Comprehensive analysis of the AI market landscape, key players, investment trends, and 2025 predictions. Covers enterprise adoption rates and open-source model benchmarks.',
    status: 'completed',
    workspaceId: 'ws-1',
    createdAt: 'Feb 12, 2026',
    updatedAt: '2 hours ago',
    sources: { web: 18, images: 5, videos: 2, audio: 0, documents: 8 },
    bucketName: 'ai-market-data',
    artifactMarkdown: ARTIFACT_SAMPLE,
  },
  {
    id: 'r-2',
    title: 'SaaS Pricing Models Deep Dive',
    summary: 'Research into subscription-based pricing strategies, usage-based billing, and hybrid models used by leading SaaS companies worldwide.',
    status: 'completed',
    workspaceId: 'ws-1',
    createdAt: 'Feb 8, 2026',
    updatedAt: '3 days ago',
    sources: { web: 24, images: 3, videos: 1, audio: 0, documents: 12 },
    bucketName: 'saas-pricing',
    artifactMarkdown: ARTIFACT_SAMPLE,
  },
  {
    id: 'r-3',
    title: 'Emerging Tech Markets 2026',
    summary: 'Analysis of AR/VR, quantum computing, and biotech markets with growth projections and key players.',
    status: 'in-progress',
    workspaceId: 'ws-1',
    createdAt: 'Feb 14, 2026',
    updatedAt: '10 mins ago',
    sources: { web: 14, images: 7, videos: 4, audio: 1, documents: 3 },
    bucketName: null,
    artifactMarkdown: ARTIFACT_SAMPLE,
  },
  {
    id: 'r-4',
    title: 'Cloud Infrastructure Cost Analysis',
    summary: 'Comparative analysis of AWS, GCP, and Azure pricing across compute, storage, and networking tiers.',
    status: 'completed',
    workspaceId: 'ws-1',
    createdAt: 'Jan 28, 2026',
    updatedAt: '2 weeks ago',
    sources: { web: 9, images: 0, videos: 0, audio: 0, documents: 6 },
    bucketName: 'cloud-costs',
    artifactMarkdown: ARTIFACT_SAMPLE,
  },
  {
    id: 'r-5',
    title: 'Competitor Product Feature Matrix',
    summary: 'Detailed feature-by-feature comparison of top 8 competitors in the research automation space.',
    status: 'completed',
    workspaceId: 'ws-2',
    createdAt: 'Feb 10, 2026',
    updatedAt: '1 day ago',
    sources: { web: 32, images: 12, videos: 0, audio: 0, documents: 5 },
    bucketName: 'competitor-data',
    artifactMarkdown: ARTIFACT_SAMPLE,
  },
  {
    id: 'r-6',
    title: 'Competitor Pricing Intelligence',
    summary: 'Ongoing tracking of competitor pricing changes, new tier introductions, and discount strategies.',
    status: 'in-progress',
    workspaceId: 'ws-2',
    createdAt: 'Feb 6, 2026',
    updatedAt: '5 hours ago',
    sources: { web: 15, images: 2, videos: 3, audio: 0, documents: 4 },
    bucketName: 'pricing-intel',
    artifactMarkdown: ARTIFACT_SAMPLE,
  },
  {
    id: 'r-7',
    title: 'UX Benchmarking Study',
    summary: 'Usability analysis across competitor products measuring task completion rates, error rates, and user satisfaction scores.',
    status: 'failed',
    workspaceId: 'ws-2',
    createdAt: 'Feb 1, 2026',
    updatedAt: '1 week ago',
    sources: { web: 8, images: 6, videos: 2, audio: 3, documents: 1 },
    bucketName: null,
    artifactMarkdown: ARTIFACT_SAMPLE,
  },
  {
    id: 'r-8',
    title: 'Neural Architecture Search Survey',
    summary: 'Literature review of NAS methods including evolutionary approaches, reinforcement learning, and differentiable architecture search.',
    status: 'completed',
    workspaceId: 'ws-3',
    createdAt: 'Feb 5, 2026',
    updatedAt: '4 days ago',
    sources: { web: 6, images: 4, videos: 1, audio: 2, documents: 22 },
    bucketName: 'nas-papers',
    artifactMarkdown: ARTIFACT_SAMPLE,
  },
  {
    id: 'r-9',
    title: 'Transformer Efficiency Methods',
    summary: 'Survey of efficient transformer architectures covering sparse attention, linear attention, and distillation techniques.',
    status: 'in-progress',
    workspaceId: 'ws-3',
    createdAt: 'Feb 13, 2026',
    updatedAt: '30 mins ago',
    sources: { web: 11, images: 3, videos: 5, audio: 0, documents: 18 },
    bucketName: 'transformer-research',
    artifactMarkdown: ARTIFACT_SAMPLE,
  },
  {
    id: 'r-10',
    title: 'Go-To-Market Strategy Analysis',
    summary: 'Research into GTM playbooks from PLG, sales-led, and hybrid growth companies. Includes case studies from Figma, Notion, and Slack.',
    status: 'completed',
    workspaceId: 'ws-4',
    createdAt: 'Feb 9, 2026',
    updatedAt: '2 days ago',
    sources: { web: 20, images: 8, videos: 6, audio: 1, documents: 7 },
    bucketName: 'gtm-playbooks',
    artifactMarkdown: ARTIFACT_SAMPLE,
  },
  {
    id: 'r-11',
    title: 'Customer Interview Synthesis',
    summary: 'Thematic analysis of 25 customer discovery interviews, covering pain points, desired outcomes, and willingness to pay.',
    status: 'completed',
    workspaceId: 'ws-4',
    createdAt: 'Jan 22, 2026',
    updatedAt: '3 weeks ago',
    sources: { web: 2, images: 0, videos: 0, audio: 25, documents: 3 },
    bucketName: 'interviews',
    artifactMarkdown: ARTIFACT_SAMPLE,
  },
]

// ─── Source Type Icons ────────────────────────────────────────────────────────
const SOURCE_ICONS: { key: keyof SourceCounts; icon: LucideIcon; label: string }[] = [
  { key: 'web', icon: Globe, label: 'Web Sources' },
  { key: 'images', icon: Image, label: 'Images' },
  { key: 'videos', icon: Video, label: 'Videos' },
  { key: 'audio', icon: Music, label: 'Audio' },
  { key: 'documents', icon: FileText, label: 'Documents' },
]

const STATUS_CONFIG = {
  'completed': { label: 'Completed', className: 'bg-emerald-500/15 text-emerald-500 border-emerald-500/20' },
  'in-progress': { label: 'In Progress', className: 'bg-amber-500/15 text-amber-500 border-amber-500/20' },
  'failed': { label: 'Failed', className: 'bg-red-500/15 text-red-500 border-red-500/20' },
}

type SortOption = 'latest' | 'oldest' | 'name-az' | 'most-sources'
type ViewMode = 'grid' | 'list'

const ITEMS_PER_PAGE_OPTIONS = [6, 12, 24]

// ─── Component ────────────────────────────────────────────────────────────────
const AllResearches = () => {
  // State
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedWorkspace, setSelectedWorkspace] = useState<string | null>(null)
  const [selectedStatus, setSelectedStatus] = useState<string>('all')
  const [selectedSourceType, setSelectedSourceType] = useState<string>('all')
  const [sortBy, setSortBy] = useState<SortOption>('latest')
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [currentPage, setCurrentPage] = useState(1)
  const [itemsPerPage, setItemsPerPage] = useState(12)
  const [collapsedWorkspaces, setCollapsedWorkspaces] = useState<Set<string>>(new Set())
  const [previewResearch, setPreviewResearch] = useState<Research | null>(null)

  // Filtering & sorting
  const filteredResearches = useMemo(() => {
    let results = [...mockResearches]

    // Search
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      results = results.filter(r =>
        r.title.toLowerCase().includes(q) ||
        r.summary.toLowerCase().includes(q)
      )
    }

    // Workspace filter
    if (selectedWorkspace) {
      results = results.filter(r => r.workspaceId === selectedWorkspace)
    }

    // Status filter
    if (selectedStatus !== 'all') {
      results = results.filter(r => r.status === selectedStatus)
    }

    // Source type filter
    if (selectedSourceType !== 'all') {
      results = results.filter(r => r.sources[selectedSourceType as keyof SourceCounts] > 0)
    }

    // Sort
    switch (sortBy) {
      case 'oldest':
        results.reverse()
        break
      case 'name-az':
        results.sort((a, b) => a.title.localeCompare(b.title))
        break
      case 'most-sources':
        results.sort((a, b) => {
          const totalA = Object.values(a.sources).reduce((s, v) => s + v, 0)
          const totalB = Object.values(b.sources).reduce((s, v) => s + v, 0)
          return totalB - totalA
        })
        break
      // 'latest' is already the default order
    }

    return results
  }, [searchQuery, selectedWorkspace, selectedStatus, selectedSourceType, sortBy])

  // Group by workspace
  const groupedResearches = useMemo(() => {
    const groups: Record<string, Research[]> = {}
    filteredResearches.forEach(r => {
      if (!groups[r.workspaceId]) groups[r.workspaceId] = []
      groups[r.workspaceId].push(r)
    })
    return groups
  }, [filteredResearches])

  // Pagination
  const totalItems = filteredResearches.length
  const totalPages = Math.max(1, Math.ceil(totalItems / itemsPerPage))
  const paginatedResearches = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage
    return filteredResearches.slice(start, start + itemsPerPage)
  }, [filteredResearches, currentPage, itemsPerPage])

  // Paginated groups
  const paginatedGroups = useMemo(() => {
    const groups: Record<string, Research[]> = {}
    paginatedResearches.forEach(r => {
      if (!groups[r.workspaceId]) groups[r.workspaceId] = []
      groups[r.workspaceId].push(r)
    })
    return groups
  }, [paginatedResearches])

  const toggleWorkspaceCollapse = (wsId: string) => {
    setCollapsedWorkspaces(prev => {
      const next = new Set(prev)
      if (next.has(wsId)) next.delete(wsId)
      else next.add(wsId)
      return next
    })
  }

  const clearFilters = () => {
    setSearchQuery('')
    setSelectedWorkspace(null)
    setSelectedStatus('all')
    setSelectedSourceType('all')
    setSortBy('latest')
    setCurrentPage(1)
  }

  const hasActiveFilters = searchQuery || selectedWorkspace || selectedStatus !== 'all' || selectedSourceType !== 'all' || sortBy !== 'latest'

  const getTotalSources = (s: SourceCounts) => Object.values(s).reduce((a, b) => a + b, 0)

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
                <h1
                  className="text-xl font-semibold tracking-tight animate-in fade-in slide-in-from-bottom-2 duration-500 fill-mode-both"
                  style={{ animationDelay: '100ms' }}
                >
                  All Researches
                </h1>
                <p
                  className="text-sm text-muted-foreground animate-in fade-in slide-in-from-bottom-2 duration-500 fill-mode-both"
                  style={{ animationDelay: '150ms' }}
                >
                  {totalItems} research{totalItems !== 1 ? 'es' : ''} across {Object.keys(groupedResearches).length} workspace{Object.keys(groupedResearches).length !== 1 ? 's' : ''}
                </p>
              </div>
            </div>

            <div
              className="flex items-center gap-2 animate-in fade-in slide-in-from-right-4 duration-500 fill-mode-both"
              style={{ animationDelay: '200ms' }}
            >
              {/* View mode toggle */}
              <div className="flex items-center border border-border/50 rounded-lg p-0.5 bg-muted/30">
                <Button
                  variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
                  size="sm"
                  className="h-7 w-7 p-0"
                  onClick={() => setViewMode('grid')}
                >
                  <LayoutGrid className="size-3.5" />
                </Button>
                <Button
                  variant={viewMode === 'list' ? 'secondary' : 'ghost'}
                  size="sm"
                  className="h-7 w-7 p-0"
                  onClick={() => setViewMode('list')}
                >
                  <List className="size-3.5" />
                </Button>
              </div>
              <Button size="sm" className="gap-2">
                <Plus className="size-4" />
                New Research
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* ── Filters ─────────────────────────────────────────────────── */}
      <div className="shrink-0 px-8 py-3 border-b border-border/30 bg-background/30 backdrop-blur-sm">
        <div
          className="flex items-center gap-3 flex-wrap animate-in fade-in slide-in-from-bottom-2 duration-500 fill-mode-both"
          style={{ animationDelay: '250ms' }}
        >
          {/* Search */}
          <div className="relative flex-1 min-w-[200px] max-w-sm">
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
          <div className="flex items-center gap-1.5">
            <Filter className="size-3.5 text-muted-foreground mr-1" />
            <button
              onClick={() => { setSelectedWorkspace(null); setCurrentPage(1) }}
              className={cn(
                "px-2.5 py-1 rounded-full text-xs font-medium transition-all",
                !selectedWorkspace
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              All
            </button>
            {mockWorkspaces.map(ws => {
              const accent = getAccentClasses(ws.color)
              const isActive = selectedWorkspace === ws.id
              return (
                <Tooltip key={ws.id}>
                  <TooltipTrigger asChild>
                    <button
                      onClick={() => { setSelectedWorkspace(isActive ? null : ws.id); setCurrentPage(1) }}
                      className={cn(
                        "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all",
                        isActive
                          ? cn(accent.bg, accent.text, 'border', accent.border)
                          : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
                      )}
                    >
                      <span className={cn("size-2 rounded-full shrink-0", accent.dot)} />
                      <span className="hidden sm:inline truncate max-w-[100px]">{ws.name}</span>
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>{ws.name} — {ws.researchCount} researches</TooltipContent>
                </Tooltip>
              )
            })}
          </div>

          <Separator orientation="vertical" className="h-6 bg-border/50" />

          {/* Status filter */}
          <Select value={selectedStatus} onValueChange={(v) => { setSelectedStatus(v); setCurrentPage(1) }}>
            <SelectTrigger className="w-[130px] h-9 bg-background border-border/50 text-xs">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="in-progress">In Progress</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
            </SelectContent>
          </Select>

          {/* Source type filter */}
          <Select value={selectedSourceType} onValueChange={(v) => { setSelectedSourceType(v); setCurrentPage(1) }}>
            <SelectTrigger className="w-[130px] h-9 bg-background border-border/50 text-xs">
              <SelectValue placeholder="Source Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Sources</SelectItem>
              <SelectItem value="web">Web</SelectItem>
              <SelectItem value="images">Images</SelectItem>
              <SelectItem value="videos">Videos</SelectItem>
              <SelectItem value="audio">Audio</SelectItem>
              <SelectItem value="documents">Documents</SelectItem>
            </SelectContent>
          </Select>

          {/* Sort */}
          <Select value={sortBy} onValueChange={(v) => setSortBy(v as SortOption)}>
            <SelectTrigger className="w-[140px] h-9 bg-background border-border/50 text-xs">
              <ArrowUpDown className="size-3 mr-1" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="latest">Latest First</SelectItem>
              <SelectItem value="oldest">Oldest First</SelectItem>
              <SelectItem value="name-az">Name A→Z</SelectItem>
              <SelectItem value="most-sources">Most Sources</SelectItem>
            </SelectContent>
          </Select>

          {/* Clear filters */}
          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearFilters}
              className="h-9 px-2 text-xs text-muted-foreground hover:text-foreground gap-1"
            >
              <X className="size-3" />
              Clear
            </Button>
          )}
        </div>
      </div>

      {/* ── Content ─────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto">
        <div className="w-full max-w-7xl mx-auto px-8 py-5 pb-6 space-y-4">
          {totalItems === 0 ? (
            /* Empty state */
            <div className="flex flex-col items-center justify-center py-20 gap-4 text-center animate-in fade-in duration-500">
              <div className="size-16 rounded-2xl bg-muted/50 border border-border/50 flex items-center justify-center">
                <FlaskConical className="size-7 text-muted-foreground/50" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-foreground">No researches found</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {hasActiveFilters
                    ? 'Try adjusting your filters or search query.'
                    : 'Start a new research to get going.'}
                </p>
              </div>
              {hasActiveFilters && (
                <Button variant="outline" size="sm" onClick={clearFilters} className="gap-2 mt-2">
                  <X className="size-3.5" />
                  Clear all filters
                </Button>
              )}
            </div>
          ) : (
            /* Workspace Groups */
            Object.entries(paginatedGroups).map(([wsId, researches], groupIdx) => {
              const ws = mockWorkspaces.find(w => w.id === wsId)
              if (!ws) return null
              const accent = getAccentClasses(ws.color)
              const isCollapsed = collapsedWorkspaces.has(wsId)
              const WsIcon = ws.icon

              return (
                <div
                  key={wsId}
                  className="animate-in fade-in slide-in-from-bottom-3 duration-500 fill-mode-both"
                  style={{ animationDelay: `${groupIdx * 100}ms` }}
                >
                  {/* Workspace group header */}
                  <button
                    onClick={() => toggleWorkspaceCollapse(wsId)}
                    className={cn(
                      "w-full flex items-center gap-3 px-4 py-2.5 rounded-xl transition-colors",
                      "hover:bg-muted/50 group"
                    )}
                  >
                    <span className={cn("size-2.5 rounded-full shrink-0", accent.dot)} />
                    <WsIcon className={cn("size-4 shrink-0", accent.text)} />
                    <span className={cn("text-sm font-semibold", accent.text)}>{ws.name}</span>
                    <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-5">
                      {researches.length}
                    </Badge>
                    <div className="flex-1" />
                    {isCollapsed
                      ? <ChevronRight className="size-4 text-muted-foreground group-hover:text-foreground transition-colors" />
                      : <ChevronDown className="size-4 text-muted-foreground group-hover:text-foreground transition-colors" />
                    }
                  </button>

                  {/* Research cards */}
                  {!isCollapsed && (
                    <div className={cn(
                      "mt-1.5 mb-4",
                      viewMode === 'grid'
                        ? "grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 pl-4"
                        : "flex flex-col gap-2 pl-4"
                    )}>
                      {researches.map((research, rIdx) => (
                        viewMode === 'grid'
                          ? <ResearchGridCard
                            key={research.id}
                            research={research}
                            accent={accent}
                            delay={rIdx * 50}
                            onPreview={() => setPreviewResearch(research)}
                          />
                          : <ResearchListCard
                            key={research.id}
                            research={research}
                            accent={accent}
                            delay={rIdx * 50}
                            onPreview={() => setPreviewResearch(research)}
                          />
                      ))}
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>

        {/* ── Pagination ───────────────────────────────────────────── */}
        {totalItems > 0 && (
          <div className="sticky bottom-0 border-t border-border/30 bg-background/80 backdrop-blur-sm px-8 py-3">
            <div className="flex items-center justify-between max-w-7xl mx-auto">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>Showing {Math.min((currentPage - 1) * itemsPerPage + 1, totalItems)}–{Math.min(currentPage * itemsPerPage, totalItems)} of {totalItems}</span>
                <Separator orientation="vertical" className="h-4 bg-border/50" />
                <Select value={String(itemsPerPage)} onValueChange={(v) => { setItemsPerPage(Number(v)); setCurrentPage(1) }}>
                  <SelectTrigger className="w-[80px] h-7 text-xs bg-background border-border/50">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ITEMS_PER_PAGE_OPTIONS.map(n => (
                      <SelectItem key={n} value={String(n)}>{n} / page</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  disabled={currentPage <= 1}
                  onClick={() => setCurrentPage(p => p - 1)}
                >
                  <ChevronLeft className="size-4" />
                </Button>
                {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
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
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  disabled={currentPage >= totalPages}
                  onClick={() => setCurrentPage(p => p + 1)}
                >
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
            const ws = mockWorkspaces.find(w => w.id === previewResearch.workspaceId)
            const accent = ws ? getAccentClasses(ws.color) : getAccentClasses('purple-400')
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
                        <SheetTitle className="text-xl font-bold pr-8">
                          {previewResearch.title}
                        </SheetTitle>
                        <SheetDescription className="text-sm mt-1">
                          {previewResearch.summary}
                        </SheetDescription>
                      </div>
                    </div>
                  </SheetHeader>

                  {/* Meta row */}
                  <div className="flex flex-wrap items-center gap-3 mt-5">
                    {/* Status */}
                    <span className={cn("text-xs font-medium px-2.5 py-1 rounded-full border", statusCfg.className)}>
                      {statusCfg.label}
                    </span>

                    {/* Workspace */}
                    {ws && (
                      <span className={cn("flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border", accent.bg, accent.text, accent.border)}>
                        <span className={cn("size-2 rounded-full", accent.dot)} />
                        {ws.name}
                      </span>
                    )}

                    {/* Dates */}
                    <span className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Calendar className="size-3" />
                      {previewResearch.createdAt}
                    </span>
                    <span className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Clock className="size-3" />
                      {previewResearch.updatedAt}
                    </span>
                  </div>

                  {/* Sources summary */}
                  <div className="mt-5 p-4 rounded-xl bg-muted/30 border border-border/50">
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Sources ({getTotalSources(previewResearch.sources)})</h4>
                    <div className="flex flex-wrap gap-4">
                      {SOURCE_ICONS.map(({ key, icon: Icon, label }) => {
                        const count = previewResearch.sources[key]
                        if (count === 0) return null
                        return (
                          <div key={key} className="flex items-center gap-2 text-sm">
                            <Icon className="size-4 text-muted-foreground" />
                            <span className="font-medium">{count}</span>
                            <span className="text-muted-foreground text-xs">{label}</span>
                          </div>
                        )
                      })}
                    </div>
                  </div>

                  {/* Bucket info */}
                  {previewResearch.bucketName && (
                    <div className="mt-3 flex items-center gap-2 px-4 py-2.5 rounded-xl bg-muted/20 border border-border/50 text-sm">
                      <Database className="size-4 text-muted-foreground" />
                      <span className="text-muted-foreground">Connected Bucket:</span>
                      <span className="font-medium text-foreground">{previewResearch.bucketName}</span>
                      <ExternalLink className="size-3 text-muted-foreground ml-auto cursor-pointer hover:text-foreground transition-colors" />
                    </div>
                  )}

                  {/* Artifact preview */}
                  <Separator className="my-6 bg-border/50" />
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">Research Artifact</h4>
                  <div className="rounded-2xl border border-border bg-background p-6 shadow-sm">
                    <Message from="assistant" className="max-w-none w-full">
                      <MessageContent className="max-w-none w-full bg-transparent p-0 text-base leading-relaxed">
                        <MessageResponse>
                          {previewResearch.artifactMarkdown}
                        </MessageResponse>
                      </MessageContent>
                    </Message>
                  </div>
                </div>

                {/* Sheet footer */}
                <div className="shrink-0 p-6 border-t bg-background/50 backdrop-blur-xl flex items-center justify-between gap-4 absolute bottom-0 left-0 right-0">
                  <Button
                    variant="ghost"
                    className="text-muted-foreground hover:text-foreground"
                    onClick={() => setPreviewResearch(null)}
                  >
                    Close
                  </Button>
                  <Button className="gap-2 shadow-lg shadow-primary/20">
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
  research,
  accent,
  delay,
  onPreview,
}: {
  research: Research
  accent: ReturnType<typeof getAccentClasses>
  delay: number
  onPreview: () => void
}) {
  const statusCfg = STATUS_CONFIG[research.status]
  const totalSources = Object.values(research.sources).reduce((a, b) => a + b, 0)

  return (
    <div
      className={cn(
        "group relative rounded-xl border border-border/50 bg-card hover:bg-muted/30 transition-all cursor-pointer overflow-hidden",
        "border-l-[3px]",
        accent.cardBorder,
        "animate-in fade-in slide-in-from-bottom-2 duration-300 fill-mode-both"
      )}
      style={{ animationDelay: `${delay}ms` }}
      onClick={onPreview}
    >
      <div className="p-4 space-y-3">
        {/* Title + Status */}
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-sm font-semibold text-foreground line-clamp-1 group-hover:text-primary transition-colors flex-1">
            {research.title}
          </h3>
          <span className={cn("text-[10px] font-medium px-2 py-0.5 rounded-full border shrink-0", statusCfg.className)}>
            {statusCfg.label}
          </span>
        </div>

        {/* Summary */}
        <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
          {research.summary}
        </p>

        {/* Source indicators */}
        <div className="flex items-center gap-3">
          {SOURCE_ICONS.map(({ key, icon: Icon, label }) => {
            const count = research.sources[key]
            if (count === 0) return null
            return (
              <Tooltip key={key}>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-1 text-muted-foreground">
                    <Icon className="size-3" />
                    <span className="text-[10px] font-medium">{count}</span>
                  </div>
                </TooltipTrigger>
                <TooltipContent>{count} {label}</TooltipContent>
              </Tooltip>
            )
          })}
          <div className="flex-1" />
          <span className="text-[10px] text-muted-foreground/60">{totalSources} total</span>
        </div>

        <Separator className="bg-border/30" />

        {/* Footer */}
        <div className="flex items-center justify-between text-[10px] text-muted-foreground">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <Calendar className="size-3" />
              {research.createdAt}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="size-3" />
              {research.updatedAt}
            </span>
          </div>
          {research.bucketName && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Database className={cn("size-3.5", accent.text)} />
              </TooltipTrigger>
              <TooltipContent>Bucket: {research.bucketName}</TooltipContent>
            </Tooltip>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── List Card ────────────────────────────────────────────────────────────────
function ResearchListCard({
  research,
  accent,
  delay,
  onPreview,
}: {
  research: Research
  accent: ReturnType<typeof getAccentClasses>
  delay: number
  onPreview: () => void
}) {
  const statusCfg = STATUS_CONFIG[research.status]
  const totalSources = Object.values(research.sources).reduce((a, b) => a + b, 0)

  return (
    <div
      className={cn(
        "group flex items-center gap-4 px-4 py-3 rounded-xl border border-border/50 bg-card hover:bg-muted/30 transition-all cursor-pointer overflow-hidden",
        "border-l-[3px]",
        accent.cardBorder,
        "animate-in fade-in slide-in-from-bottom-2 duration-300 fill-mode-both"
      )}
      style={{ animationDelay: `${delay}ms` }}
      onClick={onPreview}
    >
      {/* Title */}
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

      {/* Sources */}
      <div className="hidden md:flex items-center gap-2.5 shrink-0">
        {SOURCE_ICONS.map(({ key, icon: Icon }) => {
          const count = research.sources[key]
          if (count === 0) return null
          return (
            <div key={key} className="flex items-center gap-0.5 text-muted-foreground">
              <Icon className="size-3" />
              <span className="text-[10px] font-medium">{count}</span>
            </div>
          )
        })}
        <span className="text-[10px] text-muted-foreground/50 ml-1">{totalSources}</span>
      </div>

      {/* Date */}
      <div className="hidden lg:flex items-center gap-1 text-[10px] text-muted-foreground shrink-0">
        <Clock className="size-3" />
        {research.updatedAt}
      </div>

      {/* Bucket */}
      {research.bucketName && (
        <Tooltip>
          <TooltipTrigger asChild>
            <Database className={cn("size-3.5 shrink-0", accent.text)} />
          </TooltipTrigger>
          <TooltipContent>Bucket: {research.bucketName}</TooltipContent>
        </Tooltip>
      )}

      {/* Preview arrow */}
      <ChevronRight className="size-4 text-muted-foreground/50 group-hover:text-foreground transition-colors shrink-0" />
    </div>
  )
}

export default AllResearches