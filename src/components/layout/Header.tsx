import Icon from '@/components/ui/Icon'
import { getSession } from '@/utils/session'

interface HeaderProps {
  onToggleSidebar: () => void
}

export default function Header({ onToggleSidebar }: HeaderProps) {
  const user = getSession()

  return (
    <header className="fixed top-0 right-0 z-20 h-16 bg-surface-bright border-b border-outline-variant flex justify-between items-center px-gutter w-full md:w-[calc(100%-260px)]">
      <div className="flex items-center gap-4 min-w-0">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="md:hidden text-on-surface-variant hover:text-primary transition-colors -ml-1 p-1"
          aria-label="Abrir menú"
        >
          <Icon name="menu" />
        </button>
        <div className="hidden sm:block w-full max-w-md">
          <div className="relative">
            <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-on-surface-variant">
              <Icon name="search" size="18px" />
            </span>
            <input
              type="text"
              placeholder="Búsqueda rápida..."
              className="w-full h-10 pl-10 pr-4 bg-surface-container-low border border-outline-variant rounded-full font-body-md text-body-md text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all"
            />
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button
          type="button"
          className="text-on-surface-variant hover:text-primary transition-colors p-1 relative cursor-pointer"
          aria-label="Notificaciones"
        >
          <Icon name="notifications" />
          <span className="absolute top-0 right-0 w-2 h-2 bg-error rounded-full border border-surface-bright" />
        </button>
        <button
          type="button"
          className="text-on-surface-variant hover:text-primary transition-colors p-1 cursor-pointer"
          aria-label="Configuración"
        >
          <Icon name="settings" />
        </button>
        <div className="w-8 h-8 rounded-full bg-surface-container-high flex items-center justify-center text-primary font-bold text-xs uppercase border border-outline-variant">
          {user?.iniciales ?? 'U'}
        </div>
      </div>
    </header>
  )
}
