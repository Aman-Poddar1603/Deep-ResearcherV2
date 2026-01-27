import React, { useState, useRef, useEffect } from 'react'
import { Plus, Paperclip, Palette, ChevronDown, Mic, ArrowUp } from 'lucide-react'
import { Button } from "@/components/ui/button"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn } from "@/lib/utils"
import { useTheme } from "@/ui/components/theme-provider"

const Composer = () => {
    const [message, setMessage] = useState('')
    const [isFocused, setIsFocused] = useState(false)
    const textareaRef = useRef<HTMLTextAreaElement>(null)
    const { theme, setTheme, availableThemes } = useTheme()

    // Auto-resize textarea logic
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'
            textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
        }
    }, [message])

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            console.log('Sending message:', message)
            setMessage('')
        }

        if (e.key === 'Escape') {
            textareaRef.current?.blur()
        }
    }

    return (
        <div className="w-full max-w-4xl mx-auto px-4 animate-in fade-in slide-in-from-bottom-4 duration-1000 fill-mode-both" style={{ animationDelay: '900ms' }}>
            <div className={cn(
                "relative group transition-all duration-500 rounded-[30px]",
                isFocused ? "ring-4 ring-primary/10 scale-[1.01]" : ""
            )}>
                <div
                    onClick={() => textareaRef.current?.focus()}
                    className={cn(
                        "relative bg-card/60 backdrop-blur-2xl border border-border shadow-[0_8px_32px_rgba(0,0,0,0.2)] dark:shadow-[0_8px_32px_rgba(0,0,0,0.5)] rounded-[30px] p-2 pr-3 transition-all duration-300 cursor-text",
                        isFocused ? "border-primary/50 bg-card/80" : "hover:border-border/80 hover:bg-card/70"
                    )}
                >
                    <div className="px-3 pt-2">
                        <textarea
                            ref={textareaRef}
                            value={message}
                            onChange={(e) => setMessage(e.target.value)}
                            onKeyDown={handleKeyDown}
                            onFocus={() => setIsFocused(true)}
                            onBlur={() => setIsFocused(false)}
                            placeholder="Ask Deep Researcher..."
                            rows={1}
                            className="w-full bg-transparent border-none resize-none outline-none text-lg leading-relaxed text-foreground placeholder:text-muted-foreground min-h-[44px] max-h-[350px] py-0 px-0"
                        />
                    </div>

                    {/* Bottom Action Bar */}
                    <div className="flex items-center justify-between mt-1 px-1 pb-1">
                        <div className="flex items-center gap-1">
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 rounded-full hover:bg-accent/50 text-muted-foreground hover:text-foreground transition-all duration-200"
                            >
                                <Plus className="h-4 w-4" />
                            </Button>

                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 gap-1.5 rounded-full hover:bg-accent/50 text-muted-foreground hover:text-foreground px-3 transition-all duration-200"
                            >
                                <Paperclip className="h-3.5 w-3.5" />
                                <span className="text-[11px] font-medium">Attach</span>
                            </Button>

                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-8 gap-1 rounded-full hover:bg-accent/50 text-muted-foreground hover:text-foreground px-3 transition-all duration-200"
                                    >
                                        <Palette className="h-3.5 w-3.5" />
                                        <span className="text-[11px] font-medium capitalize">{theme}</span>
                                        <ChevronDown className="h-3 w-3 opacity-30" />
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="start" className="max-h-80 overflow-y-auto bg-card border-border">
                                    {availableThemes.map((t) => (
                                        <DropdownMenuItem
                                            key={t}
                                            onClick={() => setTheme(t)}
                                            className={cn(
                                                "capitalize cursor-pointer",
                                                theme === t ? "bg-accent text-accent-foreground" : "text-muted-foreground"
                                            )}
                                        >
                                            {t}
                                        </DropdownMenuItem>
                                    ))}
                                </DropdownMenuContent>
                            </DropdownMenu>
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
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 rounded-full text-muted-foreground hover:text-foreground transition-all duration-200"
                            >
                                <Mic className="h-4 w-4" />
                            </Button>

                            <Button
                                size="icon"
                                className={cn(
                                    "h-8 w-8 rounded-full ml-1 transition-all duration-500",
                                    message.trim()
                                        ? "bg-primary text-primary-foreground hover:opacity-90 shadow-lg scale-100"
                                        : "bg-muted text-muted-foreground cursor-not-allowed scale-95 opacity-50"
                                )}
                                disabled={!message.trim()}
                            >
                                <ArrowUp className="h-4.5 w-4.5" />
                            </Button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default Composer