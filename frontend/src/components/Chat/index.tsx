// File: frontend/src/components/Chat/index.tsx
import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { IoSend } from 'react-icons/io5';

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

interface ChatProps {
  /** Initial messages to display */
  initialMessages?: Message[];
  /** Session ID for conversation continuity */
  sessionId?: string | null;
  /** Called when a new message is sent/received */
  onMessagesChange?: (messages: Message[]) => void;
  /** Called when session ID is established/updated */
  onSessionIdChange?: (sessionId: string) => void;
  /** Custom class name for the chat container */
  className?: string;
  /** Placeholder text for input */
  placeholder?: string;
  /** Disable input? */
  disabled?: boolean;
  /** Enable streaming responses (SSE) */
  stream?: boolean;
}

const Chat: React.FC<ChatProps> = ({
  initialMessages = [],
  sessionId: externalSessionId,
  onMessagesChange,
  onSessionIdChange,
  className = '',
  placeholder = 'Ask about properties, mortgages, or get recommendations...',
  disabled = false,
  stream = false,
}) => {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [internalSessionId, setInternalSessionId] = useState<string | null>(externalSessionId || null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Sync with external sessionId if provided
  useEffect(() => {
    if (externalSessionId !== undefined) {
      setInternalSessionId(externalSessionId);
    }
  }, [externalSessionId]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Notify parent of message changes
  useEffect(() => {
    onMessagesChange?.(messages);
  }, [messages, onMessagesChange]);

  const handleSend = async () => {
    if (!input.trim() || loading || disabled) return;

    const userMessage: Message = { role: 'user', content: input };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInput('');
    setLoading(true);

    // Cancel any ongoing stream
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      if (stream) {
        await handleStreamResponse(updatedMessages);
      } else {
        await handleNonStreamResponse(updatedMessages);
      }
    } catch (error) {
      if (axios.isCancel(error)) {
        console.log('Request canceled');
        return;
      }
      console.error('Chat error:', error);
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' },
      ]);
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
    }
  };

  const handleNonStreamResponse = async (currentMessages: Message[]) => {
    const response = await axios.post(
      '/api/v1/chat',
      {
        messages: currentMessages,
        session_id: internalSessionId,
        stream: false,
      },
      { signal: abortControllerRef.current?.signal }
    );

    const data = response.data;
    const newSessionId = data.session_id;
    if (newSessionId && newSessionId !== internalSessionId) {
      setInternalSessionId(newSessionId);
      onSessionIdChange?.(newSessionId);
    }

    setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
  };

  const handleStreamResponse = async (currentMessages: Message[]) => {
    const response = await fetch('/api/v1/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: currentMessages,
        session_id: internalSessionId,
        stream: true,
      }),
      signal: abortControllerRef.current?.signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error('No response body');

    const decoder = new TextDecoder();
    let assistantMessage = '';
    let newSessionId = internalSessionId;

    // Add a placeholder assistant message that we'll update
    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            
            if (data.session_id) {
              newSessionId = data.session_id;
            }
            
            if (data.content) {
              assistantMessage += data.content;
              // Update the last message (assistant's response)
              setMessages(prev => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  role: 'assistant',
                  content: assistantMessage,
                };
                return updated;
              });
            }
            
            if (data.done) {
              if (newSessionId && newSessionId !== internalSessionId) {
                setInternalSessionId(newSessionId);
                onSessionIdChange?.(newSessionId);
              }
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setLoading(false);
    }
  };

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center py-12">
            <h3 className="text-lg font-medium text-gray-700 mb-2">
              👋 Welcome to RealEstate AI Assistant
            </h3>
            <p className="text-gray-500">
              Ask me anything about properties, mortgages, or get personalized recommendations.
            </p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-3 ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white border border-gray-200 text-gray-800 shadow-sm'
                }`}
              >
                {msg.role === 'assistant' ? (
                  <ReactMarkdown
                    className="prose prose-sm max-w-none"
                    components={{
                      a: ({ node, ...props }) => (
                        <a {...props} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline" />
                      ),
                      code: ({ node, ...props }) => (
                        <code {...props} className="bg-gray-100 rounded px-1 py-0.5 text-sm" />
                      ),
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                ) : (
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                )}
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-lg px-4 py-3 shadow-sm">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse delay-150" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse delay-300" />
                {stream && (
                  <button
                    onClick={handleStopGeneration}
                    className="ml-2 text-xs text-gray-500 hover:text-gray-700 underline"
                  >
                    Stop
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-gray-200 bg-white p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={placeholder}
            className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
            disabled={loading || disabled}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim() || disabled}
            className="bg-blue-600 text-white rounded-lg px-4 py-2 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label="Send message"
          >
            <IoSend />
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Press Enter to send, Shift+Enter for new line.
        </p>
      </div>
    </div>
  );
};

export default Chat;