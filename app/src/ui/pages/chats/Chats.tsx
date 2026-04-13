import { useState, useMemo, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { listChatThreads, deleteChatThread, type ChatThreadRecord } from '@/lib/apis'
import { toast } from '@/components/ui/sonner'
import {
  Search,
  MessageSquare,
  Clock,
  TrendingUp,
  Calendar,
  Sparkles,
  ArrowUpDown,
  ChevronDown,
  LayoutGrid,
  List,
  LucideIcon,
  Loader2,
  Trash2,
} from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'

interface ChatListItem {
  id: string
  title: string
  preview: string
  timestamp: Date
  tokenCount: number
  category: string
  isActive: boolean
  tags: string[]
}

function mapThread(record: ChatThreadRecord): ChatListItem {
  const wid = record.workspace_id?.trim()
  return {
    id: record.thread_id,
    title: record.thread_title?.trim() || 'Untitled',
    preview: wid ? `Workspace ${wid}` : 'Conversation',
    timestamp: new Date(record.updated_at),
    tokenCount: record.token_count ?? 0,
    category: 'Chat',
    isActive: false,
    tags: wid ? [wid.slice(0, 14)] : [],
  }
}

type SortOption = 'recent' | 'oldest' | 'most-messages' | 'alphabetical'
type ViewMode = 'grid' | 'list'

const Chats = () => {
  const navigate = useNavigate()
  const [threads, setThreads] = useState<ChatListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<SortOption>('recent')
  const [viewMode, setViewMode] = useState<ViewMode>('grid')

  const loadThreads = useCallback(async () => {
    setLoading(true)
    try {
      const res = await listChatThreads({
        page: 1,
        size: 200,
        sortBy: 'updated_at',
        sortOrder: 'desc',
      })
      setThreads(res.items.map(mapThread))
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to load chats')
      setThreads([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadThreads()
  }, [loadThreads])

  const handleDeleteThread = async (e: React.MouseEvent, threadId: string) => {
    e.stopPropagation()
    const previous = threads
    setThreads(prev => prev.filter(t => t.id !== threadId))
    try {
      await deleteChatThread(threadId)
    } catch (err) {
      setThreads(previous)
      toast.error(err instanceof Error ? err.message : 'Failed to delete thread')
    }
  }

  const filteredAndSortedChats = useMemo(() => {
    let filtered = threads

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(
        chat =>
          chat.title.toLowerCase().includes(query) ||
          chat.preview.toLowerCase().includes(query) ||
          chat.tags.some(tag => tag.toLowerCase().includes(query)) ||
          chat.category.toLowerCase().includes(query),
      )
    }

    const sorted = [...filtered].sort((a, b) => {
      switch (sortBy) {
        case 'recent':
          return b.timestamp.getTime() - a.timestamp.getTime()
        case 'oldest':
          return a.timestamp.getTime() - b.timestamp.getTime()
        case 'most-messages':
          return b.tokenCount - a.tokenCount
        case 'alphabetical':
          return a.title.localeCompare(b.title)
        default:
          return 0
      }
    })

    return sorted
  }, [threads, searchQuery, sortBy])

  // Format timestamp
  const formatTimestamp = (date: Date) => {
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))

    if (days === 0) {
      const hours = Math.floor(diff / (1000 * 60 * 60))
      if (hours === 0) {
        const minutes = Math.floor(diff / (1000 * 60))
        return minutes <= 1 ? 'Just now' : `${minutes}m ago`
      }
      return `${hours}h ago`
    } else if (days === 1) {
      return 'Yesterday'
    } else if (days < 7) {
      return `${days}d ago`
    } else {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    }
  }

  const getSortLabel = (sort: SortOption) => {
    const labels: Record<SortOption, string> = {
      recent: 'Most Recent',
      oldest: 'Oldest First',
      'most-messages': 'Most Messages',
      alphabetical: 'Alphabetical'
    }
    return labels[sort]
  }

  const getSortIcon = (sort: SortOption) => {
    const icons: Record<SortOption, LucideIcon> = {
      recent: Clock,
      oldest: Calendar,
      'most-messages': TrendingUp,
      alphabetical: ArrowUpDown
    }
    const Icon = icons[sort]
    return <Icon className="size-4" />
  }

  return (
    <div className="flex flex-col h-full w-full bg-linear-to-b from-background via-background to-accent/5 overflow-hidden animate-in fade-in duration-500">
      {/* Header Section */}
      <div className="shrink-0 border-b border-border/40 bg-background/80 backdrop-blur-xl sticky top-0 z-10 transition-all duration-300">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="size-12 rounded-2xl bg-linear-to-br from-primary/20 via-primary/10 to-transparent border border-primary/20 flex items-center justify-center animate-in fade-in zoom-in duration-500">
                <MessageSquare className="size-6 text-primary" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-linear-to-r from-foreground via-foreground to-foreground/70 bg-clip-text text-transparent">
                  My Conversations
                </h1>
                <p className="text-sm text-muted-foreground mt-1">
                  {filteredAndSortedChats.length} {filteredAndSortedChats.length === 1 ? 'conversation' : 'conversations'}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* View Toggle */}
              <div className="flex items-center p-1 rounded-xl bg-background/50 border border-border/50">
                <button
                  onClick={() => setViewMode('grid')}
                  className={cn(
                    "p-2 rounded-lg transition-all duration-200 hover:text-foreground",
                    viewMode === 'grid'
                      ? "bg-accent text-foreground shadow-sm"
                      : "text-muted-foreground hover:bg-accent/50"
                  )}
                  title="Grid View"
                >
                  <LayoutGrid className="size-4" />
                </button>
                <button
                  onClick={() => setViewMode('list')}
                  className={cn(
                    "p-2 rounded-lg transition-all duration-200 hover:text-foreground",
                    viewMode === 'list'
                      ? "bg-accent text-foreground shadow-sm"
                      : "text-muted-foreground hover:bg-accent/50"
                  )}
                  title="List View"
                >
                  <List className="size-4" />
                </button>
              </div>

              {/* Sort Dropdown */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button className="flex items-center gap-2 px-4 py-2 rounded-xl border border-border/50 bg-background/50 hover:bg-accent/50 hover:border-border transition-all duration-200 group h-[42px]">
                    {getSortIcon(sortBy)}
                    <span className="text-sm font-medium hidden sm:inline">{getSortLabel(sortBy)}</span>
                    <ChevronDown className="size-4 text-muted-foreground group-hover:text-foreground transition-colors" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  <DropdownMenuItem onClick={() => setSortBy('recent')} className="gap-2">
                    <Clock className="size-4" />
                    <span>Most Recent</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setSortBy('oldest')} className="gap-2">
                    <Calendar className="size-4" />
                    <span>Oldest First</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setSortBy('most-messages')} className="gap-2">
                    <TrendingUp className="size-4" />
                    <span>Most Messages</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setSortBy('alphabetical')} className="gap-2">
                    <ArrowUpDown className="size-4" />
                    <span>Alphabetical</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          {/* Search Bar */}
          <div className="relative group">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 size-5 text-muted-foreground group-focus-within:text-primary transition-colors duration-200" />
            <Input
              type="text"
              placeholder="Search conversations by title, content, or tags..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="pl-12 h-12 rounded-2xl border-border/50 bg-background/50 backdrop-blur-sm hover:border-border focus-visible:border-primary/50 transition-all duration-200 text-base shadow-sm"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-4 top-1/2 -translate-y-1/2 size-6 rounded-full bg-accent/50 hover:bg-accent flex items-center justify-center transition-colors"
              >
                <span className="text-xs font-bold text-muted-foreground">✕</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Chat List */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-6 py-6 pb-24">
          {loading ? (
            <div className="flex justify-center py-24">
              <Loader2 className="size-8 animate-spin text-muted-foreground" />
            </div>
          ) : filteredAndSortedChats.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-96 animate-in fade-in zoom-in duration-500">
              <div className="size-24 rounded-3xl bg-linear-to-br from-accent/30 to-transparent border border-border/30 flex items-center justify-center mb-6">
                <Search className="size-12 text-muted-foreground/50" />
              </div>
              <h3 className="text-xl font-semibold text-foreground/80 mb-2">No conversations found</h3>
              <p className="text-sm text-muted-foreground text-center max-w-md">
                {searchQuery
                  ? 'Try adjusting your search query or filters'
                  : 'Start a new conversation to see it here'}
              </p>
            </div>
          ) : (
            <div className={cn(
              "grid gap-4 transition-all duration-300",
              viewMode === 'grid'
                ? "grid-cols-1 md:grid-cols-2 lg:grid-cols-3"
                : "grid-cols-1"
            )}>
              {filteredAndSortedChats.map((chat, index) => (
                <Card
                  key={chat.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => navigate(`/chat/${encodeURIComponent(chat.id)}`)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' || e.key === ' ')
                      navigate(`/chat/${encodeURIComponent(chat.id)}`)
                  }}
                  className={cn(
                    'group cursor-pointer hover:shadow-xl hover:shadow-primary/5 hover:border-primary/30 transition-all duration-300 border-border/40 overflow-hidden relative animate-in fade-in slide-in-from-bottom-4',
                    chat.isActive && 'ring-2 ring-primary/20 border-primary/40',
                    viewMode === 'grid'
                      ? "hover:scale-[1.02]"
                      : "flex flex-row items-center gap-4 p-1 hover:bg-accent/5"
                  )}
                  style={{ animationDelay: `${index * 50}ms` }}
                >
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute top-2 right-2 z-20 h-8 w-8 text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100"
                    onClick={e => void handleDeleteThread(e, chat.id)}
                    aria-label="Delete thread"
                  >
                    <Trash2 className="size-4" />
                  </Button>
                  {/* Active indicator glow */}
                  {chat.isActive && (
                    <div className="absolute inset-0 bg-linear-to-br from-primary/5 via-transparent to-transparent pointer-events-none" />
                  )}

                  {viewMode === 'grid' ? (
                    // Grid View Layout
                    <>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-lg group-hover:text-primary transition-colors duration-200 line-clamp-2 flex items-start gap-2">
                          {chat.isActive && (
                            <div className="mt-1.5 size-2.5 rounded-full bg-primary animate-pulse shadow-[0_0_8px_rgba(var(--primary),0.5)] shrink-0" />
                          )}
                          {chat.title}
                        </CardTitle>
                        <CardDescription className="line-clamp-2 mt-2">
                          {chat.preview}
                        </CardDescription>
                      </CardHeader>

                      <CardContent className="pt-0 flex flex-col items-start gap-4">
                        <div className="flex flex-wrap gap-1.5 mt-auto">
                          {chat.tags.slice(0, 3).map(tag => (
                            <span
                              key={tag}
                              className="text-xs px-2 py-0.5 rounded-md bg-accent/50 text-muted-foreground border border-border/30 hover:border-border/60 transition-colors"
                            >
                              #{tag}
                            </span>
                          ))}
                        </div>

                        <div className="flex items-end justify-between w-full pt-3 border-t border-border/30 gap-2">
                          <div className="flex flex-col gap-1 text-xs text-muted-foreground w-full">
                            <div className="flex items-center justify-between gap-3 w-full">
                              <div className="flex items-center gap-1">
                                <MessageSquare className="size-3.5" />
                                <span className="font-medium">
                                  {chat.tokenCount > 0
                                    ? `${chat.tokenCount} tokens`
                                    : '—'}
                                </span>
                              </div>
                              <div className="flex items-center gap-1">
                                <Clock className="size-3.5" />
                                <span>{formatTimestamp(chat.timestamp)}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </>
                  ) : (
                    // List View Layout
                    <div className="flex items-center w-full p-4 gap-6">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          {chat.isActive && (
                            <div className="size-2 rounded-full bg-primary animate-pulse shadow-[0_0_8px_rgba(var(--primary),0.5)]" />
                          )}
                          <h3 className="text-base font-semibold group-hover:text-primary transition-colors duration-200 truncate">
                            {chat.title}
                          </h3>
                        </div>
                        <p className="text-sm text-muted-foreground truncate opacity-80 pl-4">
                          {chat.preview}
                        </p>
                      </div>

                      <div className="hidden md:flex items-center gap-6 shrink-0 text-sm text-muted-foreground">
                        <div className="flex gap-1.5">
                          {chat.tags.slice(0, 2).map(tag => (
                            <span
                              key={tag}
                              className="text-xs px-2 py-0.5 rounded-md bg-accent/50 border border-border/30"
                            >
                              #{tag}
                            </span>
                          ))}
                        </div>
                        <div className="flex items-center gap-4 min-w-[140px] justify-end">
                          <div className="flex flex-col items-end gap-0.5 text-xs">
                            <div className="flex items-center gap-1.5">
                              <MessageSquare className="size-3" />
                              <span>
                                {chat.tokenCount > 0 ? chat.tokenCount : '—'}
                              </span>
                            </div>
                            <div className="flex items-center gap-1.5 opacity-70">
                              <Clock className="size-3" />
                              <span>{formatTimestamp(chat.timestamp)}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Hover effect overlay */}
                  <div className="absolute inset-0 bg-linear-to-t from-primary/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Floating Action Button */}
      <button className="fixed bottom-8 right-8 size-14 rounded-full bg-linear-to-br from-primary via-primary to-primary/80 hover:shadow-2xl hover:shadow-primary/30 hover:scale-110 transition-all duration-300 flex items-center justify-center text-primary-foreground group z-20 animate-in fade-in zoom-in duration-500">
        <Sparkles className="size-6 group-hover:rotate-12 transition-transform duration-300" />
      </button>
    </div>
  )
}

export default Chats