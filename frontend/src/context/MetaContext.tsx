import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { LoaderCircle, RotateCcw, ServerCrash } from 'lucide-react'
import { api, messageOf } from '../api'
import { usePersistentState } from '../hooks/usePersistentState'
import { discardSessions } from '../lib/storage'
import type { LanguageCode, LanguageInfo, Meta } from '../types'
import { Button } from '../components/Button'
import { Logo } from '../components/Logo'

interface MetaContextValue {
  meta: Meta
  language: LanguageInfo
  setLanguage: (code: LanguageCode) => void
  languageInfo: (code: LanguageCode) => LanguageInfo
}

const MetaContext = createContext<MetaContextValue | null>(null)

export function MetaProvider({ children }: { children: ReactNode }) {
  const [meta, setMeta] = useState<Meta | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  const [code, setCode] = usePersistentState<LanguageCode | null>('language', null)

  useEffect(() => {
    let active = true
    api
      .meta()
      .then((value) => active && setMeta(value))
      .catch((reason: unknown) => active && setError(messageOf(reason)))
    return () => {
      active = false
    }
  }, [attempt])

  if (error) {
    return (
      <Splash>
        <ServerCrash aria-hidden className="size-8 text-bad" />
        <p className="max-w-sm text-center text-[15px] leading-relaxed text-muted">{error}</p>
        <Button
          icon={RotateCcw}
          onClick={() => {
            setError(null)
            setAttempt((value) => value + 1)
          }}
        >
          Try again
        </Button>
      </Splash>
    )
  }

  if (!meta) {
    return (
      <Splash>
        <LoaderCircle aria-label="Loading" className="size-6 animate-spin text-muted" />
      </Splash>
    )
  }

  const languageInfo = (value: LanguageCode) =>
    meta.languages.find((language) => language.code === value) ??
    meta.languages.find((language) => language.code === meta.defaults.language) ??
    meta.languages[0]

  const language = languageInfo(code ?? meta.defaults.language)
  const setLanguage = (value: LanguageCode) => {
    if (value === language.code) return
    discardSessions()
    setCode(value)
  }

  return <MetaContext.Provider value={{ meta, language, setLanguage, languageInfo }}>{children}</MetaContext.Provider>
}

function Splash({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-5 px-6">
      <Logo />
      {children}
    </div>
  )
}

export function useMeta(): MetaContextValue {
  const value = useContext(MetaContext)
  if (!value) throw new Error('useMeta must be used inside MetaProvider')
  return value
}
