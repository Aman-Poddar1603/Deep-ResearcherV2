import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import {
    Bold,
    Italic,
    Underline,
    Code,
    Strikethrough,
    Heading1,
    Heading2,
    Heading3,
    List,
    ListOrdered,
    Quote,
    Undo,
    Redo
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface PromptEditorProps {
    value: string
    onChange: (value: string) => void
    placeholder?: string
    className?: string
}

export function PromptEditor({ value, onChange, placeholder, className }: PromptEditorProps) {
    const editorRef = useRef<HTMLDivElement>(null)
    const [selectedFormat, setSelectedFormat] = useState<Set<string>>(new Set())

    useEffect(() => {
        if (editorRef.current && editorRef.current.innerHTML !== value) {
            editorRef.current.innerHTML = value || ''
        }
    }, [value])

    const handleInput = () => {
        if (editorRef.current) {
            onChange(editorRef.current.innerHTML)
        }
        updateFormatState()
    }

    const updateFormatState = () => {
        const formats = new Set<string>()
        if (document.queryCommandState('bold')) formats.add('bold')
        if (document.queryCommandState('italic')) formats.add('italic')
        if (document.queryCommandState('underline')) formats.add('underline')
        if (document.queryCommandState('strikethrough')) formats.add('strikethrough')
        setSelectedFormat(formats)
    }

    const execCommand = (command: string, value?: string) => {
        document.execCommand(command, false, value)
        editorRef.current?.focus()
        updateFormatState()
    }

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.ctrlKey || e.metaKey) {
            switch (e.key.toLowerCase()) {
                case 'b':
                    e.preventDefault()
                    execCommand('bold')
                    break
                case 'i':
                    e.preventDefault()
                    execCommand('italic')
                    break
                case 'u':
                    e.preventDefault()
                    execCommand('underline')
                    break
            }
        }
    }

    return (
        <div className={cn('rounded-md border border-input bg-background', className)}>
            {/* Fixed Toolbar */}
            <div className="flex items-center gap-1 border-b border-border p-2 bg-muted/30 flex-wrap">
                {/* Text formatting */}
                <div className="flex gap-1">
                    <Button
                        type="button"
                        variant={selectedFormat.has('bold') ? 'default' : 'ghost'}
                        size="sm"
                        onClick={() => execCommand('bold')}
                        className="size-8 p-0"
                        title="Bold (Ctrl+B)"
                    >
                        <Bold className="size-4" />
                    </Button>
                    <Button
                        type="button"
                        variant={selectedFormat.has('italic') ? 'default' : 'ghost'}
                        size="sm"
                        onClick={() => execCommand('italic')}
                        className="size-8 p-0"
                        title="Italic (Ctrl+I)"
                    >
                        <Italic className="size-4" />
                    </Button>
                    <Button
                        type="button"
                        variant={selectedFormat.has('underline') ? 'default' : 'ghost'}
                        size="sm"
                        onClick={() => execCommand('underline')}
                        className="size-8 p-0"
                        title="Underline (Ctrl+U)"
                    >
                        <Underline className="size-4" />
                    </Button>
                    <Button
                        type="button"
                        variant={selectedFormat.has('strikethrough') ? 'default' : 'ghost'}
                        size="sm"
                        onClick={() => execCommand('strikethrough')}
                        className="size-8 p-0"
                        title="Strikethrough"
                    >
                        <Strikethrough className="size-4" />
                    </Button>
                </div>

                <Separator orientation="vertical" className="h-6 mx-1" />

                {/* Headings */}
                <div className="flex gap-1">
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => execCommand('formatBlock', '<h1>')}
                        className="size-8 p-0"
                        title="Heading 1"
                    >
                        <Heading1 className="size-4" />
                    </Button>
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => execCommand('formatBlock', '<h2>')}
                        className="size-8 p-0"
                        title="Heading 2"
                    >
                        <Heading2 className="size-4" />
                    </Button>
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => execCommand('formatBlock', '<h3>')}
                        className="size-8 p-0"
                        title="Heading 3"
                    >
                        <Heading3 className="size-4" />
                    </Button>
                </div>

                <Separator orientation="vertical" className="h-6 mx-1" />

                {/* Lists */}
                <div className="flex gap-1">
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => execCommand('insertUnorderedList')}
                        className="size-8 p-0"
                        title="Bullet List"
                    >
                        <List className="size-4" />
                    </Button>
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => execCommand('insertOrderedList')}
                        className="size-8 p-0"
                        title="Numbered List"
                    >
                        <ListOrdered className="size-4" />
                    </Button>
                </div>

                <Separator orientation="vertical" className="h-6 mx-1" />

                {/* Block formatting */}
                <div className="flex gap-1">
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => execCommand('formatBlock', '<blockquote>')}
                        className="size-8 p-0"
                        title="Quote"
                    >
                        <Quote className="size-4" />
                    </Button>
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => execCommand('formatBlock', '<pre>')}
                        className="size-8 p-0"
                        title="Code Block"
                    >
                        <Code className="size-4" />
                    </Button>
                </div>

                <Separator orientation="vertical" className="h-6 mx-1" />

                {/* Undo/Redo */}
                <div className="flex gap-1">
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => execCommand('undo')}
                        className="size-8 p-0"
                        title="Undo (Ctrl+Z)"
                    >
                        <Undo className="size-4" />
                    </Button>
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => execCommand('redo')}
                        className="size-8 p-0"
                        title="Redo (Ctrl+Y)"
                    >
                        <Redo className="size-4" />
                    </Button>
                </div>
            </div>

            {/* Editor */}
            <div
                ref={editorRef}
                contentEditable
                onInput={handleInput}
                onKeyDown={handleKeyDown}
                onMouseUp={updateFormatState}
                onKeyUp={updateFormatState}
                className="min-h-[300px] px-3 py-2 text-sm outline-none focus:outline-none overflow-y-auto max-h-[60vh]"
                data-placeholder={placeholder}
                suppressContentEditableWarning
            />

            <style>{`
                [contenteditable][data-placeholder]:empty:before {
                    content: attr(data-placeholder);
                    color: hsl(var(--muted-foreground));
                    opacity: 0.5;
                }
                [contenteditable]:focus {
                    outline: none;
                }
                [contenteditable] h1 {
                    font-size: 2em;
                    font-weight: bold;
                    margin: 0.67em 0;
                }
                [contenteditable] h2 {
                    font-size: 1.5em;
                    font-weight: bold;
                    margin: 0.75em 0;
                }
                [contenteditable] h3 {
                    font-size: 1.17em;
                    font-weight: bold;
                    margin: 0.83em 0;
                }
                [contenteditable] blockquote {
                    border-left: 4px solid hsl(var(--border));
                    padding-left: 1em;
                    margin: 1em 0;
                    color: hsl(var(--muted-foreground));
                }
                [contenteditable] pre {
                    background: hsl(var(--muted));
                    padding: 0.5em;
                    border-radius: 4px;
                    font-family: monospace;
                    overflow-x: auto;
                }
                [contenteditable] ul, [contenteditable] ol {
                    margin: 0.5em 0;
                    padding-left: 2em;
                }
            `}</style>
        </div>
    )
}
