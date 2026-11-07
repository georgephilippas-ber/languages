import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Keyboard } from 'lucide-react'
import { Button } from './Button'
import { Kbd } from './Kbd'

const MAC = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)
const GROUPS = [
  { title: 'Language', items: [['Ctrl+E', 'Switch to English'], ['Ctrl+D', 'Switch to German'], ['Ctrl+F', 'Switch to French']] },
  { title: 'Navigation', items: [['Ctrl+A', 'Open Add'], ['Ctrl+S', 'Open Ask']] },
  { title: 'Exercises', items: [['1–4 or A–D', 'Choose an answer in Recognise'], ['Ctrl+H', 'Show the hint in Produce and Translate Produce'], ['Ctrl+L', 'Reveal a letter in Produce and Translate Produce'], ['Enter', 'Check an answer or continue'], ['Shift+Enter', 'Start a new line in Use'], ['Esc', 'End the exercise']] },
  { title: 'Review', items: [['Space or Enter', 'Show an answer or continue'], ['1–4', 'Grade a card'], ['1 / 2 or ← / →', 'Browse: again later / next'], ['Esc', 'End the session']] },
  { title: 'Add and Ask', items: [['Ctrl+Enter or ⌘+Enter', 'Write entries or send a question'], [MAC ? '⌥+⌘+T' : 'Ctrl+Alt+T', 'Translate the text in Add']] },
  { title: 'Book notes', items: [['Ctrl+L', 'Check and tidy Markdown'], ['Ctrl+S or ⌘+S', 'Save notes']] },
  { title: 'Read', items: [['Enter', 'Retrieve or analyze an article when not typing']] },
]

export function ShortcutsButton({ onSelect }: { onSelect: () => void }) {
  const [open, setOpen] = useState(false)
  const dialog = useRef<HTMLDialogElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const titleId = useId()
  useEffect(() => {
    if (open && !dialog.current?.open) dialog.current?.showModal()
    else if (!open && dialog.current?.open) dialog.current.close()
  }, [open])
  const close = () => { setOpen(false); trigger.current?.focus() }
  return <>
    <button ref={trigger} type="button" role="menuitem" tabIndex={-1} onClick={() => { onSelect(); setOpen(true) }} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-ink hover:bg-surface-2 focus:bg-surface-2 focus:outline-none">
      <Keyboard aria-hidden className="size-4 text-accent" />Keyboard shortcuts
    </button>
    {createPortal(<dialog ref={dialog} aria-labelledby={titleId} onCancel={(event) => { event.preventDefault(); close() }} onClick={(event) => { if (event.target === dialog.current) close() }} onKeyDown={(event) => event.stopPropagation()} className="m-auto max-h-[90vh] w-[min(92vw,38rem)] overflow-auto rounded-2xl border border-line bg-surface p-0 text-ink shadow-2xl backdrop:bg-black/45">
      {open && <div className="p-6"><h2 id={titleId} className="text-lg font-semibold">Keyboard shortcuts</h2>
        <p className="mt-2 text-sm text-muted">Ctrl+A and Ctrl+S also work while typing. When you are already in Add, Ctrl+A keeps its normal text-editing behaviour. Language shortcuts also work while typing. Navigation and exercise shortcuts do not interrupt menus or dialogs.</p>
        <div className="mt-5 space-y-5">{GROUPS.map((group) => <section key={group.title}><h3 className="text-xs font-semibold uppercase tracking-wide text-muted">{group.title}</h3>
          <dl className="mt-2 space-y-2">{group.items.map(([keys, description]) => <div key={keys} className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-sm"><dt>{description}</dt><dd><Kbd>{keys}</Kbd></dd></div>)}</dl>
        </section>)}</div>
        <div className="mt-6 flex justify-end"><Button variant="secondary" onClick={close}>Close</Button></div>
      </div>}
    </dialog>, document.body)}
  </>
}
