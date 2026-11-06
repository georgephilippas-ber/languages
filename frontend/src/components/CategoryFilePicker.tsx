import type { ReactNode } from 'react'
import { cx } from '../lib/cx'
import { categoriesFor, categoryLabels, filesLabel, selectedFiles, selectionCategory, selectionScope, termCount } from '../lib/files'
import { plural } from '../lib/format'
import type { FileSelection, LanguageInfo } from '../types'

function Chip({ selected, onClick, children, label }: { selected: boolean; onClick: () => void; children: ReactNode; label?: string }) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      aria-label={label}
      onClick={onClick}
      className={cx(
        'cursor-pointer rounded-xl border px-3 py-2 text-left text-sm transition',
        selected
          ? 'border-accent bg-accent-soft text-ink shadow-sm'
          : 'border-line bg-surface text-muted hover:border-accent/50 hover:text-ink',
      )}
    >
      {children}
    </button>
  )
}

export function CategoryFilePicker({ language, selection, onSelect }: { language: LanguageInfo; selection: FileSelection; onSelect: (selection: FileSelection) => void }) {
  const category = selectionCategory(selection)
  const scope = selectionScope(selection)
  const summary = (value: FileSelection) => {
    const chosen = selectedFiles(language, value)
    const count = chosen.reduce((total, file) => total + file.terms, 0)
    const numbers = chosen.map((file) => typeof file.number === 'number' ? file.number : file.number.split(':')[1]).join(', ')
    const fileLabel = chosen.length === 1 ? 'File' : 'Files'
    return `${plural(count, 'term', 'terms')}${numbers ? ` · ${fileLabel} ${numbers}` : ' · No files yet'}`
  }
  return (
    <div className="space-y-4">
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">Category</p>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Vocabulary category">
          {categoriesFor(language.code).map((option) => (
            <Chip key={option} selected={category === option} onClick={() => onSelect(option)}>
              <span className="block font-medium text-ink">{categoryLabels[option]}</span>
              <span className="text-xs">{plural(termCount(language, option), 'term', 'terms')}</span>
            </Chip>
          ))}
          <Chip selected={category === 'all'} onClick={() => onSelect('all')}>
            <span className="block font-medium text-ink">All categories</span>
            <span className="text-xs">{plural(termCount(language, 'all'), 'term', 'terms')}</span>
          </Chip>
        </div>
      </div>
      {category !== 'all' && (
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">Files in {categoryLabels[category]}</p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3" role="group" aria-label={`Files in ${categoryLabels[category]}`}>
            {([['current', 'Last file'], ['latest', 'Last two files'], ['entire', 'Entire category']] as const).map(([choice, label]) => {
              const value: FileSelection = choice === 'entire' ? category : `${category}:${choice}`
              return <Chip key={choice} selected={scope === choice} onClick={() => onSelect(value)}>
                <span className="block font-medium text-ink">{label}</span>
                <span className="block text-xs">{choice === 'entire' ? plural(termCount(language, category), 'term', 'terms') : summary(value)}</span>
              </Chip>
            })}
          </div>
          {scope === 'single' && <p className="mt-2 text-xs text-muted">Previously selected: {filesLabel(language, selection)}</p>}
        </div>
      )}
    </div>
  )
}

