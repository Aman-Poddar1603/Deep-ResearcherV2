import { useState, useRef } from 'react'
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
import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from '@/components/ai-elements/conversation'
import { SearchIcon, CopyIcon, RefreshCcwIcon, Loader2Icon, CheckIcon, Upload, MessageSquare } from 'lucide-react'
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
import { Separator } from '@/components/ui/separator'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

// Dummy markdown content for testing  
const DUMMY_RESPONSE = `
# 🏆 THE SUPREME MARKDOWN STREAMING STRESS TEST v3.0

This content is specifically engineered to test the structural integrity of a streaming AI response formatter. It transitions rapidly between prose, syntax-heavy code, visual assets, and mathematical notation.

---

## 🖼️ Section 1: Visual Media Integration
Testing the rendering of external image assets within the flow of text.

![Landscape Photography](https://s3.amazonaws.com/images.seroundtable.com/google-amp-1454071566.jpg)
*Figure 1: Nature and Landscape*

![Futuristic Technology](https://media.istockphoto.com/id/506910700/photo/i-can-do-it.jpg?s=612x612&w=0&k=20&c=4r5UQKSwjtVyLai0R0B38RJXX2SFr0TpK4JFSWnVCfQ=)
*Figure 2: Technological Advancement*

![Space Nebula](https://pngimg.com/d/google_PNG19641.png)
*Figure 3: Deep Space Exploration*

---

## 🏗️ Section 3: Diagrams & Logic
Mermaid.js requires a complete block to render correctly. This tests the "wait-for-block-end" logic.

\`\`\`mermaid
graph LR
    Start[User Prompt] --> Process{Streaming Engine}
    Process -->|Token A| Render[Markdown Formatter]
    Process -->|Token B| Render
    Render --> Output[Visual Display]
    Output --> Feedback{User Approval}
    Feedback -->|Yes| End((Success))
    Feedback -->|No| Start
\`\`\`

---

## 🧬 Section 3: High-Density Typography & Lists
The following nested structure tests indentation logic and symbol switching.

* **System Architecture**
    * Frontend Layer
        * React.js / Next.js
        * Tailwind CSS
            * Custom Utility Classes
            * Responsive Variants
    * Backend Layer
        * Node.js Streaming API
        * Python LLM Wrapper
1.  **Deployment Steps**
    1.  Provision Instance
    2.  Set Environment Variables
        - \`API_KEY=********\`
        - \`NODE_ENV=production\`
    3.  Launch Container

---

## 🧪 Section 4: Advanced Mathematics (LaTeX)
Testing the math engine's ability to render complex formulas during a text stream.

**The General Relativity Field Equation:**
$$G_{\\mu\\nu} + \\Lambda g_{\\mu\\nu} = \\kappa T_{\\mu\\nu}$$

**The Maxwell Equations:**
- $\\nabla \\cdot \\mathbf{E} = \\frac{\\rho}{\\varepsilon_0}$
- $\\nabla \\cdot \\mathbf{B} = 0$

---

## 📊 Section 5: Complex Data Tables
Tables are often the hardest to stream because the columns must align before the final row is received.

| Rank | Component Name | Performance Index | Reliability | Current Status |
| :--- | :--- | :---: | :---: | :--- |
| 1 | Global Load Balancer | 99.9% | High | ✅ Operational |
| 2 | Primary Database Cluster | 94.2% | Medium | ⚠️ Syncing |
| 3 | Content Delivery Network | 99.8% | High | ✅ Operational |
| 4 | Image Retrieval Engine | 88.5% | Low | 🛠️ Maintenance |

---

## 📸 Section 6: Additional Visual Assets

![Digital Art](https://img.freepik.com/free-vector/inspirational-quote-watercolour-background_1048-18831.jpg?semt=ais_user_personalization&w=740&q=80)

![Mountain Peak](https://imageio.forbes.com/specials-images/dam/imageserve/1023678802/960x0.jpg?height=474&width=711&fit=bounds)

![Coral Reef](https://img.freepik.com/free-vector/positive-lettering-be-good-yourself-message-watercolor-stain_23-2148342665.jpg?semt=ais_user_personalization&w=740&q=80)

---

## 💻 Section 7: Code Block Syntax Highlighting
Testing the buffer for large code blocks with language-specific highlighting.

\`\`\`typescript
interface StreamConfig {
  speed: number;
  chunkSize: number;
  enableMarkdown: boolean;
}

/**
 * Simulates the streaming process for testing formatters.
 */
async function streamPayload(data: string, config: StreamConfig): Promise<void> {
  const words = data.split(' ');
  for (const word of words) {
    process.stdout.write(word + ' ');
    await new Promise(resolve => setTimeout(resolve, config.speed));
  }
}
\`\`\`

---

## 📖 Section 8: Long-Form Narrative Wall
> "The limits of my language mean the limits of my world." — Ludwig Wittgenstein

The implementation of a streaming markdown formatter is a delicate balance of regular expression matching, state management, and DOM manipulation. As the AI generates content, the frontend must parse incomplete fragments of syntax—such as an open bold tag or a half-finished table row—without causing the layout to jump or flicker. This requires a robust, incremental parser that can look ahead and predict the likely structure of the incoming data while maintaining a smooth 60fps frame rate for the user. When we include complex elements like LaTeX or Mermaid, the challenge triples, as these require secondary rendering passes once the code block is completed. Every token processed is a test of the architecture's resilience, ensuring that whether the user is viewing a simple paragraph or a complex scientific paper, the experience remains fluid, legible, and visually consistent across all devices and network conditions.

---

### ✅ Test Completion Checklist
- [x] Inline and Block LaTeX
- [x] Mermaid Charting
- [x] 6 High-Res External Images
- [x] Multi-column Tables
- [x] Deeply Nested Unordered/Ordered Lists
- [x] Blockquotes and Links

**Stream Test Complete.**
`;

