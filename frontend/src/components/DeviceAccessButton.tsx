import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Smartphone } from 'lucide-react'
import { Button } from './Button'

interface Status { active: boolean; url: string | null; qr?: string; awakeMinutes: number }

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
      className="m-auto w-[min(92vw,30rem)] rounded-2xl border border-line bg-surface p-0 text-ink shadow-2xl backdrop:bg-black/45">
      {open && <div className="p-6">
        <h2 id="device-title" className="text-lg font-semibold">Access from another device</h2>
        <p className="mt-2 text-sm text-muted">Connect both devices to the same trusted network. Anyone with this link can use your vocabulary and API key while access is enabled. The connection is not encrypted.</p>
        {status?.active && status.qr && <div className="mt-4">
          <img src={status.qr} alt="QR code for device access" className="mx-auto size-48 rounded-xl bg-white p-2" />
          <p className="mt-2 break-all text-center font-mono text-xs text-muted">{status.url}</p>
        </div>}
        <div className="mt-4"><Button disabled={busy} onClick={() => void request(status?.active ? '/revoke' : '/start', 'POST')}>
          {status?.active ? 'Revoke access' : 'Enable access'}
        </Button></div>
        <label className="mt-6 block text-sm font-medium">Keep this Mac awake
          <select value={status?.awakeMinutes ?? 0} disabled={busy || !status} onChange={(event) => void request(`/awake/${event.target.value}`, 'POST')}
            className="mt-2 block w-full rounded-xl border border-line bg-surface px-3 py-2 text-ink">
            <option value="0">Off</option><option value="30">30 minutes</option><option value="60">1 hour</option><option value="120">2 hours</option>
          </select>
        </label>
        {error && <p role="alert" className="mt-3 text-sm text-bad">{error}</p>}
        <div className="mt-6 flex justify-end"><Button variant="secondary" onClick={() => setOpen(false)}>Close</Button></div>
      </div>}
    </dialog>, document.body)}
  </>
}
