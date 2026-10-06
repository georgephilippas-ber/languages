import type { ReactNode } from 'react'
import { cx } from '../lib/cx'

const BLANK = /_{3,}/

export function Sentence({ text, children, className }: { text: string; children: ReactNode; className?: string }) {
  const match = BLANK.exec(text)
  const before = match ? text.slice(0, match.index) : `${text} `
  const after = match ? text.slice(match.index + match[0].length) : ''

  return (
    <p
      className={cx(
        'serif-text text-pretty text-[1.6rem] leading-[1.5] tracking-[-0.01em] text-ink sm:text-[2rem] sm:leading-[1.45]',
        className,
      )}
    >
      {before}
      {children}
      {after}
    </p>
  )
}

export function Gap() {
  return (
    <span
      role="img"
      aria-label="blank"
      className="mx-1 inline-block w-[4.5ch] translate-y-[0.12em] border-b-[3px] border-dashed border-accent/55"
    >
      &nbsp;
    </span>
  )
}

const TONES = {
  good: 'bg-good-soft text-good',
  warn: 'bg-warn-soft text-warn',
  bad: 'bg-bad-soft text-bad',
}

export function Filled({ tone, children }: { tone: keyof typeof TONES; children: ReactNode }) {
  return <span className={cx('mx-0.5 rounded-lg px-1.5 py-0.5 [box-decoration-break:clone]', TONES[tone])}>{children}</span>
}
