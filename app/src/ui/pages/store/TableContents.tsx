import { useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { cn } from '@/lib/utils'
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select'
import {
    ChevronLeft,
    ChevronRight,
    Search,
    Table2,
    Download,
    RefreshCw,
    ArrowUpDown,
    ChevronsLeft,
    ChevronsRight
} from 'lucide-react'

// Generate mock table data
const generateMockData = (_tableName: string, count: number) => {
    const statuses = ['active', 'inactive', 'pending', 'suspended']

    return Array.from({ length: count }).map((_, i) => ({
        id: i + 1,
        name: `User ${i + 1}`,
        email: `user${i + 1}@example.com`,
        status: statuses[Math.floor(Math.random() * statuses.length)],
        created_at: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        updated_at: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    }))
}

const getColorForDb = (dbId: string) => {
    const colorMap: Record<string, { text: string; bg: string }> = {
        'basic': { text: 'text-blue-400', bg: 'bg-blue-400/10' },
        'history': { text: 'text-purple-400', bg: 'bg-purple-400/10' },
        'scrapes': { text: 'text-green-400', bg: 'bg-green-400/10' },
        'research': { text: 'text-orange-400', bg: 'bg-orange-400/10' },
    }
    return colorMap[dbId] || colorMap['basic']
}

const TableContents = () => {
    const { id, tableName } = useParams()
    const [searchQuery, setSearchQuery] = useState('')
    const [rowsPerPage, setRowsPerPage] = useState(25)
    const [currentPage, setCurrentPage] = useState(1)
    const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set())
    const [sortCol, setSortCol] = useState<string | null>(null)
    const [sortAsc, setSortAsc] = useState(true)

    const dbId = id || 'basic'
    const colors = getColorForDb(dbId)
    const table = tableName || 'users'

    // Generate mock data
    const allData = useMemo(() => generateMockData(table, 156), [table])
    const columns = Object.keys(allData[0] || {})

    // Filter and sort
    const filteredData = useMemo(() => {
        let data = allData.filter(row =>
            Object.values(row).some(v =>
                String(v).toLowerCase().includes(searchQuery.toLowerCase())
            )
        )
        if (sortCol) {
            data = [...data].sort((a, b) => {
                const aVal = a[sortCol as keyof typeof a]
                const bVal = b[sortCol as keyof typeof b]
                const cmp = String(aVal).localeCompare(String(bVal))
                return sortAsc ? cmp : -cmp
            })
        }
        return data
    }, [allData, searchQuery, sortCol, sortAsc])

    // Pagination
    const totalPages = Math.ceil(filteredData.length / rowsPerPage)
    const paginatedData = useMemo(() => {
        const start = (currentPage - 1) * rowsPerPage
        return filteredData.slice(start, start + rowsPerPage)
    }, [filteredData, currentPage, rowsPerPage])

    const toggleSort = (col: string) => {
        if (sortCol === col) setSortAsc(!sortAsc)
        else { setSortCol(col); setSortAsc(true) }
    }

    const toggleSelectAll = () => {
        if (selectedRows.size === paginatedData.length) {
            setSelectedRows(new Set())
        } else {
            setSelectedRows(new Set(paginatedData.map(r => r.id)))
        }
    }

    const toggleSelect = (id: number) => {
        const next = new Set(selectedRows)
        if (next.has(id)) next.delete(id)
        else next.add(id)
        setSelectedRows(next)
    }

    const getStatusBadge = (status: string) => {
        const config: Record<string, string> = {
            active: 'bg-green-500/20 text-green-400',
            inactive: 'bg-muted-foreground/20 text-muted-foreground',
            pending: 'bg-yellow-500/20 text-yellow-400',
            suspended: 'bg-red-500/20 text-red-400',
        }
        return config[status] || config.inactive
    }

    return (
        <div className="flex flex-col h-full w-full bg-muted/10 overflow-hidden animate-in fade-in duration-500">
            {/* Header */}
            <div className="shrink-0 border-b bg-background/50 backdrop-blur-sm sticky top-0 z-30">
                <div className="w-full px-8 py-6">
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-4">
                            <div className={cn("size-14 rounded-2xl flex items-center justify-center", colors.bg)}>
                                <Table2 className={cn("size-7", colors.text)} />
                            </div>
                            <div>
                                <h1 className="text-2xl font-semibold font-mono">{table}</h1>
                                <p className="text-sm text-muted-foreground mt-0.5">
                                    {filteredData.length} rows • {columns.length} columns
                                </p>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            {selectedRows.size > 0 && (
                                <Badge variant="secondary" className="mr-2">{selectedRows.size} selected</Badge>
                            )}
                            <Button variant="outline" size="sm" className="gap-2">
                                <RefreshCw className="size-4" />Refresh
                            </Button>
                            <Button variant="outline" size="sm" className="gap-2">
                                <Download className="size-4" />Export
                            </Button>
                        </div>
                    </div>
                    <div className="flex items-center gap-4">
                        <div className="relative flex-1 max-w-md">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                            <Input placeholder="Search in table..." value={searchQuery} onChange={e => { setSearchQuery(e.target.value); setCurrentPage(1) }} className="pl-9 bg-background" />
                        </div>
                        <Select value={String(rowsPerPage)} onValueChange={v => { setRowsPerPage(Number(v)); setCurrentPage(1) }}>
                            <SelectTrigger className="w-[130px]"><SelectValue /></SelectTrigger>
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

            {/* Table Content */}
            <div className="flex-1 overflow-auto">
                <table className="w-full text-sm border-separate border-spacing-0">
                    <thead className="sticky top-0 z-20 bg-muted/10 backdrop-blur-md">
                        <tr>
                            <th className="h-12 px-4 text-left font-medium text-muted-foreground w-[50px] border-b bg-background/50">
                                <Checkbox checked={paginatedData.length > 0 && selectedRows.size === paginatedData.length} onCheckedChange={toggleSelectAll} />
                            </th>
                            {columns.map(col => (
                                <th key={col} className="h-12 px-4 text-left font-medium text-muted-foreground border-b bg-background/50 cursor-pointer hover:text-foreground" onClick={() => toggleSort(col)}>
                                    <div className="flex items-center gap-2">
                                        {col}
                                        {sortCol === col && <ArrowUpDown className={cn("size-3", !sortAsc && "rotate-180")} />}
                                    </div>
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {paginatedData.length === 0 ? (
                            <tr><td colSpan={columns.length + 1} className="p-8 text-center text-muted-foreground">No data found.</td></tr>
                        ) : paginatedData.map(row => (
                            <tr key={row.id} className={cn("hover:bg-muted/10 transition-colors", selectedRows.has(row.id) && "bg-muted/20")}>
                                <td className="p-4 px-4"><Checkbox checked={selectedRows.has(row.id)} onCheckedChange={() => toggleSelect(row.id)} /></td>
                                {columns.map(col => (
                                    <td key={col} className="p-4 font-mono text-sm">
                                        {col === 'status' ? (
                                            <Badge className={cn("font-normal", getStatusBadge(row[col as keyof typeof row] as string))}>{String(row[col as keyof typeof row])}</Badge>
                                        ) : col === 'id' ? (
                                            <span className="text-muted-foreground">{String(row[col as keyof typeof row])}</span>
                                        ) : (
                                            String(row[col as keyof typeof row])
                                        )}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Pagination Footer */}
            <div className="shrink-0 border-t bg-background/50 backdrop-blur-sm px-8 py-4">
                <div className="flex items-center justify-between">
                    <p className="text-sm text-muted-foreground">
                        Showing {((currentPage - 1) * rowsPerPage) + 1} to {Math.min(currentPage * rowsPerPage, filteredData.length)} of {filteredData.length} rows
                    </p>
                    <div className="flex items-center gap-2">
                        <Button variant="outline" size="icon" disabled={currentPage === 1} onClick={() => setCurrentPage(1)}><ChevronsLeft className="size-4" /></Button>
                        <Button variant="outline" size="icon" disabled={currentPage === 1} onClick={() => setCurrentPage(p => p - 1)}><ChevronLeft className="size-4" /></Button>
                        <span className="text-sm px-3">Page {currentPage} of {totalPages}</span>
                        <Button variant="outline" size="icon" disabled={currentPage === totalPages} onClick={() => setCurrentPage(p => p + 1)}><ChevronRight className="size-4" /></Button>
                        <Button variant="outline" size="icon" disabled={currentPage === totalPages} onClick={() => setCurrentPage(totalPages)}><ChevronsRight className="size-4" /></Button>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default TableContents