import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Icon from '@/components/ui/Icon'
import ProductThumbnail from '@/components/ui/ProductThumbnail'
import type { StoredCredit } from '@/services/creditRepository'
import type { StoredClient } from '@/services/clientRepository'
import type { CommerceProduct } from '@/services/productRepository'

interface GlobalSearchProps {
  credits: StoredCredit[]
  clients: StoredClient[]
  products: CommerceProduct[]
}

function normalize(value: string) {
  return value.trim().toLowerCase()
}

export default function GlobalSearch({ credits, clients, products }: GlobalSearchProps) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)

  const term = normalize(query)

  const matchedCredits = term
    ? credits.filter((credit) => {
        const code = normalize(credit.code)
        const name = normalize(credit.client?.name ?? '')
        const business = normalize(credit.client?.business ?? '')
        return code.includes(term) || name.includes(term) || business.includes(term)
      })
    : []

  const matchedClients = term
    ? clients.filter((client) => {
        const name = normalize(client.name)
        const business = normalize(client.business)
        const document = normalize(client.document ?? '')
        const phone = normalize(client.phone ?? '')
        return (
          name.includes(term) ||
          business.includes(term) ||
          document.includes(term) ||
          phone.includes(term)
        )
      })
    : []

  const matchedProducts = term
    ? products.filter((product) => {
        const name = normalize(product.name)
        const sku = normalize(product.sku ?? '')
        return name.includes(term) || sku.includes(term)
      })
    : []

  const total = matchedCredits.length + matchedClients.length + matchedProducts.length
  const hasResults = term.length > 0 && open && total > 0

  const visit = (to: string) => {
    setOpen(false)
    setQuery('')
    navigate(to)
  }

  return (
    <div className="relative w-full max-w-md">
      <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-on-surface-variant">
        <Icon name="search" size="18px" />
      </span>
      <input
        type="text"
        placeholder="Buscar clientes, fiados o productos..."
        value={query}
        onChange={(e) => {
          setQuery(e.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={(e) => {
          if (e.key === 'Escape') setOpen(false)
        }}
        className="w-full h-10 pl-10 pr-10 bg-surface-container-low border border-outline-variant rounded-full font-body-md text-body-md text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all"
      />
      {query.length > 0 && (
        <button
          type="button"
          onMouseDown={(e) => {
            e.preventDefault()
            setQuery('')
            setOpen(true)
          }}
          className="absolute inset-y-0 right-0 flex items-center pr-3 text-on-surface-variant hover:text-error transition-colors"
          aria-label="Limpiar búsqueda"
        >
          <Icon name="close" size="16px" />
        </button>
      )}

      {hasResults && (
        <div className="absolute left-0 right-0 top-12 z-50 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-xl max-h-96 overflow-y-auto">
          {matchedClients.length > 0 && (
            <>
              <p className="px-4 py-2 text-[11px] uppercase tracking-wider text-on-surface-variant font-semibold bg-surface-container-low">
                Clientes
              </p>
              {matchedClients.slice(0, 4).map((client) => (
                <button
                  key={client.id}
                  type="button"
                  onMouseDown={(e) => {
                    e.preventDefault()
                    visit(`/clientes/${client.id}`)
                  }}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-surface-container-high transition-colors"
                >
                  <span className="w-8 h-8 rounded-full bg-surface-container-high flex items-center justify-center text-primary font-bold text-xs uppercase">
                    {client.initials}
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-medium text-on-surface truncate">{client.business || client.name}</span>
                    <span className="block text-[11px] text-on-surface-variant truncate">
                      {client.name} • {client.document || ''}
                    </span>
                  </span>
                </button>
              ))}
            </>
          )}

          {matchedCredits.length > 0 && (
            <>
              <p className="px-4 py-2 text-[11px] uppercase tracking-wider text-on-surface-variant font-semibold bg-surface-container-low">
                Fiados
              </p>
              {matchedCredits.slice(0, 5).map((credit) => (
                <button
                  key={credit.id}
                  type="button"
                  onMouseDown={(e) => {
                    e.preventDefault()
                    visit(`/fiados/${credit.id}`)
                  }}
                  className="w-full flex items-center justify-between gap-3 px-4 py-2.5 text-left hover:bg-surface-container-high transition-colors"
                >
                  <span className="flex items-center gap-3 min-w-0">
                    <Icon name="receipt_long" size="18px" className="text-on-surface-variant" />
                    <span className="min-w-0">
                      <span className="block text-sm font-medium text-on-surface truncate">
                        {credit.code}
                      </span>
                      <span className="block text-[11px] text-on-surface-variant truncate">
                        {credit.client?.name ?? credit.code}
                      </span>
                    </span>
                  </span>
                  <span className="text-sm font-semibold text-on-surface">
                    S/ {Number(credit.pendingAmount).toLocaleString('es-PE')}
                  </span>
                </button>
              ))}
            </>
          )}

          {matchedProducts.length > 0 && (
            <>
              <p className="px-4 py-2 text-[11px] uppercase tracking-wider text-on-surface-variant font-semibold bg-surface-container-low">
                Productos
              </p>
              {matchedProducts.slice(0, 4).map((product) => (
                <button
                  key={product.id}
                  type="button"
                  onMouseDown={(e) => {
                    e.preventDefault()
                    visit('/productos')
                  }}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-surface-container-high transition-colors"
                >
                  <ProductThumbnail
                    name={product.name}
                    icon={product.icon}
                    imageUrl={product.imageUrl}
                    iconSize="18px"
                    iconClassName="text-on-surface-variant"
                    className="w-8 h-8 rounded bg-surface-container shrink-0"
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-medium text-on-surface truncate">{product.name}</span>
                    <span className="block text-[11px] text-on-surface-variant truncate">
                      {product.sku} • Stock: {product.stock}
                    </span>
                  </span>
                </button>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  )
}
