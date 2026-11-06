import { useEffect, useRef, useState, type MouseEvent as ReactMouseEvent } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router'
import { createPortal } from 'react-dom'
import { AnimatePresence, motion } from 'motion/react'
import { ArrowRight, ArrowUpRight, BookPlus, LoaderCircle, Newspaper, RotateCcw } from 'lucide-react'
import { api, isAbort, messageOf } from '../api'
import { useMeta } from '../context/MetaContext'
import { hasModifier, isInteractive, useKeydown } from '../hooks/useKeydown'
import { usePersistentState } from '../hooks/usePersistentState'
import { cx } from '../lib/cx'
import { plural } from '../lib/format'
import { categoriesFor, categoryLabels } from '../lib/files'
import type { Article, Category, LanguageCode, Level } from '../types'
import { Button } from '../components/Button'
import { Notice } from '../components/Notice'
import { SpeakButton } from '../components/SpeakButton'
import { speak, speechAvailable, stopSpeaking } from '../lib/speech'
import { readStored, writeStored } from '../lib/storage'
import { newId, type Draft } from '../lib/drafts'

type StoredArticles = Partial<Record<LanguageCode, Article>>

type ReadMode = 'find' | 'url' | 'text'

function coreOf(token: string): string {
  return token.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, '')
}

function isLevelWord(token: string, words: string[]): boolean {
  const core = coreOf(token)
  if (!core) return false
  return words.some((word) => word.toLowerCase() === core.toLowerCase())
}

function wordKey(word: string): string {
  return coreOf(word).normalize('NFC').toLocaleLowerCase()
}

type WordHandler = (event: ReactMouseEvent<HTMLElement>, word: string, offset: number, section: 'title' | 'summary') => void

function WordTokens({ text, article, queued, section, onWordContext, highlightLevel = true }: { text: string; article: Article; queued: Set<string>; section: 'title' | 'summary'; onWordContext: WordHandler; highlightLevel?: boolean }) {
  const added = new Set((article.addedWords ?? []).map(wordKey))
  const tokens = text.split(/(\s+)/)
  return <>{tokens.map((token, index) => {
    if (/^\s+$/.test(token)) return token
    const word = coreOf(token)
    const isAdded = !!word && added.has(wordKey(word))
    const levelWord = highlightLevel && isLevelWord(token, article.words)
    const props = {
      key: index,
      onContextMenu: word ? (event: ReactMouseEvent<HTMLElement>) => onWordContext(event, word, tokens.slice(0, index).join('').length + token.indexOf(word), section) : undefined,
    }
    if (isAdded) return <mark {...props} title="Added to vocabulary" className="rounded-[5px] bg-good-soft px-0.5 font-medium text-good">{token}</mark>
    if (word && queued.has(wordKey(word))) return <mark {...props} title="Queued for Add" className="rounded-[5px] bg-good-soft px-0.5 font-medium text-good">{token}</mark>
    if (levelWord) return <mark {...props} title={`${word} · ${article.topic} vocabulary at this level`} className="rounded-[5px] bg-accent-soft px-0.5 font-medium text-accent">{token}</mark>
    return <span {...props}>{token}</span>
  })}</>
}

