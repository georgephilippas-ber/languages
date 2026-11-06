import { useEffect, useState } from 'react'
import { api, API_KEY_CHANGED, MODEL_KEY } from '../api'
import { usePersistentState } from '../hooks/usePersistentState'
import type { Models } from '../types'

export function ModelPicker() {
  const [models, setModels] = useState<Models | null>(null)
  const [selected, setSelected] = usePersistentState<string | null>(MODEL_KEY, null)
  useEffect(() => {
    let alive = true
    const load = () => api.models().then((value) => { if (alive) setModels(value) }).catch(() => { if (alive) setModels(null) })
    void load()
    window.addEventListener(API_KEY_CHANGED, load)
    return () => { alive = false; window.removeEventListener(API_KEY_CHANGED, load) }
  }, [])
  useEffect(() => {
    if (models && selected && !models.models.includes(selected)) setSelected(null)
  }, [models, selected, setSelected])
  return <label className="block text-sm font-medium text-ink">OpenAI model
    <select aria-label="OpenAI model" value={models ? (selected ?? models.default) : ''} disabled={!models}
      onChange={(event) => setSelected(event.target.value === models?.default ? null : event.target.value)}
      className="mt-2 w-full rounded-xl border border-line bg-bg px-3 py-2 text-sm text-ink outline-none focus:border-accent disabled:opacity-60">
      {!models ? <option value="">Models unavailable</option> : models.models.map((model) => <option key={model} value={model}>{model}{model === models.default ? ' (default)' : ''}</option>)}
    </select>
  </label>
}
