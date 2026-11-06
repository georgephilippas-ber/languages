import type { Category, LanguageCode } from '../types'

export interface ArticleSource { word: string; url: string; retrievedAt: string }
export interface Draft {
  id: string
  language: LanguageCode
  request: string
  status: 'queued' | 'loading' | 'ready' | 'error'
  term?: string
  markdown?: string
  gloss?: string
  error?: string
  articleSource?: ArticleSource
  category?: Category
}
export function newId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}
