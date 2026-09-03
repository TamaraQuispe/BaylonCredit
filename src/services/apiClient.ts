import { endSession, getAccessToken, getRefreshToken, updateSession } from '@/utils/session'

const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1').replace(/\/$/, '')

interface ApiErrorPayload {
  detail?: string | Array<{ msg?: string }>
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message)
  }
}

export interface AuthUser {
  id: string
  email: string
  full_name: string
  position?: string | null
  phone?: string | null
  role: 'admin' | 'operator' | 'viewer'
  is_active: boolean
  created_at?: string
  last_login_at?: string | null
  must_change_password: boolean
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  expires_in: number
  user: AuthUser
}

let refreshPromise: Promise<boolean> | null = null

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return false
  try {
    const response = await fetch(`${API_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!response.ok) return false
    const payload = (await response.json()) as TokenResponse
    updateSession(payload.access_token, payload.refresh_token)
    return true
  } catch {
    return false
  }
}

function beginRefresh(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = refreshAccessToken().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getAccessToken()
  const headers = new Headers(options.headers)
  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(`${API_URL}${path}`, { ...options, headers })
  if (response.status === 401 && token) {
    const refreshed = await beginRefresh()
    if (refreshed) {
      const retryHeaders = new Headers(options.headers)
      if (!(options.body instanceof FormData) && !retryHeaders.has('Content-Type')) {
        retryHeaders.set('Content-Type', 'application/json')
      }
      const refreshedToken = getAccessToken()
      if (refreshedToken) retryHeaders.set('Authorization', `Bearer ${refreshedToken}`)
      const retry = await fetch(`${API_URL}${path}`, { ...options, headers: retryHeaders })
      if (!retry.ok) throw await toApiError(retry)
      if (retry.status === 204) return undefined as T
      return retry.json() as Promise<T>
    }
    endSession()
  }
  if (!response.ok) throw await toApiError(response)
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

async function toApiError(response: Response): Promise<ApiError> {
  const payload = (await response.json().catch(() => ({}))) as ApiErrorPayload
  const detail = Array.isArray(payload.detail)
    ? payload.detail.map((item) => item.msg).filter(Boolean).join(' ')
    : payload.detail
  return new ApiError(detail || 'No se pudo completar la solicitud.', response.status)
}

export function login(email: string, password: string) {
  const body = new URLSearchParams({ username: email, password })
  return apiRequest<TokenResponse>('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
}

export function logout() {
  const refreshToken = getRefreshToken()
  const token = getAccessToken()
  const headers: HeadersInit = {}
  if (token) headers.Authorization = `Bearer ${token}`
  return apiRequest<void>('/auth/logout', {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  }).catch(() => undefined)
}

export interface ProfileUpdateInput {
  full_name?: string
  position?: string | null
  phone?: string | null
}

export function updateProfile(payload: ProfileUpdateInput) {
  return apiRequest<AuthUser>('/auth/me', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function getProfile() {
  return apiRequest<AuthUser>('/auth/me')
}

export function changePassword(currentPassword: string, newPassword: string) {
  return apiRequest<void>('/auth/change-password', {
    method: 'POST',
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  })
}

export function completeRegistration(newPassword: string) {
  return apiRequest<void>('/auth/complete-registration', {
    method: 'POST',
    body: JSON.stringify({ new_password: newPassword }),
  })
}

// ------------------------------------------------------------------ WebAuthn (FIDO2)

export interface WebauthnOptionsResponse {
  session_id: string
  options: Record<string, unknown>
}

export interface WebauthnCredentialRecord {
  id: string
  credential_id: string
  name?: string | null
  device_type: string
  created_at: string
}

export function webauthnRegistrationBegin(name?: string) {
  return apiRequest<WebauthnOptionsResponse>('/auth/webauthn/registration/begin', {
    method: 'POST',
    body: JSON.stringify({ name: name || null }),
  })
}

export function webauthnRegistrationFinish(
  sessionId: string,
  challenge: string,
  credential: unknown,
  name?: string,
) {
  return apiRequest<WebauthnCredentialRecord>('/auth/webauthn/registration/finish', {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
      challenge,
      credential,
      name: name || null,
    }),
  })
}

export function getWebauthnCredentials() {
  return apiRequest<WebauthnCredentialRecord[]>('/auth/webauthn/credentials')
}

export function deleteWebauthnCredential(credentialId: string) {
  return apiRequest<void>(`/auth/webauthn/credentials/${encodeURIComponent(credentialId)}`, {
    method: 'DELETE',
  })
}

export function webauthnAuthenticationBegin(userHandle?: string) {
  return apiRequest<WebauthnOptionsResponse>('/auth/webauthn/authentication/begin', {
    method: 'POST',
    body: JSON.stringify({ user_handle: userHandle || null }),
  })
}

export function webauthnAuthenticationFinish(
  sessionId: string,
  challenge: string,
  userHandle: string,
  credential: unknown,
) {
  return apiRequest<TokenResponse>('/auth/webauthn/authentication/finish', {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
      challenge,
      user_handle: userHandle,
      credential,
    }),
  })
}