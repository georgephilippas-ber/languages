import type { Category, FileSelection, LanguageCode, LanguageInfo } from '../types'

export const categoryLabels: Record<Category, string> = {
  general: 'General', legal: 'Legal', financial: 'Financial', 'phrasal-verbs': 'Phrasal Verbs',
}

export function categoriesFor(code: LanguageCode): Category[] {
  return code === 'EN' ? ['general', 'legal', 'financial', 'phrasal-verbs'] : ['general', 'legal', 'financial']
}

export function selectionCategory(selection: FileSelection): Category | 'all' {
  if (selection === 'all') return 'all'
  if (typeof selection === 'number' || selection === 'latest' || selection === 'current') return 'general'
  return selection.split(':')[0] as Category
}

export function selectionScope(selection: FileSelection): 'latest' | 'current' | 'entire' | 'single' | 'all' {
  if (selection === 'all') return 'all'
  if (selection === 'latest' || selection === 'current') return selection
  if (typeof selection === 'number') return 'single'
  if (selection in categoryLabels) return 'entire'
  const suffix = selection.split(':')[1]
  return suffix === 'latest' || suffix === 'current' ? suffix : 'single'
}

export function selectedFiles(language: LanguageInfo, selection: FileSelection) {
  if (selection === 'all') return language.files
  const category = selectionCategory(selection)
  const scoped = language.files.filter((file) => category === 'general' ? typeof file.number === 'number' : typeof file.number === 'string' && file.number.startsWith(`${category}:`))
  const scope = selectionScope(selection)
  if (scope === 'entire') return scoped
  if (scope === 'latest') return scoped.slice(-2)
  if (scope === 'current') return scoped.slice(-1)
  return language.files.filter((file) => file.number === selection)
}

export function filesLabel(language: LanguageInfo, selection: FileSelection): string {
  if (selection === 'all') return `all ${language.name} categories`
  if (selectionScope(selection) === 'entire') return `${categoryLabels[selectionCategory(selection) as Category]} ${language.name} files`
  const names = selectedFiles(language, selection).map((file) => file.name)
  return names.length ? names.join(' and ') : 'no files'
}

export function termCount(language: LanguageInfo, selection: FileSelection): number {
  return selectedFiles(language, selection).reduce((total, file) => total + file.terms, 0)
}

export function validSelection(language: LanguageInfo, selection: FileSelection, fallback: 'latest' | 'all' = 'latest'): FileSelection {
  if (selection === 'latest' || selection === 'all' || selection === 'current') return selection
  const category = selectionCategory(selection)
  if (category === 'all' || !categoriesFor(language.code).includes(category)) return fallback
  const scope = selectionScope(selection)
  if (scope === 'entire' || scope === 'latest' || scope === 'current') return selection
  return language.files.some((file) => file.number === selection) ? selection : fallback
}


/** Old saved file scopes become category selections; new exercises default to all. */
export function exerciseSelection(selection: FileSelection): FileSelection {
  if (selection === 'all' || selection === 'latest' || selection === 'current' || typeof selection === 'number') return 'all'
  const category = selectionCategory(selection)
  return category === 'general' || category === 'legal' || category === 'financial' ? category : 'all'
}
