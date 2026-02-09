import { useState } from 'react'
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
import { ChevronRight } from 'lucide-react'

interface PromptEditorModalProps {
    value: string
    onChange: (value: string) => void
}

export function PromptEditorModal({ value, onChange }: PromptEditorModalProps) {
    const [open, setOpen] = useState(false)
    const [tempValue, setTempValue] = useState(value)

    const handleSave = () => {
        onChange(tempValue)
        setOpen(false)
    }

    const handleCancel = () => {
        setTempValue(value)
        setOpen(false)
    }

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button variant="outline" className="gap-2">
                    View / Edit
                    <ChevronRight className="size-4" />
                </Button>
            </DialogTrigger>
            <DialogContent className="max-w-[75vw] max-h-[80vh] overflow-hidden flex flex-col">
                <DialogHeader>
                    <DialogTitle>Custom AI Prompt</DialogTitle>
                    <DialogDescription>
                        Define custom instructions for the AI assistant. Use rich text formatting to structure your prompt.
                    </DialogDescription>
                </DialogHeader>
                <div className="flex-1 overflow-y-auto py-4">
                    <PromptEditor
                        value={tempValue}
                        onChange={setTempValue}
                        placeholder="e.g., Always provide citations in APA format, focus on peer-reviewed sources..."
                        className="min-h-[300px]"
                    />
                </div>
                <div className="flex justify-end gap-2 pt-4 border-t">
                    <Button variant="outline" onClick={handleCancel}>
                        Cancel
                    </Button>
                    <Button onClick={handleSave}>
                        Save Changes
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    )
}
