import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { Link, useLocation } from 'react-router'
import { House } from 'lucide-react'
import { Logo } from './Logo'
import { ExitButton } from './ExitButton'
import { DeviceAccessButton } from './DeviceAccessButton'
import { SettingsButton, useApiKeyStatus } from './ApiKeyButton'
import { ReadSourcesButton } from './ReadSourcesButton'

export function AppMenu() {
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const menu = useRef<HTMLDivElement>(null)
  const lastFirst = useRef(false)
  const location = useLocation()
  const [apiKey, setApiKey] = useApiKeyStatus('openai')
  const [elevenKey, setElevenKey] = useApiKeyStatus('elevenlabs')
  const missingKey = apiKey !== null && !apiKey.configured

  const close = () => {
    setOpen(false)
    trigger.current?.focus()
  }

  useEffect(() => setOpen(false), [location.pathname])
  useEffect(() => {
    if (!open) return
    const items = menu.current?.querySelectorAll<HTMLElement>('[role="menuitem"]:not(:disabled)')
    items?.[lastFirst.current ? items.length - 1 : 0]?.focus()
    const outside = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('pointerdown', outside)
    return () => document.removeEventListener('pointerdown', outside)
  }, [open])

  const onKeyDown = (event: KeyboardEvent) => {
    if (!menu.current?.contains(event.target as Node)) return
    // Menu keys must not trigger exercise shortcuts behind the dropdown.
    event.stopPropagation()
    if (event.key === 'Escape') {
      event.preventDefault()
      close()
    } else if (event.key === 'Tab') {
      setOpen(false)
    } else if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
      event.preventDefault()
      const items = Array.from(menu.current?.querySelectorAll<HTMLElement>('[role="menuitem"]:not(:disabled)') ?? [])
      const current = items.indexOf(document.activeElement as HTMLElement)
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1
        : (current + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length
      items[next]?.focus()
    }
  }

  return (
    <div ref={root} className="relative shrink-0">
      <button ref={trigger} type="button" aria-label={missingKey ? 'Languages menu (no API key set)' : 'Languages menu'}
        title={missingKey ? 'Languages menu · No API key set' : 'Languages menu'}
        aria-haspopup="menu" aria-expanded={open} aria-controls="languages-menu"
        onClick={() => { lastFirst.current = false; setOpen((value) => !value) }}
        onKeyDown={(event) => {
          event.stopPropagation()
          if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
            event.preventDefault()
            lastFirst.current = event.key === 'ArrowUp'
            setOpen(true)
          }
        }}
        className="flex cursor-pointer items-center gap-2.5 rounded-lg font-semibold tracking-tight focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent">
        <span className="relative">
          <Logo />
          {missingKey && <span aria-hidden className="absolute -right-1 -top-1 size-2.5 rounded-full bg-bad ring-2 ring-bg" />}
        </span>
      </button>
      <div ref={menu} id="languages-menu" role="menu" aria-label="Languages" hidden={!open}
        onKeyDown={onKeyDown}
        className="absolute left-0 top-full z-30 mt-3 w-56 rounded-2xl border border-line bg-surface p-1.5 shadow-xl shadow-black/10">
        <Link to="/" role="menuitem" tabIndex={-1} onClick={close}
          className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-ink hover:bg-surface-2 focus:bg-surface-2 focus:outline-none">
          <House aria-hidden className="size-4 text-accent" />Home
        </Link>
        <SettingsButton openai={apiKey} elevenlabs={elevenKey} onOpenaiSaved={setApiKey} onElevenlabsSaved={setElevenKey} onSelect={() => setOpen(false)} />
        <DeviceAccessButton onSelect={() => setOpen(false)} />
        <ReadSourcesButton onSelect={() => setOpen(false)} />
        <ExitButton onSelect={close} />
      </div>
    </div>
  )
}
