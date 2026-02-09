import { useState, useRef, useCallback } from 'react';
import { nanoid } from 'nanoid';
import { type AttachmentData } from '@/components/ai-elements/attachments';

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    thinking?: string;
    images?: string[]; // Base64 encoded images for Ollama
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
                thinking: '',
            },
        ]);

        try {
            const response = await fetch('http://localhost:11434/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: 'granite3-moe',
                    messages: currentMessages.map(m => ({
                        role: m.role,
                        content: m.content,
                        // images: m.images
                    })),
                    stream: true,
                    // think: true
                }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `Ollama connection failed: ${response.statusText}`);
            }
            const reader = response.body?.getReader();
            const decoder = new TextDecoder();
            let currentText = '';
            let thinkingText = '';
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
                            if (json.message?.thinking) {
                                thinkingText += json.message.thinking;
                            } else if (json.message?.content) {
                                currentText += json.message.content;
                            }
                            if (json.done) break;
                        } catch (e) {
                            // Junk lines
                            console.log(e);
                        }
                    }

                    // Batch updates for performance
                    const now = Date.now();
                    if (now - lastUpdateTime > 100) {
                        setMessages((prev) => {
                            const last = prev[prev.length - 1];
                            if (last?.id === assistantMessageId) {
                                return [...prev.slice(0, -1), {
                                    ...last,
                                    content: currentText,
                                    thinking: thinkingText
                                }];
                            }
                            return prev;
                        });
                        lastUpdateTime = now;
                    }
                }

                // Final update
                setMessages((prev) => {
                    const last = prev[prev.length - 1];
                    if (last?.id === assistantMessageId) {
                        return [...prev.slice(0, -1), {
                            ...last,
                            content: currentText,
                            thinking: thinkingText
                        }];
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
                        content: `Error: ${error instanceof Error ? error.message : 'Could not connect to Ollama'}. Make sure it is running on http://localhost:11434.`
                    }];
                }
                return prev;
            });
        }

        setIsLoading(false);
    }, []);

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
