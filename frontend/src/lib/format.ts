export function formatDuration(ms: number): string {
  const seconds = Math.round(Math.abs(ms) / 1000)
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

export function plural(count: number, one: string, other: string): string {
  return `${count} ${count === 1 ? one : other}`
}

export function letter(index: number): string {
  return String.fromCharCode(65 + index)
}

export function collapseSpaces(text: string): string {
  return text.split(/\s+/).filter(Boolean).join(' ')
}
