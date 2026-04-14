import { useState, useCallback, memo, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  getAllWorkspaces,
  getChatThread,
  listChatMessages,
  resolveApiUrl,
  type ChatMessageAttachmentItem,
  type ChatMessageRecord,
} from '@/lib/apis'
import { toast } from '@/components/ui/sonner'
import { Message, MessageContent, MessageResponse, MessageAction, MessageActions, MessageToolbar } from '@/components/ai-elements/message'
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
import { CopyIcon, RefreshCcwIcon, Loader2Icon, CheckIcon, Upload, MessageSquare } from 'lucide-react'
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

function inferAttachmentMediaType(
  attachmentType: string | null | undefined,
  fileName: string | null | undefined,
): string {
  const fromType = (attachmentType || '').toLowerCase().replace(/^\./, '')
  const fromName = (fileName || '').toLowerCase().split('.').pop() || ''
  const ext = fromType || fromName

  if (['png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp', 'svg', 'tiff'].includes(ext)) {
    return `image/${ext === 'jpg' ? 'jpeg' : ext}`
  }
  if (['mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm'].includes(ext)) {
    return `video/${ext}`
  }
  if (['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a'].includes(ext)) {
    return `audio/${ext}`
  }
  if (ext === 'txt') return 'text/plain'
  if (ext === 'md') return 'text/markdown'
  if (ext === 'csv') return 'text/csv'
  if (ext === 'json') return 'application/json'
  if (ext === 'xml') return 'application/xml'
  if (ext === 'pdf') return 'application/pdf'
  if (ext === 'doc') return 'application/msword'
  if (ext === 'docx') {
    return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  }
  if (ext === 'ppt') return 'application/vnd.ms-powerpoint'
  if (ext === 'pptx') {
    return 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
  }
  if (ext === 'xls') return 'application/vnd.ms-excel'
  if (ext === 'xlsx') {
    return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  }
  return 'application/octet-stream'
}

function toAttachmentUrl(item: ChatMessageAttachmentItem): string | null {
  const direct = item.url ?? null
  if (direct) {
    return resolveApiUrl(direct)
  }
  const storedPath = item.attachment_path?.trim()
  if (!storedPath) return null
  const normalized = storedPath.replace(/^\/+/, '')
  return resolveApiUrl(`/bucket/assets/${normalized}`)
}

function mapMessageAttachments(m: ChatMessageRecord): AttachmentData[] {
  const items = m.attachment_items ?? []
  return items
    .map((item): AttachmentData | null => {
      const url = toAttachmentUrl(item)
      if (!url) return null

      const filename = item.file_name ?? item.attachment_path?.split('/').pop() ?? 'Attachment'

      return {
        id: item.attachment_id,
        type: 'file',
        url,
        filename,
        mediaType: inferAttachmentMediaType(item.attachment_type, filename),
      }
    })
    .filter((value): value is AttachmentData => value !== null)
}

