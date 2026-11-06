import { useRef, useState } from 'react'
import { ArrowRightLeft, Flag, Lightbulb } from 'lucide-react'
import { api } from '../api'
import { useMeta } from '../context/MetaContext'
import { useKeydown, hasModifier, isEditable } from '../hooks/useKeydown'
import { AccentKeys } from '../components/AccentKeys'
import { Button } from '../components/Button'
import { Section } from '../components/Section'
import { SpeakButton } from '../components/SpeakButton'
import { TranslationHint } from '../components/TranslationHint'
import { insertAtCursor } from '../lib/input'
import type { MixedQuestion, MixedCorrection } from '../types'
import type { ExerciseDefinition, FeedbackProps, QuestionProps } from './types'

const NAMES = { EN: 'English', DE: 'German', FR: 'French' } as const
const KEYS = ['1', '2', '3', '4', 'a', 'b', 'c', 'd']
type ChoiceFeedback = { correct: boolean }

function completed(item: MixedQuestion, answers: string[]) {
  return item.segments.map((part, index) => part + (answers[index] ?? '')).join('')
}

function Original({ item }: { item: MixedQuestion }) {
  return <div className="mb-7">
    <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">{NAMES[item.sourceLanguage]} sentence</p>
    <p lang={item.sourceLanguage.toLowerCase()} className="serif-text text-pretty text-xl leading-relaxed sm:text-2xl">{item.sourceSentence}</p>
    <SpeakButton text={item.sourceSentence} code={item.sourceLanguage} label={`Listen to ${NAMES[item.sourceLanguage]} sentence`} />
  </div>
}

function ChoiceQuestion({ item, record, pending, onSubmit, onGiveUp }: QuestionProps<MixedQuestion, number, ChoiceFeedback>) {
  useKeydown((event) => {
    if (pending || hasModifier(event) || isEditable(event.target)) return
    const position = KEYS.indexOf(event.key.toLowerCase())
    if (position >= 0 && position % 4 < item.choices.length) { event.preventDefault(); onSubmit(position % 4) }
  }, !record)
  return <div>
    <Original item={item} />
    <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">{NAMES[item.targetLanguage]} translation</p>
    <p lang={item.targetLanguage.toLowerCase()} className="serif-text text-xl leading-relaxed sm:text-2xl">{item.segments.map((part, index) => <span key={index}>{part}{index < item.answers.length && <span role={record ? undefined : 'img'} aria-label={record ? undefined : `Blank ${index + 1}`} className="mx-1 border-b-2 border-dashed border-accent px-3">{record ? item.answers[index] : '　'}</span>}</span>)}</p>
    <div className="mt-7 grid gap-3 sm:grid-cols-2">
      {item.choices.map((choice, index) => <button type="button" key={index} disabled={!!record || pending} onClick={() => onSubmit(index)}
        className={`rounded-2xl border px-4 py-3 text-left transition ${record && index === item.correctChoice ? 'border-good bg-good-soft' : record && index === record.answer ? 'border-bad bg-bad-soft' : 'border-line bg-surface hover:border-accent/60'}`}>
        <span className="mr-3 text-xs font-semibold text-muted">{String.fromCharCode(65 + index)}</span><span lang={item.targetLanguage.toLowerCase()} className="serif-text text-lg">{choice.join(' · ')}</span>
      </button>)}
    </div>
    {!record && onGiveUp && <div className="mt-6 flex justify-end"><Button variant="ghost" icon={Flag} onClick={onGiveUp}>I give up</Button></div>}
  </div>
}

