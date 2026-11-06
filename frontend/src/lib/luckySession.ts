import { readStored, removeStored, sessionKey, writeStored } from './storage'
import type { LanguageCode } from '../types'

export type LuckyKind = 'quiz' | 'typed' | 'mixed-recognize' | 'mixed-produce'
export const LUCKY_PATHS: Record<LuckyKind, string> = {
  quiz: '/quiz', typed: '/typed', 'mixed-recognize': '/translate/recognize', 'mixed-produce': '/translate/produce',
}
export const LUCKY_LABELS: Record<LuckyKind, string> = {
  quiz: 'Recognise', typed: 'Produce', 'mixed-recognize': 'Translate · Recognize', 'mixed-produce': 'Translate · Produce',
}

export interface LuckyProgress {
  version: number
  request: { language: LanguageCode }
  items: unknown[]
  records: unknown[]
  index: number
  finished: boolean
  requireFullCount: boolean
  luckyId?: string
}
export interface LuckySnapshot { kind: LuckyKind; session: LuckyProgress }

function valid(value: unknown): value is LuckySnapshot {
  if (!value || typeof value !== 'object') return false
  const snapshot = value as Partial<LuckySnapshot>
  if (!snapshot.kind || !Object.prototype.hasOwnProperty.call(LUCKY_PATHS, snapshot.kind) || !snapshot.session || typeof snapshot.session !== 'object') return false
  const s = snapshot.session
  return s.version === 1 && s.requireFullCount === true && !s.finished && Array.isArray(s.items) && s.items.length > 0 &&
    Array.isArray(s.records) && s.records.length === s.items.length && Number.isInteger(s.index) &&
    s.index >= 0 && s.index < s.items.length && ['EN', 'DE', 'FR'].includes(s.request?.language)
}

export function readLuckySession(): LuckySnapshot | null {
  const stored = readStored<unknown>('lucky.session')
  if (valid(stored)) return stored
  // Adopt an unfinished Lucky session created before the dedicated Lucky state existed.
  if (!readStored<boolean>('lucky.migrated')) {
    for (const kind of Object.keys(LUCKY_PATHS) as LuckyKind[]) {
      const candidate = { kind, session: readStored<unknown>(sessionKey(kind)) }
      if (valid(candidate)) {
        return candidate
      }
    }
  }
  return null
}

export function saveLuckySession(kind: string, session: unknown): void {
  const snapshot = { kind, session }
  if (!valid(snapshot)) return
  writeStored('lucky.session', snapshot)
  writeStored('lucky.migrated', true)
}

export function clearLuckySession(kind: string, luckyId?: string): void {
  const stored = readStored<unknown>('lucky.session')
  if (valid(stored) && stored.kind === kind && stored.session.luckyId === luckyId) removeStored('lucky.session')
  writeStored('lucky.migrated', true)
}
