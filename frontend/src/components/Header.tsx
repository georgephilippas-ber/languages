import { useLayoutEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { ArrowLeft, House, Newspaper, Dices, BookOpenText, BookPlus, MessageCircleQuestion } from 'lucide-react'
import { useMeta } from '../context/MetaContext'
import type { LanguageCode } from '../types'
import { useLucky } from '../hooks/useLucky'
import { LuckyChoiceDialog } from './LuckyChoiceDialog'
import { useKeydown } from '../hooks/useKeydown'
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
  const previousLanguage = (location.state as { returnLanguage?: unknown } | null)?.returnLanguage
  const returnLanguage = (location.pathname === '/add' || location.pathname === '/ask') &&
    (previousLanguage === 'EN' || previousLanguage === 'DE' || previousLanguage === 'FR') ? previousLanguage : language.code
  const returnState = returnToExercise ? { returnToExercise, returnLanguage } : null
  const { available, canStartNew, phrasalAvailable, phrasalLucky, feelLucky, choice, resume, startNew, cancel } = useLucky()
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
    const languageShortcut: Partial<Record<string, LanguageCode>> = { e: 'EN', d: 'DE', f: 'FR' }
    const requestedLanguage = languageShortcut[key]
    if (requestedLanguage) {
      if (event.target instanceof HTMLSelectElement) return
      event.preventDefault()
      switchLanguage(requestedLanguage, true)
      return
    }
    const path = key === 'a' ? '/add' : key === 's' ? '/ask' : null
    if (!path) return
    if (event.target instanceof HTMLSelectElement) return
    if (location.pathname === path) {
      if (key === 's') event.preventDefault()
      return
    }
    event.preventDefault()
    rememberArticlePosition()
    navigate(path, { state: returnState })
  })
  const switchLanguage = (code: LanguageCode, preserveSessions = false) => {
    if (code === language.code) return
    if (location.pathname === '/add') {
      setLanguage(code, { preserveSessions: true })
      return
    }
    setLanguage(code, { preserveSessions })
    navigate('/')
  }

  if (location.pathname === '/books') {
    return <header ref={headerRef} className="sticky top-0 z-20 border-b border-line/70 bg-bg/80 backdrop-blur-md">
      <div className="mx-auto flex min-h-16 max-w-7xl items-center px-4 py-3 sm:px-6">
        <Link to="/" className="inline-flex h-9 items-center gap-2 rounded-xl px-3 text-sm font-medium text-muted transition hover:bg-surface-2 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
          <ArrowLeft aria-hidden className="size-[18px]" />Back to Languages
        </Link>
      </div>
    </header>
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

          {language.code === 'EN' && <button type="button" onClick={phrasalLucky} disabled={!phrasalAvailable} aria-label="Phrasal verbs" title="12 random C1 phrasal verb questions"
            className="flex h-9 shrink-0 items-center gap-2 rounded-xl border border-violet-400/40 bg-violet-500/10 px-1 sm:px-2 text-sm font-semibold text-violet-700 transition hover:bg-violet-500/20 disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent dark:text-violet-300">
            <BookOpenText aria-hidden className="size-[18px]" /><span className="hidden xl:inline">Phrasal verbs</span>
          </button>}

          <Link to="/add" onClick={rememberArticlePosition} state={returnState} aria-label="Add" title="Add" className="flex h-9 shrink-0 items-center gap-2 rounded-xl px-1 sm:px-2 text-sm font-medium text-muted transition hover:bg-surface-2 hover:text-ink">
            <BookPlus aria-hidden className="size-[18px]" /><span className="hidden lg:inline">Add</span>
          </Link>
          <Link to="/ask" onClick={rememberArticlePosition} state={returnState} aria-label="Ask" title="Ask" className="flex h-9 shrink-0 items-center gap-2 rounded-xl px-1 sm:px-2 text-sm font-medium text-muted transition hover:bg-surface-2 hover:text-ink">
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
                title={`${option.name} (Ctrl+${option.code === 'EN' ? 'E' : option.code === 'DE' ? 'D' : 'F'})`}
                aria-keyshortcuts={`Control+${option.code === 'EN' ? 'E' : option.code === 'DE' ? 'D' : 'F'}`}
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
      <LuckyChoiceDialog choice={choice} canStartNew={canStartNew} onResume={resume} onStartNew={startNew} onCancel={cancel} />
    </header>
  )
}
