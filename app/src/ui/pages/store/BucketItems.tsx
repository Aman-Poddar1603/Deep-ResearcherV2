import { useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { cn } from '@/lib/utils'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {  
  Search,
  Grid3X3,
  List,
  Download,
  Trash2,
  Eye,
  Image,
  Video,
  FileText,
  Music,
  Files,
  Calendar,
  HardDrive,
  ArrowUpDown,
  Filter,
  ChevronDown
} from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'

// Asset item type
interface AssetItem {
  id: string
  name: string
  type: 'images' | 'videos' | 'files' | 'audio' | 'others'
  size: string
  createdAt: string
  thumbnail?: string
  format: string
}

// Generate mock data
const generateMockAssets = (type: string, count: number): AssetItem[] => {
  const formats: Record<string, string[]> = {
    images: ['PNG', 'JPG', 'WEBP', 'SVG', 'GIF'],
    videos: ['MP4', 'MOV', 'AVI', 'WEBM'],
    files: ['PDF', 'DOCX', 'XLSX', 'TXT', 'CSV'],
    audio: ['MP3', 'WAV', 'FLAC', 'AAC'],
    others: ['ZIP', 'RAR', 'JSON', 'XML', 'YAML']
  }

  const names: Record<string, string[]> = {
    images: ['Screenshot', 'Photo', 'Diagram', 'Chart', 'Banner', 'Icon', 'Logo', 'Background'],
    videos: ['Recording', 'Demo', 'Tutorial', 'Presentation', 'Interview'],
    files: ['Report', 'Document', 'Spreadsheet', 'Analysis', 'Summary', 'Data Export'],
    audio: ['Recording', 'Podcast', 'Interview', 'Music Track', 'Voiceover'],
    others: ['Archive', 'Backup', 'Config', 'Data Bundle', 'Export Package']
  }

  const typeFormats = formats[type] || formats.others
  const typeNames = names[type] || names.others

  return Array.from({ length: count }).map((_, i) => ({
    id: `asset-${type}-${i + 1}`,
    name: `${typeNames[Math.floor(Math.random() * typeNames.length)]}_${Date.now() + i}.${typeFormats[Math.floor(Math.random() * typeFormats.length)].toLowerCase()}`,
    type: type as AssetItem['type'],
    size: `${(Math.random() * 10 + 0.1).toFixed(1)} MB`,
    createdAt: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
    format: typeFormats[Math.floor(Math.random() * typeFormats.length)],
    thumbnail: type === 'images' ? `https://picsum.photos/seed/${i}/200/150` : undefined
  }))
}

const typeConfig: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  images: { icon: Image, color: 'text-blue-400', label: 'Images' },
  videos: { icon: Video, color: 'text-purple-400', label: 'Videos' },
  files: { icon: FileText, color: 'text-green-400', label: 'Files' },
  audio: { icon: Music, color: 'text-orange-400', label: 'Audio' },
  others: { icon: Files, color: 'text-pink-400', label: 'Others' }
}

