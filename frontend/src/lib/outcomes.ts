import { Check, Pencil, SkipForward, X, type LucideIcon } from 'lucide-react'
import type { Outcome } from '../types'

interface OutcomeStyle {
  icon: LucideIcon
  text: string
  soft: string
  solid: string
  edge: string
}

export const OUTCOME_STYLES: Record<Outcome, OutcomeStyle> = {
  correct: { icon: Check, text: 'text-good', soft: 'bg-good-soft', solid: 'bg-good', edge: 'border-l-good' },
  partial: { icon: Pencil, text: 'text-warn', soft: 'bg-warn-soft', solid: 'bg-warn', edge: 'border-l-warn' },
  wrong: { icon: X, text: 'text-bad', soft: 'bg-bad-soft', solid: 'bg-bad', edge: 'border-l-bad' },
  skipped: { icon: SkipForward, text: 'text-muted', soft: 'bg-surface-2', solid: 'bg-muted', edge: 'border-l-line' },
}
