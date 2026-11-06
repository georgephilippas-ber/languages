import { useNavigate } from 'react-router'
import { useMeta } from '../context/MetaContext'

export function useLucky() {
  const { meta, setLanguage } = useMeta()
  const navigate = useNavigate()
  const available = meta.languages.filter((option) => option.files.reduce((sum, file) => sum + file.terms, 0) >= 12)
  const feelLucky = () => {
    if (!available.length) return
    const selected = available[Math.floor(Math.random() * available.length)]
    const mode = Math.floor(Math.random() * 3)
    const path = mode === 0 ? '/quiz' : mode === 1 ? '/typed' : Math.random() < 0.5 ? '/translate/recognize' : '/translate/produce'
    if (mode !== 2) setLanguage(selected.code, { preserveSessions: true })
    navigate(path, { state: { start: 'lucky', luckyLanguage: selected.code } })
  }
  return { available: available.length > 0, feelLucky }
}
