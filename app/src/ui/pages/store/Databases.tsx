import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  listDatabases,
  type DatabaseRecord,
} from '@/lib/apis'
import {
  Database,
  Table2,
  HardDrive,
  Clock,
  ChevronRight,
  Eye,
  Sparkles,
  FileText,
  History,
  Globe,
  FlaskConical,
  Package,
  FolderOutput,
  Boxes,
  Zap,
  BrainCircuit,
  MessageSquare,
  Loader2,
} from 'lucide-react'

const getDatabaseIcon = (db: DatabaseRecord) => {
  if (db.type === 'vector') {
    if (db.id.includes('search')) return Zap
    if (db.id.includes('web')) return Boxes
    return BrainCircuit
  }

  const map: Record<string, React.ElementType> = {
    main: Database,
    history: History,
    scrapes: Globe,
    researches: FlaskConical,
    buckets: Package,
    chats: MessageSquare,
    logs: FileText,
    assets: FolderOutput,
  }

  return map[db.id] || Database
}

const getColorClasses = (color: string) => {
  const colorMap: Record<string, { text: string; bg: string; border: string }> = {
    'blue-400': { text: 'text-blue-400', bg: 'bg-blue-400/10', border: 'border-blue-400/30' },
    'purple-400': { text: 'text-purple-400', bg: 'bg-purple-400/10', border: 'border-purple-400/30' },
    'green-400': { text: 'text-green-400', bg: 'bg-green-400/10', border: 'border-green-400/30' },
    'orange-400': { text: 'text-orange-400', bg: 'bg-orange-400/10', border: 'border-orange-400/30' },
    'pink-400': { text: 'text-pink-400', bg: 'bg-pink-400/10', border: 'border-pink-400/30' },
    'cyan-400': { text: 'text-cyan-400', bg: 'bg-cyan-400/10', border: 'border-cyan-400/30' },
    'violet-400': { text: 'text-violet-400', bg: 'bg-violet-400/10', border: 'border-violet-400/30' },
    'amber-400': { text: 'text-amber-400', bg: 'bg-amber-400/10', border: 'border-amber-400/30' },
  }
  return colorMap[color] || colorMap['blue-400']
}

const getStatusConfig = (status: DatabaseRecord['status']) => {
  switch (status) {
    case 'active':
      return { color: 'bg-green-500', label: 'Active', pulse: true }
    case 'syncing':
      return { color: 'bg-yellow-500', label: 'Syncing', pulse: true }
    case 'idle':
      return { color: 'bg-muted-foreground/50', label: 'Idle', pulse: false }
  }
}

const formatRowsCompact = (rows: number) => {
  if (rows >= 1000) {
    return `${(rows / 1000).toFixed(1)}k`
  }
  return `${rows}`
}

