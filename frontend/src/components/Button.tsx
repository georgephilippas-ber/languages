import type { ComponentProps } from 'react'
import type { LucideIcon } from 'lucide-react'
import { cx } from '../lib/cx'
import { Kbd } from './Kbd'

type Variant = 'primary' | 'secondary' | 'ghost'
type Size = 'sm' | 'md' | 'lg'

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-accent text-accent-ink shadow-sm shadow-accent/20 hover:brightness-110 active:brightness-95',
  secondary: 'border border-line bg-surface text-ink hover:border-accent/50 hover:bg-surface-2',
  ghost: 'text-muted hover:bg-surface-2 hover:text-ink',
}

const SIZES: Record<Size, { base: string; padding: string; square: string }> = {
  sm: { base: 'h-8 gap-1.5 rounded-lg text-sm', padding: 'px-2.5', square: 'w-8' },
  md: { base: 'h-10 gap-2 rounded-xl text-sm', padding: 'px-4', square: 'w-10' },
  lg: { base: 'h-12 gap-2 rounded-xl text-[15px]', padding: 'px-5', square: 'w-12' },
}

interface ButtonProps extends ComponentProps<'button'> {
  variant?: Variant
  size?: Size
  icon?: LucideIcon
  iconRight?: LucideIcon
  shortcut?: string
  spinning?: boolean
}

export function Button({
  variant = 'primary',
  size = 'md',
  icon: Icon,
  iconRight: IconRight,
  shortcut,
  spinning = false,
  className,
  children,
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cx(
        'inline-flex shrink-0 cursor-pointer select-none items-center justify-center font-medium transition duration-150',
        'disabled:pointer-events-none disabled:opacity-45',
        VARIANTS[variant],
        SIZES[size].base,
        children ? SIZES[size].padding : SIZES[size].square,
        className,
      )}
      {...props}
    >
      {Icon && <Icon aria-hidden className={cx('size-4 shrink-0', spinning && 'animate-spin')} />}
      {children}
      {IconRight && <IconRight aria-hidden className="size-4 shrink-0" />}
      {shortcut && (
        <span className="ml-1 hidden sm:inline-flex pointer-coarse:hidden">
          <Kbd tone={variant === 'primary' ? 'accent' : 'default'}>{shortcut}</Kbd>
        </span>
      )}
    </button>
  )
}
