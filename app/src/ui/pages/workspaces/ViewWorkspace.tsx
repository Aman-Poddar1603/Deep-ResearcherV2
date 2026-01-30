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
  Palette,
  Plus,
} from 'lucide-react'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { fetchLinkMetadata, type LinkMetadata, cn } from '@/lib/utils'

// Mock workspace data
const mockWorkspace = {
  id: '1',
  name: 'Market Analysis 2024',
  description: 'Deep dive into emerging tech markets and competitor landscape analysis.',
  icon: TrendingUp,
  accentColor: 'purple-400', // Accent color for theming
  bannerImage: null,
  aiMode: 'auto',
  enableResearch: true,
  enableChat: true,
  researchCount: 5,
  chatCount: 12,
  fileCount: 8,
  createdAt: 'Jan 15, 2024',
  lastUpdated: '2 mins ago',
  stats: {
    totalQueries: 127,
    totalTokens: 45234,
    avgResponseTime: '1.2s',
  },
}

// Mock recent researches
const mockRecentResearches = [
  {
    id: '1',
    title: 'AI Market Trends Q1 2024',
    status: 'completed',
    date: '2 days ago',
    summary: 'Comprehensive analysis of AI market trends in the first quarter.',
  },
  {
    id: '2',
    title: 'Competitor Product Analysis',
    status: 'in-progress',
    date: '5 hours ago',
    summary: 'Detailed breakdown of competitor product features and pricing.',
  },
  {
    id: '3',
    title: 'Customer Sentiment Study',
    status: 'completed',
    date: '1 week ago',
    summary: 'Analysis of customer feedback from social media and reviews.',
  },
]

// Mock recent chats
const mockRecentChats = [
  {
    id: '1',
    title: 'Market sizing discussion',
    lastMessage: 'Can you help me understand the TAM calculations?',
    date: '1 hour ago',
    messageCount: 23,
  },
  {
    id: '2',
    title: 'Competitor pricing strategy',
    lastMessage: 'What are the pricing tiers for the main competitors?',
    date: '3 hours ago',
    messageCount: 15,
  },
  {
    id: '3',
    title: 'Feature comparison analysis',
    lastMessage: 'Let\'s compare the key features across top 5 players.',
    date: 'Yesterday',
    messageCount: 42,
  },
]

// Mock files/resources
const mockFiles = [
  {
    id: '1',
    name: 'Market_Research_Report_Q1.pdf',
    type: 'PDF',
    size: '2.4 MB',
    uploadedAt: 'Jan 20, 2024',
  },
  {
    id: '2',
    name: 'Competitor_Analysis.xlsx',
    type: 'Excel',
    size: '1.1 MB',
    uploadedAt: 'Jan 18, 2024',
  },
  {
    id: '3',
    name: 'Customer_Feedback_Summary.docx',
    type: 'Word',
    size: '856 KB',
    uploadedAt: 'Jan 15, 2024',
  },
  {
    id: '4',
    name: 'Industry_Trends_2024.pdf',
    type: 'PDF',
    size: '3.2 MB',
    uploadedAt: 'Jan 15, 2024',
  },
]

// Mock references (links)
const mockReferences = [
  {
    id: '1',
    url: 'https://ui.shadcn.com',
    addedAt: 'Jan 22, 2024',
  },
  {
    id: '2',
    url: 'https://nextjs.org',
    addedAt: 'Jan 20, 2024',
  },
  {
    id: '3',
    url: 'https://vercel.com',
    addedAt: 'Jan 18, 2024',
  },
  {
    id: '4',
    url: 'https://gemini.google.com',
    addedAt: 'Jan 16, 2024',
  },
  {
    id: '5',
    url: 'https://www.youtube.com/watch?time_continue=108&v=mFkw3p5qSuA&embeds_referring_euri=https%3A%2F%2Fwww.google.com%2F&source_ve_path=MTM5MTE3LDI4NjYzLDEzOTExNywyODY2MywxMzc3MjEsMjg2NjY',
    addedAt: 'Jan 15, 2024',
  },
]

