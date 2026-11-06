import { useNavigate } from 'react-router'
import { useMeta } from '../context/MetaContext'

export function useLucky() {
  const { meta, language } = useMeta()
  const navigate = useNavigate()
  const singleAvailable = language.files.reduce((sum, file) => sum + file.terms, 0) >= 12
  const mixedAvailable = meta.languages.some((option) => option.files.some((file) =>
    !(option.code === 'EN' && typeof file.number === 'string' && file.number.startsWith('phrasal-verbs:')) && file.terms > 0,
  ))
  const modes = [...(singleAvailable ? ['quiz', 'typed'] : []), ...(mixedAvailable ? ['translate'] : [])]
  const feelLucky = () => {
    if (!modes.length) return
    const mode = modes[Math.floor(Math.random() * modes.length)]
    const path = mode === 'quiz' ? '/quiz' : mode === 'typed' ? '/typed' : Math.random() < 0.5 ? '/translate/recognize' : '/translate/produce'
    navigate(path, { state: { start: 'lucky', luckyLanguage: language.code } })
  }
  return { available: modes.length > 0, feelLucky }
}
