import { useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  Database,
  Table2,
  HardDrive,
  FileText,
  Clock,
  Download,
  BarChart3,
  TrendingUp,
  Layers,
  ChevronRight,
  Info,
  Sparkles,
  Calendar
} from 'lucide-react'

// Database metadata
interface TableMeta {
  name: string
  rows: number
  columns: number
  size: string
  lastModified: string
}

interface DatabaseMeta {
  id: string
  name: string
  description: string
  type: 'standard' | 'vector'
  color: string
  tables: TableMeta[]
  totalSize: string
  createdAt: string
  lastModified: string
  engine: string
  version: string
}

// Mock database metadata
const mockDatabaseMeta: Record<string, DatabaseMeta> = {
  'basic': {
    id: 'basic',
    name: 'Basic',
    description: 'Core application data and user preferences',
    type: 'standard',
    color: 'blue-400',
    tables: [
      { name: 'users', rows: 156, columns: 12, size: '245 KB', lastModified: '2 mins ago' },
      { name: 'settings', rows: 89, columns: 8, size: '67 KB', lastModified: '1 hour ago' },
      { name: 'preferences', rows: 234, columns: 15, size: '312 KB', lastModified: '30 mins ago' },
      { name: 'workspaces', rows: 45, columns: 10, size: '156 KB', lastModified: '3 hours ago' },
      { name: 'api_keys', rows: 23, columns: 6, size: '34 KB', lastModified: '1 day ago' },
      { name: 'sessions', rows: 567, columns: 9, size: '890 KB', lastModified: '5 mins ago' },
      { name: 'notifications', rows: 89, columns: 7, size: '123 KB', lastModified: '10 mins ago' },
      { name: 'cache', rows: 44, columns: 4, size: '567 KB', lastModified: '1 min ago' },
    ],
    totalSize: '2.4 MB',
    createdAt: 'Jan 15, 2024',
    lastModified: '2 mins ago',
    engine: 'SQLite',
    version: '3.45.1'
  },
  'history': {
    id: 'history',
    name: 'History',
    description: 'Activity logs, actions, and audit trails',
    type: 'standard',
    color: 'purple-400',
    tables: [
      { name: 'activity_logs', rows: 8934, columns: 14, size: '12.4 MB', lastModified: '30 secs ago' },
      { name: 'search_history', rows: 3456, columns: 8, size: '2.8 MB', lastModified: '2 mins ago' },
      { name: 'chat_history', rows: 2123, columns: 11, size: '1.9 MB', lastModified: '5 mins ago' },
      { name: 'file_access_logs', rows: 567, columns: 7, size: '890 KB', lastModified: '10 mins ago' },
      { name: 'error_logs', rows: 154, columns: 9, size: '678 KB', lastModified: '1 hour ago' },
    ],
    totalSize: '18.7 MB',
    createdAt: 'Dec 10, 2023',
    lastModified: '30 secs ago',
    engine: 'SQLite',
    version: '3.45.1'
  },
  'scrapes': {
    id: 'scrapes',
    name: 'Scrapes',
    description: 'Web scraping results and extracted data',
    type: 'standard',
    color: 'green-400',
    tables: [
      { name: 'web_pages', rows: 12345, columns: 18, size: '45.6 MB', lastModified: '5 mins ago' },
      { name: 'extracted_text', rows: 8934, columns: 6, size: '34.2 MB', lastModified: '6 mins ago' },
      { name: 'images', rows: 4567, columns: 10, size: '23.4 MB', lastModified: '8 mins ago' },
      { name: 'links', rows: 15678, columns: 5, size: '12.1 MB', lastModified: '5 mins ago' },
      { name: 'metadata', rows: 2134, columns: 22, size: '18.9 MB', lastModified: '10 mins ago' },
      { name: 'errors', rows: 234, columns: 8, size: '1.2 MB', lastModified: '1 hour ago' },
      { name: 'queue', rows: 89, columns: 7, size: '456 KB', lastModified: '2 mins ago' },
      { name: 'schedules', rows: 23, columns: 9, size: '89 KB', lastModified: '3 hours ago' },
      { name: 'proxies', rows: 45, columns: 6, size: '34 KB', lastModified: '1 day ago' },
      { name: 'cookies', rows: 567, columns: 4, size: '234 KB', lastModified: '30 mins ago' },
      { name: 'sessions', rows: 78, columns: 8, size: '123 KB', lastModified: '45 mins ago' },
      { name: 'configs', rows: 34, columns: 12, size: '67 KB', lastModified: '2 days ago' },
    ],
    totalSize: '156.3 MB',
    createdAt: 'Nov 5, 2023',
    lastModified: '5 mins ago',
    engine: 'SQLite',
    version: '3.45.1'
  },
  'research': {
    id: 'research',
    name: 'Research',
    description: 'Research sessions, queries, and results',
    type: 'standard',
    color: 'orange-400',
    tables: [
      { name: 'sessions', rows: 234, columns: 15, size: '12.3 MB', lastModified: '1 hour ago' },
      { name: 'queries', rows: 3456, columns: 9, size: '18.9 MB', lastModified: '2 hours ago' },
      { name: 'results', rows: 4567, columns: 12, size: '23.4 MB', lastModified: '1 hour ago' },
      { name: 'sources', rows: 567, columns: 8, size: '8.9 MB', lastModified: '3 hours ago' },
      { name: 'citations', rows: 89, columns: 11, size: '2.1 MB', lastModified: '5 hours ago' },
      { name: 'exports', rows: 12, columns: 7, size: '1.2 MB', lastModified: '1 day ago' },
      { name: 'templates', rows: 9, columns: 6, size: '980 KB', lastModified: '1 week ago' },
    ],
    totalSize: '67.8 MB',
    createdAt: 'Oct 20, 2023',
    lastModified: '1 hour ago',
    engine: 'SQLite',
    version: '3.45.1'
  },
  'web-contents-vector': {
    id: 'web-contents-vector',
    name: 'Web Contents Vector',
    description: 'Embedded web content for semantic search',
    type: 'vector',
    color: 'violet-400',
    tables: [
      { name: 'embeddings', rows: 98234, columns: 1536, size: '1.8 GB', lastModified: '10 mins ago' },
      { name: 'metadata', rows: 98234, columns: 12, size: '512 MB', lastModified: '10 mins ago' },
    ],
    totalSize: '2.3 GB',
    createdAt: 'Sep 15, 2023',
    lastModified: '10 mins ago',
    engine: 'ChromaDB',
    version: '0.4.22'
  },
}

