import { useEffect, useState, type Dispatch, type SetStateAction } from 'react'
import { readStored, writeStored } from '../lib/storage'

export function usePersistentState<T>(key: string, initial: T): [T, Dispatch<SetStateAction<T>>] {
  const [value, setValue] = useState<T>(() => readStored<T>(key) ?? initial)

  useEffect(() => {
    writeStored(key, value)
  }, [key, value])

  return [value, setValue]
}
