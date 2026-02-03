import { useState, useCallback, memo } from 'react'
import { Message, MessageContent, MessageResponse, MessageAction, MessageActions, MessageToolbar } from '@/components/ai-elements/message'
import {
  ChainOfThought,
  ChainOfThoughtContent,
  ChainOfThoughtHeader,
  ChainOfThoughtStep,
} from '@/components/ai-elements/chain-of-thought'
import {
  Attachments,
  Attachment,
  AttachmentPreview,
} from '@/components/ai-elements/attachments'
import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from '@/components/ai-elements/conversation'
import { SearchIcon, CopyIcon, RefreshCcwIcon, Loader2Icon, CheckIcon, Upload, MessageSquare } from 'lucide-react'
import "katex/dist/katex.min.css";
import Composer from '@/components/widgets/Composer'
import { cn } from '@/lib/utils'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useChatSimulator, type ChatMessage } from './useChatSimulator'
import { Shimmer } from '@/components/ai-elements/shimmer'
import { Persona } from '@/components/ai-elements/persona'

// Memoized individual message item to prevent unnecessary re-renders during streaming
const ChatMessageItem = memo(({
  message,
  isLoading,
  isLast,
  handleCopy,
  handleRetry,
  handleExport,
  copyStatus
}: {
  message: ChatMessage,
  isLoading: boolean,
  isLast: boolean,
  handleCopy: (content: string, id: string) => void,
  handleRetry: () => void,
  handleExport: (format: string, id: string) => void,
  copyStatus: 'idle' | 'loading' | 'success'
}) => {
  const isAssistant = message.role === 'assistant'
  const isStreaming = isLast && isLoading && isAssistant

  return (
    <Message
      from={message.role}
      className={cn(
        "animate-in fade-in slide-in-from-bottom-2 duration-300 max-w-full",
        message.role === 'user' ? "pl-12 ml-auto" : ""
      )}
    >
      <MessageContent className={message.role === 'user' ? "shadow-sm text-foreground" : "bg-transparent px-0 py-0 w-full text-justify"}>
        {isAssistant && (message.thinking || (isStreaming && !message.content)) && (
          <div className="bg-accent/50 rounded-2xl mb-4 border border-border/50 overflow-hidden w-full">
            <ChainOfThought
              key={message.content ? 'thinking-folded' : 'thinking-active'}
              className='p-4 pb-0 w-full'
              defaultOpen={!message.content}
            >
              <ChainOfThoughtHeader className='w-full' />
              <ChainOfThoughtContent className='w-full pr-4'>
                <ChainOfThoughtStep
                  icon={SearchIcon}
                  label="Thinking Process"
                  status={isStreaming && !message.content ? "active" : "complete"}
                >
                  <MessageResponse
                    className="text-muted-foreground mt-2 mb-4 w-full"
                    isAnimating={isStreaming && !message.content}
                  >
                    {message.thinking}
                  </MessageResponse>
                </ChainOfThoughtStep>
              </ChainOfThoughtContent>
            </ChainOfThought>
          </div>
        )}

        {isAssistant ? (
          <>
            {message.content ? (
              <MessageResponse
                isAnimating={isStreaming && !!message.content}
                className={cn(isStreaming && "streaming-text-fade")}
              >
                {message.content}
              </MessageResponse>
            ) : (
              isLoading && isLast && !message.thinking && (
                <div className="flex items-center gap-2 mb-4">
                  <Persona state="thinking" className="size-5" variant="glint" />
                  <Shimmer className="text-sm font-medium">Thinking...</Shimmer>
                </div>
              )
            )}
          </>
        ) : (
          <>
            {message.attachments && message.attachments.length > 0 && (
              <div className="mb-3">
                <Attachments variant="grid">
                  {message.attachments.map((attachment) => (
                    <Attachment key={attachment.id} data={attachment}>
                      <AttachmentPreview />
                    </Attachment>
                  ))}
                </Attachments>
              </div>
            )}
            <MessageResponse>
              {message.content}
            </MessageResponse>
          </>
        )}
      </MessageContent>

      {isAssistant ? (
        (!isLoading || !isLast) && (
          <MessageToolbar>
            <MessageActions>
              <MessageAction label="Retry" onClick={handleRetry} tooltip="Regenerate response">
                <RefreshCcwIcon className="size-4" />
              </MessageAction>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <MessageAction label="Export" tooltip="Export response">
                    <Upload className="size-4" />
                  </MessageAction>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => handleExport('docs', message.id)}>Docs</DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleExport('md', message.id)}>MD</DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleExport('pdf', message.id)}>PDF</DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              <MessageAction
                label="Copy"
                onClick={() => handleCopy(message.content, message.id)}
                tooltip="Copy to clipboard"
                disabled={copyStatus === 'loading' || copyStatus === 'success'}
              >
                {copyStatus === 'loading' ? (
                  <Loader2Icon className="size-4 animate-spin" />
                ) : copyStatus === 'success' ? (
                  <CheckIcon className="size-4 text-green-500" />
                ) : (
                  <CopyIcon className="size-4" />
                )}
              </MessageAction>
            </MessageActions>
          </MessageToolbar>
        )
      ) : (
        <MessageToolbar className="justify-end mt-0">
          <MessageActions>
            <MessageAction
              label="Copy"
              onClick={() => handleCopy(message.content, message.id)}
              disabled={copyStatus === 'loading' || copyStatus === 'success'}
            >
              {copyStatus === 'loading' ? (
                <Loader2Icon className="size-4 animate-spin" />
              ) : copyStatus === 'success' ? (
                <CheckIcon className="size-4 text-green-500" />
              ) : (
                <CopyIcon className="size-4" />
              )}
            </MessageAction>
          </MessageActions>
        </MessageToolbar>
      )}
    </Message>
  )
})

