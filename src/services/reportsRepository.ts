import { useEffect, useSyncExternalStore } from 'react'
import { apiRequest } from './apiClient'

export interface PortfolioClient {
  clientId: string
  clientName: string
  businessName?: string | null
  totalPending: number
  totalOverdue: number
  activeCredits: number
  overdueCredits: number
  earliestDue?: string | null
}

export interface PortfolioSummary {
  totalPending: number
  totalOverdue: number
  totalRecovered: number
  delinquencyRate: number
  activeCredits: number
  overdueCredits: number
  dueSoonCredits: number
  paidCredits: number
  generatedAt: string
}

export interface PortfolioReport {
  summary: PortfolioSummary
  clients: PortfolioClient[]
}

interface ApiPortfolioClient {
  client_id: string
  client_name: string
  business_name?: string | null
  total_pending: string | number
  total_overdue: string | number
  active_credits: number
  overdue_credits: number
  earliest_due?: string | null
}

interface ApiPortfolioReport {
  summary: {
    total_pending: string | number
    total_overdue: string | number
    total_recovered: string | number
    delinquency_rate: number
    active_credits: number
    overdue_credits: number
    due_soon_credits: number
    paid_credits: number
    generated_at: string
  }
  clients: ApiPortfolioClient[]
}

interface ReportsState {
  report: PortfolioReport | null
  loading: boolean
  loaded: boolean
  error?: string
}

const listeners = new Set<() => void>()
let state: ReportsState = { report: null, loading: false, loaded: false }
let loadPromise: Promise<PortfolioReport> | null = null

function toNumber(value: string | number) {
  return typeof value === 'number' ? value : Number(value)
}

function mapClient(c: ApiPortfolioClient): PortfolioClient {
  return {
    clientId: c.client_id,
    clientName: c.client_name,
    businessName: c.business_name,
    totalPending: toNumber(c.total_pending),
    totalOverdue: toNumber(c.total_overdue),
    activeCredits: c.active_credits,
    overdueCredits: c.overdue_credits,
    earliestDue: c.earliest_due,
  }
}

function mapReport(report: ApiPortfolioReport): PortfolioReport {
  return {
    summary: {
      totalPending: toNumber(report.summary.total_pending),
      totalOverdue: toNumber(report.summary.total_overdue),
      totalRecovered: toNumber(report.summary.total_recovered),
      delinquencyRate: report.summary.delinquency_rate,
      activeCredits: report.summary.active_credits,
      overdueCredits: report.summary.overdue_credits,
      dueSoonCredits: report.summary.due_soon_credits,
      paidCredits: report.summary.paid_credits,
      generatedAt: report.summary.generated_at,
    },
    clients: report.clients.map(mapClient),
  }
}

function emit(next: ReportsState) {
  state = next
  listeners.forEach((listener) => listener())
}

export const reportsRepository = {
  subscribe(listener: () => void) {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },
  getSnapshot() {
    return state
  },
  async load(force = false) {
    if (state.loaded && !force) return state.report
    if (loadPromise) return loadPromise
    emit({ ...state, loading: true, error: undefined })
    loadPromise = apiRequest<ApiPortfolioReport>('/reports/portfolio')
      .then((report) => {
        const mapped = mapReport(report)
        emit({ report: mapped, loading: false, loaded: true })
        return mapped
      })
      .catch((error: unknown) => {
        emit({
          ...state,
          loading: false,
          error: error instanceof Error ? error.message : 'No se pudo cargar el reporte.',
        })
        throw error
      })
      .finally(() => {
        loadPromise = null
      })
    return loadPromise
  },
}

export function useReportsState() {
  const snapshot = useSyncExternalStore(
    reportsRepository.subscribe,
    reportsRepository.getSnapshot,
    reportsRepository.getSnapshot,
  )
  useEffect(() => {
    void reportsRepository.load().catch(() => undefined)
  }, [])
  return snapshot
}