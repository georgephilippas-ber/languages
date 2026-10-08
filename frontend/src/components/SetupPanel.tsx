import type { ReactNode } from 'react'
import { motion } from 'motion/react'
import { ArrowRight, Layers, Minus, Play, Plus, Trash2 } from 'lucide-react'
import { useMeta } from '../context/MetaContext'
import type { ExerciseInfo } from '../exercises/types'
import { hasModifier, isInteractive, useKeydown } from '../hooks/useKeydown'
import { cx } from '../lib/cx'
import { filesLabel, termCount, validSelection } from '../lib/files'
import { plural } from '../lib/format'
import type { FileSelection, Level } from '../types'
import { Button } from './Button'

export interface SetupSettings {
  level: Level
  count: number
  files: FileSelection
}

export interface ResumeInfo {
  index: number
  total: number
  source: string
  languageName: string
}

interface SetupPanelProps {
  definition: ExerciseInfo
  settings: SetupSettings
  onChange: (settings: SetupSettings) => void
  onStart: () => void
  onRevise: () => void
  resume: ResumeInfo | null
  onResume: () => void
  onDiscard: () => void
}

export function ExerciseHeading({ definition }: { definition: ExerciseInfo }) {
  const Icon = definition.icon
  return (
    <div className="mb-8">
      <p className="flex items-center gap-2 text-sm font-medium text-accent">
        <Icon aria-hidden className="size-4" />
        Step {definition.step} · {definition.name}
      </p>
      <h1 className="serif-text mt-2 text-4xl tracking-tight sm:text-5xl">{definition.verb}</h1>
      <p className="mt-3 max-w-xl text-[17px] leading-relaxed text-muted">{definition.description}</p>
    </div>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid gap-2.5 py-5 first:pt-0 sm:grid-cols-[9rem_1fr] sm:gap-6">
      <span className="pt-2 text-sm font-medium text-muted">{label}</span>
      <div>{children}</div>
    </div>
  )
}

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