ChatMessageItem.displayName = 'ChatMessageItem'

const ChatInterface = () => {
  const { messages, isLoading, sendMessage, stopStreaming } = useChatSimulator()
  const [input, setInput] = useState('')
  const [copyState, setCopyState] = useState<Record<string, 'idle' | 'loading' | 'success'>>({})

  const handleSend = useCallback((value: string, files?: File[]) => {
    sendMessage(value, files)
    setInput('')
  }, [sendMessage])

  const handleCopy = useCallback(async (content: string, messageId: string) => {
    setCopyState(prev => ({ ...prev, [messageId]: 'loading' }))
    try {
      await navigator.clipboard.writeText(content)
      setCopyState(prev => ({ ...prev, [messageId]: 'success' }))
      setTimeout(() => setCopyState(prev => ({ ...prev, [messageId]: 'idle' })), 2000)
    } catch (error) {
      console.error('Failed to copy:', error)
      setCopyState(prev => ({ ...prev, [messageId]: 'idle' }))
    }
  }, [])

  const handleRetry = useCallback(() => console.log('Retrying...'), [])
  const handleExport = useCallback((format: string, id: string) => console.log(`Exporting ${id} as ${format}`), [])

  return (
    <div className="flex flex-col h-full w-full text-foreground animate-in fade-in duration-500 overflow-hidden relative">
      <header className="absolute top-4 left-6 z-30 pointer-events-none">
        <div className="pointer-events-auto backdrop-blur-xl bg-background/80 border border-border/50 rounded-2xl px-6 py-3 shadow-lg shadow-black/5 animate-in fade-in slide-in-from-top-2 duration-500 flex items-center gap-3">
          {isLoading && (
            <Persona
              state={messages[messages.length - 1]?.content ? 'speaking' : 'thinking'}
              className="size-5"
              variant="glint"
            />
          )}
          <div className="flex flex-col">
            <h2 className="text-sm font-semibold bg-linear-to-r from-foreground to-foreground/70 bg-clip-text text-transparent leading-none">
              Cryptocurrency Market Analysis
            </h2>
            <p className="text-[10px] text-muted-foreground/60 mt-1 font-medium">
              My Workspace • Jan 31, 2026
            </p>
          </div>
        </div>
      </header>

      <Conversation className="flex-1 w-full">
        <ConversationContent className="max-w-4xl mx-auto pt-20 pb-32">
          {messages.length === 0 ? (
            <ConversationEmptyState
              icon={<MessageSquare className="size-12 text-primary/50" />}
              title="Deep Researcher"
              description="Start a conversation to begin your research journey."
            />
          ) : (
            messages.map((message, index) => (
              <ChatMessageItem
                key={message.id}
                message={message}
                isLoading={isLoading}
                isLast={index === messages.length - 1}
                handleCopy={handleCopy}
                handleRetry={handleRetry}
                handleExport={handleExport}
                copyStatus={copyState[message.id] || 'idle'}
              />
            ))
          )}
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>

      <footer className="shrink-0 w-full pb-4 pt-2 px-4 z-20 border-t border-border/10 mt-auto">
        <div className="max-w-4xl mx-auto">
          <Composer
            value={input}
            onChange={setInput}
            onSend={handleSend}
            onStop={stopStreaming}
            isLoading={isLoading}
            placeholder="Ask anything..."
          />
          <div className="text-center mt-2">
            <p className="text-[10px] text-muted-foreground/50 font-medium">
              AI can make mistakes. Please verify important information.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default ChatInterface
