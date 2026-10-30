import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { Power } from 'lucide-react'
import { ConfirmDialog } from './ConfirmDialog'

export function ExitButton({ onSelect }: { onSelect?: () => void }) {
  const [token, setToken] = useState<string | null>(null)
  const [confirm, setConfirm] = useState(false)
  const [busy, setBusy] = useState(false)
  const [quit, setQuit] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    fetch('/api/lifecycle').then((response) => response.ok ? response.json() : null)
      .then((body) => { if (active) setToken(body?.exitToken ?? null) })
      .catch(() => {})
    return () => { active = false }
  }, [])

  const exit = async () => {
    setConfirm(false)
    setBusy(true)
    setError(null)
    try {
      const response = await fetch('/api/exit', { method: 'POST', headers: { 'X-Languages-Exit': token ?? '' } })
      if (!response.ok) {
        const body = await response.json()
        throw new Error(body.detail ?? 'Could not quit Languages. Please try again.')
      }
      setQuit(true)
      window.close()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not quit Languages.')
      setBusy(false)
    }
  }

  if (!token) return null
  return (
    <>
      <button type="button" role="menuitem" tabIndex={-1} aria-label="Exit Languages" disabled={busy}
        onClick={() => { onSelect?.(); setConfirm(true) }} className="flex w-full cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-ink hover:bg-surface-2 focus:bg-surface-2 focus:outline-none">
        <Power aria-hidden className="size-4 text-muted" /><span>Exit</span>
      </button>
      {createPortal(<>
      <ConfirmDialog open={confirm} title="Quit Languages?"
        body="This stops the app. Your saved vocabulary, drafts, and exercise progress are kept."
        confirmLabel="Quit" cancelLabel="Cancel" onConfirm={() => void exit()} onCancel={() => setConfirm(false)} />
      {error && <p role="alert" className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-xl border border-line bg-surface p-4 text-sm text-bad shadow-lg">{error}</p>}
      {quit && (
        <div role="status" className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-3 bg-bg p-8 text-center text-ink">
          <h1 className="text-2xl font-semibold">Languages has quit</h1>
          <p>Your browser kept this tab open. You can close it now.</p>
        </div>
      )}
      </>, document.body)}
    </>
  )
}
