import { useMemo, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import Icon from '@/components/ui/Icon'
import Modal from '@/components/ui/Modal'
import { inventoryItems, type InventoryItem } from '@/data/inventory'

type StockFilter = 'todos' | 'optimo' | 'bajo' | 'agotado'
type StockAction = 'entrada' | 'ajuste'

function getStatus(item: InventoryItem): Exclude<StockFilter, 'todos'> {
  if (item.stock === 0) return 'agotado'
  if (item.stock <= item.minimumStock) return 'bajo'
  return 'optimo'
}

const statusConfig = {
  optimo: {
    label: 'Óptimo',
    badge: 'bg-emerald-100 text-emerald-800',
    stock: 'text-on-surface',
    row: '',
  },
  bajo: {
    label: 'Stock Bajo',
    badge: 'bg-secondary-fixed text-on-secondary-container',
    stock: 'text-secondary font-bold',
    row: 'bg-secondary-fixed/10',
  },
  agotado: {
    label: 'Agotado',
    badge: 'bg-error-container text-on-error-container',
    stock: 'text-error font-bold',
    row: 'bg-error-container/10',
  },
}

const kpis = [
  {
    label: 'Productos registrados',
    value: '1,248',
    detail: '+12 este mes',
    icon: 'inventory_2',
    iconClass: 'text-primary bg-surface-container',
    detailClass: 'text-emerald-600',
    detailIcon: 'trending_up',
    decor: 'bg-primary-fixed',
  },
  {
    label: 'Productos con stock bajo',
    value: '45',
    detail: 'Requiere atención',
    icon: 'warning',
    iconClass: 'text-secondary bg-secondary-fixed',
    detailClass: 'text-secondary',
    detailIcon: 'priority_high',
    decor: 'bg-secondary-fixed',
  },
  {
    label: 'Productos agotados',
    value: '12',
    detail: 'Impacto en ventas',
    icon: 'block',
    iconClass: 'text-error bg-error-container',
    detailClass: 'text-error',
    detailIcon: 'shopping_cart_off',
    decor: 'bg-error-container',
  },
]

export default function InventarioPage() {
  const [items, setItems] = useState(inventoryItems)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<StockFilter>('todos')
  const [showFilters, setShowFilters] = useState(false)
  const [selected, setSelected] = useState<InventoryItem | null>(null)
  const [action, setAction] = useState<StockAction>('entrada')

  const filteredItems = useMemo(() => {
    const term = search.trim().toLowerCase()
    return items.filter((item) => {
      const matchesSearch =
        !term || item.name.toLowerCase().includes(term) || item.code.toLowerCase().includes(term)
      const matchesFilter = filter === 'todos' || getStatus(item) === filter
      return matchesSearch && matchesFilter
    })
  }, [filter, items, search])

  const openStockAction = (item: InventoryItem, nextAction: StockAction) => {
    setSelected(item)
    setAction(nextAction)
  }

  const updateStock = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!selected) return
    const value = Number(new FormData(event.currentTarget).get('quantity'))
    setItems((current) =>
      current.map((item) =>
        item.id === selected.id
          ? { ...item, stock: action === 'entrada' ? item.stock + value : value }
          : item,
      ),
    )
    setSelected(null)
  }

  const exportInventory = () => {
    const rows = [
      ['Código', 'Producto', 'Categoría', 'Stock actual', 'Stock mínimo'],
      ...items.map((item) => [item.code, item.name, item.category, item.stock, item.minimumStock]),
    ]
    const csv = rows.map((row) => row.join(',')).join('\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = 'inventario.csv'
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4 mb-8">
        <div>
          <h2 className="font-h1-display text-h1-display text-on-surface mb-1">Inventario</h2>
          <p className="font-body-md text-body-md text-on-surface-variant">
            Gestión de existencias y valoración de almacén
          </p>
        </div>
        <button
          type="button"
          onClick={exportInventory}
          className="flex items-center gap-2 px-4 py-2 bg-surface-container-lowest border border-outline-variant rounded-lg text-primary font-label-sm text-label-sm hover:bg-surface-container-low transition-colors shadow-sm"
        >
          <Icon name="download" size="18px" /> Exportar
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {kpis.map((kpi) => (
          <div
            key={kpi.label}
            className="bg-surface-container-lowest p-card-padding rounded-xl border border-outline-variant shadow-sm flex flex-col justify-between h-32 relative overflow-hidden group"
          >
            <div className={`absolute -right-4 -top-4 w-24 h-24 rounded-full opacity-20 group-hover:scale-150 transition-transform duration-500 ${kpi.decor}`} />
            <div className="flex justify-between items-start z-10">
              <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wide">
                {kpi.label}
              </span>
              <span className={`p-1.5 rounded-lg ${kpi.iconClass}`}>
                <Icon name={kpi.icon} size="20px" />
              </span>
            </div>
            <div className="z-10">
              <h3 className="font-h2-headline text-h2-headline text-on-surface">{kpi.value}</h3>
              <div className={`flex items-center gap-1 mt-1 ${kpi.detailClass}`}>
                <Icon name={kpi.detailIcon} size="14px" />
                <span className="font-label-sm text-label-sm">{kpi.detail}</span>
              </div>
            </div>
          </div>
        ))}

        <div className="bg-primary p-card-padding rounded-xl border border-primary-container shadow-sm flex flex-col justify-between h-32 relative overflow-hidden group text-on-primary">
          <div className="absolute -right-12 -top-12 w-40 h-40 bg-white rounded-full opacity-10 group-hover:scale-150 transition-transform duration-700" />
          <div className="flex justify-between items-start z-10">
            <span className="font-label-sm text-label-sm text-primary-fixed-dim uppercase tracking-wide">
              Valor total del inventario
            </span>
            <span className="text-primary-fixed bg-on-primary-fixed-variant p-1.5 rounded-lg">
              <Icon name="account_balance_wallet" size="20px" />
            </span>
          </div>
          <div className="z-10">
            <div className="flex items-baseline gap-1">
              <span className="font-h3-title text-h3-title text-primary-fixed-dim">S/</span>
              <h3 className="font-h2-headline text-h2-headline">142,500.00</h3>
            </div>
            <span className="font-label-sm text-label-sm text-primary-fixed">Actualizado hoy</span>
          </div>
        </div>
      </div>

      <div className="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm overflow-hidden">
        <div className="p-6 border-b border-outline-variant flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div className="relative w-full sm:w-80">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-outline">
              <Icon name="search" size="20px" />
            </span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="w-full h-10 pl-10 pr-4 bg-background border border-outline-variant rounded-lg font-body-md text-body-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              placeholder="Buscar por producto o código..."
            />
          </div>
          <div className="flex gap-3 w-full sm:w-auto">
            <button
              type="button"
              onClick={() => setShowFilters((visible) => !visible)}
              className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-background border border-outline-variant rounded-lg text-on-surface-variant font-label-sm text-label-sm hover:bg-surface-container-low"
            >
              <Icon name="filter_list" size="18px" /> Filtros
            </button>
            <Link
              to="/productos"
              className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-primary rounded-lg text-on-primary font-label-sm text-label-sm hover:bg-primary-container shadow-sm"
            >
              <Icon name="add" size="18px" /> Nuevo Producto
            </Link>
          </div>
        </div>

        {showFilters && (
          <div className="px-6 py-3 border-b border-outline-variant bg-surface-container-low flex items-center gap-3">
            <label className="font-label-sm text-label-sm text-on-surface-variant" htmlFor="stock-filter">
              Estado
            </label>
            <select
              id="stock-filter"
              value={filter}
              onChange={(event) => setFilter(event.target.value as StockFilter)}
              className="h-9 px-3 rounded-lg border border-outline-variant bg-white text-on-surface focus:outline-none focus:border-primary"
            >
              <option value="todos">Todos</option>
              <option value="optimo">Óptimo</option>
              <option value="bajo">Stock bajo</option>
              <option value="agotado">Agotado</option>
            </select>
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[800px]">
            <thead>
              <tr className="border-b border-outline-variant">
                <th className="py-4 px-6 font-table-header text-table-header text-on-surface-variant uppercase">Producto</th>
                <th className="py-4 px-6 font-table-header text-table-header text-on-surface-variant uppercase">Categoría</th>
                <th className="py-4 px-6 font-table-header text-table-header text-on-surface-variant uppercase text-right">Stock actual</th>
                <th className="py-4 px-6 font-table-header text-table-header text-on-surface-variant uppercase text-right">Stock mínimo</th>
                <th className="py-4 px-6 font-table-header text-table-header text-on-surface-variant uppercase text-center">Estado</th>
                <th className="py-4 px-6 font-table-header text-table-header text-on-surface-variant uppercase text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/50">
              {filteredItems.map((item) => {
                const status = getStatus(item)
                const config = statusConfig[status]
                return (
                  <tr key={item.id} className={`hover:bg-surface transition-colors h-[56px] group ${config.row}`}>
                    <td className="py-3 px-6">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-surface-variant flex items-center justify-center text-primary shrink-0">
                          <Icon name={item.icon} size="20px" />
                        </div>
                        <div>
                          <p className="font-body-md text-body-md font-medium text-on-surface">{item.name}</p>
                          <p className="font-label-sm text-label-sm text-on-surface-variant">Cod: {item.code}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-6 text-on-surface-variant">{item.category}</td>
                    <td className={`py-3 px-6 text-right font-medium ${config.stock}`}>{item.stock}</td>
                    <td className="py-3 px-6 text-on-surface-variant text-right">{item.minimumStock}</td>
                    <td className="py-3 px-6 text-center">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.badge}`}>
                        {config.label}
                      </span>
                    </td>
                    <td className="py-3 px-6 text-right">
                      <div className="flex items-center justify-end gap-2 opacity-100 sm:opacity-0 group-hover:opacity-100 transition-opacity">
                        <button type="button" onClick={() => openStockAction(item, 'entrada')} className="p-1.5 rounded-md text-on-surface-variant hover:text-primary hover:bg-surface-container-high" title="Registrar entrada">
                          <Icon name="arrow_downward" size="20px" />
                        </button>
                        <button type="button" onClick={() => openStockAction(item, 'ajuste')} className="p-1.5 rounded-md text-on-surface-variant hover:text-primary hover:bg-surface-container-high" title="Ajuste de stock">
                          <Icon name="build" size="20px" />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <div className="p-4 border-t border-outline-variant flex items-center justify-between text-sm text-on-surface-variant bg-surface-bright">
          <span>Mostrando {filteredItems.length} de 1,248 productos</span>
          <div className="flex gap-1">
            <button type="button" disabled className="w-8 h-8 flex items-center justify-center rounded disabled:opacity-50"><Icon name="chevron_left" size="20px" /></button>
            <button type="button" className="w-8 h-8 flex items-center justify-center rounded bg-primary-container text-on-primary-container font-medium">1</button>
            <button type="button" className="w-8 h-8 flex items-center justify-center rounded hover:bg-surface-container-high">2</button>
            <button type="button" className="w-8 h-8 flex items-center justify-center rounded hover:bg-surface-container-high">3</button>
            <button type="button" className="w-8 h-8 flex items-center justify-center rounded hover:bg-surface-container-high"><Icon name="chevron_right" size="20px" /></button>
          </div>
        </div>
      </div>

      <Modal
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        title={action === 'entrada' ? 'Registrar entrada' : 'Ajustar stock'}
        icon={action === 'entrada' ? 'arrow_downward' : 'build'}
        iconClassName="text-primary"
      >
        <form onSubmit={updateStock} className="space-y-4">
          <div className="p-3 rounded-lg bg-surface-container-low text-on-surface">
            <p className="font-medium">{selected?.name}</p>
            <p className="text-sm text-on-surface-variant">Stock actual: {selected?.stock} unidades</p>
          </div>
          <label className="flex flex-col gap-1.5 font-label-sm text-label-sm text-on-surface">
            {action === 'entrada' ? 'Cantidad a ingresar' : 'Nuevo stock'}
            <input
              required
              autoFocus
              name="quantity"
              type="number"
              min="0"
              defaultValue={action === 'ajuste' ? selected?.stock : 1}
              className="h-11 px-4 rounded-lg bg-surface border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </label>
          <div className="flex justify-end gap-3">
            <button type="button" onClick={() => setSelected(null)} className="h-10 px-5 rounded-lg border border-outline-variant text-primary hover:bg-surface-container-low">Cancelar</button>
            <button type="submit" className="h-10 px-5 rounded-lg bg-primary text-on-primary hover:bg-primary-container">Guardar</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
