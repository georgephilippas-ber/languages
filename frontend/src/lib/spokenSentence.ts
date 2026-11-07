/** Find the spoken words occupying a sentence blank without using the correct answer. */
export function extractSpokenAnswer(question: string, transcript: string): string | null {
  const parts = question.split(/_{3,}/)
  if (parts.length !== 2) return null
  const tokenize = (text: string) => Array.from(text.matchAll(/[\p{L}\p{M}\p{N}]+/gu),
    (match) => ({ text: match[0].normalize('NFKC').toLocaleLowerCase().replace(/’/g, "'"), start: match.index, end: match.index + match[0].length }))
  const before = tokenize(parts[0]).map((item) => item.text)
  const after = tokenize(parts[1]).map((item) => item.text)
  const heard = tokenize(transcript)
  if (!heard.length || (!before.length && !after.length)) return null
  const matches = (at: number, words: string[]) => words.every((word, index) => heard[at + index]?.text === word)
  const starts = before.length ? heard.flatMap((_, index) => matches(index, before) ? [index + before.length] : []) : [0]
  const ends = after.length ? heard.flatMap((_, index) => matches(index, after) ? [index] : []) : [heard.length]
  const candidates = starts.flatMap((start) => ends.filter((end) => end > start).map((end) => ({ start, end })))
  if (candidates.length !== 1) return null
  const { start, end } = candidates[0]
  return transcript.slice(heard[start].start, heard[end - 1].end).trim() || null
}
