import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { AnimatePresence, motion } from 'motion/react'
import { ArrowRight, ArrowUpRight, BookPlus, LoaderCircle, Newspaper, RotateCcw } from 'lucide-react'
import { api, isAbort, messageOf } from '../api'
import { useMeta } from '../context/MetaContext'
import { hasModifier, isInteractive, useKeydown } from '../hooks/useKeydown'
import { usePersistentState } from '../hooks/usePersistentState'
import { cx } from '../lib/cx'
import { plural } from '../lib/format'
import type { Article, LanguageCode, Level } from '../types'
import { Button } from '../components/Button'
import { Notice } from '../components/Notice'

type StoredArticles = Partial<Record<LanguageCode, Article>>

const MAX_WORDS = 80

function coreOf(token: string): string {
  return token.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, '')
}

function isLevelWord(token: string, words: string[]): boolean {
  const core = coreOf(token)
  if (!core) return false
  return words.some((word) => word.toLowerCase() === core.toLowerCase())
}

function HighlightedSummary({ article }: { article: Article }) {
  return (
    <p className="serif-text text-[1.3rem] leading-[1.65] tracking-tight sm:text-[1.45rem]">
      {article.summary.split(/(\s+)/).map((token, index) =>
        /^\s+$/.test(token) ? (
          token
        ) : isLevelWord(token, article.words) ? (
          <mark
            key={index}
            title={`${article.words.find((word) => word.toLowerCase() === coreOf(token).toLowerCase())} · ${article.topic} vocabulary at this level`}
            className="rounded-[5px] bg-accent-soft px-0.5 font-medium text-accent"
          >
            {token}
          </mark>
        ) : (
          <span key={index}>{token}</span>
        ),
      )}
    </p>
  )
}

function ArticleCard({ article, busy, onRetry, onWordsToAdd }: { article: Article; busy: boolean; onRetry: () => void; onWordsToAdd: () => void }) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="rounded-3xl border border-line bg-surface p-6 shadow-sm sm:p-8"
    >
      <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs font-semibold uppercase tracking-[0.09em] text-muted">
        <span className="text-accent">{article.topic}</span>
        <span aria-hidden>·</span>
        {article.url ? (
          <a
            href={article.url}
            target="_blank"
            rel="noreferrer"
            title={article.url}
            className="inline-flex items-center gap-0.5 underline decoration-line underline-offset-2 transition hover:text-ink"
          >
            {article.publication}
            <ArrowUpRight aria-hidden className="size-3" />
          </a>
        ) : (
          <span>{article.publication}</span>
        )}
      </p>
      <h2 className="serif-text mt-3 text-3xl leading-tight tracking-tight">{article.title}</h2>
      <div className="mt-5">
        <HighlightedSummary article={article} />
      </div>
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-5">
        <p className="text-sm text-muted">
          {plural(article.summary.split(/\s+/).length, 'word', 'words')} · at most {MAX_WORDS} ·{' '}
          {plural(article.words.length, 'highlighted', 'highlighted')}
        </p>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" icon={busy ? LoaderCircle : RotateCcw} spinning={busy} disabled={busy} onClick={onRetry}>
            New article
          </Button>
          {article.words.length > 0 && (
            <Button variant="secondary" icon={BookPlus} onClick={onWordsToAdd} title="Put the highlighted words into the Add tab">
              Words to Add
            </Button>
          )}
        </div>
      </div>
    </motion.article>
  )
}

