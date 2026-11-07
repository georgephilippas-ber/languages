import { useEffect, useRef, useState, type MouseEvent, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { useMeta } from '../context/MetaContext'
import { categoriesFor, categoryLabels } from '../lib/files'
import { newId, type Draft } from '../lib/drafts'
import { readStored, writeStored } from '../lib/storage'
import { speak, speechAvailable } from '../lib/speech'
import type { Category, LanguageCode } from '../types'

const NAMES: Record<LanguageCode, string> = { EN: 'English', DE: 'German', FR: 'French' }

type CaretDocument = Document & {
  caretPositionFromPoint?: (x: number, y: number) => { offsetNode: Node; offset: number } | null
  caretRangeFromPoint?: (x: number, y: number) => Range | null
}

function wordAtPoint(x: number, y: number): { word: string; element: HTMLElement } | null {
  const doc = document as CaretDocument
  const position = doc.caretPositionFromPoint?.(x, y)
  const range = position ? null : doc.caretRangeFromPoint?.(x, y)
  const node = position?.offsetNode ?? range?.startContainer
  const offset = position?.offset ?? range?.startOffset
  if (!node || node.nodeType !== Node.TEXT_NODE || offset === undefined || !node.parentElement) return null
  const text = node.textContent ?? ''
  const words = text.matchAll(/[\p{L}\p{M}]+(?:['’\-][\p{L}\p{M}]+)*/gu)
  for (const match of words) {
    if (offset >= match.index && offset <= match.index + match[0].length) return { word: match[0], element: node.parentElement }
  }
  return null
}

function languageFor(element: HTMLElement, fallback: LanguageCode): LanguageCode {
  const value = element.closest('[data-word-language], [lang]')
  const lang = (value?.getAttribute('data-word-language') ?? value?.getAttribute('lang') ?? '').slice(0, 2).toUpperCase()
  return lang === 'EN' || lang === 'DE' || lang === 'FR' ? lang : fallback
}

export function ExerciseWordMenu({ children }: { children: ReactNode }) {
  const { language } = useMeta()
  const [menu, setMenu] = useState<{ word: string; language: LanguageCode; x: number; y: number } | null>(null)
  const [notice, setNotice] = useState('')
  const menuRef = useRef<HTMLDivElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)
  const lastTouch = useRef(0)
  useEffect(() => {
    let timer: number | undefined
    const selectionChanged = () => {
      if (Date.now() - lastTouch.current > 15_000) return
      window.clearTimeout(timer)
      timer = window.setTimeout(() => {
        const selection = window.getSelection()
        if (!selection || selection.isCollapsed || selection.rangeCount !== 1) return
        const range = selection.getRangeAt(0)
        const root = contentRef.current
        if (!root || !root.contains(range.startContainer) || !root.contains(range.endContainer)) return
        const element = range.startContainer.nodeType === Node.ELEMENT_NODE
          ? range.startContainer as HTMLElement : range.startContainer.parentElement
        const endElement = range.endContainer.nodeType === Node.ELEMENT_NODE
          ? range.endContainer as HTMLElement : range.endContainer.parentElement
        if (!element || !endElement || element.closest('input, textarea, select, [contenteditable="true"]') ||
            endElement.closest('input, textarea, select, [contenteditable="true"]')) return
        const word = selection.toString().trim()
        if (!/^[\p{L}\p{M}]+(?:['’\-][\p{L}\p{M}]+)*$/u.test(word)) return
        const rect = range.getBoundingClientRect()
        if (!rect.width || !rect.height) return
        setNotice('')
        setMenu({ word, language: languageFor(element, language.code),
          x: Math.max(8, Math.min(rect.left, window.innerWidth - 256)),
          y: Math.max(8, Math.min(rect.bottom + 8, window.innerHeight - 330)) })
        selection.removeAllRanges()
        lastTouch.current = 0
      }, 120)
    }
    document.addEventListener('selectionchange', selectionChanged)
    return () => { document.removeEventListener('selectionchange', selectionChanged); window.clearTimeout(timer) }
  }, [language.code])
  useEffect(() => {
    if (!menu) return
    menuRef.current?.querySelector<HTMLButtonElement>('button')?.focus()
    const close = (event: PointerEvent) => { if (!menuRef.current?.contains(event.target as Node)) setMenu(null) }
    const key = (event: KeyboardEvent) => { if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); setMenu(null) } }
    document.addEventListener('pointerdown', close)
    document.addEventListener('keydown', key, true)
    return () => { document.removeEventListener('pointerdown', close); document.removeEventListener('keydown', key, true) }
  }, [menu?.word, menu?.x, menu?.y])
  useEffect(() => {
    if (!notice) return
    const timer = window.setTimeout(() => setNotice(''), 5000)
    return () => window.clearTimeout(timer)
  }, [notice])
  const open = (event: MouseEvent<HTMLDivElement>) => {
    if (!(event.target instanceof Element) || event.target.closest('input, textarea, select, [contenteditable="true"]')) return
    const found = wordAtPoint(event.clientX, event.clientY)
    if (!found || !event.currentTarget.contains(found.element)) return
    event.preventDefault()
    lastTouch.current = 0
    setNotice('')
    setMenu({ word: found.word, language: languageFor(found.element, language.code),
      x: Math.max(8, Math.min(event.clientX, window.innerWidth - 256)),
      y: Math.max(8, Math.min(event.clientY, window.innerHeight - 330)) })
  }
  const queue = (category: Category) => {
    if (!menu) return
    const current = readStored<Draft[]>('drafts') ?? []
    const exists = current.some((draft) => draft.language === menu.language && draft.request.normalize('NFC').toLocaleLowerCase() === menu.word.normalize('NFC').toLocaleLowerCase())
    if (exists) { setNotice(`“${menu.word}” is already in the ${NAMES[menu.language]} Add queue.`); setMenu(null); return }
    const draft: Draft = { id: newId(), language: menu.language, request: menu.word, status: 'queued', category }
    writeStored('drafts', [...current, draft])
    if (!(readStored<Draft[]>('drafts') ?? []).some((item) => item.id === draft.id)) {
      setNotice('Could not add the word to the queue. Please check browser storage.')
    } else {
      writeStored('add.category', category)
      setNotice(`“${menu.word}” queued for Add · ${NAMES[menu.language]} · ${categoryLabels[category]}.`)
    }
    setMenu(null)
  }
  return <div ref={contentRef} data-word-language={language.code} onTouchStartCapture={() => { lastTouch.current = Date.now() }} onContextMenu={open}>
    {children}
    {notice && <p role="status" className="fixed bottom-5 right-5 z-50 max-w-sm rounded-xl border border-line bg-surface px-4 py-3 text-sm text-ink shadow-lg">{notice}</p>}
    {menu && createPortal(<div ref={menuRef} role="menu" aria-label={`Options for ${menu.word}`} style={{ left: menu.x, top: menu.y }} className="fixed z-50 max-h-[calc(100vh-16px)] w-60 overflow-auto rounded-xl border border-line bg-surface p-1.5 shadow-xl">
      <p className="truncate px-3 py-2 text-xs font-medium text-muted">“{menu.word}”</p>
      <label className="flex items-center justify-between gap-2 px-3 py-2 text-xs text-muted">Language
        <select aria-label="Word language" value={menu.language} onChange={(event) => setMenu({ ...menu, language: event.target.value as LanguageCode })} className="rounded-lg border border-line bg-surface px-2 py-1 text-sm text-ink">
          {(['EN', 'DE', 'FR'] as const).map((code) => <option key={code} value={code}>{NAMES[code]}</option>)}
        </select>
      </label>
      {speechAvailable && <button role="menuitem" type="button" onClick={() => {
        const { word, language: code } = menu
        speak(word, code, () => {}, (_reason, detail) => setNotice(detail ? `${detail} Using browser voice.` : 'Using browser voice.'))
        setMenu(null)
      }} className="block w-full rounded-lg px-3 py-2 text-left text-sm text-ink hover:bg-surface-2 focus:bg-surface-2 focus:outline-none">Speak word</button>}
      <p className="px-3 py-2 text-xs font-medium text-muted">Add to queue…</p>
      {categoriesFor(menu.language).map((category) => <button role="menuitem" key={category} type="button" onClick={() => queue(category)} className="block w-full rounded-lg px-3 py-2 text-left text-sm text-ink hover:bg-surface-2 focus:bg-surface-2 focus:outline-none">{categoryLabels[category]}</button>)}
    </div>, document.body)}
  </div>
}
