// Conversations are kept in this browser only (per manager code); each message points at a backend run.

export type Message = { question: string; runId: string; mode: 'demo' | 'live'; askedAt: string }
export type Conversation = { id: string; title: string; createdAt: string; messages: Message[] }

const key = (manager: string) => `echo-conversations-${manager.toUpperCase()}`

export function loadConversations(manager: string): Conversation[] {
  try {
    return JSON.parse(localStorage.getItem(key(manager)) ?? '[]')
  } catch {
    return []
  }
}

export function saveConversations(manager: string, conversations: Conversation[]) {
  try {
    localStorage.setItem(key(manager), JSON.stringify(conversations.slice(0, 50)))
  } catch {
    /* storage unavailable: conversations last for this session only */
  }
}

export function loadManagerCode(): string | null {
  try {
    return localStorage.getItem('echo-manager')
  } catch {
    return null
  }
}

export function saveManagerCode(code: string | null) {
  try {
    if (code) localStorage.setItem('echo-manager', code)
    else localStorage.removeItem('echo-manager')
  } catch {
    /* storage unavailable */
  }
}

export type Watched = WatchItemSaved
type WatchItemSaved = { metric: string; baseline: string; goal: string; savedAt: string; question: string }

const watchKey = (manager: string) => `echo-watch-${manager.toUpperCase()}`

export function loadWatch(manager: string): Watched[] {
  try {
    return JSON.parse(localStorage.getItem(watchKey(manager)) ?? '[]')
  } catch {
    return []
  }
}

export function saveWatch(manager: string, items: Watched[]) {
  try {
    localStorage.setItem(watchKey(manager), JSON.stringify(items))
  } catch {
    /* storage unavailable */
  }
}

// Recognition gaps the manager has marked as thanked (contribution ID -> when). Only stored in this browser.
const thankedKey = (manager: string) => `echo-thanked-${manager.toUpperCase()}`

export function loadThanked(manager: string): Record<string, string> {
  try {
    return JSON.parse(localStorage.getItem(thankedKey(manager)) ?? '{}')
  } catch {
    return {}
  }
}

export function saveThanked(manager: string, thanked: Record<string, string>) {
  try {
    localStorage.setItem(thankedKey(manager), JSON.stringify(thanked))
  } catch {
    /* storage unavailable */
  }
}

// Which quarter's updates the manager has already opened, so the badge only counts unseen ones.
const seenKey = (manager: string) => `echo-updates-seen-${manager.toUpperCase()}`

export function loadSeen(manager: string): string {
  try {
    return localStorage.getItem(seenKey(manager)) ?? ''
  } catch {
    return ''
  }
}

export function saveSeen(manager: string, value: string) {
  try {
    localStorage.setItem(seenKey(manager), value)
  } catch {
    /* storage unavailable */
  }
}
