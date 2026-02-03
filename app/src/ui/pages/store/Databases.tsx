import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
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
  BrainCircuit
} from 'lucide-react'

// Database types
interface DatabaseInfo {
  id: string
  name: string
  description: string
  icon: React.ElementType
  tableCount: number
  totalRows: number
  size: string
  lastModified: string
  status: 'active' | 'syncing' | 'idle'
  color: string
  type: 'standard' | 'vector'
}

// Standard databases
const standardDatabases: DatabaseInfo[] = [
  {
    id: 'basic',
    name: 'Basic',
    description: 'Core application data and user preferences',
    icon: Database,
    tableCount: 8,
    totalRows: 1247,
    size: '2.4 MB',
    lastModified: '2 mins ago',
    status: 'active',
    color: 'blue-400',
    type: 'standard'
  },
  {
    id: 'history',
    name: 'History',
    description: 'Activity logs, actions, and audit trails',
    icon: History,
    tableCount: 5,
    totalRows: 15234,
    size: '18.7 MB',
    lastModified: '30 secs ago',
    status: 'active',
    color: 'purple-400',
    type: 'standard'
  },
  {
    id: 'scrapes',
    name: 'Scrapes',
    description: 'Web scraping results and extracted data',
    icon: Globe,
    tableCount: 12,
    totalRows: 45678,
    size: '156.3 MB',
    lastModified: '5 mins ago',
    status: 'syncing',
    color: 'green-400',
    type: 'standard'
  },
  {
    id: 'research',
    name: 'Research',
    description: 'Research sessions, queries, and results',
    icon: FlaskConical,
    tableCount: 7,
    totalRows: 8934,
    size: '67.8 MB',
    lastModified: '1 hour ago',
    status: 'active',
    color: 'orange-400',
    type: 'standard'
  },
  {
    id: 'assets',
    name: 'Assets',
    description: 'Media metadata and file references',
    icon: Package,
    tableCount: 4,
    totalRows: 3456,
    size: '12.1 MB',
    lastModified: '3 hours ago',
    status: 'idle',
    color: 'pink-400',
    type: 'standard'
  },
  {
    id: 'export',
    name: 'Export',
    description: 'Export configurations and generated outputs',
    icon: FolderOutput,
    tableCount: 3,
    totalRows: 892,
    size: '4.5 MB',
    lastModified: '1 day ago',
    status: 'idle',
    color: 'cyan-400',
    type: 'standard'
  },
]

// Vector databases
const vectorDatabases: DatabaseInfo[] = [
  {
    id: 'web-contents-vector',
    name: 'Web Contents Vector',
    description: 'Embedded web content for semantic search',
    icon: Boxes,
    tableCount: 2,
    totalRows: 124567,
    size: '2.3 GB',
    lastModified: '10 mins ago',
    status: 'active',
    color: 'violet-400',
    type: 'vector'
  },
  {
    id: 'search-vector-store',
    name: 'Search Vector Store',
    description: 'Search queries and results embeddings',
    icon: Zap,
    tableCount: 3,
    totalRows: 89234,
    size: '1.8 GB',
    lastModified: '25 mins ago',
    status: 'active',
    color: 'amber-400',
    type: 'vector'
  },
]

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

const getStatusConfig = (status: DatabaseInfo['status']) => {
  switch (status) {
    case 'active':
      return { color: 'bg-green-500', label: 'Active', pulse: true }
    case 'syncing':
      return { color: 'bg-yellow-500', label: 'Syncing', pulse: true }
    case 'idle':
      return { color: 'bg-muted-foreground/50', label: 'Idle', pulse: false }
  }
}

