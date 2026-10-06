import { useEffect } from 'react'
import { usePersistentState } from './usePersistentState'

export type Theme = 'system' | 'light' | 'dark'

const NEXT_THEME: Record<Theme, Theme> = { system: 'light', light: 'dark', dark: 'system' }

export function useTheme() {
  const [theme, setTheme] = usePersistentState<Theme>('theme', 'system')

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const apply = () =>
      document.documentElement.classList.toggle('dark', theme === 'dark' || (theme === 'system' && media.matches))
    apply()
    media.addEventListener('change', apply)
    return () => media.removeEventListener('change', apply)
  }, [theme])

  return { theme, cycleTheme: () => setTheme((current) => NEXT_THEME[current]) }
}
