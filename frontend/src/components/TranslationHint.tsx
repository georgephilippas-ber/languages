import { useId, useState } from 'react'
import { Languages } from 'lucide-react'

export function TranslationHint({ text }: { text: string }) {
  const id = useId()
  const [pinned, setPinned] = useState(false)
  const [hovered, setHovered] = useState(false)
  const visible = pinned || hovered

  return (
    <div
      className="mt-7 rounded-xl border border-line bg-surface"
      onPointerEnter={(event) => {
        if (event.pointerType === 'mouse') setHovered(true)
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
        <span className="font-medium">English translation</span>
        <span className="text-xs text-muted">{visible ? 'Click or tap to toggle' : 'Hover, click or tap to reveal'}</span>
      </button>
      <p id={id} hidden={!visible} className="break-words border-t border-line px-3 py-3 text-[15px] leading-relaxed">
        {text}
      </p>
    </div>
  )
}
