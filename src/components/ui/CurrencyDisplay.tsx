import { formatCurrency } from '@/utils/format'

interface CurrencyDisplayProps {
  value: number
  className?: string
  strong?: boolean
  tone?: 'default' | 'success' | 'error'
}

const toneClasses = {
  default: 'text-on-surface',
  success: 'text-green-600',
  error: 'text-error',
}

export default function CurrencyDisplay({
  value,
  className = '',
  strong = false,
  tone = 'default',
}: CurrencyDisplayProps) {
  return (
    <span
      className={`${strong ? 'font-medium' : ''} ${toneClasses[tone]} ${className}`}
    >
      {formatCurrency(value)}
    </span>
  )
}
