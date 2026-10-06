import type { DiffPart } from '../lib/diff'

export function DiffText({ parts, show }: { parts: DiffPart[]; show: 'before' | 'after' }) {
  return (
    <span>
      {parts.map((part, index) => {
        if (part.kind === 'same') return <span key={index}>{part.text}</span>
        if (part.kind === 'removed' && show === 'before') {
          return (
            <del key={index} className="rounded-[4px] bg-bad-soft px-0.5 text-bad decoration-bad/70 decoration-2">
              {part.text}
            </del>
          )
        }
        if (part.kind === 'added' && show === 'after') {
          return (
            <ins key={index} className="rounded-[4px] bg-good-soft px-0.5 text-good no-underline">
              {part.text}
            </ins>
          )
        }
        return null
      })}
    </span>
  )
}
