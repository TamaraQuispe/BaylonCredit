import { useEffect, useSyncExternalStore } from 'react'
import { apiRequest } from './apiClient'

export interface BusinessSettings {
  businessName: string
  businessPhone: string
  businessAddress: string
  defaultCreditTermDays: number
  maxCreditAmount: string
  dueAlertsEnabled: boolean
}

interface ApiSettings {
  business_name: string
  business_phone: string
  business_address: string
  default_credit_term_days: number
  max_credit_amount: string
  due_alerts_enabled: boolean
}

export interface SettingsUpdateInput {
  businessName?: string
  businessPhone?: string
  businessAddress?: string
  defaultCreditTermDays?: number
  maxCreditAmount?: string
  dueAlertsEnabled?: boolean
}

interface SettingsState {
  settings: BusinessSettings | null
  loading: boolean
  loaded: boolean
  error?: string
}

const listeners = new Set<() => void>()
let state: SettingsState = { settings: null, loading: false, loaded: false }
let loadPromise: Promise<BusinessSettings> | null = null

function emit(nextState: SettingsState) {
  state = nextState
  listeners.forEach((listener) => listener())
}

function mapSettings(settings: ApiSettings): BusinessSettings {
  return {
    businessName: settings.business_name,
    businessPhone: settings.business_phone,
    businessAddress: settings.business_address,
    defaultCreditTermDays: settings.default_credit_term_days,
    maxCreditAmount: settings.max_credit_amount,
    dueAlertsEnabled: settings.due_alerts_enabled,
  }
}

export const settingsRepository = {
  subscribe(listener: () => void) {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },
  getSnapshot() {
    return state
  },
  async load(force = false) {
    if (state.loaded && !force) return state.settings
    if (loadPromise) return loadPromise
    emit({ ...state, loading: true, error: undefined })
    loadPromise = apiRequest<ApiSettings>('/settings')
      .then((settings) => {
        const mapped = mapSettings(settings)
        emit({ settings: mapped, loading: false, loaded: true })
        return mapped
      })
      .catch((error: unknown) => {
        emit({ ...state, loading: false, error: error instanceof Error ? error.message : 'No se pudieron cargar los parámetros.' })
        throw error
      })
      .finally(() => {
        loadPromise = null
      })
    return loadPromise
  },
  async update(input: SettingsUpdateInput) {
    const updated = await apiRequest<ApiSettings>('/settings', {
      method: 'PATCH',
      body: JSON.stringify({
        business_name: input.businessName,
        business_phone: input.businessPhone,
        business_address: input.businessAddress,
        default_credit_term_days: input.defaultCreditTermDays,
        max_credit_amount: input.maxCreditAmount,
        due_alerts_enabled: input.dueAlertsEnabled,
      }),
    })
    const settings = mapSettings(updated)
    emit({ ...state, settings, loaded: true })
    return settings
  },
}

export function useSettingsState() {
  const snapshot = useSyncExternalStore(
    settingsRepository.subscribe,
    settingsRepository.getSnapshot,
    settingsRepository.getSnapshot,
  )
  useEffect(() => {
    void settingsRepository.load().catch(() => undefined)
  }, [])
  return snapshot
}