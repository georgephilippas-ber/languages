import { useEffect, useRef } from 'react'
import { Button } from './Button'

interface ConfirmDialogProps {
  open: boolean
  title: string
  body: string
  confirmLabel: string
  cancelLabel: string
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({ open, title, body, confirmLabel, cancelLabel, onConfirm, onCancel }: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog
      ref={dialogRef}
      onCancel={(event) => {
        event.preventDefault()
        onCancel()
      }}
      onClick={(event) => {
        if (event.target === dialogRef.current) onCancel()
      }}
      className="m-auto w-[min(92vw,26rem)] rounded-2xl border border-line bg-surface p-0 text-ink shadow-2xl backdrop:bg-black/45 backdrop:backdrop-blur-[2px]"
    >
      {open && (
        <div className="p-6">
          <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
          <p className="mt-2 text-[15px] leading-relaxed text-muted">{body}</p>
          <div className="mt-6 flex justify-end gap-2">
            <Button variant="secondary" onClick={onCancel}>
              {cancelLabel}
            </Button>
            <Button onClick={onConfirm}>
              {confirmLabel}
            </Button>
          </div>
        </div>
      )}
    </dialog>
  )
}
