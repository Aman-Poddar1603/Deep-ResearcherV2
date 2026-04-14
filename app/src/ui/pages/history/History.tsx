import { useState, useMemo, useEffect, useCallback } from 'react'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from '@/components/ui/hover-card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { cn } from '@/lib/utils'
import {
  listHistoryItems,
  deleteHistoryItem,
  patchHistoryItem,
  executeHistoryAction,
  executeHistoryBulkAction,
  type HistoryItemRecord,
  type HistoryAction,
  type HistoryType,
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
  Pencil,
  RefreshCw,
  RotateCcw,
} from 'lucide-react'

interface HistoryRow {
  id: string
  action: string
  typeLabel: string
  metadata: string
  createdAt: Date
  lastSeenAt: Date
  raw: HistoryItemRecord
  isDeleted: boolean
}

interface EditDraft {
  activity: string
  type: HistoryType
  url: string
  actions: string
}

const HISTORY_TYPES: HistoryType[] = [
  'workspace',
  'usage',
  'research',
  'chat',
  'version',
  'token',
  'ai_summary',
  'bucket',
  'search',
  'export',
  'download',
  'upload',
  'generation',
]

const MAX_HISTORY_CELL_CHARS = 40

function truncateText(value: string, maxChars: number = MAX_HISTORY_CELL_CHARS): string {
  const text = (value || '').trim()
  if (text.length <= maxChars) return text
  return `${text.slice(0, maxChars)}...`
}

function TruncatedHoverCell({
  value,
  className,
}: {
  value: string
  className?: string
}) {
  const text = (value || '').trim() || '—'
  const truncated = truncateText(text)
  const isTruncated = truncated !== text

  if (!isTruncated) {
    return <span className={className}>{text}</span>
  }

  return (
    <HoverCard openDelay={120} closeDelay={70}>
      <HoverCardTrigger asChild>
        <span className={cn(className, 'cursor-help')}>{truncated}</span>
      </HoverCardTrigger>
      <HoverCardContent className="w-[420px] max-w-[80vw] break-words text-sm">
        {text}
      </HoverCardContent>
    </HoverCard>
  )
}

function isKnownHistoryType(value: string | null | undefined): value is HistoryType {
  return HISTORY_TYPES.includes((value ?? '') as HistoryType)
}

function parseActionTokens(value: string | null | undefined): Set<string> {
  if (!value) return new Set()
  const tokens = new Set<string>()
  value
    .replace(/\|/g, ',')
    .split(',')
    .map(part => part.trim().toLowerCase())
    .filter(Boolean)
    .forEach(token => tokens.add(token))
  return tokens
}

function parseApiDate(value: string | null | undefined): Date {
  if (!value) return new Date()
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? new Date() : d
}

function mapRecordToRow(record: HistoryItemRecord): HistoryRow {
  const activity = record.activity?.trim() || '—'
  const typeLabel = record.type ?? '—'
  const actionTokens = parseActionTokens(record.actions)
  const isDeleted = actionTokens.has('delete')
  const metaParts: string[] = []
  if (record.url) metaParts.push(record.url)
  if (record.workspace_id) metaParts.push(`workspace ${record.workspace_id}`)
  if (record.actions) metaParts.push(`actions: ${record.actions}`)
  if (isDeleted) metaParts.push('deleted')
  return {
    id: record.id,
    action: activity,
    typeLabel,
    metadata: metaParts.join(' · ') || '—',
    createdAt: parseApiDate(record.created_at),
    lastSeenAt: parseApiDate(record.last_seen ?? record.created_at),
    raw: record,
    isDeleted,
  }
}

function buildEditDraft(record: HistoryItemRecord): EditDraft {
  return {
    activity: record.activity ?? '',
    type: isKnownHistoryType(record.type) ? record.type : 'usage',
    url: record.url ?? '',
    actions: record.actions ?? '',
  }
}

