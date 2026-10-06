import type { Outcome } from '../types'
import { cx } from '../lib/cx'
import { OUTCOME_STYLES } from '../lib/outcomes'

export function ProgressBar({ outcomes, current }: { outcomes: (Outcome | null)[]; current: number }) {
  const done = outcomes.filter((outcome) => outcome !== null).length

  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={outcomes.length}
      aria-valuenow={done}
      aria-label={`${done} of ${outcomes.length} answered`}
      className="flex w-full items-center gap-1"
    >
      {outcomes.map((outcome, index) => (
        <span
          key={index}
          className={cx(
            'h-1.5 min-w-1 flex-1 rounded-full transition-colors duration-300',
            outcome ? OUTCOME_STYLES[outcome].solid : index === current ? 'bg-accent' : 'bg-line',
            outcome === null && index === current && 'animate-pulse',
          )}
        />
      ))}
    </div>
  )
}
