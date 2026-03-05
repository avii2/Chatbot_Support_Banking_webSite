export const CHAT_SESSION_KEY = 'visioapps_bank_chat_session_id'

export function getHistoryKey(sessionId: string): string {
  return `visioapps_bank_chat_messages_${sessionId}`
}

export function createSessionId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }

  return `session-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export function getOrCreateSessionId(): string {
  if (typeof window === 'undefined') {
    return createSessionId()
  }

  const existing = window.localStorage.getItem(CHAT_SESSION_KEY)
  if (existing) {
    return existing
  }

  const nextId = createSessionId()
  window.localStorage.setItem(CHAT_SESSION_KEY, nextId)
  return nextId
}

export function loadStoredHistory<T>(sessionId: string): T[] {
  if (typeof window === 'undefined') {
    return []
  }

  const raw = window.localStorage.getItem(getHistoryKey(sessionId))
  if (!raw) {
    return []
  }

  try {
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) {
      return []
    }
    return parsed as T[]
  } catch {
    window.localStorage.removeItem(getHistoryKey(sessionId))
    return []
  }
}

export function saveStoredHistory<T>(sessionId: string, messages: T[]): void {
  if (typeof window === 'undefined') {
    return
  }

  window.localStorage.setItem(getHistoryKey(sessionId), JSON.stringify(messages))
}

export function clearStoredHistory(sessionId: string): void {
  if (typeof window === 'undefined') {
    return
  }

  window.localStorage.removeItem(getHistoryKey(sessionId))
}
