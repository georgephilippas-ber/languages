import { useState } from 'react'
import { BookOpen, Check, Flag, ListChecks, X } from 'lucide-react'
import { api } from '../api'
import { cx } from '../lib/cx'
import { letter } from '../lib/format'
import { hasModifier, isEditable, useKeydown } from '../hooks/useKeydown'
import type { QuizQuestion } from '../types'
import { Button } from '../components/Button'
import { DictationButton } from '../components/DictationButton'
import { Filled, Gap, Sentence } from '../components/Sentence'
import { Section } from '../components/Section'
import type { ExerciseDefinition, FeedbackProps, QuestionProps } from './types'

interface QuizFeedback {
  correct: boolean
}

const CHOICE_KEYS = ['1', '2', '3', '4', 'a', 'b', 'c', 'd']

function QuizQuestionView({ item, record, pending, language, onSubmit, onGiveUp }: QuestionProps<QuizQuestion, number, QuizFeedback>) {
  const answered = record !== null
  const [dictating, setDictating] = useState(false)
  const [spoken, setSpoken] = useState('')
  const normalize = (text: string) => text.normalize('NFKC').toLocaleLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim()
  const matches = item.choices.map((choice, index) => normalize(choice) === normalize(spoken) && normalize(spoken) ? index : -1).filter((index) => index >= 0)
  const spokenChoice = matches.length === 1 ? matches[0] : -1

  useKeydown((event) => {
    if (pending || dictating || hasModifier(event) || isEditable(event.target)) return
    const position = CHOICE_KEYS.indexOf(event.key.toLowerCase())
    if (position < 0) return
    const index = position % 4
    if (index < item.choices.length) {
      event.preventDefault()
      onSubmit(index)
    }
  }, !answered)

  return (
    <div>
      <Sentence text={item.question}>
        {answered ? <Filled tone="good">{item.choices[item.correctChoice]}</Filled> : <Gap />}
      </Sentence>

      <div className="mt-8 grid gap-3 sm:grid-cols-2">
        {item.choices.map((choice, index) => {
          const isCorrect = index === item.correctChoice
          const isChosen = record?.answer === index
          return (
            <button
              key={index}
              type="button"
              disabled={answered || pending || dictating}
              onClick={() => onSubmit(index)}
              className={cx(
                'group flex min-h-16 items-center gap-3 rounded-2xl border bg-surface px-4 py-3 text-left transition duration-200',
                !answered && 'cursor-pointer border-line shadow-sm hover:-translate-y-0.5 hover:border-accent/60 hover:shadow-md',
                answered && isCorrect && 'border-good bg-good-soft',
                answered && isChosen && !isCorrect && 'border-bad bg-bad-soft',
                answered && !isCorrect && !isChosen && 'border-line opacity-60',
              )}
            >
              <span
                className={cx(
                  'flex size-7 shrink-0 items-center justify-center rounded-lg text-xs font-semibold transition',
                  answered && isCorrect
                    ? 'bg-good text-white dark:text-bg'
                    : answered && isChosen
                      ? 'bg-bad text-white dark:text-bg'
                      : 'bg-surface-2 text-muted group-hover:bg-accent-soft group-hover:text-accent',
                )}
              >
                {answered && isCorrect ? (
                  <Check aria-label="correct" className="size-4" strokeWidth={3} />
                ) : answered && isChosen ? (
                  <X aria-label="your answer" className="size-4" strokeWidth={3} />
                ) : (
                  letter(index)
                )}
              </span>
              <span className="min-w-0">
                <span className="serif-text block text-lg leading-snug text-ink">{choice}</span>
                {answered && item.choicesTranslations[index] && (
                  <span lang="en" className="mt-0.5 block text-sm text-muted">{item.choicesTranslations[index]}</span>
                )}
              </span>
            </button>
          )
        })}
      </div>

      {!answered && <div className="mt-4">
        <DictationButton language={language.code} disabled={pending} label="Speak answer" onBusyChange={setDictating} onTranscript={(text) => setSpoken(text.trim())} />
        {spoken && <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
          <span className="text-muted">Heard: <span className="text-ink">{spoken}</span></span>
          {spokenChoice >= 0 ? <Button size="sm" variant="secondary" disabled={pending || dictating} onClick={() => onSubmit(spokenChoice)}>Choose {letter(spokenChoice)}: {item.choices[spokenChoice]}</Button>
            : <span role="status" className="text-muted">No single choice matched. Try again or select an answer.</span>}
        </div>}
      </div>}

      {!answered && onGiveUp && (
        <div className="mt-6 flex justify-end">
          <Button variant="ghost" icon={Flag} onClick={onGiveUp} disabled={pending || dictating}>
            I give up
          </Button>
        </div>
      )}
    </div>
  )
}

function QuizFeedbackView({ item, language }: FeedbackProps<QuizQuestion, number, QuizFeedback>) {
  return (
    <div className="space-y-5">
      <Section label="Sentence">
        <span className="serif-text text-lg">{item.completeSentence}</span>
      </Section>
      {item.englishTranslation.trim() && (language.code !== 'EN' ||
        item.englishTranslation.trim().toLocaleLowerCase() !== item.completeSentence.trim().toLocaleLowerCase()) && (
        <Section label={language.code === 'EN' ? 'Explanation' : 'Translation'}>{item.englishTranslation}</Section>
      )}
      {item.term && (
        <Section label="Term" icon={BookOpen}>
          <span className="serif-text">{item.term}</span>
        </Section>
      )}
    </div>
  )
}

export const quizExercise: ExerciseDefinition<QuizQuestion, number, QuizFeedback> = {
  kind: 'quiz',
  path: '/quiz',
  step: 1,
  verb: 'Recognise',
  name: 'Multiple choice',
  description: 'A fresh sentence with one blank and four choices. Spot the word that fits, then see every choice translated.',
  icon: ListChecks,
  timed: true,
  usesLevel: true,
  revisable: true,
  skippable: false,
  unit: { one: 'question', other: 'questions' },
  scoreLabel: 'correct',
  outcomeLabels: { correct: 'Correct', wrong: 'Incorrect' },
  keyHints: [
    [['1–4', 'A–D'], 'answer'],
    [['↵'], 'next'],
    [['Esc'], 'end'],
  ],
  defaultCount: (meta) => meta.defaults.questions,
  emptyAnswer: -1,
  generate: async (request, signal) => {
    const set = await api.quiz(request, signal)
    return { items: set.questions, source: set.source }
  },
  check: async (item, answer) => ({ correct: answer === item.correctChoice }),
  outcome: (feedback) => (feedback.correct ? 'correct' : 'wrong'),
  giveUp: () => ({ correct: false }),
  speech: (item) => item.completeSentence,
  review: (item, record) => ({
    sentence: item.completeSentence,
    yours: record.gaveUp ? 'Gave up' : item.choices[record.answer] ?? '',
    correct: record.outcome === 'correct' ? undefined : item.choices[item.correctChoice],
    term: item.term,
  }),
  Question: QuizQuestionView,
  Feedback: QuizFeedbackView,
}
