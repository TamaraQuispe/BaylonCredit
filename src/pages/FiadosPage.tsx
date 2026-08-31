import { useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '@/components/ui/Icon'
import Button from '@/components/ui/Button'
import { formatCurrency } from '@/utils/format'
import { useCreditState } from '@/services/creditRepository'
import type { RiskLevel, FiadoStatus } from '@/types'

type StatusFilter = 'todos' | FiadoStatus

type FiadoTone = 'primary-fixed' | 'highest' | 'error-container' | 'secondary-container'

const statToneClasses: Record<FiadoTone, { icon: string; value: string }> = {
  'primary-fixed': { icon: 'bg-primary-fixed text-on-primary-fixed', value: 'text-on-surface' },
  highest: { icon: 'bg-surface-container-highest text-primary', value: 'text-on-surface' },
  'error-container': { icon: 'bg-error-container text-on-error-container', value: 'text-error' },
  'secondary-container': { icon: 'bg-secondary-container text-on-secondary-container', value: 'text-on-surface' },
}

const riskBadge: Record<RiskLevel, string> = {
  'muy-bajo': 'bg-surface-container text-on-surface-variant',
  bajo: 'bg-surface-container text-primary',
  medio: 'bg-secondary-fixed text-on-secondary-fixed-variant',
  alto: 'bg-error-container text-on-error-container',
  critico: 'bg-error-container text-error',
}

const statusBadge: Record<FiadoStatus, { className: string; label: string; dot?: string; icon?: string }> = {
  'al-dia': {
    className: 'bg-surface-container-highest text-primary',
    label: 'Al día',
    dot: 'bg-primary',
  },
  vencido: {
    className: 'bg-error-container text-on-error-container',
    label: 'Vencido',
    dot: 'bg-error',
  },
  'proximo-a-vencer': {
    className: 'bg-secondary-fixed text-on-secondary-fixed-variant',
    label: 'Próximo',
    dot: 'bg-secondary',
  },
  pagado: {
    className: 'bg-surface-variant text-on-surface-variant',
    label: 'Pagado',
    icon: 'check',
  },
}

const statusFilters: { key: StatusFilter; label: string }[] = [
  { key: 'todos', label: 'Todos' },
  { key: 'al-dia', label: 'Al día' },
  { key: 'proximo-a-vencer', label: 'Próximos a vencer' },
  { key: 'vencido', label: 'Vencidos' },
  { key: 'pagado', label: 'Pagados' },
]

export default function FiadosPage() {
  const [filter, setFilter] = useState<StatusFilter>('todos')
  const { credits } = useCreditState()

  const filtered = filter === 'todos' ? credits : credits.filter((credit) => credit.status === filter)
  const activeCredits = credits.filter((credit) => credit.status !== 'pagado')
  const totalToCollect = activeCredits.reduce((sum, credit) => sum + credit.pendingAmount, 0)
  const currentDebt = activeCredits
    .filter((credit) => ['al-dia', 'proximo-a-vencer'].includes(credit.status))
    .reduce((sum, credit) => sum + credit.pendingAmount, 0)
  const overdueDebt = activeCredits
    .filter((credit) => credit.status === 'vencido')
    .reduce((sum, credit) => sum + credit.pendingAmount, 0)
  const delinquentClients = new Set(
    activeCredits
      .filter((credit) => credit.status === 'vencido')
      .map((credit) => credit.clientId ?? credit.client.name),
  ).size
  const stats = [
    {
      label: 'Total por cobrar',
      value: formatCurrency(totalToCollect),
      detail: `En ${activeCredits.length} fiados activos`,
      icon: 'account_balance_wallet',
      tone: 'primary-fixed' as const,
    },
    {
      label: 'Deuda al día',
      value: formatCurrency(currentDebt),
      detail: totalToCollect > 0 ? `${Math.round((currentDebt / totalToCollect) * 100)}% del total` : 'Sin deuda activa',
      icon: 'check_circle',
      tone: 'highest' as const,
    },
    {
      label: 'Deuda vencida',
      value: formatCurrency(overdueDebt),
      detail: overdueDebt > 0 ? 'Requiere atención' : 'Sin deuda vencida',
      icon: 'warning',
      tone: 'error-container' as const,
    },
    {
      label: 'Clientes morosos',
      value: String(delinquentClients),
      detail: delinquentClients > 0 ? 'Requieren gestión inmediata' : 'Sin clientes morosos',
      icon: 'group_off',
      tone: 'secondary-container' as const,
    },
  ]

  const exportCredits = () => {
    const rows = [
      ['Código', 'Cliente', 'Monto original', 'Saldo pendiente', 'Fecha', 'Vencimiento', 'Estado', 'Riesgo'],
      ...credits.map((credit) => [
        credit.code,
        credit.client.business,
        credit.originalAmount,
        credit.pendingAmount,
        credit.createdAt,
        credit.dueAt,
        credit.status,
        credit.risk,
      ]),
    ]
    const url = URL.createObjectURL(
      new Blob([rows.map((row) => row.join(',')).join('\n')], { type: 'text/csv;charset=utf-8' }),
    )
    const link = document.createElement('a')
    link.href = url
    link.download = 'fiados.csv'
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col md:flex-row justify-between items-end gap-4">
        <div>
          <h2 className="font-h1-display text-h1-display text-on-surface mb-2">Control de fiados</h2>
          <p className="font-body-md text-body-md text-on-surface-variant">
            Monitorea y gestiona los créditos pendientes de tus clientes.
          </p>
        </div>
        <Link to="/fiados/nuevo">
          <Button variant="primary-container" size="md">
            <span className="material-symbols-outlined text-[18px]">add</span>
            Nuevo Fiado
          </Button>
        </Link>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-gutter">
        {stats.map((stat) => {
          const tone = statToneClasses[stat.tone as FiadoTone]
          return (
            <div
              key={stat.label}
              className="bg-surface-container-lowest p-card-padding rounded-xl border border-outline-variant shadow-sm flex flex-col justify-between h-32"
            >
              <div className="flex justify-between items-start">
                <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">
                  {stat.label}
                </span>
                {stat.icon && (
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${tone.icon}`}>
                    <Icon name={stat.icon} size="18px" />
                  </div>
                )}
              </div>
              <div>
                <h3 className={`font-h2-headline text-h2-headline ${stat.label === 'Deuda vencida' ? 'text-error' : 'text-on-surface'}`}>
                  {stat.value}
                </h3>
                <div className="flex items-center gap-1 mt-1 text-on-surface-variant">
                  {stat.label === 'Deuda vencida' && (
                    <Icon name="trending_up" size="14px" className="text-error" />
                  )}
                  <span className="font-label-sm text-label-sm text-on-surface-variant">{stat.detail}</span>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Table panel */}
      <div className="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm overflow-hidden flex flex-col">
        <div className="p-card-padding border-b border-outline-variant flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-surface-bright">
          <div className="flex flex-wrap gap-2">
            {statusFilters.map((item) => {
              const active = filter === item.key
              return (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => setFilter(item.key)}
                  className={`px-4 py-1.5 rounded-full font-label-sm text-label-sm transition-colors border ${
                    active
                      ? 'bg-primary-container text-on-primary-container border-transparent'
                      : 'bg-surface-container-lowest text-on-surface-variant border-outline-variant hover:bg-surface-container-high'
                  }`}
                >
                  {item.label}
                </button>
              )
            })}
          </div>
          <div className="flex gap-2 w-full md:w-auto">
            <button
              type="button"
              className="flex items-center justify-center gap-2 px-3 py-1.5 rounded-lg border border-outline-variant text-on-surface-variant font-label-sm hover:bg-surface-container-high transition-colors w-full md:w-auto"
            >
              <Icon name="filter_list" size="18px" />
              Más filtros
            </button>
            <button
              type="button"
              onClick={exportCredits}
              className="flex items-center justify-center gap-2 px-3 py-1.5 rounded-lg border border-outline-variant text-on-surface-variant font-label-sm hover:bg-surface-container-high transition-colors w-full md:w-auto"
            >
              <Icon name="download" size="18px" />
              Exportar
            </button>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[1000px]">
            <thead>
              <tr className="bg-surface-container-low border-b border-outline-variant">
                <th className="py-3 px-4 font-table-header text-table-header text-on-surface-variant uppercase">Cliente</th>
                <th className="py-3 px-4 font-table-header text-table-header text-on-surface-variant uppercase text-right">Monto Original</th>
                <th className="py-3 px-4 font-table-header text-table-header text-on-surface-variant uppercase text-right">Saldo Pendiente</th>
                <th className="py-3 px-4 font-table-header text-table-header text-on-surface-variant uppercase">Fecha Fiado</th>
                <th className="py-3 px-4 font-table-header text-table-header text-on-surface-variant uppercase">Vencimiento</th>
                <th className="py-3 px-4 font-table-header text-table-header text-on-surface-variant uppercase">Estado</th>
                <th className="py-3 px-4 font-table-header text-table-header text-on-surface-variant uppercase text-center">Riesgo IA</th>
                <th className="py-3 px-4 font-table-header text-table-header text-on-surface-variant uppercase text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="font-body-md text-body-md text-on-surface divide-y divide-outline-variant">
              {filtered.map((row) => {
                const st = statusBadge[row.status]
                const overduedays = row.status === 'vencido' ? 15 : row.status === 'proximo-a-vencer' ? 4 : null
                const pagado = row.status === 'pagado'
                return (
                  <tr
                    key={row.id}
                    className={`hover:bg-surface-container-low transition-colors h-[56px] ${pagado ? 'opacity-70' : ''}`}
                  >
                    <td className="py-2 px-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-surface-container-high flex items-center justify-center text-primary font-bold text-xs">
                          {row.client.initials}
                        </div>
                        <div>
                          <p className={`font-medium ${pagado ? 'text-on-surface-variant' : 'text-on-surface'}`}>
                            {row.client.name}
                          </p>
                          <p className="text-xs text-on-surface-variant">{row.client.business}</p>
                        </div>
                      </div>
                    </td>
                    <td className={`py-2 px-4 text-right ${pagado ? 'text-on-surface-variant' : ''}`}>
                      {formatCurrency(row.originalAmount)}
                    </td>
                    <td className={`py-2 px-4 text-right font-medium ${row.status === 'vencido' ? 'text-error' : pagado ? 'text-on-surface-variant' : ''}`}>
                      {formatCurrency(row.pendingAmount)}
                    </td>
                    <td className="py-2 px-4 text-on-surface-variant">{row.createdAt}</td>
                    <td className={`py-2 px-4 ${row.status === 'vencido' ? 'text-error font-medium' : row.status === 'proximo-a-vencer' ? 'text-secondary font-medium' : 'text-on-surface-variant'}`}>
                      {row.dueAt}
                    </td>
                    <td className="py-2 px-4">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full font-label-sm ${st.className}`}>
                        {st.icon ? (
                          <Icon name={st.icon} size="14px" />
                        ) : (
                          <span className={`w-1.5 h-1.5 rounded-full ${st.dot}`} />
                        )}
                        {overduedays !== null ? `${st.label} (${overduedays > 0 ? overduedays + 'd' : ''})` : st.label}
                      </span>
                    </td>
                    <td className="py-2 px-4 text-center">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${pagado ? 'bg-surface-container text-on-surface-variant' : riskBadge[row.risk]}`}>
                        {pagado ? '-' : riskLabel(row.risk)}
                      </span>
                    </td>
                    <td className="py-2 px-4 text-right">
                      <Link
                        to={`/fiados/${row.id}`}
                        className="p-1 inline-flex text-on-surface-variant hover:text-primary transition-colors"
                        aria-label="Ver detalle"
                      >
                        <Icon name="more_vert" size="20px" />
                      </Link>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="p-4 border-t border-outline-variant flex items-center justify-between bg-surface-bright">
          <span className="font-label-sm text-label-sm text-on-surface-variant">
            Mostrando {filtered.length} de {credits.length} fiados
          </span>
          <div className="flex gap-1">
            <button
              type="button"
              disabled
              className="w-8 h-8 rounded flex items-center justify-center border border-outline-variant text-on-surface-variant opacity-50"
            >
              <Icon name="chevron_left" size="18px" />
            </button>
            <button type="button" className="w-8 h-8 rounded flex items-center justify-center bg-primary-container text-on-primary-container font-label-sm">1</button>
            <button type="button" className="w-8 h-8 rounded flex items-center justify-center border border-outline-variant text-on-surface hover:bg-surface-container-high font-label-sm">2</button>
            <button type="button" className="w-8 h-8 rounded flex items-center justify-center border border-outline-variant text-on-surface hover:bg-surface-container-high font-label-sm">3</button>
            <span className="w-8 h-8 flex items-center justify-center text-on-surface-variant">...</span>
            <button type="button" className="w-8 h-8 rounded flex items-center justify-center border border-outline-variant text-on-surface-variant hover:bg-surface-container-high">
              <Icon name="chevron_right" size="18px" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function riskLabel(level: RiskLevel): string {
  switch (level) {
    case 'critico':
      return 'Crítico'
    case 'alto':
      return 'Alto'
    case 'medio':
      return 'Medio'
    case 'bajo':
      return 'Bajo'
    case 'muy-bajo':
      return 'Muy bajo'
  }
}