export function SetupPanel({ definition, settings, onChange, onStart, onRevise, resume, onResume, onDiscard }: SetupPanelProps) {
  const { meta, language } = useMeta()
  const files = validSelection(language, settings.files)
  const count = Math.min(Math.max(settings.count, 1), meta.defaults.maxCount)
  const unit = count === 1 ? definition.unit.one : definition.unit.other
  const minutes = Math.max(1, Math.ceil((count * meta.defaults.secondsPerQuestion) / 60))
  const totalTerms = language.files.reduce((total, file) => total + file.terms, 0)

  const update = (patch: Partial<SetupSettings>) => onChange({ ...settings, files, count, ...patch })

  useKeydown((event) => {
    if (event.key === 'Enter' && !hasModifier(event) && !isInteractive(event.target)) {
      event.preventDefault()
      onStart()
    }
  })

  if (!language.files.length) {
    return (
      <div className="mx-auto max-w-3xl">
        <ExerciseHeading definition={definition} />
        <p className="rounded-2xl border border-line bg-surface p-6 text-muted">There are no {language.name} vocabulary files yet.</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl">
      <ExerciseHeading definition={definition} />

      {resume && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 flex flex-col gap-3 rounded-2xl border border-accent/30 bg-accent-soft p-4 sm:flex-row sm:items-center sm:gap-4"
        >
          <div className="min-w-0 flex-1">
            <p className="font-medium">
              Unfinished: {definition.unit.one} {resume.index + 1} of {resume.total}
            </p>
            <p className="truncate text-sm text-muted">
              {resume.languageName} · {resume.source}
            </p>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" size="sm" icon={Trash2} onClick={onDiscard}>
              Discard
            </Button>
            <Button size="sm" icon={Play} onClick={onResume}>
              Resume
            </Button>
          </div>
        </motion.div>
      )}

      <div className="rounded-3xl border border-line bg-surface p-5 shadow-sm sm:p-7">
        <div className="divide-y divide-line">
          {definition.usesLevel && (
            <Field label="Level">
              <div className="flex flex-wrap gap-1.5" role="group" aria-label="CEFR level">
                {meta.levels.map((level) => (
                  <Chip key={level} selected={settings.level === level} onClick={() => update({ level })}>
                    <span className="font-semibold tabular-nums">{level}</span>
                  </Chip>
                ))}
              </div>
            </Field>
          )}

          <Field label={definition.unit.other[0].toUpperCase() + definition.unit.other.slice(1)}>
            <div className="flex items-center gap-2">
              <Button variant="secondary" size="md" icon={Minus} aria-label="Fewer" disabled={count <= 1} onClick={() => update({ count: count - 1 })} />
              <input
                type="number"
                inputMode="numeric"
                min={1}
                max={meta.defaults.maxCount}
                value={count}
                aria-label={`Number of ${definition.unit.other}`}
                onChange={(event) => {
                  const value = Number.parseInt(event.target.value, 10)
                  if (Number.isFinite(value)) update({ count: value })
                }}
                className="h-10 w-16 rounded-xl border border-line bg-surface text-center text-[15px] font-semibold tabular-nums outline-none focus:border-accent [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none"
              />
              <Button
                variant="secondary"
                size="md"
                icon={Plus}
                aria-label="More"
                disabled={count >= meta.defaults.maxCount}
                onClick={() => update({ count: count + 1 })}
              />
              {definition.timed && <span className="ml-2 text-sm text-muted">{meta.defaults.secondsPerQuestion} s each</span>}
            </div>
          </Field>

          <Field label="Words from">
            <div className="flex flex-wrap gap-2">
              <Chip selected={files === 'latest'} onClick={() => update({ files: 'latest' })}>
                <span className="block font-medium text-ink">Latest {language.latest.length > 1 ? language.latest.length : 'file'}</span>
                <span className="text-xs">{language.files.filter((file) => language.latest.includes(file.number)).map((file) => file.name.replace('.md', '')).join(' · ')}</span>
              </Chip>
              {language.files.length > 1 && (
                <Chip selected={files === 'current'} onClick={() => update({ files: 'current' })}>
                  <span className="block font-medium text-ink">Latest file</span>
                  <span className="text-xs">{language.files[language.files.length - 1].name.replace('.md', '')}</span>
                </Chip>
              )}
              <Chip selected={files === 'all'} onClick={() => update({ files: 'all' })}>
                <span className="block font-medium text-ink">All files</span>
                <span className="text-xs">{plural(totalTerms, 'term', 'terms')}</span>
              </Chip>
            </div>
            {language.files.length > 1 && (
              <div className="mt-3 flex flex-wrap gap-1.5" role="group" aria-label="One file">
                {language.files.map((file) => (
                  <Chip
                    key={file.number}
                    selected={files === file.number}
                    onClick={() => update({ files: file.number })}
                    label={`${file.name}, ${plural(file.terms, 'term', 'terms')}`}
                  >
                    <span className="font-semibold tabular-nums text-ink">{file.number}</span>
                    <span className="ml-1.5 text-xs tabular-nums">{file.terms}</span>
                  </Chip>
                ))}
              </div>
            )}
          </Field>
        </div>

        <div className="mt-2 flex flex-col gap-4 border-t border-line pt-5 sm:flex-row sm:items-center">
          <p className="min-w-0 flex-1 text-sm leading-relaxed text-muted">
            {plural(count, definition.unit.one, definition.unit.other)}
            {definition.usesLevel ? ` at ${settings.level}` : ''} from {filesLabel(language, files)} ({plural(termCount(language, files), 'term', 'terms')})
            {definition.timed ? ` · about ${minutes} min` : ''}
          </p>
          <div className="flex flex-wrap gap-2">
            {definition.revisable && (
              <Button variant="secondary" icon={Layers} onClick={onRevise} title={`${meta.defaults.revise} ${definition.unit.other} from all files`}>
                Revise all
              </Button>
            )}
            <Button size="md" iconRight={ArrowRight} shortcut="↵" onClick={onStart} aria-label={`Start ${count} ${unit}`}>
              Start
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