const Databases = () => {
  const navigate = useNavigate()
  const [hoveredDb, setHoveredDb] = useState<string | null>(null)
  const [databases, setDatabases] = useState<DatabaseRecord[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadDatabases = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await listDatabases({ page: 1, size: 200 })
      setDatabases(response.items)
    } catch (err) {
      setDatabases([])
      setError(err instanceof Error ? err.message : 'Failed to load databases')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void loadDatabases()
  }, [])

  const standardDatabases = useMemo(
    () => databases.filter((db) => db.type === 'standard'),
    [databases],
  )
  const vectorDatabases = useMemo(
    () => databases.filter((db) => db.type === 'vector'),
    [databases],
  )

  const totalStats = useMemo(
    () => ({
      databases: databases.length,
      tables: databases.reduce((acc, db) => acc + db.tableCount, 0),
      rows: databases.reduce((acc, db) => acc + db.totalRows, 0),
    }),
    [databases],
  )

  const DatabaseCard = ({ db }: { db: DatabaseRecord }) => {
    const colors = getColorClasses(db.color)
    const statusConfig = getStatusConfig(db.status)
    const Icon = getDatabaseIcon(db)
    const isHovered = hoveredDb === db.id

    return (
      <Card
        className={cn(
          'group cursor-pointer transition-all duration-300 border-muted-foreground/20 overflow-hidden hover:shadow-xl',
          isHovered && 'border-primary/40 scale-[1.02]',
        )}
        onMouseEnter={() => setHoveredDb(db.id)}
        onMouseLeave={() => setHoveredDb(null)}
        onClick={() => navigate(`/data/databases/${encodeURIComponent(db.id)}/visualizer`)}
      >
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className={cn('p-3 rounded-xl transition-all duration-300', colors.bg, isHovered && 'scale-110')}>
              <Icon className={cn('size-6', colors.text)} />
            </div>
            <div className="flex items-center gap-2">
              {db.type === 'vector' && (
                <Badge variant="outline" className="text-[10px] gap-1 border-violet-400/50 text-violet-400">
                  <Sparkles className="size-3" />
                  Vector
                </Badge>
              )}
              <div className="flex items-center gap-1.5">
                <div
                  className={cn(
                    'size-2 rounded-full',
                    statusConfig.color,
                    statusConfig.pulse && 'animate-pulse',
                  )}
                />
                <span className="text-[10px] text-muted-foreground">{statusConfig.label}</span>
              </div>
            </div>
          </div>
          <div className="mt-3">
            <CardTitle className="text-lg group-hover:text-primary transition-colors">{db.name}</CardTitle>
            <CardDescription className="text-xs mt-1 line-clamp-2">{db.description}</CardDescription>
          </div>
        </CardHeader>

        <CardContent className="pt-0">
          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="flex flex-col items-center p-2.5 rounded-lg bg-muted/30">
              <Table2 className="size-4 text-muted-foreground mb-1" />
              <span className="text-lg font-bold">{db.tableCount}</span>
              <span className="text-[10px] text-muted-foreground">Tables</span>
            </div>
            <div className="flex flex-col items-center p-2.5 rounded-lg bg-muted/30">
              <FileText className="size-4 text-muted-foreground mb-1" />
              <span className="text-lg font-bold">{formatRowsCompact(db.totalRows)}</span>
              <span className="text-[10px] text-muted-foreground">Rows</span>
            </div>
            <div className="flex flex-col items-center p-2.5 rounded-lg bg-muted/30">
              <HardDrive className="size-4 text-muted-foreground mb-1" />
              <span className="text-lg font-bold truncate">{db.size.replace(' ', '')}</span>
              <span className="text-[10px] text-muted-foreground">Size</span>
            </div>
          </div>

          <div className="flex items-center justify-between pt-3 border-t border-muted-foreground/10">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Clock className="size-3.5" />
              {db.lastModified}
            </div>
            <ChevronRight
              className={cn(
                'size-5 text-muted-foreground/30 transition-all duration-300',
                isHovered && 'text-primary translate-x-1',
              )}
            />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="flex flex-col h-full w-full bg-muted/10 overflow-hidden animate-in fade-in duration-500">
      <div className="shrink-0 border-b bg-background/50 backdrop-blur-sm sticky top-0 z-30">
        <div className="w-full px-8 py-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <div className="size-14 rounded-2xl bg-linear-to-br from-primary/20 via-primary/10 to-transparent border border-primary/20 flex items-center justify-center animate-in fade-in zoom-in duration-500">
                <Database className="size-7 text-primary" />
              </div>
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">Databases</h1>
                <p className="text-sm text-muted-foreground mt-0.5">View and explore your application databases</p>
              </div>
            </div>
            <Button variant="outline" onClick={() => void loadDatabases()} className="gap-2" disabled={isLoading}>
              {isLoading ? <Loader2 className="size-4 animate-spin" /> : <Eye className="size-4" />}
              Refresh
            </Button>
          </div>

          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-muted/30 border border-muted-foreground/10">
              <Database className="size-4 text-primary" />
              <span className="text-sm font-medium">{totalStats.databases}</span>
              <span className="text-xs text-muted-foreground">Databases</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-muted/30 border border-muted-foreground/10">
              <Table2 className="size-4 text-primary" />
              <span className="text-sm font-medium">{totalStats.tables}</span>
              <span className="text-xs text-muted-foreground">Tables</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-muted/30 border border-muted-foreground/10">
              <FileText className="size-4 text-primary" />
              <span className="text-sm font-medium">{formatRowsCompact(totalStats.rows)}</span>
              <span className="text-xs text-muted-foreground">Total Rows</span>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto w-full">
        <div className="p-8 space-y-8">
          {error && (
            <Card className="border-destructive/40 bg-destructive/10">
              <CardContent className="p-4 text-sm text-destructive">Failed to load databases: {error}</CardContent>
            </Card>
          )}

          {isLoading ? (
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Loading databases...
            </div>
          ) : (
            <>
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <Database className="size-5 text-primary" />
                  <h2 className="text-lg font-semibold">Standard Databases</h2>
                  <Badge variant="secondary" className="text-xs">
                    {standardDatabases.length}
                  </Badge>
                </div>
                {standardDatabases.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No standard databases found.</p>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {standardDatabases.map((db) => (
                      <DatabaseCard key={db.id} db={db} />
                    ))}
                  </div>
                )}
              </div>

              <div>
                <div className="flex items-center gap-3 mb-4">
                  <BrainCircuit className="size-5 text-violet-400" />
                  <h2 className="text-lg font-semibold">Vector Databases</h2>
                  <Badge variant="outline" className="text-xs border-violet-400/50 text-violet-400">
                    {vectorDatabases.length}
                  </Badge>
                </div>
                {vectorDatabases.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No vector databases found.</p>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {vectorDatabases.map((db) => (
                      <DatabaseCard key={db.id} db={db} />
                    ))}
                  </div>
                )}
              </div>
            </>
          )}

          <Card className="border-muted-foreground/20 bg-muted/10">
            <CardContent className="p-4 flex items-start gap-3">
              <div className="p-2 rounded-lg bg-primary/10">
                <Eye className="size-4 text-primary" />
              </div>
              <div>
                <h4 className="text-sm font-medium">Read-Only Access</h4>
                <p className="text-xs text-muted-foreground mt-1">
                  These databases are managed by the application. You can view and export data, but modifications are controlled by the system.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default Databases
