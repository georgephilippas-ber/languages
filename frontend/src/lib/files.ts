import type { FileSelection, LanguageInfo } from '../types'

export function selectedFiles(language: LanguageInfo, selection: FileSelection) {
  if (selection === 'all') return language.files
  const numbers = selection === 'latest' ? language.latest : [selection]
  return language.files.filter((file) => numbers.includes(file.number))
}

export function filesLabel(language: LanguageInfo, selection: FileSelection): string {
  if (selection === 'all') return `all ${language.name} files`
  const names = selectedFiles(language, selection).map((file) => file.name)
  return names.length ? names.join(' and ') : 'no files'
}

export function termCount(language: LanguageInfo, selection: FileSelection): number {
  return selectedFiles(language, selection).reduce((total, file) => total + file.terms, 0)
}

export function validSelection(language: LanguageInfo, selection: FileSelection): FileSelection {
  return typeof selection === 'number' && !language.files.some((file) => file.number === selection) ? 'latest' : selection
}
