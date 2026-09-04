import { useEffect, useSyncExternalStore } from 'react'
import type { Product } from '@/data/products'
import { apiRequest } from './apiClient'

export interface CommerceProduct extends Product {
  sku: string
  unitCost: number
  minimumStock: number
  isActive: boolean
}

interface ApiProduct {
  id: string
  sku: string
  name: string
  category: string
  icon: string
  image_url: string | null
  price: string | number
  unit_cost: string | number
  stock: number
  minimum_stock: number
  is_active: boolean
}

interface ProductState {
  products: CommerceProduct[]
  loading: boolean
  loaded: boolean
  error?: string
}

export interface SaveProductInput {
  sku?: string
  name: string
  category: string
  icon: string
  imageUrl?: string | null
  price: number
  unitCost?: number
  stock: number
  minimumStock?: number
}

const listeners = new Set<() => void>()
let state: ProductState = { products: [], loading: false, loaded: false }
let loadingPromise: Promise<CommerceProduct[]> | null = null

function emit(nextState: ProductState) {
  state = nextState
  listeners.forEach((listener) => listener())
}

function mapProduct(product: ApiProduct): CommerceProduct {
  return {
    id: product.id,
    sku: product.sku,
    name: product.name,
    category: product.category,
    icon: product.icon,
    imageUrl: product.image_url,
    price: Number(product.price),
    unitCost: Number(product.unit_cost),
    stock: product.stock,
    minimumStock: product.minimum_stock,
    isActive: product.is_active,
  }
}

export const productRepository = {
  subscribe(listener: () => void) {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },
  getSnapshot() {
    return state
  },
  async load(force = false) {
    if (state.loaded && !force) return state.products
    if (loadingPromise) return loadingPromise
    emit({ ...state, loading: true, error: undefined })
    loadingPromise = apiRequest<ApiProduct[]>('/products')
      .then((products) => {
        const mapped = products.map(mapProduct)
        emit({ products: mapped, loading: false, loaded: true })
        return mapped
      })
      .catch((error: unknown) => {
        emit({ ...state, loading: false, error: error instanceof Error ? error.message : 'No se pudieron cargar los productos.' })
        throw error
      })
      .finally(() => {
        loadingPromise = null
      })
    return loadingPromise
  },
  async create(input: SaveProductInput) {
    const product = mapProduct(await apiRequest<ApiProduct>('/products', {
      method: 'POST',
      body: JSON.stringify({
        sku: input.sku || `P-${Date.now().toString().slice(-8)}`,
        name: input.name,
        category: input.category,
        icon: input.icon,
        image_url: input.imageUrl || null,
        price: input.price,
        unit_cost: input.unitCost ?? 0,
        stock: input.stock,
        minimum_stock: input.minimumStock ?? 10,
      }),
    }))
    emit({ ...state, products: [product, ...state.products], loaded: true })
    return product
  },
  async update(id: string, input: SaveProductInput) {
    const current = state.products.find((product) => product.id === id)
    const updated = mapProduct(await apiRequest<ApiProduct>(`/products/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({
        name: input.name,
        category: input.category,
        icon: input.icon,
        image_url: input.imageUrl || null,
        price: input.price,
        unit_cost: input.unitCost ?? current?.unitCost ?? 0,
        minimum_stock: input.minimumStock ?? current?.minimumStock ?? 10,
      }),
    }))
    let finalProduct = updated
    if (current && input.stock !== current.stock) {
      finalProduct = await this.changeStock(id, 'ajuste', input.stock)
    }
    emit({ ...state, products: state.products.map((product) => product.id === id ? finalProduct : product) })
    return finalProduct
  },
  async changeStock(id: string, movementType: 'entrada' | 'ajuste', quantity: number) {
    const product = mapProduct(await apiRequest<ApiProduct>(`/products/${id}/stock`, {
      method: 'POST',
      body: JSON.stringify({ movement_type: movementType, quantity }),
    }))
    emit({ ...state, products: state.products.map((item) => item.id === id ? product : item) })
    return product
  },
  async archive(id: string) {
    await apiRequest<void>(`/products/${id}`, { method: 'DELETE' })
    emit({ ...state, products: state.products.filter((product) => product.id !== id) })
  },
}

export function useProductState() {
  const snapshot = useSyncExternalStore(
    productRepository.subscribe,
    productRepository.getSnapshot,
    productRepository.getSnapshot,
  )
  useEffect(() => {
    void productRepository.load().catch(() => undefined)
  }, [])
  return snapshot
}
