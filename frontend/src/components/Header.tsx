import { useLayoutEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { House, Newspaper, Dices, BookPlus, MessageCircleQuestion } from 'lucide-react'
import { useMeta } from '../context/MetaContext'
import type { LanguageCode } from '../types'
import { useLucky } from '../hooks/useLucky'
import { isEditable, useKeydown } from '../hooks/useKeydown'
import { cx } from '../lib/cx'
import { AppMenu } from './AppMenu'
import { ExercisesMenu } from './ExercisesMenu'
import { SourcesDropdown } from './SourcesDropdown'
import { returnExercisePath } from '../lib/exerciseReturn'

export function Header() {
  const { meta, language, setLanguage } = useMeta()
  const navigate = useNavigate()
  const location = useLocation()
  const returnToExercise = returnExercisePath(location.pathname, location.state, location.search)
  const { available, feelLucky } = useLucky()
  const headerRef = useRef<HTMLElement>(null)
  const [readMenu, setReadMenu] = useState(false)
  useLayoutEffect(() => {
    const header = headerRef.current
    if (!header) return
    const updateHeight = () => document.documentElement.style.setProperty('--languages-header-height', `${header.offsetHeight}px`)
    updateHeight()
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(updateHeight)
    observer?.observe(header)
    window.addEventListener('resize', updateHeight)
    return () => { observer?.disconnect(); window.removeEventListener('resize', updateHeight) }
  }, [])
  const rememberArticlePosition = () => {
    if (location.pathname !== '/read') return
    try { sessionStorage.setItem('languages.read.returnScrollY', String(window.scrollY)) } catch { /* Scroll restoration is optional. */ }
  }
  useKeydown((event) => {
    if (event.defaultPrevented || event.repeat || !event.ctrlKey || event.metaKey || event.altKey || event.shiftKey ||
        event.getModifierState('AltGraph') || document.querySelector('dialog[open]') ||
        [...document.querySelectorAll<HTMLElement>('[role="menu"]')].some((menu) => menu.getClientRects().length > 0)) return
    const key = event.key.toLowerCase()
    const path = key === 'a' ? '/add' : key === 's' ? '/ask' : null
    if (!path) return
    const editing = isEditable(event.target) || (event.target instanceof Element && !!event.target.closest('[role="textbox"]'))
    if (editing && (key === 'a' || ['/add', '/ask', '/read'].includes(location.pathname))) return
    event.preventDefault()
    if (location.pathname === path) return
    rememberArticlePosition()
    navigate(path, { state: returnToExercise ? { returnToExercise } : null })
  })
  const switchLanguage = (code: LanguageCode) => {
    if (code === language.code) return
    setLanguage(code)
    navigate('/')
  }

  return (
    <header ref={headerRef} className="sticky top-0 z-20 border-b border-line/70 bg-bg/80 backdrop-blur-md">
      <div className="mx-auto flex min-h-16 max-w-7xl flex-wrap items-center gap-x-1 gap-y-2 px-4 py-3 xl:flex-nowrap sm:gap-x-2 sm:px-6">
        <AppMenu />
        <ExercisesMenu />
        <nav aria-label="Main navigation" className="flex min-w-max flex-1 items-center justify-center gap-x-1 sm:gap-x-2">
          <Link to="/" aria-label="Home" title="Home" className="flex h-9 shrink-0 items-center gap-2 rounded-xl px-1 sm:px-2 text-sm font-medium text-muted transition hover:bg-surface-2 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
            <House aria-hidden className="size-[18px]" /><span className="hidden lg:inline">Home</span>
          </Link>

          <div className="relative shrink-0">
            <button type="button" aria-label="Read" title="Read" aria-haspopup="menu" aria-expanded={readMenu} onClick={() => setReadMenu((value) => !value)} onKeyDown={(event) => { if (event.key === 'Escape') setReadMenu(false) }} className="flex h-9 items-center gap-2 rounded-xl px-1 sm:px-2 text-sm font-medium text-muted transition hover:bg-surface-2 hover:text-ink">
              <Newspaper aria-hidden className="size-[18px]" /><span className="hidden lg:inline">Read</span>
            </button>
            {readMenu && <div role="menu" aria-label="Read options" className="absolute left-0 top-full z-50 mt-2 w-64 rounded-xl border border-line bg-surface p-1.5 shadow-xl">
              <Link role="menuitem" to="/read?mode=find" onClick={() => setReadMenu(false)} className="block rounded-lg px-3 py-2 text-sm hover:bg-surface-2">Find an article and read</Link>
              <Link role="menuitem" to="/read?mode=url" onClick={() => setReadMenu(false)} className="block rounded-lg px-3 py-2 text-sm hover:bg-surface-2">Summarize a webpage and read</Link>
              <Link role="menuitem" to="/read?mode=text" onClick={() => setReadMenu(false)} className="block rounded-lg px-3 py-2 text-sm hover:bg-surface-2">Read pasted article text</Link>
            </div>}
          </div>
          <button type="button" onClick={feelLucky} disabled={!available} aria-label="I feel lucky" title="12 random C1 questions"
            className="flex h-9 shrink-0 items-center gap-2 rounded-xl border border-accent/30 bg-accent-soft px-1 sm:px-2 text-sm font-semibold text-accent transition hover:border-accent/60 hover:brightness-95 disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
            <Dices aria-hidden className="size-[18px]" /><span className="hidden lg:inline">I feel lucky</span>
          </button>

          <Link to="/add" onClick={rememberArticlePosition} state={returnToExercise ? { returnToExercise } : null} aria-label="Add" title="Add" className="flex h-9 shrink-0 items-center gap-2 rounded-xl px-1 sm:px-2 text-sm font-medium text-muted transition hover:bg-surface-2 hover:text-ink">
            <BookPlus aria-hidden className="size-[18px]" /><span className="hidden lg:inline">Add</span>
          </Link>
          <Link to="/ask" onClick={rememberArticlePosition} state={returnToExercise ? { returnToExercise } : null} aria-label="Ask" title="Ask" className="flex h-9 shrink-0 items-center gap-2 rounded-xl px-1 sm:px-2 text-sm font-medium text-muted transition hover:bg-surface-2 hover:text-ink">
            <MessageCircleQuestion aria-hidden className="size-[18px]" /><span className="hidden lg:inline">Ask</span>
          </Link>

        </nav>
        <div className="ml-auto flex max-w-full flex-wrap items-center justify-end gap-2">
          <div role="group" aria-label="Language" className="flex rounded-xl border border-line bg-surface p-0.5">
            {meta.languages.map((option) => (
              <button
                key={option.code}
                type="button"
                aria-pressed={option.code === language.code}
                title={option.name}
                onClick={() => switchLanguage(option.code)}
                className={cx(
                  'h-7 cursor-pointer rounded-[9px] px-2 text-xs font-semibold tracking-wide transition',
                  option.code === language.code ? 'bg-accent text-accent-ink shadow-sm' : 'text-muted hover:text-ink',
                )}
              >
                {option.code}
              </button>
            ))}
          </div>
          <SourcesDropdown language={language.code} languageName={language.name} />

        </div>
      </div>
    </header>
  )
}
