import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { createPortal } from 'react-dom'
import { Eye, EyeOff, KeyRound } from 'lucide-react'
import { api, API_KEY_CHANGED, messageOf } from '../api'
import type { ApiKeyStatus } from '../types'
import { Button } from './Button'
import { cx } from '../lib/cx'

type Provider = 'openai' | 'elevenlabs'

export function useApiKeyStatus(provider: Provider = 'openai'): [ApiKeyStatus | null, (status: ApiKeyStatus) => void] {
  const [status, setStatus] = useState<ApiKeyStatus | null>(null)
  useEffect(() => {
    let alive = true
    ;(provider === 'openai' ? api.apiKey() : api.elevenlabsKey()).then((value) => alive && setStatus(value)).catch(() => {})
    return () => { alive = false }
  }, [provider])
  return [status, setStatus]
}

function KeyForm({ provider, status, onSaved }: { provider: Provider; status: ApiKeyStatus | null; onSaved: (status: ApiKeyStatus) => void }) {
  const service = provider === 'openai' ? 'OpenAI' : 'ElevenLabs'
  const errorId = useId()
  const [key, setKey] = useState('')
  const [visible, setVisible] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const save = async (event: FormEvent) => {
    event.preventDefault()
    if (!key.trim() || busy) return
    setBusy(true); setError(''); setSaved(false)
    try {
      onSaved(await (provider === 'openai' ? api.setApiKey(key) : api.setElevenlabsKey(key)))
      if (provider === 'openai') window.dispatchEvent(new Event(API_KEY_CHANGED))
      setKey(''); setVisible(false); setSaved(true)
    } catch (reason) { setError(messageOf(reason)) }
    finally { setBusy(false) }
  }
  return <form onSubmit={(event) => void save(event)} className="rounded-xl border border-line p-4">
    <h3 className="font-semibold"><a href={provider === 'openai' ? 'https://platform.openai.com/api-keys' : 'https://elevenlabs.io/app/api/api-keys'} target="_blank" rel="noopener noreferrer" className="text-inherit underline decoration-line underline-offset-4 hover:decoration-current">{service}</a></h3>
    <p className="mt-1 text-sm text-muted">{status?.configured
      ? `Key ending in …${status.hint} is in use${status.source === 'environment' ? ' from the environment' : ''}.`
      : provider === 'openai' ? 'No key is set. Exercises use OpenAI.' : 'Optional: use ElevenLabs voices for speech.'}</p>
    {provider === 'elevenlabs' && <p className="mt-1 text-xs text-muted">Speech text is sent to ElevenLabs and uses your account’s credits.</p>}
    <div className="relative mt-3">
      <input type={visible ? 'text' : 'password'} value={key} disabled={busy} onChange={(event) => { setKey(event.target.value); setSaved(false) }}
        aria-label={`New ${service} API key`} aria-invalid={!!error} aria-describedby={error ? errorId : undefined}
        placeholder={provider === 'openai' ? 'sk-…' : 'sk_…'} name={`${provider}-api-key`} autoComplete="off" autoCapitalize="off" autoCorrect="off" spellCheck={false}
        className="h-11 w-full rounded-xl border border-line bg-bg pl-3.5 pr-11 font-mono text-sm text-ink outline-none focus:border-accent disabled:opacity-70" />
      <button type="button" onClick={() => setVisible((value) => !value)} aria-label={`${visible ? 'Hide' : 'Show'} ${service} key`} className="absolute right-1 top-1 flex size-9 items-center justify-center rounded-lg text-muted hover:bg-surface-2">
        {visible ? <EyeOff aria-hidden className="size-4" /> : <Eye aria-hidden className="size-4" />}
      </button>
    </div>
    {error && <p id={errorId} role="alert" className="mt-2 text-sm text-bad">{error}</p>}
    <div className="mt-3 flex items-center justify-end gap-3">{saved && <span role="status" className="text-sm text-good">{service} key saved</span>}
      <Button type="submit" size="sm" disabled={!key.trim() || busy}>{busy ? 'Saving…' : `Save ${service} key`}</Button>
    </div>
  </form>
}

export function ApiKeyButton({ openai, elevenlabs, onOpenaiSaved, onElevenlabsSaved, onSelect }: {
  openai: ApiKeyStatus | null; elevenlabs: ApiKeyStatus | null; onOpenaiSaved: (status: ApiKeyStatus) => void; onElevenlabsSaved: (status: ApiKeyStatus) => void; onSelect: () => void
}) {
  const titleId = useId()
  const [open, setOpen] = useState(false)
  const dialogRef = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    if (open && !dialogRef.current?.open) dialogRef.current?.showModal()
    else if (!open && dialogRef.current?.open) dialogRef.current.close()
  }, [open])
  return <>
    <button type="button" role="menuitem" tabIndex={-1} onClick={() => { onSelect(); setOpen(true) }} className="flex w-full cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-ink hover:bg-surface-2 focus:bg-surface-2 focus:outline-none">
      <KeyRound aria-hidden className={cx('size-4', openai && !openai.configured ? 'text-bad' : 'text-accent')} />API keys
    </button>
    {createPortal(<dialog ref={dialogRef} aria-labelledby={titleId} onCancel={(event) => { event.preventDefault(); setOpen(false) }} onClick={(event) => { if (event.target === dialogRef.current) setOpen(false) }} onKeyDown={(event) => event.stopPropagation()} className="m-auto max-h-[90vh] w-[min(92vw,32rem)] overflow-auto rounded-2xl border border-line bg-surface p-0 text-ink shadow-2xl backdrop:bg-black/45">
      {open && <div className="p-6"><h2 id={titleId} className="text-lg font-semibold">API keys</h2>
        <p className="mt-2 text-sm text-muted">Each key is stored separately on this computer. Saving one does not change the other.</p>
        <div className="mt-5 space-y-4"><KeyForm provider="openai" status={openai} onSaved={onOpenaiSaved} /><KeyForm provider="elevenlabs" status={elevenlabs} onSaved={onElevenlabsSaved} /></div>
        <div className="mt-5 flex justify-end"><Button variant="secondary" onClick={() => setOpen(false)}>Close</Button></div>
      </div>}
    </dialog>, document.body)}
  </>
}
