export function validIsbn(value: string): boolean {
  if (!value.trim()) return true
  if (!/^[\dXx\s-]+$/.test(value)) return false
  const isbn = value.replace(/[\s-]/g, '').toUpperCase()
  if (/^(?:978|979)\d{10}$/.test(isbn)) return [...isbn].reduce((sum, digit, index) => sum + Number(digit) * (index % 2 ? 3 : 1), 0) % 10 === 0
  if (/^\d{9}[\dX]$/.test(isbn)) return [...isbn].reduce((sum, digit, index) => sum + (digit === 'X' ? 10 : Number(digit)) * (10 - index), 0) % 11 === 0
  return false
}

export function bookFieldsProblem(value: { title: string; language: string; isbn: string }, previousIsbn?: string): string | null {
  if (!value.title.trim()) return 'Enter a title.'
  if (!value.language.trim()) return 'Enter a language.'
  if (!validIsbn(value.isbn) && (previousIsbn === undefined || value.isbn.trim() !== previousIsbn.trim())) return 'Enter a valid ISBN-10 or ISBN-13, or leave it blank.'
  return null
}
