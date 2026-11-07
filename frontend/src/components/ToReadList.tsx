import { useEffect, useRef, useState, type Dispatch, type FormEvent, type SetStateAction } from 'react'
import { createPortal } from 'react-dom'
import { BookOpen, BookmarkPlus, Pencil, Trash2 } from 'lucide-react'
import { api, ApiError, messageOf } from '../api'
import type { Book, ToReadBook, ToReadCategory, ToReadInput } from '../types'
import { Button } from './Button'
import { ConfirmDialog } from './ConfirmDialog'
import { bookFieldsProblem } from '../lib/bookValidation'

export const TO_READ_CATEGORIES: { id: ToReadCategory; name: string }[] = [
  { id: 'work', name: 'Work' }, { id: 'education', name: 'Education' },
  { id: 'personal-development', name: 'Personal Development' }, { id: 'literature', name: 'Literature' },
]
const field = 'mt-1.5 w-full rounded-xl border border-line bg-bg px-3 py-2.5 text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent/20'
export type ToReadDraft = { id?: string; value: ToReadInput }

export function ToReadEditor({ draft, onCancel, onSaved }: { draft: ToReadDraft; onCancel: () => void; onSaved: (book: ToReadBook) => void }) {
  const [value, setValue] = useState(draft.value)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => { ref.current?.showModal() }, [])
  const patch = (update: Partial<ToReadInput>) => setValue((current) => ({ ...current, ...update }))
  const submit = async (event: FormEvent) => {
    event.preventDefault(); if (saving) return
    const problem = bookFieldsProblem(value, draft.id ? draft.value.isbn : undefined)
    if (problem) { setError(problem); return }
    setSaving(true); setError('')
    try { onSaved(draft.id ? await api.updateToRead(draft.id, value) : await api.addToRead(value)) }
    catch (reason) { setError(messageOf(reason)) } finally { setSaving(false) }
  }
  return createPortal(<dialog ref={ref} aria-labelledby="to-read-editor-title" onCancel={(event) => { event.preventDefault(); onCancel() }} onClick={(event) => { if (event.target === ref.current) onCancel() }} onKeyDown={(event) => event.stopPropagation()} className="m-auto max-h-[90vh] w-[min(92vw,36rem)] overflow-auto rounded-2xl border border-line bg-surface p-0 text-ink shadow-2xl backdrop:bg-black/45">
    <form onSubmit={(event) => void submit(event)} className="p-6 sm:p-7"><h2 id="to-read-editor-title" className="text-xl font-semibold">{draft.id ? 'Edit To Read book' : 'Add to To Read'}</h2><div className="mt-5 grid gap-4 sm:grid-cols-2">
      <label className="text-sm font-medium sm:col-span-2">Title<input autoFocus required maxLength={500} value={value.title} onChange={(event) => patch({ title: event.target.value })} className={field} /></label>
      <label className="text-sm font-medium">Author<input maxLength={500} value={value.author} onChange={(event) => patch({ author: event.target.value })} className={field} /></label>
      <label className="text-sm font-medium">ISBN <span className="font-normal text-muted">(optional)</span><input maxLength={30} value={value.isbn} onChange={(event) => patch({ isbn: event.target.value })} className={field} /></label>
      <label className="text-sm font-medium">Language<input required maxLength={100} list="to-read-languages" value={value.language} onChange={(event) => patch({ language: event.target.value })} className={field} /><datalist id="to-read-languages"><option value="English" /><option value="German" /><option value="French" /></datalist></label>
      <label className="text-sm font-medium">Personal category<select value={value.category} onChange={(event) => patch({ category: event.target.value as ToReadCategory })} className={field}>{TO_READ_CATEGORIES.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>
    </div>{error && <p role="alert" className="mt-4 text-sm text-bad">{error}</p>}<div className="mt-6 flex justify-end gap-2"><Button variant="secondary" onClick={onCancel} disabled={saving}>Cancel</Button><Button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save to list'}</Button></div></form>
  </dialog>, document.body)
}

