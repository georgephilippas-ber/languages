import { Link, useLocation } from 'react-router'
import { ArrowLeft } from 'lucide-react'
import { useMeta } from '../context/MetaContext'
import { hasExerciseToReturn, returnExercisePath } from '../lib/exerciseReturn'

export function ReturnToExercise() {
  const location = useLocation()
  const { language } = useMeta()
  const path = returnExercisePath(location.pathname, location.state)
  if (!path || !hasExerciseToReturn(path, language.code)) return null
  const article = path === '/read' || path.startsWith('/read?')
  return <Link to={path} state={article ? { resumeArticle: true } : { resumeExercise: true }} className="inline-flex shrink-0 items-center gap-2 rounded-xl border border-line bg-surface px-3 py-2 text-sm font-medium text-ink transition hover:border-accent/50 hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
    <ArrowLeft aria-hidden className="size-4" />{article ? 'Back to article' : 'Back to exercise'}
  </Link>
}
