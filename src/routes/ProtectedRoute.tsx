import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { getSession } from '@/utils/session'

interface ProtectedRouteProps {
  adminOnly?: boolean
}

export default function ProtectedRoute({ adminOnly = false }: ProtectedRouteProps) {
  const session = getSession()
  const location = useLocation()
  if (!session) {
    return <Navigate to="/iniciar-sesion" replace state={{ from: location }} />
  }
  if (adminOnly && session.rol !== 'admin') {
    return <Navigate to="/inicio" replace />
  }
  return <Outlet />
}