export function ToReadList({ items, onChanged, onEdit, onAdd, onStarted, onRefreshBooks, currentCount }: { onRefreshBooks: (books: Book[]) => void; currentCount: number; items: ToReadBook[]; onChanged: Dispatch<SetStateAction<ToReadBook[]>>; onEdit: (item: ToReadBook) => void; onAdd: () => void; onStarted: (book: Book) => void }) {
  const [remove, setRemove] = useState<ToReadBook | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { if (currentCount < 5) setError('') }, [currentCount])
  const erase = async () => {
    if (!remove || busy) return
    setBusy(true); setError('')
    try { await api.deleteToRead(remove.id); onChanged((current) => current.filter((item) => item.id !== remove.id)); setRemove(null) }
    catch (reason) { setError(messageOf(reason)); setRemove(null) } finally { setBusy(false) }
  }
  const start = async (item: ToReadBook) => {
    if (busy) return
    setBusy(true); setError('')
    try { const book = await api.startToRead(item.id); onChanged((current) => current.filter((entry) => entry.id !== item.id)); onStarted(book) }
    catch (reason) {
      if (reason instanceof ApiError && reason.status === 409 && reason.message.includes('current books')) {
        let count = currentCount
        try { const books = await api.books(); onRefreshBooks(books); count = books.filter((book) => book.status === 'current').length } catch { /* Keep the last known count. */ }
        const needed = Math.max(1, count - 4)
        setError(`You have ${count} current books. Move at least ${needed} to Done or remove ${needed === 1 ? 'one' : 'them'} before starting another.`)
      } else setError(messageOf(reason))
    } finally { setBusy(false) }
  }
  return <section aria-label="To Read list" className="mt-9 rounded-2xl border border-line bg-surface p-5 shadow-sm sm:p-6"><div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="serif-text text-2xl">To Read <span className="text-sm font-normal text-muted">{items.length}</span></h2><p className="mt-1 text-sm text-muted">Keep interesting books here until you’re ready to read them.</p></div><Button icon={BookmarkPlus} size="sm" variant="secondary" onClick={onAdd}>Add a book</Button></div>
    {currentCount >= 5 && <p className="mt-3 text-sm text-muted">Current has {currentCount} books; fewer than 5 are required to start another. <a href="#current-books" className="underline">Go to Current</a></p>}
    {error && <p role="alert" className="mt-3 text-sm text-bad">{error}</p>}
    <div className="mt-5 grid gap-4 sm:grid-cols-2">{TO_READ_CATEGORIES.map((category) => { const books = items.filter((item) => item.category === category.id); return <section key={category.id} aria-label={`${category.name} To Read`} className="rounded-xl border border-line p-4"><h3 className="text-sm font-semibold">{category.name} <span className="font-normal text-muted">{books.length}</span></h3>{books.length === 0 ? <p className="mt-3 text-sm text-muted">No books yet.</p> : <div className="mt-3 space-y-3">{books.map((book) => <article key={book.id} className="border-t border-line pt-3 first:border-0 first:pt-0"><p className="font-medium leading-snug">{book.title}</p><p className="mt-1 text-xs text-muted">{[book.author, book.language, book.isbn ? `ISBN ${book.isbn}` : ''].filter(Boolean).join(' · ')}</p><div className="mt-2 flex flex-wrap gap-1"><Button size="sm" variant="secondary" icon={BookOpen} onClick={() => void start(book)} disabled={busy}>Start reading</Button><Button size="sm" variant="ghost" icon={Pencil} onClick={() => onEdit(book)} disabled={busy} aria-label={`Edit ${book.title} in To Read`}>Edit</Button><Button size="sm" variant="ghost" icon={Trash2} onClick={() => setRemove(book)} disabled={busy} aria-label={`Remove ${book.title} from To Read`}>Remove</Button></div></article>)}</div>}</section> })}</div>
    <ConfirmDialog open={!!remove} title="Remove from To Read?" body={`Remove “${remove?.title ?? ''}” from your To Read list?`} confirmLabel="Remove" cancelLabel="Cancel" onConfirm={() => void erase()} onCancel={() => setRemove(null)} />
  </section>
}
