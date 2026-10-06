import type { LanguageCode } from '../types'

const VOICE_LANGUAGES: Record<LanguageCode, string> = { DE: 'de-DE', FR: 'fr-FR', EN: 'en-GB' }

export const speechAvailable = typeof window !== 'undefined' && 'speechSynthesis' in window

export function speak(text: string, code: LanguageCode, onEnd: () => void): void {
  if (!speechAvailable) return
  const synthesis = window.speechSynthesis
  synthesis.cancel()

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
  utterance.onend = onEnd
  utterance.onerror = onEnd
  synthesis.speak(utterance)
}

export function stopSpeaking(): void {
  if (speechAvailable) window.speechSynthesis.cancel()
}
