import { useState, useEffect, useRef } from 'react'
import { Message, MessageContent, MessageResponse } from '@/components/ai-elements/message'

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
# 🌩️ The Architect's Log: Rebuilding the Core Protocol

**Date:** January 31, 2026
**Status:** CRITICAL
**Author:** pixelThreader

\`\`\`python
import numpy as np
from system.core import QuantumState, EntropyError

def stabilize_flux_matrix(tensor_input, dilation_factor=0.04):
    """
    Stabilizes the flux matrix by applying a reverse Fourier transform
    on the destabilized energy vectors.
    """
    try:
        # Calculate the Eigenvalues of the current state
        eigen_values = np.linalg.eigvals(tensor_input)
        
        # Filter out imaginary components that cause instability
        stable_vector = [x for x in eigen_values if np.isreal(x)]
        
        if len(stable_vector) < 3:
            raise EntropyError("Critical mass destabilization imminent.")
            
        return np.mean(stable_vector) * dilation_factor
        
    except Exception as e:
        print(f"CRITICAL FAILURE: {str(e)}")
        return None
\`\`\`

> **Warning:** Do not attempt to restart the *legacy clusters* without manual approval from the SysAdmin. They are currently quarantined.
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
                <MessageContent className={message.role === 'user' ? "shadow-sm" : "bg-transparent px-0 py-0"}>
                  <MessageResponse
                    isAnimating={false}
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