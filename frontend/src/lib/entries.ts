import type { Category, LanguageInfo } from '../types'

export function fileName(language: LanguageInfo, number: number): string {
  return `${language.name.toLowerCase()}-${number}.md`
}

export interface Target {
  name: string
  terms: number
  isNew: boolean
}

export function targetFile(language: LanguageInfo, limit: number, category: Category = 'general'): Target {
  const files = language.files.filter((file) => category === 'general' ? typeof file.number === 'number' : typeof file.number === 'string' && file.number.startsWith(`${category}:`))
  const name = (number: number) => `${language.name.toLowerCase()}-${category === 'general' ? '' : `${category}-`}${number}.md`
  const latest = files[files.length - 1]
  if (!latest) return { name: name(1), terms: 0, isNew: true }
  if (latest.terms >= limit) return { name: name((typeof latest.number === 'number' ? latest.number : Number(latest.number.split(':')[1])) + 1), terms: 0, isNew: true }
  return { name: latest.name, terms: latest.terms, isNew: false }
}
