import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router'
import { AnimatePresence, motion } from 'motion/react'
import { BookPlus, ChevronDown, GalleryVerticalEnd, MessageCircleQuestion, Monitor, Moon, Newspaper, Sun } from 'lucide-react'
import { useMeta } from '../context/MetaContext'
import { exercisesFor } from '../exercises'
import type { LanguageCode } from '../types'
import { useTheme, type Theme } from '../hooks/useTheme'
import { useKeydown } from '../hooks/useKeydown'
import { cx } from '../lib/cx'
import { Logo } from './Logo'
import { ModelPicker } from './ModelPicker'

const READ = { path: '/read', verb: 'Read', name: 'Current articles', icon: Newspaper }

const TOOLS = [
  { path: '/add', verb: 'Add', name: 'New entries', icon: BookPlus },
  { path: '/review', verb: 'Review', name: 'Flashcards', icon: GalleryVerticalEnd },
]

const ASK = { path: '/ask', verb: 'Ask', name: 'Language questions', icon: MessageCircleQuestion }

const GROUP_PATHS = ['/prepositions', '/articles']
const GROUP_LABEL = 'Refine'

const NAV_ACTIVE = 'bg-surface text-ink shadow-sm ring-1 ring-line'
const NAV_IDLE = 'text-muted hover:bg-surface-2 hover:text-ink'

interface NavItem {
  path: string
  verb: string
  name: string
  icon: typeof Sun
}

function NavItemLink({ item }: { item: NavItem }) {
  const Icon = item.icon
  return (
    <NavLink
      to={item.path}
      aria-label={`${item.verb} · ${item.name}`}
      title={`${item.verb} · ${item.name}`}
      className={({ isActive }) =>
        cx('flex h-9 shrink-0 items-center gap-2 rounded-lg px-2.5 text-sm font-medium transition', isActive ? NAV_ACTIVE : NAV_IDLE)
      }
    >
      <Icon aria-hidden className="size-4" />
      <span className="hidden md:inline">{item.verb}</span>
    </NavLink>
  )
}

function NavDropdown({ items }: { items: NavItem[] }) {
  const [open, setOpen] = useState(false)
  const location = useLocation()
  const ref = useRef<HTMLDivElement>(null)
  const active = items.find((item) => location.pathname === item.path)
  const ActiveIcon = active?.icon

  useEffect(() => {
    if (!open) return
    const close = (event: PointerEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false)
    }
    window.addEventListener('pointerdown', close)
    return () => window.removeEventListener('pointerdown', close)
  }, [open])

  useKeydown((event) => {
    if (event.key === 'Escape') setOpen(false)
  }, open)

  return (
    <div ref={ref} className="relative shrink-0">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className={cx(
          'flex h-9 cursor-pointer items-center gap-1.5 rounded-lg px-2.5 text-sm font-medium transition',
          active || open ? NAV_ACTIVE : NAV_IDLE,
        )}
      >
        {ActiveIcon ? <ActiveIcon aria-hidden className="size-4" /> : null}
        <span className="hidden md:inline">{active ? active.verb : GROUP_LABEL}</span>
        <ChevronDown aria-hidden className={cx('size-3.5 transition-transform duration-200', open && 'rotate-180')} />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            role="menu"
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.16, ease: 'easeOut' }}
            className="absolute left-0 top-full z-30 mt-2 w-60 origin-top-left rounded-2xl border border-line bg-surface p-1.5 shadow-xl shadow-black/10"
          >
            {items.map((item) => {
              const Icon = item.icon
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  role="menuitem"
                  aria-label={`${item.verb} · ${item.name}`}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    cx(
                      'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition',
                      isActive ? 'bg-accent-soft text-ink' : 'text-muted hover:bg-surface-2 hover:text-ink',
                    )
                  }
                >
                  <Icon aria-hidden className="size-4 shrink-0 text-accent" />
                  <span className="min-w-0">
                    <span className="block font-medium text-ink">{item.verb}</span>
                    <span className="block truncate text-xs text-muted">{item.name}</span>
                  </span>
                </NavLink>
              )
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

const THEME_ICONS: Record<Theme, typeof Sun> = { system: Monitor, light: Sun, dark: Moon }

export function Header() {
  const { meta, language, setLanguage } = useMeta()
  const { theme, cycleTheme } = useTheme()
  const navigate = useNavigate()
  const ThemeIcon = THEME_ICONS[theme]
  const exercises = exercisesFor(language.code)
  const grouped = exercises.filter((exercise) => GROUP_PATHS.includes(exercise.path))
  const plain = exercises.filter((exercise) => !GROUP_PATHS.includes(exercise.path))
  const switchLanguage = (code: LanguageCode) => {
    if (code === language.code) return
    setLanguage(code)
    navigate('/')
  }

  return (
    <header className="sticky top-0 z-20 border-b border-line/70 bg-bg/80 backdrop-blur-md">
      <div className="mx-auto flex min-h-16 max-w-7xl flex-wrap items-center gap-x-2 gap-y-2 px-4 py-3 sm:gap-x-3 sm:px-6 xl:flex-nowrap">
        <Link to="/" className="flex shrink-0 items-center gap-2.5 rounded-lg font-semibold tracking-tight" aria-label="Languages, home">
          <Logo />
          <span className="hidden lg:inline">Languages</span>
        </Link>

        <nav aria-label="Exercises" className="order-last flex w-full min-w-0 flex-wrap items-center justify-center gap-0.5 xl:order-none xl:ml-3 xl:w-auto xl:flex-1 xl:justify-start">
          <NavItemLink item={READ} />
          <span aria-hidden className="mx-1 hidden h-5 w-px shrink-0 bg-line md:block" />
          {plain.map((exercise) => (
            <NavItemLink key={exercise.path} item={exercise} />
          ))}
          {grouped.length > 1 ? <NavDropdown items={grouped} /> : grouped.map((exercise) => <NavItemLink key={exercise.path} item={exercise} />)}
          <span aria-hidden className="mx-1 hidden h-5 w-px shrink-0 bg-line md:block" />
          {TOOLS.map((tool) => (
            <NavItemLink key={tool.path} item={tool} />
          ))}
          <span aria-hidden className="mx-1 hidden h-5 w-px shrink-0 bg-line md:block" />
          <NavItemLink item={ASK} />
        </nav>

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