export function ReadPage() {
  const { meta, language } = useMeta()
  const navigate = useNavigate()
  const topics = meta.topics
  const [topic, setTopic] = usePersistentState<string | null>('read.topic', null)
  const [level, setLevel] = usePersistentState<Level>('read.level', meta.defaults.level)
  const [articles, setArticles] = usePersistentState<StoredArticles>('read.articles', {})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const controller = useRef<AbortController | null>(null)

  const chosenTopic = topic && topics.includes(topic) ? topic : topics[0]
  const article = articles[language.code] ?? null

  useEffect(() => () => controller.current?.abort(), [])

  const retrieve = () => {
    if (!chosenTopic || loading) return
    controller.current?.abort()
    const current = new AbortController()
    controller.current = current
    setLoading(true)
    setError(null)
    api
      .read(language.code, chosenTopic, level, current.signal)
      .then((result) => setArticles((currentArticles) => ({ ...currentArticles, [language.code]: result })))
      .catch((reason: unknown) => {
        if (!isAbort(reason)) setError(messageOf(reason))
      })
      .finally(() => {
        if (controller.current === current) {
          controller.current = null
          setLoading(false)
        }
      })
  }

  useKeydown((event) => {
    if (event.key === 'Enter' && !hasModifier(event) && !isInteractive(event.target)) {
      event.preventDefault()
      retrieve()
    }
  })

  const wordsToAdd = () => {
    if (!article?.words.length) return
    navigate('/add', { state: { prefill: article.words.join('\n') } })
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-8">
        <p className="flex items-center gap-2 text-sm font-medium text-accent">
          <Newspaper aria-hidden className="size-4" />
          {language.name} · Current reading
        </p>
        <h1 className="serif-text mt-2 text-4xl tracking-tight sm:text-5xl">Read</h1>
        <p className="mt-3 max-w-xl text-[17px] leading-relaxed text-muted">
          The model finds a current article in {language.name} on a topic of your choice and summarizes it in at most{' '}
          {MAX_WORDS} words, written at the level you choose; the words of that level are highlighted. The summary
          stays here, so you can send its words to Add and practise them with the exercises.
          {meta.demo ? ' Demo mode: the article is a placeholder.' : ''}
        </p>
      </div>

      <div className="rounded-3xl border border-line bg-surface p-5 shadow-sm sm:p-7">
        <div className="divide-y divide-line">
          <div className="grid gap-2.5 py-5 first:pt-0 sm:grid-cols-[9rem_1fr] sm:gap-6">
            <span className="pt-2 text-sm font-medium text-muted">Topic</span>
            <div className="flex flex-wrap gap-1.5" role="group" aria-label="Article topic">
              {topics.map((option) => (
                <button
                  key={option}
                  type="button"
                  aria-pressed={option === chosenTopic}
                  onClick={() => setTopic(option)}
                  className={cx(
                    'cursor-pointer rounded-xl border px-3 py-2 text-left text-sm font-medium capitalize transition',
                    option === chosenTopic
                      ? 'border-accent bg-accent-soft text-ink shadow-sm'
                      : 'border-line bg-surface text-muted hover:border-accent/50 hover:text-ink',
                  )}
                >
                  {option}
                </button>
              ))}
            </div>
          </div>
          <div className="grid gap-2.5 py-5 sm:grid-cols-[9rem_1fr] sm:gap-6">
            <span className="pt-2 text-sm font-medium text-muted">Level</span>
            <div>
              <div className="flex flex-wrap gap-1.5" role="group" aria-label="CEFR level">
                {meta.levels.map((option) => (
                  <button
                    key={option}
                    type="button"
                    aria-pressed={option === level}
                    onClick={() => setLevel(option)}
                    className={cx(
                      'cursor-pointer rounded-xl border px-3 py-2 text-left text-sm transition',
                      option === level
                        ? 'border-accent bg-accent-soft text-ink shadow-sm'
                        : 'border-line bg-surface text-muted hover:border-accent/50 hover:text-ink',
                    )}
                  >
                    <span className="font-semibold tabular-nums">{option}</span>
                  </button>
                ))}
              </div>
              <p className="mt-2 text-xs leading-relaxed text-muted">
                The level is chosen before retrieving, and the summary and its highlighted words are written at it.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-2 flex flex-col gap-4 border-t border-line pt-5 sm:flex-row sm:items-center">
          <p className="min-w-0 flex-1 text-sm leading-relaxed text-muted">
            A current {chosenTopic} article in {language.name}, summarized at {level}
            {article ? ` · reading one from ${article.topic}` : ''}
          </p>
          <Button size="md" iconRight={ArrowRight} shortcut="↵" onClick={retrieve} disabled={loading || !chosenTopic} aria-label={`Retrieve a ${chosenTopic} article at ${level}`}>
            {loading ? 'Retrieving…' : 'Retrieve'}
          </Button>
        </div>
      </div>

      <AnimatePresence>
        {loading && !article && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            role="status"
            className="mt-6 flex items-center justify-center gap-2 text-sm text-muted"
          >
            <LoaderCircle aria-label="Retrieving" className="size-4 animate-spin" />
            Looking for an article…
          </motion.div>
        )}
      </AnimatePresence>

      {error && (
        <div className="mt-6">
          <Notice
            tone="error"
            action={
              <Button size="sm" variant="secondary" icon={RotateCcw} onClick={retrieve}>
                Try again
              </Button>
            }
          >
            {error}
          </Notice>
        </div>
      )}

      {article && (
        <div className="mt-6">
          <ArticleCard article={article} busy={loading} onRetry={retrieve} onWordsToAdd={wordsToAdd} />
        </div>
      )}

      {loading && article && (
        <p className="mt-3 flex items-center justify-center gap-2 text-sm text-muted" role="status">
          <LoaderCircle aria-label="Retrieving" className="size-4 animate-spin" />
          Looking for another article…
        </p>
      )}

      {!article && !loading && !error && (
        <p className="mt-8 flex items-center justify-center gap-2 text-sm text-muted">
          <Newspaper aria-hidden className="size-4" />
          No article yet: choose a topic and a level, then press Retrieve.
        </p>
      )}
    </div>
  )
}
