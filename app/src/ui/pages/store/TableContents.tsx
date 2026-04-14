import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { cn } from '@/lib/utils'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  listDatabaseTableRows,
  type DatabaseTableRowsResponse,
} from '@/lib/apis'
import {
  ChevronLeft,
  ChevronRight,
  Search,
  Table2,
  Download,
  RefreshCw,
  ArrowUpDown,
  ChevronsLeft,
  ChevronsRight,
  Loader2,
} from 'lucide-react'

const getColorForDb = (dbId: string) => {
  const colorMap: Record<string, { text: string; bg: string }> = {
    main: { text: 'text-blue-400', bg: 'bg-blue-400/10' },
    history: { text: 'text-purple-400', bg: 'bg-purple-400/10' },
    scrapes: { text: 'text-green-400', bg: 'bg-green-400/10' },
    researches: { text: 'text-orange-400', bg: 'bg-orange-400/10' },
    buckets: { text: 'text-pink-400', bg: 'bg-pink-400/10' },
    chats: { text: 'text-cyan-400', bg: 'bg-cyan-400/10' },
    logs: { text: 'text-amber-400', bg: 'bg-amber-400/10' },
    vector_chroma: { text: 'text-violet-400', bg: 'bg-violet-400/10' },
  }
  return colorMap[dbId] || colorMap.main
}

const stringifyCellValue = (value: unknown): string => {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value)
    } catch {
      return String(value)
    }
  }
  return String(value)
}

const CELL_TRUNCATE_LIMIT = 40

const truncateCellValue = (value: string, maxChars: number = CELL_TRUNCATE_LIMIT): string => {
  if (value.length <= maxChars) return value
  return `${value.slice(0, maxChars)}...`
}

