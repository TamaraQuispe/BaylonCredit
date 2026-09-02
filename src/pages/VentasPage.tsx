import { useMemo, useState } from 'react'
import Icon from '@/components/ui/Icon'
import { productCategories } from '@/data/products'
import { useClientState } from '@/services/clientRepository'
import { productRepository, useProductState, type CommerceProduct } from '@/services/productRepository'
import { salesRepository } from '@/services/salesRepository'
import { useSettingsState } from '@/services/settingsRepository'
import { formatCurrency } from '@/utils/format'

interface CartLine {
  product: CommerceProduct
  quantity: number
}

const TAX_RATE = 0.18

function isoDate(date: Date) {
  const offset = date.getTimezoneOffset()
  return new Date(date.getTime() - offset * 60_000).toISOString().slice(0, 10)
}

export default function VentasPage() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('Todos')
  const [cart, setCart] = useState<CartLine[]>([])
  const [paymentMode, setPaymentMode] = useState<'contado' | 'fiado'>('contado')
  const [clientId, setClientId] = useState('')
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const { clients } = useClientState()
  const { products, loading: loadingProducts } = useProductState()
  const { settings } = useSettingsState()
  const client = clients.find((item) => item.id === clientId)

  const filteredProducts = useMemo(() => {
    const term = search.trim().toLowerCase()
    return products.filter((product) => {
      const matchesCategory = category === 'Todos' || product.category === category
      const matchesSearch =
        !term ||
        product.name.toLowerCase().includes(term) ||
        product.id.toLowerCase().includes(term)
      return matchesCategory && matchesSearch
    })
  }, [search, category, products])

  const addToCart = (product: CommerceProduct) => {
    const available = product.stock
    setCart((prev) => {
      const existing = prev.find((line) => line.product.id === product.id)
      if ((existing?.quantity ?? 0) >= available) {
        setError(`No hay más stock disponible de ${product.name}.`)
        return prev
      }
      setError('')
      setSuccess('')
      if (existing) {
        return prev.map((line) =>
          line.product.id === product.id
            ? { ...line, quantity: line.quantity + 1 }
            : line,
        )
      }
      return [...prev, { product, quantity: 1 }]
    })
  }

  const changeQuantity = (productId: string, delta: number) => {
    setCart((prev) =>
      prev
        .map((line) =>
          line.product.id === productId
            ? {
                ...line,
                quantity: Math.min(
                  line.quantity + delta,
                  line.product.stock,
                ),
              }
            : line,
        )
        .filter((line) => line.quantity > 0),
    )
  }

  const clearCart = () => setCart([])

  const subtotal = cart.reduce((sum, line) => sum + line.product.price * line.quantity, 0)
  const igv = subtotal * TAX_RATE
  const total = subtotal + igv

  const registerSale = async () => {
    setError('')
    setSuccess('')
    try {
      setProcessing(true)
      const dueDate = new Date()
      dueDate.setDate(dueDate.getDate() + (settings?.defaultCreditTermDays ?? 15))
      const sale = await salesRepository.create({
        paymentMode,
        clientId: client?.id,
        dueDate: paymentMode === 'fiado' ? isoDate(dueDate) : undefined,
        items: cart.map((line) => ({ productId: line.product.id, quantity: line.quantity })),
      })
      await productRepository.load(true)
      setCart([])
      setClientId('')
      setPaymentMode('contado')
      setSuccess(`Venta ${sale.code} registrada correctamente.`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudo registrar la venta.')
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="flex flex-col lg:flex-row gap-6 h-[calc(100dvh-8rem)]">
      {/* Products section */}
      <section className="flex-1 flex flex-col bg-surface-container-lowest rounded-lg border border-outline-variant overflow-hidden min-h-0">
        {/* Search & filters */}
        <div className="p-4 md:p-5 border-b border-outline-variant shrink-0">
          <div className="relative mb-4">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-outline">
              <Icon name="search" size="18px" />
            </span>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar producto por nombre o código..."
              className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-outline-variant bg-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all font-body-lg text-body-lg text-on-surface placeholder:text-on-surface-variant"
            />
          </div>
          <div className="flex gap-3 overflow-x-auto pb-1 no-scrollbar">
            {productCategories.map((cat) => {
              const active = category === cat
              return (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setCategory(cat)}
                  className={`px-5 py-2 rounded-full font-label-sm text-label-sm whitespace-nowrap transition-colors ${
                    active
                      ? 'bg-primary text-on-primary shadow-sm'
                      : 'bg-surface-container border border-outline-variant text-on-surface hover:bg-surface-container-high'
                  }`}
                >
                  {cat}
                </button>
              )
            })}
          </div>
        </div>

        {/* Product grid */}
        <div className="flex-1 overflow-y-auto p-4 md:p-5">
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
            {filteredProducts.map((product) => {
              const available = product.stock
              return (
                <div
                  key={product.id}
                  className={`group bg-surface-container-lowest rounded-xl border border-outline-variant overflow-hidden transition-all duration-200 flex flex-col ${available > 0 ? 'hover:shadow-sm' : 'opacity-60'}`}
                >
                <div className="aspect-square bg-surface-container-low relative overflow-hidden p-4 flex items-center justify-center">
                  <Icon
                    name={product.icon}
                    size="52px"
                    className="text-primary group-hover:scale-105 transition-transform duration-300"
                  />
                </div>
                <div className="p-4 flex-1 flex flex-col justify-between border-t border-outline-variant">
                  <div>
                    <h3 className="font-body-md text-body-md font-medium text-on-surface line-clamp-2">
                      {product.name}
                    </h3>
                    <p className="text-on-surface-variant text-xs mt-1">{product.category}</p>
                    <p className={`text-xs mt-1 ${available > 0 ? 'text-on-surface-variant' : 'text-error'}`}>
                      {available > 0 ? `${available} disponibles` : 'Sin stock'}
                    </p>
                  </div>
                  <div className="flex items-center justify-between mt-3">
                    <span className="font-h3-title text-h3-title text-primary">
                      {formatCurrency(product.price)}
                    </span>
                    <button
                      type="button"
                      onClick={() => addToCart(product)}
                      disabled={available === 0}
                      aria-label={`Agregar ${product.name}`}
                      className="w-8 h-8 rounded-full bg-surface-container flex items-center justify-center text-primary hover:bg-primary hover:text-on-primary transition-colors disabled:cursor-not-allowed disabled:hover:bg-surface-container disabled:hover:text-primary"
                    >
                      <Icon name="add" size="18px" />
                    </button>
                  </div>
                </div>
                </div>
              )
            })}
            {filteredProducts.length === 0 && (
              <div className="col-span-full flex flex-col items-center justify-center py-16 text-center">
                <Icon name="search_off" size="40px" className="text-outline" />
                <p className="mt-3 text-on-surface-variant">{loadingProducts ? 'Cargando productos...' : 'No se encontraron productos'}</p>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Cart section */}
      <aside className="w-full lg:w-[400px] shrink-0 bg-surface-container-lowest rounded-lg border border-outline-variant flex flex-col overflow-hidden min-h-0">
        {/* Cart header */}
        <div className="p-5 border-b border-outline-variant shrink-0 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Icon name="shopping_cart" className="text-primary" />
            <h2 className="font-h2-headline text-h2-headline text-on-surface">
              Carrito de ventas
            </h2>
          </div>
          <button
            type="button"
            onClick={clearCart}
            className="text-on-surface-variant hover:text-error transition-colors text-sm font-medium"
          >
            Vaciar
          </button>
        </div>

        {/* Cart items */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-2">
          {cart.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Icon name="remove_shopping_cart" size="40px" className="text-outline" />
              <p className="mt-3 text-on-surface-variant">El carrito está vacío</p>
            </div>
          )}
          {cart.map((line) => (
            <div
              key={line.product.id}
              className="flex items-start gap-4 p-3 rounded-lg hover:bg-surface-container-low transition-colors"
            >
              <div className="w-12 h-12 bg-surface-container rounded flex-shrink-0 flex items-center justify-center">
                <Icon name={line.product.icon} size="22px" className="text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-start">
                  <h4 className="font-body-md text-body-md font-medium text-on-surface truncate pr-2">
                    {line.product.name}
                  </h4>
                  <span className="font-medium text-on-surface whitespace-nowrap">
                    {formatCurrency(line.product.price * line.quantity)}
                  </span>
                </div>
                <div className="flex items-center justify-between mt-2">
                  <div className="text-on-surface-variant text-sm">
                    {formatCurrency(line.product.price)} c/u
                  </div>
                  <div className="flex items-center bg-surface-container rounded border border-outline-variant">
                    <button
                      type="button"
                      onClick={() => changeQuantity(line.product.id, -1)}
                      aria-label="Disminuir cantidad"
                      className="w-7 h-7 flex items-center justify-center text-on-surface-variant hover:text-primary transition-colors"
                    >
                      <Icon name="remove" size="16px" />
                    </button>
                    <span className="w-8 text-center font-medium text-sm text-on-surface">
                      {line.quantity}
                    </span>
                    <button
                      type="button"
                      onClick={() => changeQuantity(line.product.id, 1)}
                      disabled={line.quantity >= line.product.stock}
                      aria-label="Aumentar cantidad"
                      className="w-7 h-7 flex items-center justify-center text-on-surface-variant hover:text-primary transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <Icon name="add" size="16px" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Checkout */}
        <div className="border-t border-outline-variant bg-surface-bright p-5 shrink-0 flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <div className="flex justify-between text-on-surface-variant text-sm">
              <span>Subtotal</span>
              <span>{formatCurrency(subtotal)}</span>
            </div>
            <div className="flex justify-between text-on-surface-variant text-sm">
              <span>IGV (18%)</span>
              <span>{formatCurrency(igv)}</span>
            </div>
            <div className="flex justify-between items-end mt-2 pt-2 border-t border-outline-variant border-dashed">
              <span className="font-h3-title text-h3-title text-on-surface">Total</span>
              <span className="font-h2-headline text-h2-headline text-primary">
                {formatCurrency(total)}
              </span>
            </div>
          </div>

          {/* Payment mode tabs */}
          <div className="flex p-1 bg-surface-container rounded-lg border border-outline-variant">
            {(['contado', 'fiado'] as const).map((mode) => {
              const active = paymentMode === mode
              const label = mode === 'contado' ? 'Contado' : 'Fiado'
              return (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setPaymentMode(mode)}
                  className={`flex-1 py-2 text-center rounded-md font-medium text-sm transition-all ${
                    active
                      ? 'bg-surface-container-lowest shadow-sm text-primary'
                      : 'text-on-surface-variant hover:text-primary'
                  }`}
                >
                  {label}
                </button>
              )
            })}
          </div>

          {/* Fiado UI */}
          {paymentMode === 'fiado' && (
            <div className="flex flex-col gap-3 p-4 bg-surface-container-low rounded-lg border border-primary-fixed">
              <label className="font-label-sm text-label-sm text-primary-container">
                Seleccionar Cliente
              </label>
              <select
                value={clientId}
                disabled={processing}
                onChange={(event) => {
                  setClientId(event.target.value)
                  setError('')
                }}
                className="w-full px-3 py-2 text-sm rounded border border-outline-variant bg-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none"
              >
                <option value="">Seleccione un cliente...</option>
                {clients.map((item) => <option key={item.id} value={item.id}>{item.business} · {item.name}</option>)}
              </select>
              {client && (
                <div className="mt-1 p-3 bg-surface-container-lowest rounded border border-outline-variant flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm text-on-surface">{client.business}</p>
                    <p className="text-xs text-on-surface-variant mt-0.5">Deuda actual: {formatCurrency(client.debt)}</p>
                  </div>
                  <div className="flex flex-col items-center justify-center w-10 h-10 rounded-full border-2 border-primary text-primary bg-primary-fixed">
                    <Icon name="psychology_alt" size="20px" />
                  </div>
                </div>
              )}
            </div>
          )}

          {error && <p className="p-3 rounded-lg bg-error-container text-on-error-container text-sm">{error}</p>}
          {success && <p className="p-3 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200 text-sm">{success}</p>}

          <button
            type="button"
            onClick={registerSale}
            disabled={processing || cart.length === 0 || (paymentMode === 'fiado' && !client)}
            className="w-full py-4 rounded-lg bg-primary text-on-primary font-h3-title text-body-lg font-semibold hover:bg-primary-container hover:shadow-md transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Icon name={processing ? 'progress_activity' : 'check_circle'} className={processing ? 'animate-spin' : ''} />
            {processing ? 'Validando y registrando...' : 'Registrar venta'}
          </button>
        </div>
      </aside>
    </div>
  )
}
