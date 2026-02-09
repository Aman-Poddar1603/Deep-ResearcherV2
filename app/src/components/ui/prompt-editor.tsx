import * as React from 'react'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'

interface PromptEditorProps {
    value: string
    onChange: (value: string) => void
    placeholder?: string
    className?: string
}

/**
 * A simplified Prompt Editor using a standard Textarea.
 * Replaces the heavy Plate.js implementation for better performance.
 */
export function PromptEditor({ value, onChange, placeholder, className }: PromptEditorProps) {
    // If the value is a JSON string (from previous Plate implementation), 
    // we try to extract the text content.
    const displayValue = React.useMemo(() => {
        if (!value) return ''
        try {
            const parsed = JSON.parse(value)
            if (Array.isArray(parsed)) {
                // Heuristic to extract text from Plate's JSON structure
                return (parsed as { type?: string; children?: { text?: string }[] }[])
                    .map((node) => {
                        if (node.children) {
                            return node.children.map((child) => child.text || '').join('')
                        }
                        return ''
                    })
                    .join('\n')
            }
        } catch {
            // It's already plain text
        }
        return value
    }, [value])

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        onChange(e.target.value)
    }

    return (
        <div className={cn("w-full relative group", className)}>
            <Textarea
                value={displayValue}
                onChange={handleChange}
                placeholder={placeholder}
                className={cn(
                    "min-h-[300px] w-full bg-background backdrop-blur-sm border-border/50",
                    "focus:border-primary/50 focus:ring-primary/20 transition-all duration-200",
                    "resize-y leading-relaxed text-sm p-4 rounded-xl",
                    className
                )}
            />
        </div>
    )
}
