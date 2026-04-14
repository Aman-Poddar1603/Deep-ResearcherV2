import { useEffect, useMemo, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  getDatabase,
  listDatabaseTables,
  type DatabaseDetailRecord,
  type DatabaseTableRecord,
} from '@/lib/apis'
import {
  Search,
  Database,
  Table2,
  FileText,
  Clock,
  ArrowUpDown,
  HardDrive,
  Layers,
  Eye,
  Loader2,
} from 'lucide-react'

const getColorForDb = (dbColor?: string, dbId?: string) => {
  const colorMap: Record<string, { text: string; bg: string }> = {
    'blue-400': { text: 'text-blue-400', bg: 'bg-blue-400/10' },
    'purple-400': { text: 'text-purple-400', bg: 'bg-purple-400/10' },
    'green-400': { text: 'text-green-400', bg: 'bg-green-400/10' },
    'orange-400': { text: 'text-orange-400', bg: 'bg-orange-400/10' },
    'pink-400': { text: 'text-pink-400', bg: 'bg-pink-400/10' },
    'cyan-400': { text: 'text-cyan-400', bg: 'bg-cyan-400/10' },
    'amber-400': { text: 'text-amber-400', bg: 'bg-amber-400/10' },
    'violet-400': { text: 'text-violet-400', bg: 'bg-violet-400/10' },
  }

  if (dbColor && colorMap[dbColor]) {
    return colorMap[dbColor]
  }

  const fallbackById: Record<string, { text: string; bg: string }> = {
    main: colorMap['blue-400'],
    history: colorMap['purple-400'],
    scrapes: colorMap['green-400'],
    researches: colorMap['orange-400'],
    buckets: colorMap['pink-400'],
    chats: colorMap['cyan-400'],
    logs: colorMap['amber-400'],
    vector_chroma: colorMap['violet-400'],
  }

  return (dbId && fallbackById[dbId]) || colorMap['blue-400']
}

const sizeToNumber = (size: string) => {
  const match = size.trim().match(/^([0-9.]+)\s*(B|KB|MB|GB|TB)$/i)
  if (!match) return 0

  const value = parseFloat(match[1])
  const unit = match[2].toUpperCase()
  const multipliers: Record<string, number> = {
    B: 1,
    KB: 1024,
    MB: 1024 ** 2,
    GB: 1024 ** 3,
    TB: 1024 ** 4,
  }

  return value * (multipliers[unit] || 1)
}

