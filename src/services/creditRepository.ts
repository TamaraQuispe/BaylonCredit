import { useSyncExternalStore } from 'react'
import { fiados as seedFiados, type Fiado } from '@/data/fiados'
import type { Cliente } from '@/data/clientes'
import { paymentRecords, type PaymentRecord } from '@/data/pagos'
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

const STORAGE_KEY = 'baylon_credit_state_v1'
const listeners = new Set<() => void>()

function seedState(): CreditState {
  return {
    credits: seedFiados.map((credit) => ({
      ...credit,
      timeline: [
        {
          id: `${credit.id}-registered`,
          title: 'Fiado registrado',
          description: 'Crédito inicial aprobado.',
          amount: credit.originalAmount,
          date: credit.createdAt,
          type: 'registered',
        },
        ...(credit.paidAmount > 0
          ? [
              {
                id: `${credit.id}-payment`,
                title: credit.status === 'pagado' ? 'Pago completado' : 'Pago parcial',
                description: 'Pago registrado en el historial.',
                amount: -credit.paidAmount,
                date: credit.dueAt,
                type: 'payment' as const,
              },
            ]
          : []),
        ...(credit.pendingAmount > 0
          ? [
              {
                id: `${credit.id}-pending`,
                title: 'Saldo pendiente',
                description: 'Pendiente de cancelación.',
                amount: credit.pendingAmount,
                date: 'Restante',
                type: 'pending' as const,
              },
            ]
          : []),
      ],
    })),
    payments: paymentRecords.map((payment) => ({
      ...payment,
      creditIds: [],
      paymentDate: payment.paidAt,
      method: 'No especificado',
    })),
  }
}

function loadState(): CreditState {
  if (typeof window === 'undefined') return seedState()
  const saved = window.localStorage.getItem(STORAGE_KEY)
  if (!saved) return seedState()
  try {
    const parsed = JSON.parse(saved) as Partial<CreditState>
    const seed = seedState()
    return {
      credits: parsed.credits ?? seed.credits,
      payments: parsed.payments ?? seed.payments,
    }
  } catch {
    return seedState()
  }
}

let state = loadState()

function persist(nextState: CreditState) {
  state = nextState
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(nextState))
  listeners.forEach((listener) => listener())
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('es-PE').format(new Date(`${value}T12:00:00`))
}

