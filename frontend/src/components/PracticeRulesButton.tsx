import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { BookOpenCheck } from 'lucide-react'
import { Button } from './Button'

export function PracticeRulesButton({ onSelect }: { onSelect: () => void }) {
  const [open, setOpen] = useState(false)
  const dialog = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  useEffect(() => {
    if (open && !dialog.current?.open) dialog.current?.showModal()
    else if (!open && dialog.current?.open) dialog.current.close()
  }, [open])
  const close = () => setOpen(false)
  return <>
    <button type="button" role="menuitem" tabIndex={-1} onClick={() => { onSelect(); setOpen(true) }} className="flex w-full cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-ink hover:bg-surface-2 focus:bg-surface-2 focus:outline-none">
      <BookOpenCheck aria-hidden className="size-4 text-accent" />Earning credits
    </button>
    {createPortal(<dialog ref={dialog} aria-labelledby={titleId} onCancel={(event) => { event.preventDefault(); close() }} onClick={(event) => { if (event.target === dialog.current) close() }} onKeyDown={(event) => event.stopPropagation()} className="m-auto max-h-[90vh] w-[min(92vw,40rem)] overflow-auto rounded-2xl border border-line bg-surface p-0 text-ink shadow-2xl backdrop:bg-black/45">
      {open && <div className="p-6 sm:p-7">
        <h2 id={titleId} className="text-lg font-semibold">Earning credits</h2>
        <p className="mt-2 text-sm text-muted">The app chooses words automatically and keeps track of your practice for each language.</p>
        <div className="mt-5 space-y-5 text-sm leading-relaxed text-ink/85">
          <section><h3 className="font-semibold text-ink">Choosing words</h3>
            <p className="mt-1">Your language and category determine the eligible words. All is the default; General, Legal and Financial are also available. New words, words due for review and words you have found difficult are more likely to appear. Words seen or answered in the last ten minutes are less likely, but can still appear.</p>
            <p className="mt-2">Words are chosen without repeating within a selection where possible. If an exercise needs more words than are available, words may repeat. A generated question is only counted as seen when it is displayed; an unanswered question is not a successful review.</p>
          </section>
          <section><h3 className="font-semibold text-ink">Review timing</h3>
            <p className="mt-1">After successive correct answers without hints, a word becomes due after roughly 1, 2, 4, 8, 16 and 32 days, then at most 60 days. A wrong or partially correct answer makes it due after 6 hours; a correct answer with a hint makes it due after 18 hours. These are priorities, not fixed appointments: words can appear before or after they are due.</p>
            <p className="mt-2">Recognise and Produce have separate records. Translate recognition and production share those respective records; Connect, Agree and Use each have their own. Skipped questions do not count as answers. In Use, each word is assessed separately.</p>
          </section>
          <section><h3 className="font-semibold text-ink">Earning and spending credits</h3>
            <p className="mt-1">English, German and French each start with 10 credits. Every five correct word answers without hints in exercises earn one more credit for that language. The answers need not be consecutive: mistakes do not reset your progress. The same word can count more than once. In Review, grading a card Good or Easy counts as a successful review; Hard and Again do not.</p>
            <p className="mt-2">Saving a word spends one credit in its language. Unused credits carry over. When credit reaches zero, you can still translate, look up and queue words; save them after earning more. If more words are queued than your balance permits, the remaining entries stay in the queue. Home and Add show the balance and warn at three or fewer.</p>
          </section>
          <section><h3 className="font-semibold text-ink">English phrasal verbs</h3>
            <p className="mt-1">Phrasal verbs do not spend or earn word credits. All includes them in English exercises; Translate excludes them by default. When English is selected, the Phrasal verbs button beside I feel lucky starts 12 C1 Recognise or Produce questions using that category. Their practice still influences which phrasal verbs are selected.</p>
          </section>
          <section><h3 className="font-semibold text-ink">Your history</h3>
            <p className="mt-1">The app keeps track of words shown, answer counts, mistakes, exercise type and review timing on the main machine. Hints affect the next review. Older practice history remains available, but the newer answer and hint records begin when this feature was introduced.</p>
          </section>
        </div>
        <div className="mt-6 flex justify-end"><Button variant="secondary" onClick={close}>Close</Button></div>
      </div>}
    </dialog>, document.body)}
  </>
}