// Mock generated blobs (AI-generated/exported files)
const mockGeneratedBlobs = [
  {
    id: '1',
    name: 'Research_Summary_2024.pdf',
    type: 'Document',
    fileType: 'PDF',
    size: '2.4 MB',
    generatedAt: '2 hours ago',
    generatedBy: 'AI (GPT-4)',
    preview: 'https://via.placeholder.com/400x300/3b82f6/ffffff?text=PDF+Document',
  },
  {
    id: '2',
    name: 'Market_Analysis_Chart.png',
    type: 'Image',
    fileType: 'PNG',
    size: '1.2 MB',
    generatedAt: '1 day ago',
    generatedBy: 'AI (DALL-E)',
    preview: 'https://via.placeholder.com/400x300/8b5cf6/ffffff?text=Market+Chart',
  },
  {
    id: '3',
    name: 'Interview_Recording.mp3',
    type: 'Audio',
    fileType: 'MP3',
    size: '8.7 MB',
    generatedAt: '3 days ago',
    generatedBy: 'User Export',
    preview: '', // No preview for audio
  },
  {
    id: '4',
    name: 'Product_Demo.mp4',
    type: 'Video',
    fileType: 'MP4',
    size: '45.3 MB',
    generatedAt: '5 days ago',
    generatedBy: 'AI (Runway)',
    preview: 'https://via.placeholder.com/400x300/10b981/ffffff?text=Video+Preview',
  },
  {
    id: '5',
    name: 'Data_Export.xlsx',
    type: 'Spreadsheet',
    fileType: 'XLSX',
    size: '512 KB',
    generatedAt: '1 week ago',
    generatedBy: 'User Export',
    preview: 'https://via.placeholder.com/400x300/f59e0b/ffffff?text=Excel+File',
  },
]

const AI_MODE_INFO = {
  auto: { icon: Sparkles, label: 'Auto', description: 'Intelligent model switching' },
  offline: { icon: Cpu, label: 'Offline', description: 'Local models only' },
  online: { icon: Globe, label: 'Online', description: 'Cloud-based models' },
}

// TEMPORARY: Accent color options for testing
const ACCENT_COLORS = ['purple-400', 'blue-400', 'green-400', 'pink-400', 'orange-400'] as const

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
    'purple-400': {
      text: 'text-purple-400',
      border: 'border-purple-400',
      hoverText: 'hover:text-purple-400',
      hoverBg: 'hover:bg-purple-400/10',
      selectionColor: 'rgba(192, 132, 252, 0.3)',
      cardBg: 'bg-purple-400/10',
    },
    'blue-400': {
      text: 'text-blue-400',
      border: 'border-blue-400',
      hoverText: 'hover:text-blue-400',
      hoverBg: 'hover:bg-blue-400/10',
      selectionColor: 'rgba(96, 165, 250, 0.3)',
      cardBg: 'bg-blue-400/10',
    },
    'green-400': {
      text: 'text-green-400',
      border: 'border-green-400',
      hoverText: 'hover:text-green-400',
      hoverBg: 'hover:bg-green-400/10',
      selectionColor: 'rgba(74, 222, 128, 0.3)',
      cardBg: 'bg-green-400/10',
    },
    'pink-400': {
      text: 'text-pink-400',
      border: 'border-pink-400',
      hoverText: 'hover:text-pink-400',
      hoverBg: 'hover:bg-pink-400/10',
      selectionColor: 'rgba(244, 114, 182, 0.3)',
      cardBg: 'bg-pink-400/10',
    },
    'orange-400': {
      text: 'text-orange-400',
      border: 'border-orange-400',
      hoverText: 'hover:text-orange-400',
      hoverBg: 'hover:bg-orange-400/10',
      selectionColor: 'rgba(251, 146, 60, 0.3)',
      cardBg: 'bg-orange-400/10',
    },
  }
  return classMap[color] || classMap['purple-400']
}

