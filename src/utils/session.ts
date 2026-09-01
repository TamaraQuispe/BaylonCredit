import type { AuthUser } from '@/services/apiClient'

const SESSION_KEY = 'baylon_auth_session'

export interface SessionUser {
  nombre: string
  correo: string
  iniciales: string
  rol: AuthUser['role']
}

interface StoredSession {
  accessToken: string
  user: SessionUser
}

function getStorageWithSession() {
  if (localStorage.getItem(SESSION_KEY)) return localStorage
  if (sessionStorage.getItem(SESSION_KEY)) return sessionStorage
  return null
}

function isExpired(token: string) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))) as { exp?: number }
    return !payload.exp || payload.exp * 1000 <= Date.now()
  } catch {
    return true
  }
}

function readSession(): StoredSession | null {
  const storage = getStorageWithSession()
  const saved = storage?.getItem(SESSION_KEY)
  if (!saved) return null
  try {
    const session = JSON.parse(saved) as StoredSession
    if (isExpired(session.accessToken)) {
      endSession()
      return null
    }
    return session
  } catch {
    endSession()
    return null
  }
}

export function getSession(): SessionUser | null {
  return readSession()?.user ?? null
}

export function getAccessToken(): string | null {
  return readSession()?.accessToken ?? null
}

export function startSession(accessToken: string, user: AuthUser, remember: boolean): void {
  endSession()
  const names = user.full_name.trim().split(/\s+/)
  const initials = `${names[0]?.[0] ?? ''}${names[1]?.[0] ?? ''}`.toUpperCase()
  const session: StoredSession = {
    accessToken,
    user: {
      nombre: user.full_name,
      correo: user.email,
      iniciales: initials || 'US',
      rol: user.role,
    },
  }
  const storage = remember ? localStorage : sessionStorage
  storage.setItem(SESSION_KEY, JSON.stringify(session))
}

export function endSession(): void {
  localStorage.removeItem(SESSION_KEY)
  sessionStorage.removeItem(SESSION_KEY)
}
