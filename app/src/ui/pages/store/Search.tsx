import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import {
  Search as SearchIcon,
  Sparkles,
  FlaskConical,
  MessageSquare,
  Briefcase,
  Files,
  Database,
  Clock,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Copy,
  X,
  History,
  ArrowRight,
  Loader2
} from 'lucide-react'

// ============================================================================
// Types
// ============================================================================

interface SearchResult {
  id: string
  title: string
  description: string
  category: CategoryId
  timestamp: Date
  metadata: string
  url: string
  relevance: number
}

type CategoryId = 'researches' | 'chats' | 'workspaces' | 'assets' | 'databases' | 'history'

interface CategoryConfig {
  id: CategoryId
  label: string
  icon: React.ElementType
  color: string
  bgColor: string
}

// ============================================================================
// Configuration
// ============================================================================

const CATEGORIES: CategoryConfig[] = [
  { id: 'researches', label: 'Researches', icon: FlaskConical, color: 'text-orange-400', bgColor: 'bg-orange-400/10' },
  { id: 'chats', label: 'Chats', icon: MessageSquare, color: 'text-blue-400', bgColor: 'bg-blue-400/10' },
  { id: 'workspaces', label: 'Workspaces', icon: Briefcase, color: 'text-purple-400', bgColor: 'bg-purple-400/10' },
  { id: 'assets', label: 'Assets', icon: Files, color: 'text-green-400', bgColor: 'bg-green-400/10' },
  { id: 'databases', label: 'Databases', icon: Database, color: 'text-cyan-400', bgColor: 'bg-cyan-400/10' },
  { id: 'history', label: 'History', icon: Clock, color: 'text-pink-400', bgColor: 'bg-pink-400/10' },
]

const RECENT_SEARCHES = [
  'quantum computing research',
  'market analysis 2024',
  'neural network architecture',
  'climate data visualization',
  'API integration guide',
]

// ============================================================================
// Mock Data Generators
// ============================================================================

