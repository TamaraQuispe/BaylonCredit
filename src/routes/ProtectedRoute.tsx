import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { getSession } from '@/utils/session'
import { MANAGEMENT_ROUTES } from '@/components/layout/Sidebar'

interface ProtectedRouteProps {
  adminOnly?: boolean
}

export default function ProtectedRoute({ adminOnly = false }: ProtectedRouteProps) {
  const session = getSession()
  const location = useLocation()
  if (!session) {
    return <Navigate to="/iniciar-sesion" replace state={{ from: location }} />
  }
  const isPasswordChange = location.pathname === '/cambiar-contrasena'
  if (session.mustChangePassword && !isPasswordChange) {
    return <Navigate to="/cambiar-contrasena" replace />
  }
  if (adminOnly && session.rol !== 'admin') {
    return <Navigate to="/inicio" replace />
  }
  if (session.rol === 'operator' && MANAGEMENT_ROUTES.has(location.pathname)) {
    return <Navigate to="/inicio" replace />
  }
  return <Outlet />
}