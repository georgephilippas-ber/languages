import { useCallback, useEffect, useRef, useState, type ReactNode, type Ref } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { useLocation, useNavigate } from 'react-router'
import { ArrowRight, Flag, RotateCcw, X } from 'lucide-react'
import { isAbort, messageOf } from '../api'
import { useMeta } from '../context/MetaContext'
import type { ExerciseDefinition, ExerciseInfo, ItemRecord, LetterHintState } from '../exercises/types'
import { hasModifier, isEditable, isInteractive, useKeydown } from '../hooks/useKeydown'
import { usePersistentState } from '../hooks/usePersistentState'
import { useScrollBehavior } from '../hooks/usePrefersReducedMotion'
import { cx } from '../lib/cx'
import { flushProgress, recordProgress } from '../lib/adaptive'
import { exerciseSelection } from '../lib/files'
import { OUTCOME_STYLES } from '../lib/outcomes'
import { readStored, removeStored, sessionKey, writeStored } from '../lib/storage'
import { clearLuckySession, readLuckySession, saveLuckySession } from '../lib/luckySession'
import type { ExerciseRequest, LanguageCode, Outcome } from '../types'
import { Button } from './Button'
import { ConfirmDialog } from './ConfirmDialog'
import { Kbd } from './Kbd'
import { Notice } from './Notice'
import { ProgressBar } from './ProgressBar'
import { ResultsView } from './ResultsView'
import { SetupPanel, type SetupSettings } from './SetupPanel'
import { SpeakButton } from './SpeakButton'
import { ErrorCard, LoadingCard } from './StatusCards'
import { TimerRing } from './TimerRing'
import { VerdictBanner } from './VerdictBanner'

interface Session<I, A, F> {
  version: 1
  request: ExerciseRequest
  source: string
  items: I[]
  records: (ItemRecord<A, F> | null)[]
  index: number
  finished: boolean
  letterHints?: Record<number, LetterHintState>
  meaningHints?: Record<number, boolean>
  requireFullCount?: boolean
  luckyId?: string
  progressId?: string
  drafts?: Record<number, string | string[]>
  elapsed?: { index: number; ms: number }
}

type Status =
  | { phase: 'idle' }
  | { phase: 'loading'; request: ExerciseRequest; startedAt: number; requireFullCount: boolean }
  | { phase: 'error'; request: ExerciseRequest; message: string; requireFullCount: boolean }

type Autostart = 'revise' | 'start' | 'lucky'

function isSession<I, A, F>(value: unknown): value is Session<I, A, F> {
  if (!value || typeof value !== 'object') return false
  const session = value as Partial<Session<I, A, F>>
  return (
    session.version === 1 &&
    !session.finished &&
    Array.isArray(session.items) &&
    Array.isArray(session.records) &&
    session.items.length > 0 &&
    session.items.length === session.records.length &&
    typeof session.index === 'number' &&
    session.index >= 0 &&
    session.index < session.items.length &&
    !!session.request
  )
}

function advance<I, A, F>(session: Session<I, A, F>): Session<I, A, F> {
  return session.index + 1 < session.items.length ? { ...session, index: session.index + 1 } : { ...session, finished: true }
}

function withRecord<I, A, F>(session: Session<I, A, F>, index: number, record: ItemRecord<A, F>): Session<I, A, F> {
  return { ...session, records: session.records.map((value, position) => (position === index ? record : value)) }
}

