import { useEffect, useMemo, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  getDatabase,
  type DatabaseDetailRecord,
} from '@/lib/apis'
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
  Calendar,
  Loader2,
} from 'lucide-react'

const getColorClasses = (color: string) => {
  const colorMap: Record<string, { text: string; bg: string; border: string }> = {
    'blue-400': { text: 'text-blue-400', bg: 'bg-blue-400/10', border: 'border-blue-400/30' },
    'purple-400': { text: 'text-purple-400', bg: 'bg-purple-400/10', border: 'border-purple-400/30' },
    'green-400': { text: 'text-green-400', bg: 'bg-green-400/10', border: 'border-green-400/30' },
    'orange-400': { text: 'text-orange-400', bg: 'bg-orange-400/10', border: 'border-orange-400/30' },
    'violet-400': { text: 'text-violet-400', bg: 'bg-violet-400/10', border: 'border-violet-400/30' },
    'pink-400': { text: 'text-pink-400', bg: 'bg-pink-400/10', border: 'border-pink-400/30' },
    'cyan-400': { text: 'text-cyan-400', bg: 'bg-cyan-400/10', border: 'border-cyan-400/30' },
    'amber-400': { text: 'text-amber-400', bg: 'bg-amber-400/10', border: 'border-amber-400/30' },
  }
  return colorMap[color] || colorMap['blue-400']
}

const DataVisualizer = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const [dbMeta, setDbMeta] = useState<DatabaseDetailRecord | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) {
      setError('Database id is missing')
      setIsLoading(false)
      return
    }

    let isCancelled = false

    const loadDatabase = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const detail = await getDatabase(id)
        if (isCancelled) return
        setDbMeta(detail)
      } catch (err) {
        if (isCancelled) return
        setDbMeta(null)
        setError(err instanceof Error ? err.message : 'Failed to load database metadata')
      } finally {
        if (!isCancelled) {
          setIsLoading(false)
        }
      }
    }

    void loadDatabase()

    return () => {
      isCancelled = true
    }
  }, [id])

  const stats = useMemo(() => {
    if (!dbMeta) {
      return { totalRows: 0, totalColumns: 0, avgRowsPerTable: 0 }
    }

    const totalRows = dbMeta.tables.reduce((acc, t) => acc + t.rows, 0)
    const totalColumns = dbMeta.tables.reduce((acc, t) => acc + t.columns, 0)
    const avgRowsPerTable = dbMeta.tables.length > 0 ? Math.round(totalRows / dbMeta.tables.length) : 0

    return { totalRows, totalColumns, avgRowsPerTable }
  }, [dbMeta])

  const tableDistribution = useMemo(() => {
    if (!dbMeta) return []

    const total = dbMeta.tables.reduce((acc, t) => acc + t.rows, 0)
    return dbMeta.tables
      .map((t) => ({
        ...t,
        percentage: total > 0 ? ((t.rows / total) * 100).toFixed(1) : '0.0',
      }))
      .sort((a, b) => b.rows - a.rows)
  }, [dbMeta])

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="size-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error || !dbMeta) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <Card className="w-full max-w-2xl border-destructive/40 bg-destructive/10">
          <CardContent className="p-6 text-sm text-destructive">
            Failed to load database metadata: {error || 'Unknown error'}
          </CardContent>
        </Card>
      </div>
    )
  }

  const colors = getColorClasses(dbMeta.color)

  return (
    <div className="flex flex-col h-full w-full bg-muted/10 overflow-hidden animate-in fade-in duration-500">
      <div className="shrink-0 border-b bg-background/50 backdrop-blur-sm sticky top-0 z-30">
        <div className="w-full px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={cn('size-14 rounded-2xl flex items-center justify-center', colors.bg)}>
                <Database className={cn('size-7', colors.text)} />
              </div>
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-semibold tracking-tight">{dbMeta.name}</h1>
                  {dbMeta.type === 'vector' && (
                    <Badge variant="outline" className="text-xs gap-1 border-violet-400/50 text-violet-400">
                      <Sparkles className="size-3" />
                      Vector
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground mt-0.5">{dbMeta.description}</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={() => navigate(`/data/databases/${encodeURIComponent(dbMeta.id)}/tables`)}
                className="gap-2"
              >
                <Table2 className="size-4" />
                View Tables
              </Button>
              <Button variant="outline" className="gap-2" disabled>
                <Download className="size-4" />
                Export
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto w-full">
        <div className="p-8 space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <Card className="border-muted-foreground/20">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-primary/10">
                    <Table2 className="size-5 text-primary" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{dbMeta.tableCount}</p>
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

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-2 border-muted-foreground/20">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <BarChart3 className={cn('size-5', colors.text)} />
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
                          className={cn('h-full rounded-full transition-all duration-500', colors.bg.replace('/10', ''))}
                          style={{ width: `${table.percentage}%` }}
                        />
                      </div>
                    </div>
                  ))}
                  {tableDistribution.length > 8 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => navigate(`/data/databases/${encodeURIComponent(dbMeta.id)}/tables`)}
                      className="w-full gap-2 mt-2"
                    >
                      View all {tableDistribution.length} tables
                      <ChevronRight className="size-4" />
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card className="border-muted-foreground/20">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Info className={cn('size-5', colors.text)} />
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

          <Card className="border-muted-foreground/20">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Table2 className={cn('size-5', colors.text)} />
                  <CardTitle className="text-lg">Tables Overview</CardTitle>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate(`/data/databases/${encodeURIComponent(dbMeta.id)}/tables`)}
                  className="gap-2"
                >
                  View All
                  <ChevronRight className="size-4" />
                </Button>
              </div>
              <CardDescription>Quick access to database tables</CardDescription>
            </CardHeader>
            <CardContent>
              {dbMeta.tables.length === 0 ? (
                <p className="text-sm text-muted-foreground">No tables available for this database.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                  {dbMeta.tables.slice(0, 8).map((table) => (
                    <div
                      key={table.name}
                      className="flex items-center gap-3 p-3 rounded-lg bg-muted/20 border border-muted-foreground/10 hover:bg-muted/30 transition-colors cursor-pointer group"
                      onClick={() => navigate(`/data/databases/${encodeURIComponent(dbMeta.id)}/tables/${encodeURIComponent(table.name)}`)}
                    >
                      <div className="p-2 rounded-md bg-muted/50">
                        <Table2 className="size-4 text-muted-foreground" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm truncate group-hover:text-primary transition-colors">{table.name}</p>
                        <p className="text-xs text-muted-foreground">{table.rows.toLocaleString()} rows • {table.columns} cols</p>
                      </div>
                      <ChevronRight className="size-4 text-muted-foreground/30 group-hover:text-primary transition-colors" />
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default DataVisualizer
