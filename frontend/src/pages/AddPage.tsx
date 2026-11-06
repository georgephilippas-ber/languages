import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { AnimatePresence, motion } from 'motion/react'
import { ArrowRight, BookPlus, Check, ChevronDown, CircleAlert, FilePlus2, Languages, LoaderCircle, Pencil, RotateCcw, Sparkles, Trash2, X } from 'lucide-react'
import { api, isAbort, messageOf } from '../api'
import { useMeta } from '../context/MetaContext'
import { useKeydown } from '../hooks/useKeydown'
import { usePersistentState } from '../hooks/usePersistentState'
import { useSessionText } from '../hooks/useSessionText'
import { cx } from '../lib/cx'
import { targetFile } from '../lib/entries'
import { categoriesFor, categoryLabels } from '../lib/files'
import { plural } from '../lib/format'
import { readStored, writeStored } from '../lib/storage'
import type { Article, Category, LanguageCode, SaveResult, Translation } from '../types'
import { Button } from '../components/Button'
import { Kbd } from '../components/Kbd'
import { Notice } from '../components/Notice'
import { Rich } from '../components/Rich'
import { DictationButton } from '../components/DictationButton'
import { ReturnToExercise } from '../components/ReturnToExercise'

import { newId, type Draft, type ArticleSource } from '../lib/drafts'

interface SavedReport {
  language: LanguageCode
  result: SaveResult
  glosses: Record<string, string>
  articleSaved?: boolean
}

interface TranslationState {
  language: LanguageCode
  phrase: string
  status: 'loading' | 'ready' | 'error'
  result?: Translation
  error?: string
}

const MAX_PARALLEL = 3
const MAC = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)
const TRANSLATE_KEYS = MAC ? '⌥⌘T' : 'Ctrl Alt T'

function isTranslateShortcut(event: KeyboardEvent): boolean {
  if (event.code !== 'KeyT' || !event.altKey || event.shiftKey || event.repeat) return false
  if (MAC) return event.metaKey && !event.ctrlKey
  return event.ctrlKey && !event.metaKey && !event.getModifierState('AltGraph')
}
const TRANSLATION_LABELS = ['English', 'German', 'French']
const SUMMARY_LABELS = ['CEFR', 'Definition', ...TRANSLATION_LABELS]
const PLACEHOLDERS: Record<LanguageCode, string> = {
  DE: 'die Krähe\netwas abdecken\ndas Gespür — the sense of having a feel for something',
  FR: 'le cafard\nse débrouiller\nrévélateur',
  EN: 'soporific\nto hedge one’s bets\nunpropitious',
}

