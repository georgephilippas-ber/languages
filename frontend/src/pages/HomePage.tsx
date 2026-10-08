import { motion } from 'motion/react'
import { ArrowRight, BookPlus, GalleryVerticalEnd, Layers, MessageCircleQuestion, type LucideIcon } from 'lucide-react'
import { useNavigate } from 'react-router'
import { useMeta } from '../context/MetaContext'
import { exercisesFor } from '../exercises'
import { targetFile } from '../lib/entries'
import type { ExerciseInfo } from '../exercises/types'
import { plural } from '../lib/format'
import { readStored, sessionKey } from '../lib/storage'
import { Button } from '../components/Button'
import { Kbd } from '../components/Kbd'

interface StoredProgress {
  index: number
  items: unknown[]
  finished: boolean
}

function ExerciseCard({ exercise, delay }: { exercise: ExerciseInfo; delay: number }) {
  const { meta } = useMeta()
  const navigate = useNavigate()
  const Icon = exercise.icon
  const stored = readStored<StoredProgress>(sessionKey(exercise.kind))
  const inProgress = stored && !stored.finished && Array.isArray(stored.items) ? stored : null
  const count = exercise.defaultCount(meta)

  return (
    <motion.article
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay, ease: 'easeOut' }}
      className="group relative flex flex-col rounded-3xl border border-line bg-surface p-6 shadow-sm transition-shadow hover:shadow-lg hover:shadow-black/5"
    >
      <div className="flex items-center justify-between">
        <span className="flex size-11 items-center justify-center rounded-2xl bg-accent-soft text-accent transition group-hover:scale-105">
          <Icon aria-hidden className="size-5" />
        </span>
        <span className="text-xs font-semibold tabular-nums tracking-widest text-muted/70">0{exercise.step}</span>
      </div>
      <h2 className="serif-text mt-6 text-3xl tracking-tight">{exercise.verb}</h2>
      <p className="text-sm font-medium text-muted">{exercise.name}</p>
      <p className="mt-3 flex-1 text-[15px] leading-relaxed text-ink/80">{exercise.description}</p>
      <p className="mt-5 text-xs font-medium text-muted">
        {plural(count, exercise.unit.one, exercise.unit.other)}
        {exercise.timed ? ` · ${meta.defaults.secondsPerQuestion} s each` : ' · untimed'}
      </p>
      {inProgress && (
        <p className="mt-2 text-xs font-semibold text-accent">
          In progress · {exercise.unit.one} {inProgress.index + 1} of {inProgress.items.length}
        </p>
      )}
      <div className="mt-5 flex flex-wrap gap-2">
        <Button iconRight={ArrowRight} onClick={() => navigate(exercise.path)}>
          {inProgress ? 'Continue' : 'Start'}
        </Button>
        {exercise.revisable && (
          <Button
            variant="secondary"
            icon={Layers}
            title={`${meta.defaults.revise} ${exercise.unit.other} from all files`}
            onClick={() => navigate(exercise.path, { state: { start: 'revise' } })}
          >
            Revise
          </Button>
        )}
      </div>
    </motion.article>
  )
}

const toolTones = {
  good: {
    card: 'border-good/30 bg-good-soft hover:border-good/60',
    icon: 'bg-surface text-good',
    arrow: 'group-hover:text-good',
  },
  warn: {
    card: 'border-warn/30 bg-warn-soft hover:border-warn/60',
    icon: 'bg-surface text-warn',
    arrow: 'group-hover:text-warn',
  },
  info: {
    card: 'border-info/30 bg-info-soft hover:border-info/60',
    icon: 'bg-surface text-info',
    arrow: 'group-hover:text-info',
  },
}

