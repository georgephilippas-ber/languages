import type { LanguageCode } from '../types'

const ACCENTS: Record<LanguageCode, string[]> = {
  DE: ['ä', 'ö', 'ü', 'ß'],
  FR: ['é', 'è', 'ê', 'ë', 'à', 'â', 'ç', 'î', 'ï', 'ô', 'û', 'ù', 'œ'],
  EN: [],
}

export function AccentKeys({ code, onInsert, disabled }: { code: LanguageCode; onInsert: (text: string) => void; disabled?: boolean }) {
  const keys = ACCENTS[code]
  if (!keys.length) return null

  return (
    <div className="flex flex-wrap gap-1.5" role="group" aria-label="Insert a special character (Shift for upper case)">
      {keys.map((key) => (
        <button
          key={key}
          type="button"
          disabled={disabled}
          onMouseDown={(event) => event.preventDefault()}
          onClick={(event) => onInsert(event.shiftKey && key !== 'ß' ? key.toUpperCase() : key)}
          title={key === 'ß' ? 'Insert ß' : `Insert ${key} (Shift: ${key.toUpperCase()})`}
          className="serif-text h-9 min-w-9 cursor-pointer rounded-lg border border-line bg-surface px-2 text-lg leading-none text-ink transition hover:border-accent/60 hover:bg-accent-soft disabled:opacity-40"
        >
          {key}
        </button>
      ))}
    </div>
  )
}
