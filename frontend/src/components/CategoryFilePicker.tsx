import { cx } from '../lib/cx'
import { categoryLabels, exerciseSelection, termCount } from '../lib/files'
import { plural } from '../lib/format'
import type { Category, FileSelection, LanguageInfo } from '../types'

export function CategoryFilePicker({ language, selection, onSelect }: { language: LanguageInfo; selection: FileSelection; onSelect: (selection: FileSelection) => void }) {
  const selected = exerciseSelection(selection)
  const choices: (Category | 'all')[] = ['all', 'general', 'legal', 'financial']
  return <div className="flex flex-wrap gap-2" role="group" aria-label="Vocabulary category">
    {choices.map((option) => <button key={option} type="button" aria-pressed={selected === option}
      onClick={() => onSelect(option)} className={cx('cursor-pointer rounded-xl border px-3 py-2 text-left text-sm transition',
        selected === option ? 'border-accent bg-accent-soft text-ink shadow-sm' : 'border-line bg-surface text-muted hover:border-accent/50 hover:text-ink')}>
      <span className="block font-medium text-ink">{option === 'all' ? 'All' : categoryLabels[option]}</span>
      <span className="text-xs">{plural(termCount(language, option), 'term', 'terms')}</span>
    </button>)}
  </div>
}
