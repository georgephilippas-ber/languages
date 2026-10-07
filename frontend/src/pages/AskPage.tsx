import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { CircleAlert, LoaderCircle, MessageCircleQuestion, RotateCcw, Send, Trash2 } from 'lucide-react'
import { api, isAbort, messageOf } from '../api'
import { useMeta } from '../context/MetaContext'
import { usePersistentState } from '../hooks/usePersistentState'
import { cx } from '../lib/cx'
import type { LanguageCode } from '../types'
import { Button } from '../components/Button'
import { Kbd } from '../components/Kbd'
import { Notice } from '../components/Notice'
import { Rich } from '../components/Rich'

interface Exchange {
  id: string
  language: LanguageCode
  question: string
  answer: string
  onTopic: boolean
}

interface Pending {
  language: LanguageCode
  question: string
  status: 'loading' | 'error'
  error?: string
}

const MAX_LENGTH = 2000
const MAX_HISTORY = 6
const PLACEHOLDERS: Record<LanguageCode, string> = {
  DE: 'When do I use “wo-” compounds like “worauf” instead of “auf was”?',
  FR: 'What is the difference between “depuis” and “pendant”?',
  EN: 'Is “less” or “fewer” right with “people”?',
}

function newId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}

function ExchangeCard({ exchange }: { exchange: Exchange }) {
  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cx('rounded-2xl border bg-surface p-5 shadow-sm sm:p-6', exchange.onTopic ? 'border-line' : 'border-warn/40')}
    >
      <p className="whitespace-pre-wrap text-sm font-medium text-muted">{exchange.question}</p>
      <div className={cx('mt-3 text-[15px] leading-relaxed', !exchange.onTopic && 'text-warn')}>
        <Rich text={exchange.answer} />
      </div>
    </motion.article>
  )
}

export function AskPage() {
  const { meta, language } = useMeta()
  const [text, setText] = useState('')
  const [exchanges, setExchanges] = usePersistentState<Exchange[]>('ask', [])
  const [pending, setPending] = useState<Pending | null>(null)
  const asker = useRef<AbortController | null>(null)
  const end = useRef<HTMLDivElement | null>(null)

  const visible = exchanges.filter((exchange) => exchange.language === language.code)
  const current = pending && pending.language === language.code ? pending : null
  const loading = current?.status === 'loading'

  useEffect(() => () => asker.current?.abort(), [])

  useEffect(() => {
    asker.current?.abort()
    setPending(null)
  }, [language.code])

  useEffect(() => {
    if (current) end.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [current, visible.length])

  const ask = (question: string) => {
    const cleaned = question.trim()
    if (!cleaned || loading) return
    asker.current?.abort()
    const controller = new AbortController()
    asker.current = controller
    const code = language.code
    const history = visible.filter((exchange) => exchange.onTopic).slice(-MAX_HISTORY).map(({ question, answer }) => ({ question, answer }))
    setPending({ language: code, question: cleaned, status: 'loading' })
    setText('')
    api
      .ask(code, cleaned, history, controller.signal)
      .then((result) => {
        setExchanges((all) => [...all, { id: newId(), language: code, question: cleaned, answer: result.answer, onTopic: result.onTopic }])
        setPending(null)
      })
      .catch((error: unknown) => {
        if (!isAbort(error)) setPending({ language: code, question: cleaned, status: 'error', error: messageOf(error) })
      })
  }

  const clear = () => {
    asker.current?.abort()
    setPending(null)
    setExchanges((all) => all.filter((exchange) => exchange.language !== language.code))
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-8">
        <p className="flex items-center gap-2 text-sm font-medium text-info">
          <MessageCircleQuestion aria-hidden className="size-4" />
          {language.name} · Questions about language
        </p>
        <h1 className="serif-text mt-2 text-4xl tracking-tight sm:text-5xl">Ask</h1>
        <p className="mt-3 max-w-xl text-[17px] leading-relaxed text-muted">
          Ask about grammar, meaning, usage, register, pronunciation, translation, or where a word comes from. Questions
          are about {language.name} unless you name another language; anything that is not about language is declined.
        </p>
      </div>

      <div className="rounded-3xl border border-line bg-surface p-5 shadow-sm sm:p-7">
        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
              event.preventDefault()
              ask(text)
            }
          }}
          rows={3}
          maxLength={MAX_LENGTH}
          aria-label="Your question"
          placeholder={PLACEHOLDERS[language.code]}
          className="w-full resize-y rounded-2xl border border-line bg-bg px-4 py-3 text-[17px] leading-relaxed outline-none placeholder:text-muted/60 focus:border-info"
        />
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
          <p className="min-w-0 flex-1 text-sm text-muted">
            {visible.length ? 'Follow-up questions see the conversation so far.' : 'Answers are in English.'}
            {meta.demo ? ' Demo mode: placeholder answers.' : ''}
          </p>
          {visible.length > 0 && (
            <Button variant="ghost" icon={Trash2} onClick={clear}>
              Clear
            </Button>
          )}
          <Button icon={loading ? LoaderCircle : Send} spinning={loading} disabled={!text.trim() || loading} onClick={() => ask(text)}>
            Ask
            <span className="ml-1 hidden sm:inline-flex pointer-coarse:hidden">
              <Kbd tone="accent">⌘↵</Kbd>
            </span>
          </Button>
        </div>
      </div>

      {(visible.length > 0 || current) && (
        <div ref={end} className="mt-6 space-y-4">
          {current && (
            <div className="rounded-2xl border border-line bg-surface p-5 shadow-sm sm:p-6" role="status" aria-live="polite">
              <div className="flex items-start gap-3">
                <p className="min-w-0 flex-1 whitespace-pre-wrap text-sm font-medium text-muted">{current.question}</p>
                {current.status === 'loading' && <LoaderCircle aria-label="Answering" className="size-5 shrink-0 animate-spin text-muted" />}
              </div>
              {current.status === 'error' && (
                <div className="mt-3">
                  <Notice
                    tone="error"
                    action={
                      <Button size="sm" variant="secondary" icon={RotateCcw} onClick={() => ask(current.question)}>
                        Try again
                      </Button>
                    }
                  >
                    {current.error}
                  </Notice>
                </div>
              )}
            </div>
          )}
          <AnimatePresence initial={false}>
            {[...visible].reverse().map((exchange) => (
              <ExchangeCard key={exchange.id} exchange={exchange} />
            ))}
          </AnimatePresence>
        </div>
      )}

      {visible.length === 0 && !current && (
        <p className="mt-8 flex items-center justify-center gap-2 text-sm text-muted">
          <CircleAlert aria-hidden className="size-4" />
          Answers are written by the model; check anything important.
        </p>
      )}
    </div>
  )
}
