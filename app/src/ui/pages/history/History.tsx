import { useState, useMemo, useEffect, useCallback } from 'react'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { cn } from '@/lib/utils'
import {
  listHistoryItems,
  deleteHistoryItem,
  type HistoryItemRecord,
} from '@/lib/apis'
import { toast } from '@/components/ui/sonner'
import {
  Search,
  Trash2,
  Clock,
  FileText,
  MessageSquare,
  Sparkles,
  Download,
  ArrowUpDown,
  History as HistoryIcon,
  Loader2,
} from 'lucide-react'

interface HistoryRow {
  id: string
  action: string
  typeLabel: string
  metadata: string
  createdAt: Date
  lastSeenAt: Date
}

function parseApiDate(value: string | null | undefined): Date {
  if (!value) return new Date()
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? new Date() : d
}

function mapRecordToRow(record: HistoryItemRecord): HistoryRow {
  const activity = record.activity?.trim() || '—'
  const typeLabel = record.type ?? '—'
  const metaParts: string[] = []
  if (record.url) metaParts.push(record.url)
  if (record.workspace_id) metaParts.push(`workspace ${record.workspace_id}`)
  if (record.actions) metaParts.push(record.actions)
  return {
    id: record.id,
    action: activity,
    typeLabel,
    metadata: metaParts.join(' · ') || '—',
    createdAt: parseApiDate(record.created_at),
    lastSeenAt: parseApiDate(record.last_seen ?? record.created_at),
  }
}

const History = () => {
  const [data, setData] = useState<HistoryRow[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const loadHistory = useCallback(async () => {
    setLoading(true)
    try {
      const res = await listHistoryItems({
        page: 1,
        size: 200,
        sortBy: 'created_at',
        sortOrder,
      })
      setData(res.history_items.map(mapRecordToRow))
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to load history')
      setData([])
    } finally {
      setLoading(false)
    }
  }, [sortOrder])

  useEffect(() => {
    void loadHistory()
  }, [loadHistory])

  const filteredData = useMemo(() => {
    const q = searchQuery.toLowerCase().trim()
    const filtered = q
      ? data.filter(
          item =>
            item.action.toLowerCase().includes(q) ||
            item.typeLabel.toLowerCase().includes(q) ||
            item.metadata.toLowerCase().includes(q),
        )
      : data

    return [...filtered].sort((a, b) =>
      sortOrder === 'desc'
        ? b.createdAt.getTime() - a.createdAt.getTime()
        : a.createdAt.getTime() - b.createdAt.getTime(),
    )
  }, [data, searchQuery, sortOrder])

  const toggleSelectAll = () => {
    if (selectedIds.size === filteredData.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filteredData.map(item => item.id)))
    }
  }

  const toggleSelect = (id: string) => {
    const next = new Set(selectedIds)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelectedIds(next)
  }

  const handleDeleteSingle = async (id: string) => {
    const previous = data
    setData(prev => prev.filter(item => item.id !== id))
    if (selectedIds.has(id)) {
      const next = new Set(selectedIds)
      next.delete(id)
      setSelectedIds(next)
    }
    try {
      await deleteHistoryItem(id)
    } catch (e) {
      setData(previous)
      toast.error(e instanceof Error ? e.message : 'Delete failed')
    }
  }

  const handleDeleteSelected = async () => {
    const ids = [...selectedIds]
    if (ids.length === 0) return
    const previous = data
    setData(prev => prev.filter(item => !selectedIds.has(item.id)))
    setSelectedIds(new Set())
    try {
      await Promise.all(ids.map(id => deleteHistoryItem(id)))
    } catch (e) {
      setData(previous)
      toast.error(e instanceof Error ? e.message : 'Delete failed')
    }
  }

  const formatTimestamp = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: 'numeric',
    }).format(date)
  }

  const getTypeIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'research':
        return <FileText className="size-3.5" />
      case 'chat':
        return <MessageSquare className="size-3.5" />
      case 'generation':
        return <Sparkles className="size-3.5" />
      case 'export':
      case 'download':
        return <Download className="size-3.5" />
      default:
        return <Clock className="size-3.5" />
    }
  }

  return (
    <div className="flex flex-col h-full w-full bg-muted/10 overflow-hidden animate-in fade-in duration-500">
      <div className="shrink-0 border-b bg-background/50 backdrop-blur-sm sticky top-0 z-30">
        <div className="w-full px-8 py-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="size-12 rounded-2xl bg-linear-to-br from-primary/20 via-primary/10 to-transparent border border-primary/20 flex items-center justify-center animate-in fade-in zoom-in duration-500">
                <HistoryIcon className="size-6 text-primary" />
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

            {selectedIds.size > 0 && (
              <div className="flex items-center gap-2 animate-in fade-in slide-in-from-right-4 duration-300">
                <span className="text-sm text-muted-foreground mr-2">
                  {selectedIds.size} selected
                </span>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => void handleDeleteSelected()}
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
              onClick={() => setSortOrder(prev => (prev === 'asc' ? 'desc' : 'asc'))}
              className="gap-2 min-w-[140px]"
            >
              <ArrowUpDown className="size-4" />
              {sortOrder === 'desc' ? 'Newest First' : 'Oldest First'}
            </Button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto w-full">
        <div className="w-full pb-24">
          {loading ? (
            <div className="flex justify-center py-24">
              <Loader2 className="size-8 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="relative w-full">
              <table className="w-full caption-bottom text-sm border-separate border-spacing-0">
                <thead className="sticky top-0 z-20 bg-muted/10 backdrop-blur-md shadow-sm">
                  <tr className="hover:bg-transparent">
                    <th className="h-12 px-6 text-left align-middle font-medium text-muted-foreground w-[50px] border-b bg-background/50">
                      <Checkbox
                        checked={
                          filteredData.length > 0 &&
                          selectedIds.size === filteredData.length
                        }
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
                    <th className="h-12 px-6 text-right align-middle font-medium text-muted-foreground w-[80px] border-b bg-background/50" />
                  </tr>
                </thead>
                <tbody className="[&_tr:last-child]:border-0 divide-y-0">
                  {filteredData.length === 0 ? (
                    <tr>
                      <td
                        colSpan={6}
                        className="p-4 text-center text-muted-foreground h-24 align-middle"
                      >
                        No results found.
                      </td>
                    </tr>
                  ) : (
                    filteredData.map(item => (
                      <tr
                        key={item.id}
                        className={cn(
                          'transition-colors hover:bg-muted/10 data-[state=selected]:bg-muted rounded-lg group border-none',
                          selectedIds.has(item.id) && 'bg-muted',
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
                            <span className="text-xs text-muted-foreground">
                              {item.metadata}
                            </span>
                          </div>
                        </td>
                        <td className="p-4 align-middle border-none">
                          <Badge
                            variant="secondary"
                            className="font-normal gap-1.5 bg-muted-foreground/10 text-foreground hover:bg-muted-foreground/20"
                          >
                            {getTypeIcon(item.typeLabel)}
                            {item.typeLabel}
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
                            onClick={() => void handleDeleteSingle(item.id)}
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
          )}
        </div>
      </div>
    </div>
  )
}

export default History
