import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { Check, ChevronDown, Cpu } from 'lucide-react'
import { api, MODEL_KEY } from '../api'
import { usePersistentState } from '../hooks/usePersistentState'
import { cx } from '../lib/cx'
import type { Models } from '../types'

export function ModelPicker() {
  const [models, setModels] = useState<Models | null>(null)
  const [selected, setSelected] = usePersistentState<string | null>(MODEL_KEY, null)
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const root = useRef<HTMLDivElement>(null)
  const list = useRef<HTMLUListElement>(null)

  useEffect(() => {
    let alive = true
    api
      .models()
      .then((value) => alive && setModels(value))
      .catch(() => alive && setModels(null))
    return () => {
      alive = false
    }
  }, [])

  useEffect(() => {
    if (models && selected && !models.models.includes(selected)) setSelected(null)
  }, [models, selected, setSelected])

  useEffect(() => {
    if (!open) return
    const close = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('pointerdown', close)
    return () => document.removeEventListener('pointerdown', close)
  }, [open])

  useEffect(() => {
    if (open) list.current?.querySelector<HTMLElement>(`[data-index="${active}"]`)?.scrollIntoView({ block: 'nearest' })
  }, [open, active])

  if (!models) return null

  const current = selected ?? models.default
  const choose = (model: string) => {
    setSelected(model === models.default ? null : model)
    setOpen(false)
  }
  const openList = () => {
    setActive(Math.max(0, models.models.indexOf(current)))
    setOpen(true)
  }

  const onKeyDown = (event: KeyboardEvent) => {
    if (!open) {
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault()
        openList()
      }
      return
    }
    if (event.key === 'Escape') {
      event.preventDefault()
      event.stopPropagation()
      setOpen(false)
    } else if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActive((index) => Math.min(models.models.length - 1, index + 1))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActive((index) => Math.max(0, index - 1))
    } else if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      choose(models.models[active])
    }
  }

  return (
    <div ref={root} className="relative" onKeyDown={onKeyDown}>
      <button
        type="button"
        onClick={() => (open ? setOpen(false) : openList())}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`Model: ${current}. Change model`}
        title={`Model: ${current}`}
        className={cx(
          'flex h-9 cursor-pointer items-center gap-1.5 rounded-xl px-2 text-xs font-medium transition hover:bg-surface-2 hover:text-ink',
          open ? 'bg-surface-2 text-ink' : 'text-muted',
        )}
      >
        <Cpu aria-hidden className="size-[18px]" />
        <span className="hidden max-w-32 truncate font-mono sm:inline">{current}</span>
        <ChevronDown aria-hidden className={cx('size-3.5 transition', open && 'rotate-180')} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: 0.12 }}
            className="absolute right-0 top-full z-30 mt-2 w-64 origin-top-right overflow-hidden rounded-2xl border border-line bg-surface shadow-xl"
          >
            <p className="border-b border-line px-3.5 py-2.5 text-xs font-semibold tracking-wide text-muted">OpenAI model</p>
            <ul ref={list} role="listbox" aria-label="OpenAI model" className="max-h-80 overflow-y-auto p-1.5">
              {models.models.map((model, index) => (
                <li
                  key={model}
                  role="option"
                  data-index={index}
                  aria-selected={model === current}
                  onClick={() => choose(model)}
                  onPointerMove={() => setActive(index)}
                  className={cx(
                    'flex cursor-pointer items-center gap-2 rounded-lg px-2.5 py-2 text-sm',
                    index === active ? 'bg-surface-2 text-ink' : 'text-muted',
                  )}
                >
                  <Check aria-hidden className={cx('size-4 shrink-0 text-accent', model !== current && 'invisible')} />
                  <span className={cx('truncate font-mono text-[13px]', model === current && 'font-semibold text-ink')}>{model}</span>
                  {model === models.default && (
                    <span className="ml-auto shrink-0 rounded-full bg-accent-soft px-2 py-0.5 text-[11px] font-semibold text-accent">default</span>
                  )}
                </li>
              ))}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
