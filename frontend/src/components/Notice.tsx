import type { ReactNode } from 'react'
import { CircleAlert, Info } from 'lucide-react'
import { cx } from '../lib/cx'

export function Notice({ tone = 'info', children, action }: { tone?: 'info' | 'error'; children: ReactNode; action?: ReactNode }) {
  const Icon = tone === 'error' ? CircleAlert : Info

  return (
    <div
      role={tone === 'error' ? 'alert' : 'status'}
      className={cx(
        'flex items-start gap-3 rounded-xl px-4 py-3 text-sm leading-relaxed',
        tone === 'error' ? 'bg-bad-soft text-bad' : 'bg-surface-2 text-muted',
      )}
    >
      <Icon aria-hidden className="mt-0.5 size-4 shrink-0" />
      <div className="flex-1">{children}</div>
      {action}
    </div>
  )
}
