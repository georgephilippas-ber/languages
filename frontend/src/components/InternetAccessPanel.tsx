import { useEffect, useState } from 'react'
import { Button } from './Button'

interface InternetStatus {
  installed: boolean
  active: boolean
  starting: boolean
  url: string | null
  pin: string | null
  pinLocked: boolean
  qr?: string
  error: string | null
}

export function InternetAccessPanel() {
  const [status, setStatus] = useState<InternetStatus | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function request(path = '', method = 'GET') {
    try {
      const response = await fetch(`/api/internet${path}`, { method })
      const body = await response.json()
      if (!response.ok) throw new Error(body.detail || 'Internet access could not be changed.')
      setStatus(body)
      setError('')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Internet access could not be changed.')
    }
  }
  useEffect(() => {
    let active = true
    const refresh = () => { if (active) void request() }
    refresh()
    const timer = window.setInterval(refresh, 2000)
    return () => { active = false; window.clearInterval(timer) }
  }, [])
  async function toggle() {
    setBusy(true)
    await request(status?.active || status?.starting ? '/stop' : '/start', 'POST')
    setBusy(false)
  }
  return <section className="min-w-0 rounded-2xl border border-line p-4" aria-labelledby="internet-title">
    <h3 id="internet-title" className="text-sm font-semibold">Internet via ngrok</h3>
    <p className="mt-1 text-sm text-muted">Connect from another network. Enter the four-digit PIN shown here on the other device. Stopping access invalidates it.</p>
    {!status?.installed && status && <p className="mt-2 text-sm text-bad">Install ngrok and configure its authtoken on this Mac first.</p>}
    {status?.starting && <p className="mt-3 text-sm text-muted">Connecting to ngrok…</p>}
    {status?.active && status.qr && <div className="mt-4">
      <img src={status.qr} alt="QR code for internet access" className="mx-auto size-44 rounded-xl bg-white p-2" />
      <p className="mt-2 break-all text-center font-mono text-xs text-muted">{status.url}</p>
      <p className="mt-3 text-sm">PIN: <strong className="font-mono tracking-widest">{status.pin}</strong></p>
    </div>}
    {status?.pinLocked && <p role="alert" className="mt-3 text-sm text-bad">PIN locked after too many attempts. Stop and re-enable internet access to generate a new PIN.</p>}
    {(error || status?.error) && <p role="alert" className="mt-3 text-sm text-bad">{error || status?.error}</p>}
    <div className="mt-3"><Button disabled={busy || !status || (!status.installed && !status.active)} variant="secondary" onClick={() => void toggle()}>
      {status?.active || status?.starting ? 'Stop internet access' : 'Enable internet access'}
    </Button></div>
  </section>
}
