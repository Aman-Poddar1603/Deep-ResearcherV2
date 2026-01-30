import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Plus, FileText, MessageSquare, Files, Clock, Calendar, Briefcase, TrendingUp, Users, LucideIcon } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

// Mock Data Type
interface Workspace {
  id: string
  title: string
  description: string
  researchCount: number
  chatCount: number
  fileCount: number
  createdAt: string
  lastUpdated: string
  icon: LucideIcon
  color: string
}

const mockWorkspaces: Workspace[] = [
  {
    id: '1',
    title: 'Market Analysis 2024',
    description: 'Deep dive into emerging tech markets and competitor landscape.',
    researchCount: 5,
    chatCount: 12,
    fileCount: 8,
    createdAt: 'Jan 15, 2024',
    lastUpdated: '2 mins ago',
    icon: TrendingUp,
    color: 'text-blue-400',
  },
  {
    id: '2',
    title: 'Competitor Tracking',
    description: 'Ongoing tracking of main competitors in the SaaS space.',
    researchCount: 3,
    chatCount: 8,
    fileCount: 15,
    createdAt: 'Dec 10, 2023',
    lastUpdated: '1 hour ago',
    icon: Users,
    color: 'text-purple-400',
  },
  {
    id: '3',
    title: 'User Feedback Loop',
    description: 'Analyzing user feedback from Q4 surveys.',
    researchCount: 8,
    chatCount: 24,
    fileCount: 42,
    createdAt: 'Nov 20, 2023',
    lastUpdated: '2 days ago',
    icon: Briefcase,
    color: 'text-green-400',
  },
  {
    id: '3',
    title: 'User Feedback Loop',
    description: 'Analyzing user feedback from Q4 surveys.',
    researchCount: 8,
    chatCount: 24,
    fileCount: 42,
    createdAt: 'Nov 20, 2023',
    lastUpdated: '2 days ago',
    icon: Briefcase,
    color: 'text-green-400',
  },
  {
    id: '3',
    title: 'User Feedback Loop',
    description: 'Analyzing user feedback from Q4 surveys.',
    researchCount: 8,
    chatCount: 24,
    fileCount: 42,
    createdAt: 'Nov 20, 2023',
    lastUpdated: '2 days ago',
    icon: Briefcase,
    color: 'text-green-400',
  },
  {
    id: '3',
    title: 'User Feedback Loop',
    description: 'Analyzing user feedback from Q4 surveys.',
    researchCount: 8,
    chatCount: 24,
    fileCount: 42,
    createdAt: 'Nov 20, 2023',
    lastUpdated: '2 days ago',
    icon: Briefcase,
    color: 'text-green-400',
  },
  {
    id: '2',
    title: 'Competitor Tracking',
    description: 'Ongoing tracking of main competitors in the SaaS space.',
    researchCount: 3,
    chatCount: 8,
    fileCount: 15,
    createdAt: 'Dec 10, 2023',
    lastUpdated: '1 hour ago',
    icon: Users,
    color: 'text-purple-400',
  },
  {
    id: '3',
    title: 'User Feedback Loop',
    description: 'Analyzing user feedback from Q4 surveys.',
    researchCount: 8,
    chatCount: 24,
    fileCount: 42,
    createdAt: 'Nov 20, 2023',
    lastUpdated: '2 days ago',
    icon: Briefcase,
    color: 'text-green-400',
  },
  {
    id: '3',
    title: 'User Feedback Loop',
    description: 'Analyzing user feedback from Q4 surveys.',
    researchCount: 8,
    chatCount: 24,
    fileCount: 42,
    createdAt: 'Nov 20, 2023',
    lastUpdated: '2 days ago',
    icon: Briefcase,
    color: 'text-green-400',
  },
  {
    id: '3',
    title: 'User Feedback Loop',
    description: 'Analyzing user feedback from Q4 surveys.',
    researchCount: 8,
    chatCount: 24,
    fileCount: 42,
    createdAt: 'Nov 20, 2023',
    lastUpdated: '2 days ago',
    icon: Briefcase,
    color: 'text-green-400',
  },
  {
    id: '3',
    title: 'User Feedback Loop',
    description: 'Analyzing user feedback from Q4 surveys.',
    researchCount: 8,
    chatCount: 24,
    fileCount: 42,
    createdAt: 'Nov 20, 2023',
    lastUpdated: '2 days ago',
    icon: Briefcase,
    color: 'text-green-400',
  },
]

const AllWorkspaces = () => {
  const navigate = useNavigate();
  return (
    <div className="p-8 space-y-8 h-full text-foreground animate-in fade-in duration-500 overflow-y-auto">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">Your Workspaces</h1>
        <p className="text-muted-foreground">Manage and organize your research projects.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 pb-10">
        {/* Create Workspace Card */}
        <Card className="flex flex-col items-center justify-center min-h-[300px] border-dashed border-2 hover:border-primary/50 hover:bg-muted/50 transition-all cursor-pointer group bg-muted/10 p-0" onClick={() => { navigate("/workspaces/new") }}>
          <div className="rounded-full bg-background p-4 mb-4 group-hover:scale-110 transition-transform shadow-sm border">
            <Plus className="w-8 h-8 text-muted-foreground group-hover:text-primary transition-colors" />
          </div>
          <h3 className="font-semibold text-lg text-primary/80 transition-colors">Create Workspace</h3>
          <p className="text-sm text-muted-foreground/60 mt-1">Start a new project</p>
        </Card>

        {/* Existing Workspaces */}
        {mockWorkspaces.map((workspace) => (
          <Card key={workspace.id} className="min-h-[300px] flex flex-col shadow-lg hover:shadow-2xl transition-shadow cursor-pointer relative overflow-hidden group border-muted-foreground/20 p-0 py-0 gap-0">
            <CardHeader className="pt-6 pb-2 px-6">
              <div className="flex justify-between items-start gap-4">
                <div className={`p-2 rounded-lg bg-secondary/30 ${workspace.color}`}>
                  <workspace.icon className="w-5 h-5" />
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
      </div>
    </div>
  )
}

export default AllWorkspaces