function ProduceQuestion({ item, record, pending, onSubmit, onGiveUp, letterHint, onLetterHintChange, draft, onDraftChange }: QuestionProps<MixedQuestion, string[], MixedCorrection>) {
  const [values, setValues] = useState<string[]>(() => Array.isArray(draft) && draft.length === item.answers.length ? draft : item.answers.map(() => ''))
  const setAnswer = (index: number, next: string) => { const updated = values.map((value, i) => i === index ? next : value); setValues(updated); onDraftChange?.(updated) }
  const [active, setActive] = useState(0)
  const inputRefs = useRef<(HTMLInputElement | null)[]>([])
  const { languageInfo } = useMeta()
  const hint = letterHint ?? { uses: 0, revealed: [] }
  const chars = Array.from(item.answers.join(' / ').normalize('NFC'))
  const isLetter = (value: string) => /\p{L}/u.test(value)
  const hidden = chars.map((character, index) => ({ character, index })).filter(({ character, index }) => isLetter(character) && !hint.revealed.includes(index))
  const canReveal = !record && !pending && hint.uses < 3 && hidden.length > 0 && !!onLetterHintChange
  const reveal = () => {
    if (!canReveal || !onLetterHintChange) return
    let revealed: number[]
    if (hint.uses === 0) revealed = [hidden[0].index]
    else {
      const candidates = [...new Set(hidden.map(({ character }) => character.toLowerCase()))]
      const chosen = candidates[Math.floor(Math.random() * candidates.length)]
      revealed = chars.flatMap((character, index) => isLetter(character) && character.toLowerCase() === chosen ? [index] : [])
    }
    onLetterHintChange({ uses: hint.uses + 1, revealed: [...new Set([...hint.revealed, ...revealed])] })
    inputRefs.current[active]?.focus({ preventScroll: true })
  }
  useKeydown((event) => {
    if (event.ctrlKey && !event.metaKey && !event.altKey && !event.shiftKey && event.key.toLowerCase() === 'l') {
      event.preventDefault(); if (!event.repeat) reveal()
    }
  }, !record)
  const submit = () => { if (!pending && values.every((value) => value.trim())) onSubmit(values.map((value) => value.trim())) }
  return <div>
    <Original item={item} />
    <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">{NAMES[item.targetLanguage]} translation</p>
    <p lang={item.targetLanguage.toLowerCase()} className="serif-text text-xl leading-relaxed sm:text-2xl">{item.segments.map((part, index) => <span key={index}>{part}{index < item.answers.length && (record ?
      <span className="mx-1 rounded bg-accent-soft px-1">{record.gaveUp ? item.answers[index] : record.answer[index]}</span> :
      <input key={index} ref={(node) => { inputRefs.current[index] = node }} autoFocus={index === 0} aria-label={`Translation blank ${index + 1}`} value={values[index]} disabled={pending}
        onFocus={() => setActive(index)} onChange={(event) => setAnswer(index, event.target.value)}
        onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); submit() } }}
        autoComplete="off" autoCapitalize="off" spellCheck={false} style={{ width: `${Math.min(Math.max(6, values[index].length + 1.5), 24)}ch` }}
        className="mx-1 max-w-full rounded-lg border-0 border-b-[3px] border-accent bg-accent-soft/70 px-1.5 text-ink outline-none" />)}</span>)}</p>
    <TranslationHint key={item.sourceSentence} text={item.hint || 'Use the source sentence to work out the missing meaning.'} label="Meaning hint" hoverReveal={false} shortcut={!record} />
    {!record && <div className="mt-5">
      <Button variant="secondary" size="sm" icon={Lightbulb} onClick={reveal} disabled={!canReveal}>Reveal letter <span className="tabular-nums text-muted">{hint.uses}/3 · Ctrl+L</span></Button>
      <p aria-label="Revealed letters" aria-live="polite" aria-hidden={hint.uses === 0} className={`mt-3 flex flex-wrap font-mono text-lg leading-7 ${hint.uses === 0 ? 'invisible' : ''}`}>
        {chars.map((character, index) => <span key={index} className="inline-block h-7 w-[1.3ch] shrink-0 text-center">{isLetter(character) && !hint.revealed.includes(index) ? '•' : character === ' ' ? '\u00a0' : character}</span>)}
      </p>
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
        <AccentKeys code={languageInfo(item.targetLanguage).code} disabled={pending} onInsert={(text) => insertAtCursor(inputRefs.current[active], values[active], text, (value) => setAnswer(active, value))} />
        <div className="ml-auto flex gap-2">{onGiveUp && <Button variant="ghost" icon={Flag} onClick={onGiveUp}>I give up</Button>}<Button onClick={submit} disabled={pending || values.some((value) => !value.trim())} shortcut="↵">{pending ? 'Checking' : 'Check'}</Button></div>
      </div>
    </div>}
  </div>
}

