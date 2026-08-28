import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '@/components/ui/Icon'
import { clients, type Cliente } from '@/data/clientes'
import { formatCurrency } from '@/utils/format'

type FilterKey = 'todos' | 'sin-deuda' | 'con-deuda' | 'vencido' | 'riesgo-alto'

const filters: { key: FilterKey; label: string; count?: number }[] = [
  { key: 'todos', label: 'Todos los clientes', count: 245 },
  { key: 'sin-deuda', label: 'Sin deuda' },
  { key: 'con-deuda', label: 'Con deuda' },
  { key: 'vencido', label: 'Deuda vencida' },
  { key: 'riesgo-alto', label: 'Riesgo alto' },
]

const statusMap: Record<Cliente['status'], { label: string; className: string }> = {
  'al-dia': {
    label: 'Al día',
    className: 'bg-inverse-on-surface text-primary-container border border-outline-variant/30',
  },
  vencido: {
    label: 'Vencido',
    className: 'bg-error-container text-on-error-container border border-error/20',
  },
  'sin-deuda': {
    label: 'Sin deuda',
    className: 'bg-surface-container-high text-on-surface-variant border border-outline-variant',
  },
  pendiente: {
    label: 'Pendiente',
    className: 'bg-secondary-fixed text-on-secondary-fixed border border-secondary-fixed-dim/30',
  },
}

const riskMap: Record<Cliente['risk'], { label: string; className: string }> = {
  'muy-bajo': { label: 'Muy Bajo', className: 'bg-surface-variant text-on-surface' },
  bajo: { label: 'Bajo', className: 'bg-surface-variant text-on-surface' },
  medio: { label: 'Medio', className: 'bg-secondary-fixed text-on-secondary-fixed' },
  alto: { label: 'Alto', className: 'bg-error-container text-on-error-container' },
  critico: { label: 'Crítico', className: 'bg-error-container text-on-error-container' },
}

