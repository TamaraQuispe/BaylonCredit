import { useMemo, useState, type FormEvent } from 'react'
import Icon from '@/components/ui/Icon'
import Modal from '@/components/ui/Modal'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import { productCategories, products as initialProducts, type Product } from '@/data/products'
import { formatCurrency } from '@/utils/format'

const categoryIcons: Record<string, string> = {
  Cervezas: 'sports_bar',
  Gaseosas: 'local_drink',
  Licores: 'liquor',
  Cigarrillos: 'smoking_rooms',
  Otros: 'category',
}

function stockState(stock: number) {
  if (stock === 0) {
    return {
      label: 'Agotado',
      badge: 'bg-red-50 text-red-600 border-red-200',
      dot: 'bg-red-500',
      row: 'bg-red-50/70',
    }
  }
  if (stock <= 10) {
    return {
      label: 'Stock bajo',
      badge: 'bg-amber-50 text-amber-600 border-amber-200',
      dot: 'bg-amber-500',
      row: 'bg-amber-50/70',
    }
  }
  return {
    label: 'Disponible',
    badge: 'bg-emerald-50 text-emerald-600 border-emerald-200',
    dot: 'bg-emerald-500',
    row: '',
  }
}

export default function ProductosPage() {
  const [catalog, setCatalog] = useState(initialProducts)
  const [category, setCategory] = useState('Cervezas')
  const [search, setSearch] = useState('')
  const [editing, setEditing] = useState<Product | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [deleting, setDeleting] = useState<Product | null>(null)

  const filteredProducts = useMemo(() => {
    const term = search.trim().toLowerCase()
    return catalog.filter(
      (product) =>
        product.category === category &&
        (!term ||
          product.name.toLowerCase().includes(term) ||
          product.category.toLowerCase().includes(term)),
    )
  }, [catalog, category, search])

  const openNew = () => {
    setEditing(null)
    setFormOpen(true)
  }

  const openEdit = (product: Product) => {
    setEditing(product)
    setFormOpen(true)
  }

  const saveProduct = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const selectedCategory = String(data.get('category'))
    const product: Product = {
      id: editing?.id ?? `p${Date.now()}`,
      name: String(data.get('name')),
      category: selectedCategory,
      price: Number(data.get('price')),
      stock: Number(data.get('stock')),
      icon: categoryIcons[selectedCategory] ?? 'category',
    }

    setCatalog((current) =>
      editing
        ? current.map((item) => (item.id === editing.id ? product : item))
        : [product, ...current],
    )
    setCategory(selectedCategory)
    setFormOpen(false)
    setEditing(null)
  }

  return (
    <div>
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
        <div>
          <h2 className="font-h2-headline text-h2-headline text-primary mb-1">Productos</h2>
          <p className="font-body-md text-body-md text-on-surface-variant">
            Gestiona el catálogo de productos y su disponibilidad.
          </p>
        </div>
        <button
          type="button"
          onClick={openNew}
          className="flex items-center gap-2 px-6 py-2.5 bg-primary-container text-on-primary rounded-lg font-label-sm shadow-sm hover:shadow-md hover:bg-primary transition-all"
        >
          <Icon name="add" size="18px" /> Nuevo producto
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        {productCategories.slice(1).map((item) => {
          const active = category === item
          return (
            <button
              key={item}
              type="button"
              onClick={() => setCategory(item)}
              className={`rounded-xl p-4 flex flex-col items-center justify-center gap-2 transition-colors group border ${
                active
                  ? 'bg-primary-fixed border-primary-fixed-dim'
                  : 'bg-surface-container-lowest border-outline-variant hover:bg-surface-container-highest'
              }`}
            >
              <Icon
                name={categoryIcons[item]}
                className={`${active ? 'text-primary' : 'text-on-surface-variant'} group-hover:scale-110 transition-transform`}
              />
              <span className="font-label-sm text-label-sm text-on-surface">{item}</span>
            </button>
          )
        })}
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-outline-variant bg-surface-bright flex justify-end">
          <div className="relative w-full sm:w-[340px]">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant">
              <Icon name="search" size="18px" />
            </span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-surface-container-low border border-outline-variant rounded-full font-body-md text-on-surface focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              placeholder="Buscar producto..."
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[760px]">
            <thead>
              <tr className="border-b border-outline-variant bg-surface-bright font-table-header text-table-header text-on-surface-variant">
                <th className="py-4 px-6 font-semibold">Producto</th>
                <th className="py-4 px-6 font-semibold">Categoría</th>
                <th className="py-4 px-6 font-semibold">Precio (S/.)</th>
                <th className="py-4 px-6 font-semibold">Stock</th>
                <th className="py-4 px-6 font-semibold">Estado</th>
                <th className="py-4 px-6 font-semibold text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="font-body-md text-body-md text-on-surface divide-y divide-outline-variant">
              {filteredProducts.map((product) => {
                const state = stockState(product.stock)
                return (
                  <tr key={product.id} className={`hover:bg-surface-container-low transition-colors group h-[64px] ${state.row}`}>
                    <td className="py-3 px-6">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded border border-outline-variant bg-surface-bright flex items-center justify-center shrink-0 ${product.stock === 0 ? 'opacity-50 grayscale' : ''}`}>
                          <Icon name={product.icon} size="22px" className="text-primary" />
                        </div>
                        <span className={`font-medium group-hover:text-primary transition-colors ${product.stock === 0 ? 'text-on-surface-variant line-through' : 'text-on-background'}`}>
                          {product.name}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-6 text-on-surface-variant">{product.category}</td>
                    <td className="py-3 px-6 font-medium">{formatCurrency(product.price)}</td>
                    <td className="py-3 px-6 text-on-surface-variant">{product.stock} u.</td>
                    <td className="py-3 px-6">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border font-label-sm text-label-sm ${state.badge}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${state.dot}`} />
                        {state.label}
                      </span>
                    </td>
                    <td className="py-3 px-6 text-right">
                      <div className="flex justify-end gap-2">
                        <button type="button" onClick={() => openEdit(product)} className="p-1.5 text-on-surface-variant hover:text-primary hover:bg-surface-container-high rounded transition-colors" aria-label={`Editar ${product.name}`}>
                          <Icon name="edit" size="20px" />
                        </button>
                        <button type="button" onClick={() => setDeleting(product)} className="p-1.5 text-on-surface-variant hover:text-error hover:bg-error-container rounded transition-colors" aria-label={`Eliminar ${product.name}`}>
                          <Icon name="delete" size="20px" />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
              {filteredProducts.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-14 px-6 text-center text-on-surface-variant">
                    No hay productos para esta búsqueda.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="px-6 py-4 border-t border-outline-variant bg-surface-bright flex items-center justify-between">
          <span className="font-label-sm text-label-sm text-on-surface-variant">
            Mostrando {filteredProducts.length} de {catalog.length} productos
          </span>
          <div className="flex gap-1">
            <button type="button" disabled className="p-1 border border-outline-variant rounded text-on-surface-variant disabled:opacity-50">
              <Icon name="chevron_left" size="18px" />
            </button>
            <button type="button" className="w-8 h-8 flex items-center justify-center border border-primary bg-primary-fixed text-primary rounded font-label-sm">1</button>
            <button type="button" className="w-8 h-8 flex items-center justify-center border border-outline-variant rounded hover:bg-surface-container-high text-on-surface-variant font-label-sm">2</button>
            <button type="button" className="p-1 border border-outline-variant rounded hover:bg-surface-container-high text-on-surface-variant">
              <Icon name="chevron_right" size="18px" />
            </button>
          </div>
        </div>
      </div>

      <Modal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title={editing ? 'Editar producto' : 'Nuevo producto'}
        icon="inventory_2"
        iconClassName="text-primary"
      >
        <form key={editing?.id ?? 'new'} onSubmit={saveProduct} className="space-y-4">
          <ProductField label="Nombre" name="name" defaultValue={editing?.name} />
          <label className="flex flex-col gap-1.5 font-label-sm text-label-sm text-on-surface">
            Categoría
            <select name="category" defaultValue={editing?.category ?? category} className="h-11 px-3 rounded-lg bg-surface border border-outline-variant text-on-surface focus:outline-none focus:border-primary">
              {productCategories.slice(1).map((item) => <option key={item}>{item}</option>)}
            </select>
          </label>
          <div className="grid grid-cols-2 gap-4">
            <ProductField label="Precio" name="price" type="number" step="0.01" min="0" defaultValue={editing?.price} />
            <ProductField label="Stock" name="stock" type="number" min="0" defaultValue={editing?.stock} />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={() => setFormOpen(false)} className="h-10 px-5 rounded-lg border border-outline-variant text-primary hover:bg-surface-container-low">Cancelar</button>
            <button type="submit" className="h-10 px-5 rounded-lg bg-primary-container text-on-primary hover:bg-primary">Guardar producto</button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(deleting)}
        title="Eliminar producto"
        message={`¿Deseas eliminar ${deleting?.name ?? 'este producto'} del catálogo?`}
        confirmLabel="Eliminar"
        tone="danger"
        onCancel={() => setDeleting(null)}
        onConfirm={() => {
          if (deleting) setCatalog((current) => current.filter((item) => item.id !== deleting.id))
          setDeleting(null)
        }}
      />
    </div>
  )
}

interface ProductFieldProps {
  label: string
  name: string
  type?: string
  step?: string
  min?: string
  defaultValue?: string | number
}

function ProductField({ label, name, type = 'text', ...props }: ProductFieldProps) {
  return (
    <label className="flex flex-col gap-1.5 font-label-sm text-label-sm text-on-surface">
      {label}
      <input
        required
        name={name}
        type={type}
        className="h-11 px-4 rounded-lg bg-surface border border-outline-variant text-on-surface focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
        {...props}
      />
    </label>
  )
}
