import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { ChevronDown } from 'lucide-react'
import { api, messageOf } from '../api'
import type { LanguageCode } from '../types'

type Sources = Record<LanguageCode, { name: string; domain: string }[]>

export function SourcesDropdown({ language, languageName }: { language: LanguageCode; languageName: string }) {
  const [open, setOpen] = useState(false)
  const [sources, setSources] = useState<Sources | null>(null)
  const [error, setError] = useState('')
  const root = useRef<HTMLDivElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const menu = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    let alive = true
    setError('')
    api.readSources().then((value) => { if (alive) setSources(value) }).catch((reason: unknown) => { if (alive) setError(messageOf(reason)) })
    const outside = (event: PointerEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false) }
    document.addEventListener('pointerdown', outside)
    return () => { alive = false; document.removeEventListener('pointerdown', outside) }
  }, [open])
  const keydown = (event: KeyboardEvent) => {
    if (!open) return
    if (event.key === 'Escape') {
      event.preventDefault(); event.stopPropagation(); setOpen(false); trigger.current?.focus()
    } else if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
      event.preventDefault(); event.stopPropagation()
      const items = Array.from(menu.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? [])
      if (!items.length) return
      const current = items.indexOf(document.activeElement as HTMLElement)
      const next = event.key === 'Home' || (current < 0 && event.key === 'ArrowDown') ? 0 : event.key === 'End' || current < 0 ? items.length - 1 : (current + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length
      items[next]?.focus()
    } else if (event.key === 'Tab' && !event.shiftKey && document.activeElement === menu.current?.querySelector('[role="menuitem"]:last-child')) {
      setOpen(false)
    }
  }
  return <div ref={root} className="relative shrink-0" onKeyDown={keydown}>
    <button ref={trigger} type="button" aria-label="Sources" title={`${languageName} sources`} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((value) => !value)}
      className="flex h-9 items-center gap-1 rounded-xl px-2 text-sm font-medium text-muted transition hover:bg-surface-2 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
      Sources<ChevronDown aria-hidden className="size-3.5" />
    </button>
    {open && <div ref={menu} role="menu" aria-label={`${languageName} sources`} className="absolute right-0 top-full z-50 mt-2 max-h-[min(60vh,28rem)] w-60 overflow-y-auto rounded-xl border border-line bg-surface p-1.5 shadow-xl">
      <p className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted">{languageName} sources</p>
      {error && <p role="alert" className="px-3 py-2 text-sm text-bad">{error}</p>}
      {!sources && !error && <p className="px-3 py-2 text-sm text-muted">Loading…</p>}
      {sources?.[language].map((source) => <a key={source.domain} role="menuitem" href={`https://${source.domain}`} target="_blank" rel="noopener noreferrer" onClick={() => setOpen(false)}
        className="block rounded-lg px-3 py-2 text-sm text-ink hover:bg-surface-2 focus:bg-surface-2 focus:outline-none">{source.name}</a>)}
    </div>}
  </div>
}
