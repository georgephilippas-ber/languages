import { Link, NavLink } from 'react-router'
import { Monitor, Moon, Sun } from 'lucide-react'
import { useMeta } from '../context/MetaContext'
import { exercises } from '../exercises'
import { useTheme, type Theme } from '../hooks/useTheme'
import { cx } from '../lib/cx'
import { Logo } from './Logo'

const THEME_ICONS: Record<Theme, typeof Sun> = { system: Monitor, light: Sun, dark: Moon }

export function Header() {
  const { meta, language, setLanguage } = useMeta()
  const { theme, cycleTheme } = useTheme()
  const ThemeIcon = THEME_ICONS[theme]

  return (
    <header className="sticky top-0 z-20 border-b border-line/70 bg-bg/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-5xl items-center gap-2 px-4 sm:gap-3 sm:px-6">
        <Link to="/" className="flex shrink-0 items-center gap-2.5 rounded-lg font-semibold tracking-tight" aria-label="Languages, home">
          <Logo />
          <span className="hidden lg:inline">Languages</span>
        </Link>

        <nav aria-label="Exercises" className="ml-1 flex items-center gap-0.5 sm:ml-3">
          {exercises.map((exercise) => {
            const Icon = exercise.icon
            return (
              <NavLink
                key={exercise.kind}
                to={exercise.path}
                title={`${exercise.verb} · ${exercise.name}`}
                className={({ isActive }) =>
                  cx(
                    'flex h-9 items-center gap-2 rounded-lg px-2.5 text-sm font-medium transition',
                    isActive ? 'bg-surface text-ink shadow-sm ring-1 ring-line' : 'text-muted hover:bg-surface-2 hover:text-ink',
                  )
                }
              >
                <Icon aria-hidden className="size-4" />
                <span className="hidden sm:inline">{exercise.verb}</span>
              </NavLink>
            )
          })}
        </nav>

        <div className="ml-auto flex items-center gap-2">
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
    </header>
  )
}
