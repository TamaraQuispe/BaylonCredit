import Icon from '@/components/ui/Icon'
import GlobalSearch from '@/components/ui/GlobalSearch'
import { useNavigate } from 'react-router-dom'
import { getSession } from '@/utils/session'
import type { StoredCredit } from '@/services/creditRepository'
import type { StoredClient } from '@/services/clientRepository'
import type { CommerceProduct } from '@/services/productRepository'

interface HeaderProps {
  onToggleSidebar: () => void
  notificationsOpen?: boolean
  onToggleNotifications?: () => void
  notificationCount?: number
  credits?: StoredCredit[]
  clients?: StoredClient[]
  products?: CommerceProduct[]
}

export default function Header({
  onToggleSidebar,
  notificationsOpen = false,
  onToggleNotifications,
  notificationCount = 0,
  credits = [],
  clients = [],
  products = [],
}: HeaderProps) {
  const user = getSession()
  const navigate = useNavigate()

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
          <GlobalSearch credits={credits} clients={clients} products={products} />
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={onToggleNotifications}
          aria-pressed={notificationsOpen}
          className={`text-on-surface-variant hover:text-primary transition-colors p-1 relative cursor-pointer ${notificationsOpen ? 'text-primary' : ''}`}
          aria-label="Notificaciones"
        >
          <Icon name="notifications" />
          {notificationCount > 0 && (
            <span className="absolute top-0.5 right-0.5 min-w-4 h-4 rounded-full bg-error text-on-error text-[10px] flex items-center justify-center px-1">
              {notificationCount > 9 ? '9+' : notificationCount}
            </span>
          )}
        </button>
        <button
          type="button"
          onClick={() => navigate('/configuracion')}
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