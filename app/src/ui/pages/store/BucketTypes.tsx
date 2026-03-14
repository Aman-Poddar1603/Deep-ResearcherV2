import { useEffect, useMemo, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import {
    Image,
    Video,
    FileText,
    Music,
    Files,
    ArrowRight,
    FolderOpen,
    HardDrive,
    Loader2,
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

interface AssetType {
    id: BucketAllowedType
    name: string
    description: string
    icon: React.ElementType
    count: number
    sizeInBytes: number
    color: string
    gradient: string
}

const TYPE_VISUALS: Record<BucketAllowedType, Omit<AssetType, 'id' | 'name' | 'count' | 'sizeInBytes'>> = {
    image: {
        description: 'Photos, screenshots, and graphics',
        icon: Image,
        color: 'text-blue-400',
        gradient: 'from-blue-500/20 to-blue-600/5',
    },
    video: {
        description: 'Recordings and video content',
        icon: Video,
        color: 'text-purple-400',
        gradient: 'from-purple-500/20 to-purple-600/5',
    },
    files: {
        description: 'Documents, PDFs, spreadsheets, and general files',
        icon: FileText,
        color: 'text-green-400',
        gradient: 'from-green-500/20 to-green-600/5',
    },
    audio: {
        description: 'Music, recordings, and sound files',
        icon: Music,
        color: 'text-orange-400',
        gradient: 'from-orange-500/20 to-orange-600/5',
    },
    other: {
        description: 'Archives, configs, and uncategorized files',
        icon: Files,
        color: 'text-pink-400',
        gradient: 'from-pink-500/20 to-pink-600/5',
    },
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

const BucketTypes = () => {
    const { bucketId } = useParams()
    const navigate = useNavigate()
    const [hoveredType, setHoveredType] = useState<string | null>(null)
    const [bucket, setBucket] = useState<BucketRecord | null>(null)
    const [items, setItems] = useState<BucketItemRecord[]>([])
    const [isLoading, setIsLoading] = useState(true)

    useEffect(() => {
        if (!bucketId) return

        let isCancelled = false
        setIsLoading(true)

        const loadBucketData = async () => {
            try {
                const bucketRecord = await getBucket(bucketId)
                if (isCancelled) return
                setBucket(bucketRecord)

                const itemPage = await listBucketItems({
                    bucketId,
                    page: 1,
                    size: Math.min(Math.max(bucketRecord.total_files, 1), 5000),
                    sortBy: 'created_at',
                    sortOrder: 'desc',
                })
                if (isCancelled) return
                setItems(itemPage.items)
            } catch (error) {
                if (isCancelled) return
                console.error('Failed to load bucket types', error)
                setBucket(null)
                setItems([])
            } finally {
                if (!isCancelled) {
                    setIsLoading(false)
                }
            }
        }

        void loadBucketData()

        return () => {
            isCancelled = true
        }
    }, [bucketId])

    const bucketTypes = useMemo(() => {
        if (!bucket) return []

        return parseBucketAllowedTypes(bucket.allowed_file_types).map((type) => {
            const relevantItems = items.filter(
                (item) => normalizeBucketAllowedType(item.file_format) === type,
            )
            const visual = TYPE_VISUALS[type]

            return {
                id: type,
                name: getBucketAllowedTypeLabel(type),
                description: visual.description,
                icon: visual.icon,
                color: visual.color,
                gradient: visual.gradient,
                count: relevantItems.length,
                sizeInBytes: relevantItems.reduce((sum, item) => sum + item.file_size, 0),
            } satisfies AssetType
        })
    }, [bucket, items])

    const totalSize = useMemo(() => {
        return formatBytes(bucket?.total_size ?? 0)
    }, [bucket?.total_size])

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

                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className="size-14 rounded-2xl bg-linear-to-br from-primary/20 via-primary/10 to-transparent border border-primary/20 flex items-center justify-center">
                                <FolderOpen className="size-7 text-primary" />
                            </div>
                            <div>
                                <h1 className="text-2xl font-semibold tracking-tight">
                                    {bucket.name}
                                </h1>
                                <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                                    <span className="flex items-center gap-1.5">
                                        <Files className="size-4" />
                                        {bucket.total_files} items
                                    </span>
                                    <span className="flex items-center gap-1.5">
                                        <HardDrive className="size-4" />
                                        {totalSize}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 overflow-y-auto w-full">
                <div className="p-8">
                    <div className="mb-6">
                        <h2 className="text-lg font-medium text-muted-foreground">Select Asset Type</h2>
                        <p className="text-sm text-muted-foreground/60 mt-1">
                            Choose a category to browse your assets
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {bucketTypes.map((type) => {
                            const Icon = type.icon
                            const isHovered = hoveredType === type.id
                            const isEmpty = type.count === 0

                            return (
                                <Card
                                    key={type.id}
                                    className={cn(
                                        "relative overflow-hidden cursor-pointer transition-all duration-300 border-muted-foreground/20 group",
                                        isHovered && "shadow-xl border-primary/30",
                                        isEmpty && "opacity-60"
                                    )}
                                    onMouseEnter={() => setHoveredType(type.id)}
                                    onMouseLeave={() => setHoveredType(null)}
                                    onClick={() => navigate(`/data/bucket/${bucketId}/${type.id}`)}
                                >
                                    {/* Gradient Background */}
                                    <div className={cn(
                                        "absolute inset-0 bg-linear-to-br opacity-0 transition-opacity duration-300",
                                        type.gradient,
                                        isHovered && "opacity-100"
                                    )} />

                                    <CardContent className="relative px-6">
                                        <div className="flex items-start justify-between mb-4">
                                            <div className={cn(
                                                "p-3 rounded-xl bg-muted/50 transition-all duration-300",
                                                isHovered && "scale-110 bg-background/50"
                                            )}>
                                                <Icon className={cn("size-8", type.color)} />
                                            </div>
                                            <ArrowRight className={cn(
                                                "size-5 text-muted-foreground/30 transition-all duration-300",
                                                isHovered && "text-primary translate-x-1"
                                            )} />
                                        </div>

                                        <h3 className={cn(
                                            "text-xl font-semibold mb-1 transition-colors",
                                            isHovered && "text-primary"
                                        )}>
                                            {type.name}
                                        </h3>
                                        <p className="text-sm text-muted-foreground mb-4">
                                            {type.description}
                                        </p>

                                        <div className="flex items-center justify-between pt-4 border-t border-muted-foreground/10">
                                            <div className="flex items-center gap-2">
                                                <span className={cn("text-2xl font-bold", type.color)}>
                                                    {type.count}
                                                </span>
                                                <span className="text-sm text-muted-foreground">items</span>
                                            </div>
                                            <span className="text-sm text-muted-foreground font-medium">
                                                {formatBytes(type.sizeInBytes)}
                                            </span>
                                        </div>

                                        {isEmpty && (
                                            <div className="absolute inset-0 flex items-center justify-center bg-background/50 backdrop-blur-[1px]">
                                                <span className="text-sm text-muted-foreground font-medium">
                                                    No items
                                                </span>
                                            </div>
                                        )}
                                    </CardContent>
                                </Card>
                            )
                        })}

                        {bucketTypes.length === 0 && (
                            <Card className="border-dashed border-muted-foreground/20">
                                <CardContent className="py-10 text-center text-sm text-muted-foreground">
                                    This bucket has no allowed types configured.
                                </CardContent>
                            </Card>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}

export default BucketTypes