export function ExerciseRunner<I, A, F>({ definition }: { definition: ExerciseDefinition<I, A, F> }) {
  const { meta, language, languageInfo, setLanguage } = useMeta()
  const navigate = useNavigate()
  const location = useLocation()
  const storageKey = sessionKey(definition.kind)
  const activeStorageKey = `session.active.${definition.kind}`
  const [settings, setSettings] = usePersistentState<SetupSettings>(`settings.${definition.kind}`, {
    level: meta.defaults.level,
    count: definition.defaultCount(meta),
    files: 'all',
    includePhrasal: false,
  })
  const returning = (location.state as { resumeExercise?: boolean } | null)?.resumeExercise === true
  const returningLucky = (location.state as { resumeLucky?: boolean } | null)?.resumeLucky === true
  const [session, setSession] = useState<Session<I, A, F> | null>(() => {
    const activeIsLucky = returningLucky || (returning && readStored<string>(activeStorageKey) === 'lucky')
    const lucky = activeIsLucky ? readLuckySession() : null
    const value = activeIsLucky ? (lucky?.kind === definition.kind ? lucky.session : null) : readStored<unknown>(storageKey)
    return (returning || returningLucky) && isSession<I, A, F>(value) ? value : null
  })
  const [saved, setSaved] = useState<Session<I, A, F> | null>(() => {
    const normal = readStored<unknown>(storageKey)
    const lucky = readLuckySession()
    const value = isSession<I, A, F>(normal) ? normal : lucky?.kind === definition.kind ? lucky.session : null
    return !returning && !returningLucky && isSession<I, A, F>(value) ? value : null
  })
  const [status, setStatus] = useState<Status>({ phase: 'idle' })
  const [checking, setChecking] = useState(false)
  const [checkError, setCheckError] = useState<string | null>(null)
  const [confirmEnd, setConfirmEnd] = useState(false)
  const [shownAt, setShownAt] = useState<number | null>(null)
  const [frozenMs, setFrozenMs] = useState<number | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const lastAnswerRef = useRef<{ answer: A; timeMs: number | null } | null>(null)
  const autostartedRef = useRef<string | null>(null)
  const nextRef = useRef<HTMLButtonElement>(null)
  const scrollBehavior = useScrollBehavior()
  const resumeSnapshot = useRef<{ session: Session<I, A, F> | null; shownAt: number | null; frozenMs: number | null }>({ session, shownAt, frozenMs })
  resumeSnapshot.current = { session, shownAt, frozenMs }

  const active = session !== null && !session.finished
  const record = active ? session.records[session.index] : null
  const questionKey = active && record === null ? `${session.luckyId ?? (session.requireFullCount ? 'legacy-lucky' : 'standard')}:${session.index}` : null

  useEffect(() => { void flushProgress() }, [])
  useEffect(() => {
    if (!session || session.finished || session.records[session.index]) return
    const id = session.progressId ? `${session.progressId}:${session.index}:seen` : undefined
    recordProgress(definition.kind, session.items[session.index], null, 'seen', session.request.language, false, id)
  }, [session?.progressId, session?.index, session?.finished, definition.kind])

  useEffect(() => () => {
    abortRef.current?.abort()
    const current = resumeSnapshot.current
    if (current.session && !current.session.finished && !current.session.records[current.session.index] && current.shownAt !== null) {
      const snapshot = { ...current.session, elapsed: { index: current.session.index, ms: current.frozenMs ?? Math.max(0, performance.now() - current.shownAt) } }
      if (snapshot.requireFullCount) saveLuckySession(definition.kind, snapshot)
      else writeStored(storageKey, snapshot)
    }
  }, [storageKey, definition.kind])
  useEffect(() => {
    if (!returning && !returningLucky) return
    if (returningLucky) {
      const lucky = readLuckySession()
      if (lucky?.kind === definition.kind && isSession<I, A, F>(lucky.session)) {
        if (!definition.mixedLanguages && lucky.session.request.language !== language.code) setLanguage(lucky.session.request.language, { preserveSessions: true })
        setSession(lucky.session)
        setSaved(null)
        setStatus({ phase: 'idle' })
      }
    }
    navigate(location.pathname, { replace: true, state: null })
  }, [returning, returningLucky, location.pathname, navigate, definition.kind, definition.mixedLanguages, language.code, setLanguage])

  useEffect(() => {
    if (session && !session.finished) {
      if (session.requireFullCount) {
        saveLuckySession(definition.kind, session)
        const legacy = readStored<Session<I, A, F>>(storageKey)
        if (legacy?.requireFullCount && legacy.luckyId === session.luckyId) removeStored(storageKey)
        writeStored(activeStorageKey, 'lucky')
      } else {
        writeStored(storageKey, session)
        writeStored(activeStorageKey, 'normal')
      }
    } else if (session?.finished) {
      if (session.requireFullCount) clearLuckySession(definition.kind, session.luckyId)
      else removeStored(storageKey)
      if (readStored<string>(activeStorageKey) === (session.requireFullCount ? 'lucky' : 'normal')) removeStored(activeStorageKey)
    }
  }, [session, storageKey, activeStorageKey, definition.kind])

  useEffect(() => {
    if (questionKey === null) return
    const elapsed = session?.elapsed && session.elapsed.index === session.index ? session.elapsed.ms : 0
    setShownAt(performance.now() - elapsed)
    setFrozenMs(null)
  }, [questionKey])

  useEffect(() => {
    if (record) nextRef.current?.focus({ preventScroll: true })
  }, [record])

  const start = useCallback(
    async (request: ExerciseRequest, requireFullCount = false) => {
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller
      setSession(null)
      setCheckError(null)
      setStatus({ phase: 'loading', request, startedAt: Date.now(), requireFullCount })
      try {
        const { items, source } = await definition.generate(request, controller.signal)
        if (controller.signal.aborted) return
        if (requireFullCount && items.length !== request.count) {
          throw new Error(`Only ${items.length} of ${request.count} questions were generated. Please try again.`)
        }
        setSaved(null)
        setSession({ version: 1, request, source, items, records: items.map(() => null), index: 0, finished: false, requireFullCount,
          progressId: typeof crypto.randomUUID === 'function' ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
          luckyId: requireFullCount ? (typeof crypto.randomUUID === 'function' ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`) : undefined })
        setStatus({ phase: 'idle' })
        window.scrollTo({ top: 0 })
      } catch (error) {
        if (isAbort(error)) return
        setStatus({ phase: 'error', request, message: messageOf(error), requireFullCount })
      }
    },
    [definition],
  )

  const settingsRequest = (): ExerciseRequest => ({
    language: language.code,
    level: settings.level,
    count: Math.min(Math.max(settings.count, 1), meta.defaults.maxCount),
    files: definition.mixedLanguages ? 'all' : exerciseSelection(settings.files),
    includePhrasal: definition.mixedLanguages ? !!settings.includePhrasal : undefined,
  })

  const reviseRequest = (): ExerciseRequest => ({
    language: language.code,
    level: settings.level,
    count: meta.defaults.revise,
    files: 'all',
    includePhrasal: definition.mixedLanguages ? !!settings.includePhrasal : undefined,
  })

  const navigationState = location.state as { start?: Autostart; luckyLanguage?: LanguageCode; luckyRequestId?: number; luckyFiles?: 'all' | 'phrasal-verbs' } | null
  const autostart = navigationState?.start

  useEffect(() => {
    const requestId = navigationState?.luckyRequestId !== undefined ? `lucky:${navigationState.luckyRequestId}` : location.key
    if (!autostart || autostartedRef.current === requestId) return
    autostartedRef.current = requestId
    navigate(location.pathname, { replace: true, state: null })
    const request = autostart === 'lucky'
      ? { language: navigationState?.luckyLanguage ?? language.code, level: 'C1' as const, count: 12, files: navigationState?.luckyFiles ?? 'all' as const, includePhrasal: false, pairLanguage: definition.mixedLanguages ? (navigationState?.luckyLanguage ?? language.code) : undefined }
      : autostart === 'revise' ? reviseRequest() : settingsRequest()
    void start(request, autostart === 'lucky')
  })

  const submit = async (answer: A, retryTimeMs?: number | null) => {
    if (!session || session.finished || checking) return
    const index = session.index
    const timeMs =
      retryTimeMs !== undefined ? retryTimeMs : definition.timed && shownAt !== null ? performance.now() - shownAt : null
    lastAnswerRef.current = { answer, timeMs }
    setFrozenMs(timeMs)
    setChecking(true)
    setCheckError(null)
    const controller = new AbortController()
    abortRef.current = controller
    try {
      const feedback = await definition.check(session.items[index], answer, session.request, controller.signal)
      const outcome = definition.outcome(feedback)
      recordProgress(definition.kind, session.items[index], feedback, outcome, session.request.language, !!session.meaningHints?.[index] || !!session.letterHints?.[index]?.uses)
      setSession((current) =>
        current && current.index === index && !current.finished ? withRecord(current, index, { answer, feedback, outcome, timeMs }) : current,
      )
    } catch (error) {
      if (!isAbort(error)) setCheckError(messageOf(error))
    } finally {
      setChecking(false)
    }
  }

  const skip = () => {
    if (!definition.skippable || checking) return
    setCheckError(null)
    setSession((current) =>
      current && !current.finished
        ? advance(withRecord(current, current.index, { answer: definition.emptyAnswer, feedback: null, outcome: 'skipped', timeMs: null }))
        : current,
    )
  }

  const giveUp = () => {
    if (!definition.giveUp || !session || session.finished || checking) return
    const index = session.index
    const timeMs = definition.timed && shownAt !== null ? performance.now() - shownAt : null
    const feedback = definition.giveUp(session.items[index])
    recordProgress(definition.kind, session.items[index], feedback, 'wrong', session.request.language, !!session.meaningHints?.[index] || !!session.letterHints?.[index]?.uses)
    setCheckError(null)
    setFrozenMs(timeMs)
    setSession((current) =>
      current && current.index === index && !current.finished
        ? withRecord(current, index, { answer: definition.emptyAnswer, feedback, outcome: 'wrong', timeMs, gaveUp: true })
        : current,
    )
  }

  const next = () => {
    setCheckError(null)
    setSession((current) => (current && !current.finished ? advance(current) : current))
    window.scrollTo({ top: 0, behavior: scrollBehavior })
  }

  const end = () => {
    setConfirmEnd(false)
    abortRef.current?.abort()
    setChecking(false)
    setSession((current) => (current ? { ...current, finished: true } : current))
    window.scrollTo({ top: 0 })
  }

  useKeydown(
    (event) => {
      if (confirmEnd) return
      if (event.key === 'Escape') {
        event.preventDefault()
        setConfirmEnd(true)
        return
      }
      if (!record || hasModifier(event)) return
      if ((event.key === 'Enter' && !isInteractive(event.target)) || (event.key === 'ArrowRight' && !isEditable(event.target))) {
        event.preventDefault()
        next()
      }
    },
    active,
  )

  if (!session) {
    if (status.phase === 'loading') {
      return (
        <LoadingCard
          definition={definition}
          request={status.request}
          language={languageInfo(status.request.language)}
          startedAt={status.startedAt}
          onCancel={() => {
            abortRef.current?.abort()
            setStatus({ phase: 'idle' })
          }}
        />
      )
    }
    if (status.phase === 'error') {
      const request = status.request
      return (
        <ErrorCard
          title={`Couldn't prepare the ${definition.name.toLowerCase()}`}
          message={status.message}
          onRetry={() => void start(request, status.requireFullCount)}
          onBack={() => setStatus({ phase: 'idle' })}
        />
      )
    }
    return (
      <SetupPanel
        definition={definition}
        settings={settings}
        onChange={setSettings}
        onStart={() => void start(settingsRequest())}
        onRevise={() => void start(reviseRequest())}
        resume={
          saved
            ? {
                index: saved.index,
                total: saved.items.length,
                source: saved.source,
                languageName: definition.mixedLanguages ? 'All languages' : languageInfo(saved.request.language).name,
              }
            : null
        }
        onResume={() => {
          if (saved) {
            if (saved.request.language !== language.code) setLanguage(saved.request.language, { preserveSessions: true })
            setSession(saved)
          }
          setSaved(null)
        }}
        onDiscard={() => {
          removeStored(storageKey)
          setSaved(null)
        }}
      />
    )
  }

  if (session.finished) {
    return <div data-word-language={session.request.language}><ResultsView definition={definition} session={session} meta={meta} onAgain={() => void start(session.request, session.requireFullCount)} onSettings={() => setSession(null)} /></div>
  }

  const sessionLanguage = languageInfo(session.request.language)
  const item = session.items[session.index]
  const isLast = session.index === session.items.length - 1
  const Question = definition.Question
  const Feedback = definition.Feedback

  return (
    <div className="mx-auto max-w-3xl" data-word-language={session.request.language}>
      <RunnerBar
        definition={definition}
        index={session.index}
        outcomes={session.records.map((value) => value?.outcome ?? null)}
        timer={
          definition.timed ? (
            <TimerRing
              startedAt={shownAt}
              frozenMs={record ? record.timeMs : frozenMs}
              limitMs={meta.defaults.secondsPerQuestion * 1000}
            />
          ) : null
        }
        onEnd={() => setConfirmEnd(true)}
      />

      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={`${session.luckyId ?? (session.requireFullCount ? 'legacy-lucky' : 'standard')}:${session.index}`}
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.22, ease: 'easeOut' }}
        >
          <Question
            item={item}
            record={record}
            pending={checking}
            language={sessionLanguage}
            onSubmit={(answer) => void submit(answer)}
            onSkip={skip}
            onGiveUp={definition.giveUp ? giveUp : undefined}
            draft={session.drafts?.[session.index]}
            onDraftChange={(draft) => setSession((current) =>
              current && !current.finished && current.index === session.index
                ? { ...current, drafts: { ...current.drafts, [current.index]: draft } } : current,
            )}
            letterHint={session.letterHints?.[session.index]}
            onMeaningHint={() => setSession((current) =>
              current && !current.finished && current.index === session.index && !current.meaningHints?.[current.index]
                ? { ...current, meaningHints: { ...current.meaningHints, [current.index]: true } } : current,
            )}
            onLetterHintChange={(hint) => setSession((current) =>
              current && !current.finished && current.index === session.index
                ? { ...current, letterHints: { ...current.letterHints, [current.index]: hint } }
                : current,
            )}
          />

          {checkError && (
            <div className="mt-6">
              <Notice
                tone="error"
                action={
                  <Button
                    size="sm"
                    variant="secondary"
                    icon={RotateCcw}
                    onClick={() => lastAnswerRef.current && void submit(lastAnswerRef.current.answer, lastAnswerRef.current.timeMs)}
                  >
                    Try again
                  </Button>
                }
              >
                {checkError}
              </Notice>
            </div>
          )}

          {record && record.feedback !== null && (
            <FeedbackPanel
              outcome={record.outcome}
              label={record.gaveUp ? 'Gave up' : definition.outcomeLabels[record.outcome] ?? record.outcome}
              speech={definition.speech(item, record.feedback)}
              code={definition.speechLanguage?.(item) ?? sessionLanguage.code}
              showSpeech={!definition.mixedLanguages}
              isLast={isLast}
              nextRef={nextRef}
              onNext={next}
            >
              <Feedback item={item} answer={record.answer} feedback={record.feedback} gaveUp={!!record.gaveUp} language={sessionLanguage} />
            </FeedbackPanel>
          )}
        </motion.div>
      </AnimatePresence>

      <KeyHints hints={definition.keyHints} />

      <div aria-live="polite" className="sr-only">
        {record ? (record.gaveUp ? 'Gave up' : definition.outcomeLabels[record.outcome]) : ''}
      </div>

      <ConfirmDialog
        open={confirmEnd}
        title="End this exercise?"
        body="You'll see your score and time for the questions you have answered so far."
        confirmLabel="End and see results"
        cancelLabel="Keep going"
        onConfirm={end}
        onCancel={() => setConfirmEnd(false)}
      />
    </div>
  )
}

function RunnerBar({
  definition,
  index,
  outcomes,
  timer,
  onEnd,
}: {
  definition: ExerciseInfo
  index: number
  outcomes: (Outcome | null)[]
  timer: ReactNode
  onEnd: () => void
}) {
  const Icon = definition.icon
  return (
    <div className="sticky top-[var(--languages-header-height,4rem)] z-10 -mx-4 mb-8 border-b border-line/70 bg-bg/85 px-4 py-2.5 backdrop-blur-md sm:mx-0 sm:rounded-2xl sm:border sm:px-4">
      <div className="flex items-center gap-3 sm:gap-4">
        <span className="hidden shrink-0 items-center gap-2 text-sm font-medium sm:flex">
          <Icon aria-hidden className="size-4 text-accent" />
          {definition.verb}
        </span>
        <div className="min-w-0 flex-1">
          <ProgressBar outcomes={outcomes} current={index} />
        </div>
        <span className="shrink-0 text-sm tabular-nums text-muted">
          <span className="font-semibold text-ink">{index + 1}</span> / {outcomes.length}
        </span>
        {timer}
        <Button variant="danger" size="sm" icon={X} shortcut="Esc" aria-label="End exercise" title="End exercise (Esc)" onClick={onEnd}>
          End
        </Button>
      </div>
    </div>
  )
}

function FeedbackPanel({
  outcome,
  label,
  speech,
  code,
  showSpeech,
  isLast,
  nextRef,
  onNext,
  children,
}: {
  outcome: Outcome
  label: string
  speech: string
  code: LanguageCode
  showSpeech: boolean
  isLast: boolean
  nextRef: Ref<HTMLButtonElement>
  onNext: () => void
  children: ReactNode
}) {
  const panelRef = useRef<HTMLElement>(null)
  const scrollBehavior = useScrollBehavior()

  useEffect(() => {
    const timer = window.setTimeout(() => panelRef.current?.scrollIntoView({ behavior: scrollBehavior, block: 'nearest' }), 60)
    return () => window.clearTimeout(timer)
  }, [scrollBehavior])

  return (
    <motion.section
      ref={panelRef}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      aria-label="Feedback"
      className={cx('mt-8 scroll-mt-[calc(var(--languages-header-height,4rem)+5rem)] scroll-mb-8 rounded-2xl border border-l-4 border-line bg-surface p-5 shadow-sm sm:p-6', OUTCOME_STYLES[outcome].edge)}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <VerdictBanner outcome={outcome} label={label} />
        {showSpeech && <SpeakButton text={speech} code={code} />}
      </div>
      <div className="mt-6">{children}</div>
      <div className="mt-7 flex justify-end">
        <Button ref={nextRef} size="lg" iconRight={isLast ? Flag : ArrowRight} shortcut="↵" onClick={onNext}>
          {isLast ? 'See results' : 'Next'}
        </Button>
      </div>
    </motion.section>
  )
}

function KeyHints({ hints }: { hints: [string[], string][] }) {
  return (
    <p className="mt-10 hidden flex-wrap items-center justify-center gap-x-5 gap-y-2 text-xs text-muted sm:flex pointer-coarse:hidden">
      {hints.map(([keys, label]) => (
        <span key={label} className="flex items-center gap-1.5">
          {keys.map((key) => (
            <Kbd key={key}>{key}</Kbd>
          ))}
          <span>{label}</span>
        </span>
      ))}
    </p>
  )
}
