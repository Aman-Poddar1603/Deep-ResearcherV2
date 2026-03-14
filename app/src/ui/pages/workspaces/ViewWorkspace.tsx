import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  FileText,
  MessageSquare,
  Files,
  Calendar,
  Clock,
  TrendingUp,
  Sparkles,
  Cpu,
  Globe,
  Bot,
  Download,
  Trash2,
  Edit,
  Eye,
  ChevronRight,
  Link,
  FileCode,
  FileImage,
  FileVideo,
  FileAudio,
  FileSpreadsheet,
  Plus,
  Upload,
  Loader2,
  BarChart2,
  BookOpen,
  Briefcase,
  Database,
  Folder,
  Home,
  Layers,
  Search,
  Settings,
  Star,
  Tag,
  Users,
  Zap,
  type LucideIcon,
} from 'lucide-react'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { fetchLinkMetadata, type LinkMetadata, cn, resolveApiAssetUrl } from '@/lib/utils'
import {
  getWorkspaceRecord,
  listResearchRecords,
  listChatThreads,
  listBucketItems,
  uploadBucketFiles,
  deleteWorkspaceRecord,
  type WorkspaceRecord,
  type ResearchRecord,
  type ChatThreadRecord,
  type BucketItemRecord,
} from '@/lib/apis'