function Feedback({ item, feedback }: FeedbackProps<MixedQuestion, number, ChoiceFeedback> | FeedbackProps<MixedQuestion, string[], MixedCorrection>) {
  return <div className="space-y-5">
    <Section label={`${NAMES[item.sourceLanguage]} sentence`}><span lang={item.sourceLanguage.toLowerCase()}>{item.sourceSentence}</span></Section>
    <Section label={`${NAMES[item.targetLanguage]} translation`}>
      <span lang={item.targetLanguage.toLowerCase()}>{completed(item, item.answers)}</span>
      <div><SpeakButton text={completed(item, item.answers)} code={item.targetLanguage} label={`Listen to ${NAMES[item.targetLanguage]} translation`} /></div>
    </Section>
    <Section label="Vocabulary"><span lang={item.sourceLanguage.toLowerCase()}>{item.terms.join(' · ')}</span></Section>
    {'comment' in feedback && feedback.comment && <p>{feedback.comment}</p>}
  </div>
}

const common = {
  step: 4, icon: ArrowRightLeft, timed: true, usesLevel: true, revisable: false, skippable: false,
  mixedLanguages: true, unit: { one: 'question', other: 'questions' }, scoreLabel: 'correct',
  defaultCount: (meta: import('../types').Meta) => meta.defaults.questions,
  speech: (item: MixedQuestion) => item.sourceSentence, speechLanguage: (item: MixedQuestion) => item.sourceLanguage,
} as const

export const mixedRecognizeExercise: ExerciseDefinition<MixedQuestion, number, ChoiceFeedback> = {
  ...common, kind: 'mixed-recognize', path: '/translate/recognize', verb: 'Translate', name: 'Recognize translation',
  description: 'Read a sentence in one language and choose the missing translation in another.',
  keyHints: [[['1–4', 'A–D'], 'answer'], [['↵'], 'next'], [['Esc'], 'end']],
  outcomeLabels: { correct: 'Correct', wrong: 'Incorrect' }, emptyAnswer: -1,
  generate: async (request, signal) => { const set = await api.mixedTranslation(request, 'recognize', signal); return { items: set.questions, source: set.source } },
  check: async (item, answer) => ({ correct: answer === item.correctChoice }), outcome: (feedback) => feedback.correct ? 'correct' : 'wrong',
  giveUp: () => ({ correct: false }),
  review: (item, record) => ({ sentence: completed(item, item.answers), yours: record.gaveUp ? 'Gave up' : item.choices[record.answer]?.join(' · ') ?? '', correct: record.outcome === 'correct' ? undefined : item.answers.join(' · '), term: item.terms.join(' · ') }),
  Question: ChoiceQuestion, Feedback,
}

export const mixedProduceExercise: ExerciseDefinition<MixedQuestion, string[], MixedCorrection> = {
  ...common, kind: 'mixed-produce', path: '/translate/produce', verb: 'Translate', name: 'Produce translation',
  description: 'Read a sentence in one language and type the missing translation in another.',
  keyHints: [[['Ctrl+H'], 'show hint'], [['Ctrl+L'], 'reveal letter'], [['↵'], 'check, then next'], [['Esc'], 'end']],
  outcomeLabels: { correct: 'Correct', partial: 'Right word, wrong form', wrong: 'Incorrect' }, emptyAnswer: [],
  generate: async (request, signal) => { const set = await api.mixedTranslation(request, 'produce', signal); return { items: set.questions, source: set.source } },
  check: (item, answer, _request, signal) => api.mixedTranslationCheck(item, answer, signal),
  outcome: (feedback) => feedback.verdict === 'correct' ? 'correct' : feedback.verdict === 'wrong_form' ? 'partial' : 'wrong',
  giveUp: (item) => ({ verdict: 'wrong_word', correctedAnswers: item.answers, comment: '' }),
  review: (item, record) => ({ sentence: completed(item, item.answers), yours: record.gaveUp ? 'Gave up' : record.answer.join(' · '), correct: record.outcome === 'correct' ? undefined : item.answers.join(' · '), term: item.terms.join(' · ') }),
  Question: ProduceQuestion, Feedback,
}