const TableContents = () => {
  const { id, tableName } = useParams()
  const [searchQuery, setSearchQuery] = useState('')
  const [rowsPerPage, setRowsPerPage] = useState(25)
  const [currentPage, setCurrentPage] = useState(1)
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set())
  const [sortCol, setSortCol] = useState<string | null>(null)
  const [sortAsc, setSortAsc] = useState(true)
  const [openCellKey, setOpenCellKey] = useState<string | null>(null)
  const [rowsResponse, setRowsResponse] = useState<DatabaseTableRowsResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshVersion, setRefreshVersion] = useState(0)

  const dbId = id || ''
  const table = tableName || ''
  const colors = getColorForDb(dbId)

  useEffect(() => {
    setCurrentPage(1)
    setSelectedRows(new Set())
    setSearchQuery('')
  }, [dbId, table])

  useEffect(() => {
    if (!dbId || !table) {
      setRowsResponse(null)
      setIsLoading(false)
      setError('Database id or table name is missing')
      return
    }

    let isCancelled = false

    const loadRows = async () => {
      setIsLoading(true)
      setError(null)

      try {
        const response = await listDatabaseTableRows(dbId, table, {
          page: currentPage,
          size: rowsPerPage,
          sortBy: sortCol ?? undefined,
          sortOrder: sortAsc ? 'asc' : 'desc',
        })

        if (isCancelled) return

        setRowsResponse(response)
        setSelectedRows(new Set())

        if (response.total_pages > 0 && currentPage > response.total_pages) {
          setCurrentPage(response.total_pages)
        }
      } catch (err) {
        if (isCancelled) return
        setRowsResponse(null)
        setError(err instanceof Error ? err.message : 'Failed to load table rows')
      } finally {
        if (!isCancelled) {
          setIsLoading(false)
        }
      }
    }

    void loadRows()

    return () => {
      isCancelled = true
    }
  }, [dbId, table, currentPage, rowsPerPage, sortCol, sortAsc, refreshVersion])

  const columns = useMemo(
    () => (rowsResponse?.columns || []).map((col) => col.name),
    [rowsResponse?.columns],
  )

  const rawRows = rowsResponse?.items || []

  const filteredRows = useMemo(() => {
    if (!searchQuery.trim()) return rawRows

    const needle = searchQuery.trim().toLowerCase()
    return rawRows.filter((row) =>
      Object.values(row).some((value) => stringifyCellValue(value).toLowerCase().includes(needle)),
    )
  }, [rawRows, searchQuery])

  const getRowKey = (row: Record<string, unknown>, index: number) => {
    const candidate = row.id ?? row.uuid ?? row._id
    if (typeof candidate === 'string' || typeof candidate === 'number') {
      return String(candidate)
    }
    return `${rowsResponse?.offset || 0}-${index}`
  }

  const visibleRows = filteredRows
  const totalPages = rowsResponse?.total_pages || 0
  const totalItems = rowsResponse?.total_items || 0
  const effectiveTotalPages = totalPages > 0 ? totalPages : 1

  const toggleSort = (col: string) => {
    if (sortCol === col) {
      setSortAsc(!sortAsc)
    } else {
      setSortCol(col)
      setSortAsc(true)
    }
    setCurrentPage(1)
  }

  const toggleSelectAll = () => {
    if (selectedRows.size === visibleRows.length) {
      setSelectedRows(new Set())
    } else {
      setSelectedRows(new Set(visibleRows.map((row, idx) => getRowKey(row, idx))))
    }
  }

  const toggleSelect = (rowId: string) => {
    const next = new Set(selectedRows)
    if (next.has(rowId)) next.delete(rowId)
    else next.add(rowId)
    setSelectedRows(next)
  }

  useEffect(() => {
    setOpenCellKey(null)
  }, [currentPage, rowsPerPage, searchQuery, dbId, table])

  const handleExportCsv = () => {
    if (visibleRows.length === 0 || columns.length === 0) return

    const escapeCsvCell = (value: string) => `"${value.replace(/"/g, '""')}"`
    const header = columns.map(escapeCsvCell).join(',')
    const body = visibleRows
      .map((row) => columns.map((col) => escapeCsvCell(stringifyCellValue(row[col]))).join(','))
      .join('\n')

    const csv = `${header}\n${body}`
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${table}-page-${currentPage}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  if (isLoading && !rowsResponse) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="size-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error && !rowsResponse) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="text-sm text-destructive">Failed to load table rows: {error}</div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full w-full min-w-0 bg-muted/10 overflow-hidden animate-in fade-in duration-500">
      <div className="shrink-0 border-b bg-background/50 backdrop-blur-sm sticky top-0 z-30">
        <div className="w-full px-8 py-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <div className={cn('size-14 rounded-2xl flex items-center justify-center', colors.bg)}>
                <Table2 className={cn('size-7', colors.text)} />
              </div>
              <div>
                <h1 className="text-2xl font-semibold font-mono">{table || 'table'}</h1>
                <p className="text-sm text-muted-foreground mt-0.5">
                  {totalItems.toLocaleString()} rows • {columns.length} columns
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {selectedRows.size > 0 && (
                <Badge variant="secondary" className="mr-2">
                  {selectedRows.size} selected
                </Badge>
              )}
              <Button
                variant="outline"
                size="sm"
                className="gap-2"
                onClick={() => setRefreshVersion((prev) => prev + 1)}
                disabled={isLoading}
              >
                <RefreshCw className={cn('size-4', isLoading && 'animate-spin')} />
                Refresh
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="gap-2"
                onClick={handleExportCsv}
                disabled={visibleRows.length === 0}
              >
                <Download className="size-4" />
                Export
              </Button>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
              <Input
                placeholder="Search in current page..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 bg-background"
              />
            </div>
            <Select
              value={String(rowsPerPage)}
              onValueChange={(v) => {
                setRowsPerPage(Number(v))
                setCurrentPage(1)
              }}
            >
              <SelectTrigger className="w-[130px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="10">10 rows</SelectItem>
                <SelectItem value="25">25 rows</SelectItem>
                <SelectItem value="50">50 rows</SelectItem>
                <SelectItem value="100">100 rows</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      <div className="flex-1 min-w-0 overflow-x-auto overflow-y-auto">
        <table className="w-max min-w-full text-sm border-separate border-spacing-0">
          <thead className="sticky top-0 z-20 bg-muted/10 backdrop-blur-md">
            <tr>
              <th className="h-12 px-4 text-left font-medium text-muted-foreground w-[50px] border-b bg-background/50">
                <Checkbox
                  checked={visibleRows.length > 0 && selectedRows.size === visibleRows.length}
                  onCheckedChange={toggleSelectAll}
                />
              </th>
              {columns.map((col) => (
                <th
                  key={col}
                  className="h-12 px-4 text-left font-medium text-muted-foreground border-b bg-background/50 cursor-pointer hover:text-foreground"
                  onClick={() => toggleSort(col)}
                >
                  <div className="flex items-center gap-2">
                    {col}
                    {sortCol === col && <ArrowUpDown className={cn('size-3', !sortAsc && 'rotate-180')} />}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleRows.length === 0 ? (
              <tr>
                <td colSpan={columns.length + 1} className="p-8 text-center text-muted-foreground">
                  No data found.
                </td>
              </tr>
            ) : (
              visibleRows.map((row, rowIndex) => {
                const rowKey = getRowKey(row, rowIndex)
                return (
                  <tr
                    key={rowKey}
                    className={cn('hover:bg-muted/10 transition-colors', selectedRows.has(rowKey) && 'bg-muted/20')}
                  >
                    <td className="p-4 px-4">
                      <Checkbox checked={selectedRows.has(rowKey)} onCheckedChange={() => toggleSelect(rowKey)} />
                    </td>
                    {columns.map((col) => {
                      const rawValue = row[col]
                      const value = stringifyCellValue(rawValue)
                      const isStatus = col.toLowerCase().includes('status')
                      const shouldTruncate = value.length > CELL_TRUNCATE_LIMIT
                      const cellKey = `${rowKey}:${col}`

                      return (
                        <td key={col} className="p-0 font-mono text-sm align-top whitespace-nowrap">
                          {shouldTruncate ? (
                            <Popover
                              open={openCellKey === cellKey}
                              onOpenChange={(open) => {
                                if (!open && openCellKey === cellKey) {
                                  setOpenCellKey(null)
                                }
                              }}
                            >
                              <PopoverTrigger asChild>
                                <button
                                  type="button"
                                  className="block w-full h-full px-4 py-4 text-left hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                                  onMouseEnter={() => setOpenCellKey(cellKey)}
                                  onMouseLeave={() =>
                                    setOpenCellKey((current) => (current === cellKey ? null : current))
                                  }
                                  onClick={() =>
                                    setOpenCellKey((current) => (current === cellKey ? null : cellKey))
                                  }
                                >
                                  {isStatus && typeof rawValue === 'string' ? (
                                    <Badge variant="secondary" className="font-normal max-w-[40ch] truncate">
                                      {truncateCellValue(value)}
                                    </Badge>
                                  ) : (
                                    <span className="block whitespace-nowrap overflow-hidden text-ellipsis max-w-[40ch]">
                                      {truncateCellValue(value)}
                                    </span>
                                  )}
                                </button>
                              </PopoverTrigger>
                              <PopoverContent
                                align="start"
                                side="top"
                                className="max-w-[min(80vw,60rem)] whitespace-pre-wrap break-all font-mono text-xs"
                              >
                                {value}
                              </PopoverContent>
                            </Popover>
                          ) : isStatus && typeof rawValue === 'string' ? (
                            <div className="px-4 py-4">
                              <Badge variant="secondary" className="font-normal">
                                {value}
                              </Badge>
                            </div>
                          ) : (
                            <span className="block px-4 py-4 whitespace-nowrap">{value}</span>
                          )}
                        </td>
                      )
                    })}
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="shrink-0 border-t bg-background/50 backdrop-blur-sm px-8 py-4">
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {totalItems > 0
              ? `Showing ${(rowsResponse?.offset || 0) + 1} to ${(rowsResponse?.offset || 0) + (rowsResponse?.items.length || 0)} of ${totalItems} rows`
              : 'No rows available'}
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="icon"
              disabled={currentPage <= 1 || isLoading}
              onClick={() => setCurrentPage(1)}
            >
              <ChevronsLeft className="size-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              disabled={currentPage <= 1 || isLoading}
              onClick={() => setCurrentPage((p) => p - 1)}
            >
              <ChevronLeft className="size-4" />
            </Button>
            <span className="text-sm px-3">
              Page {totalPages > 0 ? currentPage : 0} of {totalPages > 0 ? totalPages : 0}
            </span>
            <Button
              variant="outline"
              size="icon"
              disabled={currentPage >= effectiveTotalPages || totalPages === 0 || isLoading}
              onClick={() => setCurrentPage((p) => p + 1)}
            >
              <ChevronRight className="size-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              disabled={currentPage >= effectiveTotalPages || totalPages === 0 || isLoading}
              onClick={() => setCurrentPage(effectiveTotalPages)}
            >
              <ChevronsRight className="size-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default TableContents