function headingOf(markdown: string): string {
  return markdown.split('\n')[0].replace(/^##\s*/, '').trim()
}

function entryProblem(markdown: string): string | null {
  const text = markdown.trim()
  if (!text.startsWith('## ') || !headingOf(text)) return 'The entry must start with a “## ” heading.'
  if (text.slice(3).includes('##')) return '“##” may appear only at the start of the heading.'
  if (!text.includes('**Definition:**')) return 'The entry needs a **Definition:** paragraph.'
  return null
}

interface Paragraph {
  label: string | null
  text: string
  full: string
}

function paragraphsOf(markdown: string): Paragraph[] {
  return markdown
    .split(/\n\s*\n/)
    .slice(1)
    .filter((paragraph) => paragraph.trim())
    .map((paragraph) => {
      const full = paragraph.trim()
      const label = /^\*\*([A-Za-z ]+):\*\*\s*/.exec(full) ?? /^(Another example|Useful nuance):\s*/.exec(full)
      return { label: label ? label[1] : null, text: label ? full.slice(label[0].length) : full, full }
    })
}

function EntryPreview({ markdown, expanded }: { markdown: string; expanded: boolean }) {
  const paragraphs = paragraphsOf(markdown).filter((paragraph) => expanded || (paragraph.label && SUMMARY_LABELS.includes(paragraph.label)))
  return (
    <div className="space-y-3 text-[15px] leading-relaxed">
      {paragraphs.map((paragraph, index) =>
        paragraph.label && !TRANSLATION_LABELS.includes(paragraph.label) ? (
          <div key={index}>
            <p className="text-[11px] font-semibold uppercase tracking-[0.09em] text-muted">{paragraph.label}</p>
            <Rich text={paragraph.text} />
          </div>
        ) : (
          <Rich key={index} text={paragraph.full} />
        ),
      )}
    </div>
  )
}

function DraftCard({
  draft,
  onRemove,
  onRetry,
  onEdit,
  onCategory,
}: {
  draft: Draft
  onRemove: () => void
  onRetry: () => void
  onEdit: (markdown: string) => void
  onCategory: (category: Category) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [editing, setEditing] = useState<string | null>(null)
  const problem = editing === null ? null : entryProblem(editing)

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.98 }}
      transition={{ duration: 0.2 }}
      className={cx(
        'rounded-2xl border bg-surface p-5 shadow-sm sm:p-6',
        draft.status === 'error' ? 'border-bad/40' : 'border-line',
      )}
    >
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="serif-text text-2xl leading-tight tracking-tight">{draft.term ?? draft.request}</h3>
          <p className="mt-1 text-sm text-muted">
            {draft.status === 'ready' && draft.gloss ? draft.gloss : null}
            {draft.status === 'queued' && 'Waiting…'}
            {draft.status === 'loading' && 'Writing the entry…'}
          </p>
        </div>
        {draft.status === 'loading' || draft.status === 'queued' ? (
          <LoaderCircle aria-label="Writing" className="mt-1 size-5 shrink-0 animate-spin text-muted" />
        ) : null}
        <Button variant="ghost" size="sm" icon={Trash2} aria-label={`Remove ${draft.term ?? draft.request}`} title="Remove" onClick={onRemove} />
      </div>

      {draft.category && <label className="mt-3 block text-sm text-muted">Category
        <select aria-label={`Category for ${draft.request}`} value={draft.category} onChange={(event) => onCategory(event.target.value as Category)} className="ml-2 rounded-xl border border-line bg-surface px-3 py-2 text-ink">
          {categoriesFor(draft.language).map((option) => <option key={option} value={option}>{categoryLabels[option]}</option>)}
        </select>
      </label>}
      {draft.status === 'error' && (
        <div className="mt-4">
          <Notice
            tone="error"
            action={
              <Button size="sm" variant="secondary" icon={RotateCcw} onClick={onRetry}>
                Try again
              </Button>
            }
          >
            {draft.error}
          </Notice>
        </div>
      )}

      {draft.status === 'ready' && draft.markdown && (
        <div className="mt-4">
          {editing !== null ? (
            <div>
              <textarea
                value={editing}
                onChange={(event) => setEditing(event.target.value)}
                aria-label={`Markdown for ${draft.term}`}
                spellCheck={false}
                rows={Math.min(28, Math.max(10, editing.split('\n').length + 1))}
                className="w-full rounded-xl border border-line bg-bg p-3 font-mono text-[13px] leading-relaxed outline-none focus:border-accent"
              />
              {problem && <p className="mt-2 text-sm text-bad">{problem}</p>}
              <div className="mt-3 flex justify-end gap-2">
                <Button variant="ghost" size="sm" icon={X} onClick={() => setEditing(null)}>
                  Cancel
                </Button>
                <Button
                  size="sm"
                  icon={Check}
                  disabled={problem !== null}
                  onClick={() => {
                    onEdit(editing.trim())
                    setEditing(null)
                  }}
                >
                  Done
                </Button>
              </div>
            </div>
          ) : (
            <>
              <EntryPreview markdown={draft.markdown} expanded={expanded} />
              <div className="mt-4 flex flex-wrap gap-2">
                <Button variant="secondary" size="sm" icon={ChevronDown} aria-expanded={expanded} onClick={() => setExpanded((value) => !value)}>
                  {expanded ? 'Show less' : 'Full entry'}
                </Button>
                <Button variant="ghost" size="sm" icon={Pencil} onClick={() => setEditing(draft.markdown ?? '')}>
                  Edit
                </Button>
                <Button variant="ghost" size="sm" icon={RotateCcw} title="Write the entry again" onClick={onRetry}>
                  Rewrite
                </Button>
              </div>
            </>
          )}
        </div>
      )}
    </motion.article>
  )
}

