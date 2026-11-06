import { useEffect, useId, useRef } from 'react'
import { createPortal } from 'react-dom'
import { LUCKY_LABELS, type LuckySnapshot } from '../lib/luckySession'
import { Button } from './Button'

export function LuckyChoiceDialog({ choice, canStartNew, onResume, onStartNew, onCancel }: {
  choice: LuckySnapshot | null; canStartNew: boolean; onResume: () => void; onStartNew: () => void; onCancel: () => void
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  useEffect(() => {
    if (choice && !dialog.current?.open) dialog.current?.showModal()
    else if (!choice && dialog.current?.open) dialog.current.close()
  }, [choice])
  const language = choice ? ({ EN: 'English', DE: 'German', FR: 'French' } as const)[choice.session.request.language] : ''
  const mixed = choice?.kind.startsWith('mixed-')
  return createPortal(<dialog ref={dialog} aria-labelledby={titleId} onCancel={(event) => { event.preventDefault(); onCancel() }} onClick={(event) => { if (event.target === dialog.current) onCancel() }} onKeyDown={(event) => event.stopPropagation()} className="m-auto w-[min(92vw,30rem)] rounded-2xl border border-line bg-surface p-0 text-ink shadow-2xl backdrop:bg-black/45">
    {choice && <div className="p-6"><h2 id={titleId} className="text-lg font-semibold">Continue Lucky?</h2>
      <p className="mt-2 text-sm leading-relaxed text-muted">You have an unfinished {LUCKY_LABELS[choice.kind]} exercise · {mixed ? 'mixed languages' : language} · question {choice.session.index + 1} of {choice.session.items.length}.</p>
      <p className="mt-2 text-sm leading-relaxed text-muted">You can continue where you left off, or start a new Lucky exercise.</p>
      <div className="mt-6 flex flex-wrap justify-end gap-2"><Button variant="ghost" onClick={onCancel}>Cancel</Button><Button variant="secondary" disabled={!canStartNew} onClick={onStartNew}>Start new</Button><Button onClick={onResume}>Resume</Button></div>
    </div>}
  </dialog>, document.body)
}
