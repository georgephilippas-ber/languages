import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'

export function Section({ label, icon: Icon, children }: { label: string; icon?: LucideIcon; children: ReactNode }) {
  return (
    <section>
      <h3 className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.09em] text-muted">
        {Icon && <Icon aria-hidden className="size-3.5" />}
        {label}
      </h3>
      <div className="text-[15px] leading-relaxed">{children}</div>
    </section>
  )
}
