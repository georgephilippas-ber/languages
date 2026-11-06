import { useCallback, useRef, useState, type Dispatch, type SetStateAction } from 'react'

function read(key: string): string {
  try { return sessionStorage.getItem(`languages.${key}`) ?? '' } catch { return '' }
}

// Keep unfinished text only for this browser tab; submitting clears it.
export function useSessionText(key: string): [string, Dispatch<SetStateAction<string>>] {
  const [, refresh] = useState(0)
  const current = useRef({ key, value: read(key) })
  if (current.current.key !== key) current.current = { key, value: read(key) }
  const set = useCallback<Dispatch<SetStateAction<string>>>((action) => {
    const value = typeof action === 'function' ? action(current.current.value) : action
    current.current = { key, value }
    try {
      if (value) sessionStorage.setItem(`languages.${key}`, value)
      else sessionStorage.removeItem(`languages.${key}`)
    } catch { /* Continue editing even when browser storage is unavailable. */ }
    refresh((revision) => revision + 1)
  }, [key])
  return [current.current.value, set]
}