const ChatInterface = () => {
  // Mimic useChat state for client-side demo
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [copyState, setCopyState] = useState<Record<string, 'idle' | 'loading' | 'success'>>({})

  // Ref for stopping stream
  const stopStreamingRef = useRef(false)

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

    const userMessage: ChatMessage = {
      id: Date.now().toString() + '-user',
      role: 'user',
      content: value,
      attachments,
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
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
      setTimeout(() => setCopyState(prev => ({ ...prev, [messageId]: 'idle' })), 2000)
    } catch (error) {
      console.error('Failed to copy:', error)
      setCopyState(prev => ({ ...prev, [messageId]: 'idle' }))
    }
  }

  const handleRetry = () => console.log('Retrying...')
  const handleExport = (format: string, id: string) => console.log(`Exporting ${id} as ${format}`)

  return (
    <div className="flex flex-col h-full w-full text-foreground animate-in fade-in duration-500 overflow-hidden relative">
      {/* 1. Header Area */}
      <header className="absolute top-4 right-6 z-30 pointer-events-none">
        <div className="pointer-events-auto backdrop-blur-xl bg-background/80 border border-border/50 rounded-2xl px-6 py-3 shadow-lg shadow-black/5 animate-in fade-in slide-in-from-top-2 duration-500">
          <h2 className="text-sm font-semibold bg-linear-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
            Cryptocurrency Market Analysis
          </h2>
        </div>
      </header>

      {/* 2. Messages area using Conversation element */}
      <Conversation className="flex-1 w-full mt-20">
        <ConversationContent className="max-w-4xl mx-auto pb-32">
          {messages.length === 0 ? (
            <ConversationEmptyState
              icon={<MessageSquare className="size-12 text-primary/50" />}
              title="Deep Researcher"
              description="Start a conversation to begin your research journey."
            />
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

                {message.role === 'assistant' ? (
                  (!isLoading || message.id !== messages[messages.length - 1]?.id) && (
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
                  )
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
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>

      {/* 3. Footer Area */}
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
