import { useNavigate } from 'react-router'
import { Monitor, Moon, Sun } from 'lucide-react'
import { useMeta } from '../context/MetaContext'
import type { LanguageCode } from '../types'
import { useTheme, type Theme } from '../hooks/useTheme'
import { cx } from '../lib/cx'
import { ModelPicker } from './ModelPicker'
import { AppMenu } from './AppMenu'

const THEME_ICONS: Record<Theme, typeof Sun> = { system: Monitor, light: Sun, dark: Moon }

export function Header() {
  const { meta, language, setLanguage } = useMeta()
  const { theme, cycleTheme } = useTheme()
  const navigate = useNavigate()
  const ThemeIcon = THEME_ICONS[theme]
  const switchLanguage = (code: LanguageCode) => {
    if (code === language.code) return
    setLanguage(code)
    navigate('/')
  }

  return (
    <header className="sticky top-0 z-20 border-b border-line/70 bg-bg/80 backdrop-blur-md">
      <div className="mx-auto flex min-h-16 max-w-7xl items-center gap-2 px-4 py-3 sm:gap-3 sm:px-6">
        <AppMenu />

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