const Databases = () => {
  const navigate = useNavigate()
  const [hoveredDb, setHoveredDb] = useState<string | null>(null)

  const totalStats = {
    databases: standardDatabases.length + vectorDatabases.length,
    tables: [...standardDatabases, ...vectorDatabases].reduce((acc, db) => acc + db.tableCount, 0),
    rows: [...standardDatabases, ...vectorDatabases].reduce((acc, db) => acc + db.totalRows, 0),
  }

  const DatabaseCard = ({ db }: { db: DatabaseInfo }) => {
    const colors = getColorClasses(db.color)
    const statusConfig = getStatusConfig(db.status)
    const Icon = db.icon
    const isHovered = hoveredDb === db.id

    return (
      <Card
        className={cn(
          "group cursor-pointer transition-all duration-300 border-muted-foreground/20 overflow-hidden hover:shadow-xl",
          isHovered && "border-primary/40 scale-[1.02]"
        )}
        onMouseEnter={() => setHoveredDb(db.id)}
        onMouseLeave={() => setHoveredDb(null)}
        onClick={() => navigate(`/data/databases/${db.id}/visualizer`)}
      >
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className={cn("p-3 rounded-xl transition-all duration-300", colors.bg, isHovered && "scale-110")}>
              <Icon className={cn("size-6", colors.text)} />
            </div>
            <div className="flex items-center gap-2">
              {db.type === 'vector' && (
                <Badge variant="outline" className="text-[10px] gap-1 border-violet-400/50 text-violet-400">
                  <Sparkles className="size-3" />
                  Vector
                </Badge>
              )}
              <div className="flex items-center gap-1.5">
                <div className={cn(
                  "size-2 rounded-full",
                  statusConfig.color,
                  statusConfig.pulse && "animate-pulse"
                )} />
                <span className="text-[10px] text-muted-foreground">{statusConfig.label}</span>
              </div>
            </div>
          </div>
          <div className="mt-3">
            <CardTitle className="text-lg group-hover:text-primary transition-colors">
              {db.name}
            </CardTitle>
            <CardDescription className="text-xs mt-1 line-clamp-2">
              {db.description}
            </CardDescription>
          </div>
        </CardHeader>

        <CardContent className="pt-0">
          {/* Stats Grid */}
          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="flex flex-col items-center p-2.5 rounded-lg bg-muted/30">
              <Table2 className="size-4 text-muted-foreground mb-1" />
              <span className="text-lg font-bold">{db.tableCount}</span>
              <span className="text-[10px] text-muted-foreground">Tables</span>
            </div>
            <div className="flex flex-col items-center p-2.5 rounded-lg bg-muted/30">
              <FileText className="size-4 text-muted-foreground mb-1" />
              <span className="text-lg font-bold">{(db.totalRows / 1000).toFixed(1)}k</span>
              <span className="text-[10px] text-muted-foreground">Rows</span>
            </div>
            <div className="flex flex-col items-center p-2.5 rounded-lg bg-muted/30">
              <HardDrive className="size-4 text-muted-foreground mb-1" />
              <span className="text-lg font-bold truncate">{db.size.replace(' ', '')}</span>
              <span className="text-[10px] text-muted-foreground">Size</span>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between pt-3 border-t border-muted-foreground/10">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Clock className="size-3.5" />
              {db.lastModified}
            </div>
            <ChevronRight className={cn(
              "size-5 text-muted-foreground/30 transition-all duration-300",
              isHovered && "text-primary translate-x-1"
            )} />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="flex flex-col h-full w-full bg-muted/10 overflow-hidden animate-in fade-in duration-500">
      {/* Header Section */}
      <div className="shrink-0 border-b bg-background/50 backdrop-blur-sm sticky top-0 z-30">
        <div className="w-full px-8 py-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <div className="size-14 rounded-2xl bg-linear-to-br from-primary/20 via-primary/10 to-transparent border border-primary/20 flex items-center justify-center animate-in fade-in zoom-in duration-500">
                <Database className="size-7 text-primary" />
              </div>
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">
                  Databases
                </h1>
                <p className="text-sm text-muted-foreground mt-0.5">
                  View and explore your application databases
                </p>
              </div>
            </div>
          </div>

          {/* Stats Summary */}
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
              <span className="text-sm font-medium">{(totalStats.rows / 1000).toFixed(1)}k</span>
              <span className="text-xs text-muted-foreground">Total Rows</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto w-full">
        <div className="p-8 space-y-8">
          {/* Standard Databases */}
          <div>
            <div className="flex items-center gap-3 mb-4">
              <Database className="size-5 text-primary" />
              <h2 className="text-lg font-semibold">Standard Databases</h2>
              <Badge variant="secondary" className="text-xs">
                {standardDatabases.length}
              </Badge>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {standardDatabases.map((db) => (
                <DatabaseCard key={db.id} db={db} />
              ))}
            </div>
          </div>

          {/* Vector Databases */}
          <div>
            <div className="flex items-center gap-3 mb-4">
              <BrainCircuit className="size-5 text-violet-400" />
              <h2 className="text-lg font-semibold">Vector Databases</h2>
              <Badge variant="outline" className="text-xs border-violet-400/50 text-violet-400">
                {vectorDatabases.length}
              </Badge>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {vectorDatabases.map((db) => (
                <DatabaseCard key={db.id} db={db} />
              ))}
            </div>
          </div>

          {/* Info Note */}
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