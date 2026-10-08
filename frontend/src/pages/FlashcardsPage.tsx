import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { ArrowLeft, ArrowRight, ChevronDown, Eye, GalleryVerticalEnd, LoaderCircle, RotateCcw, Shuffle, X } from 'lucide-react'
import { api, isAbort, messageOf } from '../api'
import { useMeta } from '../context/MetaContext'
import { hasModifier, isInteractive, useKeydown } from '../hooks/useKeydown'
import { usePersistentState } from '../hooks/usePersistentState'
import { cx } from '../lib/cx'
import { plural } from '../lib/format'
import type { CardSection, Direction, FileSelection, Flashcard, Grade, LanguageCode } from '../types'
import { Button } from '../components/Button'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { Kbd } from '../components/Kbd'
import { Notice } from '../components/Notice'
import { Rich } from '../components/Rich'
import { SpeakButton } from '../components/SpeakButton'

interface CardSettings {
  files: FileSelection
  direction: Direction
  newCards: number
}

type Mode = 'study' | 'browse'

interface Study {
  mode: Mode
  queue: Flashcard[]
  total: number
  done: number
  grades: Record<Grade, number>
  language: LanguageCode
  direction: Direction
}

const GRADES: { grade: Grade; label: string; key: string; tone: string }[] = [
  { grade: 'again', label: 'Again', key: '1', tone: 'border-bad/40 hover:bg-bad-soft text-bad' },
  { grade: 'hard', label: 'Hard', key: '2', tone: 'border-warn/40 hover:bg-warn-soft text-warn' },
  { grade: 'good', label: 'Good', key: '3', tone: 'border-good/40 hover:bg-good-soft text-good' },
  { grade: 'easy', label: 'Easy', key: '4', tone: 'border-accent/40 hover:bg-accent-soft text-accent' },
]

const MAIN_LABELS = ['Definition', 'Translation', 'Example', 'Another example', 'Synonym']
const EMPTY_GRADES: Record<Grade, number> = { again: 0, hard: 0, good: 0, easy: 0 }
const MAX_NEW = 100

function shuffle<T>(items: T[]): T[] {
  const copy = [...items]
  for (let index = copy.length - 1; index > 0; index--) {
    const other = Math.floor(Math.random() * (index + 1))
    ;[copy[index], copy[other]] = [copy[other], copy[index]]
  }
  return copy
}

function relative(iso: string | null): string {
  if (!iso) return ''
  const minutes = Math.round((new Date(iso).getTime() - Date.now()) / 60000)
  if (minutes < 1) return 'now'
  if (minutes < 60) return `in ${minutes} min`
  if (minutes < 60 * 24) return `in ${Math.round(minutes / 60)} h`
  return `in ${plural(Math.round(minutes / (60 * 24)), 'day', 'days')}`
}

function sectionsWith(card: Flashcard, labels: string[]): CardSection[] {
  return card.sections.filter((section) => labels.includes(section.label))
}

function SectionBlock({ section, large = false }: { section: CardSection; large?: boolean }) {
  return (
    <section>
      {section.label !== 'Translation' && (
        <h3 className="mb-1 text-[11px] font-semibold uppercase tracking-[0.09em] text-muted">{section.label}</h3>
      )}
      <div className={large ? 'text-xl leading-relaxed sm:text-2xl' : 'text-[15px] leading-relaxed'}>
        <Rich text={section.text} />
      </div>
    </section>
  )
}

function Chip({ selected, onClick, children }: { selected: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={cx(
        'cursor-pointer rounded-xl border px-3 py-2 text-left text-sm transition',
        selected ? 'border-accent bg-accent-soft text-ink shadow-sm' : 'border-line bg-surface text-muted hover:border-accent/50 hover:text-ink',
      )}
    >
      {children}
    </button>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid gap-2.5 py-5 first:pt-0 sm:grid-cols-[9rem_1fr] sm:gap-6">
      <span className="pt-2 text-sm font-medium text-muted">{label}</span>
      <div>{children}</div>
    </div>
  )
}

