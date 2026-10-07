import type { LanguageInfo } from '../types'

export function fileName(language: LanguageInfo, number: number): string {
  return `${language.name.toLowerCase()}-${number}.md`
}

export interface Target {
  name: string
  terms: number
  isNew: boolean
}

export function targetFile(language: LanguageInfo, limit: number): Target {
  const files = language.files
  const latest = files[files.length - 1]
  if (!latest) return { name: fileName(language, 1), terms: 0, isNew: true }
  if (latest.terms >= limit) return { name: fileName(language, latest.number + 1), terms: 0, isNew: true }
  return { name: latest.name, terms: latest.terms, isNew: false }
}
