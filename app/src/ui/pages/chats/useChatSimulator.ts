import { useState, useRef, useCallback, useEffect } from 'react';
import { nanoid } from 'nanoid';
import { type AttachmentData } from '@/components/ai-elements/attachments';
import {
    createChatThread,
    getChatRuntimeWsUrl,
} from '@/lib/apis';

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    images?: string[]; // Base64 encoded images for Ollama
    attachments?: AttachmentData[];
    citations?: Record<string, string>;
}

interface ChatRuntimeSource {
    href?: string;
    title?: string;
}

interface UseChatSimulatorOptions {
    threadId?: string;
    workspaceId?: string;
    onThreadCreated?: (threadId: string) => void;
    onTitle?: (title: string) => void;
    onStatus?: (status: string) => void;
    useAgent?: boolean;
}

interface ChatRuntimeAttachment {
    file_name: string;
    file_format: string;
    data: string;
}

interface ChatRuntimeEvent {
    type?: string;
    content?: string;
    status?: string;
    tool?: string;
    file_name?: string;
    sources?: ChatRuntimeSource[];
    count?: number;
}

const sourcesToCitations = (sources: ChatRuntimeSource[] | undefined): Record<string, string> => {
    if (!Array.isArray(sources) || sources.length === 0) {
        return {};
    }

    const citations: Record<string, string> = {};
    const seenTitles: Record<string, number> = {};
    for (const item of sources) {
        const href = (item?.href ?? '').trim();
        const baseTitle = (item?.title ?? '').trim() || 'Source';
        if (!href) continue;

        const nextCount = (seenTitles[baseTitle] ?? 0) + 1;
        seenTitles[baseTitle] = nextCount;
        const title = nextCount > 1 ? `${baseTitle} (${nextCount})` : baseTitle;
        citations[title] = href;
    }
    return citations;
};

const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
            const result = reader.result as string;
            if (!result) {
                reject(new Error('Failed to read file data'));
                return;
            }
            resolve(result.split(',')[1] ?? '');
        };
        reader.onerror = () => reject(new Error('Failed to read file data'));
        reader.readAsDataURL(file);
    });
};

const toAttachmentPayload = async (file: File): Promise<ChatRuntimeAttachment> => {
    const ext = file.name.includes('.')
        ? file.name.split('.').pop()?.toLowerCase()
        : file.type.split('/').pop()?.toLowerCase();
    return {
        file_name: file.name,
        file_format: ext || 'file',
        data: await fileToBase64(file),
    };
};

