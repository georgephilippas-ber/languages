import { Link, NavLink } from 'react-router'
import { BookPlus, GalleryVerticalEnd, MessageCircleQuestion, Monitor, Moon, Newspaper, Sun } from 'lucide-react'
import { useMeta } from '../context/MetaContext'
import { exercisesFor } from '../exercises'
import { useTheme, type Theme } from '../hooks/useTheme'
import { cx } from '../lib/cx'
import { Logo } from './Logo'
import { ModelPicker } from './ModelPicker'

const READ = { path: '/read', verb: 'Read', name: 'Current articles', icon: Newspaper }

const TOOLS = [
  { path: '/add', verb: 'Add', name: 'New entries', icon: BookPlus, tone: 'warn' as const },
  { path: '/review', verb: 'Review', name: 'Flashcards', icon: GalleryVerticalEnd, tone: 'good' as const },
]

const ASK = { path: '/ask', verb: 'Ask', name: 'Language questions', icon: MessageCircleQuestion }

const NAV_TONES = {
  accent: {
    active: 'bg-surface text-ink shadow-sm ring-1 ring-line',
    idle: 'text-muted hover:bg-surface-2 hover:text-ink',
  },
  good: {
    active: 'bg-good-soft text-good shadow-sm ring-1 ring-good/40',
    idle: 'text-good/80 hover:bg-good-soft hover:text-good',
  },
  warn: {
    active: 'bg-warn-soft text-warn shadow-sm ring-1 ring-warn/40',
    idle: 'text-warn/80 hover:bg-warn-soft hover:text-warn',
  },
  info: {
    active: 'bg-info-soft text-info shadow-sm ring-1 ring-info/40',
    idle: 'text-info/80 hover:bg-info-soft hover:text-info',
  },
}

interface NavItem {
  path: string
  verb: string
  name: string
  icon: typeof Sun
}

function NavItemLink({ item, tone }: { item: NavItem; tone: keyof typeof NAV_TONES }) {
  const Icon = item.icon
  return (
    <NavLink
      to={item.path}
      aria-label={`${item.verb} · ${item.name}`}
      title={`${item.verb} · ${item.name}`}
      className={({ isActive }) =>
        cx('flex h-9 shrink-0 items-center gap-2 rounded-lg px-2.5 text-sm font-medium transition', isActive ? NAV_TONES[tone].active : NAV_TONES[tone].idle)
      }
    >
      <Icon aria-hidden className="size-4" />
      <span className="hidden md:inline">{item.verb}</span>
    </NavLink>
  )
}

const THEME_ICONS: Record<Theme, typeof Sun> = { system: Monitor, light: Sun, dark: Moon }

export function Header() {
  const { meta, language, setLanguage } = useMeta()
  const { theme, cycleTheme } = useTheme()
  const ThemeIcon = THEME_ICONS[theme]

  return (
    <header className="sticky top-0 z-20 border-b border-line/70 bg-bg/80 backdrop-blur-md">
      <div className="mx-auto flex min-h-16 max-w-7xl flex-wrap items-center gap-x-2 gap-y-2 px-4 py-3 sm:gap-x-3 sm:px-6 xl:flex-nowrap">
        <Link to="/" className="flex shrink-0 items-center gap-2.5 rounded-lg font-semibold tracking-tight" aria-label="Languages, home">
          <Logo />
          <span className="hidden lg:inline">Languages</span>
        </Link>

        <nav aria-label="Exercises" className="order-last flex w-full min-w-0 flex-wrap items-center justify-center gap-0.5 xl:order-none xl:ml-3 xl:w-auto xl:flex-1 xl:justify-start">
          <NavItemLink item={READ} tone="accent" />
          <span aria-hidden className="mx-1 hidden h-5 w-px shrink-0 bg-line md:block" />
          {exercisesFor(language.code).map((exercise) => (
            <NavItemLink key={exercise.path} item={exercise} tone="accent" />
          ))}
          <span aria-hidden className="mx-1 hidden h-5 w-px shrink-0 bg-line md:block" />
          {TOOLS.map((tool, index) => (
            <span key={tool.path} className="flex items-center">
              {index > 0 && <span aria-hidden className="mx-1 hidden h-5 w-px shrink-0 bg-line md:block" />}
              <NavItemLink item={tool} tone={tool.tone} />
            </span>
          ))}
          <span aria-hidden className="mx-1 hidden h-5 w-px shrink-0 bg-line md:block" />
          <NavItemLink item={ASK} tone="info" />
        </nav>

        <div className="ml-auto flex shrink-0 items-center gap-2">
          {meta.demo && (
            <span className="hidden rounded-full bg-warn-soft px-2.5 py-1 text-xs font-semibold text-warn sm:inline" title="Placeholder exercises: no API calls, no practice history">
              Demo
            </span>
          )}
          <div role="group" aria-label="Language" className="flex rounded-xl border border-line bg-surface p-0.5">
            {meta.languages.map((option) => (
              <button
                key={option.code}
                type="button"
                aria-pressed={option.code === language.code}
                title={option.name}
                onClick={() => setLanguage(option.code)}
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
