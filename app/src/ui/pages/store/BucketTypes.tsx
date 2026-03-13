import { useState, useMemo } from 'react'
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
    HardDrive
} from 'lucide-react'

// Asset type definitions
interface AssetType {
    id: string
    name: string
    description: string
    icon: React.ElementType
    count: number
    size: string
    color: string
    gradient: string
}

// Mock bucket data
const mockBucketData: Record<string, { name: string; types: AssetType[] }> = {
    'bucket-1': {
        name: 'Research Assets',
        types: [
            { id: 'images', name: 'Images', description: 'Photos, screenshots, and graphics', icon: Image, count: 245, size: '890 MB', color: 'text-blue-400', gradient: 'from-blue-500/20 to-blue-600/5' },
            { id: 'videos', name: 'Videos', description: 'Recordings and video content', icon: Video, count: 12, size: '1.2 GB', color: 'text-purple-400', gradient: 'from-purple-500/20 to-purple-600/5' },
            { id: 'files', name: 'Files', description: 'Documents, PDFs, and spreadsheets', icon: FileText, count: 89, size: '156 MB', color: 'text-green-400', gradient: 'from-green-500/20 to-green-600/5' },
            { id: 'audio', name: 'Audio', description: 'Music, recordings, and sound files', icon: Music, count: 5, size: '45 MB', color: 'text-orange-400', gradient: 'from-orange-500/20 to-orange-600/5' },
            { id: 'others', name: 'Others', description: 'Miscellaneous files and data', icon: Files, count: 23, size: '89 MB', color: 'text-pink-400', gradient: 'from-pink-500/20 to-pink-600/5' },
        ]
    },
    'bucket-2': {
        name: 'Product Screenshots',
        types: [
            { id: 'images', name: 'Images', description: 'Photos, screenshots, and graphics', icon: Image, count: 567, size: '1.6 GB', color: 'text-blue-400', gradient: 'from-blue-500/20 to-blue-600/5' },
            { id: 'videos', name: 'Videos', description: 'Recordings and video content', icon: Video, count: 0, size: '0 MB', color: 'text-purple-400', gradient: 'from-purple-500/20 to-purple-600/5' },
            { id: 'files', name: 'Files', description: 'Documents, PDFs, and spreadsheets', icon: FileText, count: 12, size: '24 MB', color: 'text-green-400', gradient: 'from-green-500/20 to-green-600/5' },
            { id: 'audio', name: 'Audio', description: 'Music, recordings, and sound files', icon: Music, count: 0, size: '0 MB', color: 'text-orange-400', gradient: 'from-orange-500/20 to-orange-600/5' },
            { id: 'others', name: 'Others', description: 'Miscellaneous files and data', icon: Files, count: 8, size: '12 MB', color: 'text-pink-400', gradient: 'from-pink-500/20 to-pink-600/5' },
        ]
    },
}

// Default bucket data for unknown IDs
const defaultBucketData = {
    name: 'Unknown Bucket',
    types: [
        { id: 'images', name: 'Images', description: 'Photos, screenshots, and graphics', icon: Image, count: 0, size: '0 MB', color: 'text-blue-400', gradient: 'from-blue-500/20 to-blue-600/5' },
        { id: 'videos', name: 'Videos', description: 'Recordings and video content', icon: Video, count: 0, size: '0 MB', color: 'text-purple-400', gradient: 'from-purple-500/20 to-purple-600/5' },
        { id: 'files', name: 'Files', description: 'Documents, PDFs, and spreadsheets', icon: FileText, count: 0, size: '0 MB', color: 'text-green-400', gradient: 'from-green-500/20 to-green-600/5' },
        { id: 'audio', name: 'Audio', description: 'Music, recordings, and sound files', icon: Music, count: 0, size: '0 MB', color: 'text-orange-400', gradient: 'from-orange-500/20 to-orange-600/5' },
        { id: 'others', name: 'Others', description: 'Miscellaneous files and data', icon: Files, count: 0, size: '0 MB', color: 'text-pink-400', gradient: 'from-pink-500/20 to-pink-600/5' },
    ]
}

const BucketTypes = () => {
    const { bucketId } = useParams()
    const navigate = useNavigate()
    const [hoveredType, setHoveredType] = useState<string | null>(null)

    const bucketData = useMemo(() => {
        return mockBucketData[bucketId || ''] || defaultBucketData
    }, [bucketId])

    const totalItems = useMemo(() => {
        return bucketData.types.reduce((acc, type) => acc + type.count, 0)
    }, [bucketData])

    const totalSize = useMemo(() => {
        // Simplified size calculation - in real app would parse and sum properly
        return '2.4 GB'
    }, [])

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
                                    {bucketData.name}
                                </h1>
                                <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                                    <span className="flex items-center gap-1.5">
                                        <Files className="size-4" />
                                        {totalItems} items
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
                        {bucketData.types.map((type) => {
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
                                    onClick={() => !isEmpty && navigate(`/data/bucket/${bucketId}/${type.id}`)}
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
                                                {type.size}
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
                    </div>
                </div>
            </div>
        </div>
    )
}

export default BucketTypes