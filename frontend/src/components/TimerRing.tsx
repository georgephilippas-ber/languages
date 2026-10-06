import { useEffect, useState } from 'react'
import { cx } from '../lib/cx'

const RADIUS = 17
const CIRCUMFERENCE = 2 * Math.PI * RADIUS
const WARNING_MS = 10_000

export function TimerRing({ startedAt, frozenMs, limitMs }: { startedAt: number | null; frozenMs: number | null; limitMs: number }) {
  const [now, setNow] = useState(() => performance.now())

  useEffect(() => {
    if (frozenMs !== null || startedAt === null) return
    setNow(performance.now())
    const timer = window.setInterval(() => setNow(performance.now()), 200)
    return () => window.clearInterval(timer)
  }, [frozenMs, startedAt])

  const elapsed = frozenMs ?? (startedAt === null ? 0 : Math.max(0, now - startedAt))
  const remaining = limitMs - elapsed
  const over = remaining < 0
  const tone = over ? 'text-bad' : remaining <= WARNING_MS ? 'text-warn' : 'text-accent'
  const fraction = over ? 1 : remaining / limitMs
  const label = over ? `+${Math.floor(-remaining / 1000)}` : String(Math.ceil(remaining / 1000))

  return (
    <div
      role="timer"
      aria-label={over ? `${Math.floor(-remaining / 1000)} seconds over the time budget` : `${Math.ceil(remaining / 1000)} seconds left`}
      className={cx('relative flex size-11 shrink-0 items-center justify-center', tone, frozenMs !== null && 'opacity-70')}
    >
      <svg viewBox="0 0 40 40" className="absolute inset-0 -rotate-90">
        <circle cx="20" cy="20" r={RADIUS} fill="none" stroke="currentColor" strokeWidth="3" className="opacity-15" />
        <circle
          cx="20"
          cy="20"
          r={RADIUS}
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={CIRCUMFERENCE * (1 - fraction)}
          className="transition-[stroke-dashoffset] duration-200 ease-linear"
        />
      </svg>
      <span className="text-[13px] font-semibold tabular-nums">{label}</span>
    </div>
  )
}
