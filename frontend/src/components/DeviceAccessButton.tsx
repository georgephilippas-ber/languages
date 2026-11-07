import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Smartphone } from 'lucide-react'
import { Button } from './Button'
import { InternetAccessPanel } from './InternetAccessPanel'

interface Status { active: boolean; url: string | null; qr?: string; localUrl: string | null; localQr?: string; awakeMinutes: number }

export function DeviceAccessButton({ onSelect }: { onSelect: () => void }) {
  const [open, setOpen] = useState(false)
  const [status, setStatus] = useState<Status | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const dialog = useRef<HTMLDialogElement>(null)
  const requestNumber = useRef(0)
  const actionPending = useRef(false)
  async function request(path: string, method = 'GET', background = false) {
    if (background && actionPending.current) return
    const action = method !== 'GET'
    const number = ++requestNumber.current
    if (action) { actionPending.current = true; setBusy(true) }
    if (!background) setError('')
    try {
      const response = await fetch(`/api/device${path}`, { method })
      const body = await response.json()
      if (!response.ok) throw new Error(body.detail || 'The request failed.')
      if (number === requestNumber.current) setStatus(body)
    } catch (reason) {
      if (!background && number === requestNumber.current) setError(reason instanceof Error ? reason.message : 'The request failed.')
    } finally {
      if (action) { actionPending.current = false; setBusy(false) }
    }
  }
  useEffect(() => {
    if (!open) { if (dialog.current?.open) dialog.current.close(); return }
    if (!dialog.current?.open) dialog.current?.showModal()
    void request('')
    const timer = window.setInterval(() => void request('', 'GET', true), 2000)
    return () => { window.clearInterval(timer); requestNumber.current += 1 }
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
        <p className="mt-2 text-sm text-muted">Choose a connection for the other device. Local sharing is available to anyone on the same network who knows the address.</p>
        <div className="mt-5 grid gap-5 sm:grid-cols-2 sm:gap-8">
          <section className="min-w-0 rounded-2xl border border-line p-4" aria-labelledby="local-title">
            <h3 id="local-title" className="text-sm font-semibold">Local network</h3>
            <p className="mt-1 text-sm text-muted">Connect devices on the same trusted network. The connection is not encrypted.</p>
            {status?.active && status.localQr && <div className="mt-4">
              <img src={status.localQr} alt="QR code for local address" className="mx-auto size-44 rounded-xl bg-white p-2" />
              <p className="mt-2 break-all text-center font-mono text-xs text-muted">{status.localUrl}</p>
            </div>}
            <div className="mt-3"><Button disabled={busy} variant="secondary" onClick={() => void request(status?.active ? '/revoke' : '/start', 'POST')}>
              {status?.active ? 'Revoke local access' : 'Enable local access'}
            </Button></div>
          </section>
          <InternetAccessPanel />
        </div>
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