const generateMockResults = (query: string): SearchResult[] => {
  if (!query.trim()) return []

  const results: SearchResult[] = []
  const queryLower = query.toLowerCase()

  // Generate research results
  const researchTopics = ['Quantum Computing', 'Machine Learning', 'Climate Science', 'Blockchain', 'Biotechnology', 'Renewable Energy']
  researchTopics.forEach((topic, i) => {
    if (topic.toLowerCase().includes(queryLower) || queryLower.includes(topic.toLowerCase().split(' ')[0])) {
      results.push({
        id: `research-${i}`,
        title: `Research Report: ${topic} Analysis`,
        description: `Comprehensive analysis of ${topic.toLowerCase()} trends, methodologies, and future implications. Includes data visualization and key findings.`,
        category: 'researches',
        timestamp: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000),
        metadata: `PDF • ${(Math.random() * 5 + 1).toFixed(1)} MB`,
        url: `/researches/view/${i}`,
        relevance: 0.9 - i * 0.1
      })
    }
  })

  // Generate chat results
  const chatTopics = ['AI Discussion', 'Project Planning', 'Data Analysis', 'Code Review', 'Research Query']
  chatTopics.forEach((topic, i) => {
    if (Math.random() > 0.5 || topic.toLowerCase().includes(queryLower)) {
      results.push({
        id: `chat-${i}`,
        title: `${topic} Session`,
        description: `Conversation about ${queryLower} with AI assistant. ${Math.floor(Math.random() * 50 + 10)} messages exchanged.`,
        category: 'chats',
        timestamp: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000),
        metadata: `${Math.floor(Math.random() * 50 + 10)} messages`,
        url: `/chat/${i}`,
        relevance: 0.85 - i * 0.1
      })
    }
  })

  // Generate workspace results
  const workspaceNames = ['Research Hub', 'Data Science', 'Product Development', 'Marketing Analytics', 'Innovation Lab']
  workspaceNames.forEach((name, i) => {
    if (Math.random() > 0.6) {
      results.push({
        id: `workspace-${i}`,
        title: name,
        description: `Workspace containing projects, documents, and resources related to ${name.toLowerCase()}.`,
        category: 'workspaces',
        timestamp: new Date(Date.now() - Math.random() * 60 * 24 * 60 * 60 * 1000),
        metadata: `${Math.floor(Math.random() * 20 + 5)} items`,
        url: `/workspaces/view/${i}`,
        relevance: 0.75 - i * 0.05
      })
    }
  })

  // Generate asset results
  const assetTypes = [
    { name: 'Chart', type: 'image', icon: 'PNG' },
    { name: 'Dataset', type: 'file', icon: 'CSV' },
    { name: 'Recording', type: 'video', icon: 'MP4' },
    { name: 'Presentation', type: 'file', icon: 'PDF' },
  ]
  assetTypes.forEach((asset, i) => {
    if (Math.random() > 0.4) {
      results.push({
        id: `asset-${i}`,
        title: `${asset.name}_${query.replace(/\s/g, '_')}.${asset.icon.toLowerCase()}`,
        description: `${asset.type.charAt(0).toUpperCase() + asset.type.slice(1)} asset from research materials.`,
        category: 'assets',
        timestamp: new Date(Date.now() - Math.random() * 14 * 24 * 60 * 60 * 1000),
        metadata: `${asset.icon} • ${(Math.random() * 10 + 0.5).toFixed(1)} MB`,
        url: `/data/bucket/main/${asset.type}s`,
        relevance: 0.7 - i * 0.1
      })
    }
  })

  // Generate database results
  const tableNames = ['users', 'sessions', 'analytics', 'experiments', 'configurations']
  tableNames.forEach((table, i) => {
    if (Math.random() > 0.5) {
      results.push({
        id: `db-${i}`,
        title: `Table: ${table}`,
        description: `Database table containing ${table} data with ${Math.floor(Math.random() * 10000 + 100)} rows.`,
        category: 'databases',
        timestamp: new Date(Date.now() - Math.random() * 3 * 24 * 60 * 60 * 1000),
        metadata: `${Math.floor(Math.random() * 10000 + 100).toLocaleString()} rows`,
        url: `/data/databases/basic/tables/${table}`,
        relevance: 0.65 - i * 0.05
      })
    }
  })

  // Generate history results
  const actions = ['Generated Report', 'Exported Data', 'Created Workspace', 'Started Research', 'Downloaded Asset']
  actions.forEach((action, i) => {
    if (Math.random() > 0.5) {
      results.push({
        id: `history-${i}`,
        title: `${action}: "${query}"`,
        description: `Action performed on ${new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toLocaleDateString()}`,
        category: 'history',
        timestamp: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000),
        metadata: 'Activity',
        url: '/history',
        relevance: 0.5 - i * 0.05
      })
    }
  })

  return results.sort((a, b) => b.relevance - a.relevance)
}

const generateAISummary = (query: string, results: SearchResult[]): string => {
  const categoryCount = CATEGORIES.reduce((acc, cat) => {
    acc[cat.id] = results.filter(r => r.category === cat.id).length
    return acc
  }, {} as Record<CategoryId, number>)

  const topCategories = Object.entries(categoryCount)
    .filter(([, count]) => count > 0)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 3)
    .map(([cat]) => CATEGORIES.find(c => c.id === cat)?.label)
    .join(', ')

  return `Based on your search for "${query}", I found ${results.length} relevant items across your workspace.

**Key Findings:**
• Most results are from: ${topCategories || 'various categories'}
• ${results.filter(r => r.category === 'researches').length} research documents contain relevant information
• ${results.filter(r => r.category === 'chats').length} chat conversations mention related topics

**Suggested Actions:**
1. Review the top research documents for comprehensive analysis
2. Check recent chat sessions for context and discussions
3. Explore related assets and datasets for supporting materials`
}

// ============================================================================
// Helper Components
// ============================================================================

