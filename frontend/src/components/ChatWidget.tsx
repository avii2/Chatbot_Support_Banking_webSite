import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react'
import {
  clearStoredHistory,
  getOrCreateSessionId,
  loadStoredHistory,
  saveStoredHistory
} from './chatWidgetStorage'

type MessageRole = 'user' | 'assistant'

type ChatSource = {
  doc: string
  snippet: string
}

type ChatMessage = {
  id: string
  role: MessageRole
  content: string
  createdAt: string
  sources?: ChatSource[]
  isError?: boolean
}

type ChatResponse = {
  answer: string
  sources?: ChatSource[]
}

type ChatWidgetProps = {
  apiBaseUrl?: string
  title?: string
  subtitle?: string
}

const BOT_WELCOME_MESSAGE: ChatMessage = {
  id: 'welcome',
  role: 'assistant',
  content:
    'Hi, I am your banking assistant. Ask about accounts, KYC, card fees, loans, disputes, or support escalation.',
  createdAt: new Date(0).toISOString()
}

function toErrorMessage(error: unknown): string {
  if (error instanceof DOMException && error.name === 'AbortError') {
    return 'Request was cancelled. Please send your message again.'
  }

  return 'I could not reach support systems right now. Please try again in a moment.'
}

function nextMessageId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export default function ChatWidget({
  apiBaseUrl,
  title = 'Visioapps Bank Assistant',
  subtitle = 'Answers from approved bank policy documents'
}: ChatWidgetProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [sessionId, setSessionId] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const listRef = useRef<HTMLDivElement | null>(null)
  const inputRef = useRef<HTMLTextAreaElement | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const baseUrl = useMemo(() => {
    const fromEnv = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? ''
    return (apiBaseUrl ?? fromEnv).replace(/\/$/, '')
  }, [apiBaseUrl])

  useEffect(() => {
    const id = getOrCreateSessionId()
    setSessionId(id)

    const stored = loadStoredHistory<ChatMessage>(id)
    if (stored.length > 0) {
      setMessages(stored)
      return
    }

    setMessages([BOT_WELCOME_MESSAGE])
  }, [])

  useEffect(() => {
    if (!sessionId || messages.length === 0) {
      return
    }

    saveStoredHistory(sessionId, messages)
  }, [messages, sessionId])

  useEffect(() => {
    if (!listRef.current) {
      return
    }

    listRef.current.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, isLoading])

  useEffect(() => {
    if (!isOpen) {
      return
    }

    inputRef.current?.focus()
  }, [isOpen])

  useEffect(() => {
    return () => {
      abortRef.current?.abort()
    }
  }, [])

  const appendMessage = useCallback((message: ChatMessage) => {
    setMessages((prev) => [...prev, message])
  }, [])

  const handleClearChat = useCallback(() => {
    if (!sessionId) {
      return
    }

    abortRef.current?.abort()
    setIsLoading(false)

    const initial = [
      {
        ...BOT_WELCOME_MESSAGE,
        id: nextMessageId('welcome')
      }
    ]

    setMessages(initial)
    clearStoredHistory(sessionId)
    saveStoredHistory(sessionId, initial)
    setInputValue('')
  }, [sessionId])

  const sendMessage = useCallback(async () => {
    const trimmed = inputValue.trim()
    if (!trimmed || isLoading || !sessionId) {
      return
    }

    const userMessage: ChatMessage = {
      id: nextMessageId('user'),
      role: 'user',
      content: trimmed,
      createdAt: new Date().toISOString()
    }

    appendMessage(userMessage)
    setInputValue('')
    setIsLoading(true)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const response = await fetch(`${baseUrl}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          sessionId,
          message: trimmed
        }),
        signal: controller.signal
      })

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`)
      }

      const payload = (await response.json()) as ChatResponse
      const answerText = payload.answer?.trim()

      appendMessage({
        id: nextMessageId('assistant'),
        role: 'assistant',
        content: answerText || 'I do not have enough data to answer that right now.',
        createdAt: new Date().toISOString(),
        sources: Array.isArray(payload.sources) ? payload.sources : []
      })
    } catch (error) {
      appendMessage({
        id: nextMessageId('error'),
        role: 'assistant',
        content: toErrorMessage(error),
        createdAt: new Date().toISOString(),
        isError: true
      })
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null
      }
      setIsLoading(false)
    }
  }, [appendMessage, baseUrl, inputValue, isLoading, sessionId])

  const onInputKeyDown = useCallback(
    (event: KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault()
        void sendMessage()
      }
    },
    [sendMessage]
  )

  return (
    <div className="fixed bottom-6 right-6 z-40 flex items-end justify-end">
      <div
        className={[
          'absolute bottom-16 right-0 h-[480px] w-[360px] max-w-[calc(100vw-1.5rem)] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft transition-all duration-200',
          isOpen ? 'translate-y-0 opacity-100' : 'pointer-events-none translate-y-3 opacity-0'
        ].join(' ')}
        role="dialog"
        aria-label="Banking chat assistant"
        aria-hidden={!isOpen}
      >
        <div className="flex h-full flex-col">
          <header className="flex items-start justify-between gap-2 border-b border-slate-200 bg-brand-navy px-4 py-3 text-white">
            <div className="min-w-0">
              <h2 className="truncate font-display text-sm">{title}</h2>
              <p className="truncate text-xs text-blue-100">{subtitle}</p>
            </div>

            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={handleClearChat}
                className="rounded-md bg-white/15 px-2 py-1 text-xs font-medium hover:bg-white/25"
              >
                Clear
              </button>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="rounded-md bg-white/15 px-2 py-1 text-xs font-medium hover:bg-white/25"
              >
                Close
              </button>
            </div>
          </header>

          <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto bg-slate-50 p-3">
            {messages.map((message) => {
              const isUser = message.role === 'user'
              return (
                <div
                  key={message.id}
                  className={[
                    'max-w-[90%] rounded-2xl px-3 py-2 text-sm shadow-sm',
                    isUser
                      ? 'ml-auto bg-brand-teal text-white'
                      : message.isError
                        ? 'mr-auto border border-red-200 bg-red-50 text-red-700'
                        : 'mr-auto border border-slate-200 bg-white text-slate-800'
                  ].join(' ')}
                >
                  <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>

                  {!isUser && message.sources && message.sources.length > 0 && (
                    <div className="mt-2 rounded-lg bg-slate-100 p-2">
                      <p className="text-[11px] font-semibold uppercase text-slate-500">Sources</p>
                      <ul className="mt-1 space-y-1 text-[11px] text-slate-700">
                        {message.sources.map((source, index) => (
                          <li key={`${message.id}-source-${index}`}>
                            <span className="font-semibold">{source.doc}:</span> {source.snippet}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )
            })}

            {isLoading && (
              <div className="mr-auto inline-flex items-center gap-1 rounded-2xl border border-slate-200 bg-white px-3 py-2 text-slate-700">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-slate-500" />
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-slate-500 [animation-delay:120ms]" />
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-slate-500 [animation-delay:240ms]" />
              </div>
            )}
          </div>

          <footer className="border-t border-slate-200 bg-white p-3">
            <div className="flex items-end gap-2">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(event) => setInputValue(event.target.value)}
                onKeyDown={onInputKeyDown}
                rows={2}
                disabled={isLoading}
                placeholder="Ask a banking question..."
                className="min-h-[64px] flex-1 resize-none rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-brand-teal disabled:cursor-not-allowed disabled:bg-slate-100"
              />
              <button
                type="button"
                onClick={() => void sendMessage()}
                disabled={isLoading || !inputValue.trim()}
                className="rounded-xl bg-brand-navy px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {isLoading ? 'Sending...' : 'Send'}
              </button>
            </div>
          </footer>
        </div>
      </div>

      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
        aria-label={isOpen ? 'Close chat assistant' : 'Open chat assistant'}
        className="flex h-14 w-14 items-center justify-center rounded-full bg-brand-coral text-white shadow-soft transition hover:scale-105 hover:bg-red-500 focus:outline-none focus:ring-2 focus:ring-brand-coral focus:ring-offset-2"
      >
        <svg viewBox="0 0 24 24" className="h-6 w-6 fill-current" aria-hidden="true">
          <path d="M4 4h16v11H7.5L4 18.5V4zm2 2v8.1l1.1-1.1H18V6H6zm2.5 2h7v2h-7V8zm0 3h5v2h-5v-2z" />
        </svg>
      </button>
    </div>
  )
}