function mapRecordToChatMessage(m: ChatMessageRecord): ChatMessage {
  const roleRaw = (m.role ?? 'assistant').toLowerCase()
  const role: 'user' | 'assistant' =
    roleRaw === 'user' ? 'user' : 'assistant'
  const attachments = mapMessageAttachments(m)
  return {
    id: m.message_id,
    role,
    content: m.content ?? '',
    attachments: attachments.length > 0 ? attachments : undefined,
  }
}
import { Shimmer } from '@/components/ai-elements/shimmer'
import { Persona } from '@/components/ai-elements/persona'
// Memoized individual message item to prevent unnecessary re-renders during streaming
const ChatMessageItem = memo(({
  message,
  isLoading,
  isLast,
  runtimeStatus,
  handleCopy,
  handleRetry,
  handleExport,
  copyStatus
}: {
  message: ChatMessage,
  isLoading: boolean,
  isLast: boolean,
  runtimeStatus: string,
  handleCopy: (content: string, id: string) => void,
  handleRetry: () => void,
  handleExport: (format: string, id: string) => void,
  copyStatus: 'idle' | 'loading' | 'success'
}) => {
  const isAssistant = message.role === 'assistant'
  const isStreaming = isLast && isLoading && isAssistant
  const activeStatus = runtimeStatus.trim()

  return (
    <Message
      from={message.role}
      className={cn(
        "animate-in fade-in slide-in-from-bottom-2 duration-300 max-w-full",
        message.role === 'user' ? "pl-12 ml-auto" : ""
      )}
    >
      <MessageContent className={message.role === 'user' ? "shadow-sm text-foreground" : "bg-transparent px-0 py-0 w-full text-justify"}>
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
              isLoading && isLast && (
                <div className="flex items-center gap-2 mb-4">
                  <Persona state="thinking" className="size-5" variant="glint" />
                  <Shimmer className="text-sm font-medium">
                    {activeStatus || 'Generating response...'}
                  </Shimmer>
                </div>
              )
            )}
            {isStreaming && activeStatus && !!message.content && (
              <div className="mt-2 flex items-center gap-2 text-muted-foreground/80">
                <Persona
                  state={message.content ? 'speaking' : 'thinking'}
                  className="size-4"
                  variant="glint"
                />
                <span className="text-xs font-medium">{activeStatus}</span>
              </div>
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
  const navigate = useNavigate()
  const { id: threadId } = useParams<{ id: string }>()
  const normalizedThreadId = threadId?.trim() ?? ''
  const isDraftThread = !normalizedThreadId || normalizedThreadId === 'new'
  const [workspaceOptions, setWorkspaceOptions] = useState<Array<{ id: string; name: string }>>([])
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState('')
  const [isLoadingWorkspaces, setIsLoadingWorkspaces] = useState(false)
  const [headerTitle, setHeaderTitle] = useState('Chat')
  const [headerSub, setHeaderSub] = useState('')
  const [runtimeStatus, setRuntimeStatus] = useState('')

  const handleRuntimeTitle = useCallback((title: string) => {
    const nextTitle = title.trim()
    if (!nextTitle) return
    setHeaderTitle(nextTitle)
  }, [])

  const { messages, isLoading, sendMessage, stopStreaming, replaceMessages } =
    useChatSimulator({
      threadId: isDraftThread ? undefined : normalizedThreadId,
      workspaceId: selectedWorkspaceId,
      onTitle: handleRuntimeTitle,
      onStatus: setRuntimeStatus,
      onThreadCreated: (nextThreadId) => {
        navigate(`/chat/${encodeURIComponent(nextThreadId)}`, { replace: true })
      },
    })
  const [input, setInput] = useState('')
  const [copyState, setCopyState] = useState<
    Record<string, 'idle' | 'loading' | 'success'>
  >({})

  useEffect(() => {
    let cancelled = false

    void (async () => {
      setIsLoadingWorkspaces(true)
      try {
        const { workspaces } = await getAllWorkspaces({
          page: 1,
          size: 200,
          sortBy: 'updated_at',
          sortOrder: 'desc',
        })
        if (cancelled) return

        const options = workspaces.map((workspace) => ({
          id: workspace.id,
          name: workspace.name,
        }))
        setWorkspaceOptions(options)

        const savedWorkspaceId = window.localStorage
          .getItem('dr.chat.workspaceId')
          ?.trim() ?? ''
        if (!savedWorkspaceId) return
        if (!options.some((workspace) => workspace.id === savedWorkspaceId)) return

        setSelectedWorkspaceId((current) => current || savedWorkspaceId)
      } catch {
        if (!cancelled) {
          setWorkspaceOptions([])
        }
      } finally {
        if (!cancelled) {
          setIsLoadingWorkspaces(false)
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (isDraftThread) {
      setHeaderTitle('New Chat')
      setHeaderSub('Unsaved conversation')
      setRuntimeStatus('')
      if (!isLoading && messages.length > 0) {
        replaceMessages([], { preserveStreaming: true })
      }
      return
    }

    if (isLoading) {
      return
    }

    let cancelled = false
    void (async () => {
      try {
        const [thread, msgRes] = await Promise.all([
          getChatThread(normalizedThreadId),
          listChatMessages({
            threadId: normalizedThreadId,
            page: 1,
            size: 200,
            sortBy: 'message_seq',
            sortOrder: 'asc',
          }),
        ])
        if (cancelled) return
        setHeaderTitle(thread.thread_title?.trim() || 'Chat')
        const ws = thread.workspace_id?.trim()
        const updated = new Date(thread.updated_at).toLocaleDateString(
          'en-US',
          { month: 'short', day: 'numeric', year: 'numeric' },
        )
        setHeaderSub(
          ws ? `Workspace ${ws} • ${updated}` : updated,
        )
        if (ws) {
          setSelectedWorkspaceId(ws)
          window.localStorage.setItem('dr.chat.workspaceId', ws)
        }

        const hydratedMessages = msgRes.items.map(mapRecordToChatMessage)
        if (hydratedMessages.length > 0 || messages.length === 0) {
          replaceMessages(hydratedMessages, { preserveStreaming: true })
        }
      } catch (e) {
        if (!cancelled) {
          toast.error(
            e instanceof Error ? e.message : 'Failed to load conversation',
          )
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [isDraftThread, isLoading, messages.length, normalizedThreadId, replaceMessages])

  const handleWorkspaceChange = useCallback((workspaceId: string) => {
    const normalized = workspaceId.trim()
    setSelectedWorkspaceId(normalized)
    if (normalized) {
      window.localStorage.setItem('dr.chat.workspaceId', normalized)
    }
  }, [])

  const handleSend = useCallback((value: string, files?: File[]) => {
    if (isDraftThread && !selectedWorkspaceId.trim()) {
      toast.error('Select a workspace before starting a chat')
      return
    }
    sendMessage(value, files)
    setInput('')
  }, [isDraftThread, selectedWorkspaceId, sendMessage])

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
          <div className="flex flex-col min-w-0">
            <h2 className="text-sm font-semibold bg-linear-to-r from-foreground to-foreground/70 bg-clip-text text-transparent leading-none truncate max-w-[min(100vw-8rem,28rem)]">
              {headerTitle}
            </h2>
            <p className="text-[10px] text-muted-foreground/60 mt-1 font-medium truncate max-w-[min(100vw-8rem,28rem)]">
              {(isLoading && runtimeStatus) || headerSub || (threadId ? `Thread ${threadId}` : 'Conversation')}
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
                runtimeStatus={runtimeStatus}
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
            workspaceId={selectedWorkspaceId}
            workspaceOptions={workspaceOptions}
            onWorkspaceChange={handleWorkspaceChange}
            workspaceRequired={isDraftThread}
            workspaceLoading={isLoadingWorkspaces}
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
