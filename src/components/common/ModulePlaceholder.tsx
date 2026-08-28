import Icon from '@/components/ui/Icon'

interface ModulePlaceholderProps {
  title: string
  icon: string
}

export default function ModulePlaceholder({ title, icon }: ModulePlaceholderProps) {
  return (
    <div className="bg-surface-container-lowest rounded-lg border border-outline-variant shadow-card overflow-hidden">
      <div className="p-6 border-b border-outline-variant flex items-center gap-2 text-on-surface-variant bg-surface-bright">
        <span className="font-label-sm text-label-sm uppercase tracking-wider">{title}</span>
      </div>
      <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
        <div className="w-16 h-16 rounded-full bg-surface-container-low text-primary flex items-center justify-center mb-4">
          <Icon name={icon} size="32px" />
        </div>
        <h2 className="font-h3-title text-h3-title text-on-surface">{title}</h2>
        <p className="font-body-md text-body-md text-on-surface-variant mt-1">
          Módulo en construcción
        </p>
        <p className="font-label-sm text-label-sm text-on-surface-variant mt-2 max-w-sm">
          Esta funcionalidad será implementada en una siguiente etapa.
        </p>
      </div>
    </div>
  )
}
