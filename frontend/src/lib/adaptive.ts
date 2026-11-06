import { api } from '../api'
import type { LanguageCode, Outcome } from '../types'

type Skill = 'recognize' | 'produce' | 'prepositions' | 'articles' | 'writing'
type Event = { eventId: string; language: LanguageCode; skill: Skill; answers: { term: string; outcome: 'correct' | 'partial' | 'wrong' | 'seen'; assisted: boolean }[] }
const KEY = 'languages.exercise-progress.pending'
let flushing = false

function pending(): Event[] {
  try { const value: unknown = JSON.parse(localStorage.getItem(KEY) || '[]'); return Array.isArray(value) ? value : [] } catch { return [] }
}

export async function flushProgress() {
  if (flushing) return
  flushing = true
  try {
    while (true) {
      const queue = pending()
      if (!queue.length) break
      try { await api.exerciseProgress(queue[0]) } catch { break }
      localStorage.setItem(KEY, JSON.stringify(pending().filter((event) => event.eventId !== queue[0].eventId)))
    }
  } finally { flushing = false }
}

export function recordProgress(kind: string, item: unknown, feedback: unknown, outcome: Outcome | 'seen', language: LanguageCode, assisted: boolean, viewId?: string) {
  if (outcome === 'skipped') return
  const skills: Record<string, Skill> = { quiz: 'recognize', typed: 'produce', 'mixed-recognize': 'recognize', 'mixed-produce': 'produce', prepositions: 'prepositions', articles: 'articles', writing: 'writing' }
  const skill = skills[kind]
  if (!skill) return
  let terms: { term: string; outcome: 'correct' | 'partial' | 'wrong' | 'seen'; assisted: boolean }[] = []
  if (Array.isArray(item) && kind === 'writing') {
    const checks = (feedback as { terms?: { term: string; used: boolean; usedCorrectly: boolean }[] } | null)?.terms ?? []
    terms = item.flatMap<Event['answers'][number]>((entry: { term: string }) => {
      if (outcome === 'seen') return [{ term: entry.term, outcome: 'seen' as const, assisted: false }]
      const check = checks.find((candidate) => candidate.term === entry.term)
      return check ? [{ term: entry.term, outcome: check.used && check.usedCorrectly ? 'correct' as const : 'wrong' as const, assisted }] : []
    })
  } else if (item && typeof item === 'object') {
    const question = item as { term?: string; terms?: string[]; sourceLanguage?: LanguageCode }
    if (question.sourceLanguage) language = question.sourceLanguage
    const names = question.terms ?? (question.term ? [question.term] : [])
    terms = names.map((term) => ({ term, outcome, assisted }))
  }
  if (!terms.length) return
  const eventId = viewId ?? (typeof crypto.randomUUID === 'function' ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`)
  const queue = pending()
  queue.push({ eventId, language, skill, answers: terms })
  try { localStorage.setItem(KEY, JSON.stringify(queue)); void flushProgress() } catch { /* Exercise feedback must remain usable. */ }
}