const Tables = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [sortOrder, setSortOrder] = useState<'name' | 'rows' | 'size'>('rows')
  const [sortAsc, setSortAsc] = useState(false)
  const [database, setDatabase] = useState<DatabaseDetailRecord | null>(null)
  const [tables, setTables] = useState<DatabaseTableRecord[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const dbId = id || ''
  const colors = getColorForDb(database?.color, dbId)

  useEffect(() => {
    if (!dbId) {
      setError('Database id is missing')
      setIsLoading(false)
      return
    }

    let isCancelled = false

    const loadData = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const [databaseDetail, tableResponse] = await Promise.all([
          getDatabase(dbId),
          listDatabaseTables(dbId, { page: 1, size: 1000 }),
        ])

        if (isCancelled) return
        setDatabase(databaseDetail)
        setTables(tableResponse.items)
      } catch (err) {
        if (isCancelled) return
        setDatabase(null)
        setTables([])
        setError(err instanceof Error ? err.message : 'Failed to load tables')
      } finally {
        if (!isCancelled) {
          setIsLoading(false)
        }
      }
    }

    void loadData()

    return () => {
      isCancelled = true
    }
  }, [dbId])

  const filteredTables = useMemo(() => {
    const filtered = tables.filter((t) =>
      t.name.toLowerCase().includes(searchQuery.toLowerCase()),
    )

    return [...filtered].sort((a, b) => {
      let cmp = 0
      if (sortOrder === 'name') cmp = a.name.localeCompare(b.name)
      else if (sortOrder === 'rows') cmp = b.rows - a.rows
      else cmp = sizeToNumber(b.size) - sizeToNumber(a.size)
      return sortAsc ? -cmp : cmp
    })
  }, [tables, searchQuery, sortOrder, sortAsc])

  const toggleSort = (s: typeof sortOrder) => {
    if (sortOrder === s) setSortAsc(!sortAsc)
    else {
      setSortOrder(s)
      setSortAsc(false)
    }
  }

  const totalStats = useMemo(
    () => ({
      rows: tables.reduce((acc, t) => acc + t.rows, 0),
      columns: tables.reduce((acc, t) => acc + t.columns, 0),
    }),
    [tables],
  )

  const dbName = database?.name || dbId || 'Database'

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="size-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="text-sm text-destructive">Failed to load tables: {error}</div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full w-full bg-muted/10 overflow-hidden animate-in fade-in duration-500">
      <div className="shrink-0 border-b bg-background/50 backdrop-blur-sm sticky top-0 z-30">
        <div className="w-full px-8 py-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <div className={cn('size-14 rounded-2xl flex items-center justify-center', colors.bg)}>
                <Database className={cn('size-7', colors.text)} />
              </div>
              <div>
                <h1 className="text-2xl font-semibold">{dbName} Tables</h1>
                <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1.5">
                    <Table2 className="size-4" />
                    {tables.length} tables
                  </span>
                  <span className="flex items-center gap-1.5">
                    <FileText className="size-4" />
                    {totalStats.rows.toLocaleString()} rows
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Layers className="size-4" />
                    {totalStats.columns} columns
                  </span>
                </div>
              </div>
            </div>
          </div>
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              placeholder="Search tables..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 bg-background"
            />
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto w-full pb-24">
        <table className="w-full text-sm border-separate border-spacing-0">
          <thead className="sticky top-0 z-20 bg-muted/10 backdrop-blur-md">
            <tr>
              <th className="h-12 px-6 text-left font-medium text-muted-foreground w-[50px] border-b bg-background/50">
                <Table2 className="size-4" />
              </th>
              <th
                className="h-12 px-4 text-left font-medium text-muted-foreground border-b bg-background/50 cursor-pointer"
                onClick={() => toggleSort('name')}
              >
                <div className="flex items-center gap-2">
                  Name
                  {sortOrder === 'name' && <ArrowUpDown className={cn('size-3', sortAsc && 'rotate-180')} />}
                </div>
              </th>
              <th className="h-12 px-4 text-left font-medium text-muted-foreground w-[250px] border-b bg-background/50">Description</th>
              <th
                className="h-12 px-4 text-right font-medium text-muted-foreground w-[100px] border-b bg-background/50 cursor-pointer"
                onClick={() => toggleSort('rows')}
              >
                <div className="flex items-center justify-end gap-2">
                  Rows
                  {sortOrder === 'rows' && <ArrowUpDown className={cn('size-3', sortAsc && 'rotate-180')} />}
                </div>
              </th>
              <th className="h-12 px-4 text-right font-medium text-muted-foreground w-[80px] border-b bg-background/50">Cols</th>
              <th
                className="h-12 px-4 text-right font-medium text-muted-foreground w-[100px] border-b bg-background/50 cursor-pointer"
                onClick={() => toggleSort('size')}
              >
                <div className="flex items-center justify-end gap-2">
                  Size
                  {sortOrder === 'size' && <ArrowUpDown className={cn('size-3', sortAsc && 'rotate-180')} />}
                </div>
              </th>
              <th className="h-12 px-4 text-right font-medium text-muted-foreground w-[120px] border-b bg-background/50">Modified</th>
              <th className="h-12 px-6 w-[60px] border-b bg-background/50"></th>
            </tr>
          </thead>
          <tbody>
            {filteredTables.length === 0 ? (
              <tr>
                <td colSpan={8} className="p-4 text-center text-muted-foreground h-24">
                  No tables found.
                </td>
              </tr>
            ) : (
              filteredTables.map((t) => (
                <tr
                  key={t.name}
                  className="hover:bg-muted/10 cursor-pointer group"
                  onClick={() => navigate(`/data/databases/${encodeURIComponent(dbId)}/tables/${encodeURIComponent(t.name)}`)}
                >
                  <td className="p-4 px-6">
                    <div className={cn('p-2 rounded-lg w-fit', colors.bg)}>
                      <Table2 className={cn('size-4', colors.text)} />
                    </div>
                  </td>
                  <td className="p-4">
                    <span className="font-medium font-mono text-sm group-hover:text-primary">{t.name}</span>
                  </td>
                  <td className="p-4 text-muted-foreground text-sm">{t.description || '-'}</td>
                  <td className="p-4 text-right">
                    <Badge variant="secondary" className="font-mono text-xs">
                      {t.rows.toLocaleString()}
                    </Badge>
                  </td>
                  <td className="p-4 text-right text-muted-foreground font-mono">{t.columns}</td>
                  <td className="p-4 text-right text-muted-foreground">
                    <div className="flex items-center justify-end gap-1">
                      <HardDrive className="size-3.5" />
                      {t.size}
                    </div>
                  </td>
                  <td className="p-4 text-right text-muted-foreground text-xs">
                    <div className="flex items-center justify-end gap-1">
                      <Clock className="size-3.5" />
                      {t.lastModified}
                    </div>
                  </td>
                  <td className="p-4 px-6 text-right">
                    <Button variant="ghost" size="icon" className="h-8 w-8 opacity-0 group-hover:opacity-100">
                      <Eye className="size-4" />
                    </Button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default Tables
