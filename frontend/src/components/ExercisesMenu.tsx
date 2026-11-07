import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { Link, useLocation } from 'react-router'
import { ChevronDown, ListChecks, Keyboard, LibraryBig } from 'lucide-react'
import { useMeta } from '../context/MetaContext'
import { exercisesFor } from '../exercises'

export function ExercisesMenu() {
  const { language } = useMeta()
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const menu = useRef<HTMLDivElement>(null)
  const lastFirst = useRef(false)
  const exercises = exercisesFor(language.code)
  const vocabulary = exercises.filter((exercise) => ['quiz', 'typed', 'writing'].includes(exercise.kind))
  const grammar = exercises.filter((exercise) => ['prepositions', 'articles'].includes(exercise.kind))
  useEffect(() => setOpen(false), [location.pathname])
  useEffect(() => {
    if (!open) return
    const items = menu.current?.querySelectorAll<HTMLElement>('[role="menuitem"]')
    items?.[lastFirst.current ? items.length - 1 : 0]?.focus()
    const outside = (event: PointerEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false) }
    document.addEventListener('pointerdown', outside)
    return () => document.removeEventListener('pointerdown', outside)
  }, [open])
  const close = () => { setOpen(false); trigger.current?.focus() }
  const onKeyDown = (event: KeyboardEvent) => {
    event.stopPropagation()
    if (event.key === 'Escape') { event.preventDefault(); close() }
    else if (event.key === 'Tab') setOpen(false)
    else if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
      event.preventDefault()
      const items = Array.from(menu.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? [])
      if (!items.length) return
      const current = items.indexOf(document.activeElement as HTMLElement)
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1 : (current + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length
      items[next]?.focus()
    }
  }
  const itemClass = 'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-ink hover:bg-surface-2 focus:bg-surface-2 focus:outline-none'
  return <div ref={root} className="relative shrink-0">
    <button ref={trigger} type="button" aria-label="Exercises menu" title="Exercises" aria-haspopup="menu" aria-expanded={open} aria-controls="exercises-menu"
      onClick={() => { lastFirst.current = false; setOpen((value) => !value) }}
      onKeyDown={(event) => { event.stopPropagation(); if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); lastFirst.current = event.key === 'ArrowUp'; setOpen(true) } }}
      className="flex h-9 items-center gap-1 rounded-lg px-1 text-sm font-semibold tracking-tight text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
      Languages<ChevronDown aria-hidden className="size-3.5 text-muted" />
    </button>
    <div ref={menu} id="exercises-menu" role="menu" aria-label="Exercises" hidden={!open} onKeyDown={onKeyDown}
      className="absolute left-0 top-full z-30 mt-3 max-h-[min(70vh,36rem)] w-64 overflow-y-auto rounded-2xl border border-line bg-surface p-1.5 shadow-xl shadow-black/10">
      <p className="px-3 pb-1 pt-2 text-xs font-semibold uppercase tracking-wide text-muted">Vocabulary</p>
      {vocabulary.map((exercise) => <Link key={exercise.kind} to={exercise.path} role="menuitem" tabIndex={-1} onClick={close} className={itemClass}>
        <exercise.icon aria-hidden className="size-4 text-accent" /><span>{exercise.verb} <span className="text-muted">· {exercise.name}</span></span>
      </Link>)}
      {grammar.length > 0 && <><div role="separator" className="my-1 border-t border-line" /><p className="px-3 pb-1 pt-2 text-xs font-semibold uppercase tracking-wide text-muted">Grammar</p>
        {grammar.map((exercise) => <Link key={exercise.kind} to={exercise.path} role="menuitem" tabIndex={-1} onClick={close} className={itemClass}>
          <exercise.icon aria-hidden className="size-4 text-accent" /><span>{exercise.verb} <span className="text-muted">· {exercise.name}</span></span>
        </Link>)}</>}
      <div role="separator" className="my-1 border-t border-line" /><p className="px-3 pb-1 pt-2 text-xs font-semibold uppercase tracking-wide text-muted">Translate</p>
      <Link to="/translate/recognize" role="menuitem" tabIndex={-1} onClick={close} className={itemClass}><ListChecks aria-hidden className="size-4 text-accent" /><span>Recognize translation</span></Link>
      <Link to="/translate/produce" role="menuitem" tabIndex={-1} onClick={close} className={itemClass}><Keyboard aria-hidden className="size-4 text-accent" /><span>Produce translation</span></Link>
      <div role="separator" className="my-1 border-t border-line" />
      <Link to="/books" role="menuitem" tabIndex={-1} onClick={close} className={itemClass}><LibraryBig aria-hidden className="size-4 text-accent" /><span>BOOKS</span></Link>
    </div>
  </div>
}
