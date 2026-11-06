import { Link, useLocation } from 'react-router'
import { ArrowLeft } from 'lucide-react'
import { useMeta } from '../context/MetaContext'
import { hasExerciseToReturn, returnExercisePath } from '../lib/exerciseReturn'

export function ReturnToExercise() {
  const location = useLocation()
  const { language, setLanguage } = useMeta()
  const path = returnExercisePath(location.pathname, location.state)
  const original = (location.state as { returnLanguage?: unknown } | null)?.returnLanguage
  const returnLanguage = original === 'EN' || original === 'DE' || original === 'FR' ? original : language.code
  if (!path || !hasExerciseToReturn(path, returnLanguage)) return null
  const article = path === '/read' || path.startsWith('/read?')
  return <Link to={path} onClick={(event) => {
    if (!event.metaKey && !event.ctrlKey && !event.altKey && !event.shiftKey && event.button === 0 && language.code !== returnLanguage) {
      setLanguage(returnLanguage, { preserveSessions: true })
    }
  }} state={article ? { resumeArticle: true } : { resumeExercise: true }} className="inline-flex shrink-0 items-center gap-2 rounded-xl border border-line bg-surface px-3 py-2 text-sm font-medium text-ink transition hover:border-accent/50 hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
    <ArrowLeft aria-hidden className="size-4" />{article ? 'Back to article' : 'Back to exercise'}
  </Link>
}
