import { ArrowRight, Keyboard, ListChecks, Languages } from 'lucide-react'
import { Link } from 'react-router'

export function TranslatePage() {
  return <div className="mx-auto max-w-3xl">
    <div className="mb-8"><p className="flex items-center gap-2 text-sm font-medium text-accent"><Languages className="size-4" /> English · German · French</p>
      <h1 className="serif-text mt-2 text-4xl tracking-tight sm:text-5xl">Translate</h1>
      <p className="mt-3 max-w-xl text-[17px] leading-relaxed text-muted">Read a sentence in one language and complete its translation in another, using words from your vocabulary.</p>
    </div>
    <div className="grid gap-4 sm:grid-cols-2">{[
      { path: '/translate/recognize', icon: ListChecks, title: 'Recognize', description: 'Choose the missing translation from four options.' },
      { path: '/translate/produce', icon: Keyboard, title: 'Produce', description: 'Type the missing words yourself, with optional hints.' },
    ].map(({ path, icon: Icon, title, description }) => <Link key={path} to={path} className="group rounded-2xl border border-line bg-surface p-6 shadow-sm transition hover:border-accent/50 hover:shadow-md">
      <Icon className="size-5 text-accent" /><h2 className="serif-text mt-5 text-2xl">{title}</h2><p className="mt-2 text-sm text-muted">{description}</p><span className="mt-5 flex items-center gap-2 text-sm font-medium text-accent">Choose <ArrowRight className="size-4" /></span>
    </Link>)}</div>
  </div>
}
