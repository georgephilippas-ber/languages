import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Newspaper } from 'lucide-react'
import { api, messageOf } from '../api'
import type { LanguageCode } from '../types'
import { Button } from './Button'

type Sources = Record<LanguageCode, { name: string; domain: string }[]>
const NAMES: Record<LanguageCode, string> = { EN: 'English', DE: 'German', FR: 'French' }

export function ReadSourcesButton({ onSelect }: { onSelect: () => void }) {
  const [open, setOpen] = useState(false)
  const [sources, setSources] = useState<Sources | null>(null)
  const [error, setError] = useState('')
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    if (open && !dialog.current?.open) dialog.current?.showModal()
    else if (!open && dialog.current?.open) dialog.current.close()
    if (!open) return
    let live = true
    setError('')
    api.readSources().then((value) => { if (live) setSources(value) }).catch((reason: unknown) => { if (live) setError(messageOf(reason)) })
    return () => { live = false }
  }, [open])
  return <>
    <button type="button" role="menuitem" tabIndex={-1} onClick={() => { onSelect(); setOpen(true) }} className="flex w-full cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-ink hover:bg-surface-2 focus:bg-surface-2 focus:outline-none">
      <Newspaper aria-hidden className="size-4 text-accent" />Allowed sources
    </button>
    {createPortal(<dialog ref={dialog} aria-labelledby="read-sources-title" onCancel={(event) => { event.preventDefault(); setOpen(false) }} onClick={(event) => { if (event.target === dialog.current) setOpen(false) }} onKeyDown={(event) => event.stopPropagation()} className="m-auto max-h-[90vh] w-[min(92vw,48rem)] overflow-auto rounded-2xl border border-line bg-surface p-0 text-ink shadow-2xl backdrop:bg-black/45">
      {open && <div className="p-6">
        <h2 id="read-sources-title" className="text-lg font-semibold">Allowed webpage sources</h2>
        <p className="mt-2 text-sm text-muted">Choose a website for the language selected in Read. Some articles may require a subscription or block automated access.</p>
        {error && <p role="alert" className="mt-4 text-bad">{error}</p>}
        {!sources && !error && <p className="mt-4 text-sm text-muted">Loading…</p>}
        {sources && <div className="mt-5 grid gap-6 sm:grid-cols-3">{(['EN', 'DE', 'FR'] as const).map((code) => <section key={code}>
          <h3 className="font-semibold">{NAMES[code]}</h3>
          <ul className="mt-2 space-y-2 text-sm">{sources[code].map((source) => <li key={source.domain}><a href={`https://${source.domain}`} target="_blank" rel="noopener noreferrer" className="block text-inherit no-underline"><span className="block">{source.name}</span><span className="text-xs text-muted">{source.domain}</span></a></li>)}</ul>
        </section>)}</div>}
        <div className="mt-6 flex justify-end"><Button onClick={() => setOpen(false)}>Close</Button></div>
      </div>}
    </dialog>, document.body)}
  </>
}
