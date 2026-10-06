import type { EntryKind, FileInfo, LanguageInfo } from '../types'

export const ENTRY_KINDS: { kind: EntryKind; label: string; one: string }[] = [
  { kind: 'vocabulary', label: 'Vocabulary', one: 'term' },
  { kind: 'idioms', label: 'Idioms', one: 'idiom' },
  { kind: 'grammatical', label: 'Constructions', one: 'construction' },
]

export const KIND_FOLDERS: Record<EntryKind, string> = {
  vocabulary: 'vocabulary',
  idioms: 'expressions/idioms',
  grammatical: 'expressions/grammatical',
}

export function kindFiles(language: LanguageInfo, kind: EntryKind): FileInfo[] {
  return kind === 'vocabulary' ? language.files : language[kind]
}

export function fileName(language: LanguageInfo, number: number): string {
  return `${language.name.toLowerCase()}-${number}.md`
}

export interface Target {
  name: string
  terms: number
  isNew: boolean
}

export function targetFile(language: LanguageInfo, kind: EntryKind, limit: number): Target {
  const files = kindFiles(language, kind)
  const latest = files[files.length - 1]
  if (!latest) return { name: fileName(language, 1), terms: 0, isNew: true }
  if (latest.terms >= limit) return { name: fileName(language, latest.number + 1), terms: 0, isNew: true }
  return { name: latest.name, terms: latest.terms, isNew: false }
}
