const SESSION_KEY = 'baylon_demo_session'

const currentUser = {
  nombre: 'Administrador',
  correo: 'admin@baylon.com',
  iniciales: 'AD',
}

export interface DemoUser {
  nombre: string
  correo: string
  iniciales: string
}

export function getSession(): DemoUser | null {
  return localStorage.getItem(SESSION_KEY) === 'true' ? currentUser : null
}

export function startSession(): void {
  localStorage.setItem(SESSION_KEY, 'true')
}

export function endSession(): void {
  localStorage.removeItem(SESSION_KEY)
}