function ArticleCard({ article, language, busy, queued, onRetry, onWordsToAdd, onWordToAdd }: { article: Article; language: LanguageCode; busy: boolean; queued: Set<string>; onRetry: () => void; onWordsToAdd: () => void; onWordToAdd: (word: string, category: Category) => void }) {
  const [menu, setMenu] = useState<{word: string; x: number; y: number; offset: number; section: 'title' | 'summary'} | null>(null)
  const [readingFromHere, setReadingFromHere] = useState(false)
  const [speechNotice, setSpeechNotice] = useState('')
  const menuRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!menu) return
    menuRef.current?.querySelector<HTMLButtonElement>('[role="menuitem"]')?.focus()
    const close = (event: PointerEvent) => { if (!menuRef.current?.contains(event.target as Node)) setMenu(null) }
    const keydown = (event: KeyboardEvent) => { if (event.key === 'Escape') { event.preventDefault(); setMenu(null) } }
    document.addEventListener('pointerdown', close)
    document.addEventListener('keydown', keydown)
    return () => { document.removeEventListener('pointerdown', close); document.removeEventListener('keydown', keydown) }
  }, [menu])
  const wordContext: WordHandler = (event, word, offset, section) => {
    event.preventDefault()
    setMenu({word, offset, section, x: Math.max(8, Math.min(event.clientX, window.innerWidth - 240)), y: Math.max(8, Math.min(event.clientY, window.innerHeight - 275))})
  }
  return (
    <motion.article
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="rounded-2xl border border-line bg-surface p-6 shadow-sm sm:p-8"
    >
      <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs font-semibold uppercase tracking-[0.09em] text-muted">
        <span className="text-accent">{article.topic}</span>
        <span aria-hidden>·</span>
        {article.url ? (
          <a href={article.url} target="_blank" rel="noreferrer" title={article.url}
            className="inline-flex items-center gap-0.5 underline decoration-line underline-offset-2 transition hover:text-ink">
            {article.publication}<ArrowUpRight aria-hidden className="size-3" />
          </a>
        ) : <span>{article.publication}</span>}
      </p>
      {article.publishedAt && <p className="mt-2 text-xs text-muted">Published <time dateTime={article.publishedAt}>{new Date(article.publishedAt).toLocaleDateString()}</time></p>}
      <h2 className="serif-text mt-3 text-3xl leading-tight tracking-tight"><WordTokens text={article.title} article={article} queued={queued} section="title" onWordContext={wordContext} highlightLevel={false} /></h2>
      <div className="mt-5"><p className="serif-text whitespace-pre-wrap text-[1.3rem] leading-[1.65] tracking-tight sm:text-[1.45rem]"><WordTokens text={article.summary} article={article} queued={queued} section="summary" onWordContext={wordContext} /></p></div>
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-5">
        <p className="text-sm text-muted">{plural(article.summary.split(/\s+/).length, 'word', 'words')} · {plural(article.words.length, 'highlighted', 'highlighted')}</p>
        <div className="flex flex-wrap items-center gap-2">
          <span className={readingFromHere ? "hidden" : ""}><SpeakButton text={`${article.title}. ${article.summary}`} code={language} label="Listen to article" /></span>
          {readingFromHere && <Button variant="secondary" size="sm" onClick={() => stopSpeaking()}>Stop</Button>}
          {speechNotice && <span role="status" className="text-xs text-muted">{speechNotice}</span>}
          <Button variant="secondary" icon={busy ? LoaderCircle : RotateCcw} spinning={busy} disabled={busy} onClick={onRetry}>New article</Button>
          {article.words.length > 0 && <Button variant="secondary" icon={BookPlus} onClick={onWordsToAdd} title="Put the highlighted words into the Add tab">Words to Add</Button>}
        </div>
      </div>
      {menu && createPortal(<div ref={menuRef} role="menu" aria-label={`Options for ${menu.word}`} style={{left: menu.x, top: menu.y}}
        className="fixed z-50 w-56 rounded-xl border border-line bg-surface p-1.5 shadow-xl">
        {speechAvailable && <button role="menuitem" type="button" onClick={() => {
          const passage = menu.section === 'title' ? `${article.title.slice(menu.offset)}. ${article.summary}` : article.summary.slice(menu.offset)
          setSpeechNotice('')
          speak(passage, language, () => setReadingFromHere(false), (_reason, detail) => setSpeechNotice(detail ? `${detail} Using browser voice.` : 'Using browser voice.'), true)
          setReadingFromHere(true)
          setMenu(null)
        }} className="block w-full rounded-lg px-3 py-2 text-left text-sm text-ink hover:bg-surface-2 focus:bg-surface-2 focus:outline-none">Read aloud from here</button>}
        <p className="truncate px-3 py-2 text-xs font-medium text-muted">Add “{menu.word}” to…</p>
        {categoriesFor(language).map((category) => <button key={category} role="menuitem" type="button"
          onClick={() => { onWordToAdd(menu.word, category); setMenu(null) }}
          className="block w-full rounded-lg px-3 py-2 text-left text-sm text-ink hover:bg-surface-2 focus:bg-surface-2 focus:outline-none">{categoryLabels[category]}</button>)}
      </div>, document.body)}
    </motion.article>
  )
}

