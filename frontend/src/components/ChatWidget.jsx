import { useEffect, useMemo, useRef, useState } from 'react'
import logochatbot from '../../logochatbot.png'

const SESSION_STORAGE_KEY = 'dummybank_chat_session_id'
const LANGUAGE_STORAGE_KEY = 'dummybank_chat_language'
const DEFAULT_LANGUAGE = 'en-IN'

const LANGUAGES = [
  { label: 'English', code: 'en-IN' },
  { label: 'हिन्दी', code: 'hi-IN' },
  { label: 'தமிழ்', code: 'ta-IN' },
  { label: 'ಕನ್ನಡ', code: 'kn-IN' },
  { label: 'తెలుగు', code: 'te-IN' },
  { label: 'বাংলা', code: 'bn-IN' },
  { label: 'मराठी', code: 'mr-IN' },
  { label: 'മലയാളം', code: 'ml-IN' },
  { label: 'ਪੰਜਾਬੀ', code: 'pa-IN' },
  { label: 'ગુજરાતી', code: 'gu-IN' },
  { label: 'ଓଡ଼ିଆ', code: 'or-IN' },
  { label: 'অসমীয়া', code: 'as-IN' },
  { label: 'اردو', code: 'ur-IN' }
]

function getSpeechRecognitionCtor() {
  if (typeof window === 'undefined') return null
  return window.SpeechRecognition || window.webkitSpeechRecognition || null
}

function getOrCreateSessionId() {
  const existing = localStorage.getItem(SESSION_STORAGE_KEY)
  if (existing) return existing

  const generated =
    typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `session-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`

  localStorage.setItem(SESSION_STORAGE_KEY, generated)
  return generated
}

function historyKey(sessionId) {
  return `dummybank_messages_${sessionId}`
}

