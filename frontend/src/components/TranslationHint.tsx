import { useEffect, useId, useState } from 'react'
import { Languages } from 'lucide-react'
import { useKeydown } from '../hooks/useKeydown'

export function TranslationHint({ text, label = 'English translation', hoverReveal = true, shortcut = false, onReveal }: { text: string; label?: string; hoverReveal?: boolean; shortcut?: boolean; onReveal?: () => void }) {
  const id = useId()
  const [pinned, setPinned] = useState(false)
  const [hovered, setHovered] = useState(false)
  const visible = pinned || hovered
  useEffect(() => { if (visible) onReveal?.() }, [visible, onReveal])

  useKeydown((event) => {
    if (event.ctrlKey && !event.metaKey && !event.altKey && !event.shiftKey && event.key.toLowerCase() === 'h') {
      event.preventDefault()
      if (!event.repeat) setPinned(true)
    }
  }, shortcut)

  return (
    <div
      className="mt-7 rounded-xl border border-line bg-surface"
      onPointerEnter={(event) => {
        if (hoverReveal && event.pointerType === 'mouse') setHovered(true)
      }}
      onPointerLeave={() => setHovered(false)}
      onKeyDown={(event) => {
        if (event.key === 'Escape' && visible) {
          event.preventDefault()
          event.stopPropagation()
          setPinned(false)
          setHovered(false)
        }
      }}
    >
      <button
        type="button"
        aria-expanded={visible}
        aria-controls={id}
        onClick={() => {
          setHovered(false)
          setPinned((value) => !value)
        }}
        className="flex min-h-12 w-full cursor-pointer flex-wrap items-center gap-x-3 gap-y-1 rounded-xl px-3 py-3 text-left text-sm outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        <Languages aria-hidden className="size-4 shrink-0 text-accent" />
        <span className="font-medium">{label}</span>
        <span className="text-xs text-muted">{visible ? 'Click or tap to hide' : hoverReveal ? 'Hover, click or tap to reveal' : 'Click or tap to reveal'}{shortcut && ' · Ctrl+H'}</span>
      </button>
      <p id={id} lang={label === 'English translation' ? 'en' : undefined} hidden={!visible} className="break-words border-t border-line px-3 py-3 text-[15px] leading-relaxed">
        {text}
      </p>
    </div>
  )
}
