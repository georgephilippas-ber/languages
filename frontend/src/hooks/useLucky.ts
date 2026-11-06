import { useState } from 'react'
import { useNavigate } from 'react-router'
import { useMeta } from '../context/MetaContext'
import { LUCKY_PATHS, readLuckySession, type LuckySnapshot } from '../lib/luckySession'

let luckyNavigationSequence = 0

export function useLucky() {
  const { meta, language } = useMeta()
  const navigate = useNavigate()
  const [choice, setChoice] = useState<LuckySnapshot | null>(null)
  const [choiceMode, setChoiceMode] = useState<'standard' | 'phrasal'>('standard')
  const singleAvailable = language.files.reduce((sum, file) => sum + file.terms, 0) >= 12
  const mixedAvailable = language.code !== 'EN' && meta.languages.some((option) => (option.code === 'EN' || option.code === language.code) && option.files.some((file) =>
    !(option.code === 'EN' && typeof file.number === 'string' && file.number.startsWith('phrasal-verbs:')) && file.terms > 0,
  ))
  const modes = [...(singleAvailable ? ['quiz', 'typed'] : []), ...(mixedAvailable ? ['translate'] : [])]
  const phrasalAvailable = language.code === 'EN' && language.files.some((file) => typeof file.number === 'string' && file.number.startsWith('phrasal-verbs:') && file.terms > 0)
  const start = (phrasal: boolean) => {
    setChoice(null)
    const choices = phrasal ? (phrasalAvailable ? ['quiz', 'typed'] : []) : modes
    if (!choices.length) return
    const mode = choices[Math.floor(Math.random() * choices.length)]
    const path = mode === 'quiz' ? '/quiz' : mode === 'typed' ? '/typed' : Math.random() < 0.5 ? '/translate/recognize' : '/translate/produce'
    navigate(path, { state: { start: 'lucky', luckyLanguage: language.code, luckyFiles: phrasal ? 'phrasal-verbs' : 'all', luckyRequestId: ++luckyNavigationSequence } })
  }
  const feelLucky = () => {
    const saved = readLuckySession()
    setChoiceMode('standard')
    if (saved) setChoice(saved)
    else start(false)
  }
  const phrasalLucky = () => {
    const saved = readLuckySession()
    setChoiceMode('phrasal')
    if (saved?.session.request.language === 'EN' && saved.session.request.files === 'phrasal-verbs') setChoice(saved)
    else start(true)
  }
  const startNew = () => start(choiceMode === 'phrasal')
  const resume = () => {
    if (!choice) return
    const path = LUCKY_PATHS[choice.kind]
    setChoice(null)
    navigate(path, { state: { resumeLucky: true } })
  }
  return { available: modes.length > 0 || !!readLuckySession(), canStartNew: choiceMode === 'phrasal' ? phrasalAvailable : modes.length > 0, phrasalAvailable, phrasalLucky, feelLucky, choice, resume, startNew, cancel: () => setChoice(null) }
}