function ToolCard({ icon: Icon, verb, text, detail, path, tone, delay }: { icon: LucideIcon; verb: string; text: string; detail: string; path: string; tone: keyof typeof toolTones; delay: number }) {
  const classes = toolTones[tone]
  const navigate = useNavigate()
  return (
    <motion.button
      type="button"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay, ease: 'easeOut' }}
      onClick={() => navigate(path)}
      className={`group flex cursor-pointer items-center gap-4 rounded-3xl border p-5 text-left shadow-sm transition hover:shadow-lg hover:shadow-black/5 ${classes.card}`}
    >
      <span className={`flex size-11 shrink-0 items-center justify-center rounded-2xl transition group-hover:scale-105 ${classes.icon}`}>
        <Icon aria-hidden className="size-5" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="serif-text block text-2xl tracking-tight">{verb}</span>
        <span className="block text-sm leading-relaxed text-muted">{text}</span>
        <span className="mt-1 block text-xs font-medium text-muted">{detail}</span>
      </span>
      <ArrowRight aria-hidden className={`size-4 shrink-0 text-muted transition group-hover:translate-x-0.5 ${classes.arrow}`} />
    </motion.button>
  )
}

export function HomePage() {
  const { meta, language } = useMeta()
  const target = targetFile(language, meta.defaults.maxTermsPerFile)
  const total = language.files.reduce((sum, file) => sum + file.terms, 0)
  const newest = language.files[language.files.length - 1]
  const exercises = exercisesFor(language.code)

  return (
    <div>
      <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="pb-10 pt-4 sm:pb-14 sm:pt-10">
        <p className="text-sm font-medium text-accent">
          {language.name} · {plural(total, 'term', 'terms')} in {plural(language.files.length, 'file', 'files')}
          {newest ? ` · newest: ${newest.name} (${newest.terms})` : ''}
        </p>
        <h1 className="serif-text mt-4 max-w-3xl text-[2.6rem] leading-[1.08] tracking-tight text-balance sm:text-6xl">
          See it. Learn it. <span className="text-accent">Use it.</span>
        </h1>
        <p className="mt-5 max-w-xl text-lg leading-relaxed text-muted">
          Exercises built from your own vocabulary, from spotting the right word to writing sentences of your own.
        </p>
      </motion.section>

      <div className={exercises.length === 4 ? 'grid gap-4 md:grid-cols-2' : 'grid gap-4 md:grid-cols-3'}>
        {exercises.map((exercise, index) => (
          <ExerciseCard key={exercise.kind} exercise={exercise} delay={0.08 + index * 0.07} />
        ))}
      </div>

      <div className="mt-12 flex items-center gap-4" role="separator" aria-label="Your library">
        <span className="h-px flex-1 bg-line" />
        <span className="text-xs font-semibold uppercase tracking-widest text-muted">Your library</span>
        <span className="h-px flex-1 bg-line" />
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <ToolCard
          icon={GalleryVerticalEnd}
          verb="Review"
          text="Flashcards from your files, with spaced repetition."
          detail={`${plural(total, 'card', 'cards')} in ${language.name}`}
          path="/review"
          tone="good"
          delay={0.3}
        />
        <ToolCard
          icon={BookPlus}
          verb="Add"
          text="Write full entries for new words and file them."
          detail={target.isNew ? `Next: ${target.name}` : `${target.name} · ${target.terms} of ${meta.defaults.maxTermsPerFile}`}
          path="/add"
          tone="warn"
          delay={0.36}
        />
      </div>

      <div className="mt-4 grid">
        <ToolCard
          icon={MessageCircleQuestion}
          verb="Ask"
          text="Ask anything about language: grammar, usage, meaning, pronunciation, translation."
          detail={`Answers in English, about ${language.name} unless you name another language`}
          path="/ask"
          tone="info"
          delay={0.42}
        />
      </div>

      <p className="mt-12 hidden flex-wrap items-center justify-center gap-x-5 gap-y-2 text-xs text-muted sm:flex pointer-coarse:hidden">
        <span className="flex items-center gap-1.5">
          <Kbd>↵</Kbd> start, check, next
        </span>
        <span className="flex items-center gap-1.5">
          <Kbd>1–4</Kbd> answer multiple choice
        </span>
        <span className="flex items-center gap-1.5">
          <Kbd>Esc</Kbd> end an exercise
        </span>
      </p>
    </div>
  )
}
