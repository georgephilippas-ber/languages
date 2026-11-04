import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Smartphone } from 'lucide-react'
import { Button } from './Button'

interface Status { active: boolean; url: string | null; qr?: string; localUrl: string | null; localQr?: string; awakeMinutes: number }

export function DeviceAccessButton({ onSelect }: { onSelect: () => void }) {
  const [open, setOpen] = useState(false)
  const [status, setStatus] = useState<Status | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const dialog = useRef<HTMLDialogElement>(null)
  async function request(path: string, method = 'GET') {
    setBusy(true)
    setError('')
    try {
      const response = await fetch(`/api/device${path}`, { method })
      const body = await response.json()
      if (!response.ok) throw new Error(body.detail || 'The request failed.')
      setStatus(body)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The request failed.')
    } finally { setBusy(false) }
  }
  useEffect(() => {
    if (open && !dialog.current?.open) { dialog.current?.showModal(); void request('') }
    if (!open && dialog.current?.open) dialog.current.close()
  }, [open])
  return <>
    <button type="button" role="menuitem" tabIndex={-1} onClick={() => { onSelect(); setOpen(true) }}
      className="flex w-full cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-ink hover:bg-surface-2 focus:bg-surface-2 focus:outline-none">
      <Smartphone aria-hidden className="size-4 text-accent" />Other devices
    </button>
    {createPortal(<dialog ref={dialog} aria-labelledby="device-title" onCancel={(event) => { event.preventDefault(); setOpen(false) }}
      onKeyDown={(event) => event.stopPropagation()}
      className="m-auto w-[min(94vw,42rem)] rounded-2xl border border-line bg-surface p-0 text-ink shadow-2xl backdrop:bg-black/45">
      {open && <div className="p-6">
        <h2 id="device-title" className="text-lg font-semibold">Access from another device</h2>
        <p className="mt-2 text-sm text-muted">Connect both devices to the same trusted network. While access is enabled, anyone on that network who knows the local address can use your vocabulary and API key. The connection is not encrypted.</p>
        {status?.active && status.qr && status.localQr && <div className="mt-5 grid gap-6 sm:grid-cols-2 sm:gap-10">
          <div className="min-w-0 text-center">
            <p className="mb-2 text-sm font-semibold">Access link</p>
            <img src={status.qr} alt="QR code for device access" className="mx-auto size-44 rounded-xl bg-white p-2" />
            <p className="mt-2 break-all font-mono text-xs text-muted">{status.url}</p>
          </div>
          <div className="min-w-0 text-center">
            <p className="mb-2 text-sm font-semibold">Local IP and port</p>
            <img src={status.localQr} alt="QR code for local address" className="mx-auto size-44 rounded-xl bg-white p-2" />
            <p className="mt-2 break-all font-mono text-xs text-muted">{status.localUrl}</p>
          </div>
        </div>}
        <div className="mt-4"><Button disabled={busy} onClick={() => void request(status?.active ? '/revoke' : '/start', 'POST')}>
          {status?.active ? 'Revoke access' : 'Enable access'}
        </Button></div>
        <div className="mt-6">
          <p id="keep-awake-label" className="text-sm font-medium">Keep this Mac awake</p>
          <div role="group" aria-labelledby="keep-awake-label" className="mt-2 flex flex-wrap gap-2">
            {([{ minutes: 0, label: 'Off' }, { minutes: 30, label: '30 minutes' }, { minutes: 60, label: '1 hour' },
              { minutes: 120, label: '2 hours' }, { minutes: 180, label: '3 hours' }] as const).map(({ minutes, label }) => (
              <Button key={minutes} size="sm" variant={status?.awakeMinutes === minutes ? 'primary' : 'secondary'}
                aria-pressed={status?.awakeMinutes === minutes} disabled={busy || !status}
                onClick={() => void request(`/awake/${minutes}`, 'POST')}>{label}</Button>
            ))}
          </div>
        </div>
        {error && <p role="alert" className="mt-3 text-sm text-bad">{error}</p>}
        <div className="mt-6 flex justify-end"><Button variant="secondary" onClick={() => setOpen(false)}>Close</Button></div>
      </div>}
    </dialog>, document.body)}
  </>
}
