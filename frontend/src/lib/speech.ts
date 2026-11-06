import type { LanguageCode } from '../types'

const VOICE_LANGUAGES: Record<LanguageCode, string> = { DE: 'de-DE', FR: 'fr-FR', EN: 'en-GB' }
const VOICE_WAIT_MS = 900

export const speechAvailable = typeof window !== 'undefined' && 'speechSynthesis' in window

type ActiveSpeech = { end: (cancelled?: boolean) => void; cleanup?: () => void; fade?: () => void }
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

function speakSingle(text: string, code: LanguageCode, onEnd: (cancelled?: boolean) => void, onUnavailable?: (reason: 'not-configured' | 'unavailable', detail?: string) => void, fadePrevious = false): void {
  if (!speechAvailable) return
  const synthesis = window.speechSynthesis
  stopSpeaking(fadePrevious)
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

  const browserSpeech = () => {
    if (active !== request) return
    request.cleanup?.()
    request.cleanup = undefined
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

  const controller = new AbortController()
  let notConfigured = false
  let failureDetail: string | undefined
  request.cleanup = () => controller.abort()
  void fetch('/api/speech', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, language: code }), signal: controller.signal,
  }).then(async (response) => {
    if (!response.ok) {
      notConfigured = response.status === 404
      if (!notConfigured) {
        try {
          const body = await response.json() as { detail?: unknown }
          if (typeof body.detail === 'string' && body.detail.startsWith('ElevenLabs ') && body.detail.length < 200) failureDetail = body.detail
        } catch { /* Use a general fallback message. */ }
      }
      throw new Error('Speech service unavailable')
    }
    const blob = await response.blob()
    if (active !== request) return
    const url = URL.createObjectURL(blob)
    const audio = new Audio(url)
    let finished = false
    const cleanup = () => { audio.pause(); URL.revokeObjectURL(url) }
    const fallback = () => {
      if (finished || active !== request) return
      finished = true
      onUnavailable?.('unavailable')
      browserSpeech()
    }
    request.cleanup = cleanup
    request.fade = () => {
      const start = audio.volume
      const started = performance.now()
      const timer = setInterval(() => {
        const remaining = Math.max(0, 1 - (performance.now() - started) / 250)
        audio.volume = start * remaining
        if (!remaining) { clearInterval(timer); cleanup() }
      }, 25)
    }
    audio.onended = () => { if (!finished) { finished = true; finish() } }
    audio.onerror = fallback
    void audio.play().catch(fallback)
  }).catch(() => {
    if (active === request) {
      onUnavailable?.(notConfigured ? 'not-configured' : 'unavailable', failureDetail)
      browserSpeech()
    }
  })
}

export function stopSpeaking(fade = false): void {
  if (!speechAvailable) return
  const request = active
  active = null
  if (fade && request?.fade) request.fade()
  else request?.cleanup?.()
  window.speechSynthesis.cancel()
  request?.end(true)
}


export function speak(text: string, code: LanguageCode, onEnd: () => void, onUnavailable?: (reason: 'not-configured' | 'unavailable', detail?: string) => void, fadePrevious = false): void {
  const chunks: string[] = []
  let remaining = text.trim()
  while (remaining.length > 950) {
    const prefix = remaining.slice(0, 950)
    const boundary = Math.max(prefix.lastIndexOf('. '), prefix.lastIndexOf('! '), prefix.lastIndexOf('? '), prefix.lastIndexOf(' '))
    const end = boundary > 100 ? boundary + 1 : 950
    chunks.push(remaining.slice(0, end).trim())
    remaining = remaining.slice(end).trim()
  }
  if (remaining) chunks.push(remaining)
  if (!chunks.length) { onEnd(); return }
  const play = (index: number) => speakSingle(chunks[index], code, (cancelled) => {
    if (cancelled || index === chunks.length - 1) onEnd()
    else play(index + 1)
  }, onUnavailable, index === 0 && fadePrevious)
  play(0)
}
