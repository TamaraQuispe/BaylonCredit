import { useEffect, useSyncExternalStore } from 'react'
import { apiRequest } from './apiClient'

export type SalePaymentMode = 'contado' | 'fiado'
export type SalesPeriod = 'hoy' | 'semana' | 'mes'

export interface SaleLine {
  productId: string
  name: string
  category: string
  unitPrice: number
  quantity: number
  total: number
}

export interface StoredSale {
  id: string
  code: string
  createdAt: string
  paymentMode: SalePaymentMode
  clientId?: string
  clientName?: string
  creditId?: string
  subtotal: number
  tax: number
  total: number
  items: SaleLine[]
}

interface SalesState {
  sales: StoredSale[]
  loading: boolean
  loaded: boolean
  error?: string
}

interface ApiSale {
  id: string
  code: string
  created_at: string
  payment_mode: SalePaymentMode
  client_id?: string
  client_name?: string
  subtotal: string | number
  tax: string | number
  total: string | number
  items: Array<{
    product_id: string
    product_name: string
    product_category: string
    unit_price: string | number
    quantity: number
    line_subtotal: string | number
  }>
  credit?: { id: string }
}

export interface CreateSaleInput {
  paymentMode: SalePaymentMode
  clientId?: string
  dueDate?: string
  items: Array<{ productId: string; quantity: number }>
}

export interface SalesMetrics {
  total: number
  cash: number
  credit: number
  count: number
  trend: number
  bars: Array<{ label: string; cash: number; credit: number }>
  topProducts: Array<{ name: string; category: string; quantity: number; revenue: number }>
}

const listeners = new Set<() => void>()
let state: SalesState = { sales: [], loading: false, loaded: false }
let loadingPromise: Promise<StoredSale[]> | null = null

function emit(nextState: SalesState) {
  state = nextState
  listeners.forEach((listener) => listener())
}

function mapSale(sale: ApiSale): StoredSale {
  return {
    id: sale.id,
    code: sale.code,
    createdAt: sale.created_at,
    paymentMode: sale.payment_mode,
    clientId: sale.client_id,
    clientName: sale.client_name,
    creditId: sale.credit?.id,
    subtotal: Number(sale.subtotal),
    tax: Number(sale.tax),
    total: Number(sale.total),
    items: sale.items.map((item) => ({
      productId: item.product_id,
      name: item.product_name,
      category: item.product_category,
      unitPrice: Number(item.unit_price),
      quantity: item.quantity,
      total: Number(item.line_subtotal),
    })),
  }
}

export const salesRepository = {
  subscribe(listener: () => void) {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },
  getSnapshot() {
    return state
  },
  async load(force = false) {
    if (state.loaded && !force) return state.sales
    if (loadingPromise) return loadingPromise
    emit({ ...state, loading: true, error: undefined })
    loadingPromise = apiRequest<ApiSale[]>('/sales')
      .then((sales) => {
        const mapped = sales.map(mapSale)
        emit({ sales: mapped, loading: false, loaded: true })
        return mapped
      })
      .catch((error: unknown) => {
        emit({ ...state, loading: false, error: error instanceof Error ? error.message : 'No se pudieron cargar las ventas.' })
        throw error
      })
      .finally(() => {
        loadingPromise = null
      })
    return loadingPromise
  },
  async create(input: CreateSaleInput) {
    const sale = mapSale(await apiRequest<ApiSale>('/sales', {
      method: 'POST',
      body: JSON.stringify({
        payment_mode: input.paymentMode,
        client_id: input.clientId || null,
        due_date: input.dueDate || null,
        items: input.items.map((item) => ({ product_id: item.productId, quantity: item.quantity })),
      }),
    }))
    emit({ ...state, sales: [sale, ...state.sales], loaded: true })
    return sale
  },
}

