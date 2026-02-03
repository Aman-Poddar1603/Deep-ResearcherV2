import { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  Search,
  Database,
  Table2,
  FileText,
  Clock,
  ArrowUpDown,
  HardDrive,
  Layers,
  Eye
} from 'lucide-react'

interface TableInfo {
  name: string
  rows: number
  columns: number
  size: string
  lastModified: string
  description: string
}

const mockTables: Record<string, TableInfo[]> = {
  'basic': [
    { name: 'users', rows: 156, columns: 12, size: '245 KB', lastModified: '2 mins ago', description: 'User accounts and profiles' },
    { name: 'settings', rows: 89, columns: 8, size: '67 KB', lastModified: '1 hour ago', description: 'Application settings' },
    { name: 'preferences', rows: 234, columns: 15, size: '312 KB', lastModified: '30 mins ago', description: 'User preferences' },
    { name: 'workspaces', rows: 45, columns: 10, size: '156 KB', lastModified: '3 hours ago', description: 'Workspace definitions' },
    { name: 'api_keys', rows: 23, columns: 6, size: '34 KB', lastModified: '1 day ago', description: 'API authentication keys' },
    { name: 'sessions', rows: 567, columns: 9, size: '890 KB', lastModified: '5 mins ago', description: 'Active user sessions' },
    { name: 'notifications', rows: 89, columns: 7, size: '123 KB', lastModified: '10 mins ago', description: 'Notifications queue' },
    { name: 'cache', rows: 44, columns: 4, size: '567 KB', lastModified: '1 min ago', description: 'Cached data' },
  ],
  'history': [
    { name: 'activity_logs', rows: 8934, columns: 14, size: '12.4 MB', lastModified: '30 secs ago', description: 'Activity logs' },
    { name: 'search_history', rows: 3456, columns: 8, size: '2.8 MB', lastModified: '2 mins ago', description: 'Search queries' },
    { name: 'chat_history', rows: 2123, columns: 11, size: '1.9 MB', lastModified: '5 mins ago', description: 'Chat archive' },
    { name: 'file_access_logs', rows: 567, columns: 7, size: '890 KB', lastModified: '10 mins ago', description: 'File access audit' },
    { name: 'error_logs', rows: 154, columns: 9, size: '678 KB', lastModified: '1 hour ago', description: 'Application errors' },
  ],
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

const dbNames: Record<string, string> = {
  'basic': 'Basic', 'history': 'History', 'scrapes': 'Scrapes', 'research': 'Research',
}

const Tables = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [sortOrder, setSortOrder] = useState<'name' | 'rows' | 'size'>('rows')
  const [sortAsc, setSortAsc] = useState(false)

  const dbId = id || 'basic'
  const colors = getColorForDb(dbId)
  const tables = mockTables[dbId] || mockTables['basic']

  const filteredTables = useMemo(() => {
    const filtered = tables.filter(t =>
      t.name.toLowerCase().includes(searchQuery.toLowerCase())
    )
    return [...filtered].sort((a, b) => {
      let cmp = 0
      if (sortOrder === 'name') cmp = a.name.localeCompare(b.name)
      else if (sortOrder === 'rows') cmp = b.rows - a.rows
      else cmp = parseFloat(b.size) - parseFloat(a.size)
      return sortAsc ? -cmp : cmp
    })
  }, [tables, searchQuery, sortOrder, sortAsc])

  const toggleSort = (s: typeof sortOrder) => {
    if (sortOrder === s) setSortAsc(!sortAsc)
    else { setSortOrder(s); setSortAsc(false) }
  }

  const totalStats = { rows: tables.reduce((a, t) => a + t.rows, 0), columns: tables.reduce((a, t) => a + t.columns, 0) }

  return (
    <div className="flex flex-col h-full w-full bg-muted/10 overflow-hidden animate-in fade-in duration-500">
      <div className="shrink-0 border-b bg-background/50 backdrop-blur-sm sticky top-0 z-30">
        <div className="w-full px-8 py-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <div className={cn("size-14 rounded-2xl flex items-center justify-center", colors.bg)}>
                <Database className={cn("size-7", colors.text)} />
              </div>
              <div>
                <h1 className="text-2xl font-semibold">{dbNames[dbId]} Tables</h1>
                <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1.5"><Table2 className="size-4" />{tables.length} tables</span>
                  <span className="flex items-center gap-1.5"><FileText className="size-4" />{totalStats.rows.toLocaleString()} rows</span>
                  <span className="flex items-center gap-1.5"><Layers className="size-4" />{totalStats.columns} columns</span>
                </div>
              </div>
            </div>
          </div>
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input placeholder="Search tables..." value={searchQuery} onChange={e => setSearchQuery(e.target.value)} className="pl-9 bg-background" />
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto w-full pb-24">
        <table className="w-full text-sm border-separate border-spacing-0">
          <thead className="sticky top-0 z-20 bg-muted/10 backdrop-blur-md">
            <tr>
              <th className="h-12 px-6 text-left font-medium text-muted-foreground w-[50px] border-b bg-background/50"><Table2 className="size-4" /></th>
              <th className="h-12 px-4 text-left font-medium text-muted-foreground border-b bg-background/50 cursor-pointer" onClick={() => toggleSort('name')}>
                <div className="flex items-center gap-2">Name{sortOrder === 'name' && <ArrowUpDown className={cn("size-3", sortAsc && "rotate-180")} />}</div>
              </th>
              <th className="h-12 px-4 text-left font-medium text-muted-foreground w-[250px] border-b bg-background/50">Description</th>
              <th className="h-12 px-4 text-right font-medium text-muted-foreground w-[100px] border-b bg-background/50 cursor-pointer" onClick={() => toggleSort('rows')}>
                <div className="flex items-center justify-end gap-2">Rows{sortOrder === 'rows' && <ArrowUpDown className={cn("size-3", sortAsc && "rotate-180")} />}</div>
              </th>
              <th className="h-12 px-4 text-right font-medium text-muted-foreground w-[80px] border-b bg-background/50">Cols</th>
              <th className="h-12 px-4 text-right font-medium text-muted-foreground w-[100px] border-b bg-background/50 cursor-pointer" onClick={() => toggleSort('size')}>
                <div className="flex items-center justify-end gap-2">Size{sortOrder === 'size' && <ArrowUpDown className={cn("size-3", sortAsc && "rotate-180")} />}</div>
              </th>
              <th className="h-12 px-4 text-right font-medium text-muted-foreground w-[120px] border-b bg-background/50">Modified</th>
              <th className="h-12 px-6 w-[60px] border-b bg-background/50"></th>
            </tr>
          </thead>
          <tbody>
            {filteredTables.length === 0 ? (
              <tr><td colSpan={8} className="p-4 text-center text-muted-foreground h-24">No tables found.</td></tr>
            ) : filteredTables.map((t) => (
              <tr key={t.name} className="hover:bg-muted/10 cursor-pointer group" onClick={() => navigate(`/data/databases/${dbId}/tables/${t.name}`)}>
                <td className="p-4 px-6"><div className={cn("p-2 rounded-lg w-fit", colors.bg)}><Table2 className={cn("size-4", colors.text)} /></div></td>
                <td className="p-4"><span className="font-medium font-mono text-sm group-hover:text-primary">{t.name}</span></td>
                <td className="p-4 text-muted-foreground text-sm">{t.description}</td>
                <td className="p-4 text-right"><Badge variant="secondary" className="font-mono text-xs">{t.rows.toLocaleString()}</Badge></td>
                <td className="p-4 text-right text-muted-foreground font-mono">{t.columns}</td>
                <td className="p-4 text-right text-muted-foreground"><div className="flex items-center justify-end gap-1"><HardDrive className="size-3.5" />{t.size}</div></td>
                <td className="p-4 text-right text-muted-foreground text-xs"><div className="flex items-center justify-end gap-1"><Clock className="size-3.5" />{t.lastModified}</div></td>
                <td className="p-4 px-6 text-right"><Button variant="ghost" size="icon" className="h-8 w-8 opacity-0 group-hover:opacity-100"><Eye className="size-4" /></Button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default Tables