import type { ExerciseKind } from '../types'

const PREFIX = 'languages.'

export function readStored<T>(key: string): T | undefined {
  try {
    const raw = localStorage.getItem(PREFIX + key)
    return raw === null ? undefined : (JSON.parse(raw) as T)
  } catch {
    return undefined
  }
}

export function writeStored(key: string, value: unknown): void {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(value))
  } catch {
    return
  }
}

export function removeStored(key: string): void {
  try {
    localStorage.removeItem(PREFIX + key)
  } catch {
    return
  }
}

const SESSION_KINDS: ExerciseKind[] = ['quiz', 'typed', 'writing']

export function sessionKey(kind: ExerciseKind): string {
  return `session.${kind}`
}

export function discardSessions(): void {
  for (const kind of SESSION_KINDS) removeStored(sessionKey(kind))
}
