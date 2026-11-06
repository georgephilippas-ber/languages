import { useState } from 'react'
import { useNavigate } from 'react-router'
import { useMeta } from '../context/MetaContext'
import { LUCKY_PATHS, readLuckySession, type LuckySnapshot } from '../lib/luckySession'

let luckyNavigationSequence = 0

export function useLucky() {
  const { meta, language } = useMeta()
  const navigate = useNavigate()
  const [choice, setChoice] = useState<LuckySnapshot | null>(null)
  const singleAvailable = language.files.reduce((sum, file) => sum + file.terms, 0) >= 12
  const mixedAvailable = meta.languages.some((option) => option.files.some((file) =>
    !(option.code === 'EN' && typeof file.number === 'string' && file.number.startsWith('phrasal-verbs:')) && file.terms > 0,
  ))
  const modes = [...(singleAvailable ? ['quiz', 'typed'] : []), ...(mixedAvailable ? ['translate'] : [])]
  const startNew = () => {
    setChoice(null)
    if (!modes.length) return
    const mode = modes[Math.floor(Math.random() * modes.length)]
    const path = mode === 'quiz' ? '/quiz' : mode === 'typed' ? '/typed' : Math.random() < 0.5 ? '/translate/recognize' : '/translate/produce'
    navigate(path, { state: { start: 'lucky', luckyLanguage: language.code, luckyRequestId: ++luckyNavigationSequence } })
  }
  const feelLucky = () => {
    const saved = readLuckySession()
    if (saved) setChoice(saved)
    else startNew()
  }
  const resume = () => {
    if (!choice) return
    const path = LUCKY_PATHS[choice.kind]
    setChoice(null)
    navigate(path, { state: { resumeLucky: true } })
  }
  return { available: modes.length > 0 || !!readLuckySession(), canStartNew: modes.length > 0, feelLucky, choice, resume, startNew, cancel: () => setChoice(null) }
}
