import { NavLink } from 'react-router-dom'
import type { AuthUser } from '@/services/apiClient'
import { endSession, getSession } from '@/utils/session'
import { logout } from '@/services/apiClient'
import Icon from '@/components/ui/Icon'

const navItems = [
  { to: '/inicio', label: 'Inicio', icon: 'dashboard' },
  { to: '/ventas', label: 'Ventas', icon: 'point_of_sale' },
  { to: '/fiados', label: 'Fiados', icon: 'receipt_long' },
  { to: '/clientes', label: 'Clientes', icon: 'group' },
  { to: '/productos', label: 'Productos', icon: 'inventory_2' },
  { to: '/inventario', label: 'Inventario', icon: 'inventory' },
  { to: '/pagos', label: 'Pagos', icon: 'payments' },
  { to: '/evaluacion-crediticia', label: 'Evaluación crediticia', icon: 'psychology_alt' },
  { to: '/reportes', label: 'Reportes', icon: 'analytics' },
  { to: '/usuarios', label: 'Usuarios', icon: 'person' },
  { to: '/configuracion', label: 'Configuración', icon: 'settings' },
]

const footerItems = [
  { to: '/perfil', label: 'Perfil', icon: 'account_circle' },
]

const ADMIN_ROUTES = new Set(['/usuarios', '/configuracion'])

function canView(rol: AuthUser['role'] | undefined, to: string) {
  if (rol === 'admin') return true
  if (ADMIN_ROUTES.has(to)) return false
  if (rol === 'viewer' && to === '/ventas') return false
  return true
}

interface SidebarProps {
  open: boolean
  onClose: () => void
}

export default function Sidebar({ open, onClose }: SidebarProps) {
  const rol = getSession()?.rol
  const visibleNav = navItems.filter((item) => canView(rol, item.to))

  const baseLink =
    'flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:bg-surface-container-high transition-colors'

  const activeLink =
    'flex items-center gap-3 px-4 py-3 border-l-4 border-primary bg-surface-container-low text-primary font-semibold transition-all'

  const handleLogout = async () => {
    await logout()
    endSession()
    onClose()
    window.location.assign('/iniciar-sesion')
  }

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-30 bg-on-surface/40 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <nav
        id="sidebar"
        className={`fixed left-0 top-0 h-screen w-[260px] bg-surface-container-lowest border-r border-outline-variant shadow-sm flex flex-col justify-between py-6 z-40 transition-transform duration-300 ${
          open ? 'translate-x-0' : '-translate-x-full'
        } md:translate-x-0`}
      >
        <div className="flex flex-col h-full">
          <div className="px-6 mb-8 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center text-on-primary">
              <span className="material-symbols-outlined text-[22px]">psychology</span>
            </div>
            <div>
              <h1 className="font-h3-title text-h3-title font-bold text-primary tracking-tight">
                BaylonCredit IA
              </h1>
              <p className="font-label-sm text-label-sm text-on-surface-variant">
                Gestión de Créditos
              </p>
            </div>
          </div>

          <nav className="flex-1 overflow-y-auto w-full">
            <ul className="flex flex-col w-full font-body-md text-body-md">
              {visibleNav.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    onClick={onClose}
                    className={({ isActive }) => (isActive ? activeLink : baseLink)}
                  >
                    <Icon name={item.icon} />
                    <span>{item.label}</span>
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>

          <div className="mt-4 border-t border-outline-variant pt-4 w-full">
            <ul className="flex flex-col w-full font-body-md text-body-md">
              {footerItems.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    onClick={onClose}
                    className={({ isActive }) => (isActive ? activeLink : baseLink)}
                  >
                    <Icon name={item.icon} />
                    <span>{item.label}</span>
                  </NavLink>
                </li>
              ))}
              <li>
                <button
                  type="button"
                  onClick={handleLogout}
                  className={`${baseLink} w-full text-left`}
                >
                  <Icon name="logout" />
                  <span>Cerrar sesión</span>
                </button>
              </li>
            </ul>
          </div>
        </div>
      </nav>
    </>
  )
}
