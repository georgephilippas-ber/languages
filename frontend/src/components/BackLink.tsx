import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router'

export function BackLink({ to = '/' }: { to?: string }) {
  return <Link to={to} className="mb-5 inline-flex min-h-9 items-center gap-2 rounded-lg px-2 text-sm font-medium text-muted transition hover:bg-surface-2 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
    <ArrowLeft aria-hidden className="size-4" /> Back
  </Link>
}
