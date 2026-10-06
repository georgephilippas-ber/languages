import { useEffect, useRef } from 'react'

export function useKeydown(handler: (event: KeyboardEvent) => void, enabled = true): void {
  const handlerRef = useRef(handler)

  useEffect(() => {
    handlerRef.current = handler
  })

  useEffect(() => {
    if (!enabled) return
    const listener = (event: KeyboardEvent) => handlerRef.current(event)
    window.addEventListener('keydown', listener)
    return () => window.removeEventListener('keydown', listener)
  }, [enabled])
}

export function isEditable(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName))
  )
}

export function isInteractive(target: EventTarget | null): boolean {
  return isEditable(target) || (target instanceof HTMLElement && ['BUTTON', 'A'].includes(target.tagName))
}

export function hasModifier(event: KeyboardEvent): boolean {
  return event.metaKey || event.ctrlKey || event.altKey
}
