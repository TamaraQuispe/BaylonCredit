import { useSyncExternalStore } from 'react'
import type { Product } from '@/data/products'

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
}

export interface CreateSaleInput {
  paymentMode: SalePaymentMode
  clientId?: string
  clientName?: string
  creditId?: string
  items: Array<{ product: Product; quantity: number }>
  subtotal: number
  tax: number
  total: number
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

const STORAGE_KEY = 'baylon_sales_state_v1'
const listeners = new Set<() => void>()

function loadState(): SalesState {
  if (typeof window === 'undefined') return { sales: [] }
  const saved = window.localStorage.getItem(STORAGE_KEY)
  if (!saved) return { sales: [] }
  try {
    const parsed = JSON.parse(saved) as Partial<SalesState>
    return { sales: parsed.sales ?? [] }
  } catch {
    return { sales: [] }
  }
}

let state = loadState()

function persist(nextState: SalesState) {
  state = nextState
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(nextState))
  listeners.forEach((listener) => listener())
}

export function getAvailableStock(product: Product, sales: StoredSale[]) {
  const sold = sales.reduce(
    (total, sale) => total + (sale.items.find((item) => item.productId === product.id)?.quantity ?? 0),
    0,
  )
  return Math.max(0, product.stock - sold)
}

function validateSale(input: CreateSaleInput) {
  if (input.items.length === 0 || input.total <= 0) throw new Error('Agrega al menos un producto a la venta.')
  if (input.paymentMode === 'fiado' && !input.clientId) throw new Error('Selecciona el cliente para la venta fiada.')
  input.items.forEach(({ product, quantity }) => {
    if (!Number.isInteger(quantity) || quantity <= 0) throw new Error('La cantidad de productos no es válida.')
    if (quantity > getAvailableStock(product, state.sales)) {
      throw new Error(`No hay stock suficiente de ${product.name}.`)
    }
  })
}

export const salesRepository = {
  subscribe(listener: () => void) {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },
  getSnapshot() {
    return state
  },
  validate(input: CreateSaleInput) {
    validateSale(input)
  },
  create(input: CreateSaleInput) {
    validateSale(input)
    const now = new Date()
    const sale: StoredSale = {
      id: `sale-${Date.now()}`,
      code: `V-${now.getFullYear()}-${String(state.sales.length + 1).padStart(5, '0')}`,
      createdAt: now.toISOString(),
      paymentMode: input.paymentMode,
      clientId: input.clientId,
      clientName: input.clientName,
      creditId: input.creditId,
      subtotal: Number(input.subtotal.toFixed(2)),
      tax: Number(input.tax.toFixed(2)),
      total: Number(input.total.toFixed(2)),
      items: input.items.map(({ product, quantity }) => ({
        productId: product.id,
        name: product.name,
        category: product.category,
        unitPrice: product.price,
        quantity,
        total: Number((product.price * quantity).toFixed(2)),
      })),
    }
    persist({ sales: [sale, ...state.sales] })
    return sale
  },
}

export function useSalesState() {
  return useSyncExternalStore(
    salesRepository.subscribe,
    salesRepository.getSnapshot,
    salesRepository.getSnapshot,
  )
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

function saleDate(sale: StoredSale) {
  return new Date(sale.createdAt)
}

function selectPeriodSales(sales: StoredSale[], start: Date, end: Date) {
  return sales.filter((sale) => {
    const date = saleDate(sale)
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
    const date = saleDate(sale)
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

export function selectSalesMetrics(
  sales: StoredSale[],
  period: SalesPeriod,
  now = new Date(),
): SalesMetrics {
  const currentStart = periodStart(period, now)
  const currentEnd = new Date(now)
  currentEnd.setMilliseconds(currentEnd.getMilliseconds() + 1)
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
      category: item.category,
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
