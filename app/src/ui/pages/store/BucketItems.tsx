import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { cn, resolveApiAssetUrl, formatRelativeTime } from '@/lib/utils'
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
  HardDrive,
  ArrowUpDown,
  Loader2,
  Clock
} from 'lucide-react'
import {
  getBucket,
  listBucketItems,
  type BucketItemRecord,
  type BucketRecord,
} from '@/lib/apis'
import {
  getBucketAllowedTypeLabel,
  normalizeBucketAllowedType,
  parseBucketAllowedTypes,
  type BucketAllowedType,
} from '@/lib/bucket-types'

const typeConfig: Record<BucketAllowedType, { icon: React.ElementType; color: string; label: string }> = {
  image: { icon: Image, color: 'text-blue-400', label: 'Image' },
  video: { icon: Video, color: 'text-purple-400', label: 'Video' },
  files: { icon: FileText, color: 'text-green-400', label: 'Files' },
  audio: { icon: Music, color: 'text-orange-400', label: 'Audio' },
  other: { icon: Files, color: 'text-pink-400', label: 'Other' }
}

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


const openAsset = (item: BucketItemRecord) => {
  const url = resolveApiAssetUrl(`/bucket/items/${item.id}/asset`)
  if (url) {
    window.open(url, '_blank', 'noopener,noreferrer')
  }
}

const downloadAsset = (item: BucketItemRecord) => {
  const url = resolveApiAssetUrl(`/bucket/items/${item.id}/asset`)
  if (!url) return
  const link = document.createElement('a')
  link.href = url
  link.download = item.file_name
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const BucketItems = () => {
  const { bucketId, type } = useParams()
  const [searchQuery, setSearchQuery] = useState('')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [sortOrder, setSortOrder] = useState<'newest' | 'oldest' | 'name' | 'size'>('newest')
  const [bucket, setBucket] = useState<BucketRecord | null>(null)
  const [items, setItems] = useState<BucketItemRecord[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!bucketId) return

    let isCancelled = false
    setIsLoading(true)

    const loadBucketItems = async () => {
      try {
        const bucketRecord = await getBucket(bucketId)
        if (isCancelled) return
        setBucket(bucketRecord)

        const itemPage = await listBucketItems({
          bucketId,
          page: 1,
          size: Math.min(Math.max(bucketRecord.total_files, 1), 200),
          sortBy: 'created_at',
          sortOrder: 'desc',
        })
        if (isCancelled) return
        setItems(itemPage.items.filter((item) => !item.is_deleted))
      } catch (error) {
        if (isCancelled) return
        console.error('Failed to load bucket items', error)
        setBucket(null)
        setItems([])
      } finally {
        if (!isCancelled) {
          setIsLoading(false)
        }
      }
    }

    void loadBucketItems()

    return () => {
      isCancelled = true
    }
  }, [bucketId])

  const allowedTypes = useMemo(() => {
    return parseBucketAllowedTypes(bucket?.allowed_file_types)
  }, [bucket?.allowed_file_types])

  const currentType = useMemo<BucketAllowedType>(() => {
    const normalizedRouteType = normalizeBucketAllowedType(type)
    if (normalizedRouteType && (allowedTypes.length === 0 || allowedTypes.includes(normalizedRouteType))) {
      return normalizedRouteType
    }
    return allowedTypes[0] ?? 'files'
  }, [allowedTypes, type])

  const config = typeConfig[currentType] || typeConfig.files
  const Icon = config.icon

  const assets = useMemo(() => {
    return items.filter((item) => normalizeBucketAllowedType(item.file_format) === currentType)
  }, [currentType, items])

  const filteredAssets = useMemo(() => {
    let filtered = assets.filter(asset =>
      asset.file_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      asset.file_format.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (asset.summary || '').toLowerCase().includes(searchQuery.toLowerCase())
    )

    switch (sortOrder) {
      case 'newest':
        filtered = [...filtered].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        break
      case 'oldest':
        filtered = [...filtered].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
        break
      case 'name':
        filtered = [...filtered].sort((a, b) => a.file_name.localeCompare(b.file_name))
        break
      case 'size':
        filtered = [...filtered].sort((a, b) => b.file_size - a.file_size)
        break
    }

    return filtered
  }, [assets, searchQuery, sortOrder])

  // Selection handlers
  const toggleSelectAll = () => {
    if (selectedIds.size === filteredAssets.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filteredAssets.map((asset) => asset.id)))
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

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="size-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!bucket) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-muted-foreground">Bucket not found.</p>
      </div>
    )
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
                  {getBucketAllowedTypeLabel(currentType)}
                </h1>
                <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1.5">
                    <Files className="size-4" />
                    {filteredAssets.length} items
                  </span>
                  <span className="flex items-center gap-1.5">
                    <HardDrive className="size-4" />
                    {formatBytes(filteredAssets.reduce((acc, asset) => acc + asset.file_size, 0))}
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

            <Select value={sortOrder} onValueChange={(v) => setSortOrder(v as typeof sortOrder)}>
              <SelectTrigger className="w-40">
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
                  <div className="relative aspect-4/3 bg-muted/30">
                    {currentType === 'image' ? (
                      <img
                        src={resolveApiAssetUrl(`/bucket/items/${asset.id}/asset`) || undefined}
                        alt=""
                        className="w-full h-full object-cover rounded-t-lg"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Icon className={cn("size-12 opacity-30", config.color)} />
                      </div>
                    )}

                    {/* Overlay */}
                    <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                      <Button size="icon" variant="secondary" className="h-8 w-8" onClick={() => openAsset(asset)}>
                        <Eye className="size-4" />
                      </Button>
                      <Button size="icon" variant="secondary" className="h-8 w-8" onClick={() => downloadAsset(asset)}>
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
                      {asset.file_format.toUpperCase()}
                    </Badge>
                  </div>
                  <CardContent className="p-3">
                    <p className="text-sm font-medium truncate" title={asset.file_name}>
                      {asset.file_name}
                    </p>
                    <div className="flex items-center justify-between mt-1.5 text-xs text-muted-foreground">
                      <span>{formatBytes(asset.file_size)}</span>
                      <span>{formatRelativeTime(asset.created_at)}</span>
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
                    {currentType === 'image' ? (
                      <img src={resolveApiAssetUrl(`/bucket/items/${asset.id}/asset`) || undefined} alt="" className="w-full h-full object-cover" />
                    ) : (
                      <Icon className={cn("size-6", config.color)} />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate">{asset.file_name}</p>
                    <div className="flex items-center gap-3 mt-0.5 text-xs text-muted-foreground">
                      <Badge variant="outline" className="text-[10px]">{asset.file_format.toUpperCase()}</Badge>
                      <span>{formatBytes(asset.file_size)}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 text-xs text-muted-foreground whitespace-nowrap">
                    <Clock className="size-3.5" />
                    {formatRelativeTime(asset.created_at)}
                  </div>

                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => openAsset(asset)}>
                      <Eye className="size-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => downloadAsset(asset)}>
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
                {searchQuery ? 'Try adjusting your search query' : `${bucket.name} has no ${config.label.toLowerCase()} items yet`}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default BucketItems