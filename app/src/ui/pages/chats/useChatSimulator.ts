import { useState, useRef, useCallback } from 'react';
import { nanoid } from 'nanoid';
import { type AttachmentData } from '@/components/ai-elements/attachments';

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    attachments?: AttachmentData[];
}

export function useChatSimulator() {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const stopStreamingRef = useRef(false);

    const simulateResponse = useCallback(async (currentMessages: ChatMessage[]) => {
        stopStreamingRef.current = false;
        setIsLoading(true);

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
            const response = await fetch('http://localhost:11434/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: 'granite3-moe', // Default to deepseek-r1:8b, you can change this
                    messages: currentMessages.map(m => ({ role: m.role, content: m.content })),
                    stream: true,
                }),
            });

            if (!response.ok) throw new Error('Ollama connection failed');
            const reader = response.body?.getReader();
            const decoder = new TextDecoder();
            let currentText = '';
            let lastUpdateTime = Date.now();

            if (reader) {
                while (true) {
                    if (stopStreamingRef.current) {
                        await reader.cancel();
                        break;
                    }

                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value, { stream: true });
                    const lines = chunk.split('\n');

                    for (const line of lines) {
                        if (!line) continue;
                        try {
                            const json = JSON.parse(line);
                            if (json.message?.content) {
                                currentText += json.message.content;
                            }
                            if (json.done) break;
                        } catch (e) {
                            // Junk lines are common in streams
                            console.error('Error parsing chunk:', e);
                        }
                    }

                    // Batch updates for performance
                    const now = Date.now();
                    if (now - lastUpdateTime > 100) {
                        setMessages((prev) => {
                            const last = prev[prev.length - 1];
                            if (last?.id === assistantMessageId) {
                                return [...prev.slice(0, -1), { ...last, content: currentText }];
                            }
                            return prev;
                        });
                        lastUpdateTime = now;
                    }
                }

                // Final update to ensure everything is captured
                setMessages((prev) => {
                    const last = prev[prev.length - 1];
                    if (last?.id === assistantMessageId) {
                        return [...prev.slice(0, -1), { ...last, content: currentText }];
                    }
                    return prev;
                });
            }
        } catch (error) {
            console.error('Ollama Error:', error);
            setMessages((prev) => {
                const last = prev[prev.length - 1];
                if (last?.id === assistantMessageId) {
                    return [...prev.slice(0, -1), {
                        ...last,
                        content: 'Error: Could not connect to Ollama. Make sure it is running on http://localhost:11434 and you have the model "deepseek-r1:8b" pulled.'
                    }];
                }
                return prev;
            });
        }

        setIsLoading(false);
    }, []);

    const sendMessage = useCallback((value: string, files?: File[]) => {
        if (!value.trim() && (!files || files.length === 0)) return;

        const attachments: AttachmentData[] | undefined = files?.map((file) => ({
            id: nanoid(),
            type: 'file' as const,
            url: URL.createObjectURL(file),
            mediaType: file.type,
            filename: file.name,
        }));

        const userMessage: ChatMessage = {
            id: nanoid() + '-user',
            role: 'user',
            content: value,
            attachments,
        };

        const nextMessages = [...messages, userMessage];
        setMessages(nextMessages);
        simulateResponse(nextMessages);
    }, [simulateResponse, messages]);

    const stopStreaming = useCallback(() => {
        stopStreamingRef.current = true;
        setIsLoading(false);
    }, []);

    return {
        messages,
        isLoading,
        sendMessage,
        stopStreaming,
    };
}
