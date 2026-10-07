import { motion } from 'motion/react'
import { House, RotateCcw, Settings2, Timer, Trophy } from 'lucide-react'
import { useNavigate } from 'react-router'
import type { ExerciseDefinition, ItemRecord } from '../exercises/types'
import { cx } from '../lib/cx'
import { formatDuration, plural } from '../lib/format'
import { OUTCOME_STYLES } from '../lib/outcomes'
import type { Meta, Outcome } from '../types'
import { Button } from './Button'
import { ScoreRing } from './ScoreRing'

const OUTCOME_ORDER: Outcome[] = ['correct', 'partial', 'wrong', 'skipped']

interface FinishedSession<I, A, F> {
  source: string
  items: I[]
  records: (ItemRecord<A, F> | null)[]
}

function headline(score: number, answered: number): string {
  if (!answered) return 'Nothing answered'
  if (score === 1) return 'Perfect score'
  if (score >= 0.8) return 'Excellent'
  if (score >= 0.6) return 'Well done'
  if (score >= 0.4) return 'Getting there'
  return 'Keep practising'
}

export function ResultsView<I, A, F>({
  definition,
  session,
  meta,
  onAgain,
  onSettings,
}: {
  definition: ExerciseDefinition<I, A, F>
  session: FinishedSession<I, A, F>
  meta: Meta
  onAgain: () => void
  onSettings: () => void
}) {
  const navigate = useNavigate()
  const records = session.records.flatMap((record) => (record ? [record] : []))
  const counted = records.filter((record) => record.outcome !== 'skipped')
  const correct = counted.filter((record) => record.outcome === 'correct').length
  const score = counted.length ? correct / counted.length : 0
  const timed = counted.filter((record) => record.timeMs !== null)
  const spent = timed.reduce((total, record) => total + (record.timeMs ?? 0), 0)
  const allotted = timed.length * meta.defaults.secondsPerQuestion * 1000
  const under = spent <= allotted
  const unanswered = session.items.length - records.length

  return (
    <div className="mx-auto max-w-3xl">
      <motion.section
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className="rounded-3xl border border-line bg-surface p-6 shadow-sm sm:p-8"
      >
        <div className="flex flex-col items-center gap-6 sm:flex-row">
          {counted.length > 0 ? <ScoreRing value={score} /> : null}
          <div className="min-w-0 text-center sm:text-left">
            <p className="text-sm font-medium text-accent">
              {definition.verb} · {definition.name}
            </p>
            <h1 className="serif-text mt-1 flex items-center justify-center gap-2 text-3xl tracking-tight sm:justify-start sm:text-4xl">
              {score === 1 && counted.length > 0 && (
                <motion.span initial={{ rotate: -20, scale: 0.5 }} animate={{ rotate: 0, scale: 1 }} transition={{ type: 'spring', delay: 0.6 }}>
                  <Trophy aria-hidden className="size-8 text-warn" />
                </motion.span>
              )}
              {headline(score, counted.length)}
            </h1>
            <p className="mt-1.5 text-muted">
              {correct} of {counted.length} {definition.scoreLabel}
              {unanswered > 0 && ` · ended after ${records.length} of ${session.items.length}`}
            </p>
            <div className="mt-4 flex flex-wrap justify-center gap-2 sm:justify-start">
              {OUTCOME_ORDER.map((outcome) => {
                const label = definition.outcomeLabels[outcome]
                const count = records.filter((record) => record.outcome === outcome).length
                if (!label || !count) return null
                const style = OUTCOME_STYLES[outcome]
                return (
                  <span key={outcome} className={cx('rounded-full px-3 py-1 text-sm font-medium', style.soft, style.text)}>
                    {count} · {label}
                  </span>
                )
              })}
            </div>
          </div>
        </div>

        {definition.timed && timed.length > 0 && (
          <div className="mt-7 flex flex-wrap items-center gap-4 rounded-2xl bg-surface-2 p-4">
            <span className="flex size-10 items-center justify-center rounded-xl bg-surface text-muted">
              <Timer aria-hidden className="size-5" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="font-medium tabular-nums">
                {formatDuration(spent)} <span className="font-normal text-muted">of {formatDuration(allotted)} allotted</span>
              </p>
              <p className="text-sm text-muted">
                {timed.length} × {meta.defaults.secondsPerQuestion} s · {formatDuration(spent / timed.length)} on average
              </p>
            </div>
            <span className={cx('rounded-full px-3 py-1 text-sm font-semibold tabular-nums', under ? 'bg-good-soft text-good' : 'bg-bad-soft text-bad')}>
              {formatDuration(allotted - spent)} {under ? 'under' : 'over'}
            </span>
          </div>
        )}

        <div className="mt-7 flex flex-wrap gap-2">
          <Button icon={RotateCcw} onClick={onAgain}>
            Again
          </Button>
          <Button variant="secondary" icon={Settings2} onClick={onSettings}>
            New settings
          </Button>
          <Button variant="ghost" icon={House} onClick={() => navigate('/')}>
            Home
          </Button>
        </div>
      </motion.section>

      <section className="mt-10">
        <h2 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.09em] text-muted">
          Review · {plural(session.items.length, definition.unit.one, definition.unit.other)} from {session.source}
        </h2>
        <ol className="space-y-2.5">
          {session.items.map((item, index) => {
            const record = session.records[index]
            if (!record) {
              return (
                <li key={index} className="rounded-2xl border border-dashed border-line px-4 py-3 text-sm text-muted">
                  {index + 1}. Not answered
                </li>
              )
            }
            const entry = definition.review(item, record)
            const style = OUTCOME_STYLES[record.outcome]
            const Icon = style.icon
            return (
              <motion.li
                key={index}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(index * 0.04, 0.6) }}
                className="flex gap-3 rounded-2xl border border-line bg-surface p-4"
              >
                <span className={cx('mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full', style.soft, style.text)}>
                  <Icon aria-label={definition.outcomeLabels[record.outcome] ?? record.outcome} className="size-4" strokeWidth={2.75} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="serif-text text-[17px] leading-snug">{entry.sentence}</p>
                  <p className="mt-1.5 text-sm leading-relaxed">
                    <span className="text-muted">You: </span>
                    <span className={cx(record.outcome === 'correct' ? 'text-good' : record.outcome === 'skipped' || record.gaveUp ? 'text-muted' : style.text)}>
                      {entry.yours}
                    </span>
                    {entry.correct && (
                      <>
                        <span className="text-muted"> · {entry.correctLabel ?? 'Correct'}: </span>
                        <span className="text-good">{entry.correct}</span>
                      </>
                    )}
                  </p>
                  {entry.term && <p className="mt-1 truncate text-xs text-muted">{entry.term}</p>}
                </div>
                {record.timeMs !== null && (
                  <span
                    className={cx(
                      'shrink-0 text-xs tabular-nums',
                      record.timeMs > meta.defaults.secondsPerQuestion * 1000 ? 'text-bad' : 'text-muted',
                    )}
                  >
                    {Math.round(record.timeMs / 1000)} s
                  </span>
                )}
              </motion.li>
            )
          })}
        </ol>
      </section>
    </div>
  )
}