const isWorkspaceAssetPath = (value?: string | null) => {
  return Boolean(value && (value.includes('/') || /^https?:\/\//i.test(value)))
}

const ICON_MAP: Record<string, LucideIcon> = {
  TrendingUp,
  trendingup: TrendingUp,
  'trending up': TrendingUp,
  BarChart2,
  barchart2: BarChart2,
  BookOpen,
  bookopen: BookOpen,
  book: BookOpen,
  Bot,
  bot: Bot,
  Briefcase,
  briefcase: Briefcase,
  Database,
  database: Database,
  FileText,
  filetext: FileText,
  document: FileText,
  Folder,
  folder: Folder,
  Globe,
  globe: Globe,
  Home,
  home: Home,
  Layers,
  layers: Layers,
  MessageSquare,
  messagesquare: MessageSquare,
  chat: MessageSquare,
  Search,
  search: Search,
  Settings,
  settings: Settings,
  Sparkles,
  sparkles: Sparkles,
  Star,
  star: Star,
  Tag,
  tag: Tag,
  Users,
  users: Users,
  Zap,
  zap: Zap,
}

const resolveIcon = (iconName: string | null | undefined): LucideIcon => {
  const normalizedIconName = iconName?.toLowerCase() ?? ''
  if (normalizedIconName && ICON_MAP[normalizedIconName]) return ICON_MAP[normalizedIconName]
  return Briefcase
}

const normalizeAccentColor = (color?: string | null) => {
  if (!color) return '#C084FC'

  const trimmed = color.trim()
  const fullHex = trimmed.match(/^#([0-9a-fA-F]{6})([0-9a-fA-F]{2})?$/)
  if (fullHex) {
    return `#${fullHex[1].toUpperCase()}`
  }

  const shortHex = trimmed.match(/^#([0-9a-fA-F]{3,4})$/)
  if (shortHex) {
    const rgb = shortHex[1].slice(0, 3)
    const expanded = rgb.split('').map((c) => `${c}${c}`).join('').toUpperCase()
    return `#${expanded}`
  }

  const accent = color.toLowerCase()
  if (accent.includes('blue')) return '#60A5FA'
  if (accent.includes('green')) return '#4ADE80'
  if (accent.includes('purple')) return '#C084FC'
  if (accent.includes('pink')) return '#F472B6'
  if (accent.includes('yellow')) return '#FACC15'
  if (accent.includes('red')) return '#F87171'
  if (accent.includes('orange')) return '#FB923C'
  if (accent.includes('indigo')) return '#818CF8'
  if (accent.includes('cyan')) return '#22D3EE'
  if (accent.includes('teal')) return '#2DD4BF'
  if (accent.includes('emerald')) return '#34D399'
  if (accent.includes('violet')) return '#A78BFA'

  return '#C084FC'
}

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

const formatDate = (iso: string | null | undefined): string => {
  if (!iso) return '-'
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

const getFileIconComponent = (format: string, accentClass: string) => {
  const cls = cn('w-5 h-5', accentClass)
  const fmt = format.toLowerCase()
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(fmt)) return <FileImage className={cls} />
  if (['mp4', 'mov', 'avi', 'webm'].includes(fmt)) return <FileVideo className={cls} />
  if (['mp3', 'wav', 'ogg', 'm4a'].includes(fmt)) return <FileAudio className={cls} />
  if (['xlsx', 'xls', 'csv'].includes(fmt)) return <FileSpreadsheet className={cls} />
  if (['js', 'ts', 'py', 'html', 'css', 'json'].includes(fmt)) return <FileCode className={cls} />
  return <FileText className={cls} />
}

const AI_MODE_INFO = {
  auto: { icon: Sparkles, label: 'Auto', description: 'Intelligent model switching' },
  local: { icon: Cpu, label: 'Offline', description: 'Local models only' },
  offline: { icon: Cpu, label: 'Offline', description: 'Local models only' },
  online: { icon: Globe, label: 'Online', description: 'Cloud-based models' },
}

// Complete class name mappings (Tailwind needs complete class names for JIT)
const getAccentClasses = (color: string) => {
  const classMap: Record<string, {
    text: string
    border: string
    hoverText: string
    hoverBg: string
    selectionColor: string
    cardBg: string
  }> = {
    '#C084FC': {
      text: 'text-purple-400',
      border: 'border-purple-400',
      hoverText: 'hover:text-purple-400',
      hoverBg: 'hover:bg-purple-400/10',
      selectionColor: 'rgba(192, 132, 252, 0.3)',
      cardBg: 'bg-purple-400/10',
    },
    '#60A5FA': {
      text: 'text-blue-400',
      border: 'border-blue-400',
      hoverText: 'hover:text-blue-400',
      hoverBg: 'hover:bg-blue-400/10',
      selectionColor: 'rgba(96, 165, 250, 0.3)',
      cardBg: 'bg-blue-400/10',
    },
    '#4ADE80': {
      text: 'text-green-400',
      border: 'border-green-400',
      hoverText: 'hover:text-green-400',
      hoverBg: 'hover:bg-green-400/10',
      selectionColor: 'rgba(74, 222, 128, 0.3)',
      cardBg: 'bg-green-400/10',
    },
    '#F472B6': {
      text: 'text-pink-400',
      border: 'border-pink-400',
      hoverText: 'hover:text-pink-400',
      hoverBg: 'hover:bg-pink-400/10',
      selectionColor: 'rgba(244, 114, 182, 0.3)',
      cardBg: 'bg-pink-400/10',
    },
    '#FB923C': {
      text: 'text-orange-400',
      border: 'border-orange-400',
      hoverText: 'hover:text-orange-400',
      hoverBg: 'hover:bg-orange-400/10',
      selectionColor: 'rgba(251, 146, 60, 0.3)',
      cardBg: 'bg-orange-400/10',
    },
    '#FACC15': {
      text: 'text-yellow-400',
      border: 'border-yellow-400',
      hoverText: 'hover:text-yellow-400',
      hoverBg: 'hover:bg-yellow-400/10',
      selectionColor: 'rgba(250, 204, 21, 0.3)',
      cardBg: 'bg-yellow-400/10',
    },
    '#F87171': {
      text: 'text-red-400',
      border: 'border-red-400',
      hoverText: 'hover:text-red-400',
      hoverBg: 'hover:bg-red-400/10',
      selectionColor: 'rgba(248, 113, 113, 0.3)',
      cardBg: 'bg-red-400/10',
    },
    '#818CF8': {
      text: 'text-indigo-400',
      border: 'border-indigo-400',
      hoverText: 'hover:text-indigo-400',
      hoverBg: 'hover:bg-indigo-400/10',
      selectionColor: 'rgba(129, 140, 248, 0.3)',
      cardBg: 'bg-indigo-400/10',
    },
    '#22D3EE': {
      text: 'text-cyan-400',
      border: 'border-cyan-400',
      hoverText: 'hover:text-cyan-400',
      hoverBg: 'hover:bg-cyan-400/10',
      selectionColor: 'rgba(34, 211, 238, 0.3)',
      cardBg: 'bg-cyan-400/10',
    },
    '#2DD4BF': {
      text: 'text-teal-400',
      border: 'border-teal-400',
      hoverText: 'hover:text-teal-400',
      hoverBg: 'hover:bg-teal-400/10',
      selectionColor: 'rgba(45, 212, 191, 0.3)',
      cardBg: 'bg-teal-400/10',
    },
    '#34D399': {
      text: 'text-emerald-400',
      border: 'border-emerald-400',
      hoverText: 'hover:text-emerald-400',
      hoverBg: 'hover:bg-emerald-400/10',
      selectionColor: 'rgba(52, 211, 153, 0.3)',
      cardBg: 'bg-emerald-400/10',
    },
    '#A78BFA': {
      text: 'text-violet-400',
      border: 'border-violet-400',
      hoverText: 'hover:text-violet-400',
      hoverBg: 'hover:bg-violet-400/10',
      selectionColor: 'rgba(167, 139, 250, 0.3)',
      cardBg: 'bg-violet-400/10',
    },
  }
  const normalizedColor = normalizeAccentColor(color)
  return classMap[normalizedColor] || classMap['#C084FC']
}

const ViewWorkspace = () => {
  const { id } = useParams()
  const navigate = useNavigate()

  const [workspace, setWorkspace] = useState<WorkspaceRecord | null>(null)
  const [researches, setResearches] = useState<ResearchRecord[]>([])
  const [chatThreads, setChatThreads] = useState<ChatThreadRecord[]>([])
  const [files, setFiles] = useState<BucketItemRecord[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isUploading, setIsUploading] = useState(false)
  const [accentColor, setAccentColor] = useState('#C084FC')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!id) return
    setIsLoading(true)

    const loadAll = async () => {
      try {
        const [ws, resPage, chatPage] = await Promise.all([
          getWorkspaceRecord(id),
          listResearchRecords({ workspaceId: id, page: 1, size: 5, sortOrder: 'desc' }),
          listChatThreads({ workspaceId: id, page: 1, size: 5, sortOrder: 'desc' }),
        ])
        setWorkspace(ws)
        if (ws.accent_clr) setAccentColor(normalizeAccentColor(ws.accent_clr))
        setResearches(resPage.items)
        setChatThreads(chatPage.items)

        if (ws.connected_bucket_id) {
          const bucketItems = await listBucketItems({
            bucketId: ws.connected_bucket_id,
            page: 1,
            size: 20,
            sortBy: 'updated_at',
            sortOrder: 'desc',
          })
          setFiles(bucketItems.items)
        }
      } catch (err) {
        console.error('Failed to load workspace:', err)
      } finally {
        setIsLoading(false)
      }
    }

    loadAll()
  }, [id])

  const handleUploadFiles = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files ?? [])
    if (selected.length === 0 || !workspace?.connected_bucket_id) return
    setIsUploading(true)
    try {
      const createdBy =
        localStorage.getItem('dr_profile_email') ||
        localStorage.getItem('dr_profile_name') ||
        'local-user'
      const uploaded = await uploadBucketFiles(workspace.connected_bucket_id, selected, {
        created_by: createdBy,
        connectedWorkspaceIds: workspace.id,
      })
      setFiles((prev) => [...uploaded, ...prev])
    } catch (err) {
      console.error('Upload failed:', err)
      alert('Upload failed. Please try again.')
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleDeleteWorkspace = async () => {
    if (!id || !confirm('Delete this workspace? This cannot be undone.')) return
    try {
      await deleteWorkspaceRecord(id)
      navigate('/workspaces')
    } catch (err) {
      console.error('Delete failed:', err)
      alert('Failed to delete workspace.')
    }
  }

  const accent = getAccentClasses(accentColor)

  // Update selection color CSS variable (scoped to this workspace)
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.style.setProperty('--workspace-selection-color', accent.selectionColor)
    }
  }, [accent.selectionColor])

  const aiMode = (workspace?.ai_config ?? 'auto') as keyof typeof AI_MODE_INFO
  const aiModeInfo = AI_MODE_INFO[aiMode] ?? AI_MODE_INFO.auto
  const AiModeIcon = aiModeInfo.icon

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!workspace) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-muted-foreground">Workspace not found.</p>
      </div>
    )
  }

  const WorkspaceIcon = resolveIcon(workspace.icon)
  const bannerUrl = resolveApiAssetUrl(workspace.banner_img)
  const iconUrl = isWorkspaceAssetPath(workspace.icon)
    ? resolveApiAssetUrl(workspace.icon)
    : null

  return (
    <div
      ref={containerRef}
      className="h-full overflow-y-auto animate-in fade-in duration-500 workspace-theme-root"
    >
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={handleUploadFiles}
      />

      {/* Header with Banner */}
      <div className="relative">
        {/* Banner */}
        {bannerUrl ? (
          <div className="h-48 border-b border-muted-foreground/20 overflow-hidden bg-muted/20">
            <img src={bannerUrl} alt={`${workspace.name} banner`} className="w-full h-full object-cover" />
          </div>
        ) : (
          <div className="h-48 bg-linear-to-br from-primary/20 via-primary/10 to-background border-b border-muted-foreground/20" />
        )}

        {/* Workspace Info Overlay */}
        <div className="relative -mt-20 px-8 pb-8">
          <Card className={cn("border-muted-foreground/20 shadow-xl backdrop-blur-2xl", accent.cardBg)}>
            <CardContent className="p-6">
              <div className="flex flex-col md:flex-row gap-6 items-start">
                {/* Icon */}
                <div className={cn("p-6 rounded-2xl bg-secondary/30 border border-muted-foreground/10 shadow-lg", accent.text)}>
                  {iconUrl ? (
                    <img src={iconUrl} alt={`${workspace.name} icon`} className="w-12 h-12 object-cover rounded-lg" />
                  ) : (
                    <WorkspaceIcon className="w-12 h-12" />
                  )}
                </div>

                {/* Info */}
                <div className="flex-1 space-y-3">
                  <div>
                    <h1 className={cn("text-3xl font-bold tracking-tight", accent.text)}>{workspace.name}</h1>
                    <p className="text-muted-foreground text-lg mt-1">{workspace.desc || 'No description.'}</p>
                  </div>

                  {/* Meta Info */}
                  <div className="flex flex-wrap gap-6 text-sm text-muted-foreground">
                    <div className="flex items-center gap-2">
                      <Calendar className="w-4 h-4" />
                      Created {formatDate(workspace.created_at)}
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4" />
                      Updated {formatDate(workspace.updated_at)}
                    </div>
                    <div className="flex items-center gap-2">
                      <AiModeIcon className="w-4 h-4" />
                      {aiModeInfo.label} Mode
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2 shrink-0 flex-wrap">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate(`/workspaces/edit/${id}`)}
                    className="gap-2"
                  >
                    <Edit className="w-4 h-4" />
                    Edit
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-2 text-destructive hover:text-destructive"
                    onClick={handleDeleteWorkspace}
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Main Content */}
      <div className="px-8 pb-8 space-y-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <Card className="border-muted-foreground/20">
            <CardHeader className="pb-3">
              <CardDescription className="flex items-center gap-2 text-xs">
                <FileText className={cn("w-4 h-4", accent.text)} />
                <span className={cn(accent.text, "font-semibold")}>Researches</span>
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{researches.length}</div>
              <p className="text-xs text-muted-foreground mt-1">Recent projects</p>
            </CardContent>
          </Card>

          <Card className="border-muted-foreground/20">
            <CardHeader className="pb-3">
              <CardDescription className="flex items-center gap-2 text-xs">
                <MessageSquare className={cn("w-4 h-4", accent.text)} />
                <span className={cn("font-semibold", accent.text)}>Chats</span>
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{chatThreads.length}</div>
              <p className="text-xs text-muted-foreground mt-1">Conversations</p>
            </CardContent>
          </Card>

          <Card className="border-muted-foreground/20">
            <CardHeader className="pb-3">
              <CardDescription className="flex items-center gap-2 text-xs">
                <Files className={cn("w-4 h-4", accent.text)} />
                <span className={cn("font-semibold", accent.text)}>Files</span>
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{files.length}</div>
              <p className="text-xs text-muted-foreground mt-1">Resources</p>
            </CardContent>
          </Card>
        </div>

        {/* Two Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Researches */}
          <Card className="border-muted-foreground/20">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className={accent.text}>Recent Researches</CardTitle>
                  <CardDescription>Latest research activities</CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    className={cn("gap-1 text-xs font-semibold", accent.text)}
                    onClick={() => navigate('/researches/new')}
                  >
                    <Plus className="w-3 h-3" />
                    New Research
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className={cn("gap-1 text-xs", accent.text)}
                    onClick={() => navigate('/researches')}
                  >
                    View All
                    <ChevronRight className="w-3 h-3" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {researches.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">No researches yet.</p>
              ) : (
                researches.map((research) => (
                  <div
                    key={research.id}
                    className="p-3 rounded-lg bg-muted/20 border border-muted-foreground/10 hover:bg-muted/30 transition-colors cursor-pointer"
                    onClick={() => navigate(`/researches/${research.id}`)}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <h4 className="font-medium text-sm line-clamp-1">{research.title || 'Untitled Research'}</h4>
                      <span className="text-xs px-2 py-0.5 rounded-full shrink-0 bg-green-500/20 text-green-400">
                        Done
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2">{research.desc || research.prompt || 'â€”'}</p>
                    <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                      <Clock className="w-3 h-3" />
                      {formatDate(null)}
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          {/* Recent Chats */}
          <Card className="border-muted-foreground/20">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className={accent.text}>Recent Chats</CardTitle>
                  <CardDescription>Latest conversations</CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="secondary" size="sm" className={cn("gap-1 text-xs font-semibold", accent.text)}>
                    <Plus className="w-3 h-3" />
                    New Chat
                  </Button>
                  <Button variant="ghost" size="sm" className={cn("gap-1 text-xs", accent.text)}>
                    View All
                    <ChevronRight className="w-3 h-3" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {chatThreads.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">No chats yet.</p>
              ) : (
                chatThreads.map((chat) => (
                  <div
                    key={chat.thread_id}
                    className="p-3 rounded-lg bg-muted/20 border border-muted-foreground/10 hover:bg-muted/30 transition-colors cursor-pointer"
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <h4 className="font-medium text-sm line-clamp-1">{chat.thread_title || 'Untitled Chat'}</h4>
                      <span className="text-xs text-muted-foreground shrink-0">
                        {chat.token_count ? `${chat.token_count} tokens` : ''}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                      <Clock className="w-3 h-3" />
                      {formatDate(chat.updated_at)}
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        {/* Files/Resources */}
        <Card className="border-muted-foreground/20">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className={accent.text}>Resources</CardTitle>
                <CardDescription>Files in this workspace's storage bucket</CardDescription>
              </div>
              <div className="flex gap-2">
                {workspace.connected_bucket_id && (
                  <Button
                    variant="outline"
                    size="sm"
                    className={cn("gap-2", accent.text, accent.border, accent.hoverBg)}
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isUploading}
                  >
                    {isUploading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Upload className="w-4 h-4" />
                    )}
                    {isUploading ? 'Uploadingâ€¦' : 'Upload Files'}
                  </Button>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {!workspace.connected_bucket_id ? (
              <p className="text-sm text-muted-foreground text-center py-6">
                No storage bucket connected. Edit the workspace to attach one.
              </p>
            ) : files.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-6">No files yet. Upload some files to get started.</p>
            ) : (
              <div className="space-y-2">
                {files.map((file) => (
                  <div
                    key={file.id}
                    className="flex items-center justify-between p-3 rounded-lg bg-muted/20 border border-muted-foreground/10 hover:bg-muted/30 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-md bg-primary/10">
                        {getFileIconComponent(file.file_format, accent.text)}
                      </div>
                      <div>
                        <h4 className="font-medium text-sm">{file.file_name}</h4>
                        <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                          <span className="uppercase">{file.file_format}</span>
                          <span>â€¢</span>
                          <span>{formatBytes(file.file_size)}</span>
                          <span>â€¢</span>
                          <span>Uploaded {formatDate(file.created_at)}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        className={cn("h-8 w-8 p-0", accent.hoverText)}
                      >
                        <Eye className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className={cn("h-8 w-8 p-0", accent.hoverText)}
                      >
                        <Download className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default ViewWorkspace
