import Icon from './Icon'

export type StatIconTone = 'primary' | 'secondary' | 'error' | 'tertiary' | 'success'

interface StatCardProps {
  label: string
  value: string
  detail?: string
  detailTone?: 'positive' | 'negative' | 'neutral'
  icon: string
  iconTone: StatIconTone
}

const iconToneClasses: Record<StatIconTone, string> = {
  primary: 'text-primary',
  secondary: 'text-secondary-container',
  error: 'text-error',
  tertiary: 'text-tertiary-container',
  success: 'text-green-600',
}

const decorClasses: Record<StatIconTone, string> = {
  primary: 'bg-surface-container opacity-50',
  secondary: 'bg-surface-container opacity-50',
  error: 'bg-error-container opacity-30',
  tertiary: 'bg-surface-container opacity-50',
  success: 'bg-surface-container opacity-50',
}

export default function StatCard({
  label,
  value,
  detail,
  detailTone = 'neutral',
  icon,
  iconTone,
}: StatCardProps) {
  const detailClasses =
    detailTone === 'positive'
      ? 'text-green-600'
      : detailTone === 'negative'
        ? 'text-error'
        : 'text-on-surface-variant'

  return (
    <div className="bg-surface-container-lowest p-card-padding rounded-lg shadow-card border border-surface-container-high flex flex-col gap-2 relative overflow-hidden group">
      <div
        className={`absolute -right-4 -top-4 w-16 h-16 rounded-full group-hover:scale-150 transition-transform duration-500 ${decorClasses[iconTone]}`}
      />
      <div className="flex justify-between items-center relative z-10">
        <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">
          {label}
        </span>
        <Icon name={icon} size="20px" className={iconToneClasses[iconTone]} />
      </div>
      <div className="font-h2-headline text-h2-headline text-on-surface relative z-10">{value}</div>
      {detail && (
        <div
          className={`flex items-center gap-1 font-label-sm text-label-sm relative z-10 ${detailClasses}`}
        >
          {detail}
        </div>
      )}
    </div>
  )
}
