import { Navigate, Outlet } from 'react-router-dom'
import { getSession } from '@/utils/session'

export default function ProtectedRoute() {
  const session = getSession()
  if (!session) {
    return <Navigate to="/iniciar-sesion" replace />
  }
  return <Outlet />
}
