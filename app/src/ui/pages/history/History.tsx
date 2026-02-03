import { useState, useMemo } from 'react'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { cn } from '@/lib/utils'
import {
  Search,
  Trash2,
  Clock,
  FileText,
  MessageSquare,
  Sparkles,
  Download,
  ArrowUpDown,
  History as HistoryIcon
} from 'lucide-react'

// Generate 50 Dummy History Items
const ACTIONS = [
  'Generated Research Report',
  'Chat Session',
  'Exported Chart',
  'Research Query',
  'Generated Summary',
  'Downloaded Dataset',
  'Exported Data',
  'Downloaded Invoice'
]

const TOPICS = [
  'Quantum Computing',
  'Market Volatility',
  'Global Temp Rise',
  'CRISPR Advancements',
  'Python Optimization',
  'Web3 Protocols',
  'Crypto Prices 2026',
  'Neural Networks',
  'SpaceX Starship',
  'React Performance',
  'User Analytics',
  'AI Ethics',
  'Sustainable Energy',
  'Cybersecurity Trends',
  'Cloud Architecture'
]

const TYPES = ['Research', 'Chat', 'Export', 'Generation', 'Download']

const generateDummyData = (count: number) => {
  return Array.from({ length: count }).map((_, i) => {
    const type = TYPES[Math.floor(Math.random() * TYPES.length)]
    const actionBase = ACTIONS[Math.floor(Math.random() * ACTIONS.length)]
    const topic = TOPICS[Math.floor(Math.random() * TOPICS.length)]

    let metadata = ''
    switch (type) {
      case 'Research': metadata = `PDF • ${(Math.random() * 5 + 0.5).toFixed(1)} MB`; break;
      case 'Chat': metadata = `${Math.floor(Math.random() * 50 + 5)} messages`; break;
      case 'Export': metadata = `${Math.random() > 0.5 ? 'PNG' : 'CSV'} • ${(Math.random() * 2 + 0.1).toFixed(1)} MB`; break;
      case 'Generation': metadata = 'Markdown'; break;
      case 'Download': metadata = `ZIP • ${(Math.random() * 50 + 1).toFixed(1)} MB`; break;
    }

    // Generate createdAt within the last 30 days
    const createdAt = new Date()
    createdAt.setDate(createdAt.getDate() - Math.floor(Math.random() * 30))
    createdAt.setHours(Math.floor(Math.random() * 24), Math.floor(Math.random() * 60))

    // Generate lastSeenAt (anytime after createdAt)
    const lastSeenAt = new Date(createdAt.getTime() + Math.random() * (Date.now() - createdAt.getTime()))

    return {
      id: `history-${i + 1}`,
      action: `${actionBase}: "${topic}"`,
      type,
      createdAt,
      lastSeenAt,
      metadata
    }
  }).sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
}

const DUMMY_HISTORY = generateDummyData(50)

type HistoryItem = typeof DUMMY_HISTORY[0]

