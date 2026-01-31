import { useState, useEffect, useRef } from 'react'
import { Message, MessageContent, MessageResponse, MessageAction, MessageActions, MessageToolbar } from '@/components/ai-elements/message'
import {
  ChainOfThought,
  ChainOfThoughtContent,
  ChainOfThoughtHeader,
  ChainOfThoughtSearchResult,
  ChainOfThoughtSearchResults,
  ChainOfThoughtStep,
} from '@/components/ai-elements/chain-of-thought'
import {
  Attachments,
  Attachment,
  AttachmentPreview,
  type AttachmentData,
} from '@/components/ai-elements/attachments'
import { SearchIcon, CopyIcon, RefreshCcwIcon, Loader2Icon, CheckIcon, Upload } from 'lucide-react'
import "katex/dist/katex.min.css";
import { nanoid } from 'nanoid'

// Define a local type that matches expectations for this component's text-based logic
interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  attachments?: AttachmentData[]
}
import Composer from '@/components/widgets/Composer'
import { cn } from '@/lib/utils'
import { FileText } from 'lucide-react'
import { Separator } from '@/components/ui/separator'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

// Dummy markdown content for testing  
const DUMMY_RESPONSE = `
| ID | Ticker | Price (USD) | 24h Change | Momentum Formula | Volatility Index | $$\\alpha$$ (Alpha) | $$\\beta$$ (Beta) | $$\\gamma$$ (Gamma) | $$\\delta$$ (Delta) | $$\\theta$$ (Theta) | Market Cap | Volume (24h) | Hash | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **001** | \`BTC-X\` | **$94,320.50** | 🟢 +2.4% | $$P = P_0 e^{rt}$$ | High | $$\\alpha > 0.5$$ | $$\\beta \\approx 1.2$$ | $$\\gamma = \\frac{\\partial^2 V}{\\partial S^2}$$ | $$\\delta = 0.45$$ | $$\\theta = -0.05$$ | $1.8T | 45B | \`0x4d2...\` | Primary reserve asset. |
| **002** | \`ETH-Q\` | **$4,102.10** | 🔴 -1.2% | $$v = \\frac{d}{t}$$ | Medium | $$\\alpha = 0.1$$ | $$\\beta = 0.9$$ | $$\\gamma \\to 0$$ | $$\\delta = 0.60$$ | $$\\theta = -0.12$$ | $450B | 12B | \`0x9a1...\` | Smart contract layer. |
`;

