import type { ReactNode } from 'react'
import { cx } from '../lib/cx'

const TONES = {
  default: 'border-line bg-surface-2 text-muted',
  accent: 'border-accent-ink/25 bg-accent-ink/10 text-accent-ink',
}

export function Kbd({ children, className, tone = 'default' }: { children: ReactNode; className?: string; tone?: keyof typeof TONES }) {
  return (
    <kbd
      className={cx(
        'inline-flex h-5 min-w-5 items-center justify-center rounded-md border px-1.5 font-sans text-[11px] font-medium',
        TONES[tone],
        className,
      )}
    >
      {children}
    </kbd>
  )
}
