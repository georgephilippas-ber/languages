import { useEffect, useState, type FormEvent } from 'react'
import { api, messageOf } from '../api'
import type { Book } from '../types'
import { Button } from './Button'

export function BookProgress({ book, onSaved }: { book: Book; onSaved: (book: Book) => void }) {
  const [mode, setMode] = useState<'percent' | 'page'>(book.currentPage === null ? 'percent' : 'page')
  const [percent, setPercent] = useState(String(book.progress))
  const [page, setPage] = useState(book.currentPage === null ? '' : String(book.currentPage))
  const [lastPage, setLastPage] = useState(book.lastReadablePage === null ? '' : String(book.lastReadablePage))
  const [total, setTotal] = useState<number | null>(book.totalPages)
  const [lookingUp, setLookingUp] = useState(false)
  const [lookedUp, setLookedUp] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const customEnd = lastPage.trim() === '' ? null : Number(lastPage)
  const validCustomEnd = customEnd === null || (Number.isInteger(customEnd) && customEnd >= 1 && customEnd <= 100000)
  const canEnterPage = customEnd !== null && validCustomEnd
  const end = canEnterPage ? customEnd : null
  const pageTooHigh = mode === 'page' && end !== null && page.trim() !== '' && Number(page) > end
  const updatePercent = (pageValue: string, endValue: number | null) => {
    if (pageValue.trim() !== '' && endValue && Number.isInteger(Number(pageValue)) && Number(pageValue) >= 0 && Number(pageValue) <= endValue) {
      setPercent(String(Math.min(100, Math.round(Number(pageValue) * 100 / endValue))))
    }
  }
  useEffect(() => {
    if (mode === 'page') updatePercent(page, end)
  }, [mode, page, end])
  const lookupPages = async () => {
    if (total || !book.isbn || lookedUp || lookingUp || customEnd !== null) return
    setLookingUp(true); setLookedUp(true)
    try {
      const result = await api.bookPageCount(book.id)
      setTotal(result.totalPages)
    } catch { /* Manual page count and percentage remain available. */ } finally { setLookingUp(false) }
  }
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const value = Number(mode === 'page' ? page : percent)
    if (!validCustomEnd) { setError('Enter a whole last page between 1 and 100,000.'); return }
    if (saving || (mode === 'page' ? !end || page.trim() === '' || !Number.isInteger(value) || value < 0 || value > 100000 || value > end : percent.trim() === '' || !Number.isInteger(value) || value < 0 || value > 100)) {
      setError(mode === 'page' ? (end && value > end ? `Current page cannot exceed ${customEnd !== null ? 'the last readable page' : 'the total pages'} (${end}).` : 'Enter a valid current page and a last readable page.') : 'Enter a whole percentage between 0 and 100.')
      return
    }
    setSaving(true); setError('')
    try {
      const updated = await api.updateBookProgress(book.id, mode === 'percent' ? value : book.progress, mode === 'page' ? value : undefined, mode === 'page' ? total ?? undefined : undefined, customEnd)
      setPercent(String(updated.progress)); setPage(updated.currentPage === null ? '' : String(updated.currentPage)); setLastPage(updated.lastReadablePage === null ? '' : String(updated.lastReadablePage)); setTotal(updated.totalPages)
      onSaved(updated)
    } catch (reason) { setError(messageOf(reason)) } finally { setSaving(false) }
  }
  return <form onSubmit={(event) => void submit(event)} className="mt-4 rounded-xl border border-line bg-bg p-3" aria-label={`Update progress for ${book.title}`}>
    <p className="mb-2 text-xs font-semibold text-muted">Reading progress</p>
    <fieldset disabled={saving} className="flex flex-wrap items-end gap-2">
      <label className="text-xs font-medium">Current page<input aria-label="Current page" type="number" min="0" max={end ?? 100000} step="1" disabled={!canEnterPage} aria-describedby={!canEnterPage ? `last-page-help-${book.id}` : undefined} aria-invalid={pageTooHigh || undefined} value={page} onChange={(event) => { const next = event.target.value; setPage(next); setMode(next.trim() ? 'page' : 'percent'); setError(''); updatePercent(next, end) }} placeholder="Page" className="mt-1 block w-20 rounded-lg border border-line bg-surface px-2 py-1.5 text-sm disabled:bg-surface-2 disabled:opacity-50" /></label>
      <label className="text-xs font-medium">Last readable page<input aria-label="Last readable page" type="number" min="1" max="100000" step="1" value={lastPage} onFocus={() => void lookupPages()} onChange={(event) => { const next = event.target.value; setLastPage(next); setError(''); if (mode === 'page') { const custom = next.trim() === '' ? null : Number(next); updatePercent(page, custom && custom > 0 ? custom : null) } }} placeholder={total === null ? 'Last page' : String(total)} className="mt-1 block w-24 rounded-lg border border-line bg-surface px-2 py-1.5 text-sm" /></label>
      <label className="text-xs font-medium">Complete (%)<input aria-label="Completion (%)" type="number" min="0" max="100" step="1" value={percent} onChange={(event) => { setPercent(event.target.value); setPage(''); setMode('percent'); setError('') }} className="mt-1 block w-20 rounded-lg border border-line bg-surface px-2 py-1.5 text-sm" /></label>
      <Button type="submit" size="sm" disabled={saving || (mode === 'page' && !canEnterPage)}>{saving ? 'Saving…' : 'Save'}</Button>
    </fieldset>
    {pageTooHigh ? <p role="alert" className="mt-2 text-xs text-bad">Current page cannot exceed the last readable page ({end}).</p> : <p id={`last-page-help-${book.id}`} className="mt-2 text-xs text-muted">{lookingUp ? 'Looking up the catalogue page count…' : end === null ? `Enter the last readable page to enable current page.${total !== null ? ` Catalogue total: ${total} pages.` : ''}` : mode === 'page' && page.trim() !== '' && Number(page) >= 0 ? `${Math.round(Number(page) * 100 / end)}% complete · last readable page ${end}` : `Progress uses your last readable page: ${end}.`}</p>}
    {error && <p role="alert" className="mt-2 text-sm text-bad">{error}</p>}
  </form>
}