const ChatInterface = () => {
  // Mimic useChat state for client-side demo
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [copyState, setCopyState] = useState<Record<string, 'idle' | 'loading' | 'success'>>({})

  // Refs for auto-scrolling and stopping stream
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const stopStreamingRef = useRef(false)

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'auto' })
    }
  }

  // Only scroll to bottom when messages count changes or significant events happen
  useEffect(() => {
    scrollToBottom()
  }, [messages.length, isLoading])

  const simulateResponse = async () => {
    stopStreamingRef.current = false
    setIsLoading(true)

    // Add minimal assistant message placeholder
    const assistantMessageId = Date.now().toString() + '-ai'
    setMessages(prev => [...prev, {
      id: assistantMessageId,
      role: 'assistant',
      content: ''
    }])

    // Simulate streaming "word by word"
    // Split by spaces/newlines but keep delimiters to preserve formatting
    const words = DUMMY_RESPONSE.split(/(\s+)/)
    let currentText = ''

    for (let i = 0; i < words.length; i++) {
      if (stopStreamingRef.current) break
      await new Promise(resolve => setTimeout(resolve, 15 + Math.random() * 30)) // Typing speed
      currentText += words[i]

      // Update the last message
      setMessages(prev => prev.map(msg =>
        msg.id === assistantMessageId
          ? { ...msg, content: currentText }
          : msg
      ))
    }

    setIsLoading(false)
  }

  const handleSend = (value: string, files?: File[]) => {
    if (!value.trim() && (!files || files.length === 0)) return

    // Convert files to AttachmentData format
    const attachments: AttachmentData[] | undefined = files?.map(file => ({
      id: nanoid(),
      type: 'file' as const,
      url: URL.createObjectURL(file),
      mediaType: file.type,
      filename: file.name,
    }))

    // Add user message
    const userMessage: ChatMessage = {
      id: Date.now().toString() + '-user',
      role: 'user',
      content: value,
      attachments,
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')

    // Trigger dummy response
    simulateResponse()
  }

  const handleStop = () => {
    stopStreamingRef.current = true
    setIsLoading(false)
  }

  const handleCopy = async (content: string, messageId: string) => {
    setCopyState(prev => ({ ...prev, [messageId]: 'loading' }))

    try {
      await navigator.clipboard.writeText(content)
      setCopyState(prev => ({ ...prev, [messageId]: 'success' }))

      // Reset to idle after 2 seconds
      setTimeout(() => {
        setCopyState(prev => ({ ...prev, [messageId]: 'idle' }))
      }, 2000)
    } catch (error) {
      console.error('Failed to copy:', error)
      setCopyState(prev => ({ ...prev, [messageId]: 'idle' }))
    }
  }

  const handleRetry = () => {
    // TODO: Implement retry logic
    console.log('Retrying...')
  }

  const handleExport = (format: 'docs' | 'md' | 'pdf', messageId: string) => {
    // TODO: Implement export logic
    console.log(`Exporting message ${messageId} as ${format}`)
  }

  return (
    <div className="flex flex-col h-full w-full text-foreground animate-in fade-in duration-500 overflow-hidden relative">
      {/* 1. Header Area - Fixed Height */}
      <header className="absolute top-4 right-6 z-30 pointer-events-none">
        <div className="pointer-events-auto backdrop-blur-xl bg-background/80 border border-border/50 rounded-2xl px-6 py-3 shadow-lg shadow-black/5 animate-in fade-in slide-in-from-top-2 duration-500">
          <h2 className="text-sm font-semibold bg-linear-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
            Cryptocurrency Market Analysis
          </h2>
        </div>
      </header>

      {/* 2. Scrollable Messages Area - Takes remaining space */}
      <main className="flex-1 min-h-0 w-full overflow-y-auto overflow-x-hidden">
        <div className="max-w-4xl mx-auto px-4 md:px-8 py-4 pt-24 space-y-8">
          {messages.length === 0 ? (
            // Empty State
            <div className="flex flex-col items-center justify-center h-[50vh] text-center space-y-4 opacity-50">
              <div className="p-4 rounded-3xl bg-primary/5">
                <FileText className="w-12 h-12 text-primary/50" />
              </div>
              <div>
                <h3 className="text-lg font-semibold">No messages yet</h3>
                <p className="text-sm text-muted-foreground">Start a conversation with Deep Researcher</p>
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <Message
                key={message.id}
                from={message.role}
                className={cn(
                  "animate-in fade-in slide-in-from-bottom-2 duration-300 max-w-full",
                  message.role === 'user' ? "pl-12" : ""
                )}
              >
                <MessageContent className={message.role === 'user' ? "shadow-sm text-foreground" : "bg-transparent px-0 py-0 w-full text-justify"}>
                  {message.role === 'assistant' && (
                    <div className="w-fit bg-accent rounded-2xl">
                      <ChainOfThought className='p-4 pb-0' defaultOpen>
                        <ChainOfThoughtHeader />
                        <ChainOfThoughtContent className='mb-4'>
                          <ChainOfThoughtStep
                            icon={SearchIcon}
                            label="Searching for relevant market data"
                            status="complete"
                          >
                            <ChainOfThoughtSearchResults>
                              {[
                                "https://www.coinmarketcap.com",
                                "https://www.coingecko.com",
                                "https://www.blockchain.com",
                              ].map((website) => (
                                <ChainOfThoughtSearchResult key={website}>
                                  {new URL(website).hostname}
                                </ChainOfThoughtSearchResult>
                              ))}
                            </ChainOfThoughtSearchResults>
                          </ChainOfThoughtStep>

                          <ChainOfThoughtStep
                            label="Analyzing cryptocurrency price trends and volatility indices"
                            status="complete"
                          />

                          <ChainOfThoughtStep
                            icon={SearchIcon}
                            label="Generating comprehensive market analysis..."
                            status={isLoading && message.id === messages[messages.length - 1]?.id ? "active" : "complete"}
                          />
                        </ChainOfThoughtContent>
                      </ChainOfThought>
                    </div>
                  )}

                  {message.role === 'assistant' ? (
                    <>
                      <Separator className='my-4' />
                      <MessageResponse
                        isAnimating={isLoading && message.id === messages[messages.length - 1]?.id}
                      >
                        {message.content || (isLoading ? "Thinking..." : "")}
                      </MessageResponse>
                    </>
                  ) : (
                    <>
                      {/* Show attachments if present */}
                      {message.attachments && message.attachments.length > 0 && (
                        <div className="mb-3">
                          <Attachments variant="grid">
                            {message.attachments.map((attachment) => (
                              <Attachment
                                key={attachment.id}
                                data={attachment}
                              >
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
                {/* Message Toolbar */}
                {message.role === 'assistant' ? (
                  // Only show toolbar when response is complete
                  !isLoading || message.id !== messages[messages.length - 1]?.id ? (
                    <MessageToolbar>
                      <MessageActions>
                        <MessageAction
                          label="Retry"
                          onClick={handleRetry}
                          tooltip="Regenerate response"
                        >
                          <RefreshCcwIcon className="size-4" />
                        </MessageAction>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <MessageAction
                              label="Export"
                              tooltip="Export response"
                            >
                              <Upload className="size-4" />
                            </MessageAction>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => handleExport('docs', message.id)}>
                              Export as Docs
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleExport('md', message.id)}>
                              Export as MD
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleExport('pdf', message.id)}>
                              Export as PDF
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                        <MessageAction
                          label="Copy"
                          onClick={() => handleCopy(message.content, message.id)}
                          tooltip="Copy to clipboard"
                          disabled={copyState[message.id] === 'loading' || copyState[message.id] === 'success'}
                        >
                          {copyState[message.id] === 'loading' ? (
                            <Loader2Icon className="size-4 animate-spin" />
                          ) : copyState[message.id] === 'success' ? (
                            <CheckIcon className="size-4 text-green-500" />
                          ) : (
                            <CopyIcon className="size-4" />
                          )}
                        </MessageAction>
                      </MessageActions>
                    </MessageToolbar>
                  ) : null
                ) : (
                  <MessageToolbar className="justify-end mt-0">
                    <MessageActions>
                      <MessageAction
                        label="Copy"
                        onClick={() => handleCopy(message.content, message.id)}
                        disabled={copyState[message.id] === 'loading' || copyState[message.id] === 'success'}
                      >
                        {copyState[message.id] === 'loading' ? (
                          <Loader2Icon className="size-4 animate-spin" />
                        ) : copyState[message.id] === 'success' ? (
                          <CheckIcon className="size-4 text-green-500" />
                        ) : (
                          <CopyIcon className="size-4" />
                        )}
                      </MessageAction>
                    </MessageActions>
                  </MessageToolbar>
                )}
              </Message>
            ))
          )}
          <div ref={messagesEndRef} className="h-4 w-full invisible" aria-hidden="true" />
        </div>
      </main>

      {/* 3. Footer Area - Fixed Height Composer */}
      <footer className="shrink-0 w-full pb-4 pt-2 px-4 bg-background z-20 border-t border-border/10 mt-auto">
        <div className="max-w-4xl mx-auto">
          <Composer
            value={input}
            onChange={setInput}
            onSend={handleSend}
            onStop={handleStop}
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