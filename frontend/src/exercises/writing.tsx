import { useEffect, useRef, useState } from 'react'
import { Check, LoaderCircle, PenLine, SkipForward, Sparkles, X } from 'lucide-react'
import { api } from '../api'
import { cx } from '../lib/cx'
import { diffWords } from '../lib/diff'
import { insertAtCursor } from '../lib/input'
import type { WritingCorrection, WritingTerm } from '../types'
import { AccentKeys } from '../components/AccentKeys'
import { Button } from '../components/Button'
import { DiffText } from '../components/DiffText'
import { Section } from '../components/Section'
import type { ExerciseDefinition, FeedbackProps, QuestionProps } from './types'

function WritingQuestionView({ item, record, pending, language, onSubmit, onSkip }: QuestionProps<WritingTerm[], string, WritingCorrection>) {
  const [value, setValue] = useState('')
  const textRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!record) textRef.current?.focus()
  }, [record])

  const submit = () => {
    const sentence = value.trim()
    if (sentence && !pending) onSubmit(sentence)
  }

  return (
    <div>
      <p className="text-[15px] text-muted">
        Write one sentence in {language.name} that uses both of these words, in any form.
      </p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {item.map((term) => (
          <div key={term.term} className="rounded-2xl border border-line bg-surface p-4 shadow-sm">
            <p className="serif-text text-xl leading-snug text-ink">{term.term}</p>
            {term.hint && <p className="mt-1.5 text-sm text-muted">{term.hint}</p>}
            <p className="mt-3 text-[11px] font-medium uppercase tracking-[0.09em] text-muted/80">{term.fileName}</p>
          </div>
        ))}
      </div>

      {record ? (
        <blockquote className="serif-text mt-6 border-l-[3px] border-line pl-4 text-xl leading-relaxed text-muted">
          {record.answer || 'Skipped.'}
        </blockquote>
      ) : (
        <>
          <textarea
            ref={textRef}
            value={value}
            disabled={pending}
            rows={3}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                submit()
              }
            }}
            placeholder="Your sentence…"
            aria-label="Your sentence"
            spellCheck={false}
            className="serif-text mt-6 block w-full resize-y rounded-2xl border border-line bg-surface px-4 py-3 text-xl leading-relaxed text-ink shadow-sm outline-none transition placeholder:text-muted/60 focus:border-accent focus:ring-4 focus:ring-accent/15 disabled:opacity-70"
          />
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <AccentKeys code={language.code} disabled={pending} onInsert={(text) => insertAtCursor(textRef.current, value, text, setValue)} />
            <div className="ml-auto flex gap-2">
              <Button variant="ghost" icon={SkipForward} onClick={onSkip} disabled={pending}>
                Skip
              </Button>
              <Button
                onClick={submit}
                disabled={!value.trim() || pending}
                icon={pending ? LoaderCircle : undefined}
                spinning={pending}
                shortcut={pending ? undefined : '↵'}
              >
                {pending ? 'Correcting' : 'Check'}
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function WritingFeedbackView({ answer, feedback }: FeedbackProps<WritingTerm[], string, WritingCorrection>) {
  const changed = feedback.minimalCorrection.trim() !== answer.trim()
  const parts = diffWords(answer, feedback.minimalCorrection)
  const naturalDiffers = feedback.naturalVersion.trim() !== feedback.minimalCorrection.trim()

  return (
    <div className="space-y-5">
      <Section label="Yours">
        <span className="serif-text text-lg">{changed ? <DiffText parts={parts} show="before" /> : answer}</span>
      </Section>
      {changed && (
        <Section label="Minimal fix">
          <span className="serif-text text-lg">
            <DiffText parts={parts} show="after" />
          </span>
        </Section>
      )}
      <Section label="Natural" icon={Sparkles}>
        {naturalDiffers ? (
          <span className="serif-text text-lg text-good">{feedback.naturalVersion}</span>
        ) : (
          <span className="text-muted">Already natural.</span>
        )}
      </Section>
      {naturalDiffers && feedback.naturalExplanation && <Section label="Why the natural version">{feedback.naturalExplanation}</Section>}
      {feedback.translation && <Section label="Translation">{feedback.translation}</Section>}

      <Section label="Words">
        <ul className="space-y-2.5">
          {feedback.terms.map((check) => {
            const fine = check.used && check.usedCorrectly
            const Icon = fine ? Check : check.used ? PenLine : X
            return (
              <li key={check.term} className="flex gap-3">
                <span
                  className={cx(
                    'mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full',
                    fine ? 'bg-good-soft text-good' : check.used ? 'bg-warn-soft text-warn' : 'bg-bad-soft text-bad',
                  )}
                >
                  <Icon aria-hidden className="size-3.5" strokeWidth={3} />
                </span>
                <div>
                  <p>
                    <span className="serif-text">{check.term}</span>
                    <span className="text-muted"> · {fine ? 'used correctly' : check.used ? 'used, but not quite right' : 'not used'}</span>
                  </p>
                  {!fine && check.comment && <p className="mt-0.5 text-[14px] text-muted">{check.comment}</p>}
                </div>
              </li>
            )
          })}
        </ul>
      </Section>

      {changed && feedback.corrections.length > 0 && (
        <Section label="Corrections">
          <ul className="space-y-2.5">
            {feedback.corrections.map((correction, index) => (
              <li key={index}>
                <span className="serif-text">
                  <span className="text-bad">{correction.original}</span> <span className="text-muted">→</span>{' '}
                  <span className="text-good">{correction.corrected}</span>
                </span>
                {correction.explanation && <p className="mt-0.5 text-[14px] text-muted">{correction.explanation}</p>}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {feedback.feedback && <p className="rounded-xl bg-surface-2 px-4 py-3 text-[15px] leading-relaxed">{feedback.feedback}</p>}
    </div>
  )
}

export const writingExercise: ExerciseDefinition<WritingTerm[], string, WritingCorrection> = {
  kind: 'writing',
  path: '/writing',
  step: 3,
  verb: 'Use',
  name: 'Writing',
  description: 'Two words, one sentence of your own. Get a minimal fix, a native-sounding version, and a check of each word.',
  icon: PenLine,
  timed: false,
  usesLevel: false,
  revisable: false,
  skippable: true,
  unit: { one: 'sentence', other: 'sentences' },
  scoreLabel: 'correct as written',
  outcomeLabels: { correct: 'Correct as written', partial: 'Corrected', skipped: 'Skipped' },
  keyHints: [
    [['↵'], 'check, then next'],
    [['⇧', '↵'], 'new line'],
    [['Esc'], 'end'],
  ],
  defaultCount: (meta) => meta.defaults.sentences,
  emptyAnswer: '',
  generate: async (request, signal) => {
    const set = await api.writing(request, signal)
    return { items: set.rounds, source: set.source }
  },
  check: (item, answer, request, signal) => api.writingCheck(request.language, item, answer, signal),
  outcome: (feedback) => (feedback.isCorrect ? 'correct' : 'partial'),
  speech: (_item, feedback) => feedback.naturalVersion,
  review: (item, record) => {
    const terms = item.map((term) => term.term).join(' · ')
    if (!record.feedback) return { sentence: terms, yours: 'Skipped' }
    const fixed = record.feedback.minimalCorrection.trim() !== record.answer.trim()
    return {
      sentence: record.feedback.naturalVersion,
      yours: record.answer,
      correct: fixed ? record.feedback.minimalCorrection : undefined,
      correctLabel: 'Fixed',
      term: terms,
    }
  },
  Question: WritingQuestionView,
  Feedback: WritingFeedbackView,
}
