import type { Category, FileSelection, LanguageCode, LanguageInfo } from '../types'

export const categoryLabels: Record<Category, string> = {
  general: 'General', legal: 'Legal', financial: 'Financial', 'phrasal-verbs': 'Phrasal Verbs',
}

export function categoriesFor(code: LanguageCode): Category[] {
  return code === 'EN' ? ['general', 'legal', 'financial', 'phrasal-verbs'] : ['general', 'legal', 'financial']
}

export function selectedFiles(language: LanguageInfo, selection: FileSelection) {
  if (selection === 'all') return language.files
  if (selection === 'general' || selection === 'legal' || selection === 'financial' || selection === 'phrasal-verbs') return language.files.filter((file) => selection === 'general' ? typeof file.number === 'number' : typeof file.number === 'string' && file.number.startsWith(`${selection}:`))
  if (selection === 'current') return language.files.filter((file) => typeof file.number === 'number').slice(-1)
  const numbers = selection === 'latest' ? language.latest : [selection]
  return language.files.filter((file) => numbers.some((number) => number === file.number))
}

export function filesLabel(language: LanguageInfo, selection: FileSelection): string {
  if (selection === 'all') return `all ${language.name} files`
  if (selection === 'general' || selection === 'legal' || selection === 'financial' || selection === 'phrasal-verbs') return `${categoryLabels[selection]} ${language.name} files`
  const names = selectedFiles(language, selection).map((file) => file.name)
  return names.length ? names.join(' and ') : 'no files'
}

export function termCount(language: LanguageInfo, selection: FileSelection): number {
  return selectedFiles(language, selection).reduce((total, file) => total + file.terms, 0)
}

export function validSelection(language: LanguageInfo, selection: FileSelection, fallback: 'latest' | 'all' = 'latest'): FileSelection {
  if (selection === 'latest' || selection === 'all' || selection === 'current') return selection
  if (typeof selection === 'string' && selection in categoryLabels) {
    return categoriesFor(language.code).includes(selection as Category) ? selection : fallback
  }
  return language.files.some((file) => file.number === selection) ? selection : fallback
}
