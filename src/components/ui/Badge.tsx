import type { ReactNode } from 'react'

export type BadgeTone =
  | 'neutral'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'primary'
  | 'disabled'

interface BadgeProps {
  tone?: BadgeTone
  children: ReactNode
  className?: string
}

const toneClasses: Record<BadgeTone, string> = {
  neutral: 'bg-surface-variant text-on-surface',
  success: 'bg-surface-container-high text-primary-container',
  warning: 'bg-secondary-fixed text-on-secondary-fixed',
  danger: 'bg-error-container text-on-error-container',
  info: 'bg-surface-container-highest text-primary',
  primary: 'bg-inverse-on-surface text-primary-container border border-outline-variant/30',
  disabled: 'bg-surface-variant text-on-surface-variant',
}

export default function Badge({ tone = 'neutral', children, className = '' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-label-sm text-[11px] font-medium ${toneClasses[tone]} ${className}`}
    >
      {children}
    </span>
  )
}
