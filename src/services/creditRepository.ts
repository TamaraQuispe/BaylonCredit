import { useEffect, useSyncExternalStore } from 'react'
import type { Fiado } from '@/data/fiados'
import type { Cliente } from '@/data/clientes'
import type { PaymentRecord } from '@/data/pagos'
import type { RiskLevel } from '@/types'
import { apiRequest } from './apiClient'
import type { CreditEvaluation } from './scoringService'

export interface CreditTimelineEntry {
  id: string
  title: string
  description: string
  amount: number
  date: string
  type: 'registered' | 'payment' | 'pending'
}

export interface StoredCredit extends Fiado {
  clientId?: string
  phone?: string
  evaluation?: CreditEvaluation
  timeline: CreditTimelineEntry[]
}

export interface StoredPayment extends PaymentRecord {
  clientId?: string
  creditIds: string[]
  paymentDate: string
  method: string
  reference?: string
}

interface CreditState {
  credits: StoredCredit[]
  payments: StoredPayment[]
  loading: boolean
  loaded: boolean
  error?: string
}

export interface CreateCreditInput {
  client: Cliente
  amount: number
  creditDate: string
  dueDate: string
  evaluation: CreditEvaluation
}

export interface ApplyPaymentInput {
  client: Cliente
  allocations: { creditId: string; amount: number }[]
  paymentDate: string
  method: string
  reference?: string
}

interface ApiCreditPayment {
  id: string
  payment_id: string
  amount: string | number
  payment_date: string
  method: string
  reference?: string
  created_at: string
}

interface ApiCredit {
  id: string
  code: string
  client_id: string
  client_name: string
  client_business: string
  client_phone: string
  original_amount: string | number
  pending_amount: string | number
  paid_amount: string | number
  paid_percent: number
  credit_date: string
  due_date: string
  status: Fiado['status']
  risk: RiskLevel
  score: number
  recommended_limit: string | number
  created_at: string
  payments: ApiCreditPayment[]
}

interface ApiPayment {
  id: string
  client_id: string
  client_name: string
  amount: string | number
  credit_ids: string[]
  credit_codes: string[]
  credit_dates: string[]
  payment_date: string
  method: string
  reference?: string
  remaining_balance: string | number
  registered_by: string
  created_at: string
}

const listeners = new Set<() => void>()
let state: CreditState = { credits: [], payments: [], loading: false, loaded: false }
let loadingPromise: Promise<CreditState> | null = null

function emit(nextState: CreditState) {
  state = nextState
  listeners.forEach((listener) => listener())
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('es-PE').format(new Date(`${value}T12:00:00`))
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat('es-PE', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value))
}

function mapCredit(credit: ApiCredit): StoredCredit {
  const originalAmount = Number(credit.original_amount)
  const pendingAmount = Number(credit.pending_amount)
  const paymentTimeline: CreditTimelineEntry[] = credit.payments.map((payment) => ({
    id: payment.id,
    title: pendingAmount === 0 ? 'Pago completado' : 'Pago parcial',
    description: `${payment.method}${payment.reference ? ` · Ref. ${payment.reference}` : ''}`,
    amount: -Number(payment.amount),
    date: formatDateTime(payment.created_at),
    type: 'payment',
  }))
  return {
    id: credit.id,
    code: credit.code,
    clientId: credit.client_id,
    client: {
      initials: credit.client_name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase(),
      name: credit.client_name,
      business: credit.client_business,
    },
    phone: credit.client_phone,
    originalAmount,
    pendingAmount,
    paidAmount: Number(credit.paid_amount),
    paidPercent: credit.paid_percent,
    createdAt: formatDate(credit.credit_date),
    dueAt: formatDate(credit.due_date),
    status: credit.status,
    risk: credit.risk,
    evaluation: {
      score: credit.score,
      risk: credit.risk,
      defaultProbability: Math.max(2, 100 - credit.score),
      recommendedLimit: Number(credit.recommended_limit),
      approved: originalAmount <= Number(credit.recommended_limit),
      recommendation: `Límite recomendado: ${Number(credit.recommended_limit).toLocaleString('es-PE', { style: 'currency', currency: 'PEN' })}.`,
      calculatedAt: credit.created_at,
      responseTimeMs: 0,
    },
    timeline: [
      {
        id: `${credit.id}-registered`,
        title: 'Fiado registrado',
        description: `Crédito aprobado con score ${credit.score}.`,
        amount: originalAmount,
        date: formatDateTime(credit.created_at),
        type: 'registered',
      },
      ...paymentTimeline,
      ...(pendingAmount > 0
        ? [{
            id: `${credit.id}-pending`,
            title: 'Saldo pendiente',
            description: 'Pendiente de cancelación.',
            amount: pendingAmount,
            date: 'Restante',
            type: 'pending' as const,
          }]
        : []),
    ],
  }
}

function initials(name: string) {
  return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
}

function mapPayment(payment: ApiPayment): StoredPayment {
  return {
    id: payment.id,
    clientId: payment.client_id,
    client: payment.client_name,
    amount: Number(payment.amount),
    creditIds: payment.credit_ids,
    creditCode: payment.credit_codes.join(', '),
    creditDate: payment.credit_dates.map(formatDate).join(', '),
    paidAt: formatDateTime(payment.created_at),
    paymentDate: payment.payment_date,
    remainingBalance: Number(payment.remaining_balance),
    registeredBy: payment.registered_by,
    initials: initials(payment.registered_by),
    method: payment.method,
    reference: payment.reference,
  }
}

export const creditRepository = {
  subscribe(listener: () => void) {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },
  getSnapshot() {
    return state
  },
  async load(force = false) {
    if (state.loaded && !force) return state
    if (loadingPromise) return loadingPromise
    emit({ ...state, loading: true, error: undefined })
    loadingPromise = Promise.all([
      apiRequest<ApiCredit[]>('/credits'),
      apiRequest<ApiPayment[]>('/payments'),
    ]).then(([credits, payments]) => {
      const next = {
        credits: credits.map(mapCredit),
        payments: payments.map(mapPayment),
        loading: false,
        loaded: true,
      }
      emit(next)
      return next
    }).catch((error: unknown) => {
      const next = { ...state, loading: false, error: error instanceof Error ? error.message : 'No se pudo cargar la cartera.' }
      emit(next)
      throw error
    }).finally(() => {
      loadingPromise = null
    })
    return loadingPromise
  },
  async create(input: CreateCreditInput) {
    const credit = mapCredit(await apiRequest<ApiCredit>('/credits', {
      method: 'POST',
      body: JSON.stringify({
        client_id: input.client.id,
        amount: input.amount,
        credit_date: input.creditDate,
        due_date: input.dueDate,
        manual_override: !input.evaluation.approved,
      }),
    }))
    emit({ ...state, credits: [credit, ...state.credits], loaded: true })
    return credit
  },
  async applyPayment(input: ApplyPaymentInput) {
    const payment = mapPayment(await apiRequest<ApiPayment>('/payments', {
      method: 'POST',
      body: JSON.stringify({
        client_id: input.client.id,
        allocations: input.allocations.map((allocation) => ({
          credit_id: allocation.creditId,
          amount: allocation.amount,
        })),
        payment_date: input.paymentDate,
        method: input.method,
        reference: input.reference || null,
      }),
    }))
    await this.load(true)
    return payment
  },
}

export function useCreditState() {
  const snapshot = useSyncExternalStore(
    creditRepository.subscribe,
    creditRepository.getSnapshot,
    creditRepository.getSnapshot,
  )
  useEffect(() => {
    void creditRepository.load().catch(() => undefined)
  }, [])
  return snapshot
}
