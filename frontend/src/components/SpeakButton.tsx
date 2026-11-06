import { useEffect, useState } from 'react'
import { Volume2 } from 'lucide-react'
import type { LanguageCode } from '../types'
import { speak, speechAvailable, stopSpeaking } from '../lib/speech'
import { Button } from './Button'

export function SpeakButton({ text, code, label = 'Listen' }: { text: string; code: LanguageCode; label?: string }) {
  const [speaking, setSpeaking] = useState(false)
  const [notice, setNotice] = useState('')

  useEffect(() => () => stopSpeaking(), [])

  if (!speechAvailable || !text.trim()) return null

  const toggle = () => {
    if (speaking) {
      stopSpeaking()
      setSpeaking(false)
    } else {
      setNotice('')
      setSpeaking(true)
      speak(text, code, () => setSpeaking(false), (reason, detail) => setNotice(reason === 'not-configured'
        ? 'ElevenLabs key not set; using browser voice.' : detail ? `${detail} Using browser voice.` : 'ElevenLabs unavailable; using browser voice.'))
    }
  }

  return (
    <span className="inline-flex flex-col items-start">
      <Button variant={speaking ? 'secondary' : 'ghost'} size="sm" icon={Volume2} aria-pressed={speaking} onClick={toggle}>
        {speaking ? 'Stop' : label}
      </Button>
      {notice && <span role="status" className="text-xs text-muted">{notice}</span>}
    </span>
  )
}
