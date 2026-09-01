import { useEffect, useSyncExternalStore } from 'react'
import type { Cliente } from '@/data/clientes'
import { apiRequest } from './apiClient'

export interface StoredClient extends Cliente {
  address?: string
  registeredAt: string
  hasEvaluation: boolean
}

interface ClientState {
  clients: StoredClient[]
  loading: boolean
  loaded: boolean
  error?: string
}

export interface CreateClientInput {
  firstName: string
  lastName: string
  business?: string
  document: string
  phone: string
  address?: string
}

interface ApiClient {
  id: string
  first_name: string
  last_name: string
  business_name?: string
  document: string
  phone: string
  address?: string
  created_at: string
}

const listeners = new Set<() => void>()
let state: ClientState = { clients: [], loading: false, loaded: false }
let loadingPromise: Promise<StoredClient[]> | null = null

function emit(nextState: ClientState) {
  state = nextState
  listeners.forEach((listener) => listener())
}

function mapClient(client: ApiClient): StoredClient {
  const name = `${client.first_name} ${client.last_name}`.trim()
  return {
    id: client.id,
    initials: `${client.first_name[0] ?? ''}${client.last_name[0] ?? ''}`.toUpperCase(),
    business: client.business_name || name,
    name,
    document: client.document,
    phone: client.phone,
    address: client.address,
    registeredAt: new Intl.DateTimeFormat('es-PE').format(new Date(client.created_at)),
    purchases: 0,
    debt: 0,
    status: 'sin-deuda',
    risk: 'medio',
    hasEvaluation: false,
  }
}

export const clientRepository = {
  subscribe(listener: () => void) {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },
  getSnapshot() {
    return state
  },
  async load(force = false) {
    if (state.loaded && !force) return state.clients
    if (loadingPromise) return loadingPromise
    emit({ ...state, loading: true, error: undefined })
    loadingPromise = apiRequest<ApiClient[]>('/clients')
      .then((clients) => {
        const mapped = clients.map(mapClient)
        emit({ clients: mapped, loading: false, loaded: true })
        return mapped
      })
      .catch((error: unknown) => {
        emit({ ...state, loading: false, error: error instanceof Error ? error.message : 'No se pudieron cargar los clientes.' })
        throw error
      })
      .finally(() => {
        loadingPromise = null
      })
    return loadingPromise
  },
  async create(input: CreateClientInput) {
    const created = await apiRequest<ApiClient>('/clients', {
      method: 'POST',
      body: JSON.stringify({
        first_name: input.firstName.trim(),
        last_name: input.lastName.trim(),
        business_name: input.business?.trim() || null,
        document: input.document.trim(),
        phone: input.phone.trim(),
        address: input.address?.trim() || null,
      }),
    })
    const client = mapClient(created)
    emit({ ...state, clients: [client, ...state.clients], loaded: true })
    return client
  },
}

export function useClientState() {
  const snapshot = useSyncExternalStore(
    clientRepository.subscribe,
    clientRepository.getSnapshot,
    clientRepository.getSnapshot,
  )
  useEffect(() => {
    void clientRepository.load().catch(() => undefined)
  }, [])
  return snapshot
}
