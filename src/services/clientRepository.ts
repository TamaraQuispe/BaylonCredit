import { useSyncExternalStore } from 'react'
import { clients as seedClients, type Cliente } from '@/data/clientes'

export interface StoredClient extends Cliente {
  address?: string
  registeredAt: string
  hasEvaluation: boolean
}

interface ClientState {
  clients: StoredClient[]
}

export interface CreateClientInput {
  firstName: string
  lastName: string
  business?: string
  document: string
  phone: string
  address?: string
}

const STORAGE_KEY = 'baylon_client_state_v1'
const listeners = new Set<() => void>()

function seedState(): ClientState {
  return {
    clients: seedClients.map((client, index) => ({
      ...client,
      registeredAt: index === 0 ? '15/03/2021' : '24/10/2023',
      hasEvaluation: true,
    })),
  }
}

function loadState(): ClientState {
  if (typeof window === 'undefined') return seedState()
  const saved = window.localStorage.getItem(STORAGE_KEY)
  if (!saved) return seedState()
  try {
    const parsed = JSON.parse(saved) as Partial<ClientState>
    return { clients: parsed.clients ?? seedState().clients }
  } catch {
    return seedState()
  }
}

let state = loadState()

function persist(nextState: ClientState) {
  state = nextState
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(nextState))
  listeners.forEach((listener) => listener())
}

function makeInitials(firstName: string, lastName: string) {
  return `${firstName.trim()[0] ?? ''}${lastName.trim()[0] ?? ''}`.toUpperCase()
}

export const clientRepository = {
  subscribe(listener: () => void) {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },
  getSnapshot() {
    return state
  },
  create(input: CreateClientInput) {
    const document = input.document.trim()
    if (state.clients.some((client) => client.document === document)) {
      throw new Error('Ya existe un cliente con ese DNI o RUC.')
    }

    const name = `${input.firstName.trim()} ${input.lastName.trim()}`
    const client: StoredClient = {
      id: `c-${Date.now()}`,
      initials: makeInitials(input.firstName, input.lastName),
      business: input.business?.trim() || name,
      name,
      document,
      phone: input.phone.trim(),
      address: input.address?.trim() || undefined,
      registeredAt: new Intl.DateTimeFormat('es-PE').format(new Date()),
      purchases: 0,
      debt: 0,
      status: 'sin-deuda',
      risk: 'medio',
      hasEvaluation: false,
    }
    persist({ clients: [client, ...state.clients] })
    return client
  },
}

export function useClientState() {
  return useSyncExternalStore(
    clientRepository.subscribe,
    clientRepository.getSnapshot,
    clientRepository.getSnapshot,
  )
}
