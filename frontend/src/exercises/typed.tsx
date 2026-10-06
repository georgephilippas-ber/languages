import { useEffect, useRef, useState } from 'react'
import { ArrowRight, BookOpen, Check, Keyboard, Lightbulb, LoaderCircle } from 'lucide-react'
import { api } from '../api'
import { cx } from '../lib/cx'
import { diffCharacters } from '../lib/diff'
import { collapseSpaces, letter } from '../lib/format'
import { insertAtCursor } from '../lib/input'
import type { TypedCorrection, TypedQuestion } from '../types'
import { AccentKeys } from '../components/AccentKeys'
import { Button } from '../components/Button'
import { DiffText } from '../components/DiffText'
import { Notice } from '../components/Notice'
import { Filled, Sentence } from '../components/Sentence'
import { Section } from '../components/Section'
import type { ExerciseDefinition, FeedbackProps, QuestionProps } from './types'

const TONES = { correct: 'good', partial: 'warn', wrong: 'bad', skipped: 'bad' } as const

function TypedQuestionView({ item, record, pending, language, onSubmit }: QuestionProps<TypedQuestion, string, TypedCorrection>) {
  const [value, setValue] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!record) inputRef.current?.focus()
  }, [record])

  const submit = () => {
    const answer = collapseSpaces(value)
    if (answer && !pending) onSubmit(answer)
  }

  return (
    <div>
      <Sentence text={item.question}>
        {record ? (
          <Filled tone={TONES[record.outcome]}>{record.answer}</Filled>
        ) : (
          <input
            ref={inputRef}
            value={value}
            disabled={pending}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault()
                submit()
              }
            }}
            aria-label="Your answer"
            autoComplete="off"
            autoCapitalize="off"
            autoCorrect="off"
            spellCheck={false}
            style={{ width: `${Math.min(Math.max(6, value.length + 1.5), 28)}ch` }}
            className="serif-text mx-1 inline-block max-w-full rounded-lg border-0 border-b-[3px] border-accent bg-accent-soft/70 px-1.5 py-0 text-[length:inherit] leading-[inherit] text-ink caret-accent outline-none transition-[width] duration-100 focus:bg-accent-soft disabled:opacity-70"
          />
        )}
      </Sentence>

      <div className="mt-7">
        <p className="mb-2.5 text-[11px] font-semibold uppercase tracking-[0.09em] text-muted">
          Choices · {language.supportLanguage}
        </p>
        <ul className="grid gap-2 sm:grid-cols-2">
          {item.choicesTranslations.map((translation, index) => (
            <li key={index} className="flex items-center gap-2.5 rounded-xl border border-line bg-surface px-3 py-2 text-[15px]">
              <span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-surface-2 text-[11px] font-semibold text-muted">
                {letter(index)}
              </span>
              {translation}
            </li>
          ))}
        </ul>
      </div>

      {!record && (
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
          <AccentKeys code={language.code} disabled={pending} onInsert={(text) => insertAtCursor(inputRef.current, value, text, setValue)} />
          <Button
            className="ml-auto"
            onClick={submit}
            disabled={!collapseSpaces(value) || pending}
            icon={pending ? LoaderCircle : undefined}
            spinning={pending}
            shortcut={pending ? undefined : '↵'}
          >
            {pending ? 'Checking' : 'Check'}
          </Button>
        </div>
      )}
    </div>
  )
}

