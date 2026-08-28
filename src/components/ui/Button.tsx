import type { ButtonHTMLAttributes } from 'react'
import type { ButtonSize, ButtonVariant } from '@/types'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
}

const baseClasses =
  'inline-flex items-center justify-center gap-2 rounded-lg font-label-sm text-label-sm transition-all focus:outline-none focus:ring-2 focus:ring-primary/30 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap select-none'

const variantClasses: Record<ButtonVariant, string> = {
  primary: 'bg-primary text-on-primary shadow-sm hover:bg-primary-container',
  'primary-container':
    'bg-primary-container text-on-primary shadow-sm hover:bg-primary hover:shadow-md',
  secondary: 'bg-surface-container-lowest text-primary-container border border-outline-variant hover:bg-surface-container-low',
  outline: 'bg-surface-container-lowest text-primary border border-outline-variant hover:bg-surface-container-low',
  ghost: 'bg-transparent text-primary hover:bg-surface-container-high',
  danger: 'bg-error text-on-error shadow-sm hover:opacity-90',
}

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 py-1.5',
  md: 'h-10 px-5 py-2.5',
  lg: 'h-12 px-6 py-3',
}

export default function Button({
  variant = 'primary',
  size = 'md',
  className = '',
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  )
}
