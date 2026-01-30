import { useState, useEffect, useRef } from 'react'
import { Message, MessageContent, MessageResponse } from '@/components/ai-elements/message'
import "katex/dist/katex.min.css";

// Define a local type that matches expectations for this component's text-based logic
interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
}
import Composer from '@/components/widgets/Composer'
import { cn } from '@/lib/utils'
import { FileText } from 'lucide-react'

// Dummy markdown content for testing
const DUMMY_RESPONSE = `
# 📉 High-Dimensional Market Data (Responsiveness Test)

This table has **15 columns**. If your CSS is correct, it should show a horizontal scrollbar instead of breaking the layout or squishing the text unreadably.

| ID | Ticker | Price (USD) | 24h Change | Momentum Formula | Volatility Index | $$\\alpha$$ (Alpha) | $$\\beta$$ (Beta) | $$\\gamma$$ (Gamma) | $$\\delta$$ (Delta) | $$\\theta$$ (Theta) | Market Cap | Volume (24h) | Hash | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **001** | \`BTC-X\` | **$94,320.50** | 🟢 +2.4% | $$P = P_0 e^{rt}$$ | High | $$\\alpha > 0.5$$ | $$\\beta \\approx 1.2$$ | $$\\gamma = \\frac{\\partial^2 V}{\\partial S^2}$$ | $$\\delta = 0.45$$ | $$\\theta = -0.05$$ | $1.8T | 45B | \`0x4d2...\` | Primary reserve asset. |
| **002** | \`ETH-Q\` | **$4,102.10** | 🔴 -1.2% | $$v = \\frac{d}{t}$$ | Medium | $$\\alpha = 0.1$$ | $$\\beta = 0.9$$ | $$\\gamma \\to 0$$ | $$\\delta = 0.60$$ | $$\\theta = -0.12$$ | $450B | 12B | \`0x9a1...\` | Smart contract layer. |
| **003** | \`SOL-V\` | **$145.67** | 🟢 +5.8% | $$F = ma$$ | Extreme | $$\\alpha < 0$$ | $$\\beta > 2.0$$ | $$\\gamma = \\infty$$ | $$\\delta = 0.88$$ | $$\\theta = -0.99$$ | $78B | 4B | \`0x1f4...\` | High throughput chain. |
| **004** | \`ATOM\` | **$12.45** | 🟡 0.0% | $$E = mc^2$$ | Low | $$\\alpha = 0$$ | $$\\beta = 1.0$$ | $$\\gamma = 1$$ | $$\\delta = 0.50$$ | $$\\theta = -0.01$$ | $5B | 200M | \`0x3c2...\` | Interchain connectivity. |
| **005** | \`QNT-M\` | **$1,024.00** | 🟢 +12% | $$\\sum_{i=0}^{n} x_i$$ | High | $$\\alpha \\approx 1$$ | $$\\beta = 1.5$$ | $$\\gamma = \\pi$$ | $$\\delta = 0.33$$ | $$\\theta = -0.02$$ | $12B | 800M | \`0x7b9...\` | Enterprise gateway. |
| **006** | \`LINK\` | **$18.90** | 🔴 -0.5% | $$\\sqrt{x^2 + y^2}$$ | Low | $$\\alpha = 0.2$$ | $$\\beta = 0.8$$ | $$\\gamma = 0.5$$ | $$\\delta = 0.12$$ | $$\\theta = -0.04$$ | $9B | 350M | \`0x2e8...\` | Oracle network. |
`;

const ChatInterface = () => {
  // Mimic useChat state for client-side demo
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')

  // Refs for auto-scrolling and stopping stream
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const stopStreamingRef = useRef(false)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, streamingContent])

  const simulateResponse = async () => {
    stopStreamingRef.current = false
    setIsLoading(true)
    setStreamingContent('')

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
      setStreamingContent(currentText)

      // Update the last message
      setMessages(prev => prev.map(msg =>
        msg.id === assistantMessageId
          ? { ...msg, content: currentText }
          : msg
      ))
    }

    setIsLoading(false)
  }

  const handleSend = (value: string) => {
    if (!value.trim()) return

    // Add user message
    const userMessage: ChatMessage = {
      id: Date.now().toString() + '-user',
      role: 'user',
      content: value
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

  return (
    <div className="flex flex-col h-full w-full relative">
      {/* Messages Area - Scrollable */}
      <div className="flex-1 overflow-y-auto w-full">
        <div className="max-w-4xl mx-auto px-4 md:px-8 py-8 space-y-8">
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
                <MessageContent className={message.role === 'user' ? "shadow-sm" : "bg-transparent px-0 py-0 w-full text-justify"}>
                  <MessageResponse
                    isAnimating={isLoading && message.role === 'assistant' && message.id === messages[messages.length - 1]?.id}
                  >
                    {message.content || (isLoading && message.role === 'assistant' ? "Thinking..." : "")}
                  </MessageResponse>
                </MessageContent>
              </Message>
            ))
          )}
          <div ref={messagesEndRef} className="h-4" />
        </div>
      </div>

      {/* Composer Area - Fixed at bottom of the container */}
      <div className="w-full pb-2 pt-2 px-4 bg-linear-to-t from-background via-background/95 to-transparent z-20">
        <div className="max-w-6xl mx-auto">
          <Composer
            value={input}
            onChange={setInput}
            onSend={handleSend}
            onStop={handleStop}
            isLoading={isLoading}
            placeholder="Ask anything..."
          />
          <div className="text-center mt-3">
            <p className="text-[10px] text-muted-foreground/60 font-medium">
              AI can make mistakes. Please verify important information.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ChatInterface