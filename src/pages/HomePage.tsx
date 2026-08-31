import { Link } from 'react-router-dom'
import PageHeader from '@/components/layout/PageHeader'
import Button from '@/components/ui/Button'
import StatCard from '@/components/ui/StatCard'
import RiskBadge from '@/components/ui/RiskBadge'
import CurrencyDisplay from '@/components/ui/CurrencyDisplay'
import DataTable, { type Column } from '@/components/ui/DataTable'
import Icon from '@/components/ui/Icon'
import DonutChart from '@/components/dashboard/DonutChart'
import ActivityFeed from '@/components/dashboard/ActivityFeed'
import { homeStats } from '@/data/home'
import type { CustomerAttention } from '@/data/home'
import { useClientState } from '@/services/clientRepository'
import { useCreditState } from '@/services/creditRepository'
import { selectDashboardMetrics } from '@/services/dashboardSelectors'
import { formatCurrency } from '@/utils/format'

const attentionColumns: Column<CustomerAttention>[] = [
  {
    key: 'name',
    header: 'Cliente',
    cell: (row) => <span className="font-medium text-on-surface">{row.name}</span>,
  },
  {
    key: 'fiado',
    header: 'Fiado',
    cell: (row) => <span className="text-on-surface-variant">{row.fiado}</span>,
  },
  {
    key: 'amount',
    header: 'Monto',
    align: 'right',
    cell: (row) => <CurrencyDisplay value={row.amount} strong />,
  },
  {
    key: 'days',
    header: 'Días vencidos',
    align: 'center',
    cell: (row) => (
      <span className={row.daysOverdue > 15 ? 'text-error font-medium' : 'text-on-surface'}>
        {row.daysOverdue}
      </span>
    ),
  },
  {
    key: 'risk',
    header: 'Riesgo',
    cell: (row) => <RiskBadge level={row.risk} />,
  },
  {
    key: 'actions',
    header: '',
    align: 'right',
    cell: (row) => (
      <Link
        to={`/fiados/${row.id}`}
        className="inline-flex items-center gap-1 font-label-sm text-label-sm text-primary hover:underline"
      >
        Ver
        <Icon name="chevron_right" size="16px" />
      </Link>
    ),
  },
]

function Card({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="bg-surface-container-lowest rounded-lg shadow-sm border border-surface-container-high overflow-hidden">
      <div className="flex items-center justify-between px-6 pt-5 pb-3">
        <h3 className="font-h3-title text-h3-title text-on-surface">{title}</h3>
        {action}
      </div>
      <div className="px-6 pb-6">{children}</div>
    </section>
  )
}

export default function HomePage() {
  const { clients } = useClientState()
  const { credits, payments } = useCreditState()
  const metrics = selectDashboardMetrics(credits, payments, clients)
  const stats = [
    { ...homeStats[0], label: 'Ventas de hoy (demo)' },
    {
      label: 'Total fiado',
      value: formatCurrency(metrics.totalPending),
      detail: `En ${metrics.activeCredits} fiados activos`,
      icon: 'account_balance_wallet',
      iconTone: 'secondary' as const,
    },
    {
      label: 'Deuda vencida',
      value: formatCurrency(metrics.totalOverdue),
      detail: metrics.totalOverdue > 0 ? 'Requiere atención' : 'Sin deuda vencida',
      detailTone: metrics.totalOverdue > 0 ? 'negative' as const : 'positive' as const,
      icon: 'warning',
      iconTone: 'error' as const,
    },
    {
      label: 'Clientes con deuda',
      value: String(metrics.clientsWithDebt),
      detail: `${metrics.criticalClients} de riesgo alto`,
      icon: 'group_remove',
      iconTone: 'tertiary' as const,
    },
    {
      label: 'Pagos hoy',
      value: formatCurrency(metrics.paymentsToday),
      detail: 'Recibidos',
      icon: 'payments',
      iconTone: 'success' as const,
    },
  ]

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Buenos días, Administrador"
        subtitle="Aquí tienes un resumen de la actividad de hoy."
        actions={
          <Link to="/fiados/nuevo">
            <Button variant="primary-container" size="md">
              <span className="material-symbols-outlined text-[18px]">add</span>
              Nuevo Fiado
            </Button>
          </Link>
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {stats.map((stat) => (
          <StatCard key={stat.label} {...stat} />
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2">
          <Card
            title="Clientes que requieren atención"
            action={
              <Link
                to="/clientes"
                className="inline-flex items-center gap-1 font-label-sm text-label-sm text-primary hover:underline"
              >
                Ver todos
                <Icon name="chevron_right" size="16px" />
              </Link>
            }
          >
            <DataTable
              columns={attentionColumns}
              data={metrics.attention}
              rowKey={(row) => row.id}
              minWidth="min-w-[640px]"
            />
          </Card>
        </div>

        <div className="xl:col-span-1 flex flex-col gap-6">
          <Card title="Estado de los fiados">
            <DonutChart
              segments={metrics.fiadoSegments}
              centerValue={formatCurrency(metrics.totalPending)}
              centerLabel="en fiados"
            />
          </Card>
        </div>
      </div>

      <div className="w-full">
        <Card title="Actividad reciente">
          <ActivityFeed items={metrics.recentActivity} />
        </Card>
      </div>
    </div>
  )
}
