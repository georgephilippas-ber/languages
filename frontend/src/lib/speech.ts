import type { LanguageCode } from '../types'

const VOICE_LANGUAGES: Record<LanguageCode, string> = { DE: 'de-DE', FR: 'fr-FR', EN: 'en-GB' }
const VOICE_WAIT_MS = 900

export const speechAvailable = typeof window !== 'undefined' && 'speechSynthesis' in window

type ActiveSpeech = { end: () => void; cleanup?: () => void }
let active: ActiveSpeech | null = null

function isNaturalOnline(voice: SpeechSynthesisVoice): boolean {
  return !voice.localService && /natural|neural/i.test(voice.name)
}

function chooseVoice(voices: SpeechSynthesisVoice[], language: string, natural: boolean): SpeechSynthesisVoice | null {
  const wanted = language.toLowerCase()
  const sameLanguage = voices.filter((voice) => voice.lang.toLowerCase().split('-')[0] === wanted.split('-')[0])
  const exact = (voice: SpeechSynthesisVoice) => voice.lang.toLowerCase() === wanted
  if (natural) {
    return sameLanguage.find((voice) => exact(voice) && isNaturalOnline(voice)) ??
      sameLanguage.find(isNaturalOnline) ?? null
  }
  return sameLanguage.find((voice) => exact(voice) && voice.localService) ??
    sameLanguage.find((voice) => voice.localService) ??
    sameLanguage.find(exact) ?? sameLanguage[0] ?? null
}

export function speak(text: string, code: LanguageCode, onEnd: () => void): void {
  if (!speechAvailable) return
  const synthesis = window.speechSynthesis
  stopSpeaking()
  const language = VOICE_LANGUAGES[code]
  const request: ActiveSpeech = { end: onEnd }
  active = request

  const finish = () => {
    if (active !== request) return
    request.cleanup?.()
    active = null
    onEnd()
  }
  const play = (voices: SpeechSynthesisVoice[], preferNatural: boolean) => {
    if (active !== request) return
    request.cleanup?.()
    request.cleanup = undefined
    const natural = preferNatural ? chooseVoice(voices, language, true) : null
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = language
    utterance.rate = 0.95
    utterance.voice = natural ?? chooseVoice(voices, language, false)
    utterance.onend = finish
    utterance.onerror = () => {
      if (active !== request) return
      const local = chooseVoice(voices.filter((voice) => voice.localService), language, false)
      if (natural && local) play([local], false)
      else finish()
    }
    synthesis.speak(utterance)
  }

  const voices = synthesis.getVoices()
  const isEdge = /Edg\//.test(navigator.userAgent)
  const shouldWait = !voices.length || (isEdge && !chooseVoice(voices, language, true))
  if (!shouldWait || typeof synthesis.addEventListener !== 'function') {
    play(voices, true)
    return
  }
  let timeout: ReturnType<typeof setTimeout>
  const cleanup = () => {
    clearTimeout(timeout)
    synthesis.removeEventListener('voiceschanged', changed)
  }
  const changed = () => {
    const available = synthesis.getVoices()
    if (chooseVoice(available, language, true) || (!isEdge && available.length)) play(available, true)
  }
  request.cleanup = cleanup
  synthesis.addEventListener('voiceschanged', changed)
  timeout = setTimeout(() => play(synthesis.getVoices(), true), VOICE_WAIT_MS)
  changed()
}

export function stopSpeaking(): void {
  if (!speechAvailable) return
  const request = active
  active = null
  request?.cleanup?.()
  window.speechSynthesis.cancel()
  request?.end()
}
