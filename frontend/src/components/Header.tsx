import { useLayoutEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router'
import { House, Newspaper, Dices, Monitor, Moon, Sun } from 'lucide-react'
import { useMeta } from '../context/MetaContext'
import type { LanguageCode } from '../types'
import { useTheme, type Theme } from '../hooks/useTheme'
import { useLucky } from '../hooks/useLucky'
import { cx } from '../lib/cx'
import { ModelPicker } from './ModelPicker'
import { AppMenu } from './AppMenu'

const THEME_ICONS: Record<Theme, typeof Sun> = { system: Monitor, light: Sun, dark: Moon }

export function Header() {
  const { meta, language, setLanguage } = useMeta()
  const { theme, cycleTheme } = useTheme()
  const navigate = useNavigate()
  const ThemeIcon = THEME_ICONS[theme]
  const { available, feelLucky } = useLucky()
  const headerRef = useRef<HTMLElement>(null)
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
  const switchLanguage = (code: LanguageCode) => {
    if (code === language.code) return
    setLanguage(code)
    navigate('/')
  }

  return (
    <header ref={headerRef} className="sticky top-0 z-20 border-b border-line/70 bg-bg/80 backdrop-blur-md">
      <div className="mx-auto flex min-h-16 max-w-7xl flex-wrap items-center gap-x-1 gap-y-2 px-4 py-3 sm:flex-nowrap sm:gap-x-2 sm:px-6">
        <AppMenu />
        <Link to="/" aria-label="Home" title="Home" className="flex h-9 shrink-0 items-center gap-2 rounded-xl px-2 text-sm font-medium text-muted transition hover:bg-surface-2 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
          <House aria-hidden className="size-[18px]" /><span className="hidden sm:inline">Home</span>
        </Link>

        <Link to="/read" aria-label="Read" title="Read" className="flex h-9 shrink-0 items-center gap-2 rounded-xl px-2 text-sm font-medium text-muted transition hover:bg-surface-2 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
          <Newspaper aria-hidden className="size-[18px]" /><span className="hidden sm:inline">Read</span>
        </Link>
        <button type="button" onClick={feelLucky} disabled={!available} aria-label="I feel lucky" title="12 random C1 questions"
          className="flex h-9 shrink-0 items-center gap-2 rounded-xl px-2 text-sm font-medium text-muted transition hover:bg-surface-2 hover:text-ink disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
          <Dices aria-hidden className="size-[18px]" /><span className="hidden sm:inline">I feel lucky</span>
        </button>

        <div className="ml-auto flex shrink-0 items-center gap-2">
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
          <div className="flex items-center">
            <ModelPicker />
            <button
              type="button"
              onClick={cycleTheme}
              aria-label={`Theme: ${theme}. Change theme`}
              title={`Theme: ${theme}`}
              className="flex size-9 cursor-pointer items-center justify-center rounded-xl text-muted transition hover:bg-surface-2 hover:text-ink"
            >
              <ThemeIcon aria-hidden className="size-[18px]" />
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
