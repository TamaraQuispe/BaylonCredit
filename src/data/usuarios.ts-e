export type UserRole = 'Administrador' | 'Vendedor' | 'Supervisor'

export interface SystemUser {
  id: string
  initials: string
  name: string
  email: string
  role: UserRole
  active: boolean
  lastAccess: string
}

export const systemUsers: SystemUser[] = [
  { id: 'u1', initials: 'JP', name: 'Juan Pérez', email: 'jperez@baylon.com', role: 'Administrador', active: true, lastAccess: '24 Oct, 09:30 AM' },
  { id: 'u2', initials: 'MG', name: 'María García', email: 'mgarcia@baylon.com', role: 'Vendedor', active: true, lastAccess: '24 Oct, 08:15 AM' },
  { id: 'u3', initials: 'CL', name: 'Carlos López', email: 'clopez@baylon.com', role: 'Vendedor', active: false, lastAccess: '12 Oct, 16:45 PM' },
]