const HighlightText = ({ text, highlight }: { text: string; highlight: string }) => {
  if (!highlight.trim()) return <>{text}</>

  const parts = text.split(new RegExp(`(${highlight.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'))

  return (
    <>
      {parts.map((part, i) =>
        part.toLowerCase() === highlight.toLowerCase() ? (
          <mark key={i} className="bg-yellow-400/30 text-foreground rounded px-0.5">{part}</mark>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  )
}

const CategoryIcon = ({ category }: { category: CategoryId }) => {
  const config = CATEGORIES.find(c => c.id === category)
  if (!config) return null
  const Icon = config.icon
  return (
    <div className={cn("p-2 rounded-lg", config.bgColor)}>
      <Icon className={cn("size-4", config.color)} />
    </div>
  )
}

const ResultItem = ({
  result,
  query,
  onNavigate
}: {
  result: SearchResult
  query: string
  onNavigate: (url: string) => void
}) => {
  const [isHovered, setIsHovered] = useState(false)

  return (
    <div
      className="flex items-start gap-4 p-4 rounded-xl hover:bg-muted/30 transition-all cursor-pointer group"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => onNavigate(result.url)}
    >
      <CategoryIcon category={result.category} />

      <div className="flex-1 min-w-0">
        <h4 className="font-medium text-sm group-hover:text-primary transition-colors">
          <HighlightText text={result.title} highlight={query} />
        </h4>
        <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
          <HighlightText text={result.description} highlight={query} />
        </p>
        <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground/70">
          <span>{result.metadata}</span>
          <span>•</span>
          <span>{result.timestamp.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
        </div>
      </div>

      <div className={cn(
        "flex items-center gap-1 transition-opacity duration-200",
        isHovered ? "opacity-100" : "opacity-0"
      )}>
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={e => { e.stopPropagation(); navigator.clipboard.writeText(result.url) }}>
          <Copy className="size-3.5" />
        </Button>
        <Button variant="ghost" size="icon" className="h-8 w-8">
          <ExternalLink className="size-3.5" />
        </Button>
      </div>
    </div>
  )
}

const CategoryGroup = ({
  category,
  results,
  query,
  onNavigate,
  defaultExpanded = true
}: {
  category: CategoryConfig
  results: SearchResult[]
  query: string
  onNavigate: (url: string) => void
  defaultExpanded?: boolean
}) => {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const Icon = category.icon

  if (results.length === 0) return null

  return (
    <div className="border border-muted-foreground/10 rounded-2xl overflow-hidden bg-background/50">
      <button
        className="w-full flex items-center gap-3 p-4 hover:bg-muted/20 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className={cn("p-2 rounded-lg", category.bgColor)}>
          <Icon className={cn("size-5", category.color)} />
        </div>
        <span className="font-medium">{category.label}</span>
        <Badge variant="secondary" className="ml-1 text-xs font-normal">
          {results.length}
        </Badge>
        <div className="flex-1" />
        {expanded ? <ChevronDown className="size-4 text-muted-foreground" /> : <ChevronRight className="size-4 text-muted-foreground" />}
      </button>

      {expanded && (
        <div className="border-t border-muted-foreground/10 divide-y divide-muted-foreground/5">
          {results.slice(0, 5).map(result => (
            <ResultItem key={result.id} result={result} query={query} onNavigate={onNavigate} />
          ))}
          {results.length > 5 && (
            <div className="p-3 text-center">
              <Button variant="ghost" size="sm" className="text-muted-foreground gap-2">
                View all {results.length} results
                <ArrowRight className="size-3.5" />
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const AISummaryCard = ({
  summary,
  isLoading,
  sources
}: {
  summary: string
  isLoading: boolean
  sources: SearchResult[]
}) => {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    if (!isLoading) {
      const timer = setTimeout(() => {
        setIsVisible(true)
      }, 100)
      return () => clearTimeout(timer)
    } else {
      setIsVisible(false)
    }
  }, [isLoading])

  // Parse markdown-like formatting
  const renderContent = (text: string) => {
    return text.split('\n').map((line, i) => {
      if (line.startsWith('**') && line.endsWith('**')) {
        return <p key={i} className="font-semibold text-foreground mt-4 mb-2 text-base">{line.replace(/\*\*/g, '')}</p>
      }
      if (line.startsWith('•')) {
        return <p key={i} className="ml-3 my-1.5 flex items-start gap-2"><span className="text-primary mt-1">•</span><span>{line.slice(1).trim()}</span></p>
      }
      if (line.match(/^\d+\./)) {
        const num = line.match(/^(\d+)\./)?.[1]
        return <p key={i} className="ml-3 my-1.5 flex items-start gap-2"><span className="text-primary font-medium">{num}.</span><span>{line.replace(/^\d+\.\s*/, '')}</span></p>
      }
      if (line.trim() === '') return <div key={i} className="h-2" />
      return <p key={i} className="my-1.5 leading-relaxed">{line}</p>
    })
  }

  return (
    <Card className="py-0 relative overflow-hidden border-primary/30 bg-linear-to-br from-primary/5 via-primary/2 to-transparent shadow-lg shadow-primary/5">
      {/* Animated gradient border effect */}
      <div className="absolute inset-0 bg-linear-to-r from-primary/20 via-transparent to-primary/20 opacity-50" style={{ backgroundSize: '200% 100%' }} />
      
      {/* Glow effects */}
      <div className="absolute top-0 left-0 w-40 h-40 bg-primary/10 rounded-full blur-3xl -translate-x-1/2 -translate-y-1/2" />
      <div className="absolute bottom-0 right-0 w-32 h-32 bg-primary/5 rounded-full blur-2xl translate-x-1/2 translate-y-1/2" />

      <CardContent className="relative p-6">
        {/* Header */}
        <div className="flex items-center gap-3 mb-5">
          <div className="p-2 rounded-xl bg-primary/10 ring-1 ring-primary/20">
            <Sparkles className="size-5 text-primary" />
          </div>
          <div>
            <span className="font-semibold text-sm">AI Overview</span>
            <p className="text-[11px] text-muted-foreground">Powered by AI</p>
          </div>
          {isLoading && (
            <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              <span>Analyzing...</span>
            </div>
          )}
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <Skeleton className="h-4 w-4 rounded" />
              <Skeleton className="h-4 flex-1" />
            </div>
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-4/5" />
            <div className="h-3" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-2/3" />
          </div>
        ) : (
          <div 
            className={cn(
              "text-sm text-muted-foreground transition-all duration-700 ease-out",
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2"
            )}
          >
            {renderContent(summary)}
          </div>
        )}

        {/* Sources */}
        {sources.length > 0 && !isLoading && isVisible && (
          <div className={cn(
            "flex items-center gap-3 mt-5 pt-5 border-t border-primary/10 transition-all duration-700 delay-300",
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2"
          )}>
            <span className="text-xs text-muted-foreground font-medium">Sources:</span>
            <div className="flex flex-wrap gap-1.5">
              {sources.slice(0, 4).map(source => {
                const catConfig = CATEGORIES.find(c => c.id === source.category)
                return (
                  <Badge 
                    key={source.id} 
                    variant="outline" 
                    className={cn(
                      "text-[10px] font-normal gap-1 cursor-pointer hover:bg-muted/50 transition-colors",
                      catConfig?.color
                    )}
                  >
                    {source.title.length > 20 ? source.title.slice(0, 20) + '...' : source.title}
                  </Badge>
                )
              })}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ============================================================================
// Main Component
// ============================================================================

const Search = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)

  // State from URL params
  const initialQuery = useMemo(() => searchParams.get('q') || '', [searchParams])
  const aiMode = useMemo(() => searchParams.get('ai') === 'true', [searchParams])
  const selectedCategories = useMemo(() => 
    searchParams.get('categories')?.split(',').filter(Boolean) as CategoryId[] || [],
    [searchParams]
  )

  // Local state
  const [inputValue, setInputValue] = useState(initialQuery)
  const [isSearching, setIsSearching] = useState(false)
  const [results, setResults] = useState<SearchResult[]>(() => 
    initialQuery ? generateMockResults(initialQuery) : []
  )
  const [aiSummary, setAiSummary] = useState('')
  const [isAiLoading, setIsAiLoading] = useState(false)
  const [showRecentSearches, setShowRecentSearches] = useState(false)

  // Update URL params
  const updateParams = useCallback((updates: Record<string, string | null>) => {
    const newParams = new URLSearchParams(searchParams)
    Object.entries(updates).forEach(([key, value]) => {
      if (value === null || value === '') {
        newParams.delete(key)
      } else {
        newParams.set(key, value)
      }
    })
    setSearchParams(newParams, { replace: true })
  }, [searchParams, setSearchParams])

  // Execute search function
  const executeSearch = useCallback((q: string, ai: boolean) => {
    if (!q.trim()) {
      setResults([])
      setAiSummary('')
      updateParams({ q: null })
      return
    }

    setIsSearching(true)
    updateParams({ q })

    // Simulate search delay
    const timer = setTimeout(() => {
      const searchResults = generateMockResults(q)
      setResults(searchResults)
      setIsSearching(false)

      // Generate AI summary if enabled
      if (ai && searchResults.length > 0) {
        setIsAiLoading(true)
        setTimeout(() => {
          setAiSummary(generateAISummary(q, searchResults))
          setIsAiLoading(false)
        }, 800)
      } else {
        setAiSummary('')
      }
    }, 400)

    return () => clearTimeout(timer)
  }, [updateParams])

  // Handle Enter press
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      executeSearch(inputValue, aiMode)
      setShowRecentSearches(false)
      inputRef.current?.blur()
    }
    if (e.key === 'Escape') {
      setInputValue('')
      inputRef.current?.blur()
    }
  }

  // Effect for global keyboard shortcuts
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if (e.key === '/' && document.activeElement !== inputRef.current) {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handleGlobalKeyDown)
    return () => window.removeEventListener('keydown', handleGlobalKeyDown)
  }, [])

  // Perform re-search when AI mode or categories change (if query exists)
  useEffect(() => {
    if (initialQuery) {
      // Just refresh the existing results without full loading state if only categories changed
      // but if AI mode changed, we might need to trigger the AI summary
      const searchResults = generateMockResults(initialQuery)
      setResults(searchResults)
      
      if (aiMode && searchResults.length > 0 && !aiSummary) {
        setIsAiLoading(true)
        const timer = setTimeout(() => {
          setAiSummary(generateAISummary(initialQuery, searchResults))
          setIsAiLoading(false)
        }, 800)
        return () => clearTimeout(timer)
      }
    }
  }, [aiMode, initialQuery, aiSummary])

  // Filter results by selected categories
  const filteredResults = useMemo(() => {
    if (selectedCategories.length === 0) return results
    return results.filter(r => selectedCategories.includes(r.category))
  }, [results, selectedCategories])

  // Group results by category
  const groupedResults = useMemo(() => {
    return CATEGORIES.map(cat => ({
      category: cat,
      results: filteredResults.filter(r => r.category === cat.id)
    })).filter(group => group.results.length > 0)
  }, [filteredResults])

  // Toggle category
  const toggleCategory = (catId: CategoryId) => {
    const current = selectedCategories.includes(catId)
      ? selectedCategories.filter(c => c !== catId)
      : [...selectedCategories, catId]
    updateParams({ categories: current.length > 0 ? current.join(',') : null })
  }

  // Toggle AI mode
  const toggleAiMode = () => {
    const newAiMode = !aiMode
    updateParams({ ai: newAiMode ? 'true' : null })
  }

  const handleNavigate = (url: string) => {
    navigate(url)
  }

  const handleRecentSearch = (term: string) => {
    setInputValue(term)
    executeSearch(term, aiMode)
    setShowRecentSearches(false)
    inputRef.current?.blur()
  }

  return (
    <div className="flex flex-col h-full w-full bg-muted/10 overflow-hidden animate-in fade-in duration-500">
      {/* Header Section - Compact */}
      <div className="shrink-0 border-b bg-background/80 backdrop-blur-md sticky top-0 z-30">
        <div className="w-full max-w-5xl mx-auto px-6 py-4">
          <div className="flex flex-col gap-3">
            {/* Search Input Group */}
            <div className="relative group/input flex items-center">
              <div className="absolute left-4 z-10">
                <SearchIcon className="size-4.5 text-muted-foreground group-focus-within/input:text-primary transition-colors" />
              </div>
              
              <Input
                ref={inputRef}
                placeholder="Search everything... (Enter to search)"
                value={inputValue}
                onChange={e => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                onFocus={() => setShowRecentSearches(true)}
                onBlur={() => setTimeout(() => setShowRecentSearches(false), 200)}
                className="h-12 pl-12 pr-[140px] text-base bg-muted/20 border-muted-foreground/10 hover:border-muted-foreground/30 focus:border-primary/50 focus:ring-4 focus:ring-primary/5 rounded-xl transition-all"
              />

              <div className="absolute right-2 flex items-center gap-2">
                {inputValue && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-foreground"
                    onClick={() => setInputValue('')}
                  >
                    <X className="size-4" />
                  </Button>
                )}
                
                {/* AI Toggle inside Input */}
                <button
                  onClick={toggleAiMode}
                  className={cn(
                    "flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border transition-all duration-300",
                    aiMode 
                      ? "bg-primary/10 border-primary/20 text-primary shadow-sm" 
                      : "bg-background border-muted-foreground/10 text-muted-foreground hover:border-muted-foreground/30"
                  )}
                  title="AI Search Toggle"
                >
                  <Sparkles className={cn("size-3.5", aiMode && "text-primary")} />
                  <span className="text-[10px] font-bold uppercase tracking-wider">AI</span>
                </button>

                <Button 
                  size="sm" 
                  className="h-8 px-3 rounded-lg shadow-sm"
                  onClick={() => executeSearch(inputValue, aiMode)}
                >
                  Search
                </Button>
              </div>

              {/* Recent Searches Dropdown */}
              {showRecentSearches && !inputValue && (
                <div className="absolute top-full left-0 right-0 mt-2 p-1.5 bg-background border border-muted-foreground/20 rounded-xl shadow-2xl z-50 animate-in fade-in slide-in-from-top-2 duration-200">
                  <div className="flex items-center gap-2 px-3 py-2 text-[10px] uppercase font-bold tracking-widest text-muted-foreground/60">
                    <History className="size-3" />
                    Recent
                  </div>
                  {RECENT_SEARCHES.map((term, i) => (
                    <button
                      key={i}
                      className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-muted/50 transition-colors text-left"
                      onClick={() => handleRecentSearch(term)}
                    >
                      <Clock className="size-3.5 text-muted-foreground/40" />
                      <span className="text-sm text-foreground/80">{term}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Compact Category Filter Row */}
            <div className="flex items-center gap-2 overflow-x-auto no-scrollbar py-0.5">
              <Button
                variant={selectedCategories.length === 0 ? "secondary" : "ghost"}
                size="sm"
                className="h-7 px-3 text-xs rounded-lg shrink-0"
                onClick={() => updateParams({ categories: null })}
              >
                All Results
              </Button>
              <div className="w-px h-3 bg-muted-foreground/20 mx-1" />
              {CATEGORIES.map(cat => {
                const Icon = cat.icon
                const isSelected = selectedCategories.includes(cat.id)
                const count = results.filter(r => r.category === cat.id).length
                return (
                  <Button
                    key={cat.id}
                    variant={isSelected ? "secondary" : "ghost"}
                    size="sm"
                    className={cn(
                      "h-7 px-3 text-xs rounded-lg shrink-0 gap-2 transition-all",
                      isSelected && "bg-primary/5 text-primary border-primary/20",
                      !isSelected && "hover:bg-muted/50"
                    )}
                    onClick={() => toggleCategory(cat.id)}
                  >
                    <Icon className={cn("size-3.5", cat.color)} />
                    {cat.label}
                    {count > 0 && (
                      <span className="flex items-center justify-center min-w-[18px] h-[18px] bg-muted/50 rounded-md text-[10px]">
                        {count}
                      </span>
                    )}
                  </Button>
                )
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-8 py-6 space-y-6">
          {/* Loading State */}
          {isSearching && (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="size-8 animate-spin text-muted-foreground" />
            </div>
          )}

          {/* Empty State - No Query */}
          {!initialQuery && !isSearching && (
            <div className="flex flex-col items-center justify-center py-20 text-center animate-in fade-in slide-in-from-bottom-4 duration-1000">
              <div className="p-4 rounded-3xl bg-linear-to-b from-muted-foreground/10 to-transparent mb-8 ring-1 ring-muted-foreground/5 shadow-xl">
                <SearchIcon className="size-16 text-muted-foreground/20" />
              </div>
              <h2 className="text-2xl font-semibold text-foreground/80 mb-3 tracking-tight">Search Everything</h2>
              <p className="text-base text-muted-foreground/60 max-w-lg mx-auto leading-relaxed">
                Connect your dots. Explore researches, chats, assets and knowledge across your entire digital workspace instantly.
              </p>
              <div className="flex items-center gap-3 mt-10 p-2 px-4 rounded-xl bg-muted/20 border border-muted-foreground/5 backdrop-blur-sm text-xs text-muted-foreground/80">
                <div className="flex items-center gap-1.5 font-mono">
                    <kbd className="px-1.5 py-0.5 bg-background border border-muted-foreground/20 rounded shadow-xs">/</kbd>
                    <span>focus</span>
                </div>
                <span className="opacity-30">•</span>
                <div className="flex items-center gap-1.5">
                    <kbd className="px-1.5 py-0.5 bg-background border border-muted-foreground/20 rounded shadow-xs">Enter</kbd>
                    <span>search</span>
                </div>
                <span className="opacity-30">•</span>
                <div className="flex items-center gap-1.5 font-mono">
                    <kbd className="px-1.5 py-0.5 bg-background border border-muted-foreground/20 rounded shadow-xs">Esc</kbd>
                    <span>clear</span>
                </div>
              </div>
            </div>
          )}

          {/* No Results */}
          {initialQuery && !isSearching && filteredResults.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="p-4 rounded-2xl bg-muted/30 mb-6">
                <SearchIcon className="size-12 text-muted-foreground/30" />
              </div>
              <h2 className="text-xl font-medium text-muted-foreground mb-2">No results found</h2>
              <p className="text-sm text-muted-foreground/70 max-w-md">
                Try adjusting your search terms or filters to find what you're looking for.
              </p>
            </div>
          )}

          {/* Results */}
          {!isSearching && filteredResults.length > 0 && (
            <>
              {/* AI Summary */}
              {aiMode && (
                <AISummaryCard
                  summary={aiSummary}
                  isLoading={isAiLoading}
                  sources={filteredResults.slice(0, 4)}
                />
              )}

              {/* Result Count */}
              <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
                <div className="flex items-center gap-2">
                  <span>Found {filteredResults.length} items</span>
                  <span className="text-muted-foreground/30">•</span>
                  <span>Results for "{initialQuery}"</span>
                </div>
                {aiMode && (
                  <div className="flex items-center gap-1.5 text-primary font-medium animate-pulse">
                    <Sparkles className="size-3" />
                    <span className="text-[10px] uppercase tracking-wider">AI Insight Active</span>
                  </div>
                )}
              </div>

              {/* Grouped Results */}
              <div className="space-y-4">
                {groupedResults.map(({ category, results: catResults }, i) => (
                  <CategoryGroup
                    key={category.id}
                    category={category}
                    results={catResults}
                    query={initialQuery}
                    onNavigate={handleNavigate}
                    defaultExpanded={i < 3}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default Search