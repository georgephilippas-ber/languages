import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import { ArrowLeft, CircleAlert, RotateCcw } from 'lucide-react'
import type { ExerciseInfo } from '../exercises/types'
import type { ExerciseRequest, LanguageInfo } from '../types'
import { filesLabel } from '../lib/files'
import { plural } from '../lib/format'
import { Button } from './Button'

export function LoadingCard({
  definition,
  request,
  language,
  startedAt,
  onCancel,
}: {
  definition: ExerciseInfo
  request: ExerciseRequest
  language: LanguageInfo
  startedAt: number
  onCancel: () => void
}) {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  const seconds = Math.max(0, Math.floor((now - startedAt) / 1000))
  const what = definition.kind === 'writing'
    ? `Picking ${plural(request.count, 'pair', 'pairs')} of words`
    : `Writing ${plural(request.count, definition.unit.one, definition.unit.other)} at ${request.level}`

  return (
    <div className="mx-auto max-w-3xl" aria-busy="true">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-3xl border border-line bg-surface p-6 shadow-sm sm:p-8"
      >
        <div className="space-y-3" aria-hidden>
          <div className="h-7 w-11/12 animate-pulse rounded-lg bg-surface-2" />
          <div className="h-7 w-3/4 animate-pulse rounded-lg bg-surface-2 [animation-delay:150ms]" />
        </div>
        <div className="mt-8 grid gap-3 sm:grid-cols-2" aria-hidden>
          {[0, 1, 2, 3].map((index) => (
            <div
              key={index}
              className="h-16 animate-pulse rounded-2xl bg-surface-2"
              style={{ animationDelay: `${200 + index * 120}ms` }}
            />
          ))}
        </div>
        <div className="mt-8 flex flex-wrap items-center gap-x-4 gap-y-3">
          <div role="status" className="min-w-0 flex-1">
            <p className="font-medium">{what}…</p>
            <p className="mt-0.5 text-sm text-muted">
              From {filesLabel(language, request.files)} · {seconds} s
            </p>
          </div>
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        </div>
      </motion.div>
    </div>
  )
}

export function ErrorCard({ title, message, onRetry, onBack }: { title: string; message: string; onRetry: () => void; onBack: () => void }) {
  return (
    <div className="mx-auto max-w-3xl">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        role="alert"
        className="rounded-3xl border border-line bg-surface p-6 shadow-sm sm:p-8"
      >
        <span className="flex size-11 items-center justify-center rounded-full bg-bad-soft text-bad">
          <CircleAlert aria-hidden className="size-5" />
        </span>
        <h2 className="mt-4 text-xl font-semibold tracking-tight">{title}</h2>
        <p className="mt-2 text-[15px] leading-relaxed text-muted">{message}</p>
        <div className="mt-6 flex flex-wrap gap-2">
          <Button icon={RotateCcw} onClick={onRetry}>
            Try again
          </Button>
          <Button variant="secondary" icon={ArrowLeft} onClick={onBack}>
            Back to settings
          </Button>
        </div>
      </motion.div>
    </div>
  )
}
