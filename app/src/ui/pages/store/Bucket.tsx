import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  FolderOpen,
  Plus,
  Search,
  MoreVertical,
  Image,
  Video,
  FileText,
  Music,
  Files,
  Clock,
  HardDrive,
  Trash2,
  Edit,
  Calendar
} from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import CreateBucketModal from '@/components/modals/CreateBucketModal'
import { createBucket, deleteBucket, listBuckets, type BucketRecord } from '@/lib/apis'

// Mock bucket data
interface Bucket {
  id: string
  name: string
  description: string
  stats: {
    images: number
    videos: number
    files: number
    audio: number
    others: number
  }
  totalSize: string
  createdAt: string
  lastUpdated: string
  color: string
}

const COLORS = ['blue-400', 'purple-400', 'green-400', 'orange-400', 'pink-400'] as const

const formatBytes = (bytes: number): string => {
  if (bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let value = bytes
  let unitIndex = 0
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }
  return `${value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`
}

const formatDate = (value: string): string => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

const mapBucketRecord = (record: BucketRecord, index: number): Bucket => {
  return {
    id: record.id,
    name: record.name,
    description: record.description || 'No description available',
    stats: {
      images: 0,
      videos: 0,
      files: record.total_files,
      audio: 0,
      others: 0,
    },
    totalSize: formatBytes(record.total_size),
    createdAt: formatDate(record.created_at),
    lastUpdated: formatDate(record.updated_at),
    color: COLORS[index % COLORS.length],
  }
}

const getColorClasses = (color: string) => {
  const colorMap: Record<string, { text: string; bg: string; border: string }> = {
    'blue-400': { text: 'text-blue-400', bg: 'bg-blue-400/10', border: 'border-blue-400/30' },
    'purple-400': { text: 'text-purple-400', bg: 'bg-purple-400/10', border: 'border-purple-400/30' },
    'green-400': { text: 'text-green-400', bg: 'bg-green-400/10', border: 'border-green-400/30' },
    'orange-400': { text: 'text-orange-400', bg: 'bg-orange-400/10', border: 'border-orange-400/30' },
    'pink-400': { text: 'text-pink-400', bg: 'bg-pink-400/10', border: 'border-pink-400/30' },
  }
  return colorMap[color] || colorMap['blue-400']
}