function CardView({ card, direction, revealed, code }: { card: Flashcard; direction: Direction; revealed: boolean; code: LanguageCode }) {
  const [more, setMore] = usePersistentState('flashcards.more', false)
  const cefr = card.sections.find((section) => section.label === 'CEFR')
  const translations = sectionsWith(card, ['Translation'])
  const prompt = direction === 'reverse' ? (translations.length ? translations : sectionsWith(card, ['Definition'])) : []
  const shownOnFront = new Set(prompt)
  const main = MAIN_LABELS.flatMap((label) => sectionsWith(card, [label])).filter((section) => !shownOnFront.has(section))
  const extra = card.sections.filter((section) => section.label !== 'CEFR' && !MAIN_LABELS.includes(section.label))

  const term = (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <h2 className="serif-text text-3xl leading-tight tracking-tight text-balance sm:text-4xl">{card.term}</h2>
      <SpeakButton text={card.term.split(' / ')[0].replace(/\([^)]*\)/g, '')} code={code} />
    </div>
  )

  return (
    <div className="rounded-3xl border border-line bg-surface p-6 shadow-sm sm:p-8">
      <div className="mb-5 flex items-center justify-between gap-3 text-xs text-muted">
        <span>{card.fileName}</span>
        <span className="flex items-center gap-2">
          {card.isNew && <span className="rounded-full bg-accent-soft px-2 py-0.5 font-semibold text-accent">new</span>}
          {cefr && (
            <span className="rounded-full bg-surface-2 px-2 py-0.5 font-medium">
              <Rich text={cefr.text.replace(/^roughly\s*/, '').replace(/\.$/, '')} />
            </span>
          )}
        </span>
      </div>

      {direction === 'forward' ? (
        term
      ) : (
        <div className="space-y-3">
          {prompt.map((section, index) => (
            <SectionBlock key={index} section={section} large />
          ))}
        </div>
      )}

      <AnimatePresence initial={false}>
        {revealed && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
            <div className="my-6 border-t border-dashed border-line" />
            {direction === 'reverse' && <div className="mb-5">{term}</div>}
            <div className="space-y-4">
              {main.map((section, index) => (
                <SectionBlock key={index} section={section} />
              ))}
            </div>
            {extra.length > 0 && (
              <div className="mt-5">
                <Button variant="ghost" size="sm" icon={ChevronDown} aria-expanded={more} onClick={() => setMore((value) => !value)}>
                  {more ? 'Hide grammar and notes' : 'Grammar and notes'}
                </Button>
                {more && (
                  <div className="mt-3 space-y-4">
                    {extra.map((section, index) => (
                      <SectionBlock key={index} section={section} />
                    ))}
                  </div>
                )}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export function FlashcardsPage() {
  const { meta, language } = useMeta()
  const [settings, setSettings] = usePersistentState<CardSettings>('settings.flashcards', {
    files: 'all',
    direction: 'forward',
    newCards: 10,
  })
  const [cards, setCards] = useState<Flashcard[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [reload, setReload] = useState(0)
  const [study, setStudy] = useState<Study | null>(null)
  const [revealed, setRevealed] = useState(false)
  const [grading, setGrading] = useState(false)
  const [gradeError, setGradeError] = useState<string | null>(null)
  const [confirmEnd, setConfirmEnd] = useState(false)
  const studyLanguage = useRef(language.code)

  const files = language.files
  const selection: FileSelection =
    typeof settings.files === 'number' && !files.some((file) => file.number === settings.files) ? 'all' : settings.files
  const newLimit = Math.min(Math.max(settings.newCards, 0), MAX_NEW)
  const update = (patch: Partial<CardSettings>) => setSettings({ ...settings, files: selection, ...patch })

  useEffect(() => {
    if (study) return
    const controller = new AbortController()
    setCards(null)
    setLoadError(null)
    api
      .flashcards({ language: language.code, files: selection, direction: settings.direction }, controller.signal)
      .then((set) => setCards(set.cards))
      .catch((error: unknown) => {
        if (!isAbort(error)) setLoadError(messageOf(error))
      })
    return () => controller.abort()
  }, [language.code, selection, settings.direction, study, reload])

  useEffect(() => {
    if (studyLanguage.current === language.code) return
    studyLanguage.current = language.code
    setStudy(null)
    setConfirmEnd(false)
  }, [language.code])

  const summary = useMemo(() => {
    const list = cards ?? []
    const due = list.filter((card) => card.isDue)
    const fresh = list.filter((card) => card.isNew)
    const upcoming = list
      .filter((card) => !card.isNew && !card.isDue && card.state.dueAt)
      .map((card) => card.state.dueAt as string)
      .sort()[0]
    return { due, fresh, upcoming: upcoming ?? null, total: list.length }
  }, [cards])

  const begin = (mode: Mode) => {
    if (!cards) return
    const queue =
      mode === 'study'
        ? [...[...summary.due].sort((a, b) => (a.state.dueAt ?? '').localeCompare(b.state.dueAt ?? '')), ...summary.fresh.slice(0, newLimit)]
        : shuffle(cards)
    if (!queue.length) return
    setStudy({
      mode,
      queue,
      total: queue.length,
      done: 0,
      grades: { ...EMPTY_GRADES },
      language: language.code,
      direction: settings.direction,
    })
    setRevealed(false)
    setGradeError(null)
    window.scrollTo({ top: 0 })
  }

  const current = study?.queue[0] ?? null

  const answer = async (grade: Grade) => {
    if (!study || !current || !revealed || grading) return
    setGradeError(null)
    let reviewed: Flashcard = { ...current, isNew: false }
    if (study.mode === 'study') {
      setGrading(true)
      try {
        const review = await api.review(study.language, study.direction, current.term, grade)
        reviewed = { ...current, isNew: false, state: review.state, intervals: review.intervals }
      } catch (error) {
        setGradeError(messageOf(error))
        setGrading(false)
        return
      }
      setGrading(false)
    }
    const again = grade === 'again'
    setStudy({
      ...study,
      queue: again ? [...study.queue.slice(1), reviewed] : study.queue.slice(1),
      done: again ? study.done : study.done + 1,
      grades: { ...study.grades, [grade]: study.grades[grade] + 1 },
    })
    setRevealed(false)
  }

  useKeydown(
    (event) => {
      if (confirmEnd || hasModifier(event)) return
      if (event.key === 'Escape') {
        event.preventDefault()
        if (current) setConfirmEnd(true)
        else setStudy(null)
        return
      }
      if (!current || isInteractive(event.target)) return
      if (!revealed && (event.key === ' ' || event.key === 'Enter')) {
        event.preventDefault()
        setRevealed(true)
        return
      }
      if (!revealed) return
      if (study?.mode === 'browse') {
        if (event.key === '1' || event.key === 'ArrowLeft') void answer('again')
        if (event.key === '2' || event.key === ' ' || event.key === 'Enter' || event.key === 'ArrowRight') {
          event.preventDefault()
          void answer('good')
        }
        return
      }
      const option = GRADES.find((value) => value.key === event.key)
      if (option) {
        event.preventDefault()
        void answer(option.grade)
      } else if (event.key === ' ' || event.key === 'Enter') {
        event.preventDefault()
        void answer('good')
      }
    },
    study !== null,
  )

  if (study) {
    if (!current) {
      return (
        <div className="mx-auto max-w-3xl">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-3xl border border-line bg-surface p-6 text-center shadow-sm sm:p-10"
          >
            <p className="text-sm font-medium text-accent">{study.mode === 'study' ? 'Session complete' : 'All cards seen'}</p>
            <h1 className="serif-text mt-2 text-4xl tracking-tight">{plural(study.total, 'card', 'cards')}</h1>
            {study.mode === 'study' && (
              <p className="mt-4 flex flex-wrap justify-center gap-x-4 gap-y-1 text-sm text-muted">
                {GRADES.map(({ grade, label }) => (
                  <span key={grade}>
                    {label} <span className="font-semibold tabular-nums text-ink">{study.grades[grade]}</span>
                  </span>
                ))}
              </p>
            )}
            <div className="mt-8 flex justify-center">
              <Button icon={ArrowLeft} onClick={() => setStudy(null)}>
                Back to the deck
              </Button>
            </div>
          </motion.div>
        </div>
      )
    }

    const intervals = current.intervals
    return (
      <div className="mx-auto max-w-3xl">
        <div className="sticky top-16 z-10 -mx-4 mb-8 border-b border-line/70 bg-bg/85 px-4 py-2.5 backdrop-blur-md sm:mx-0 sm:rounded-2xl sm:border sm:px-4">
          <div className="flex items-center gap-3 sm:gap-4">
            <span className="hidden shrink-0 items-center gap-2 text-sm font-medium sm:flex">
              <GalleryVerticalEnd aria-hidden className="size-4 text-accent" />
              {study.mode === 'study' ? 'Review' : 'Browse'}
            </span>
            <div
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={study.total}
              aria-valuenow={study.done}
              className="h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-line"
            >
              <div className="h-full rounded-full bg-accent transition-[width] duration-300" style={{ width: `${(study.done / study.total) * 100}%` }} />
            </div>
            <span className="shrink-0 text-sm tabular-nums text-muted">
              <span className="font-semibold text-ink">{study.queue.length}</span> left
            </span>
            <Button variant="ghost" size="sm" icon={X} aria-label="End session" title="End session (Esc)" onClick={() => setConfirmEnd(true)} />
          </div>
        </div>

        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={`${current.term}-${study.done}-${study.queue.length}`}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
          >
            <CardView card={current} direction={study.direction} revealed={revealed} code={study.language} />
          </motion.div>
        </AnimatePresence>

        {gradeError && (
          <div className="mt-5">
            <Notice tone="error">{gradeError}</Notice>
          </div>
        )}

        <div className="sticky bottom-4 z-10 mt-6">
          {!revealed ? (
            <Button size="lg" icon={Eye} shortcut="Space" className="w-full shadow-lg" onClick={() => setRevealed(true)}>
              Show answer
            </Button>
          ) : study.mode === 'browse' ? (
            <div className="grid grid-cols-2 gap-3">
              <Button variant="secondary" size="lg" icon={RotateCcw} shortcut="1" onClick={() => void answer('again')}>
                Again later
              </Button>
              <Button size="lg" iconRight={ArrowRight} shortcut="2" onClick={() => void answer('good')}>
                Next
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-4 gap-2 rounded-2xl bg-bg/85 backdrop-blur-md">
              {GRADES.map(({ grade, label, key, tone }) => (
                <button
                  key={grade}
                  type="button"
                  disabled={grading}
                  onClick={() => void answer(grade)}
                  className={cx(
                    'flex h-16 cursor-pointer flex-col items-center justify-center rounded-xl border bg-surface shadow-sm transition disabled:opacity-50',
                    tone,
                  )}
                >
                  <span className="flex items-center gap-1.5 text-sm font-semibold">
                    {grading ? <LoaderCircle aria-hidden className="size-3.5 animate-spin" /> : null}
                    {label}
                    <span className="hidden sm:inline-flex pointer-coarse:hidden">
                      <Kbd>{key}</Kbd>
                    </span>
                  </span>
                  <span className="text-xs tabular-nums text-muted">{intervals[grade]}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <ConfirmDialog
          open={confirmEnd}
          title="End this session?"
          body="Cards you have already graded keep their new schedule."
          confirmLabel="End session"
          cancelLabel="Keep going"
          onConfirm={() => {
            setConfirmEnd(false)
            setStudy(null)
          }}
          onCancel={() => setConfirmEnd(false)}
        />
      </div>
    )
  }

  const studyCount = summary.due.length + Math.min(summary.fresh.length, newLimit)

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-8">
        <p className="flex items-center gap-2 text-sm font-medium text-accent">
          <GalleryVerticalEnd aria-hidden className="size-4" />
          {language.name} · Spaced repetition
        </p>
        <h1 className="serif-text mt-2 text-4xl tracking-tight sm:text-5xl">Review</h1>
        <p className="mt-3 max-w-xl text-[17px] leading-relaxed text-muted">
          Flashcards straight from your files. Recall the card, reveal it, and grade yourself: cards you know come back
          less and less often, the ones you miss come back soon.
        </p>
      </div>

      <div className="rounded-3xl border border-line bg-surface p-5 shadow-sm sm:p-7">
        <div className="divide-y divide-line">
          {files.length > 1 && (
            <Field label="Files">
              <div className="flex flex-wrap gap-1.5" role="group" aria-label="Files">
                <Chip selected={selection === 'all'} onClick={() => update({ files: 'all' })}>
                  <span className="font-medium text-ink">All</span>
                </Chip>
                <Chip selected={selection === 'latest'} onClick={() => update({ files: 'latest' })}>
                  <span className="font-medium text-ink">Latest {Math.min(meta.defaults.latestFiles, files.length)}</span>
                </Chip>
                <Chip selected={selection === 'current'} onClick={() => update({ files: 'current' })}>
                  <span className="font-medium text-ink">Latest 1</span>
                </Chip>
                {files.map((file) => (
                  <Chip key={file.number} selected={selection === file.number} onClick={() => update({ files: file.number })}>
                    <span className="font-semibold tabular-nums text-ink">{file.number}</span>
                    <span className="ml-1.5 text-xs tabular-nums">{file.terms}</span>
                  </Chip>
                ))}
              </div>
            </Field>
          )}

          <Field label="Direction">
            <div className="flex flex-wrap gap-1.5" role="group" aria-label="Direction">
              <Chip selected={settings.direction === 'forward'} onClick={() => update({ direction: 'forward' })}>
                <span className="block font-medium text-ink">{language.name} → meaning</span>
                <span className="text-xs">See the term, recall what it means</span>
              </Chip>
              <Chip selected={settings.direction === 'reverse'} onClick={() => update({ direction: 'reverse' })}>
                <span className="block font-medium text-ink">Meaning → {language.name}</span>
                <span className="text-xs">See the translation, recall the term</span>
              </Chip>
            </div>
          </Field>

          <Field label="New cards">
            <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="New cards per session">
              {[5, 10, 20, 50].map((value) => (
                <Chip key={value} selected={newLimit === value} onClick={() => update({ newCards: value })}>
                  <span className="font-semibold tabular-nums text-ink">{value}</span>
                </Chip>
              ))}
              <span className="ml-2 text-sm text-muted">per session</span>
            </div>
          </Field>
        </div>

        <div className="mt-2 border-t border-line pt-5">
          {loadError ? (
            <Notice
              tone="error"
              action={
                <Button size="sm" variant="secondary" icon={RotateCcw} onClick={() => setReload((value) => value + 1)}>
                  Try again
                </Button>
              }
            >
              {loadError}
            </Notice>
          ) : !cards ? (
            <p className="flex items-center gap-2 text-sm text-muted">
              <LoaderCircle aria-hidden className="size-4 animate-spin" /> Reading the cards…
            </p>
          ) : (
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
              <div className="min-w-0 flex-1">
                <p className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted">
                  <span>
                    <span className="font-semibold tabular-nums text-ink">{summary.due.length}</span> due
                  </span>
                  <span>
                    <span className="font-semibold tabular-nums text-ink">{summary.fresh.length}</span> new
                  </span>
                  <span>
                    <span className="font-semibold tabular-nums text-ink">{summary.total}</span> in the deck
                  </span>
                </p>
                {studyCount === 0 && summary.total > 0 && (
                  <p className="mt-1 text-sm text-muted">
                    All caught up{summary.upcoming ? ` · next card due ${relative(summary.upcoming)}` : ''}.
                  </p>
                )}
                {meta.demo && <p className="mt-1 text-sm text-muted">Demo mode: grades are not saved.</p>}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="secondary" icon={Shuffle} disabled={!summary.total} onClick={() => begin('browse')} title="All cards, shuffled, without grading">
                  Browse
                </Button>
                <Button iconRight={ArrowRight} disabled={!studyCount} onClick={() => begin('study')}>
                  {studyCount ? `Study ${plural(studyCount, 'card', 'cards')}` : 'Study'}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>

      <p className="mt-10 hidden flex-wrap items-center justify-center gap-x-5 gap-y-2 text-xs text-muted sm:flex pointer-coarse:hidden">
        <span className="flex items-center gap-1.5">
          <Kbd>Space</Kbd> show answer
        </span>
        <span className="flex items-center gap-1.5">
          <Kbd>1–4</Kbd> again, hard, good, easy
        </span>
        <span className="flex items-center gap-1.5">
          <Kbd>Esc</Kbd> end
        </span>
      </p>
    </div>
  )
}