const getColorClasses = (color: string) => {
  const colorMap: Record<string, { text: string; bg: string; border: string }> = {
    'blue-400': { text: 'text-blue-400', bg: 'bg-blue-400/10', border: 'border-blue-400/30' },
    'purple-400': { text: 'text-purple-400', bg: 'bg-purple-400/10', border: 'border-purple-400/30' },
    'green-400': { text: 'text-green-400', bg: 'bg-green-400/10', border: 'border-green-400/30' },
    'orange-400': { text: 'text-orange-400', bg: 'bg-orange-400/10', border: 'border-orange-400/30' },
    'violet-400': { text: 'text-violet-400', bg: 'bg-violet-400/10', border: 'border-violet-400/30' },
  }
  return colorMap[color] || colorMap['blue-400']
}

const DataVisualizer = () => {
  const { id } = useParams()
  const navigate = useNavigate()

  const dbMeta = useMemo(() => {
    return mockDatabaseMeta[id || 'basic'] || mockDatabaseMeta['basic']
  }, [id])

  const colors = getColorClasses(dbMeta.color)

  // Compute statistics
  const stats = useMemo(() => {
    const totalRows = dbMeta.tables.reduce((acc, t) => acc + t.rows, 0)
    const totalColumns = dbMeta.tables.reduce((acc, t) => acc + t.columns, 0)
    const avgRowsPerTable = Math.round(totalRows / dbMeta.tables.length)
    return { totalRows, totalColumns, avgRowsPerTable }
  }, [dbMeta])

  // Distribution data for visualization
  const tableDistribution = useMemo(() => {
    const total = dbMeta.tables.reduce((acc, t) => acc + t.rows, 0)
    return dbMeta.tables.map(t => ({
      ...t,
      percentage: ((t.rows / total) * 100).toFixed(1)
    })).sort((a, b) => b.rows - a.rows)
  }, [dbMeta])

  return (
    <div className="flex flex-col h-full w-full bg-muted/10 overflow-hidden animate-in fade-in duration-500">
      {/* Header Section */}
      <div className="shrink-0 border-b bg-background/50 backdrop-blur-sm sticky top-0 z-30">
        <div className="w-full px-8 py-6">

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={cn("size-14 rounded-2xl flex items-center justify-center", colors.bg)}>
                <Database className={cn("size-7", colors.text)} />
              </div>
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-semibold tracking-tight">
                    {dbMeta.name}
                  </h1>
                  {dbMeta.type === 'vector' && (
                    <Badge variant="outline" className="text-xs gap-1 border-violet-400/50 text-violet-400">
                      <Sparkles className="size-3" />
                      Vector
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground mt-0.5">
                  {dbMeta.description}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={() => navigate(`/data/databases/${id}/tables`)}
                className="gap-2"
              >
                <Table2 className="size-4" />
                View Tables
              </Button>
              <Button variant="outline" className="gap-2">
                <Download className="size-4" />
                Export
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto w-full">
        <div className="p-8 space-y-6">
          {/* Quick Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <Card className="border-muted-foreground/20">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-primary/10">
                    <Table2 className="size-5 text-primary" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{dbMeta.tables.length}</p>
                    <p className="text-xs text-muted-foreground">Tables</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-muted-foreground/20">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-green-400/10">
                    <FileText className="size-5 text-green-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{(stats.totalRows / 1000).toFixed(1)}k</p>
                    <p className="text-xs text-muted-foreground">Total Rows</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-muted-foreground/20">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-blue-400/10">
                    <Layers className="size-5 text-blue-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{stats.totalColumns}</p>
                    <p className="text-xs text-muted-foreground">Total Columns</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-muted-foreground/20">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-purple-400/10">
                    <HardDrive className="size-5 text-purple-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{dbMeta.totalSize}</p>
                    <p className="text-xs text-muted-foreground">Total Size</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-muted-foreground/20">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-orange-400/10">
                    <TrendingUp className="size-5 text-orange-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{stats.avgRowsPerTable}</p>
                    <p className="text-xs text-muted-foreground">Avg Rows/Table</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-muted-foreground/20">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-pink-400/10">
                    <Clock className="size-5 text-pink-400" />
                  </div>
                  <div>
                    <p className="text-lg font-bold truncate">{dbMeta.lastModified}</p>
                    <p className="text-xs text-muted-foreground">Last Modified</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Distribution & Metadata */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Table Distribution */}
            <Card className="lg:col-span-2 border-muted-foreground/20">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <BarChart3 className={cn("size-5", colors.text)} />
                  <CardTitle className="text-lg">Data Distribution</CardTitle>
                </div>
                <CardDescription>Row distribution across tables</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {tableDistribution.slice(0, 8).map((table) => (
                    <div key={table.name} className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium">{table.name}</span>
                        <span className="text-muted-foreground">
                          {table.rows.toLocaleString()} rows ({table.percentage}%)
                        </span>
                      </div>
                      <div className="h-2 bg-muted/30 rounded-full overflow-hidden">
                        <div
                          className={cn("h-full rounded-full transition-all duration-500", colors.bg.replace('/10', ''))}
                          style={{ width: `${table.percentage}%` }}
                        />
                      </div>
                    </div>
                  ))}
                  {tableDistribution.length > 8 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => navigate(`/data/databases/${id}/tables`)}
                      className="w-full gap-2 mt-2"
                    >
                      View all {tableDistribution.length} tables
                      <ChevronRight className="size-4" />
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Database Metadata */}
            <Card className="border-muted-foreground/20">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Info className={cn("size-5", colors.text)} />
                  <CardTitle className="text-lg">Database Info</CardTitle>
                </div>
                <CardDescription>System-level metadata</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between py-2 border-b border-muted-foreground/10">
                  <span className="text-sm text-muted-foreground">Engine</span>
                  <Badge variant="secondary">{dbMeta.engine}</Badge>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-muted-foreground/10">
                  <span className="text-sm text-muted-foreground">Version</span>
                  <span className="text-sm font-mono">{dbMeta.version}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-muted-foreground/10">
                  <span className="text-sm text-muted-foreground">Type</span>
                  <Badge variant="outline" className={dbMeta.type === 'vector' ? 'border-violet-400/50 text-violet-400' : ''}>
                    {dbMeta.type === 'vector' ? 'Vector DB' : 'Standard'}
                  </Badge>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-muted-foreground/10">
                  <span className="text-sm text-muted-foreground">Created</span>
                  <div className="flex items-center gap-1.5 text-sm">
                    <Calendar className="size-3.5 text-muted-foreground" />
                    {dbMeta.createdAt}
                  </div>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-sm text-muted-foreground">Modified</span>
                  <div className="flex items-center gap-1.5 text-sm">
                    <Clock className="size-3.5 text-muted-foreground" />
                    {dbMeta.lastModified}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Tables Preview */}
          <Card className="border-muted-foreground/20">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Table2 className={cn("size-5", colors.text)} />
                  <CardTitle className="text-lg">Tables Overview</CardTitle>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate(`/data/databases/${id}/tables`)}
                  className="gap-2"
                >
                  View All
                  <ChevronRight className="size-4" />
                </Button>
              </div>
              <CardDescription>Quick access to database tables</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {dbMeta.tables.slice(0, 8).map((table) => (
                  <div
                    key={table.name}
                    className="flex items-center gap-3 p-3 rounded-lg bg-muted/20 border border-muted-foreground/10 hover:bg-muted/30 transition-colors cursor-pointer group"
                    onClick={() => navigate(`/data/databases/${id}/tables/${table.name}`)}
                  >
                    <div className="p-2 rounded-md bg-muted/50">
                      <Table2 className="size-4 text-muted-foreground" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm truncate group-hover:text-primary transition-colors">
                        {table.name}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {table.rows.toLocaleString()} rows • {table.columns} cols
                      </p>
                    </div>
                    <ChevronRight className="size-4 text-muted-foreground/30 group-hover:text-primary transition-colors" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default DataVisualizer