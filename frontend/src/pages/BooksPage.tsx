import { useEffect, useRef, useState, type FormEvent } from 'react'
import { createPortal } from 'react-dom'
import { BookOpen, Check, LibraryBig, Pencil, Plus, Search, Sparkles, Trash2 } from 'lucide-react'
import { api, isAbort, messageOf } from '../api'
import { useMeta } from '../context/MetaContext'
import type { Book, BookInput, BookCategory, BookSearchResult, BookRecommendation, BookCategoryInfo } from '../types'
import { Button } from '../components/Button'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { cx } from '../lib/cx'

const label = (category: BookCategory, categories: BookCategoryInfo[]) => categories.find((item) => item.id === category)?.name ?? category
const matches = (book: Book, category: BookCategory, categories: BookCategoryInfo[]) => category === 'all' || (category === 'non-fiction' ? book.category === 'non-fiction' || categories.some((item) => item.id === book.category && item.group === 'nonfiction') : book.category === category)
const field = 'mt-1.5 w-full rounded-xl border border-line bg-bg px-3 py-2.5 text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent/20'

type Draft = { id?: string; value: BookInput }

function BookEditor({ draft, categories, onCancel, onSaved }: { draft: Draft; categories: BookCategoryInfo[]; onCancel: () => void; onSaved: (book: Book) => void }) {
  const [value, setValue] = useState(draft.value)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => { dialog.current?.showModal() }, [])
  const update = (patch: Partial<BookInput>) => setValue((current) => ({ ...current, ...patch }))
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (saving) return
    setSaving(true); setError('')
    try {
      const book = draft.id ? await api.updateBook(draft.id, value) : await api.addBook(value)
      onSaved(book)
    } catch (reason) { setError(messageOf(reason)) } finally { setSaving(false) }
  }
  return createPortal(<dialog ref={dialog} aria-labelledby="book-editor-title" onCancel={(event) => { event.preventDefault(); onCancel() }} onClick={(event) => { if (event.target === dialog.current) onCancel() }} onKeyDown={(event) => event.stopPropagation()} className="m-auto max-h-[90vh] w-[min(92vw,36rem)] overflow-auto rounded-2xl border border-line bg-surface p-0 text-ink shadow-2xl backdrop:bg-black/45">
    <form onSubmit={(event) => void submit(event)} className="p-6 sm:p-7">
      <h2 id="book-editor-title" className="text-xl font-semibold">{draft.id ? 'Edit book' : 'Add to your books'}</h2>
      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <label className="text-sm font-medium sm:col-span-2">Title<input autoFocus required maxLength={500} value={value.title} onChange={(event) => update({ title: event.target.value })} className={field} /></label>
        <label className="text-sm font-medium">Author<input maxLength={500} value={value.author} onChange={(event) => update({ author: event.target.value })} className={field} /></label>
        <label className="text-sm font-medium">ISBN <span className="font-normal text-muted">(optional)</span><input maxLength={30} value={value.isbn} onChange={(event) => update({ isbn: event.target.value })} className={field} /></label>
        <label className="text-sm font-medium">Language<input required maxLength={100} list="book-languages" value={value.language} onChange={(event) => update({ language: event.target.value })} className={field} /><datalist id="book-languages"><option value="English" /><option value="German" /><option value="French" /></datalist></label>
        <label className="text-sm font-medium">Category<select value={value.category} onChange={(event) => update({ category: event.target.value as BookCategory })} className={field}>
          <option value="fiction">Fiction</option><optgroup label="Non-fiction"><option value="non-fiction">Non-fiction</option>{categories.filter((item) => item.group === 'nonfiction').map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</optgroup><option value="other">Other</option>
        </select></label>
        <label className="text-sm font-medium">Completion (%)<input required type="number" min={0} max={100} step={1} value={value.progress} onChange={(event) => update({ progress: event.target.valueAsNumber })} className={field} /></label>
        <label className="text-sm font-medium">Status<select value={value.status} onChange={(event) => update({ status: event.target.value as BookInput['status'] })} className={field}><option value="current">Current</option><option value="done">Done</option></select></label>
      </div>
      {error && <p role="alert" className="mt-4 text-sm text-bad">{error}</p>}
      <div className="mt-6 flex justify-end gap-2"><Button variant="secondary" onClick={onCancel} disabled={saving}>Cancel</Button><Button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save book'}</Button></div>
    </form>
  </dialog>, document.body)
}

