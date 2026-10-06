import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { BookPlus, Check, ChevronDown, CircleAlert, FilePlus2, LoaderCircle, Pencil, RotateCcw, Sparkles, Trash2, X } from 'lucide-react'
import { api, isAbort, messageOf } from '../api'
import { useMeta } from '../context/MetaContext'
import { usePersistentState } from '../hooks/usePersistentState'
import { cx } from '../lib/cx'
import { ENTRY_KINDS, KIND_FOLDERS, targetFile } from '../lib/entries'
import { plural } from '../lib/format'
import type { EntryKind, LanguageCode, SaveResult } from '../types'
import { Button } from '../components/Button'
import { Kbd } from '../components/Kbd'
import { Notice } from '../components/Notice'
import { Rich } from '../components/Rich'

type DraftStatus = 'queued' | 'loading' | 'ready' | 'error'

interface Draft {
  id: string
  language: LanguageCode
  kind: EntryKind
  request: string
  status: DraftStatus
  term?: string
  markdown?: string
  gloss?: string
  error?: string
}

interface SavedReport {
  kind: EntryKind
  result: SaveResult
  glosses: Record<string, string>
}

const MAX_PARALLEL = 3
const TRANSLATION_LABELS = ['English', 'German', 'French']
const SUMMARY_LABELS = ['CEFR', 'Definition', ...TRANSLATION_LABELS]
const PLACEHOLDERS: Record<LanguageCode, string> = {
  DE: 'die Krähe\netwas abdecken\ndas Gespür — the sense of having a feel for something',
  FR: 'le cafard\nse débrouiller\nrévélateur',
  EN: 'soporific\nto hedge one’s bets\nunpropitious',
}

