import Icon from './Icon'

interface ErrorStateProps {
  title?: string
  description?: string
}

export default function ErrorState({
  title = 'Ocurrió un error',
  description = 'No se pudo completar la operación. Inténtalo nuevamente.',
}: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center gap-3">
      <div className="w-12 h-12 rounded-full bg-error-container flex items-center justify-center">
        <Icon name="error" className="text-error" />
      </div>
      <p className="font-h3-title text-h3-title text-on-surface">{title}</p>
      {description && (
        <p className="font-body-md text-body-md text-on-surface-variant max-w-sm">
          {description}
        </p>
      )}
    </div>
  )
}
