import { endSession, getAccessToken } from '@/utils/session'

const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1').replace(/\/$/, '')

interface ApiErrorPayload {
  detail?: string
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message)
  }
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getAccessToken()
  const headers = new Headers(options.headers)
  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(`${API_URL}${path}`, { ...options, headers })
  if (!response.ok) {
    if (response.status === 401 && token) endSession()
    const payload = await response.json().catch(() => ({})) as ApiErrorPayload
    throw new ApiError(payload.detail || 'No se pudo completar la solicitud.', response.status)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export interface AuthUser {
  id: string
  email: string
  full_name: string
  role: 'admin' | 'operator' | 'viewer'
  is_active: boolean
}

interface LoginResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  user: AuthUser
}

export function login(email: string, password: string) {
  const body = new URLSearchParams({ username: email, password })
  return apiRequest<LoginResponse>('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
}