export const creditRepository = {
  subscribe(listener: () => void) {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },
  getSnapshot() {
    return state
  },
  create(input: CreateCreditInput) {
    const id = `f-${Date.now()}`
    const now = new Date()
    const due = new Date(`${input.dueDate}T12:00:00`)
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const daysToDue = Math.ceil((due.getTime() - today.getTime()) / 86_400_000)
    const status = daysToDue < 0 ? 'vencido' : daysToDue <= 5 ? 'proximo-a-vencer' : 'al-dia'
    const credit: StoredCredit = {
      id,
      code: `F-${now.getFullYear()}-${String(state.credits.length + 1).padStart(4, '0')}`,
      clientId: input.client.id,
      client: {
        initials: input.client.initials,
        name: input.client.name,
        business: input.client.business,
      },
      phone: input.client.phone,
      originalAmount: input.amount,
      pendingAmount: input.amount,
      paidAmount: 0,
      paidPercent: 0,
      createdAt: formatDate(input.creditDate),
      dueAt: formatDate(input.dueDate),
      status,
      risk: input.evaluation.risk,
      evaluation: input.evaluation,
      timeline: [
        {
          id: `${id}-registered`,
          title: 'Fiado registrado',
          description: `Crédito aprobado con score ${input.evaluation.score}.`,
          amount: input.amount,
          date: `${formatDate(input.creditDate)}, ${now.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' })}`,
          type: 'registered',
        },
        {
          id: `${id}-pending`,
          title: 'Pago completado',
          description: 'Pendiente de cancelación total.',
          amount: input.amount,
          date: 'Restante',
          type: 'pending',
        },
      ],
    }
    persist({ ...state, credits: [credit, ...state.credits] })
    return credit
  },
  applyPayment(input: ApplyPaymentInput) {
    const allocations = input.allocations.filter((allocation) => allocation.amount > 0)
    if (allocations.length === 0) throw new Error('El pago no tiene asignaciones válidas.')
    if (input.paymentDate > new Date().toISOString().slice(0, 10)) {
      throw new Error('La fecha del pago no puede estar en el futuro.')
    }

    const paymentId = `pay-${Date.now()}`
    const now = new Date()
    const allocationMap = new Map(allocations.map((allocation) => [allocation.creditId, allocation.amount]))

    for (const allocation of allocations) {
      const credit = state.credits.find((item) => item.id === allocation.creditId)
      if (!credit || credit.clientId !== input.client.id) {
        throw new Error('Uno de los fiados seleccionados no pertenece al cliente.')
      }
      if (allocation.amount > credit.pendingAmount + 0.001) {
        throw new Error(`El pago supera el saldo de ${credit.code}.`)
      }
    }

    const updatedCredits = state.credits.map((credit) => {
      const appliedAmount = allocationMap.get(credit.id)
      if (!appliedAmount) return credit

      const pendingAmount = Math.max(0, Number((credit.pendingAmount - appliedAmount).toFixed(2)))
      const paidAmount = Number((credit.paidAmount + appliedAmount).toFixed(2))
      const paidPercent = Math.min(100, Number(((paidAmount / credit.originalAmount) * 100).toFixed(1)))
      const paymentEntry: CreditTimelineEntry = {
        id: `${paymentId}-${credit.id}`,
        title: pendingAmount === 0 ? 'Pago completado' : 'Pago parcial',
        description: `${input.method}${input.reference ? ` · Ref. ${input.reference}` : ''}`,
        amount: -appliedAmount,
        date: `${formatDate(input.paymentDate)}, ${now.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' })}`,
        type: 'payment',
      }
      const timelineWithoutPending = credit.timeline.filter((entry) => entry.type !== 'pending')

      return {
        ...credit,
        pendingAmount,
        paidAmount,
        paidPercent,
        status: pendingAmount === 0 ? 'pagado' as const : credit.status,
        timeline: [
          ...timelineWithoutPending,
          paymentEntry,
          ...(pendingAmount > 0
            ? [
                {
                  id: `${credit.id}-pending-${paymentId}`,
                  title: 'Pago completado',
                  description: 'Pendiente de cancelación total.',
                  amount: pendingAmount,
                  date: 'Restante',
                  type: 'pending' as const,
                },
              ]
            : []),
        ],
      }
    })

    const appliedCredits = updatedCredits.filter((credit) => allocationMap.has(credit.id))
    const amount = Number(allocations.reduce((sum, allocation) => sum + allocation.amount, 0).toFixed(2))
    const remainingBalance = updatedCredits
      .filter((credit) => credit.clientId === input.client.id)
      .reduce((sum, credit) => sum + credit.pendingAmount, 0)
    const payment: StoredPayment = {
      id: paymentId,
      clientId: input.client.id,
      client: input.client.business,
      amount,
      creditIds: allocations.map((allocation) => allocation.creditId),
      creditCode: appliedCredits.map((credit) => credit.code).join(', '),
      creditDate: appliedCredits.map((credit) => credit.createdAt).join(', '),
      paidAt: `${formatDate(input.paymentDate)}, ${now.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' })}`,
      paymentDate: input.paymentDate,
      remainingBalance,
      registeredBy: 'Administrador',
      initials: 'AD',
      method: input.method,
      reference: input.reference,
    }

    persist({ credits: updatedCredits, payments: [payment, ...state.payments] })
    return payment
  },
}

export function useCreditState() {
  return useSyncExternalStore(
    creditRepository.subscribe,
    creditRepository.getSnapshot,
    creditRepository.getSnapshot,
  )
}
