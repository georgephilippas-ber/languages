import { useEffect, useRef, useState } from 'react'
import { LoaderCircle, Mic, Square, X } from 'lucide-react'
import { api, isAbort, messageOf } from '../api'
import type { LanguageCode } from '../types'
import { Button } from './Button'

type Phase = 'idle' | 'requesting' | 'recording' | 'transcribing'
const MAX_RECORDING_MS = 60_000

export function DictationButton({ language, disabled, onTranscript, onBusyChange }: {
  language: LanguageCode; disabled: boolean; onTranscript: (text: string) => void; onBusyChange: (busy: boolean) => void
}) {
  const [phase, setPhase] = useState<Phase>('idle')
  const [error, setError] = useState('')
  const mounted = useRef(true)
  const sequence = useRef(0)
  const recorder = useRef<MediaRecorder | null>(null)
  const stream = useRef<MediaStream | null>(null)
  const controller = useRef<AbortController | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const stopTracks = () => { stream.current?.getTracks().forEach((track) => track.stop()); stream.current = null }
  const clearTimer = () => { if (timer.current !== null) clearTimeout(timer.current); timer.current = null }
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
      sequence.current++
      controller.current?.abort()
      clearTimer()
      if (recorder.current && recorder.current.state !== 'inactive') recorder.current.stop()
      stopTracks()
    }
  }, [])
  const cancel = () => {
    sequence.current++
    controller.current?.abort(); controller.current = null
    clearTimer()
    if (recorder.current && recorder.current.state !== 'inactive') recorder.current.stop()
    recorder.current = null
    stopTracks()
    setPhase('idle'); setError(''); onBusyChange(false)
  }
  const start = async () => {
    if (disabled || phase !== 'idle') return
    setError('')
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      setError('Microphone access requires a secure connection. On another device, use the HTTPS internet-sharing link.')
      return
    }
    if (typeof MediaRecorder === 'undefined') {
      setError('This browser cannot record audio. Please try another browser or type your sentence.')
      return
    }
    const current = ++sequence.current
    setPhase('requesting'); onBusyChange(true)
    try {
      const input = await navigator.mediaDevices.getUserMedia({ audio: true })
      if (!mounted.current || sequence.current !== current) { input.getTracks().forEach((track) => track.stop()); return }
      stream.current = input
      const type = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/ogg;codecs=opus'].find((value) => MediaRecorder.isTypeSupported?.(value))
      const recording = type ? new MediaRecorder(input, { mimeType: type }) : new MediaRecorder(input)
      recorder.current = recording
      const chunks: Blob[] = []
      let failed = false
      recording.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data) }
      recording.onerror = () => {
        failed = true
        if (!mounted.current || sequence.current !== current) return
        clearTimer(); if (stream.current === input) stopTracks()
        setError('Recording failed. Please try again.'); setPhase('idle'); onBusyChange(false)
      }
      recording.onstop = () => {
        if (stream.current === input) stopTracks()
        if (recorder.current === recording) recorder.current = null
        if (!mounted.current || sequence.current !== current || failed) return
        clearTimer()
        const mime = (recording.mimeType || chunks[0]?.type || 'audio/webm').split(';', 1)[0]
        const audio = new Blob(chunks, { type: mime })
        if (!audio.size) { setError('The recording was empty. Please try again.'); setPhase('idle'); onBusyChange(false); return }
        setPhase('transcribing')
        const request = new AbortController(); controller.current = request
        api.transcribe(audio, language, request.signal).then((result) => {
          if (mounted.current && sequence.current === current) onTranscript(result.text)
        }).catch((reason: unknown) => {
          if (mounted.current && sequence.current === current && !isAbort(reason)) setError(messageOf(reason))
        }).finally(() => {
          if (mounted.current && sequence.current === current) { controller.current = null; setPhase('idle'); onBusyChange(false) }
        })
      }
      recording.start()
      setPhase('recording')
      timer.current = setTimeout(() => { if (recording.state !== 'inactive') recording.stop() }, MAX_RECORDING_MS)
    } catch (reason) {
      if (!mounted.current || sequence.current !== current) return
      recorder.current = null
      stopTracks()
      const errorName = reason instanceof DOMException ? reason.name : ''
      setError(errorName === 'NotAllowedError' ? 'Microphone permission was denied. Allow it in your browser settings and try again.'
        : errorName === 'NotFoundError' ? 'No microphone was found.' : 'Could not start the microphone. Please try again.')
      setPhase('idle'); onBusyChange(false)
    }
  }
  return <div className="mt-3">
    <div className="flex flex-wrap items-center gap-2">
      {phase === 'idle' && <Button variant="secondary" size="sm" icon={Mic} disabled={disabled} onClick={() => void start()}>Speak sentence</Button>}
      {phase === 'requesting' && <span role="status" className="text-sm text-muted">Waiting for microphone permission…</span>}
      {phase === 'recording' && <><Button variant="secondary" size="sm" icon={Square} onClick={() => { if (recorder.current && recorder.current.state !== 'inactive') recorder.current.stop() }}>Stop and transcribe</Button><span role="status" className="text-sm text-muted">Recording · up to 60 seconds</span></>}
      {phase === 'transcribing' && <span role="status" className="flex items-center gap-2 text-sm text-muted"><LoaderCircle aria-hidden className="size-4 animate-spin" />Transcribing…</span>}
      {phase !== 'idle' && <Button variant="ghost" size="sm" icon={X} onClick={cancel}>Cancel</Button>}
    </div>
    {error && <p role="alert" className="mt-2 text-sm text-bad">{error}</p>}
    <p className="mt-2 text-xs text-muted">Your recording is sent to ElevenLabs for transcription and may use credits. Review the text before checking it.</p>
  </div>
}
