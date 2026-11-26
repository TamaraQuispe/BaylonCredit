import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '@/components/ui/Icon'
import CarteraUnavailableAlert from '@/components/ui/CarteraUnavailableAlert'
import type { Cliente } from '@/data/clientes'
import { formatCurrency, orDash } from '@/utils/format'
import { useClientState } from '@/services/clientRepository'
import { useCreditState } from '@/services/creditRepository'

type FilterKey = 'todos' | 'sin-deuda' | 'con-deuda' | 'vencido' | 'riesgo-alto'

const filters: { key: FilterKey; label: string }[] = [
  { key: 'todos', label: 'Todos los clientes' },
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

const balancesUnavailableStatus = {
  label: 'Sin datos',
  className: 'bg-surface-container text-on-surface-variant',
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
  const { clients } = useClientState()
  const { credits, balancesUnavailable } = useCreditState()
  const nameCounts = new Map<string, number>()
  for (const client of clients) {
    const name = client.business.trim().toLocaleLowerCase('es-PE')
    nameCounts.set(name, (nameCounts.get(name) ?? 0) + 1)
  }

  const displayedClients = clients.map((client) => {
    const clientCredits = credits.filter((credit) => credit.clientId === client.id)
    const debt = client.debt
    const latestEvaluation = clientCredits.find((credit) => credit.evaluation)?.evaluation
    const hasOverdue = clientCredits.some(
      (credit) => credit.status === 'vencido' && credit.pendingAmount > 0,
    )
    const status =
      clientCredits.length === 0
        ? client.status
        : hasOverdue
          ? 'vencido' as const
          : debt === 0
            ? 'sin-deuda' as const
            : 'pendiente' as const
    return {
      ...client,
      debt,
      purchases: client.purchases + clientCredits.length,
      status,
      risk: latestEvaluation?.risk ?? client.risk,
      hasEvaluation: latestEvaluation ? true : client.hasEvaluation,
    }
  })

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase()
    return displayedClients.filter((client) => {
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
  }, [displayedClients, search, filter])

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

      {balancesUnavailable && (
        <CarteraUnavailableAlert className="mb-4">
          Los saldos pendientes no están disponibles: se ocultan en lugar de mostrarse como S/
          0.00. Recarga la página para volver a intentarlo.
        </CarteraUnavailableAlert>
      )}

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
              {item.key === 'todos' && (
                <span className="bg-primary text-on-primary text-[10px] px-1.5 py-0.5 rounded-full">
                  {displayedClients.length}
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
                const status = balancesUnavailable ? balancesUnavailableStatus : statusMap[client.status]
                const risk = riskMap[client.risk]
                const vencido = client.status === 'vencido'
                const debtTone = balancesUnavailable
                  ? 'text-on-surface-variant'
                  : vencido
                    ? 'text-error'
                    : client.debt === 0
                      ? 'text-on-surface-variant'
                      : 'text-on-surface'
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
                          {(nameCounts.get(client.business.trim().toLocaleLowerCase('es-PE')) ?? 0) > 1 && (
                            <span className="text-xs text-secondary">Nombre compartido: identifica por DNI/RUC</span>
                          )}
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
                    <td className={`px-4 align-middle text-right font-body-md text-body-md font-medium ${debtTone}`}>
                      {orDash(formatCurrency(client.debt), balancesUnavailable)}
                    </td>
                    <td className="px-4 align-middle">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full font-label-sm text-[11px] font-medium ${status.className}`}>
                        {status.label}
                      </span>
                    </td>
                    <td className="px-4 align-middle">
                      {client.hasEvaluation ? (
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
                      ) : (
                        <span className="inline-flex px-2 py-0.5 rounded-full bg-surface-container text-on-surface-variant text-[11px] font-medium">
                          Sin evaluar
                        </span>
                      )}
                    </td>
                    <td className="px-4 align-middle text-right">
                      <div className="flex justify-end gap-1">
                        <Link
                          to={`/clientes/${client.id}`}
                          className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:text-primary hover:bg-surface-bright transition-colors"
                          title="Ver detalle"
                          aria-label={`Ver detalle de ${client.business}`}
                        >
                          <Icon name="visibility" size="20px" />
                        </Link>
                        <button
                          type="button"
                          disabled
                          className="w-8 h-8 rounded-full flex items-center justify-center text-outline opacity-50 cursor-not-allowed"
                          title="Edición no disponible en este MVP"
                          aria-label="Editar: no disponible en este MVP"
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
            Mostrando {filtered.length} de {clients.length} clientes
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