function BookCard({ book, categories, onEdit, onToggle, onDelete, busy }: { book: Book; categories: BookCategoryInfo[]; onEdit: () => void; onToggle: () => void; onDelete: () => void; busy: boolean }) {
  return <article className="rounded-2xl border border-line bg-surface p-5 shadow-sm">
    <div className="flex items-start gap-3"><span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent"><BookOpen aria-hidden className="size-5" /></span><div className="min-w-0 flex-1">
      <h3 className="serif-text break-words text-xl leading-tight">{book.title}</h3>
      <p className="mt-1 text-sm text-muted">{book.author || 'Author not specified'}</p>
    </div></div>
    <p className="mt-4 text-xs text-muted">{book.language} · {label(book.category, categories)}{book.isbn ? ` · ISBN ${book.isbn}` : ''}</p>
    <div className="mt-3 flex items-center gap-3"><div role="progressbar" aria-label={`${book.title} completion`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={book.progress} className="h-2 flex-1 overflow-hidden rounded-full bg-surface-2"><div className="h-full rounded-full bg-accent" style={{ width: `${book.progress}%` }} /></div><span className="text-sm font-semibold tabular-nums">{book.progress}%</span></div>
    <div className="mt-4 flex flex-wrap items-center gap-2"><Button size="sm" variant="secondary" icon={book.status === 'current' ? Check : BookOpen} disabled={busy} onClick={onToggle}>{book.status === 'current' ? 'Mark done' : 'Move to current'}</Button><Button size="sm" variant="ghost" icon={Pencil} disabled={busy} onClick={onEdit} aria-label={`Edit ${book.title}`}>Edit</Button><Button size="sm" variant="ghost" icon={Trash2} disabled={busy} onClick={onDelete} aria-label={`Delete ${book.title}`}>Delete</Button></div>
  </article>
}

export function BooksPage() {
  const { language } = useMeta()
  const [books, setBooks] = useState<Book[]>([])
  const [categories, setCategories] = useState<BookCategoryInfo[]>([])
  const [addingCategory, setAddingCategory] = useState(false)
  const [newCategory, setNewCategory] = useState('')
  const [categoryError, setCategoryError] = useState('')
  const [savingCategory, setSavingCategory] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [category, setCategory] = useState<BookCategory | 'all'>('all')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<BookSearchResult[] | null>(null)
  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [draft, setDraft] = useState<Draft | null>(null)
  const [remove, setRemove] = useState<Book | null>(null)
  const [busy, setBusy] = useState(false)
  const [recommendation, setRecommendation] = useState<BookRecommendation | null>(null)
  const [recommendLanguage, setRecommendLanguage] = useState(language.name)
  const [recommending, setRecommending] = useState(false)
  const [recommendError, setRecommendError] = useState('')
  const searchRef = useRef<HTMLElement>(null)
  const searchAbort = useRef<AbortController | null>(null)
  const recommendAbort = useRef<AbortController | null>(null)
  useEffect(() => { let active = true; Promise.all([api.books(), api.bookCategories()]).then(([savedBooks, savedCategories]) => { if (active) { setBooks(savedBooks); setCategories(savedCategories) } }).catch((reason: unknown) => { if (active) setError(messageOf(reason)) }).finally(() => { if (active) setLoading(false) }); return () => { active = false; searchAbort.current?.abort(); recommendAbort.current?.abort() } }, [])
  const blank = (): BookInput => ({ title: '', author: '', isbn: '', language: language.name, progress: 0, status: 'current', category: category === 'all' ? 'other' : category })
  const lookup = async (value: string) => {
    const clean = value.trim(); if (!clean) return
    searchAbort.current?.abort(); const controller = new AbortController(); searchAbort.current = controller
    setSearching(true); setSearchError(''); setResults(null); setQuery(clean)
    try { setResults(await api.searchBooks(clean, controller.signal)) } catch (reason) { if (!isAbort(reason)) setSearchError(messageOf(reason)) } finally { if (!controller.signal.aborted) setSearching(false) }
  }
  const suggest = async () => {
    recommendAbort.current?.abort(); const controller = new AbortController(); recommendAbort.current = controller
    setRecommending(true); setRecommendError(''); setRecommendation(null)
    try { setRecommendation(await api.recommendBook(category, recommendLanguage, controller.signal)) } catch (reason) { if (!isAbort(reason)) setRecommendError(messageOf(reason)) } finally { if (!controller.signal.aborted) setRecommending(false) }
  }
  const update = async (book: Book, status: Book['status']) => {
    setBusy(true); setError('')
    try { const updated = await api.updateBook(book.id, { ...book, status }); setBooks((current) => current.map((item) => item.id === book.id ? updated : item)) }
    catch (reason) { setError(messageOf(reason)) } finally { setBusy(false) }
  }
  const erase = async () => {
    if (!remove) return
    const id = remove.id; setBusy(true); setError('')
    try { await api.deleteBook(id); setBooks((current) => current.filter((book) => book.id !== id)); setRemove(null) }
    catch (reason) { setError(messageOf(reason)); setRemove(null) } finally { setBusy(false) }
  }
  const addCategory = async () => {
    if (!newCategory.trim() || savingCategory) return
    setSavingCategory(true); setCategoryError('')
    try {
      const created = await api.createBookCategory(newCategory)
      setCategories((current) => current.some((item) => item.id === created.id) ? current : [...current, created])
      setCategory(created.id); setNewCategory(''); setAddingCategory(false)
    } catch (reason) { setCategoryError(messageOf(reason)) } finally { setSavingCategory(false) }
  }
  const selected = books.filter((book) => matches(book, category, categories))
  return <div className="mx-auto max-w-4xl">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="flex items-center gap-2 text-sm font-medium text-accent"><LibraryBig aria-hidden className="size-4" />Your library</p><h1 className="serif-text mt-2 text-4xl tracking-tight sm:text-5xl">Books</h1><p className="mt-3 text-muted">Keep track of what you’re reading and what you’ve finished.</p></div><Button icon={Plus} onClick={() => setDraft({ value: blank() })}>Add manually</Button></div>
    <section ref={searchRef} aria-label="Find a book" className="mt-8 rounded-2xl border border-line bg-surface p-5 shadow-sm sm:p-6"><h2 className="font-semibold">Find a book</h2><form className="mt-3 flex flex-wrap gap-2" onSubmit={(event) => { event.preventDefault(); void lookup(query) }}><label className="sr-only" htmlFor="book-search">Title or ISBN</label><input id="book-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Title or ISBN" maxLength={200} className="min-w-0 flex-1 rounded-xl border border-line bg-bg px-3 py-2 text-ink outline-none focus:border-accent" /><Button type="submit" icon={Search} disabled={!query.trim() || searching}>{searching ? 'Searching…' : 'Search'}</Button></form><p className="mt-2 text-xs text-muted">Book lookup by Open Library; no AI key needed. You can add or edit details manually.</p>
      {searchError && <p role="alert" className="mt-3 text-sm text-bad">{searchError}</p>}
      {results && <div className="mt-4 space-y-2" aria-label="Search results">{results.length === 0 ? <p className="text-sm text-muted">No books found. Try another search or add it manually.</p> : results.map((result, index) => <div key={`${result.title}-${index}`} className="flex flex-wrap items-center gap-3 rounded-xl border border-line p-3"><div className="min-w-0 flex-1"><p className="font-medium">{result.title}</p><p className="text-sm text-muted">{[result.author, result.year, result.isbn ? `ISBN ${result.isbn}` : ''].filter(Boolean).join(' · ')}</p></div><Button size="sm" variant="secondary" onClick={() => setDraft({ value: { ...blank(), title: result.title, author: result.author, isbn: result.isbn } })}>Add</Button></div>)}</div>}
    </section>
    <section className="mt-8" aria-label="Book categories"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-lg font-semibold">Categories</h2><span className="text-sm text-muted">{books.length} {books.length === 1 ? 'book' : 'books'}</span></div><div className="mt-3 flex flex-wrap gap-2"><button type="button" aria-pressed={category === 'all'} onClick={() => setCategory('all')} className={cx('rounded-xl border px-3 py-2 text-sm', category === 'all' ? 'border-accent bg-accent-soft text-ink' : 'border-line bg-surface text-muted')}>All <span className="tabular-nums">{books.length}</span></button>{categories.filter((item) => item.group === 'main').map((item) => <button key={item.id} type="button" aria-pressed={category === item.id} onClick={() => setCategory(item.id)} className={cx('rounded-xl border px-3 py-2 text-sm', category === item.id ? 'border-accent bg-accent-soft text-ink' : 'border-line bg-surface text-muted')}>{item.name} <span className="tabular-nums">{books.filter((book) => matches(book, item.id, categories)).length}</span></button>)}</div>
      <p className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wide text-muted">Non-fiction subjects</p><div className="flex flex-wrap gap-2">{categories.filter((item) => item.group === 'nonfiction').map((item) => <button key={item.id} type="button" aria-pressed={category === item.id} onClick={() => setCategory(item.id)} className={cx('rounded-xl border px-3 py-2 text-sm', category === item.id ? 'border-accent bg-accent-soft text-ink' : 'border-line bg-surface text-muted')}>{item.name} <span className="tabular-nums">{books.filter((book) => matches(book, item.id, categories)).length}</span></button>)}</div>
      <div className="mt-3">{addingCategory ? <div className="flex flex-wrap items-center gap-2"><label className="sr-only" htmlFor="new-book-category">New subject name</label><input id="new-book-category" value={newCategory} onChange={(event) => setNewCategory(event.target.value)} maxLength={80} placeholder="Subject name" className="rounded-xl border border-line bg-surface px-3 py-2 text-sm text-ink" /><Button size="sm" onClick={() => void addCategory()} disabled={!newCategory.trim() || savingCategory}>Add subject</Button><Button size="sm" variant="ghost" onClick={() => { setAddingCategory(false); setCategoryError('') }}>Cancel</Button></div> : <Button size="sm" variant="ghost" icon={Plus} onClick={() => setAddingCategory(true)}>New subject</Button>}{categoryError && <p role="alert" className="mt-2 text-sm text-bad">{categoryError}</p>}</div>
    </section>
    <section aria-label="Book recommendation" className="mt-7 rounded-2xl border border-accent/25 bg-accent-soft p-5"><div className="flex flex-col gap-4 sm:flex-row sm:items-end"><div className="min-w-0 flex-1"><h2 className="flex items-center gap-2 font-semibold"><Sparkles aria-hidden className="size-4 text-accent" />What to read next</h2><p className="mt-1 text-sm text-muted">Ask AI for a suggestion based on your saved books {category === 'all' ? 'across all categories' : `in ${label(category, categories)}`}.</p></div><div className="flex flex-wrap items-center gap-3"><label className="text-xs text-muted">Reading language<select aria-label="Recommendation language" value={recommendLanguage} onChange={(event) => setRecommendLanguage(event.target.value)} className="ml-2 rounded-lg border border-line bg-surface px-2 py-1.5 text-sm text-ink"><option>Any</option><option>English</option><option>German</option><option>French</option></select></label><Button size="sm" icon={Sparkles} onClick={() => void suggest()} disabled={recommending}>{recommending ? 'Thinking…' : 'Suggest a book'}</Button></div></div>
      <p className="mt-2 text-xs text-muted">Your saved book details are sent to your selected AI model. Check suggestions before adding them.</p>
      {recommendError && <p role="alert" className="mt-3 text-sm text-bad">{recommendError}</p>}
      {recommendation && <div className="mt-4 rounded-xl border border-line bg-surface p-4"><p className="font-semibold">{recommendation.title}</p><p className="text-sm text-muted">{recommendation.author} · {recommendation.language}</p><p className="mt-2 text-sm">{recommendation.reason}</p><div className="mt-3 flex flex-wrap gap-2"><Button size="sm" variant="secondary" onClick={() => { void lookup(recommendation.title); searchRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }}>Look up title</Button><Button size="sm" variant="secondary" onClick={() => setDraft({ value: { ...blank(), title: recommendation.title, author: recommendation.author, language: recommendation.language } })}>Add suggestion</Button></div></div>}
    </section>
    {error && <p role="alert" className="mt-5 text-sm text-bad">{error}</p>}
    {loading ? <p className="mt-8 text-muted">Loading your books…</p> : <div className="mt-8 grid gap-8 md:grid-cols-2">{(['current', 'done'] as const).map((status) => { const items = selected.filter((book) => book.status === status); return <section key={status} aria-label={status === 'current' ? 'Current books' : 'Done books'}><div className="flex items-baseline justify-between"><h2 className="serif-text text-2xl">{status === 'current' ? 'Current' : 'Done'}</h2><span className="text-sm text-muted">{items.length}</span></div><div className="mt-3 space-y-3">{items.length ? items.map((book) => <BookCard key={book.id} book={book} categories={categories} busy={busy} onEdit={() => setDraft({ id: book.id, value: { title: book.title, author: book.author, isbn: book.isbn, language: book.language, progress: book.progress, status: book.status, category: book.category } })} onToggle={() => void update(book, book.status === 'current' ? 'done' : 'current')} onDelete={() => setRemove(book)} />) : <p className="rounded-2xl border border-dashed border-line p-5 text-sm text-muted">{status === 'current' ? 'No current books in this category.' : 'No completed books in this category.'}</p>}</div></section> })}</div>}
    {draft && <BookEditor draft={draft} categories={categories} onCancel={() => setDraft(null)} onSaved={(book) => { setBooks((current) => [book, ...current.filter((item) => item.id !== book.id)]); setDraft(null) }} />}
    <ConfirmDialog open={!!remove} title="Remove book?" body={`Remove “${remove?.title ?? ''}” from your library?`} confirmLabel="Remove" cancelLabel="Cancel" onConfirm={() => void erase()} onCancel={() => setRemove(null)} />
  </div>
}
