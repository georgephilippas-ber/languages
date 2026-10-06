import { Fragment, type ReactNode } from 'react'

const BOLD = /\*\*(.+?)\*\*/gs
const ITALIC = /(?<![\p{L}\p{N}*])\*(?!\s)(.+?)(?<!\s)\*(?![\p{L}\p{N}*])/gsu

function split(text: string, pattern: RegExp, render: (inner: string, key: number) => ReactNode, rest: (part: string, key: number) => ReactNode): ReactNode[] {
  const nodes: ReactNode[] = []
  let last = 0
  let key = 0
  for (const match of text.matchAll(pattern)) {
    const index = match.index ?? 0
    if (index > last) nodes.push(rest(text.slice(last, index), key++))
    nodes.push(render(match[1], key++))
    last = index + match[0].length
  }
  if (last < text.length) nodes.push(rest(text.slice(last), key++))
  return nodes
}

function italics(text: string): ReactNode[] {
  return split(
    text,
    ITALIC,
    (inner, key) => (
      <em key={key} className="serif-text">
        {inner}
      </em>
    ),
    (part, key) => <Fragment key={key}>{part}</Fragment>,
  )
}

function inline(text: string): ReactNode[] {
  return split(
    text,
    BOLD,
    (inner, key) => (
      <strong key={key} className="font-semibold">
        {italics(inner)}
      </strong>
    ),
    (part, key) => <Fragment key={key}>{italics(part)}</Fragment>,
  )
}

export function Rich({ text }: { text: string }) {
  const paragraphs = text.split(/\n\s*\n/).filter((paragraph) => paragraph.trim())
  return (
    <>
      {paragraphs.map((paragraph, index) => (
        <p key={index} className="[&+p]:mt-2">
          {paragraph.split('\n').map((line, position) => (
            <Fragment key={position}>
              {position > 0 && <br />}
              {inline(line.replace(/^[*-] /, '• '))}
            </Fragment>
          ))}
        </p>
      ))}
    </>
  )
}