const Bucket = () => {
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [buckets, setBuckets] = useState<Bucket[]>([])
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const loadBuckets = async () => {
    setIsLoading(true)
    try {
      const response = await listBuckets({
        page: 1,
        size: 200,
        sortBy: 'updated_at',
        sortOrder: 'desc',
      })

      const mapped = response.items.map((item, index) => mapBucketRecord(item, index))
      setBuckets(mapped)
    } catch (error) {
      console.error('Failed to fetch buckets', error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void loadBuckets()
  }, [])

  const handleCreateBucket = async (name: string) => {
    const trimmed = name.trim()
    if (!trimmed) return

    try {
      const created = await createBucket({
        name: trimmed,
        description: 'Created from Deep Researcher UI',
        allowed_file_types:
          'pdf,doc,docx,xls,xlsx,png,jpg,jpeg,webp,mp4,mp3,txt,csv,json,zip',
        created_by:
          localStorage.getItem('dr_profile_email') ||
          localStorage.getItem('dr_profile_name') ||
          'local-user',
        deletable: true,
        status: true,
      })

      setBuckets((prev) => [mapBucketRecord(created, 0), ...prev])
    } catch (error) {
      console.error('Failed to create bucket', error)
      alert(error instanceof Error ? error.message : 'Failed to create bucket')
    }
  }

  const handleDeleteBucket = async (bucketId: string, event: React.MouseEvent) => {
    event.stopPropagation()
    try {
      await deleteBucket(bucketId)
      setBuckets((prev) => prev.filter((bucket) => bucket.id !== bucketId))
    } catch (error) {
      console.error('Failed to delete bucket', error)
      alert(error instanceof Error ? error.message : 'Failed to delete bucket')
    }
  }

  const filteredBuckets = buckets.filter(bucket =>
    bucket.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    bucket.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const getTotalItems = (stats: Bucket['stats']) => {
    return stats.images + stats.videos + stats.files + stats.audio + stats.others
  }

  return (
    <div className="flex flex-col h-full w-full bg-muted/10 overflow-hidden animate-in fade-in duration-500">
      {/* Header Section */}
      <div className="shrink-0 border-b bg-background/50 backdrop-blur-sm sticky top-0 z-30">
        <div className="w-full px-8 py-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="size-12 rounded-2xl bg-linear-to-br from-primary/20 via-primary/10 to-transparent border border-primary/20 flex items-center justify-center animate-in fade-in zoom-in duration-500">
                <HardDrive className="size-6 text-primary" />
              </div>
              <div>
                <h1 className="text-xl font-semibold tracking-tight">
                  Storage Buckets
                </h1>
                <p className="text-sm text-muted-foreground">
                  Organize and manage your media assets
                </p>
              </div>
            </div>

            <Button
              onClick={() => setIsModalOpen(true)}
              className="gap-2"
            >
              <Plus className="size-4" />
              Create Bucket
            </Button>
          </div>

          <div className="flex items-center gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
              <Input
                placeholder="Search buckets..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="pl-9 bg-background"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto w-full">
        <div className="p-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 pb-10">
          {/* Create Bucket Card */}
          <Card
            className="flex flex-col items-center justify-center min-h-80 border-dashed border-2 hover:border-primary/50 hover:bg-muted/50 transition-all cursor-pointer group bg-muted/10 p-0"
            onClick={() => setIsModalOpen(true)}
          >
            <div className="rounded-full bg-background p-4 mb-4 group-hover:scale-110 transition-transform shadow-sm border">
              <Plus className="w-8 h-8 text-muted-foreground group-hover:text-primary transition-colors" />
            </div>
            <h3 className="font-semibold text-lg text-primary/80 transition-colors">Create Bucket</h3>
            <p className="text-sm text-muted-foreground/60 mt-1">Start organizing your data</p>
          </Card>

          {/* Bucket Cards */}
          {filteredBuckets.map((bucket) => {
            const colors = getColorClasses(bucket.color)
            return (
              <Card
                key={bucket.id}
                className="min-h-80 flex flex-col shadow-lg hover:shadow-2xl transition-all cursor-pointer relative overflow-hidden group border-muted-foreground/20 p-0 py-0 gap-0 hover:border-primary/30"
                onClick={() => navigate(`/data/bucket/${bucket.id}`)}
              >
                <CardHeader className="pt-5 pb-3 px-5">
                  <div className="flex justify-between items-start gap-3">
                    <div className={cn("p-2.5 rounded-xl", colors.bg)}>
                      <FolderOpen className={cn("w-5 h-5", colors.text)} />
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild onClick={e => e.stopPropagation()}>
                        <Button variant="ghost" size="icon" className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity">
                          <MoreVertical className="w-4 h-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={e => e.stopPropagation()}>
                          <Edit className="w-4 h-4 mr-2" />
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={(e) => handleDeleteBucket(bucket.id, e)} className="text-destructive">
                          <Trash2 className="w-4 h-4 mr-2" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                  <div className="mt-3">
                    <CardTitle className="line-clamp-1 text-lg group-hover:text-primary transition-colors">
                      {bucket.name}
                    </CardTitle>
                    <CardDescription className="line-clamp-2 h-10 text-xs mt-1.5">
                      {bucket.description}
                    </CardDescription>
                  </div>
                </CardHeader>

                <CardContent className="flex-1 px-5 py-3">
                  {/* Asset Type Stats */}
                  <div className="grid grid-cols-5 gap-2">
                    <div className="flex flex-col items-center p-2 rounded-lg bg-muted/30">
                      <Image className="w-4 h-4 text-blue-400 mb-1" />
                      <span className="text-xs font-medium">{bucket.stats.images}</span>
                    </div>
                    <div className="flex flex-col items-center p-2 rounded-lg bg-muted/30">
                      <Video className="w-4 h-4 text-purple-400 mb-1" />
                      <span className="text-xs font-medium">{bucket.stats.videos}</span>
                    </div>
                    <div className="flex flex-col items-center p-2 rounded-lg bg-muted/30">
                      <FileText className="w-4 h-4 text-green-400 mb-1" />
                      <span className="text-xs font-medium">{bucket.stats.files}</span>
                    </div>
                    <div className="flex flex-col items-center p-2 rounded-lg bg-muted/30">
                      <Music className="w-4 h-4 text-orange-400 mb-1" />
                      <span className="text-xs font-medium">{bucket.stats.audio}</span>
                    </div>
                    <div className="flex flex-col items-center p-2 rounded-lg bg-muted/30">
                      <Files className="w-4 h-4 text-pink-400 mb-1" />
                      <span className="text-xs font-medium">{bucket.stats.others}</span>
                    </div>
                  </div>

                  {/* Total Stats */}
                  <div className="flex items-center justify-between mt-4 pt-3 border-t border-muted-foreground/10">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Files className="w-4 h-4" />
                      <span className="text-xs">{getTotalItems(bucket.stats)} items</span>
                    </div>
                    <Badge variant="secondary" className="text-xs font-normal">
                      {bucket.totalSize}
                    </Badge>
                  </div>
                </CardContent>

                <CardFooter className="py-3 px-5 text-[10px] grid grid-cols-2 gap-2 bg-muted/10 border-t border-muted-foreground/10 items-center">
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[9px] text-muted-foreground/60 uppercase font-bold tracking-widest">Created</span>
                    <div className="flex items-center gap-1.5 text-foreground/70">
                      <Calendar className="w-3 h-3 text-muted-foreground/50" />
                      <span className="truncate">{bucket.createdAt}</span>
                    </div>
                  </div>
                  <div className="flex flex-col gap-0.5 border-l border-muted-foreground/10 pl-3">
                    <span className="text-[9px] text-muted-foreground/60 uppercase font-bold tracking-widest">Modified</span>
                    <div className="flex items-center gap-1.5 text-foreground/70">
                      <Clock className="w-3 h-3 text-muted-foreground/50" />
                      <span className="truncate">{bucket.lastUpdated}</span>
                    </div>
                  </div>
                </CardFooter>
              </Card>
            )
          })}
        </div>

        {/* Empty State */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <FolderOpen className="w-16 h-16 text-muted-foreground/30 mb-4 animate-pulse" />
            <h3 className="text-lg font-medium text-muted-foreground">Loading buckets...</h3>
          </div>
        )}

        {!isLoading && filteredBuckets.length === 0 && searchQuery && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <FolderOpen className="w-16 h-16 text-muted-foreground/30 mb-4" />
            <h3 className="text-lg font-medium text-muted-foreground">No buckets found</h3>
            <p className="text-sm text-muted-foreground/60 mt-1">
              Try adjusting your search query
            </p>
          </div>
        )}
      </div>

      <CreateBucketModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onCreate={handleCreateBucket}
      />
    </div>
  )
}

export default Bucket