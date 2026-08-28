import Icon from './Icon'

interface EmptyStateProps {
  icon?: string
  title: string
  description?: string
}

export default function EmptyState({
  icon = 'inbox',
  title,
  description,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Icon name={icon} size="48px" className="text-outline mb-3" />
      <p className="font-h3-title text-h3-title text-on-surface">{title}</p>
      {description && (
        <p className="font-body-md text-body-md text-on-surface-variant mt-1 max-w-sm">
          {description}
        </p>
      )}
    </div>
  )
}