const BucketItems = () => {
  const { type } = useParams()
  const [searchQuery, setSearchQuery] = useState('')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [sortOrder, setSortOrder] = useState<'newest' | 'oldest' | 'name' | 'size'>('newest')

  const currentType = type || 'images'
  const config = typeConfig[currentType] || typeConfig.images
  const Icon = config.icon

  // Generate mock data based on type
  const assets = useMemo(() => {
    const count = Math.floor(Math.random() * 30) + 20
    return generateMockAssets(currentType, count)
  }, [currentType])

  // Filter and sort
  const filteredAssets = useMemo(() => {
    let filtered = assets.filter(asset =>
      asset.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      asset.format.toLowerCase().includes(searchQuery.toLowerCase())
    )

    switch (sortOrder) {
      case 'newest':
        filtered = [...filtered].reverse()
        break
      case 'oldest':
        // Already in order
        break
      case 'name':
        filtered = [...filtered].sort((a, b) => a.name.localeCompare(b.name))
        break
      case 'size':
        filtered = [...filtered].sort((a, b) => parseFloat(b.size) - parseFloat(a.size))
        break
    }

    return filtered
  }, [assets, searchQuery, sortOrder])

  // Selection handlers
  const toggleSelectAll = () => {
    if (selectedIds.size === filteredAssets.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filteredAssets.map(a => a.id)))
    }
  }

  const toggleSelect = (id: string) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }

  return (
    <div className="flex flex-col h-full w-full bg-muted/10 overflow-hidden animate-in fade-in duration-500">
      {/* Header Section */}
      <div className="shrink-0 border-b bg-background/50 backdrop-blur-sm sticky top-0 z-30">
        <div className="w-full px-8 py-6">

          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <div className={cn(
                "size-14 rounded-2xl bg-linear-to-br from-primary/20 via-primary/10 to-transparent border border-primary/20 flex items-center justify-center"
              )}>
                <Icon className={cn("size-7", config.color)} />
              </div>
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">
                  {config.label}
                </h1>
                <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1.5">
                    <Files className="size-4" />
                    {filteredAssets.length} items
                  </span>
                  <span className="flex items-center gap-1.5">
                    <HardDrive className="size-4" />
                    {(filteredAssets.reduce((acc, a) => acc + parseFloat(a.size), 0)).toFixed(1)} MB
                  </span>
                </div>
              </div>
            </div>

            {/* Bulk Actions */}
            {selectedIds.size > 0 && (
              <div className="flex items-center gap-2 animate-in fade-in slide-in-from-right-4 duration-300">
                <span className="text-sm text-muted-foreground mr-2">
                  {selectedIds.size} selected
                </span>
                <Button variant="outline" size="sm" className="gap-2">
                  <Download className="size-4" />
                  Download
                </Button>
                <Button variant="destructive" size="sm" className="gap-2">
                  <Trash2 className="size-4" />
                  Delete
                </Button>
              </div>
            )}
          </div>

          {/* Filters & Search */}
          <div className="flex items-center gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
              <Input
                placeholder="Search assets..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="pl-9 bg-background"
              />
            </div>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="gap-2">
                  <Filter className="size-4" />
                  Filter
                  <ChevronDown className="size-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuItem>All Formats</DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem>PNG</DropdownMenuItem>
                <DropdownMenuItem>JPG</DropdownMenuItem>
                <DropdownMenuItem>WEBP</DropdownMenuItem>
                <DropdownMenuItem>Other</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <Select value={sortOrder} onValueChange={(v) => setSortOrder(v as typeof sortOrder)}>
              <SelectTrigger className="w-[160px]">
                <ArrowUpDown className="size-4 mr-2" />
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="newest">Newest First</SelectItem>
                <SelectItem value="oldest">Oldest First</SelectItem>
                <SelectItem value="name">Name</SelectItem>
                <SelectItem value="size">Size</SelectItem>
              </SelectContent>
            </Select>

            <div className="flex items-center border rounded-lg overflow-hidden">
              <Button
                variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('grid')}
                className="rounded-none"
              >
                <Grid3X3 className="size-4" />
              </Button>
              <Button
                variant={viewMode === 'list' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('list')}
                className="rounded-none"
              >
                <List className="size-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto w-full">
        <div className="p-8">
          {/* Select All */}
          <div className="flex items-center gap-3 mb-4 pb-4 border-b border-muted-foreground/10">
            <Checkbox
              checked={filteredAssets.length > 0 && selectedIds.size === filteredAssets.length}
              onCheckedChange={toggleSelectAll}
            />
            <span className="text-sm text-muted-foreground">
              Select all ({filteredAssets.length} items)
            </span>
          </div>

          {viewMode === 'grid' ? (
            /* Grid View */
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
              {filteredAssets.map((asset) => (
                <Card
                  key={asset.id}
                  className={cn(
                    "py-0 group cursor-pointer transition-all hover:shadow-lg border-muted-foreground/20 overflow-hidden",
                    selectedIds.has(asset.id) && "ring-2 ring-primary"
                  )}
                >
                  <div className="relative aspect-[4/3] bg-muted/30">
                    {asset.thumbnail ? (
                      <img
                        src={asset.thumbnail}
                        alt={asset.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Icon className={cn("size-12 opacity-30", config.color)} />
                      </div>
                    )}

                    {/* Overlay */}
                    <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                      <Button size="icon" variant="secondary" className="h-8 w-8">
                        <Eye className="size-4" />
                      </Button>
                      <Button size="icon" variant="secondary" className="h-8 w-8">
                        <Download className="size-4" />
                      </Button>
                    </div>

                    {/* Checkbox */}
                    <div className="absolute top-2 left-2">
                      <Checkbox
                        checked={selectedIds.has(asset.id)}
                        onCheckedChange={() => toggleSelect(asset.id)}
                        className="bg-background/80 backdrop-blur-sm"
                        onClick={e => e.stopPropagation()}
                      />
                    </div>

                    {/* Format Badge */}
                    <Badge
                      variant="secondary"
                      className="absolute top-2 right-2 text-[10px] font-medium"
                    >
                      {asset.format}
                    </Badge>
                  </div>
                  <CardContent className="p-3">
                    <p className="text-sm font-medium truncate" title={asset.name}>
                      {asset.name}
                    </p>
                    <div className="flex items-center justify-between mt-1.5 text-xs text-muted-foreground">
                      <span>{asset.size}</span>
                      <span>{asset.createdAt}</span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            /* List View */
            <div className="space-y-2">
              {filteredAssets.map((asset) => (
                <div
                  key={asset.id}
                  className={cn(
                    "flex items-center gap-4 p-3 rounded-lg bg-muted/20 border border-muted-foreground/10 hover:bg-muted/30 transition-colors group",
                    selectedIds.has(asset.id) && "ring-2 ring-primary bg-primary/5"
                  )}
                >
                  <Checkbox
                    checked={selectedIds.has(asset.id)}
                    onCheckedChange={() => toggleSelect(asset.id)}
                  />

                  <div className="size-12 rounded-lg bg-muted/50 flex items-center justify-center shrink-0 overflow-hidden">
                    {asset.thumbnail ? (
                      <img src={asset.thumbnail} alt="" className="w-full h-full object-cover" />
                    ) : (
                      <Icon className={cn("size-6", config.color)} />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate">{asset.name}</p>
                    <div className="flex items-center gap-3 mt-0.5 text-xs text-muted-foreground">
                      <Badge variant="outline" className="text-[10px]">{asset.format}</Badge>
                      <span>{asset.size}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Calendar className="size-3.5" />
                    {asset.createdAt}
                  </div>

                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <Eye className="size-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <Download className="size-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 hover:text-destructive">
                      <Trash2 className="size-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Empty State */}
          {filteredAssets.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Icon className={cn("size-16 opacity-30 mb-4", config.color)} />
              <h3 className="text-lg font-medium text-muted-foreground">No assets found</h3>
              <p className="text-sm text-muted-foreground/60 mt-1">
                {searchQuery ? 'Try adjusting your search query' : 'Upload some assets to get started'}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default BucketItems