const ViewWorkspace = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const [accentColor, setAccentColor] = useState(mockWorkspace.accentColor)
  const WorkspaceIcon = mockWorkspace.icon
  const aiModeInfo = AI_MODE_INFO[mockWorkspace.aiMode as keyof typeof AI_MODE_INFO]
  const AiModeIcon = aiModeInfo.icon

  // TEMPORARY: Toggle accent color
  const toggleAccentColor = () => {
    const currentIndex = ACCENT_COLORS.indexOf(accentColor as typeof ACCENT_COLORS[number])
    const nextIndex = (currentIndex + 1) % ACCENT_COLORS.length
    setAccentColor(ACCENT_COLORS[nextIndex])
  }

  // Get accent color classes
  const accent = getAccentClasses(accentColor)

  const containerRef = useRef<HTMLDivElement>(null)

  // Update selection color CSS variable (scoped to this workspace)
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.style.setProperty('--workspace-selection-color', accent.selectionColor)
    }
  }, [accent.selectionColor])

  return (
    <div
      ref={containerRef}
      className="h-full overflow-y-auto animate-in fade-in duration-500 workspace-theme-root"
    >
      {/* Header with Banner */}
      <div className="relative">
        {/* Banner */}
        <div className="h-48 bg-linear-to-br from-primary/20 via-primary/10 to-background border-b border-muted-foreground/20" />

        {/* Workspace Info Overlay */}
        <div className="relative -mt-20 px-8 pb-8">
          <Card className={cn("border-muted-foreground/20 shadow-xl backdrop-blur-2xl", accent.cardBg)}>
            <CardContent className="p-6">
              <div className="flex flex-col md:flex-row gap-6 items-start">
                {/* Icon */}
                <div className={cn("p-6 rounded-2xl bg-secondary/30 border border-muted-foreground/10 shadow-lg", accent.text)}>
                  <WorkspaceIcon className="w-12 h-12" />
                </div>

                {/* Info */}
                <div className="flex-1 space-y-3">
                  <div>
                    <h1 className={cn("text-3xl font-bold tracking-tight", accent.text)}>{mockWorkspace.name}</h1>
                    <p className="text-muted-foreground text-lg mt-1">{mockWorkspace.description}</p>
                  </div>

                  {/* Meta Info */}
                  <div className="flex flex-wrap gap-6 text-sm text-muted-foreground">
                    <div className="flex items-center gap-2">
                      <Calendar className="w-4 h-4" />
                      Created {mockWorkspace.createdAt}
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4" />
                      Updated {mockWorkspace.lastUpdated}
                    </div>
                    <div className="flex items-center gap-2">
                      <AiModeIcon className="w-4 h-4" />
                      {aiModeInfo.label} Mode
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2 shrink-0">
                  {/* TEMPORARY: Color toggle button - REMOVE LATER */}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={toggleAccentColor}
                    className={cn("gap-2", accent.text, accent.border, accent.hoverBg)}
                    title="Toggle accent color (temporary)"
                  >
                    <Palette className="w-4 h-4" />
                    Color
                  </Button>
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="border-muted-foreground/20">
            <CardHeader className="pb-3">
              <CardDescription className="flex items-center gap-2 text-xs">
                <FileText className={cn("w-4 h-4", accent.text)} />
                <span className={cn(accent.text, "font-semibold")}>Researches</span>
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{mockWorkspace.researchCount}</div>
              <p className="text-xs text-muted-foreground mt-1">Active projects</p>
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
              <div className="text-3xl font-bold">{mockWorkspace.chatCount}</div>
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
              <div className="text-3xl font-bold">{mockWorkspace.fileCount}</div>
              <p className="text-xs text-muted-foreground mt-1">Resources</p>
            </CardContent>
          </Card>

          <Card className="border-muted-foreground/20">
            <CardHeader className="pb-3">
              <CardDescription className="flex items-center gap-2 text-xs">
                <Bot className={cn("w-4 h-4", accent.text)} />
                <span className={cn("font-semibold", accent.text)}>AI Queries</span>
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{mockWorkspace.stats.totalQueries}</div>
              <p className="text-xs text-muted-foreground mt-1">Total queries</p>
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
                  <Button variant="secondary" size="sm" className={cn("gap-1 text-xs font-semibold", accent.text)}>
                    <Plus className="w-3 h-3" />
                    New Research
                  </Button>
                  <Button variant="ghost" size="sm" className={cn("gap-1 text-xs", accent.text)}>
                    View All
                    <ChevronRight className="w-3 h-3" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {mockRecentResearches.map((research) => (
                <div
                  key={research.id}
                  className="p-3 rounded-lg bg-muted/20 border border-muted-foreground/10 hover:bg-muted/30 transition-colors cursor-pointer"
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <h4 className="font-medium text-sm">{research.title}</h4>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${research.status === 'completed'
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-yellow-500/20 text-yellow-400'
                        }`}
                    >
                      {research.status === 'completed' ? 'Done' : 'In Progress'}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground line-clamp-2">{research.summary}</p>
                  <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                    <Clock className="w-3 h-3" />
                    {research.date}
                  </div>
                </div>
              ))}
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
              {mockRecentChats.map((chat) => (
                <div
                  key={chat.id}
                  className="p-3 rounded-lg bg-muted/20 border border-muted-foreground/10 hover:bg-muted/30 transition-colors cursor-pointer"
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <h4 className="font-medium text-sm">{chat.title}</h4>
                    <span className="text-xs text-muted-foreground shrink-0">
                      {chat.messageCount} msgs
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground line-clamp-1 italic">
                    "{chat.lastMessage}"
                  </p>
                  <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                    <Clock className="w-3 h-3" />
                    {chat.date}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Files/Resources */}
        <Card className="border-muted-foreground/20">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className={accent.text}>Resources</CardTitle>
                <CardDescription>Files and documents in this workspace</CardDescription>
              </div>
              <Button variant="outline" size="sm" className={cn("gap-2", accent.text, accent.border, accent.hoverBg)}>
                <Download className="w-4 h-4" />
                Download All
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {mockFiles.map((file) => (
                <div
                  key={file.id}
                  className="flex items-center justify-between p-3 rounded-lg bg-muted/20 border border-muted-foreground/10 hover:bg-muted/30 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-md bg-primary/10">
                      <FileText className={cn("w-5 h-5", accent.text)} />
                    </div>
                    <div>
                      <h4 className="font-medium text-sm">{file.name}</h4>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                        <span>{file.type}</span>
                        <span>•</span>
                        <span>{file.size}</span>
                        <span>•</span>
                        <span>Uploaded {file.uploadedAt}</span>
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
          </CardContent>
        </Card>

        {/* Two Column Layout - References and Generated Blobs */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* References (Links) */}
          <Card className="border-muted-foreground/20">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className={accent.text}>References</CardTitle>
                  <CardDescription>External links and resources</CardDescription>
                </div>
                <Button variant="ghost" size="sm" className={cn("gap-2", accent.text, accent.border, accent.hoverBg)}>
                  View All
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              {mockReferences.map((reference) => {
                const ReferenceCard = () => {
                  const [isOpen, setIsOpen] = useState(false)
                  const [metadata, setMetadata] = useState<LinkMetadata | null>(null)
                  const [loading, setLoading] = useState(false)
                  let hoverTimeout: number

                  const handleMouseEnter = () => {
                    clearTimeout(hoverTimeout)
                    setIsOpen(true)
                  }

                  const handleMouseLeave = () => {
                    hoverTimeout = setTimeout(() => {
                      setIsOpen(false)
                    }, 200)
                  }
                  // Fetch metadata when popover opens
                  useEffect(() => {
                    if (isOpen && !metadata && !loading) {
                      setLoading(true)

                      fetchLinkMetadata(reference.url)
                        .then((data: LinkMetadata) => {
                          console.log(data)
                          setMetadata(data)
                          setLoading(false)
                        })
                        .catch((err: Error) => {
                          console.error('Failed to fetch metadata:', err)
                          setMetadata({ title: reference.url, description: '', ogImage: '' })
                          setLoading(false)
                        })
                    }
                  }, [isOpen, metadata, loading])

                  return (
                    <Popover open={isOpen} onOpenChange={setIsOpen}>
                      <PopoverTrigger asChild>
                        <a
                          href={reference.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-start gap-3 p-3 rounded-lg bg-muted/20 border border-muted-foreground/10 hover:bg-muted/30 hover:border-primary/30 transition-colors group"
                          onMouseEnter={handleMouseEnter}
                          onMouseLeave={handleMouseLeave}
                        >
                          <div className="p-2 rounded-md bg-primary/10 shrink-0">
                            <Link className={cn("w-4 h-4", accent.text)} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <h4 className="font-medium text-sm line-clamp-1 group-hover:text-primary transition-colors">
                              {metadata?.title || reference.url}
                            </h4>
                            <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                              {new URL(reference.url).hostname}
                            </p>
                            <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                              <Clock className="w-3 h-3" />
                              Added {reference.addedAt}
                            </div>
                          </div>
                        </a>
                      </PopoverTrigger>
                      <PopoverContent
                        side="right"
                        className="max-w-md p-0 overflow-hidden"
                        onMouseEnter={handleMouseEnter}
                        onMouseLeave={handleMouseLeave}
                      >
                        {loading ? (
                          <div className="p-6 flex items-center justify-center">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                          </div>
                        ) : (
                          <div className="space-y-3">
                            {metadata?.ogImage && (
                              <img
                                src={metadata.ogImage}
                                alt={metadata.title}
                                className="w-full h-32 object-cover"
                                onError={(e) => {
                                  (e.target as HTMLImageElement).style.display = 'none'
                                }}
                              />
                            )}
                            <div className="p-3 space-y-2">
                              <h4 className="font-semibold text-sm">{metadata?.title || 'No title'}</h4>
                              {metadata?.description && (
                                <p className="text-xs text-muted-foreground line-clamp-6">
                                  {metadata.description.slice(0, 400)}
                                  {metadata.description.length > 400 ? '...' : ''}
                                </p>
                              )}
                              <p className="text-xs text-primary font-medium">{new URL(reference.url).hostname}</p>
                            </div>
                          </div>
                        )}
                      </PopoverContent>
                    </Popover>
                  )
                }

                return <ReferenceCard key={reference.id} />
              })}
            </CardContent>
          </Card>

          {/* Generated Blobs */}
          <Card className="border-muted-foreground/20">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className={accent.text}>Generated Content</CardTitle>
                  <CardDescription>AI-generated and exported files</CardDescription>
                </div>
                <Button variant="ghost" size="sm" className={cn("gap-1 text-xs", accent.text)}>
                  View All
                  <ChevronRight className="w-3 h-3" />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {mockGeneratedBlobs.map((blob) => {
                  // Determine icon based on file type
                  const getFileIcon = () => {
                    const iconClass = cn("w-5 h-5", accent.text)
                    switch (blob.type) {
                      case 'Image':
                        return <FileImage className={iconClass} />
                      case 'Video':
                        return <FileVideo className={iconClass} />
                      case 'Audio':
                        return <FileAudio className={iconClass} />
                      case 'Document':
                        return <FileText className={iconClass} />
                      case 'Spreadsheet':
                        return <FileSpreadsheet className={iconClass} />
                      default:
                        return <FileCode className={iconClass} />
                    }
                  }

                  return (
                    <div
                      key={blob.id}
                      className="flex items-center justify-between p-3 rounded-lg bg-muted/20 border border-muted-foreground/10 hover:bg-muted/30 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-md bg-primary/10">
                          {getFileIcon()}
                        </div>
                        <div>
                          <h4 className="font-medium text-sm">{blob.name}</h4>
                          <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                            <span>{blob.fileType}</span>
                            <span>•</span>
                            <span>{blob.size}</span>
                            <span>•</span>
                            <span>{blob.generatedBy}</span>
                            <span>•</span>
                            <span>{blob.generatedAt}</span>
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
                  )
                })}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default ViewWorkspace