export function useSalesState() {
  const snapshot = useSyncExternalStore(
    salesRepository.subscribe,
    salesRepository.getSnapshot,
    salesRepository.getSnapshot,
  )
  useEffect(() => {
    void salesRepository.load().catch(() => undefined)
  }, [])
  return snapshot
}

function periodStart(period: SalesPeriod, date: Date) {
  const start = new Date(date)
  start.setHours(0, 0, 0, 0)
  if (period === 'semana') {
    const day = start.getDay() || 7
    start.setDate(start.getDate() - day + 1)
  } else if (period === 'mes') {
    start.setDate(1)
  }
  return start
}

function previousPeriodStart(period: SalesPeriod, currentStart: Date) {
  const start = new Date(currentStart)
  if (period === 'hoy') start.setDate(start.getDate() - 1)
  else if (period === 'semana') start.setDate(start.getDate() - 7)
  else start.setMonth(start.getMonth() - 1)
  return start
}

function selectPeriodSales(sales: StoredSale[], start: Date, end: Date) {
  return sales.filter((sale) => {
    const date = new Date(sale.createdAt)
    return date >= start && date < end
  })
}

function buildBars(sales: StoredSale[], period: SalesPeriod) {
  const labels = period === 'hoy'
    ? ['00h', '04h', '08h', '12h', '16h', '20h']
    : period === 'semana'
      ? ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
      : ['Sem 1', 'Sem 2', 'Sem 3', 'Sem 4', 'Sem 5']
  const values = labels.map((label) => ({ label, cash: 0, credit: 0 }))
  sales.forEach((sale) => {
    const date = new Date(sale.createdAt)
    const index = period === 'hoy'
      ? Math.floor(date.getHours() / 4)
      : period === 'semana'
        ? (date.getDay() || 7) - 1
        : Math.min(4, Math.floor((date.getDate() - 1) / 7))
    if (sale.paymentMode === 'contado') values[index].cash += sale.total
    else values[index].credit += sale.total
  })
  const maximum = Math.max(0, ...values.flatMap((value) => [value.cash, value.credit]))
  if (maximum === 0) return values
  return values.map((value) => ({
    label: value.label,
    cash: Number(((value.cash / maximum) * 100).toFixed(1)),
    credit: Number(((value.credit / maximum) * 100).toFixed(1)),
  }))
}

export function selectSalesMetrics(sales: StoredSale[], period: SalesPeriod, now = new Date()): SalesMetrics {
  const currentStart = periodStart(period, now)
  const currentEnd = new Date(now.getTime() + 1)
  const previousStart = previousPeriodStart(period, currentStart)
  const current = selectPeriodSales(sales, currentStart, currentEnd)
  const previous = selectPeriodSales(sales, previousStart, currentStart)
  const total = current.reduce((sum, sale) => sum + sale.total, 0)
  const previousTotal = previous.reduce((sum, sale) => sum + sale.total, 0)
  const products = new Map<string, SalesMetrics['topProducts'][number]>()
  current.forEach((sale) => sale.items.forEach((item) => {
    const existing = products.get(item.productId)
    products.set(item.productId, {
      name: item.name,
      category: item.category || 'Sin categoría',
      quantity: (existing?.quantity ?? 0) + item.quantity,
      revenue: Number(((existing?.revenue ?? 0) + item.total).toFixed(2)),
    })
  }))
  return {
    total,
    cash: current.filter((sale) => sale.paymentMode === 'contado').reduce((sum, sale) => sum + sale.total, 0),
    credit: current.filter((sale) => sale.paymentMode === 'fiado').reduce((sum, sale) => sum + sale.total, 0),
    count: current.length,
    trend: previousTotal > 0 ? Number((((total - previousTotal) / previousTotal) * 100).toFixed(1)) : 0,
    bars: buildBars(current, period),
    topProducts: [...products.values()].sort((a, b) => b.quantity - a.quantity || b.revenue - a.revenue).slice(0, 5),
  }
}
