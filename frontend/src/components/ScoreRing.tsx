import { motion } from 'motion/react'
import { cx } from '../lib/cx'

const RADIUS = 54
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

export function ScoreRing({ value }: { value: number }) {
  const tone = value >= 0.8 ? 'text-good' : value >= 0.5 ? 'text-warn' : 'text-bad'

  return (
    <div className={cx('relative flex size-36 shrink-0 items-center justify-center', tone)}>
      <svg viewBox="0 0 128 128" className="absolute inset-0 -rotate-90">
        <circle cx="64" cy="64" r={RADIUS} fill="none" stroke="currentColor" strokeWidth="10" className="opacity-15" />
        <motion.circle
          cx="64"
          cy="64"
          r={RADIUS}
          fill="none"
          stroke="currentColor"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          initial={{ strokeDashoffset: CIRCUMFERENCE }}
          animate={{ strokeDashoffset: CIRCUMFERENCE * (1 - value) }}
          transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1], delay: 0.15 }}
        />
      </svg>
      <span className="text-4xl font-semibold tracking-tight tabular-nums text-ink">{Math.round(value * 100)}%</span>
    </div>
  )
}
