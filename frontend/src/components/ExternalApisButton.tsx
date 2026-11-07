import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Network } from 'lucide-react'
import { Button } from './Button'

const SERVICES = [
  { name: 'OpenAI', url: 'https://platform.openai.com/', description: 'Generates and checks exercises, explains words, analyses articles and suggests books. Uses your OpenAI API key.' },
  { name: 'ElevenLabs', url: 'https://elevenlabs.io/', description: 'Provides speech playback and microphone transcription when configured. Uses your ElevenLabs API key; speech playback can fall back to your browser.' },
  { name: 'Open Library', url: 'https://openlibrary.org/', description: 'Looks up book titles, authors and ISBN editions. No AI key is needed.' },
  { name: 'ngrok', url: 'https://ngrok.com/', description: 'Optionally makes the app available across networks when you enable internet access. Uses your locally configured ngrok account.' },
]

export function ExternalApisButton({ onSelect }: { onSelect: () => void }) {
  const [open, setOpen] = useState(false)
  const dialog = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  useEffect(() => { if (open && !dialog.current?.open) dialog.current?.showModal(); else if (!open && dialog.current?.open) dialog.current.close() }, [open])
  return <>
    <button type="button" role="menuitem" tabIndex={-1} onClick={() => { onSelect(); setOpen(true) }} className="flex w-full cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-ink hover:bg-surface-2 focus:bg-surface-2 focus:outline-none"><Network aria-hidden className="size-4 text-accent" />External APIs</button>
    {createPortal(<dialog ref={dialog} aria-labelledby={titleId} onCancel={(event) => { event.preventDefault(); setOpen(false) }} onClick={(event) => { if (event.target === dialog.current) setOpen(false) }} onKeyDown={(event) => event.stopPropagation()} className="m-auto max-h-[90vh] w-[min(92vw,38rem)] overflow-auto rounded-2xl border border-line bg-surface p-0 text-ink shadow-2xl backdrop:bg-black/45">
      {open && <div className="p-6 sm:p-7"><h2 id={titleId} className="text-lg font-semibold">External APIs and services</h2><p className="mt-2 text-sm text-muted">Services Languages contacts when you use the corresponding features.</p>
        <div className="mt-5 space-y-4">{SERVICES.map((service) => <section key={service.name}><h3 className="font-semibold"><a href={service.url} target="_blank" rel="noopener noreferrer" className="underline decoration-line underline-offset-4 hover:decoration-current">{service.name}</a></h3><p className="mt-1 text-sm leading-relaxed text-muted">{service.description}</p></section>)}</div>
        <p className="mt-5 text-sm text-muted">Read also contacts the selected news publishers to retrieve articles. The full list is available under Allowed sources.</p><div className="mt-6 flex justify-end"><Button variant="secondary" onClick={() => setOpen(false)}>Close</Button></div>
      </div>}
    </dialog>, document.body)}
  </>
}