const History = () => {
  const [data, setData] = useState<HistoryItem[]>(DUMMY_HISTORY)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  // Filter and Sort
  const filteredData = useMemo(() => {
    const filtered = data.filter(item =>
      item.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.type.toLowerCase().includes(searchQuery.toLowerCase())
    )

    return filtered.sort((a, b) => {
      return sortOrder === 'desc'
        ? b.createdAt.getTime() - a.createdAt.getTime()
        : a.createdAt.getTime() - b.createdAt.getTime()
    })
  }, [data, searchQuery, sortOrder])

  // Selection Handlers
  const toggleSelectAll = () => {
    if (selectedIds.size === filteredData.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filteredData.map(item => item.id)))
    }
  }

  const toggleSelect = (id: string) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }

  // Delete Handlers
  const handleDeleteSelected = () => {
    setData(prev => prev.filter(item => !selectedIds.has(item.id)))
    setSelectedIds(new Set())
  }

  const handleDeleteSingle = (id: string) => {
    setData(prev => prev.filter(item => item.id !== id))
    if (selectedIds.has(id)) {
      const newSelected = new Set(selectedIds)
      newSelected.delete(id)
      setSelectedIds(newSelected)
    }
  }

  // Formatting
  const formatTimestamp = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: 'numeric'
    }).format(date)
  }

  const getTypeIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'research': return <FileText className="size-3.5" />
      case 'chat': return <MessageSquare className="size-3.5" />
      case 'generation': return <Sparkles className="size-3.5" />
      case 'export':
      case 'download': return <Download className="size-3.5" />
      default: return <Clock className="size-3.5" />
    }
  }

  return (
    <div className="flex flex-col h-full w-full bg-muted/10 overflow-hidden">
      {/* Header Section */}
      <div className="shrink-0 border-b bg-background/50 backdrop-blur-sm sticky top-0 z-30">
        <div className="w-full px-8 py-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="size-10 rounded-xl bg-primary/10 flex items-center justify-center">
                <HistoryIcon className="size-5 text-primary" />
              </div>
              <div>
                <h1 className="text-xl font-semibold tracking-tight">
                  Activity History
                </h1>
                <p className="text-sm text-muted-foreground">
                  View and manage your recent activity
                </p>
              </div>
            </div>

            {/* Bulk Actions */}
            {selectedIds.size > 0 && (
              <div className="flex items-center gap-2 animate-in fade-in slide-in-from-right-4 duration-300">
                <span className="text-sm text-muted-foreground mr-2">
                  {selectedIds.size} selected
                </span>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleDeleteSelected}
                  className="gap-2"
                >
                  <Trash2 className="size-4" />
                  Delete Selected
                </Button>
              </div>
            )}
          </div>

          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
              <Input
                placeholder="Search history..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="pl-9 bg-background"
              />
            </div>

            <Button
              variant="outline"
              onClick={() => setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')}
              className="gap-2 min-w-[140px]"
            >
              <ArrowUpDown className="size-4" />
              {sortOrder === 'desc' ? 'Newest First' : 'Oldest First'}
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content - Single Scroll Container */}
      <div className="flex-1 overflow-y-auto w-full">
        <div className="w-full pb-24">
          <div className="relative w-full">
            <table className="w-full caption-bottom text-sm border-separate border-spacing-0">
              <thead className="sticky top-0 z-20 bg-muted/10 backdrop-blur-md shadow-sm">
                <tr className="hover:bg-transparent">
                  <th className="h-12 px-6 text-left align-middle font-medium text-muted-foreground w-[50px] border-b bg-background/50">
                    <Checkbox
                      checked={filteredData.length > 0 && selectedIds.size === filteredData.length}
                      onCheckedChange={toggleSelectAll}
                    />
                  </th>
                  <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground border-b bg-background/50">
                    Activity
                  </th>
                  <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground w-[150px] border-b bg-background/50">
                    Type
                  </th>
                  <th className="h-12 px-4 text-right align-middle font-medium text-muted-foreground w-[180px] border-b bg-background/50">
                    Created At
                  </th>
                  <th className="h-12 px-4 text-right align-middle font-medium text-muted-foreground w-[180px] border-b bg-background/50">
                    Last Seen At
                  </th>
                  <th className="h-12 px-6 text-right align-middle font-medium text-muted-foreground w-[80px] border-b bg-background/50">

                  </th>
                </tr>
              </thead>
              <tbody className="[&_tr:last-child]:border-0 divide-y-0">
                {filteredData.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-4 text-center text-muted-foreground h-24 align-middle">
                      No results found.
                    </td>
                  </tr>
                ) : (
                  filteredData.map((item) => (
                    <tr
                      key={item.id}
                      className={cn(
                        "transition-colors hover:bg-muted/10 data-[state=selected]:bg-muted rounded-lg group border-none",
                        selectedIds.has(item.id) && "bg-muted"
                      )}
                    >
                      <td className="p-4 px-6 align-middle border-none">
                        <Checkbox
                          checked={selectedIds.has(item.id)}
                          onCheckedChange={() => toggleSelect(item.id)}
                        />
                      </td>
                      <td className="p-4 align-middle border-none">
                        <div className="flex flex-col gap-1">
                          <span className="font-medium">{item.action}</span>
                          <span className="text-xs text-muted-foreground">{item.metadata}</span>
                        </div>
                      </td>
                      <td className="p-4 align-middle border-none">
                        <Badge variant="secondary" className="font-normal gap-1.5 bg-muted-foreground/10 text-foreground hover:bg-muted-foreground/20">
                          {getTypeIcon(item.type)}
                          {item.type}
                        </Badge>
                      </td>
                      <td className="p-4 align-middle text-right text-muted-foreground font-mono text-xs border-none">
                        {formatTimestamp(item.createdAt)}
                      </td>
                      <td className="p-4 align-middle text-right text-muted-foreground font-mono text-xs border-none">
                        {formatTimestamp(item.lastSeenAt)}
                      </td>
                      <td className="p-4 px-6 align-middle text-right border-none">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDeleteSingle(item.id)}
                          className="h-8 w-8 text-muted-foreground/40 hover:text-destructive hover:bg-destructive/10 transition-all rounded-lg group-hover:opacity-100"
                        >
                          <Trash2 className="size-4" />
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

export default History