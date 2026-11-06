import type { LanguageCode } from '../types'

const VOICE_LANGUAGES: Record<LanguageCode, string> = { DE: 'de-DE', FR: 'fr-FR', EN: 'en-GB' }

export const speechAvailable = typeof window !== 'undefined' && 'speechSynthesis' in window

let currentEnd: (() => void) | null = null

export function speak(text: string, code: LanguageCode, onEnd: () => void): void {
  if (!speechAvailable) return
  const synthesis = window.speechSynthesis
  stopSpeaking()

  const language = VOICE_LANGUAGES[code]
  const voices = synthesis.getVoices()
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = language
  utterance.rate = 0.95
  utterance.voice =
    voices.find((voice) => voice.lang === language && voice.localService) ??
    voices.find((voice) => voice.lang === language) ??
    voices.find((voice) => voice.lang.startsWith(language.slice(0, 2))) ??
    null
  currentEnd = onEnd
  const finish = () => {
    if (currentEnd !== onEnd) return
    currentEnd = null
    onEnd()
  }
  utterance.onend = finish
  utterance.onerror = finish
  synthesis.speak(utterance)
}

export function stopSpeaking(): void {
  if (!speechAvailable) return
  const end = currentEnd
  currentEnd = null
  window.speechSynthesis.cancel()
  end?.()
}
