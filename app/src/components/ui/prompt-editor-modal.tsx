import { useState, useMemo } from 'react'
import { Button } from '@/components/ui/button'
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '@/components/ui/dialog'
import { PromptEditor } from '@/components/ui/prompt-editor'
import {
    Message,
    MessageContent,
    MessageResponse,
} from "@/components/ai-elements/message"
import { ChevronRight, Eye, Edit3, BrainCircuit } from 'lucide-react'

interface PromptEditorModalProps {
    value: string
    onChange: (value: string) => void
}

/**
 * Heuristic to extract text from Plate's JSON structure if needed.
 */
function extractText(value: string): string {
    if (!value) return ''
    try {
        const parsed = JSON.parse(value)
        if (Array.isArray(parsed)) {
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
}

export function PromptEditorModal({ value, onChange }: PromptEditorModalProps) {
    const [open, setOpen] = useState(false)
    const [isEditing, setIsEditing] = useState(false)
    const [tempValue, setTempValue] = useState(value)

    // Ensure tempValue is synced when modal opens
    const handleOpenChange = (isOpen: boolean) => {
        setOpen(isOpen)
        if (isOpen) {
            setTempValue(value)
            setIsEditing(false) // Start in preview mode
        }
    }

    const handleSave = () => {
        onChange(tempValue)
        setOpen(false)
    }

    const handleCancel = () => {
        setTempValue(value)
        setOpen(false)
    }

    const displayValue = useMemo(() => extractText(tempValue), [tempValue])

    return (
        <Dialog open={open} onOpenChange={handleOpenChange}>
            <DialogTrigger asChild>
                <Button variant="outline" className="gap-2">
                    View / Edit
                    <ChevronRight className="size-4" />
                </Button>
            </DialogTrigger>
            <DialogContent className="max-w-[75vw] w-full max-h-[85vh] overflow-hidden flex flex-col p-0 gap-0 bg-card border-none shadow-2xl">
                <DialogHeader className="p-8 pb-4">
                    <div className="flex items-center gap-3 mb-1">
                        <div className="p-2 rounded-lg bg-primary/10">
                            <BrainCircuit className="size-5 text-primary" />
                        </div>
                        <DialogTitle className="text-2xl outline-none">Custom AI Prompt</DialogTitle>
                    </div>
                    <DialogDescription className="text-base text-muted-foreground/80">
                        {isEditing
                            ? "Refine your assistant's behavior using Markdown syntax."
                            : "This is a preview of your current custom research instructions."}
                    </DialogDescription>
                </DialogHeader>

                <div className="flex-1 overflow-y-auto px-8 py-4 bg-muted/5">
                    {isEditing ? (
                        <div className="h-full rounded-2xl border border-border bg-background overflow-hidden p-1 shadow-inner group focus-within:ring-2 focus-within:ring-primary/20 transition-all">
                            <PromptEditor
                                value={tempValue}
                                onChange={(val) => setTempValue(val)}
                                placeholder="Define how the AI should research, analyze, and present findings..."
                                className="bg-transparent border-none focus:ring-0 min-h-[450px]"
                            />
                        </div>
                    ) : (
                        <div className="rounded-2xl border border-border bg-background p-6 shadow-sm">
                            {displayValue ? (
                                <Message from="assistant" className="max-w-none w-full">
                                    <MessageContent className="max-w-none w-full bg-transparent p-0 text-base leading-relaxed">
                                        <MessageResponse>
                                            {displayValue}
                                        </MessageResponse>
                                    </MessageContent>
                                </Message>
                            ) : (
                                <div className="flex flex-col items-center justify-center py-24 text-muted-foreground">
                                    <BrainCircuit className="size-12 mb-4 opacity-20" />
                                    <p className="italic text-lg">No custom prompt instructions defined yet.</p>
                                    <Button
                                        variant="link"
                                        onClick={() => setIsEditing(true)}
                                        className="mt-2 text-primary hover:text-primary/80"
                                    >
                                        Click here to start writing
                                    </Button>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                <div className="flex items-center justify-between gap-3 p-8 pt-4 border-t bg-background/50 backdrop-blur-xl">
                    <Button variant="ghost" onClick={handleCancel} className="text-muted-foreground hover:text-foreground">
                        Close
                    </Button>

                    <div className="flex items-center gap-3">
                        <Button
                            variant="outline"
                            onClick={() => setIsEditing(!isEditing)}
                            className="gap-2 min-w-[120px] border-primary/20 hover:bg-primary/5 hover:text-primary transition-colors"
                        >
                            {isEditing ? (
                                <><Eye className="size-4" /> Preview</>
                            ) : (
                                <><Edit3 className="size-4" /> Edit Code</>
                            )}
                        </Button>

                        <Button
                            onClick={handleSave}
                            className="bg-primary hover:bg-primary/90 text-primary-foreground min-w-[140px] shadow-lg shadow-primary/20"
                        >
                            Save Changes
                        </Button>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    )
}
