import type { ComponentType } from 'react'
import type { LucideIcon } from 'lucide-react'
import type { ExerciseKind, ExerciseRequest, LanguageInfo, Meta, Outcome } from '../types'

export interface ItemRecord<A, F> {
  answer: A
  feedback: F | null
  outcome: Outcome
  timeMs: number | null
  gaveUp?: boolean
}

export interface QuestionProps<I, A, F> {
  item: I
  record: ItemRecord<A, F> | null
  pending: boolean
  language: LanguageInfo
  onSubmit: (answer: A) => void
  onSkip: () => void
  onGiveUp?: () => void
}

export interface FeedbackProps<I, A, F> {
  item: I
  answer: A
  feedback: F
  gaveUp: boolean
  language: LanguageInfo
}

export interface ReviewEntry {
  sentence: string
  yours: string
  correct?: string
  correctLabel?: string
  term?: string
}

export interface ExerciseInfo {
  kind: ExerciseKind
  path: string
  step: number
  verb: string
  name: string
  description: string
  icon: LucideIcon
  timed: boolean
  usesLevel: boolean
  revisable: boolean
  skippable: boolean
  unit: { one: string; other: string }
  scoreLabel: string
  outcomeLabels: Partial<Record<Outcome, string>>
  keyHints: [string[], string][]
  defaultCount: (meta: Meta) => number
}

export interface ExerciseDefinition<I, A, F> extends ExerciseInfo {
  emptyAnswer: A
  generate: (request: ExerciseRequest, signal: AbortSignal) => Promise<{ items: I[]; source: string }>
  check: (item: I, answer: A, request: ExerciseRequest, signal: AbortSignal) => Promise<F>
  outcome: (feedback: F) => Outcome
  giveUp?: (item: I) => F
  speech: (item: I, feedback: F) => string
  review: (item: I, record: ItemRecord<A, F>) => ReviewEntry
  Question: ComponentType<QuestionProps<I, A, F>>
  Feedback: ComponentType<FeedbackProps<I, A, F>>
}