function newId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
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
}: {
  draft: Draft
  onRemove: () => void
  onRetry: () => void
  onEdit: (markdown: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [editing, setEditing] = useState<string | null>(null)
  const problem = editing === null ? null : entryProblem(editing)
  const kindLabel = ENTRY_KINDS.find((option) => option.kind === draft.kind)

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
            {draft.kind !== 'vocabulary' && kindLabel && (
              <span className="ml-2 rounded-full bg-surface-2 px-2 py-0.5 text-xs font-medium">{kindLabel.one}</span>
            )}
          </p>
        </div>
        {draft.status === 'loading' || draft.status === 'queued' ? (
          <LoaderCircle aria-label="Writing" className="mt-1 size-5 shrink-0 animate-spin text-muted" />
        ) : null}
        <Button variant="ghost" size="sm" icon={Trash2} aria-label={`Remove ${draft.term ?? draft.request}`} title="Remove" onClick={onRemove} />
      </div>

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

function Report({ reports, onClose }: { reports: SavedReport[]; onClose: () => void }) {
  const { language } = useMeta()
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      role="status"
      className="mb-6 rounded-2xl border border-good/40 bg-good-soft p-5"
    >
      <div className="flex items-start gap-3">
        <Check aria-hidden className="mt-0.5 size-5 shrink-0 text-good" />
        <div className="min-w-0 flex-1 space-y-4 text-[15px] leading-relaxed">
          {reports.map(({ kind, result, glosses }) => {
            const files = [...new Set(result.saved.map((entry) => entry.fileName))]
            return (
              <div key={kind}>
                <p className="font-semibold">
                  {result.demo ? 'Demo, nothing was written: would add ' : 'Added '}
                  {plural(result.saved.length, 'entry', 'entries')} to {files.map((file) => `${KIND_FOLDERS[kind]}/${language.name.toLowerCase()}/${file}`).join(' and ')}
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
              </div>
            )
          })}
        </div>
        <Button variant="ghost" size="sm" icon={X} aria-label="Close" onClick={onClose} />
      </div>
    </motion.div>
  )
}

export function AddPage() {
  const { meta, language, refresh } = useMeta()
  const [kind, setKind] = usePersistentState<EntryKind>('add.kind', 'vocabulary')
  const [text, setText] = useState('')
  const [drafts, setDrafts] = usePersistentState<Draft[]>('drafts', [])
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [reports, setReports] = useState<SavedReport[]>([])
  const controllers = useRef(new Map<string, AbortController>())
  const limit = meta.defaults.maxTermsPerFile

  const update = (id: string, patch: Partial<Draft>) =>
    setDrafts((current) => current.map((draft) => (draft.id === id ? { ...draft, ...patch } : draft)))

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
        .define(draft.language, draft.kind, draft.request, controller.signal)
        .then((entry) => update(draft.id, { status: 'ready', term: entry.term, markdown: entry.markdown, gloss: entry.gloss }))
        .catch((error: unknown) => {
          if (!isAbort(error)) update(draft.id, { status: 'error', error: messageOf(error) })
        })
        .finally(() => controllers.current.delete(draft.id))
    }
  })

  const visible = drafts.filter((draft) => draft.language === language.code)
  const ready = visible.filter((draft) => draft.status === 'ready' && draft.markdown)
  const busy = visible.some((draft) => draft.status === 'loading' || draft.status === 'queued')
  const target = targetFile(language, kind, limit)
  const kindInfo = ENTRY_KINDS.find((option) => option.kind === kind) ?? ENTRY_KINDS[0]

  const submit = () => {
    const lines = text
      .split('\n')
      .map((line) => line.split(/\s+/).filter(Boolean).join(' '))
      .filter(Boolean)
    if (!lines.length) return
    setDrafts((current) => [
      ...current,
      ...lines.map((line): Draft => ({ id: newId(), language: language.code, kind, request: line, status: 'queued' })),
    ])
    setText('')
    setReports([])
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
    if (!ready.length || saving) return
    setSaving(true)
    setSaveError(null)
    const done: SavedReport[] = []
    try {
      for (const option of ENTRY_KINDS) {
        const group = ready.filter((draft) => draft.kind === option.kind)
        if (!group.length) continue
        const result = await api.save(language.code, option.kind, group.map((draft) => draft.markdown ?? ''))
        const glosses = Object.fromEntries(group.map((draft) => [draft.term ?? '', draft.gloss ?? '']))
        done.push({ kind: option.kind, result, glosses })
        const ids = new Set(group.map((draft) => draft.id))
        setDrafts((current) => current.filter((draft) => !ids.has(draft.id)))
      }
    } catch (error) {
      setSaveError(messageOf(error))
    } finally {
      setReports(done)
      setSaving(false)
      void refresh().catch(() => undefined)
    }
  }

  const readyKinds = new Set(ready.map((draft) => draft.kind))
  const destination = [...readyKinds].map((value) => {
    const count = ready.filter((draft) => draft.kind === value).length
    const file = targetFile(language, value, limit)
    const overflow = file.terms + count > limit
    return `${file.name}${overflow ? ' and the next file' : ''}`
  })

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-8">
        <p className="flex items-center gap-2 text-sm font-medium text-accent">
          <BookPlus aria-hidden className="size-4" />
          {language.name} · Your notebook
        </p>
        <h1 className="serif-text mt-2 text-4xl tracking-tight sm:text-5xl">Add</h1>
        <p className="mt-3 max-w-xl text-[17px] leading-relaxed text-muted">
          Type the words you met. Each one gets a full entry in your usual format — definition, grammar, examples,
          translations — which you can check and edit before it goes into the latest file.
        </p>
      </div>

      <AnimatePresence>{reports.length > 0 && <Report reports={reports} onClose={() => setReports([])} />}</AnimatePresence>

      <div className="rounded-3xl border border-line bg-surface p-5 shadow-sm sm:p-7">
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Kind of entry">
          {ENTRY_KINDS.map((option) => (
            <button
              key={option.kind}
              type="button"
              aria-pressed={kind === option.kind}
              onClick={() => setKind(option.kind)}
              className={cx(
                'cursor-pointer rounded-xl border px-3 py-2 text-sm font-medium transition',
                kind === option.kind
                  ? 'border-accent bg-accent-soft text-ink shadow-sm'
                  : 'border-line bg-surface text-muted hover:border-accent/50 hover:text-ink',
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
        <p className="mt-3 flex items-center gap-1.5 text-sm text-muted">
          <FilePlus2 aria-hidden className="size-4" />
          {target.isNew ? (
            <>New entries start {KIND_FOLDERS[kind]}/{language.name.toLowerCase()}/{target.name}</>
          ) : (
            <>
              New entries go into {KIND_FOLDERS[kind]}/{language.name.toLowerCase()}/{target.name} · {target.terms} of {limit}
            </>
          )}
        </p>

        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
              event.preventDefault()
              submit()
            }
          }}
          rows={4}
          aria-label={`${language.name} ${kindInfo.label.toLowerCase()}, one per line`}
          placeholder={PLACEHOLDERS[language.code]}
          className="serif-text mt-5 w-full resize-y rounded-2xl border border-line bg-bg px-4 py-3 text-lg leading-relaxed outline-none placeholder:text-muted/60 focus:border-accent"
        />
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
          <p className="min-w-0 flex-1 text-sm text-muted">
            One per line. Add a note after a dash to pick a sense.
            {meta.demo ? ' Demo mode: placeholder entries, nothing is saved.' : ''}
          </p>
          <Button icon={Sparkles} disabled={!text.trim()} onClick={submit}>
            Write entries
            <span className="ml-1 hidden sm:inline-flex pointer-coarse:hidden">
              <Kbd tone="accent">⌘↵</Kbd>
            </span>
          </Button>
        </div>
      </div>

      {visible.length > 0 && (
        <div className="mt-8">
          <div className="sticky top-16 z-10 -mx-4 mb-4 flex flex-wrap items-center gap-3 border-b border-line/70 bg-bg/85 px-4 py-3 backdrop-blur-md sm:mx-0 sm:rounded-2xl sm:border">
            <p className="min-w-0 flex-1 text-sm text-muted">
              <span className="font-semibold text-ink">{ready.length}</span> of {plural(visible.length, 'entry', 'entries')} ready
              {destination.length ? ` · into ${destination.join(', ')}` : ''}
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
            <Button icon={saving ? LoaderCircle : Check} spinning={saving} disabled={!ready.length || saving} onClick={() => void save()}>
              {ready.length ? `Add ${plural(ready.length, 'entry', 'entries')}` : 'Add'}
            </Button>
          </div>

          {saveError && (
            <div className="mb-4">
              <Notice tone="error">{saveError}</Notice>
            </div>
          )}

          <div className="space-y-4">
            <AnimatePresence initial={false}>
              {visible.map((draft) => (
                <DraftCard
                  key={draft.id}
                  draft={draft}
                  onRemove={() => remove(draft.id)}
                  onRetry={() => retry(draft.id)}
                  onEdit={(markdown) => update(draft.id, { markdown, term: headingOf(markdown) })}
                />
              ))}
            </AnimatePresence>
          </div>
        </div>
      )}

      {visible.length === 0 && reports.length === 0 && (
        <p className="mt-8 flex items-center justify-center gap-2 text-sm text-muted">
          <CircleAlert aria-hidden className="size-4" />
          Entries are written by the model; read them before you add them.
        </p>
      )}
    </div>
  )
}
