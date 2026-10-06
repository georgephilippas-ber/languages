import { motion } from 'motion/react'
import type { Outcome } from '../types'
import { cx } from '../lib/cx'
import { OUTCOME_STYLES } from '../lib/outcomes'

export function VerdictBanner({ outcome, label }: { outcome: Outcome; label: string }) {
  const style = OUTCOME_STYLES[outcome]
  const Icon = style.icon

  return (
    <div className="flex items-center gap-3">
      <motion.span
        initial={{ scale: 0.4, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 500, damping: 22 }}
        className={cx('flex size-9 items-center justify-center rounded-full text-white dark:text-bg', style.solid)}
      >
        <Icon aria-hidden className="size-5" strokeWidth={2.75} />
      </motion.span>
      <span className={cx('text-lg font-semibold tracking-tight', style.text)}>{label}</span>
    </div>
  )
}
