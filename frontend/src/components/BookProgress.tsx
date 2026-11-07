import { useEffect, useState, type FormEvent } from 'react'
import { api, messageOf } from '../api'
import type { Book } from '../types'
import { Button } from './Button'

export function BookProgress({ book, onSaved, onCancel }: { book: Book; onSaved: (book: Book) => void; onCancel: () => void }) {
  const [mode, setMode] = useState<'percent' | 'page'>('percent')
  const [percent, setPercent] = useState(String(book.progress))
  const [page, setPage] = useState(book.currentPage === null ? '' : String(book.currentPage))
  const [total, setTotal] = useState<number | null>(book.totalPages)
  const [lookingUp, setLookingUp] = useState(!book.totalPages && !!book.isbn)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    if (book.totalPages || !book.isbn) return
    let active = true
    api.bookPageCount(book.id).then((result) => { if (active) setTotal(result.totalPages) }).catch(() => { /* Percentage entry remains available. */ }).finally(() => { if (active) setLookingUp(false) })
    return () => { active = false }
  }, [book.id, book.isbn, book.totalPages])
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const value = Number(mode === 'page' ? page : percent)
    if (saving || (mode === 'page' ? !total || page.trim() === '' || !Number.isInteger(value) || value < 0 || value > total : percent.trim() === '' || !Number.isInteger(value) || value < 0 || value > 100)) {
      setError(mode === 'page' ? `Enter a whole page number between 0 and ${total}.` : 'Enter a whole percentage between 0 and 100.')
      return
    }
    setSaving(true); setError('')
    try { onSaved(await api.updateBookProgress(book.id, mode === 'percent' ? value : book.progress, mode === 'page' ? value : undefined, mode === 'page' ? total! : undefined)) }
    catch (reason) { setError(messageOf(reason)) } finally { setSaving(false) }
  }
  return <form onSubmit={(event) => void submit(event)} className="mt-3 rounded-xl border border-line bg-bg p-3" aria-label={`Update progress for ${book.title}`}>
    <div className="flex flex-wrap items-end gap-2">
      <label className="text-xs font-medium">Update by<select aria-label="Progress method" value={mode} onChange={(event) => { setMode(event.target.value as 'percent' | 'page'); setError('') }} className="mt-1 block rounded-lg border border-line bg-surface px-2 py-1.5 text-sm"><option value="percent">Percentage</option>{total !== null && <option value="page">Page number</option>}</select></label>
      {mode === 'percent' ? <label className="text-xs font-medium">Completion (%)<input autoFocus type="number" min="0" max="100" step="1" value={percent} onChange={(event) => setPercent(event.target.value)} className="mt-1 block w-24 rounded-lg border border-line bg-surface px-2 py-1.5 text-sm" /></label> : <label className="text-xs font-medium">Current page <span className="font-normal text-muted">of {total}</span><input autoFocus type="number" min="0" max={total ?? undefined} step="1" value={page} onChange={(event) => setPage(event.target.value)} className="mt-1 block w-24 rounded-lg border border-line bg-surface px-2 py-1.5 text-sm" /></label>}
      <Button type="submit" size="sm" disabled={saving}>{saving ? 'Saving…' : 'Save'}</Button><Button size="sm" variant="ghost" onClick={onCancel} disabled={saving}>Cancel</Button>
    </div>
    <p className="mt-2 text-xs text-muted">{lookingUp ? 'Looking up the page count…' : total === null ? 'No page count available for this edition.' : mode === 'page' && page.trim() !== '' && Number(page) >= 0 && Number(page) <= total ? `${Math.round(Number(page) * 100 / total)}% complete · ${total} pages (Open Library)` : `${total} pages · Open Library`}</p>
    {error && <p role="alert" className="mt-2 text-sm text-bad">{error}</p>}
  </form>
}
