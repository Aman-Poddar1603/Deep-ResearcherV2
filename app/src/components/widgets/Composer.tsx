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

const Composer = () => {
    const [message, setMessage] = useState('')
    const textareaRef = useRef<HTMLTextAreaElement>(null)

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
    }

    return (
        <div className="w-full max-w-4xl mx-auto px-4 animate-in fade-in slide-in-from-bottom-4 duration-1000 fill-mode-both" style={{ animationDelay: '900ms' }}>
            <div className="relative group transition-all duration-300">
                <div className="relative bg-[#1a1a1a] border border-white/10 shadow-[0_8px_32px_rgba(0,0,0,0.4)] rounded-[30px] p-2 pr-3 transition-all duration-300">
                    <div className="px-3 pt-2">
                        <textarea
                            ref={textareaRef}
                            value={message}
                            onChange={(e) => setMessage(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Ask Deep Researcher..."
                            rows={1}
                            className="w-full bg-transparent border-none resize-none outline-none text-lg leading-relaxed text-white placeholder:text-zinc-500 min-h-[44px] max-h-[350px] py-0 px-0"
                        />
                    </div>

                    {/* Bottom Action Bar */}
                    <div className="flex items-center justify-between mt-1 px-1 pb-1">
                        <div className="flex items-center gap-1">
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 rounded-full hover:bg-white/5 text-zinc-500 hover:text-white transition-colors"
                            >
                                <Plus className="h-4 w-4" />
                            </Button>

                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 gap-1.5 rounded-full hover:bg-white/5 text-zinc-500 hover:text-white px-3 transition-colors"
                            >
                                <Paperclip className="h-3.5 w-3.5" />
                                <span className="text-[11px] font-medium">Attach</span>
                            </Button>

                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-8 gap-1 rounded-full hover:bg-white/5 text-zinc-500 hover:text-white px-3 transition-colors"
                                    >
                                        <Palette className="h-3.5 w-3.5" />
                                        <span className="text-[11px] font-medium">Theme</span>
                                        <ChevronDown className="h-3 w-3 opacity-30" />
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="start" className="bg-[#222] border-white/5 text-zinc-400">
                                    <DropdownMenuItem className="focus:bg-white/5 cursor-pointer">Deep Dark</DropdownMenuItem>
                                    <DropdownMenuItem className="focus:bg-white/5 cursor-pointer">Glass Blur</DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        </div>

                        <div className="flex items-center gap-1">
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 rounded-full text-zinc-500 hover:text-white text-[11px] font-bold px-3 transition-colors"
                            >
                                Plan
                            </Button>

                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 rounded-full text-zinc-500 hover:text-white transition-colors"
                            >
                                <Mic className="h-4 w-4" />
                            </Button>

                            <Button
                                size="icon"
                                className={cn(
                                    "h-8 w-8 rounded-full ml-1 transition-all duration-300",
                                    message.trim()
                                        ? "bg-white text-black hover:bg-zinc-200 shadow-[0_4px_12px_rgba(255,255,255,0.2)]"
                                        : "bg-white/5 text-zinc-600 cursor-not-allowed"
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