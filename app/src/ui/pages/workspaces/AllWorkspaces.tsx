import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Plus, FileText, MessageSquare, Files, Clock, Calendar, Briefcase, TrendingUp, Users, LucideIcon, FolderOpen, Brain, Sparkles, Globe, Database, Code, Network } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { getAllWorkspaces, listResearchRecords, listChatThreads, type WorkspaceOut } from '@/lib/apis'
import { resolveApiAssetUrl } from '@/lib/utils'

interface WorkspaceCard {
  id: string
  title: string
  description: string
  researchCount: number
  chatCount: number
  fileCount: number
  createdAt: string
  lastUpdated: string
  icon: LucideIcon | null
  iconUrl: string | null
  colorClass: string
  colorHex: string | null
}

const isWorkspaceAssetPath = (value?: string | null) => {
  return Boolean(value && (value.includes('/') || /^https?:\/\//i.test(value)))
}

const isHexColor = (value?: string | null): value is string => {
  return Boolean(value && /^#[0-9a-fA-F]{6}$/.test(value))
}

const ICON_MAP: Record<string, LucideIcon> = {
  briefcase: Briefcase,
  'trending up': TrendingUp,
  trendingup: TrendingUp,
  users: Users,
  brain: Brain,
  sparkles: Sparkles,
  globe: Globe,
  database: Database,
  code: Code,
  network: Network,
}

const resolveAccentClass = (accentColor?: string | null): string => {
  if (!accentColor) return 'text-primary'
  const accent = accentColor.toLowerCase()
  if (accent.includes('blue')) return 'text-blue-400'
  if (accent.includes('green')) return 'text-green-400'
  if (accent.includes('purple')) return 'text-purple-400'
  if (accent.includes('pink')) return 'text-pink-400'
  if (accent.includes('orange')) return 'text-orange-400'
  return 'text-primary'
}

const resolveIcon = (icon?: string | null): LucideIcon => {
  if (!icon) return FolderOpen
  return ICON_MAP[icon.toLowerCase()] ?? FolderOpen
}

const toWorkspaceCard = (
  workspace: WorkspaceOut,
  researchCount: number,
  chatCount: number,
): WorkspaceCard => {
  const iconUrl = isWorkspaceAssetPath(workspace.icon)
    ? resolveApiAssetUrl(workspace.icon)
    : null
  const colorHex = isHexColor(workspace.accentColor)
    ? workspace.accentColor
    : null

  return {
    id: workspace.id,
    title: workspace.name,
    description: workspace.description || 'No description available.',
    researchCount,
    chatCount,
    fileCount: 0,
    createdAt: workspace.createdAt || 'Unknown',
    lastUpdated: workspace.updatedAt || 'Unknown',
    icon: iconUrl ? null : resolveIcon(workspace.icon),
    iconUrl,
    colorClass: colorHex ? 'text-primary' : resolveAccentClass(workspace.accentColor),
    colorHex,
  }
}

const AllWorkspaces = () => {
  const navigate = useNavigate()
  const [workspaces, setWorkspaces] = useState<WorkspaceCard[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    let isCancelled = false

    const loadData = async () => {
      setIsLoading(true)
      setErrorMessage(null)

      try {
        const [workspaceList, researchResponse, chatThreadsResponse] = await Promise.all([
          getAllWorkspaces(),
          listResearchRecords({ page: 1, size: 200 }),
          listChatThreads({ page: 1, size: 200 }),
        ])

        if (isCancelled) return

        const researchCountByWorkspace = researchResponse.items.reduce<Record<string, number>>((acc, item) => {
          if (!item.workspace_id) return acc
          acc[item.workspace_id] = (acc[item.workspace_id] ?? 0) + 1
          return acc
        }, {})

        const chatCountByWorkspace = chatThreadsResponse.items.reduce<Record<string, number>>((acc, item) => {
          if (!item.workspace_id) return acc
          acc[item.workspace_id] = (acc[item.workspace_id] ?? 0) + 1
          return acc
        }, {})

        const cards = workspaceList.map((workspace) => {
          return toWorkspaceCard(
            workspace,
            researchCountByWorkspace[workspace.id] ?? 0,
            chatCountByWorkspace[workspace.id] ?? 0,
          )
        })

        setWorkspaces(cards)
      } catch (error) {
        if (isCancelled) return
        const message = error instanceof Error ? error.message : 'Failed to load workspaces'
        setErrorMessage(message)
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
  }, [])

  return (
    <div className="space-y-8 h-full text-foreground animate-in fade-in duration-500 overflow-y-auto">

      {/* Header section */}
      <div className="border-b bg-background/50 backdrop-blur-sm sticky top-0 z-30">
        <div className="w-full px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-5">
              <div className="size-12 rounded-2xl bg-linear-to-br from-primary/20 via-primary/10 to-transparent border border-primary/20 flex items-center justify-center animate-in fade-in zoom-in duration-500">
                <FolderOpen className="size-6 text-primary" />
              </div>
              <div className="flex flex-col gap-2">
                <h1 className="text-xl font-semibold tracking-tight">Your Workspaces</h1>
                <p className="text-muted-foreground">Manage and organize your research projects.</p>
              </div>
            </div>
          </div>
        </div>
      </div>



      <div className="p-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 pb-10">
        {/* Create Workspace Card */}
        <Card className="flex flex-col items-center justify-center min-h-75 border-dashed border-2 hover:border-primary/50 hover:bg-muted/50 transition-all cursor-pointer group bg-muted/10 p-0" onClick={() => { navigate("/workspaces/new") }}>
          <div className="rounded-full bg-background p-4 mb-4 group-hover:scale-110 transition-transform shadow-sm border">
            <Plus className="w-8 h-8 text-muted-foreground group-hover:text-primary transition-colors" />
          </div>
          <h3 className="font-semibold text-lg text-primary/80 transition-colors">Create Workspace</h3>
          <p className="text-sm text-muted-foreground/60 mt-1">Start a new project</p>
        </Card>

        {/* Existing Workspaces */}
        {workspaces.map((workspace) => (
          <Card key={workspace.id} className="min-h-75 flex flex-col shadow-lg hover:shadow-2xl transition-shadow cursor-pointer relative overflow-hidden group border-muted-foreground/20 p-0 py-0 gap-0" onClick={() => navigate(`/workspaces/view/${workspace.id}`)}>
            <CardHeader className="pt-6 pb-2 px-6">
              <div className="flex justify-between items-start gap-4">
                <div
                  className={`p-2 rounded-lg bg-secondary/30 ${workspace.colorClass}`}
                  style={workspace.colorHex ? { color: workspace.colorHex, backgroundColor: `${workspace.colorHex}1A` } : undefined}
                >
                  {workspace.iconUrl ? (
                    <img src={workspace.iconUrl} alt={`${workspace.title} icon`} className="w-5 h-5 object-cover rounded" />
                  ) : workspace.icon ? (
                    <workspace.icon className="w-5 h-5" />
                  ) : (
                    <FolderOpen className="w-5 h-5" />
                  )}
                </div>
                <div className="space-y-1 flex-1">
                  <CardTitle className="line-clamp-1 text-xl group-hover:text-primary transition-colors">{workspace.title}</CardTitle>
                  <CardDescription className="line-clamp-2 h-10 text-xs">
                    {workspace.description}
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="flex-1 px-6 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-1 p-2 rounded-md bg-secondary/20">
                  <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                    <FileText className="w-3 h-3" /> Researches
                  </span>
                  <span className="font-semibold text-lg">{workspace.researchCount}</span>
                </div>
                <div className="flex flex-col gap-1 p-2 rounded-md bg-secondary/20">
                  <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                    <MessageSquare className="w-3 h-3" /> Chats
                  </span>
                  <span className="font-semibold text-lg">{workspace.chatCount}</span>
                </div>
                <div className="col-span-2 flex items-center gap-2 px-1 mt-1 text-muted-foreground/80">
                  <Files className="w-4 h-4" />
                  <span className="text-xs">{workspace.fileCount} Files</span>
                </div>
              </div>
            </CardContent>

            <Separator className="opacity-30" />

            <CardFooter className="py-4 px-6 text-[10px] grid grid-cols-2 gap-2 bg-muted/5 items-center">
              <div className="flex flex-col gap-0.5">
                <span className="text-[9px] text-muted-foreground/60 uppercase font-bold tracking-widest">Created</span>
                <div className="flex items-center gap-1.5 text-foreground/70">
                  <Calendar className="w-3 h-3 text-muted-foreground/50" />
                  <span className="truncate">{workspace.createdAt}</span>
                </div>
              </div>
              <div className="flex flex-col gap-0.5 border-l border-muted-foreground/10 pl-3">
                <span className="text-[9px] text-muted-foreground/60 uppercase font-bold tracking-widest">Modified</span>
                <div className="flex items-center gap-1.5 text-foreground/70">
                  <Clock className="w-3 h-3 text-muted-foreground/50" />
                  <span className="truncate">{workspace.lastUpdated}</span>
                </div>
              </div>
            </CardFooter>
          </Card>
        ))}

        {!isLoading && workspaces.length === 0 && (
          <Card className="min-h-75 border-dashed border-2 col-span-full flex items-center justify-center bg-muted/5 p-0">
            <CardContent className="text-center">
              <h3 className="font-semibold text-lg">No workspaces found</h3>
              <p className="text-sm text-muted-foreground mt-1">Create your first workspace to get started.</p>
            </CardContent>
          </Card>
        )}

        {isLoading && (
          <Card className="min-h-75 border-dashed border-2 col-span-full flex items-center justify-center bg-muted/5 p-0">
            <CardContent className="text-center">
              <h3 className="font-semibold text-lg">Loading workspaces...</h3>
            </CardContent>
          </Card>
        )}

        {errorMessage && (
          <Card className="min-h-75 border-destructive/30 border col-span-full flex items-center justify-center bg-destructive/5 p-0">
            <CardContent className="text-center">
              <h3 className="font-semibold text-lg text-destructive">Failed to load workspaces</h3>
              <p className="text-sm text-muted-foreground mt-1">{errorMessage}</p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}

export default AllWorkspaces
