import { useSyncExternalStore } from 'react'
import { fiados as seedFiados, type Fiado } from '@/data/fiados'
import type { Cliente } from '@/data/clientes'
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

interface CreditState {
  credits: StoredCredit[]
}

export interface CreateCreditInput {
  client: Cliente
  amount: number
  creditDate: string
  dueDate: string
  evaluation: CreditEvaluation
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
  }
}

function loadState(): CreditState {
  if (typeof window === 'undefined') return seedState()
  const saved = window.localStorage.getItem(STORAGE_KEY)
  if (!saved) return seedState()
  try {
    return JSON.parse(saved) as CreditState
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
    persist({ credits: [credit, ...state.credits] })
    return credit
  },
}

export function useCreditState() {
  return useSyncExternalStore(
    creditRepository.subscribe,
    creditRepository.getSnapshot,
    creditRepository.getSnapshot,
  )
}