function TypedFeedbackView({ item, answer, feedback }: FeedbackProps<TypedQuestion, string, TypedCorrection>) {
  const correct = feedback.verdict === 'correct'
  const parts = diffCharacters(answer, feedback.correctedAnswer)

  return (
    <div className="space-y-5">
      {!correct && (
        <Section label="Your answer">
          <span className="serif-text flex flex-wrap items-center gap-x-3 gap-y-1 text-xl">
            {feedback.verdict === 'wrong_form' ? (
              <>
                <DiffText parts={parts} show="before" />
                <ArrowRight aria-label="corrected to" className="size-4 text-muted" />
                <DiffText parts={parts} show="after" />
              </>
            ) : (
              <>
                <del className="text-bad decoration-bad/60 decoration-2">{answer}</del>
                <ArrowRight aria-label="corrected to" className="size-4 text-muted" />
                <span className="text-good">{feedback.correctedAnswer}</span>
              </>
            )}
          </span>
        </Section>
      )}
      {feedback.correctedAnswer.trim() !== item.correctAnswer.trim() && (
        <Section label="Expected">
          <span className="serif-text text-lg">{item.correctAnswer}</span>
        </Section>
      )}
      <Section label="Sentence">
        <span className="serif-text text-lg">{item.completeSentence}</span>
      </Section>
      <Section label="Translation">{item.englishTranslation}</Section>

      <Section label="Choices">
        <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line">
          {item.choices.map((choice, index) => (
            <li
              key={index}
              className={cx('flex items-center gap-3 px-3 py-2', index === item.correctChoice ? 'bg-good-soft' : 'bg-surface')}
            >
              <span className="flex size-6 shrink-0 items-center justify-center rounded-md text-[11px] font-semibold text-muted">
                {index === item.correctChoice ? <Check aria-label="correct" className="size-4 text-good" strokeWidth={3} /> : letter(index)}
              </span>
              <span className={cx('serif-text', index === item.correctChoice ? 'text-good' : 'text-ink')}>{choice}</span>
              <span className="ml-auto text-right text-sm text-muted">{item.choicesTranslations[index]}</span>
            </li>
          ))}
        </ul>
      </Section>

      {!correct && feedback.errors.length > 0 && (
        <Section label="Errors">
          <ul className="space-y-2.5">
            {feedback.errors.map((error, index) => (
              <li key={index}>
                <span className="serif-text">
                  <span className="text-bad">{error.original}</span> <span className="text-muted">→</span>{' '}
                  <span className="text-good">{error.corrected}</span>
                </span>
                {error.explanation && <p className="mt-0.5 text-[14px] text-muted">{error.explanation}</p>}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {feedback.comment && <p className="text-[15px] leading-relaxed">{feedback.comment}</p>}

      {feedback.suggestions.length > 0 && (
        <Section label="Suggestions" icon={Lightbulb}>
          <ul className="space-y-1.5">
            {feedback.suggestions.map((suggestion, index) => (
              <li key={index} className="flex gap-2">
                <span aria-hidden className="mt-2.5 size-1 shrink-0 rounded-full bg-accent" />
                <span>{suggestion}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      <Section label="Term" icon={BookOpen}>
        <span className="serif-text">{item.term}</span>
      </Section>

      {feedback.notice && <Notice>{feedback.notice}</Notice>}
    </div>
  )
}

export const typedExercise: ExerciseDefinition<TypedQuestion, string, TypedCorrection> = {
  kind: 'typed',
  path: '/typed',
  step: 2,
  verb: 'Produce',
  name: 'Typed quiz',
  description: 'The choices are shown only by meaning. Type the word yourself, in the exact form the sentence needs.',
  icon: Keyboard,
  timed: true,
  usesLevel: true,
  revisable: true,
  skippable: false,
  unit: { one: 'question', other: 'questions' },
  scoreLabel: 'correct',
  outcomeLabels: { correct: 'Correct', partial: 'Right word, wrong form', wrong: 'Incorrect' },
  keyHints: [
    [['↵'], 'check, then next'],
    [['Esc'], 'end'],
  ],
  defaultCount: (meta) => meta.defaults.questions,
  emptyAnswer: '',
  generate: async (request, signal) => {
    const set = await api.typed(request, signal)
    return { items: set.questions, source: set.source }
  },
  check: (item, answer, request, signal) => api.typedCheck(request.language, item, answer, signal),
  outcome: (feedback) => (feedback.verdict === 'correct' ? 'correct' : feedback.verdict === 'wrong_form' ? 'partial' : 'wrong'),
  speech: (item) => item.completeSentence,
  review: (item, record) => ({
    sentence: item.completeSentence,
    yours: record.answer,
    correct: record.outcome === 'correct' ? undefined : record.feedback?.correctedAnswer ?? item.correctAnswer,
    term: item.term,
  }),
  Question: TypedQuestionView,
  Feedback: TypedFeedbackView,
}
