import { useEffect, useSyncExternalStore } from 'react'
import { apiRequest } from './apiClient'

export type UserRole = 'admin' | 'operator' | 'viewer'

export interface UserRecord {
  id: string
  fullName: string
  email: string
  role: UserRole
  isActive: boolean
  createdAt: string
  lastLoginAt?: string | null
  position?: string | null
  phone?: string | null
  mustChangePassword: boolean
}

export interface AuditRecord {
  id: string
  actorEmail?: string | null
  action: string
  entityType: string
  entityId?: string | null
  ipAddress?: string | null
  description?: string | null
  createdAt: string
}

export interface CreateUserInput {
  email: string
  fullName: string
  password: string
  role: UserRole
  position?: string | null
  phone?: string | null
}

export interface UpdateUserInput {
  fullName?: string
  role?: UserRole
  position?: string | null
  phone?: string | null
}

interface ApiUser {
  id: string
  email: string
  full_name: string
  position?: string | null
  phone?: string | null
  role: UserRole
  is_active: boolean
  created_at: string
  last_login_at?: string | null
  must_change_password: boolean
}

interface ApiAuditLog {
  id: string
  actor_email?: string | null
  action: string
  entity_type: string
  entity_id?: string | null
  ip_address?: string | null
  details?: unknown
  description?: string | null
  created_at: string
}

interface UserState {
  users: UserRecord[]
  loading: boolean
  loaded: boolean
  error?: string
}

interface AuditState {
  logs: AuditRecord[]
  loading: boolean
  loaded: boolean
  error?: string
}

const userListeners = new Set<() => void>()
const auditListeners = new Set<() => void>()
let userState: UserState = { users: [], loading: false, loaded: false }
let auditState: AuditState = { logs: [], loading: false, loaded: false }
let loadPromise: Promise<UserRecord[]> | null = null
let auditPromise: Promise<AuditRecord[]> | null = null

function emitUser(nextState: UserState) {
  userState = nextState
  userListeners.forEach((listener) => listener())
}

function emitAudit(nextState: AuditState) {
  auditState = nextState
  auditListeners.forEach((listener) => listener())
}

function mapUser(user: ApiUser): UserRecord {
  return {
    id: user.id,
    fullName: user.full_name,
    email: user.email,
    role: user.role,
    isActive: user.is_active,
    createdAt: user.created_at,
    lastLoginAt: user.last_login_at,
    position: user.position,
    phone: user.phone,
    mustChangePassword: user.must_change_password,
  }
}

function mapAudit(log: ApiAuditLog): AuditRecord {
  return {
    id: log.id,
    actorEmail: log.actor_email,
    action: log.action,
    entityType: log.entity_type,
    entityId: log.entity_id,
    ipAddress: log.ip_address,
    description: log.description,
    createdAt: log.created_at,
  }
}

export const userRepository = {
  subscribe(listener: () => void) {
    userListeners.add(listener)
    return () => userListeners.delete(listener)
  },
  getSnapshot() {
    return userState
  },
  async load(force = false) {
    if (userState.loaded && !force) return userState.users
    if (loadPromise) return loadPromise
    emitUser({ ...userState, loading: true, error: undefined })
    loadPromise = apiRequest<ApiUser[]>('/users')
      .then((users) => {
        const mapped = users.map(mapUser)
        emitUser({ users: mapped, loading: false, loaded: true })
        return mapped
      })
      .catch((error: unknown) => {
        emitUser({ ...userState, loading: false, error: error instanceof Error ? error.message : 'No se pudieron cargar los usuarios.' })
        throw error
      })
      .finally(() => {
        loadPromise = null
      })
    return loadPromise
  },
  async create(input: CreateUserInput) {
    const created = await apiRequest<ApiUser>('/users', {
      method: 'POST',
      body: JSON.stringify({
        email: input.email.trim(),
        full_name: input.fullName.trim(),
        password: input.password,
        role: input.role,
        position: input.position?.trim() || null,
        phone: input.phone?.trim() || null,
      }),
    })
    const user = mapUser(created)
    emitUser({ ...userState, users: [user, ...userState.users], loaded: true })
    return user
  },
  async update(id: string, input: UpdateUserInput) {
    const updated = await apiRequest<ApiUser>(`/users/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({
        full_name: input.fullName,
        role: input.role,
        position: input.position,
        phone: input.phone,
      }),
    })
    const user = mapUser(updated)
    emitUser({ ...userState, users: userState.users.map((item) => (item.id === id ? user : item)) })
    return user
  },
  async setStatus(id: string, active: boolean) {
    const updated = await apiRequest<ApiUser>(`/users/${id}/status?active=${active}`, {
      method: 'PATCH',
    })
    const user = mapUser(updated)
    emitUser({ ...userState, users: userState.users.map((item) => (item.id === id ? user : item)) })
    return user
  },
}

export function useUserState() {
  const snapshot = useSyncExternalStore(
    userRepository.subscribe,
    userRepository.getSnapshot,
    userRepository.getSnapshot,
  )
  useEffect(() => {
    void userRepository.load().catch(() => undefined)
  }, [])
  return snapshot
}

export const auditRepository = {
  subscribe(listener: () => void) {
    auditListeners.add(listener)
    return () => auditListeners.delete(listener)
  },
  getSnapshot() {
    return auditState
  },
  async load(force = false) {
    if (auditState.loaded && !force) return auditState.logs
    if (auditPromise) return auditPromise
    emitAudit({ ...auditState, loading: true, error: undefined })
    auditPromise = apiRequest<ApiAuditLog[]>('/users/audit')
      .then((logs) => {
        const mapped = logs.map(mapAudit)
        emitAudit({ logs: mapped, loading: false, loaded: true })
        return mapped
      })
      .catch((error: unknown) => {
        emitAudit({ ...auditState, loading: false, error: error instanceof Error ? error.message : 'No se pudieron cargar los registros de auditoría.' })
        throw error
      })
      .finally(() => {
        auditPromise = null
      })
    return auditPromise
  },
}

export function useAuditState() {
  const snapshot = useSyncExternalStore(
    auditRepository.subscribe,
    auditRepository.getSnapshot,
    auditRepository.getSnapshot,
  )
  useEffect(() => {
    void auditRepository.load().catch(() => undefined)
  }, [])
  return snapshot
}