export default function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [sessionId, setSessionId] = useState('')
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [language, setLanguage] = useState(DEFAULT_LANGUAGE)
  const [pendingLanguage, setPendingLanguage] = useState(DEFAULT_LANGUAGE)
  const [languageModalOpen, setLanguageModalOpen] = useState(false)
  const listRef = useRef(null)
  const recognitionRef = useRef(null)
  const transcriptRef = useRef('')
  const holdTimerRef = useRef(null)
  const voiceActiveRef = useRef(false)

  const apiBaseUrl = useMemo(
    () => (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, ''),
    []
  )

  useEffect(() => {
    setSessionId(getOrCreateSessionId())
  }, [])

  useEffect(() => {
    const savedLanguage = localStorage.getItem(LANGUAGE_STORAGE_KEY)
    const isKnownLanguage = LANGUAGES.some((item) => item.code === savedLanguage)

    if (isKnownLanguage) {
      setLanguage(savedLanguage)
      setPendingLanguage(savedLanguage)
    }
  }, [])

  useEffect(() => {
    if (!sessionId) return
    const saved = localStorage.getItem(historyKey(sessionId))
    if (!saved) return

    try {
      const parsed = JSON.parse(saved)
      if (Array.isArray(parsed)) {
        setMessages(parsed)
      }
    } catch {
      localStorage.removeItem(historyKey(sessionId))
    }
  }, [sessionId])

  useEffect(() => {
    if (!sessionId) return
    localStorage.setItem(historyKey(sessionId), JSON.stringify(messages))
  }, [messages, sessionId])

  useEffect(() => {
    if (!listRef.current) return
    listRef.current.scrollTop = listRef.current.scrollHeight
  }, [messages, loading])

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop()
        } catch {
          // no-op cleanup
        }
      }
      if (holdTimerRef.current) {
        clearTimeout(holdTimerRef.current)
      }
    }
  }, [])

  async function handleSend(customMessage) {
    const base = typeof customMessage === 'string' ? customMessage : input
    const trimmed = base.trim()
    if (!trimmed || loading || !sessionId) return

    const userMsg = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: trimmed,
      createdAt: new Date().toISOString()
    }

    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const response = await fetch(`${apiBaseUrl}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          sessionId,
          message: trimmed
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const payload = await response.json()
      const botMsg = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: payload.answer,
        sources: payload.sources || [],
        createdAt: new Date().toISOString()
      }

      setMessages((prev) => [...prev, botMsg])
    } catch (error) {
      const fallback = {
        id: `e-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I could not reach support systems. Please try again.',
        sources: [],
        createdAt: new Date().toISOString()
      }
      setMessages((prev) => [...prev, fallback])
    } finally {
      setLoading(false)
    }
  }

  function startVoiceRecognition() {
    const SpeechRecognitionCtor = getSpeechRecognitionCtor()
    if (!SpeechRecognitionCtor || loading || !sessionId) return

    transcriptRef.current = ''

    const recognition = new SpeechRecognitionCtor()
    recognition.lang = language
    recognition.continuous = false
    recognition.interimResults = true

    recognition.onresult = (event) => {
      const transcript = Array.from(event.results || [])
        .map((result) => result?.[0]?.transcript || '')
        .join(' ')
        .trim()

      if (transcript) {
        transcriptRef.current = transcript
      }
    }

    recognition.onend = () => {
      const transcript = transcriptRef.current.trim()
      recognitionRef.current = null
      transcriptRef.current = ''

      if (transcript) {
        setInput(transcript)
        handleSend(transcript)
      }

      voiceActiveRef.current = false
    }

    recognition.onerror = () => {
      recognitionRef.current = null
      voiceActiveRef.current = false
    }

    try {
      recognition.start()
      recognitionRef.current = recognition
    } catch {
      recognitionRef.current = null
      voiceActiveRef.current = false
    }
  }

  function stopVoiceRecognition() {
    if (!voiceActiveRef.current) return
    if (holdTimerRef.current) {
      clearTimeout(holdTimerRef.current)
      holdTimerRef.current = null
    }

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop()
      } catch {
        // no-op
      }
    }
  }

  function handleSendPressStart(event) {
    if (loading || !sessionId) return
    if (event.type === 'mousedown' && event.button !== 0) return

    if (holdTimerRef.current) {
      clearTimeout(holdTimerRef.current)
    }

    holdTimerRef.current = setTimeout(() => {
      voiceActiveRef.current = true
      startVoiceRecognition()
    }, 220)
  }

  function handleSendPressEnd() {
    if (holdTimerRef.current) {
      clearTimeout(holdTimerRef.current)
      holdTimerRef.current = null
    }

    if (voiceActiveRef.current) {
      stopVoiceRecognition()
    }
  }

  function handleSendClick() {
    if (voiceActiveRef.current) return
    handleSend()
  }

  function openLanguageModal() {
    setPendingLanguage(language)
    setLanguageModalOpen(true)
  }

  function submitLanguageSelection() {
    setLanguage(pendingLanguage)
    localStorage.setItem(LANGUAGE_STORAGE_KEY, pendingLanguage)
    setLanguageModalOpen(false)
  }

  function onInputKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="fixed bottom-6 right-6 z-40 flex items-end justify-end">
      <div
        className={[
          'absolute bottom-16 right-0 h-[480px] w-[360px] max-w-[calc(100vw-1.5rem)] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft transition-all duration-300',
          open ? 'translate-y-0 opacity-100' : 'pointer-events-none translate-y-4 opacity-0'
        ].join(' ')}
      >
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between bg-brand-navy px-4 py-3 text-white">
            <div>
              <p className="font-display text-sm">Hi, Welcome, I am Louie.</p>


              <p className="text-xs text-slate-200">How may I assist you today!</p>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="rounded-md bg-white/15 px-2 py-1 text-xs hover:bg-white/25"
            >
              Close
            </button>
          </div>

          <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto bg-slate-50 p-3">
           

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={[
                  'max-w-[90%] rounded-2xl px-3 py-2 text-sm shadow-sm',
                  msg.role === 'user'
                    ? 'ml-auto bg-brand-teal text-white'
                    : 'mr-auto border border-slate-200 bg-white text-slate-800'
                ].join(' ')}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>

                {msg.role === 'assistant' && Array.isArray(msg.sources) && msg.sources.length > 0 && (
                  <div className="mt-2 rounded-lg bg-slate-100 p-2">
                    <p className="text-[11px] font-semibold uppercase text-slate-500">Sources</p>
                    <ul className="mt-1 space-y-1 text-[11px] text-slate-700">
                      {msg.sources.map((source, index) => (
                        <li key={`${msg.id}-src-${index}`}>
                          <span className="font-semibold">{source.doc}:</span> {source.snippet}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="mr-auto inline-flex items-center gap-1 rounded-2xl border border-slate-200 bg-white px-3 py-2 text-slate-700">
                <span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-slate-500" style={{ animationDelay: '0ms' }} />
                <span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-slate-500" style={{ animationDelay: '150ms' }} />
                <span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-slate-500" style={{ animationDelay: '300ms' }} />
              </div>
            )}
          </div>

          <div className="border-t border-slate-200 bg-white p-3">
            <div className="flex items-end gap-2">
              <button
                type="button"
                onClick={openLanguageModal}
                className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                title="Select language"
              >
                Aa
              </button>
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={onInputKeyDown}
                rows={2}
                placeholder="Ask a banking question..."
                className="min-h-[64px] flex-1 resize-none rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-brand-teal"
              />
              <button
                type="button"
                onClick={handleSendClick}
                onMouseDown={handleSendPressStart}
                onMouseUp={handleSendPressEnd}
                onMouseLeave={handleSendPressEnd}
                onTouchStart={handleSendPressStart}
                onTouchEnd={handleSendPressEnd}
                onTouchCancel={handleSendPressEnd}
                disabled={loading}
                className="rounded-xl bg-brand-navy px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
                title="Hold Send to speak"
              >
                Send
              </button>
            </div>
            <p className="mt-1 text-[11px] text-slate-500">Hold Send to speak</p>
          </div>
        </div>
      </div>

      {languageModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <p className="font-display text-lg text-brand-navy">Select your Language</p>
              <button
                type="button"
                onClick={() => setLanguageModalOpen(false)}
                className="rounded-md px-2 py-1 text-slate-500 hover:bg-slate-100"
                aria-label="Close language selector"
              >
                X
              </button>
            </div>

            <div className="mt-4 grid grid-cols-3 gap-2">
              {LANGUAGES.map((item) => (
                <button
                  key={item.code}
                  type="button"
                  onClick={() => setPendingLanguage(item.code)}
                  className={[
                    'rounded-lg border px-2 py-2 text-xs font-medium text-slate-700 transition',
                    pendingLanguage === item.code
                      ? 'border-brand-teal bg-teal-50 text-brand-navy'
                      : 'border-slate-300 bg-white hover:bg-slate-50'
                  ].join(' ')}
                >
                  {item.label}
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={submitLanguageSelection}
              className="mt-4 w-full rounded-lg bg-brand-navy px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
            >
              SUBMIT
            </button>
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex h-14 w-14 items-center justify-center overflow-hidden rounded-full bg-brand-coral text-white shadow-soft transition hover:scale-105 hover:bg-red-500"
        aria-label="Open chat assistant"
      >
        <img src={logochatbot} alt="Chatbot" className="h-full w-full object-cover" />
      </button>
    </div>
  )
}