const History = () => {
  const [data, setData] = useState<HistoryRow[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [includeDeleted, setIncludeDeleted] = useState(false)
  const [typeFilter, setTypeFilter] = useState<'all' | HistoryType>('all')
  const [activeMutationId, setActiveMutationId] = useState<string | null>(null)
  const [bulkMutating, setBulkMutating] = useState(false)
  const [isEditOpen, setIsEditOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<EditDraft>({
    activity: '',
    type: 'usage',
    url: '',
    actions: '',
  })
  const [savingEdit, setSavingEdit] = useState(false)

  const upsertRow = useCallback((record: HistoryItemRecord) => {
    setData(prev => {
      const mapped = mapRecordToRow(record)
      const idx = prev.findIndex(item => item.id === record.id)
      if (idx === -1) return [mapped, ...prev]
      const next = [...prev]
      next[idx] = mapped
      return next
    })
  }, [])

  const loadHistory = useCallback(async () => {
    setLoading(true)
    try {
      const res = await listHistoryItems({
        page: 1,
        size: 200,
        sortBy: 'created_at',
        sortOrder,
        includeDeleted,
        itemType: typeFilter === 'all' ? undefined : typeFilter,
      })
      const mapped = res.history_items.map(mapRecordToRow)
      setData(mapped)
      setSelectedIds(prev => {
        const availableIds = new Set(mapped.map(item => item.id))
        return new Set([...prev].filter(id => availableIds.has(id)))
      })
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to load history')
      setData([])
      setSelectedIds(new Set())
    } finally {
      setLoading(false)
    }
  }, [includeDeleted, sortOrder, typeFilter])

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

  const openEditDialog = (item: HistoryRow) => {
    setEditingId(item.id)
    setEditDraft(buildEditDraft(item.raw))
    setIsEditOpen(true)
  }

  const closeEditDialog = () => {
    if (savingEdit) return
    setIsEditOpen(false)
    setEditingId(null)
  }

  const handleSaveEdit = async () => {
    if (!editingId) return
    setSavingEdit(true)
    try {
      const updated = await patchHistoryItem(editingId, {
        activity: editDraft.activity.trim() || null,
        type: editDraft.type,
        url: editDraft.url.trim() || null,
        actions: editDraft.actions.trim() || null,
      })
      upsertRow(updated)
      toast.success('History item updated')
      setIsEditOpen(false)
      setEditingId(null)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to update history')
    } finally {
      setSavingEdit(false)
    }
  }

  const handleRowAction = async (id: string, action: HistoryAction) => {
    setActiveMutationId(id)
    try {
      if (action === 'purge') {
        await deleteHistoryItem(id)
        setData(prev => prev.filter(item => item.id !== id))
        setSelectedIds(prev => {
          const next = new Set(prev)
          next.delete(id)
          return next
        })
        toast.success('History item permanently deleted')
        return
      }

      const updated = await executeHistoryAction(id, action)
      upsertRow(updated)
      if (action === 'delete') toast.success('History item soft-deleted')
      if (action === 'restore') toast.success('History item restored')
      if (action === 'touch') toast.success('Last seen updated')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'History action failed')
    } finally {
      setActiveMutationId(null)
    }
  }

  const handleBulkAction = async (action: HistoryAction) => {
    const ids = [...selectedIds]
    if (ids.length === 0) return
    setBulkMutating(true)
    try {
      if (action === 'purge') {
        await Promise.all(ids.map(id => deleteHistoryItem(id)))
        setData(prev => prev.filter(item => !selectedIds.has(item.id)))
        setSelectedIds(new Set())
        toast.success(`Permanently deleted ${ids.length} history item(s)`)
        return
      }

      const result = await executeHistoryBulkAction(ids, action)
      setData(prev => {
        const updates = new Map(result.items.map(item => [item.id, mapRecordToRow(item)]))
        return prev.map(item => updates.get(item.id) ?? item)
      })

      if (result.failed_ids.length > 0) {
        toast.error(
          `Processed ${result.items.length} items; failed ${result.failed_ids.length}`,
        )
      } else {
        toast.success(`Updated ${result.items.length} history item(s)`)
      }
      setSelectedIds(new Set())
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Bulk action failed')
    } finally {
      setBulkMutating(false)
    }
  }

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
      case 'workspace':
        return <HistoryIcon className="size-3.5" />
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
                  variant="outline"
                  size="sm"
                  onClick={() => void handleBulkAction('delete')}
                  disabled={bulkMutating}
                  className="gap-2"
                >
                  {bulkMutating ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Trash2 className="size-4" />
                  )}
                  Soft Delete
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void handleBulkAction('restore')}
                  disabled={bulkMutating}
                  className="gap-2"
                >
                  <RotateCcw className="size-4" />
                  Restore
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => void handleBulkAction('purge')}
                  disabled={bulkMutating}
                  className="gap-2"
                >
                  <Trash2 className="size-4" />
                  Purge Selected
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

            <Select
              value={typeFilter}
              onValueChange={value => setTypeFilter(value as 'all' | HistoryType)}
            >
              <SelectTrigger className="w-[180px] bg-background">
                <SelectValue placeholder="All Types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                {HISTORY_TYPES.map(type => (
                  <SelectItem key={type} value={type}>
                    {type}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <label className="flex items-center gap-2 text-sm text-muted-foreground select-none">
              <Checkbox
                checked={includeDeleted}
                onCheckedChange={checked => setIncludeDeleted(checked === true)}
              />
              Include Deleted
            </label>

            <Button
              variant="outline"
              size="icon"
              onClick={() => void loadHistory()}
              disabled={loading}
            >
              <RefreshCw className={cn('size-4', loading && 'animate-spin')} />
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
                    <th className="h-12 px-6 text-right align-middle font-medium text-muted-foreground w-[210px] border-b bg-background/50">
                      Actions
                    </th>
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
                            <TruncatedHoverCell
                              value={item.action}
                              className="font-medium"
                            />
                            <TruncatedHoverCell
                              value={item.metadata}
                              className="text-xs text-muted-foreground"
                            />
                          </div>
                        </td>
                        <td className="p-4 align-middle border-none">
                          <div className="flex items-center justify-start gap-2">
                            <Badge
                              variant="secondary"
                              className="font-normal gap-1.5 bg-muted-foreground/10 text-foreground hover:bg-muted-foreground/20"
                            >
                              {getTypeIcon(item.typeLabel)}
                              {item.typeLabel}
                            </Badge>
                            {item.isDeleted && (
                              <Badge
                                variant="outline"
                                className="font-normal border-destructive/40 text-destructive"
                              >
                                deleted
                              </Badge>
                            )}
                          </div>
                        </td>
                        <td className="p-4 align-middle text-right text-muted-foreground font-mono text-xs border-none">
                          {formatTimestamp(item.createdAt)}
                        </td>
                        <td className="p-4 align-middle text-right text-muted-foreground font-mono text-xs border-none">
                          {formatTimestamp(item.lastSeenAt)}
                        </td>
                        <td className="p-4 px-6 align-middle text-right border-none">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => openEditDialog(item)}
                              disabled={activeMutationId === item.id || bulkMutating}
                              className="h-8 w-8 text-muted-foreground/70 hover:text-foreground"
                            >
                              <Pencil className="size-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => void handleRowAction(item.id, 'touch')}
                              disabled={activeMutationId === item.id || bulkMutating}
                              className="h-8 w-8 text-muted-foreground/70 hover:text-foreground"
                            >
                              {activeMutationId === item.id ? (
                                <Loader2 className="size-4 animate-spin" />
                              ) : (
                                <Clock className="size-4" />
                              )}
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() =>
                                void handleRowAction(
                                  item.id,
                                  item.isDeleted ? 'restore' : 'delete',
                                )
                              }
                              disabled={activeMutationId === item.id || bulkMutating}
                              className={cn(
                                'h-8 w-8 transition-all rounded-lg',
                                item.isDeleted
                                  ? 'text-emerald-600/80 hover:text-emerald-700 hover:bg-emerald-500/10'
                                  : 'text-amber-600/80 hover:text-amber-700 hover:bg-amber-500/10',
                              )}
                            >
                              {item.isDeleted ? (
                                <RotateCcw className="size-4" />
                              ) : (
                                <Trash2 className="size-4" />
                              )}
                            </Button>
                          </div>
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

      <Dialog open={isEditOpen} onOpenChange={open => (open ? setIsEditOpen(true) : closeEditDialog())}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Edit History Item</DialogTitle>
            <DialogDescription>
              Update activity details, type, URL, and actions metadata.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-2">
            <div className="grid gap-1.5">
              <span className="text-xs text-muted-foreground uppercase tracking-wide">
                Activity
              </span>
              <Input
                value={editDraft.activity}
                onChange={e =>
                  setEditDraft(prev => ({ ...prev, activity: e.target.value }))
                }
                placeholder="Describe the activity"
              />
            </div>

            <div className="grid gap-1.5">
              <span className="text-xs text-muted-foreground uppercase tracking-wide">
                Type
              </span>
              <Select
                value={editDraft.type}
                onValueChange={value =>
                  setEditDraft(prev => ({ ...prev, type: value as HistoryType }))
                }
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {HISTORY_TYPES.map(type => (
                    <SelectItem key={type} value={type}>
                      {type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-1.5">
              <span className="text-xs text-muted-foreground uppercase tracking-wide">
                URL
              </span>
              <Input
                value={editDraft.url}
                onChange={e => setEditDraft(prev => ({ ...prev, url: e.target.value }))}
                placeholder="https://..."
              />
            </div>

            <div className="grid gap-1.5">
              <span className="text-xs text-muted-foreground uppercase tracking-wide">
                Actions
              </span>
              <Input
                value={editDraft.actions}
                onChange={e =>
                  setEditDraft(prev => ({ ...prev, actions: e.target.value }))
                }
                placeholder="delete, pinned, reviewed"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={closeEditDialog} disabled={savingEdit}>
              Cancel
            </Button>
            <Button onClick={() => void handleSaveEdit()} disabled={savingEdit}>
              {savingEdit ? <Loader2 className="size-4 animate-spin" /> : null}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default History