export function ReadPage() {
  const { meta, language } = useMeta()
  const location = useLocation()
  const navigate = useNavigate()
  useEffect(() => {
    if (!(location.state as { resumeArticle?: boolean } | null)?.resumeArticle) return
    let position = 0
    try { position = Number(sessionStorage.getItem('languages.read.returnScrollY')) || 0 } catch { /* Scroll restoration is optional. */ }
    requestAnimationFrame(() => window.scrollTo({ top: position }))
    navigate(location.pathname + location.search, { replace: true, state: null })
  }, [location.pathname, location.search, location.state, navigate])
  const [queuedDrafts, setQueuedDrafts] = useState<Draft[]>(() => readStored<Draft[]>('drafts') ?? [])
  const [queueNotice, setQueueNotice] = useState('')
  const topics = meta.topics
  const [topic, setTopic] = usePersistentState<string | null>('read.topic', null)
  const [level, setLevel] = usePersistentState<Level>('read.level', meta.defaults.level)
  const [articles, setArticles] = usePersistentState<StoredArticles>('read.articles', {})
  const [searchParams] = useSearchParams()
  const requestedMode = searchParams.get('mode')
  const [mode, setMode] = useState<ReadMode>(requestedMode === 'url' || requestedMode === 'text' ? requestedMode : 'find')
  useEffect(() => { if (requestedMode === 'find' || requestedMode === 'url' || requestedMode === 'text') setMode(requestedMode) }, [requestedMode])
  const [source, setSource] = useState('')
  const [summaryWords, setSummaryWords] = usePersistentState<number>('read.summaryWords', 100)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const controller = useRef<AbortController | null>(null)

  const chosenTopic = topic && topics.includes(topic) ? topic : topics[0]
  const storedArticle = articles[language.code]
  const article = storedArticle?.retrievedAt ? storedArticle : null

  useEffect(() => () => controller.current?.abort(), [])

  const retrieve = () => {
    if (!chosenTopic || loading || (mode !== 'find' && !source.trim())) return
    controller.current?.abort()
    const current = new AbortController()
    controller.current = current
    setLoading(true)
    setError(null)
    api
      .read(language.code, chosenTopic, level, current.signal, mode, source, summaryWords)
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

  const queued = new Set(queuedDrafts.filter((draft) => draft.language === language.code && draft.articleSource &&
    draft.articleSource.url === (article?.url ?? '') && draft.articleSource.retrievedAt === (article?.retrievedAt ?? '')).map((draft) => wordKey(draft.articleSource!.word)))
  const queueWords = (words: string[], category: Category) => {
    if (!article) return
    const current = readStored<Draft[]>('drafts') ?? []
    const next = [...current]
    for (const word of words) {
      const existing = next.findIndex((draft) => draft.language === language.code && draft.articleSource?.url === (article.url ?? '') &&
        draft.articleSource?.retrievedAt === (article.retrievedAt ?? '') && wordKey(draft.articleSource.word) === wordKey(word))
      if (existing >= 0) next[existing] = { ...next[existing], category }
      else next.push({ id: newId(), language: language.code, request: word, status: 'queued', category,
        articleSource: { word, url: article.url ?? '', retrievedAt: article.retrievedAt ?? '' } })
    }
    writeStored('drafts', next)
    const persisted = readStored<Draft[]>('drafts')
    if (!persisted || !next.every((draft) => persisted.some((item) => item.id === draft.id && item.category === draft.category))) {
      setQueueNotice('Could not add the words to the queue. Please check browser storage.')
      return
    }
    setQueuedDrafts(persisted)
    setQueueNotice(`${plural(words.length, 'word', 'words')} queued for Add · ${categoryLabels[category]}.`)
  }
  const wordToAdd = (word: string, category: Category) => queueWords([word], category)
  const wordsToAdd = () => {
    if (!article?.words.length) return
    const stored = readStored<Category>('add.category')
    queueWords(article.words, stored && categoriesFor(language.code).includes(stored) ? stored : 'general')
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
          Choose an article in {language.name}, select a level, and explore the highlighted vocabulary. You can listen to it and queue words for Add.
        </p>
      </div>

      <div className="rounded-2xl border border-line bg-surface p-5 shadow-sm sm:p-7">
        <div className="divide-y divide-line">
          <div className="grid gap-2.5 py-5 first:pt-0 sm:grid-cols-[9rem_1fr] sm:gap-6">
            <label htmlFor="read-mode" className="pt-2 text-sm font-medium text-muted">Read</label>
            <select id="read-mode" value={mode} onChange={(event) => { setMode(event.target.value as ReadMode); setError(null) }} className="rounded-xl border border-line bg-surface px-3 py-2 text-ink">
              <option value="find">Find an article and read</option>
              <option value="url">Summarize a webpage and read</option>
              <option value="text">Read pasted article text</option>
            </select>
          </div>
          {mode === 'find' && <div className="grid gap-2.5 py-5 sm:grid-cols-[9rem_1fr] sm:gap-6">
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
          </div>}
          {mode !== 'find' && <div className="grid gap-2.5 py-5 sm:grid-cols-[9rem_1fr] sm:gap-6">
            <label htmlFor="read-source" className="pt-2 text-sm font-medium text-muted">{mode === 'url' ? 'Webpage URL' : 'Article text'}</label>
            {mode === 'url' ? <input id="read-source" type="url" value={source} onChange={(event) => setSource(event.target.value)} placeholder="https://…" className="w-full rounded-xl border border-line bg-surface p-3 text-ink" /> :
              <textarea id="read-source" value={source} onChange={(event) => setSource(event.target.value)} maxLength={24000} rows={8} placeholder="Paste the article here" className="w-full rounded-xl border border-line bg-surface p-3 text-ink" />}
          </div>}
          {mode === 'url' && <p className="py-3 text-sm text-muted">Only allowed {language.name} websites can be used. See Allowed sources in the Languages menu.</p>}
          {mode !== 'text' && <div className="grid gap-2.5 py-5 sm:grid-cols-[9rem_1fr] sm:gap-6">
            <label htmlFor="summary-words" className="pt-2 text-sm font-medium text-muted">Summary length</label>
            <select id="summary-words" value={summaryWords} onChange={(event) => setSummaryWords(Number(event.target.value))} className="rounded-xl border border-line bg-surface px-3 py-2 text-ink">
              {[50, 75, 100, 150, 200, 250, 300].map((count) => <option key={count} value={count}>{count} words</option>)}
            </select>
          </div>}
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
                The chosen level determines which words are highlighted. Summaries are written at that level.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-2 flex flex-col gap-4 border-t border-line pt-5 sm:flex-row sm:items-center">
          <p className="min-w-0 flex-1 text-sm leading-relaxed text-muted">
            {mode === 'find' ? `A current ${chosenTopic} article in ${language.name}` : mode === 'url' ? 'Summarize the webpage' : 'Analyze the pasted article'} · {level}
          </p>
          <Button size="md" iconRight={ArrowRight} shortcut="↵" onClick={retrieve} disabled={loading || !chosenTopic || (mode !== 'find' && !source.trim())} aria-label={mode === 'find' ? `Retrieve a ${chosenTopic} article at ${level}` : mode === 'url' ? 'Summarize webpage' : 'Analyze article'}>
            {loading ? 'Working…' : mode === 'find' ? 'Retrieve' : mode === 'url' ? 'Summarize' : 'Analyze'}
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
          {queueNotice && <p role="status" className="mb-3 text-sm text-muted">{queueNotice} <Link to="/add" className="text-accent underline">Open Add</Link></p>}
          <ArticleCard queued={queued} key={`${article.url}-${article.retrievedAt}`} article={article} language={language.code} busy={loading} onRetry={retrieve} onWordsToAdd={wordsToAdd} onWordToAdd={wordToAdd} />
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
