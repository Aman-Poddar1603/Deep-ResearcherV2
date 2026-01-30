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
**Author:** Dr. Aris Thorne

---

## 1. The Incident Report (Text Wrapping Test)

It began as a minor fluctuation in the telemetry data, something easily dismissed as sensor drift or cosmic ray interference, but within hours, the cascading failures across the distributed node network indicated a catastrophic synchronization error that threatened to decouple the primary logic gates from the temporal anchor. We spent the better part of the morning analyzing the heap dumps from the main server, only to realize that the memory leaks weren't just consuming RAM—they were actively overwriting the instruction pointers of adjacent processes, creating a chaotic feedback loop where the system was essentially trying to garbage-collect its own operating system kernel while simultaneously attempting to scale up to meet a phantom traffic spike that didn't exist in reality but was being hallucinated by the corrupted load balancer configuration.

The team scrambled to isolate the affected clusters, physically pulling network cables from the racking units in the server farm because the software-defined networking switches had become unresponsive to administrative overrides, leaving us with no choice but to resort to manual, hardware-level intervention to stop the propagation of the corrupt data packets before they could infect the backup archives stored in the subterranean vault, which, if compromised, would have resulted in the total loss of three decades of research data and the immediate insolvency of the entire organization.

---

## 2. Technical Analysis & Code Patch

To stabilize the grid, we had to hot-patch the quantum alignment algorithm. The original implementation failed to account for non-linear time dilation during high-load execution cycles.

Here is the **Python** patch we deployed to the edge nodes:

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

### The Mathematical Basis (LaTeX Test)

The reason the code above works is based on the **Heisenberg-Compensator Limit**. We model the system stability $S(t)$ using the following differential equation:

$$
\\frac{dS}{dt} = -\\alpha S(t) + \\beta \\sum_{i=1}^{N} \\frac{e^{-\\lambda_i t}}{\\sqrt{1 + \\omega_i^2}}
$$

Where:
* $\\alpha$ is the decay constant of the error.
* $\\lambda_i$ represents the latency of the $i$-th node.

If $S(t) \\to 0$, the system crashes. We need $S(t) \\geq 1.0$ at all times.

---

## 3. Comparative Metrics (Table Test)

We compared the performance of three different rendering engines during the recovery phase. Note how the memory usage spikes with the legacy parser.

| Engine | Cold Start (ms) | Memory (MB) | Throughput (Req/s) | Status |
| :--- | :---: | :---: | :---: | ---: |
| **Vulkan-X** | 120ms | 450MB | 12,500 | ✅ Stable |
| **Legacy-V2** | 850ms | **2,400MB** | 3,200 | ❌ Deprecated |
| **Neutron** | 45ms | 120MB | 28,000 | 🚀 Optimal |

---

## 4. The Recovery Narrative (Density Test)

After the patch was applied, we watched the monitors in silence, the hum of the cooling fans slowly returning to a steady, rhythmic drone that signified normal operation, a stark contrast to the erratic, high-pitched whining that had filled the room only moments before. The dashboard lights, which had been flashing a seizure-inducing pattern of critical red alerts, began to turn green one by one, rippling across the wall of screens like a wave of relief washing over the tired faces of the engineering team. It was a testament to the resilience of the open-source stack we had built; despite the proprietary modules failing first, the underlying Linux kernel and the custom Rust-based microservices held the line just long enough for us to inject the fix, proving once again that in the face of unforeseen entropy, simplicity and transparency in code architecture are not just best practices, but survival strategies. We ordered pizza at 4:00 AM, sitting on the anti-static floor tiles, exhausted but victorious, knowing that while the shareholders would never understand how close we came to the brink, the logs—the immutable, cryptographic logs—would forever bear witness to the night we saved the machine from itself.

---

## 5. Architectural Diagram (Mermaid Test)

\`\`\`mermaid
graph TD
    User[End User] -->|Request| LB{Load Balancer}
    LB -->|Route A| API[API Gateway]
    LB -->|Route B| Edge[Edge Functions]
    
    subgraph "Secure Zone"
    API --> Auth[OAuth2 Service]
    API --> DB[(Primary Database)]
    end
    
    subgraph "Async Processing"
    Edge --> Queue[Kafka Stream]
    Queue --> Worker[GPU Worker Node]
    Worker --> Cache[(Redis Cache)]
    end
    
    Worker -->|Update Status| DB
\`\`\`

---

## 6. Final Checklist (Task List)

- [x] **Verify Data Integrity:** Ensure no records were lost during the reboot.
- [x] **Flush DNS Cache:** Propagate the new IP addresses.
- [ ] **Write Post-Mortem:** (In Progress)
- [ ] **Sleep:** Not started yet.

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
                  <MessageResponse shikiTheme={['dracula', 'dracula']}
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