export default function ClientesPage() {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<FilterKey>('todos')

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase()
    return clients.filter((client) => {
      const matchesFilter =
        filter === 'todos' ||
        (filter === 'sin-deuda' && client.debt === 0) ||
        (filter === 'con-deuda' && client.debt > 0) ||
        (filter === 'vencido' && client.status === 'vencido') ||
        (filter === 'riesgo-alto' && (client.risk === 'alto' || client.risk === 'critico'))
      const matchesSearch =
        !term ||
        client.business.toLowerCase().includes(term) ||
        client.name.toLowerCase().includes(term) ||
        client.document.includes(term) ||
        client.phone.replace(/\s/g, '').includes(term.replace(/\s/g, ''))
      return matchesFilter && matchesSearch
    })
  }, [search, filter])

  return (
    <div>
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h2 className="font-h1-display text-h1-display font-bold text-on-surface tracking-tight">
            Clientes
          </h2>
          <p className="font-body-md text-body-md text-on-surface-variant mt-1">
            Gestione su cartera de clientes y evalúe su estado crediticio.
          </p>
        </div>
        <div className="flex flex-col sm:flex-row items-center gap-4 w-full md:w-auto">
          <div className="relative w-full sm:w-[320px]">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant">
              <Icon name="search" size="18px" />
            </span>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por nombre, DNI o teléfono..."
              className="w-full h-10 pl-10 pr-4 bg-surface-container-lowest border border-outline-variant rounded font-body-md text-body-md text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all"
            />
          </div>
          <Link
            to="/clientes/nuevo"
            className="w-full sm:w-auto h-10 px-5 bg-primary-container text-on-primary font-label-sm text-label-sm rounded flex items-center justify-center gap-2 shadow-sm hover:shadow-md hover:bg-primary transition-all whitespace-nowrap"
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            Registrar cliente
          </Link>
        </div>
      </div>

      {/* Quick filters */}
      <div className="flex overflow-x-auto pb-4 mb-4 gap-2 no-scrollbar w-full border-b border-outline-variant">
        {filters.map((item) => {
          const active = filter === item.key
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => setFilter(item.key)}
              className={`px-4 py-2 font-label-sm text-label-sm rounded-full border transition-colors whitespace-nowrap flex items-center gap-2 ${
                active
                  ? 'bg-surface-container-highest text-primary border-primary'
                  : 'bg-surface-container-lowest text-on-surface-variant border-outline-variant hover:bg-surface-container-low'
              }`}
            >
              {item.label}
              {item.count && (
                <span className="bg-primary text-on-primary text-[10px] px-1.5 py-0.5 rounded-full">
                  {item.count}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Table */}
      <div className="bg-surface-container-lowest rounded-lg border border-outline-variant shadow-sm overflow-hidden">
        <div className="overflow-x-auto w-full">
          <table className="w-full text-left border-collapse min-w-[900px]">
            <thead className="bg-surface-container-low border-b border-outline-variant">
              <tr>
                <th className="h-10 px-4 font-table-header text-table-header text-on-surface-variant whitespace-nowrap">Cliente</th>
                <th className="h-10 px-4 font-table-header text-table-header text-on-surface-variant whitespace-nowrap">DNI / RUC</th>
                <th className="h-10 px-4 font-table-header text-table-header text-on-surface-variant whitespace-nowrap">Teléfono</th>
                <th className="h-10 px-4 font-table-header text-table-header text-on-surface-variant text-center whitespace-nowrap">Compras</th>
                <th className="h-10 px-4 font-table-header text-table-header text-on-surface-variant text-right whitespace-nowrap">Deuda Actual</th>
                <th className="h-10 px-4 font-table-header text-table-header text-on-surface-variant whitespace-nowrap">Estado</th>
                <th className="h-10 px-4 font-table-header text-table-header text-on-surface-variant whitespace-nowrap">Riesgo (IA)</th>
                <th className="h-10 px-4 font-table-header text-table-header text-on-surface-variant text-right whitespace-nowrap">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant">
              {filtered.map((client) => {
                const status = statusMap[client.status]
                const risk = riskMap[client.risk]
                const vencido = client.status === 'vencido'
                return (
                  <tr
                    key={client.id}
                    className={`h-[56px] hover:bg-surface-container-low transition-colors group ${vencido ? 'bg-error-container/10' : ''}`}
                  >
                    <td className="px-4 align-middle">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-surface-container-high flex items-center justify-center text-primary font-bold text-xs">
                          {client.initials}
                        </div>
                        <div className="flex flex-col">
                          <span className="font-body-md text-body-md font-medium text-on-surface leading-tight">
                            {client.business}
                          </span>
                          <span className="font-label-sm text-label-sm text-on-surface-variant">
                            {client.name}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 align-middle font-body-md text-body-md text-on-surface-variant">
                      {client.document}
                    </td>
                    <td className="px-4 align-middle font-body-md text-body-md text-on-surface-variant">
                      {client.phone}
                    </td>
                    <td className="px-4 align-middle text-center font-body-md text-body-md text-on-surface">
                      {client.purchases}
                    </td>
                    <td className={`px-4 align-middle text-right font-body-md text-body-md font-medium ${vencido ? 'text-error' : client.debt === 0 ? 'text-on-surface-variant' : 'text-on-surface'}`}>
                      {formatCurrency(client.debt)}
                    </td>
                    <td className="px-4 align-middle">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full font-label-sm text-[11px] font-medium ${status.className}`}>
                        {status.label}
                        {client.status === 'vencido' ? ' (15d)' : ''}
                      </span>
                    </td>
                    <td className="px-4 align-middle">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-label-sm text-[11px] font-medium ${risk.className}`}>
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${
                            client.risk === 'alto' || client.risk === 'critico'
                              ? 'bg-error'
                              : client.risk === 'medio'
                                ? 'bg-secondary'
                                : 'bg-primary-fixed-dim'
                          }`}
                        />
                        {risk.label}
                      </span>
                    </td>
                    <td className="px-4 align-middle text-right">
                      <div className="flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Link
                          to={`/clientes/${client.id}`}
                          className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:text-primary hover:bg-surface-bright transition-colors"
                          title="Ver detalle"
                        >
                          <Icon name="visibility" size="20px" />
                        </Link>
                        <button
                          type="button"
                          className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:text-primary hover:bg-surface-bright transition-colors"
                          title="Editar"
                        >
                          <Icon name="edit" size="20px" />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-16 text-center text-on-surface-variant">
                    No se encontraron clientes
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="px-4 py-3 border-t border-outline-variant bg-surface-container-lowest flex items-center justify-between">
          <span className="font-label-sm text-label-sm text-on-surface-variant">
            Mostrando 1-5 de 245 clientes
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled
              className="w-8 h-8 rounded flex items-center justify-center border border-outline-variant text-on-surface-variant opacity-50"
            >
              <Icon name="chevron_left" size="18px" />
            </button>
            <button
              type="button"
              className="w-8 h-8 rounded flex items-center justify-center border border-outline-variant text-on-surface-variant hover:bg-surface-container-low transition-colors"
            >
              <Icon name="chevron_right" size="18px" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