function TranslationPanel({ state, onClose, onRetry }: { state: TranslationState; onClose: () => void; onRetry: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      transition={{ duration: 0.2 }}
      role="status"
      aria-live="polite"
      className="mt-5 rounded-2xl border border-line bg-bg p-4 sm:p-5"
    >
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <p className="flex flex-wrap items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.09em] text-muted">
            <Languages aria-hidden className="size-3.5" />
            {state.result ? (
              <>
                {state.result.sourceLanguage}
                <ArrowRight aria-hidden className="size-3" />
                {state.result.targetLanguage}
              </>
            ) : (
              'Translation'
            )}
          </p>
          <p className="mt-1.5 text-sm text-muted">{state.phrase}</p>
        </div>
        {state.status === 'loading' && <LoaderCircle aria-label="Translating" className="mt-1 size-5 shrink-0 animate-spin text-muted" />}
        <Button variant="ghost" size="sm" icon={X} aria-label="Close translation" onClick={onClose} />
      </div>

      {state.status === 'error' && (
        <div className="mt-3">
          <Notice
            tone="error"
            action={
              <Button size="sm" variant="secondary" icon={RotateCcw} onClick={onRetry}>
                Try again
              </Button>
            }
          >
            {state.error}
          </Notice>
        </div>
      )}

      {state.status === 'ready' && state.result && (
        <div className="mt-3">
          <p className="serif-text text-2xl leading-snug tracking-tight">{state.result.translation}</p>
          {state.result.notes.length > 0 && (
            <ul className="mt-3 space-y-1.5 border-t border-line pt-3 text-[15px] leading-relaxed">
              {state.result.notes.map((note, index) => (
                <li key={index} className="flex gap-2">
                  <span aria-hidden className="text-muted">•</span>
                  <div className="min-w-0 flex-1">
                    <Rich text={note} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </motion.div>
  )
}

function Report({ report: { result, glosses, articleSaved }, onClose, onReturn }: { report: SavedReport; onClose: () => void; onReturn: () => void }) {
  const { language } = useMeta()
  const files = [...new Set(result.saved.map((entry) => entry.fileName))]
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      role="status"
      className="mb-6 rounded-2xl border border-good/40 bg-good-soft p-5"
    >
      <div className="flex items-start gap-3">
        <Check aria-hidden className="mt-0.5 size-5 shrink-0 text-good" />
        <div className="min-w-0 flex-1 text-[15px] leading-relaxed">
          <p className="font-semibold">
            Added{' '}
            {plural(result.saved.length, 'entry', 'entries')} to {files.map((file) => `vocabulary/${language.name.toLowerCase()}/${file}`).join(' and ')}
          </p>
          <ul className="mt-1.5">
            {result.saved.map((entry, index) => (
              <li key={index}>
                <span className="serif-text">{entry.term}</span>
                {glosses[entry.term] ? <span className="text-muted"> — {glosses[entry.term]}</span> : null}
              </li>
            ))}
          </ul>
          <p className="mt-1.5 font-medium">
            Terms in {result.fileName.replace('.md', '')} so far: {result.termsInFile}
          </p>
          {result.fileFull && (
            <p className="text-muted">{result.fileName} is complete; the next entry starts a new file.</p>
          )}
          {articleSaved && <Button variant="secondary" size="sm" className="mt-3" onClick={onReturn}>Back to article</Button>}
        </div>
        <Button variant="ghost" size="sm" icon={X} aria-label="Close" onClick={onClose} />
      </div>
    </motion.div>
  )
}

export function AddPage() {
  const { meta, language, refresh } = useMeta()
  const location = useLocation()
  const navigate = useNavigate()
  const [text, setText] = useSessionText(`add.input.${language.code}`)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  useEffect(() => { inputRef.current?.focus({ preventScroll: true }) }, [])
  const [dictating, setDictating] = useState(false)
  const [articleSources, setArticleSources] = useState<Partial<Record<LanguageCode, ArticleSource[]>>>({})
  const [category, setCategory] = usePersistentState<Category>('add.category', 'general')
  const [drafts, setDrafts] = usePersistentState<Draft[]>('drafts', [])
  const [allowances, setAllowances] = useState<Partial<Record<LanguageCode, { available: number; reviews_toward_next: number }>>>({})
  const refreshAllowance = (code: LanguageCode) => api.allowance(code).then((value) => setAllowances((current) => ({ ...current, [code]: value }))).catch(() => undefined)
  useEffect(() => { void refreshAllowance(language.code) }, [language.code])
  const allowance = allowances[language.code]
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<{ language: LanguageCode; message: string } | null>(null)
  const [report, setReport] = useState<SavedReport | null>(null)
  const controllers = useRef(new Map<string, AbortController>())
  const [translation, setTranslation] = useState<TranslationState | null>(null)
  const translator = useRef<AbortController | null>(null)
  const limit = meta.defaults.maxTermsPerFile
  useEffect(() => { setDictating(false) }, [language.code])

  const update = (id: string, patch: Partial<Draft>) =>
    setDrafts((current) => current.map((draft) => (draft.id === id ? { ...draft, ...patch } : draft)))

  useEffect(() => {
    const state = location.state as { prefill?: string; category?: Category; articleSources?: ArticleSource[]; returnToExercise?: string; returnLanguage?: LanguageCode } | null
    if (!state?.prefill) return
    setText((current) => [current.trim(), state.prefill].filter(Boolean).join('\n'))
    if (state.category && categoriesFor(language.code).includes(state.category)) setCategory(state.category)
    if (state.articleSources) setArticleSources((current) => ({ ...current, [language.code]: state.articleSources }))
    navigate('/add', { replace: true, state: state.returnToExercise ? { returnToExercise: state.returnToExercise, returnLanguage: state.returnLanguage } : null })
  }, [location.state, navigate, language.code, setCategory])

  useEffect(() => {
    const running = controllers.current
    setDrafts((current) => current.map((draft) => (draft.status === 'loading' ? { ...draft, status: 'queued' } : draft)))
    return () => {
      for (const controller of running.values()) controller.abort()
      running.clear()
      setDrafts((current) => current.map((draft) => (draft.status === 'loading' ? { ...draft, status: 'queued' } : draft)))
    }
  }, [setDrafts])

  useEffect(() => {
    const loading = drafts.filter((draft) => draft.status === 'loading').length
    const next = drafts.filter((draft) => draft.status === 'queued').slice(0, Math.max(0, MAX_PARALLEL - loading))
    if (!next.length) return
    const ids = new Set(next.map((draft) => draft.id))
    setDrafts((current) => current.map((draft) => (ids.has(draft.id) ? { ...draft, status: 'loading', error: undefined } : draft)))
    for (const draft of next) {
      const controller = new AbortController()
      controllers.current.set(draft.id, controller)
      api
        .define(draft.language, draft.request, controller.signal)
        .then((entry) => update(draft.id, { status: 'ready', term: entry.term, markdown: entry.markdown, gloss: entry.gloss }))
        .catch((error: unknown) => {
          if (!isAbort(error)) update(draft.id, { status: 'error', error: messageOf(error) })
        })
        .finally(() => controllers.current.delete(draft.id))
    }
  })

  const visible = drafts.filter((draft) => draft.language === language.code)
  const ready = visible.filter((draft) => draft.status === 'ready' && draft.markdown)
  const activeCategory = categoriesFor(language.code).includes(category) ? category : 'general'
  const available = allowance?.available ?? null
  let remaining = available ?? 0
  const savable = ready.filter((draft) => {
    if (language.code === 'EN' && (draft.category ?? activeCategory) === 'phrasal-verbs') return true
    if (available === null || remaining <= 0) return false
    remaining -= 1
    return true
  })
  const busy = visible.some((draft) => draft.status === 'loading' || draft.status === 'queued')
  const target = targetFile(language, limit, activeCategory)

  const submit = () => {
    if (dictating) return
    const lines = text
      .split('\n')
      .map((line) => line.split(/\s+/).filter(Boolean).join(' '))
      .filter(Boolean)
    if (!lines.length) return
    setDrafts((current) => [
      ...current,
      ...lines.map((line): Draft => ({ id: newId(), language: language.code, request: line, status: 'queued',
        articleSource: articleSources[language.code]?.find((source) => line.normalize('NFC').toLocaleLowerCase() === source.word.normalize('NFC').toLocaleLowerCase()) })),
    ])
    setText('')
    setArticleSources((current) => ({ ...current, [language.code]: [] }))
    setReport(null)
  }

  useEffect(() => () => translator.current?.abort(), [])

  const translate = (phrase: string) => {
    const cleaned = phrase.split(/\s+/).filter(Boolean).join(' ')
    if (!cleaned) return
    translator.current?.abort()
    const controller = new AbortController()
    translator.current = controller
    const code = language.code
    setTranslation({ language: code, phrase: cleaned, status: 'loading' })
    api
      .translate(code, cleaned, controller.signal)
      .then((result) => setTranslation({ language: code, phrase: cleaned, status: 'ready', result }))
      .catch((error: unknown) => {
        if (!isAbort(error)) setTranslation({ language: code, phrase: cleaned, status: 'error', error: messageOf(error) })
      })
  }

  const translateDisabled = !text.trim() || translation?.status === 'loading' || dictating

  useKeydown((event) => {
    if (!isTranslateShortcut(event)) return
    event.preventDefault()
    if (!translateDisabled) translate(text)
  })

  const closeTranslation = () => {
    translator.current?.abort()
    setTranslation(null)
  }

  const remove = (id: string) => {
    controllers.current.get(id)?.abort()
    controllers.current.delete(id)
    setDrafts((current) => current.filter((draft) => draft.id !== id))
  }

  const retry = (id: string) => {
    controllers.current.get(id)?.abort()
    controllers.current.delete(id)
    update(id, { status: 'queued', error: undefined })
  }

  const save = async () => {
    if (!savable.length || saving) return
    setSaving(true)
    setSaveError(null)
    setReport(null)
    const glosses = Object.fromEntries(savable.map((draft) => [draft.term ?? '', draft.gloss ?? '']))
    const groups = new Map<Category, Draft[]>()
    for (const draft of savable) {
      const category = draft.category ?? activeCategory
      groups.set(category, [...(groups.get(category) ?? []), draft])
    }
    let combined: SaveResult | undefined
    let articleSaved = false
    try {
      for (const [category, group] of groups) {
        const result = await api.save(language.code, group.map((draft) => draft.markdown ?? ''), category)
        const savedDrafts = group.slice(0, result.saved.length)
        const articles = readStored<Partial<Record<LanguageCode, Article>>>('read.articles')
        const currentArticle = articles?.[language.code]
        if (currentArticle && articles) {
          const added = [...(currentArticle.addedWords ?? [])]
          let changed = false
          savedDrafts.forEach((draft) => {
            const source = draft.articleSource
            if (!source || source.url !== (currentArticle.url ?? '') || source.retrievedAt !== (currentArticle.retrievedAt ?? '')) return
            if (!added.some((word) => word.normalize('NFC').toLocaleLowerCase() === source.word.normalize('NFC').toLocaleLowerCase())) added.push(source.word)
            changed = true
          })
          if (changed) { writeStored('read.articles', { ...articles, [language.code]: { ...currentArticle, addedWords: added } }); articleSaved = true }
        }
        const ids = new Set(savedDrafts.map((draft) => draft.id))
        setDrafts((current) => current.filter((draft) => !ids.has(draft.id)))
        combined = { ...result, saved: [...(combined?.saved ?? []), ...result.saved] }
        if (savedDrafts.length !== group.length) throw new Error('Some entries were not saved. Please retry the remaining entries.')
      }
    } catch (error) {
      setSaveError({ language: language.code, message: (combined ? 'Some entries were saved. ' : '') + messageOf(error) })
    } finally {
      if (combined) setReport({ language: language.code, result: combined, glosses, articleSaved })
      setSaving(false)
      void refresh().catch(() => undefined)
      void refreshAllowance(language.code)
    }
  }

  const destination = ready.length ? (ready.some((draft) => draft.category) ? 'the selected categories' : `${target.name}${target.terms + ready.length > limit ? ' and the next file' : ''}`) : ''

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-8">
        <div className="flex flex-wrap items-start justify-between gap-3"><p className="flex items-center gap-2 text-sm font-medium text-accent">
          <BookPlus aria-hidden className="size-4" />
          {language.name} · Your notebook
        </p><ReturnToExercise /></div>
        <h1 className="serif-text mt-2 text-4xl tracking-tight sm:text-5xl">Add</h1>
        {available !== null && <p role={available <= 3 ? "status" : undefined} className={`mt-3 text-sm ${available <= 3 ? "font-semibold text-warn" : "text-muted"}`}>{available <= 3 ? "Low word credit · " : ""}{available} {available === 1 ? 'word' : 'words'} available to add in {language.name} · {5 - (allowance?.reviews_toward_next ?? 0)} successful reviews until the next word{language.code === 'EN' ? ' · Phrasal verbs are unlimited' : ''}</p>}
        <p className="mt-3 max-w-xl text-[17px] leading-relaxed text-muted">
          Type the words you met. Each one gets a full entry in your usual format — definition, grammar, examples,
          translations — which you can check and edit before it goes into the latest file.
        </p>
      </div>

      <AnimatePresence>{report?.language === language.code && <Report report={report} onClose={() => setReport(null)} onReturn={() => navigate('/read')} />}</AnimatePresence>

      <div className="rounded-2xl border border-line bg-surface p-5 shadow-sm sm:p-7">
        <div className="flex flex-wrap items-center gap-1.5">
          <label className="text-sm text-muted">Category
            <select value={activeCategory} onChange={(event) => setCategory(event.target.value as Category)} className="ml-2 rounded-xl border border-line bg-surface px-3 py-2 text-ink">
              {categoriesFor(language.code).map((option) => <option key={option} value={option}>{categoryLabels[option]}</option>)}
            </select>
          </label>
          <button
            type="button"
            disabled={translateDisabled}
            onClick={() => translate(text)}
            aria-keyshortcuts={MAC ? 'Alt+Meta+T' : 'Control+Alt+T'}
            title={`Translate the text in the box, with short grammar notes; nothing is saved (${TRANSLATE_KEYS})`}
            className="inline-flex cursor-pointer items-center gap-1.5 rounded-xl border border-dashed border-accent/60 px-3 py-2 text-sm font-medium text-accent transition hover:border-accent hover:bg-accent-soft disabled:pointer-events-none disabled:opacity-45 sm:ml-auto"
          >
            <Languages aria-hidden className="size-4" />
            Translate
            <span className="ml-1 hidden sm:inline-flex pointer-coarse:hidden">
              <Kbd>{TRANSLATE_KEYS}</Kbd>
            </span>
          </button>
        </div>
        <p className="mt-3 flex items-center gap-1.5 text-sm text-muted">
          <FilePlus2 aria-hidden className="size-4" />
          {target.isNew ? (
            <>New entries start vocabulary/{language.name.toLowerCase()}/{target.name}</>
          ) : (
            <>
              New entries go into vocabulary/{language.name.toLowerCase()}/{target.name} · {target.terms} of {limit}
            </>
          )}
        </p>

        <textarea
          ref={inputRef}
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
              event.preventDefault()
              submit()
            }
          }}
          rows={4}
          aria-label={`${language.name} vocabulary, one per line`}
          placeholder={PLACEHOLDERS[language.code]}
          className="serif-text mt-5 w-full resize-y rounded-2xl border border-line bg-bg px-4 py-3 text-lg leading-relaxed outline-none placeholder:text-muted/60 focus:border-accent"
        />
        <DictationButton key={language.code} language={language.code} disabled={false} label="Speak a word or sentence" onBusyChange={setDictating} onTranscript={(transcript) => {
          const line = transcript.replace(/\s+/g, ' ').trim()
          setText((current) => current ? `${current}${current.endsWith('\n') ? '' : '\n'}${line}` : line)
        }} />
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
          <p className="min-w-0 flex-1 text-sm text-muted">
            One per line. Add a note after a dash to pick a sense.
          </p>
          <Button icon={Sparkles} disabled={!text.trim() || dictating} onClick={submit}>
            Write entries
            <span className="ml-1 hidden sm:inline-flex pointer-coarse:hidden">
              <Kbd tone="accent">⌘↵</Kbd>
            </span>
          </Button>
        </div>

        <AnimatePresence>
          {translation && translation.language === language.code && (
            <TranslationPanel state={translation} onClose={closeTranslation} onRetry={() => translate(translation.phrase)} />
          )}
        </AnimatePresence>
      </div>

      {visible.length > 0 && (
        <div className="mt-8">
          <div className="sticky top-[var(--languages-header-height,4rem)] z-10 -mx-4 mb-4 flex flex-wrap items-center gap-3 border-b border-line/70 bg-bg/85 px-4 py-3 backdrop-blur-md sm:mx-0 sm:rounded-2xl sm:border">
            <p className="min-w-0 flex-1 text-sm text-muted">
              <span className="font-semibold text-ink">{ready.length}</span> of {plural(visible.length, 'entry', 'entries')} ready
              {destination ? ` · into ${destination}` : ''}
            </p>
            {!busy && visible.length > ready.length && (
              <Button
                variant="ghost"
                size="sm"
                icon={Trash2}
                onClick={() => setDrafts((current) => current.filter((draft) => draft.language !== language.code || draft.status !== 'error'))}
              >
                Clear failed
              </Button>
            )}
            <Button icon={saving ? LoaderCircle : Check} spinning={saving} disabled={!savable.length || saving} onClick={() => void save()}>
              {savable.length ? `Add ${plural(savable.length, 'entry', 'entries')}` : 'Add'}
            </Button>
          </div>

          {saveError?.language === language.code && (
            <div className="mb-4">
              <Notice tone="error">{saveError.message}</Notice>
            </div>
          )}

          <div className="space-y-4">
            <AnimatePresence initial={false}>
              {[...visible].reverse().map((draft) => (
                <DraftCard
                  key={draft.id}
                  draft={draft}
                  onCategory={(category) => update(draft.id, { category })}
                  onRemove={() => remove(draft.id)}
                  onRetry={() => retry(draft.id)}
                  onEdit={(markdown) => update(draft.id, { markdown, term: headingOf(markdown) })}
                />
              ))}
            </AnimatePresence>
          </div>
        </div>
      )}

      {visible.length === 0 && report?.language !== language.code && (
        <p className="mt-8 flex items-center justify-center gap-2 text-sm text-muted">
          <CircleAlert aria-hidden className="size-4" />
          Entries are written by the model; read them before you add them.
        </p>
      )}
    </div>
  )
}
