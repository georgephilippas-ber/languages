import { useEffect, useState } from 'react'
import { Volume2 } from 'lucide-react'
import type { LanguageCode } from '../types'
import { speak, speechAvailable, stopSpeaking } from '../lib/speech'
import { Button } from './Button'

export function SpeakButton({ text, code }: { text: string; code: LanguageCode }) {
  const [speaking, setSpeaking] = useState(false)

  useEffect(() => () => stopSpeaking(), [])

  if (!speechAvailable || !text.trim()) return null

  const toggle = () => {
    if (speaking) {
      stopSpeaking()
      setSpeaking(false)
    } else {
      setSpeaking(true)
      speak(text, code, () => setSpeaking(false))
    }
  }

  return (
    <Button variant={speaking ? 'secondary' : 'ghost'} size="sm" icon={Volume2} aria-pressed={speaking} onClick={toggle}>
      {speaking ? 'Stop' : 'Listen'}
    </Button>
  )
}
