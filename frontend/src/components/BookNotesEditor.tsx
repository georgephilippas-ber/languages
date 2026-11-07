import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import MarkdownIt from 'markdown-it'
import katex from 'katex'
import texmath from 'markdown-it-texmath'
import 'katex/dist/katex.min.css'
import { api, messageOf } from '../api'
import type { Book } from '../types'
import { TOOLBAR, applyAction, headingShortcut, type EditorAction } from '../lib/bookEditor'
import { Button } from './Button'
import { ConfirmDialog } from './ConfirmDialog'
import type { LintOutcome } from '../lib/bookLint'
import { CheckCheck, ChevronDown, ClipboardCheck, RotateCcw } from 'lucide-react'
import './book-notes.css'

const markdown = new MarkdownIt({ html: false, linkify: true, breaks: false }).use(texmath, {
  engine: katex, delimiters: 'dollars', katexOptions: { throwOnError: false, trust: false, strict: 'ignore' },
})

export function BookNotesEditor({ book, onClose }: { book: Book; onClose: () => void }) {
  const [text, setText] = useState('')
  const [saved, setSaved] = useState('')
  const [revision, setRevision] = useState(0)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [confirmClose, setConfirmClose] = useState(false)
  const [lintResult, setLintResult] = useState<LintOutcome | null>(null)
  const [lintUndo, setLintUndo] = useState<string | null>(null)
  const [linting, setLinting] = useState(false)
  const textRef = useRef(text)
  textRef.current = text
  const [mode, setMode] = useState<'split' | 'write' | 'preview'>('split')
  const dialog = useRef<HTMLDialogElement>(null)
  const advanced = useRef<HTMLDetailsElement>(null)
  const input = useRef<HTMLTextAreaElement>(null)
  const dirty = text !== saved
  const preview = useMemo(() => markdown.render(text), [text])
  useEffect(() => { dialog.current?.showModal() }, [])
  useEffect(() => { const dismiss = (event: PointerEvent) => { if (advanced.current && !advanced.current.contains(event.target as Node)) advanced.current.open = false }; document.addEventListener('pointerdown', dismiss); return () => document.removeEventListener('pointerdown', dismiss) }, [])
  useEffect(() => { let active = true; api.bookNotes(book.id).then((value) => { if (active) { setText(value.markdown); setSaved(value.markdown); setRevision(value.revision) } }).catch((reason: unknown) => { if (active) setError(messageOf(reason)) }).finally(() => { if (active) setLoading(false) }); return () => { active = false } }, [book.id])
  useEffect(() => { const warn = (event: BeforeUnloadEvent) => { if (dirty) event.preventDefault() }; window.addEventListener('beforeunload', warn); return () => window.removeEventListener('beforeunload', warn) }, [dirty])
  const close = () => { if (saving) return; if (dirty) setConfirmClose(true); else onClose() }
  const save = async () => {
    if (saving || loading || !dirty) return
    setSaving(true); setError('')
    try { const result = await api.saveBookNotes(book.id, text, revision); setSaved(result.markdown); setRevision(result.revision) }
    catch (reason) { setError(messageOf(reason)) } finally { setSaving(false) }
  }
  const action = (item: EditorAction) => {
    const element = input.current
    if (!element) return
    const result = applyAction(text, element.selectionStart, element.selectionEnd, item)
    setLintResult(null); setLintUndo(null)
    setText(result.text)
    requestAnimationFrame(() => { element.focus(); element.setSelectionRange(result.start, result.end) })
  }
  const runLint = async () => {
    if (loading || linting) return
    setLinting(true)
    const before = textRef.current
    try {
      const { lintMarkdown } = await import('../lib/bookLint')
      if (textRef.current !== before) { setError('Notes changed while checking. Please run the linter again.'); return }
      const result = lintMarkdown(before)
      setError('')
      if (result.text !== before) { setLintUndo(before); setText(result.text) }
      setLintResult(result)
    } catch (reason) { setError(`Could not check Markdown: ${messageOf(reason)}`) }
    finally { setLinting(false) }
  }
  const jumpToLine = (line: number) => {
    setMode('split')
    requestAnimationFrame(() => {
      const el = input.current
      if (!el) return
      const lines = el.value.split('\n'), index = Math.min(Math.max(line - 1, 0), lines.length - 1)
      const start = lines.slice(0, index).reduce((sum, value) => sum + value.length + 1, 0)
      el.focus(); el.setSelectionRange(start, start + lines[index].length)
      el.scrollTop = Math.max(0, (index - 3) * (parseFloat(getComputedStyle(el).lineHeight) || 24))
    })
  }
  const toolButton = (item: EditorAction) => <button key={item.id} type="button" title={item.title ?? item.id} aria-label={item.title ?? item.id} onMouseDown={(event) => event.preventDefault()} onClick={() => { setLintResult(null); action(item) }} disabled={loading || mode === 'preview'} className="notes-tool">{item.math ? <span aria-hidden dangerouslySetInnerHTML={{ __html: katex.renderToString(item.label.replace(/^\$|\$$/g, ''), { throwOnError: false, trust: false }) }} /> : item.label}</button>
  return createPortal(<><dialog ref={dialog} aria-labelledby="notes-title" onCancel={(event) => { event.preventDefault(); close() }} onKeyDown={(event) => {
    event.stopPropagation()
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') { event.preventDefault(); void save(); return }
    const heading = headingShortcut(event.nativeEvent)
    const format = (event.metaKey || event.ctrlKey) && !event.altKey && !event.shiftKey ? ({ b: 'bold', i: 'italic' } as Record<string, string>)[event.key.toLowerCase()] : undefined
    const id = heading || format
    if (id && document.activeElement === input.current) { const item = TOOLBAR.flatMap((group) => group.actions).find((candidate) => candidate.id === id); if (item) { event.preventDefault(); action(item) } }
  }} className="m-auto flex h-[min(92vh,64rem)] max-h-[92vh] w-[min(96vw,90rem)] max-w-none flex-col overflow-hidden rounded-2xl border border-line bg-surface p-0 text-ink shadow-2xl backdrop:bg-black/45">
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4"><div className="min-w-0"><h2 id="notes-title" className="text-lg font-semibold">Book notes</h2><p className="truncate text-sm text-muted">{book.title}</p></div><div className="flex items-center gap-2"><span role="status" className="text-sm text-muted">{loading ? 'Loading…' : dirty ? 'Unsaved changes' : 'Saved'}</span><Button variant="secondary" onClick={close} disabled={saving}>Close</Button><Button onClick={() => void save()} disabled={loading || saving || !dirty}>{saving ? 'Saving…' : 'Save notes'}</Button></div></div>
    <div className="notes-toolbar border-b border-line px-4 py-3 sm:px-5">
      <div className="notes-toolbar-row" role="toolbar" aria-label="Markdown formatting toolbar">
        <div className="notes-tool-group" aria-label="Heading levels"><span className="notes-tool-label">Heading</span>{TOOLBAR[0].actions.filter((item) => /^h[1-6]$/.test(item.id)).map(toolButton)}</div>
        <div className="notes-tool-group" aria-label="Text formatting"><span className="notes-tool-label">Format</span>{TOOLBAR[1].actions.map(toolButton)}</div>
        <div className="notes-tool-group" aria-label="Lists and blocks"><span className="notes-tool-label">Insert</span>{TOOLBAR[0].actions.filter((item) => !/^h[1-6]$/.test(item.id)).map(toolButton)}</div>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <details ref={advanced} className="notes-advanced"><summary><span>Math & symbols</span><ChevronDown aria-hidden size={14} /></summary><div className="notes-advanced-content">{TOOLBAR.slice(2).map((group) => <div key={group.name} className="notes-tool-group"><span className="notes-tool-label">{group.name}</span>{group.actions.map(toolButton)}</div>)}</div></details>
        <div className="flex flex-wrap items-center gap-2"><button type="button" onClick={() => void runLint()} disabled={loading || linting} className="notes-check"><ClipboardCheck aria-hidden size={15} />{linting ? 'Checking…' : 'Check Markdown'}</button>{lintUndo !== null && <button type="button" onClick={() => { setText(lintUndo); setLintUndo(null); setLintResult(null) }} className="notes-check" title="Undo the last automatic fixes"><RotateCcw aria-hidden size={14} />Undo fixes</button>}
          <div className="notes-view-toggle" aria-label="Editor view">{(['split', 'write', 'preview'] as const).map((view) => <button key={view} type="button" aria-pressed={mode === view} onClick={() => setMode(view)}>{view === 'split' ? 'Split' : view === 'write' ? 'Write' : 'Preview'}</button>)}</div>
        </div>
      </div>
    </div>
    {lintResult && <section aria-label="Markdown check results" className="max-h-32 shrink-0 overflow-auto border-b border-line bg-accent-soft px-5 py-2 text-sm"><div className="flex items-center justify-between gap-3"><p className="flex items-center gap-2 font-medium"><CheckCheck aria-hidden size={16} />{lintResult.fixed ? `Fixed ${lintResult.fixed} issue${lintResult.fixed === 1 ? '' : 's'}` : 'No automatic fixes'} · {lintResult.issues.length ? `${lintResult.issues.length} to review` : 'No other issues'}</p><button type="button" onClick={() => setLintResult(null)} className="text-xs underline">Close</button></div>{lintResult.mathGuard && <p className="mt-1 text-bad">{lintResult.mathGuard}</p>}{lintResult.issues.length > 0 && <ul className="mt-1 space-y-1">{lintResult.issues.map((issue, index) => <li key={`${issue.line}-${issue.rule}-${index}`}><button type="button" onClick={() => jumpToLine(issue.line)} className="text-left text-xs hover:underline">Line {issue.line} · {issue.rule} · {issue.description}{issue.detail ? ` — ${issue.detail}` : ''}</button></li>)}</ul>}</section>}
    {error && <p role="alert" className="border-b border-line px-5 py-2 text-sm text-bad">{error}</p>}
    <div className={`grid min-h-0 flex-1 ${mode === 'split' ? 'grid-rows-2 md:grid-cols-2 md:grid-rows-1' : 'grid-cols-1'}`}>
      {mode !== 'preview' && <textarea ref={input} aria-label="Markdown notes" value={text} onChange={(event) => { setText(event.target.value); setLintResult(null); setLintUndo(null) }} disabled={loading || (!!error && !saved && revision === 0 && !dirty)} placeholder="Write the important concepts here…" spellCheck className="h-full min-h-0 w-full resize-none border-b border-line bg-bg p-5 font-mono text-sm leading-6 outline-none md:border-b-0 md:border-r" />}
      {mode !== 'write' && <div className="overflow-auto p-5"><p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">Preview</p><article aria-label="Notes preview" className="book-notes-preview" dangerouslySetInnerHTML={{ __html: preview || '<p>Start writing to see a preview.</p>' }} /></div>}
    </div>
    <p className="border-t border-line px-5 py-2 text-xs text-muted">Markdown and LaTeX supported · {text.length.toLocaleString()} characters · ⌘/Ctrl+S to save</p>
  </dialog><ConfirmDialog open={confirmClose} title="Discard unsaved notes?" body="Your changes have not been saved." confirmLabel="Discard changes" cancelLabel="Keep editing" onConfirm={onClose} onCancel={() => setConfirmClose(false)} /></>, document.body)
}
