import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { createPortal } from 'react-dom'
import { Eye, EyeOff, KeyRound } from 'lucide-react'
import { api, API_KEY_CHANGED, messageOf } from '../api'
import type { ApiKeyStatus } from '../types'
import { Button } from './Button'
import { cx } from '../lib/cx'

export function useApiKeyStatus(provider: 'openai' | 'elevenlabs' = 'openai'): [ApiKeyStatus | null, (status: ApiKeyStatus) => void] {
  const [status, setStatus] = useState<ApiKeyStatus | null>(null)

  useEffect(() => {
    let alive = true
    ;(provider === 'openai' ? api.apiKey() : api.elevenlabsKey()).then((value) => alive && setStatus(value)).catch(() => {})
    return () => {
      alive = false
    }
  }, [provider])

  return [status, setStatus]
}

interface ApiKeyButtonProps {
  provider?: 'openai' | 'elevenlabs'
  status: ApiKeyStatus | null
  onSaved: (status: ApiKeyStatus) => void
  onSelect?: () => void
}

export function ApiKeyButton({ status, onSaved, onSelect, provider = 'openai' }: ApiKeyButtonProps) {
  const titleId = useId()
  const errorId = useId()
  const isOpenAI = provider === 'openai'
  const service = isOpenAI ? 'OpenAI' : 'ElevenLabs' 
  const [open, setOpen] = useState(false)
  const [key, setKey] = useState('')
  const [visible, setVisible] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const dialogRef = useRef<HTMLDialogElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (open && !dialog.open) {
      dialog.showModal()
      inputRef.current?.focus()
    }
    if (!open && dialog.open) dialog.close()
  }, [open])

  const close = () => {
    if (busy) return
    setOpen(false)
    setKey('')
    setVisible(false)
    setError(null)
  }

  const save = async (event: FormEvent) => {
    event.preventDefault()
    if (!key.trim() || busy) return
    setBusy(true)
    setError(null)
    try {
      onSaved(await (isOpenAI ? api.setApiKey(key) : api.setElevenlabsKey(key)))
      if (isOpenAI) window.dispatchEvent(new Event(API_KEY_CHANGED))
      setBusy(false)
      setOpen(false)
      setKey('')
      setVisible(false)
    } catch (reason) {
      setError(messageOf(reason))
      setBusy(false)
      inputRef.current?.focus()
    }
  }

  const missing = status !== null && !status.configured
  return (
    <>
      <button type="button" role="menuitem" tabIndex={-1} aria-label={`Set ${service} API key`}
        onClick={() => { onSelect?.(); setOpen(true) }}
        className="flex w-full cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-ink hover:bg-surface-2 focus:bg-surface-2 focus:outline-none">
        <KeyRound aria-hidden className={cx('size-4', missing && isOpenAI ? 'text-bad' : 'text-accent')} />
        <span>{service} key</span>
        {status && (
          <span className={cx('ml-auto font-mono text-xs', missing ? 'text-bad' : 'text-muted')}>
            {status.configured ? `…${status.hint}` : 'not set'}
          </span>
        )}
      </button>
      {createPortal(
        <dialog
          ref={dialogRef}
          aria-labelledby={titleId}
          onCancel={(event) => {
            event.preventDefault()
            close()
          }}
          onClick={(event) => {
            if (event.target === dialogRef.current) close()
          }}
          onKeyDown={(event) => event.stopPropagation()}
          className="m-auto w-[min(92vw,28rem)] rounded-2xl border border-line bg-surface p-0 text-ink shadow-2xl backdrop:bg-black/45 backdrop:backdrop-blur-[2px]"
        >
          {open && (
            <form className="p-6" onSubmit={(event) => void save(event)}>
              <h2 id={titleId} className="text-lg font-semibold tracking-tight">{service} API key</h2>
              <p className="mt-2 text-[15px] leading-relaxed text-muted">
                {status?.configured
                  ? `A key ending in …${status.hint} is in use${status.source === 'environment' ? ', from the environment' : ''}. A new key replaces it.`
                  : isOpenAI ? 'No key is set yet. Every exercise needs one.' : 'Optional: use ElevenLabs voices for speech. Enable Text to Speech; Voices read is optional and allows voice selection. Text is sent to ElevenLabs and uses your account’s credits.'}{' '}
                The key is saved only on this computer, separately from the other service.
              </p>
              <div className="relative mt-5">
                <input
                  ref={inputRef}
                  type={visible ? 'text' : 'password'}
                  value={key}
                  disabled={busy}
                  onChange={(event) => setKey(event.target.value)}
                  aria-label={`New ${service} API key`}
                  aria-invalid={error !== null}
                  aria-describedby={error ? errorId : undefined}
                  placeholder={isOpenAI ? 'sk-…' : 'sk_…'}
                  name={isOpenAI ? 'openai-api-key' : 'elevenlabs-api-key'}
                  autoComplete="off"
                  autoCapitalize="off"
                  autoCorrect="off"
                  spellCheck={false}
                  className="h-11 w-full rounded-xl border border-line bg-bg pl-3.5 pr-11 font-mono text-sm text-ink caret-accent outline-none transition focus:border-accent disabled:opacity-70"
                />
                <button type="button" onClick={() => setVisible((value) => !value)}
                  aria-label={visible ? 'Hide key' : 'Show key'} title={visible ? 'Hide key' : 'Show key'}
                  className="absolute right-1 top-1 flex size-9 cursor-pointer items-center justify-center rounded-lg text-muted hover:bg-surface-2 hover:text-ink">
                  {visible ? <EyeOff aria-hidden className="size-4" /> : <Eye aria-hidden className="size-4" />}
                </button>
              </div>
              {error && <p id={errorId} role="alert" className="mt-3 text-sm text-bad">{error}</p>}
              <div className="mt-6 flex justify-end gap-2">
                <Button variant="secondary" onClick={close} disabled={busy}>Cancel</Button>
                <Button type="submit" disabled={!key.trim() || busy}>{busy ? 'Saving…' : 'Save key'}</Button>
              </div>
            </form>
          )}
        </dialog>,
        document.body,
      )}
    </>
  )
}
