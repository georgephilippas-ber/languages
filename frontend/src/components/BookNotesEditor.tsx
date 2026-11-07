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
  const [mode, setMode] = useState<'split' | 'write' | 'preview'>('split')
  const dialog = useRef<HTMLDialogElement>(null)
  const input = useRef<HTMLTextAreaElement>(null)
  const dirty = text !== saved
  const preview = useMemo(() => markdown.render(text), [text])
  useEffect(() => { dialog.current?.showModal() }, [])
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
    setText(result.text)
    requestAnimationFrame(() => { element.focus(); element.setSelectionRange(result.start, result.end) })
  }
  return createPortal(<><dialog ref={dialog} aria-labelledby="notes-title" onCancel={(event) => { event.preventDefault(); close() }} onKeyDown={(event) => {
    event.stopPropagation()
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') { event.preventDefault(); void save(); return }
    const heading = headingShortcut(event.nativeEvent)
    const format = (event.metaKey || event.ctrlKey) && !event.altKey && !event.shiftKey ? ({ b: 'bold', i: 'italic' } as Record<string, string>)[event.key.toLowerCase()] : undefined
    const id = heading || format
    if (id && document.activeElement === input.current) { const item = TOOLBAR.flatMap((group) => group.actions).find((candidate) => candidate.id === id); if (item) { event.preventDefault(); action(item) } }
  }} className="m-auto flex h-[min(92vh,64rem)] max-h-[92vh] w-[min(96vw,90rem)] max-w-none flex-col overflow-hidden rounded-2xl border border-line bg-surface p-0 text-ink shadow-2xl backdrop:bg-black/45">
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4"><div className="min-w-0"><h2 id="notes-title" className="text-lg font-semibold">Book notes</h2><p className="truncate text-sm text-muted">{book.title}</p></div><div className="flex items-center gap-2"><span role="status" className="text-sm text-muted">{loading ? 'Loading…' : dirty ? 'Unsaved changes' : 'Saved'}</span><Button variant="secondary" onClick={close} disabled={saving}>Close</Button><Button onClick={() => void save()} disabled={loading || saving || !dirty}>{saving ? 'Saving…' : 'Save notes'}</Button></div></div>
    <div className="border-b border-line px-5 py-3"><div className="flex flex-wrap items-start gap-x-4 gap-y-2" aria-label="Markdown formatting toolbar">{TOOLBAR.map((group) => <div key={group.name} className="flex flex-wrap items-center gap-1"><span className="mr-1 text-xs font-semibold text-muted">{group.name}</span>{group.actions.map((item) => <button key={item.id} type="button" title={item.title ?? item.id} aria-label={item.title ?? item.id} onMouseDown={(event) => event.preventDefault()} onClick={() => action(item)} disabled={loading || mode === 'preview'} className="rounded-lg border border-line px-2 py-1 text-xs hover:bg-surface-2 disabled:opacity-40">{item.label}</button>)}</div>)}</div><div className="mt-3 flex gap-1" aria-label="Editor view">{(['split', 'write', 'preview'] as const).map((view) => <button key={view} type="button" aria-pressed={mode === view} onClick={() => setMode(view)} className={`rounded-lg px-3 py-1 text-xs ${mode === view ? 'bg-accent-soft font-semibold text-accent' : 'text-muted hover:bg-surface-2'}`}>{view === 'split' ? 'Write & preview' : view === 'write' ? 'Write' : 'Preview'}</button>)}</div></div>
    {error && <p role="alert" className="border-b border-line px-5 py-2 text-sm text-bad">{error}</p>}
    <div className={`grid min-h-0 flex-1 ${mode === 'split' ? 'grid-rows-2 md:grid-cols-2 md:grid-rows-1' : 'grid-cols-1'}`}>
      {mode !== 'preview' && <textarea ref={input} aria-label="Markdown notes" value={text} onChange={(event) => setText(event.target.value)} disabled={loading || (!!error && !saved && revision === 0 && !dirty)} placeholder="Write the important concepts here…" spellCheck className="h-full min-h-0 w-full resize-none border-b border-line bg-bg p-5 font-mono text-sm leading-6 outline-none md:border-b-0 md:border-r" />}
      {mode !== 'write' && <div className="overflow-auto p-5"><p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">Preview</p><article aria-label="Notes preview" className="book-notes-preview" dangerouslySetInnerHTML={{ __html: preview || '<p>Start writing to see a preview.</p>' }} /></div>}
    </div>
    <p className="border-t border-line px-5 py-2 text-xs text-muted">Markdown and LaTeX supported · {text.length.toLocaleString()} characters · ⌘/Ctrl+S to save</p>
  </dialog><ConfirmDialog open={confirmClose} title="Discard unsaved notes?" body="Your changes have not been saved." confirmLabel="Discard changes" cancelLabel="Keep editing" onConfirm={onClose} onCancel={() => setConfirmClose(false)} /></>, document.body)
}
