import { readStored, sessionKey } from './storage'
import type { Article, ExerciseKind, LanguageCode } from '../types'

const EXERCISES: Record<string, ExerciseKind> = {
  '/quiz': 'quiz', '/typed': 'typed', '/writing': 'writing', '/prepositions': 'prepositions',
  '/articles': 'articles', '/translate/recognize': 'mixed-recognize', '/translate/produce': 'mixed-produce',
}

export function returnExercisePath(path: string, state: unknown, search = ''): string | null {
  if (path in EXERCISES || path === '/review') return path
  if (path === '/read') {
    const mode = new URLSearchParams(search).get('mode')
    return mode === 'find' || mode === 'url' || mode === 'text' ? `/read?mode=${mode}` : '/read'
  }
  if ((path === '/add' || path === '/ask') && state && typeof state === 'object' && 'returnToExercise' in state) {
    const value = (state as { returnToExercise?: unknown }).returnToExercise
    if (typeof value === 'string' && (value in EXERCISES || value === '/review' || /^\/read(?:\?mode=(?:find|url|text))?$/.test(value))) return value
  }
  return null
}

export function hasExerciseToReturn(path: string, language: LanguageCode): boolean {
  if (path === '/read' || path.startsWith('/read?')) {
    const articles = readStored<Partial<Record<LanguageCode, Article>>>('read.articles')
    return !!articles?.[language]?.retrievedAt
  }
  if (path === '/review') {
    const snapshot = readStored<{ study?: { queue?: unknown[] } }>('review.active')
    return !!snapshot?.study?.queue?.length
  }
  const kind = EXERCISES[path]
  if (!kind) return false
  const session = readStored<{ finished?: boolean; items?: unknown[] }>(sessionKey(kind))
  return !!session && !session.finished && Array.isArray(session.items) && session.items.length > 0
}
