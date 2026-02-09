import React, { useState, useRef, useEffect } from 'react'
import { Paperclip, ArrowUp, Square, X, FileText, Image as ImageIcon, File, Library } from 'lucide-react'
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface AttachedFile {
    id: string
    file: File
    preview?: string
}

interface ComposerProps {
    value?: string
    onChange?: (value: string) => void
    onSend?: (value: string, files?: File[]) => void
    onStop?: () => void
    isLoading?: boolean
    placeholder?: string
}

const Composer = ({ value, onChange, onSend, onStop, isLoading, placeholder }: ComposerProps) => {
    const [internalMessage, setInternalMessage] = useState('')
    const [isFocused, setIsFocused] = useState(false)
    const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([])
    const textareaRef = useRef<HTMLTextAreaElement>(null)
    const fileInputRef = useRef<HTMLInputElement>(null)

    const isControlled = value !== undefined
    const message = isControlled ? value : internalMessage

    const handleChange = (newValue: string) => {
        if (isControlled) {
            onChange?.(newValue)
        } else {
            setInternalMessage(newValue)
        }
    }

    // Handle file selection
    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(e.target.files || [])

        files.forEach(file => {
            const newFile: AttachedFile = {
                id: `${Date.now()}-${Math.random()}`,
                file,
            }

            // Generate preview for images
            if (file.type.startsWith('image/')) {
                const reader = new FileReader()
                reader.onload = (e) => {
                    setAttachedFiles(prev => prev.map(f =>
                        f.id === newFile.id ? { ...f, preview: e.target?.result as string } : f
                    ))
                }
                reader.readAsDataURL(file)
            }

            setAttachedFiles(prev => [...prev, newFile])
        })

        // Reset input
        if (fileInputRef.current) {
            fileInputRef.current.value = ''
        }
    }

    // Remove file
    const handleRemoveFile = (fileId: string) => {
        setAttachedFiles(prev => prev.filter(f => f.id !== fileId))
    }

    // Get file icon
    const getFileIcon = (file: File) => {
        if (file.type.startsWith('image/')) return ImageIcon
        if (file.type.includes('pdf')) return FileText
        return File
    }

    // Auto-resize textarea logic
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'
            textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
        }
    }, [message])

    // Global keyboard shortcuts
    useEffect(() => {
        const handleGlobalKeyDown = (e: KeyboardEvent) => {
            // Check for "/" key
            // Don't trigger if user is already typing in an input, textarea, or contentEditable element
            const target = e.target as HTMLElement
            const isTyping =
                target.tagName === 'INPUT' ||
                target.tagName === 'TEXTAREA' ||
                target.isContentEditable ||
                target.closest('[contenteditable="true"]') !== null

            if (e.key === '/' && !isTyping) {
                e.preventDefault()
                textareaRef.current?.focus()
            }

            // Check for Ctrl+K or Cmd+K
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
                e.preventDefault()
                textareaRef.current?.focus()
            }
        }

        window.addEventListener('keydown', handleGlobalKeyDown)
        return () => window.removeEventListener('keydown', handleGlobalKeyDown)
    }, [])

    const handleSend = () => {
        if ((!message.trim() && attachedFiles.length === 0) || isLoading) return

        const files = attachedFiles.map(af => af.file)

        if (onSend) {
            onSend(message, files.length > 0 ? files : undefined)
        } else {
            console.log('Sending message:', message, 'with files:', files)
        }

        if (!isControlled) {
            setInternalMessage('')
        }

        // Clear attached files
        setAttachedFiles([])
    }

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSend()
        }

        if (e.key === 'Escape') {
            textareaRef.current?.blur()
        }
    }

    return (
        <div className="w-full max-w-4xl mx-auto px-4 animate-in fade-in slide-in-from-bottom-4 duration-1000 fill-mode-both" style={{ animationDelay: '900ms' }}>
            {/* Hidden file input */}
            <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={handleFileSelect}
                className="hidden"
                accept="image/*,.pdf,.doc,.docx,.txt"
            />

            <div className={cn(
                "relative group transition-all duration-500 rounded-[30px]",
                isFocused ? "ring-4 ring-primary/10" : ""
            )}>
                <div
                    onClick={() => textareaRef.current?.focus()}
                    className={cn(
                        "relative bg-card/60 backdrop-blur-2xl border border-border shadow-[0_8px_32px_rgba(0,0,0,0.2)] dark:shadow-[0_8px_32px_rgba(0,0,0,0.5)] rounded-[30px] p-2 pr-3 transition-all duration-300 cursor-text",
                        isFocused ? "border-primary/50 bg-card/80" : "hover:border-border/80 hover:bg-card/70"
                    )}
                >
                    {/* File Previews */}
                    {attachedFiles.length > 0 && (
                        <div className="px-3 pt-2 pb-1 flex flex-wrap gap-2">
                            {attachedFiles.map((attachedFile) => {
                                const FileIcon = getFileIcon(attachedFile.file)
                                return (
                                    <div
                                        key={attachedFile.id}
                                        className="group/file relative flex items-center gap-2 bg-accent/50 hover:bg-accent/70 border border-border/50 rounded-lg px-3 py-2 pr-8 transition-all duration-200"
                                    >
                                        {attachedFile.preview ? (
                                            <img
                                                src={attachedFile.preview}
                                                alt={attachedFile.file.name}
                                                className="w-8 h-8 rounded object-cover"
                                            />
                                        ) : (
                                            <FileIcon className="w-4 h-4 text-muted-foreground" />
                                        )}
                                        <div className="flex flex-col min-w-0">
                                            <span className="text-xs font-medium truncate max-w-[150px]">
                                                {attachedFile.file.name}
                                            </span>
                                            <span className="text-[10px] text-muted-foreground">
                                                {(attachedFile.file.size / 1024).toFixed(1)} KB
                                            </span>
                                        </div>
                                        <Button
                                            size="icon"
                                            variant="ghost"
                                            onClick={(e) => {
                                                e.stopPropagation()
                                                handleRemoveFile(attachedFile.id)
                                            }}
                                            className="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6 rounded-full hover:bg-destructive/20 hover:text-destructive opacity-0 group-hover/file:opacity-100 transition-opacity"
                                        >
                                            <X className="h-3 w-3" />
                                        </Button>
                                    </div>
                                )
                            })}
                        </div>
                    )}

                    <div className="px-3 pt-2">
                        <textarea
                            ref={textareaRef}
                            value={message}
                            onChange={(e) => handleChange(e.target.value)}
                            onKeyDown={handleKeyDown}
                            onFocus={() => setIsFocused(true)}
                            onBlur={() => setIsFocused(false)}
                            placeholder={placeholder || "Ask Deep Researcher..."}
                            rows={1}
                            className="w-full bg-transparent border-none resize-none outline-none text-lg leading-relaxed text-foreground placeholder:text-muted-foreground min-h-[44px] max-h-[350px] py-0 px-0"
                            disabled={isLoading}
                        />
                    </div>

                    {/* Bottom Action Bar */}
                    <div className="flex items-center justify-between mt-1 px-1 pb-1">
                        <div className="flex items-center gap-1">
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={(e) => {
                                    e.stopPropagation()
                                    fileInputRef.current?.click()
                                }}
                                className="h-8 gap-1.5 rounded-full hover:bg-accent/50 text-muted-foreground hover:text-foreground px-3 transition-all duration-200"
                            >
                                <Paperclip className="h-3.5 w-3.5" />
                                <span className="text-[11px] font-medium">Attach</span>
                            </Button>

                            <div className="flex items-center gap-2 ml-1 border-l border-border/30 pl-3">
                                <span className="text-[10px] uppercase tracking-wider font-bold text-muted-foreground/40 select-none">My Workspace</span>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-8 gap-1.5 rounded-full hover:bg-background/50 text-muted-foreground hover:text-foreground px-3 transition-all duration-200 border border-border/50 shadow-sm"
                                >
                                    <Library className="h-3.5 w-3.5" />
                                    <span className="text-[11px] font-medium">Attach Research Context</span>
                                </Button>
                            </div>
                        </div>

                        <div className="flex items-center gap-1">
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 rounded-full text-muted-foreground hover:text-foreground text-[11px] font-bold px-3 transition-all duration-200"
                            >
                                Plan
                            </Button>

                            <Button
                                size="icon"
                                onClick={isLoading && onStop ? onStop : handleSend}
                                className={cn(
                                    "h-8 w-8 rounded-full ml-1 transition-all duration-500",
                                    ((message.trim() || attachedFiles.length > 0) && !isLoading) || (isLoading && onStop)
                                        ? "bg-primary text-primary-foreground hover:opacity-90 shadow-lg scale-100"
                                        : "bg-muted text-muted-foreground cursor-not-allowed scale-95 opacity-50"
                                )}
                                disabled={(!message.trim() && attachedFiles.length === 0 && !isLoading) || (isLoading && !onStop)}
                            >
                                {isLoading && onStop ? (
                                    <Square className="h-3.5 w-3.5 fill-current" />
                                ) : (
                                    <ArrowUp className="h-4.5 w-4.5" />
                                )}
                            </Button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default Composer