export function useChatSimulator(options: UseChatSimulatorOptions = {}) {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const onThreadCreated = options.onThreadCreated;
    const onTitle = options.onTitle;
    const onStatus = options.onStatus;
    const useAgent = options.useAgent;
    const stopStreamingRef = useRef(false);
    const wsRef = useRef<WebSocket | null>(null);
    const threadIdRef = useRef(options.threadId?.trim() ?? '');
    const workspaceIdRef = useRef(options.workspaceId?.trim() ?? '');
    const statusRef = useRef('');

    useEffect(() => {
        threadIdRef.current = options.threadId?.trim() ?? '';
    }, [options.threadId]);

    useEffect(() => {
        workspaceIdRef.current = options.workspaceId?.trim() ?? '';
    }, [options.workspaceId]);

    const closeSocket = useCallback(() => {
        if (wsRef.current) {
            try {
                wsRef.current.close();
            } catch {
                // no-op
            }
            wsRef.current = null;
        }
    }, []);

    const emitStatus = useCallback((nextStatus: string) => {
        const normalized = nextStatus.trim();
        if (statusRef.current === normalized) {
            return;
        }
        statusRef.current = normalized;
        onStatus?.(normalized);
    }, [onStatus]);

    const ensureThreadId = useCallback(async (): Promise<string> => {
        const existing = threadIdRef.current;
        if (existing && existing !== 'new') {
            return existing;
        }

        const workspaceId = workspaceIdRef.current;
        if (!workspaceId || workspaceId === 'new') {
            throw new Error('Please select a workspace before starting a new chat');
        }

        const created = await createChatThread({
            thread_title: 'New Chat',
            workspace_id: workspaceId,
        });
        threadIdRef.current = created.thread_id;
        onThreadCreated?.(created.thread_id);
        return created.thread_id;
    }, [onThreadCreated]);

    const simulateResponse = useCallback(async (currentMessages: ChatMessage[], files?: File[]) => {
        stopStreamingRef.current = false;
        setIsLoading(true);
        emitStatus(files && files.length > 0 ? 'Analyzing attachments...' : 'Preparing response...');

        const assistantMessageId = nanoid() + '-ai';
        setMessages((prev) => [
            ...prev,
            {
                id: assistantMessageId,
                role: 'assistant',
                content: '',
            },
        ]);

        try {
            const threadId = await ensureThreadId();
            const payloadAttachments = files
                ? await Promise.all(files.map(toAttachmentPayload))
                : [];

            const wsUrl = getChatRuntimeWsUrl(threadId);

            await new Promise<void>((resolve, reject) => {
                let finished = false;

                const finalize = () => {
                    if (finished) return;
                    finished = true;
                    resolve();
                };

                const fail = (error: Error) => {
                    if (finished) return;
                    finished = true;
                    reject(error);
                };

                const ws = new WebSocket(wsUrl);
                wsRef.current = ws;

                ws.onopen = () => {
                    const user = [...currentMessages]
                        .reverse()
                        .find((msg) => msg.role === 'user');
                    ws.send(
                        JSON.stringify({
                            content: user?.content ?? '',
                            attachments: payloadAttachments,
                            use_agent: !!useAgent,
                        }),
                    );
                };

                ws.onmessage = (event) => {
                    if (stopStreamingRef.current) {
                        finalize();
                        return;
                    }

                    let data: ChatRuntimeEvent | null = null;
                    try {
                        data = JSON.parse(event.data) as ChatRuntimeEvent;
                    } catch {
                        return;
                    }

                    if (!data?.type) return;

                    if (data.type === 'token') {
                        const chunk = data.content ?? '';
                        if (!chunk) return;
                        emitStatus('Generating response...');
                        setMessages((prev) => {
                            const last = prev[prev.length - 1];
                            if (last?.id === assistantMessageId) {
                                return [...prev.slice(0, -1), {
                                    ...last,
                                    content: `${last.content}${chunk}`,
                                }];
                            }
                            return prev;
                        });
                        return;
                    }

                    if (data.type === 'thinking') {
                        emitStatus('Planning next steps...');
                        return;
                    }

                    if (data.type === 'attachment_status') {
                        const fileName = (data.file_name ?? '').trim();
                        const tool = (data.tool ?? '').trim();
                        const status = (data.status ?? '').trim().toLowerCase();

                        if (status === 'failed' || status === 'error') {
                            emitStatus(fileName ? `Analysis failed for ${fileName}` : 'Attachment analysis failed');
                            return;
                        }
                        if (status === 'success' || status === 'completed') {
                            if (tool) {
                                emitStatus(`Using ${tool}`);
                            } else {
                                emitStatus(fileName ? `Analyzed ${fileName}` : 'Attachment analyzed');
                            }
                            return;
                        }
                        if (fileName) {
                            emitStatus(`Analyzing ${fileName}`);
                            return;
                        }
                        if (tool) {
                            emitStatus(`Using ${tool}`);
                        }
                        return;
                    }

                    if (data.type === 'tool_status') {
                        const tool = (data.tool ?? '').trim();
                        emitStatus(tool ? `Using ${tool}` : 'Using tools...');
                        return;
                    }

                    if (data.type === 'error') {
                        const errorText = data.content ?? 'Failed to stream response';
                        emitStatus('Response failed');
                        setMessages((prev) => {
                            const last = prev[prev.length - 1];
                            if (last?.id === assistantMessageId) {
                                return [...prev.slice(0, -1), {
                                    ...last,
                                    content: errorText,
                                }];
                            }
                            return prev;
                        });
                        finalize();
                        closeSocket();
                        return;
                    }

                    if (data.type === 'sources') {
                        const citations = sourcesToCitations(data.sources);
                        if (Object.keys(citations).length === 0) {
                            return;
                        }
                        setMessages((prev) => {
                            const last = prev[prev.length - 1];
                            if (last?.id === assistantMessageId) {
                                return [
                                    ...prev.slice(0, -1),
                                    {
                                        ...last,
                                        citations,
                                    },
                                ];
                            }
                            return prev;
                        });
                        return;
                    }

                    if (data.type === 'title') {
                        const title = (data.content ?? '').trim();
                        if (title) {
                            onTitle?.(title);
                        }
                        return;
                    }

                    if (data.type === 'done') {
                        window.setTimeout(() => {
                            emitStatus('');
                            finalize();
                            closeSocket();
                        }, 250);
                    }
                };

                ws.onerror = () => {
                    emitStatus('Connection failed');
                    fail(new Error('Could not connect to backend chat runtime websocket'));
                };

                ws.onclose = () => {
                    wsRef.current = null;
                    if (!finished) {
                        finalize();
                    }
                };
            });
        } catch (error) {
            console.error('Chat Runtime Error:', error);
            emitStatus('');
            setMessages((prev) => {
                const last = prev[prev.length - 1];
                if (last?.id === assistantMessageId) {
                    return [...prev.slice(0, -1), {
                        ...last,
                        content: `Error: ${error instanceof Error ? error.message : 'Could not connect to backend chat service'}. Make sure backend is running on http://localhost:8000.`
                    }];
                }
                return prev;
            });
        } finally {
            closeSocket();
            setIsLoading(false);
            emitStatus('');
        }
    }, [closeSocket, emitStatus, ensureThreadId, onTitle, useAgent]);

    const sendMessage = useCallback(async (value: string, files?: File[]) => {
        if (!value.trim() && (!files || files.length === 0)) return;

        // Process attachments and convert images to base64 for Ollama
        const messageImages: string[] = [];
        const attachments: AttachmentData[] | undefined = files?.map((file) => {
            const id = nanoid();
            const url = URL.createObjectURL(file);

            // If it's an image, we need to handle base64 for the API
            if (file.type.startsWith('image/')) {
                // We'll handle the async conversion below
            }

            return {
                id,
                type: 'file' as const,
                url,
                mediaType: file.type,
                filename: file.name,
            };
        });

        // Async helper to convert files to base64
        if (files) {
            for (const file of files) {
                if (file.type.startsWith('image/')) {
                    const base64 = await new Promise<string>((resolve) => {
                        const reader = new FileReader();
                        reader.onloadend = () => {
                            const result = reader.result as string;
                            // strip the prefix (e.g. data:image/jpeg;base64,)
                            resolve(result.split(',')[1]);
                        };
                        reader.readAsDataURL(file);
                    });
                    messageImages.push(base64);
                }
            }
        }

        const userMessage: ChatMessage = {
            id: nanoid() + '-user',
            role: 'user',
            content: value,
            images: messageImages.length > 0 ? messageImages : undefined,
            attachments,
        };

        const nextMessages = [...messages, userMessage];
        setMessages(nextMessages);
        await simulateResponse(nextMessages, files);
    }, [simulateResponse, messages]);

    const stopStreaming = useCallback(() => {
        stopStreamingRef.current = true;
        closeSocket();
        setIsLoading(false);
        emitStatus('');
    }, [closeSocket, emitStatus]);

    const replaceMessages = useCallback((
        next: ChatMessage[],
        config?: { preserveStreaming?: boolean },
    ) => {
        if (!config?.preserveStreaming) {
            stopStreamingRef.current = true;
            closeSocket();
            setIsLoading(false);
            emitStatus('');
        }
        setMessages(next);
    }, [closeSocket, emitStatus]);

    return {
        messages,
        isLoading,
        sendMessage,
        stopStreaming,
        replaceMessages,
    };
}
