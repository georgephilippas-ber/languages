export interface DiffPart {
  kind: 'same' | 'removed' | 'added'
  text: string
}

function diffTokens(before: string[], after: string[]): DiffPart[] {
  const table = Array.from({ length: before.length + 1 }, () => new Array<number>(after.length + 1).fill(0))
  for (let i = before.length - 1; i >= 0; i--) {
    for (let j = after.length - 1; j >= 0; j--) {
      table[i][j] = before[i] === after[j] ? table[i + 1][j + 1] + 1 : Math.max(table[i + 1][j], table[i][j + 1])
    }
  }

  const parts: DiffPart[] = []
  const push = (kind: DiffPart['kind'], text: string) => {
    const last = parts[parts.length - 1]
    if (last && last.kind === kind) last.text += text
    else parts.push({ kind, text })
  }

  let i = 0
  let j = 0
  while (i < before.length && j < after.length) {
    if (before[i] === after[j]) {
      push('same', before[i])
      i++
      j++
    } else if (table[i + 1][j] >= table[i][j + 1]) {
      push('removed', before[i++])
    } else {
      push('added', after[j++])
    }
  }
  while (i < before.length) push('removed', before[i++])
  while (j < after.length) push('added', after[j++])
  return parts
}

export function diffWords(before: string, after: string): DiffPart[] {
  const split = (text: string) => text.match(/\s+|[^\s]+/g) ?? []
  return diffTokens(split(before), split(after))
}

export function diffCharacters(before: string, after: string): DiffPart[] {
  return diffTokens(Array.from(before), Array.from(after))
}
