import { useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '@/components/ui/Icon'
import { reportsByPeriod } from '@/data/reportes'
import { useClientState } from '@/services/clientRepository'
import { useCreditState } from '@/services/creditRepository'
import { useReportsState } from '@/services/reportsRepository'
import { selectDashboardMetrics } from '@/services/dashboardSelectors'
import { selectSalesMetrics, useSalesState, type SalesPeriod } from '@/services/salesRepository'
import { formatCurrency } from '@/utils/format'

export default function ReportesPage() {
  const [period, setPeriod] = useState<SalesPeriod>('mes')
  const { clients } = useClientState()
  const { credits, payments } = useCreditState()
  const { sales } = useSalesState()
  const { report: portfolio } = useReportsState()
  const report = reportsByPeriod[period]
  const metrics = selectDashboardMetrics(credits, payments, clients, sales)
  const salesMetrics = selectSalesMetrics(sales, period)
  const riskGradient = `conic-gradient(#10b981 0% ${metrics.risk.low}%, #fe932c ${metrics.risk.low}% ${metrics.risk.low + metrics.risk.medium}%, #ef4444 ${metrics.risk.low + metrics.risk.medium}% 100%)`

  const exportReport = () => {
    const rows = [
      ['Reporte', report.label],
      ['Ventas totales', salesMetrics.total],
      ['Cartera fiada actual', metrics.totalPending],
      ['Total recuperado acumulado', metrics.totalRecovered],
      ['Monto vencido actual', metrics.totalOverdue],
      ['Tasa de morosidad actual', `${metrics.delinquencyRate}%`],
      [],
      ...(portfolio ? [
        ['Cartera por cliente', 'Deuda', 'Vencido', 'Fiados', 'Vencidos'],
        ...portfolio.clients.map((client) => [
          client.clientName,
          client.totalPending,
          client.totalOverdue,
          client.activeCredits,
          client.overdueCredits,
        ]),
        [],
      ] : []),
      ['Producto', 'Cantidad', 'Ingresos'],
      ...salesMetrics.topProducts.map((product) => [product.name, product.quantity, product.revenue]),
    ]
    const csv = rows.map((row) => row.join(',')).join('\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `reporte-${period}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  const kpis = [
    { label: 'Ventas totales (S/.)', value: salesMetrics.total, trend: salesMetrics.trend, tone: salesMetrics.trend >= 0 ? 'text-emerald-600' : 'text-error' },
    { label: 'Cartera fiada actual (S/.)', value: metrics.totalPending, detail: `${metrics.activeCredits} activos`, tone: 'text-on-surface-variant' },
    { label: 'Recuperado acumulado (S/.)', value: metrics.totalRecovered, detail: `${payments.length} pagos`, tone: 'text-emerald-600' },
    { label: 'Monto vencido actual (S/.)', value: metrics.totalOverdue, detail: 'de cartera', tone: metrics.totalOverdue > 0 ? 'text-error' : 'text-emerald-600' },
  ]

  return (
    <div>
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
        <div>
          <h1 className="font-h1-display text-h1-display text-on-background">Panel de Reportes</h1>
          <p className="font-body-md text-on-surface-variant mt-1">Ventas, cartera y métricas de riesgo actualizadas en tiempo real.</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <select value={period} onChange={(event) => setPeriod(event.target.value as SalesPeriod)} className="bg-surface-container-lowest border border-outline-variant text-on-surface-variant py-2 px-4 rounded-lg focus:ring-2 focus:ring-primary shadow-sm">
            <option value="hoy">Hoy</option><option value="semana">Esta semana</option><option value="mes">Este mes</option>
          </select>
          <button type="button" onClick={exportReport} className="flex items-center gap-2 bg-primary-container text-on-primary font-label-sm px-4 py-2 rounded-lg hover:shadow-md">
            <Icon name="download" size="18px" /> Exportar reporte
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="bg-surface-container-lowest p-card-padding rounded-xl shadow-sm border border-surface-container-high flex flex-col justify-between">
            <p className="font-label-sm text-label-sm text-on-surface-variant mb-2">{kpi.label}</p>
            <div className="flex items-end gap-2">
              <h3 className="font-h2-headline text-h2-headline text-on-background">{kpi.value.toLocaleString('es-PE')}</h3>
               <span className={`font-label-sm text-label-sm flex items-center mb-1 ${kpi.tone}`}>
                 {kpi.trend !== undefined ? <><Icon name={kpi.trend < 0 ? 'trending_down' : 'trending_up'} size="14px" /> {Math.abs(kpi.trend)}%</> : kpi.detail}
               </span>
            </div>
          </div>
        ))}
        <div className="bg-surface-container-lowest p-card-padding rounded-xl shadow-sm border border-surface-container-high relative overflow-hidden">
          <div className="absolute -right-4 -bottom-4 w-24 h-24 bg-error-container rounded-full opacity-20 blur-xl" />
          <p className="font-label-sm text-label-sm text-on-surface-variant mb-2">Tasa de morosidad</p>
          <div className="flex items-end gap-2 relative"><h3 className="font-h2-headline text-h2-headline text-error">{metrics.delinquencyRate}%</h3><span className="font-label-sm text-label-sm text-on-surface-variant mb-1">Actual</span></div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <section className="bg-surface-container-lowest p-card-padding rounded-xl shadow-sm border border-surface-container-high lg:col-span-2 flex flex-col">
          <h3 className="font-h3-title text-h3-title text-on-background mb-6">Ventas al contado vs. ventas fiadas</h3>
          <div className="relative flex-1 min-h-[300px] flex items-end justify-around gap-3 px-2 pb-6">
            <div className="absolute inset-0 pb-8 pt-2 flex flex-col justify-between pointer-events-none">{[1, 2, 3, 4].map((line) => <div key={line} className="border-b border-outline-variant border-dashed opacity-30" />)}</div>
            {salesMetrics.bars.map((bar) => (
              <div key={bar.label} className="flex flex-col items-center gap-2 z-10 flex-1 max-w-28">
                <div className="flex items-end justify-center gap-1 h-[210px] w-full">
                  <div className="w-7 md:w-10 bg-primary rounded-t-sm hover:opacity-80" style={{ height: `${bar.cash}%` }} title={`Contado: ${bar.cash}%`} />
                  <div className="w-7 md:w-10 bg-secondary-container rounded-t-sm hover:opacity-80" style={{ height: `${bar.credit}%` }} title={`Fiado: ${bar.credit}%`} />
                </div>
                <span className="font-label-sm text-label-sm text-on-surface-variant">{bar.label}</span>
              </div>
            ))}
          </div>
          <div className="flex justify-center gap-6 mt-4 border-t border-surface-container-high pt-4">
            <Legend color="bg-primary" label="Contado" /><Legend color="bg-secondary-container" label="Fiado" />
          </div>
        </section>

        <section className="bg-surface-container-lowest p-card-padding rounded-xl shadow-sm border border-surface-container-high flex flex-col relative overflow-hidden">
          <div className="absolute -right-12 -top-12 w-40 h-40 bg-surface-container rounded-full opacity-50" />
          <h3 className="font-h3-title text-h3-title text-on-background mb-6 relative">Clientes según nivel de riesgo</h3>
          <div className="flex-1 flex items-center justify-center min-h-[250px]">
            <div className="relative w-48 h-48 rounded-full flex items-center justify-center" style={{ background: riskGradient }}>
               <div className="w-32 h-32 bg-surface-container-lowest rounded-full flex flex-col items-center justify-center shadow-inner"><span className="font-h2-headline text-h2-headline">{metrics.risk.total}</span><span className="font-label-sm text-label-sm text-on-surface-variant">Total</span></div>
            </div>
          </div>
          <div className="flex flex-col gap-3 mt-6">
             <RiskLegend color="bg-emerald-500" label="Riesgo Bajo" value={metrics.risk.low} />
             <RiskLegend color="bg-secondary-container" label="Riesgo Medio" value={metrics.risk.medium} />
             <RiskLegend color="bg-red-500" label="Riesgo Alto" value={metrics.risk.high} />
          </div>
        </section>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <section className="bg-surface-container-lowest p-card-padding rounded-xl shadow-sm border border-surface-container-high flex flex-col">
          <h3 className="font-h3-title text-h3-title text-on-background mb-1">Cartera de fiados por cliente</h3>
          <p className="font-label-sm text-label-sm text-on-surface-variant mb-6">
            {portfolio?.summary?.activeCredits ?? 0} fiados activos · {portfolio?.summary?.overdueCredits ?? 0} vencidos · {portfolio?.summary?.dueSoonCredits ?? 0} por vencer (≤5 días)
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-left min-w-[560px]">
              <thead><tr className="border-b border-surface-container-high"><th className="font-table-header text-table-header text-on-surface-variant py-3 px-2">CLIENTE</th><th className="font-table-header text-table-header text-on-surface-variant py-3 px-2 text-right">DEUDA</th><th className="font-table-header text-table-header text-on-surface-variant py-3 px-2 text-right">VENCIDO</th><th className="font-table-header text-table-header text-on-surface-variant py-3 px-2 text-center">FIADOS</th><th className="font-table-header text-table-header text-on-surface-variant py-3 px-2 text-center">MORA</th></tr></thead>
              <tbody>
                {portfolio?.clients.map((client) => (
                  <tr key={client.clientId} className="border-b border-surface-container-high last:border-0 hover:bg-surface-container-low h-[56px]">
                    <td className="py-3 px-2"><p className="font-medium text-on-background">{client.clientName}</p>{client.businessName && <p className="font-label-sm text-on-surface-variant">{client.businessName}</p>}</td>
                    <td className="py-3 px-2 text-right font-semibold text-primary">{formatCurrency(client.totalPending)}</td>
                    <td className={`py-3 px-2 text-right ${client.totalOverdue > 0 ? 'text-error font-medium' : 'text-on-surface-variant'}`}>{client.totalOverdue > 0 ? formatCurrency(client.totalOverdue) : '—'}</td>
                    <td className="py-3 px-2 text-center">{client.activeCredits}</td>
                    <td className="py-3 px-2 text-center">{client.overdueCredits > 0 ? <span className="px-2 py-1 rounded text-xs font-semibold bg-error-container text-on-error-container">{client.overdueCredits} vencido{client.overdueCredits > 1 ? 's' : ''}</span> : <span className="px-2 py-1 rounded text-xs font-semibold bg-green-50 text-green-700">Al día</span>}</td>
                  </tr>
                ))}
                {(!portfolio || portfolio.clients.length === 0) && <tr><td colSpan={5} className="py-12 text-center text-on-surface-variant">No hay fiados registrados en la cartera.</td></tr>}
              </tbody>
            </table>
          </div>
        </section>

        <section className="bg-surface-container-lowest p-card-padding rounded-xl shadow-sm border border-surface-container-high flex flex-col">
          <div className="flex justify-between items-center mb-6"><h3 className="font-h3-title text-h3-title text-on-background">Top 5 productos más vendidos</h3><Link to="/productos" className="font-label-sm text-label-sm text-primary hover:underline">Ver todos</Link></div>
          <div className="overflow-x-auto">
            <table className="w-full text-left min-w-[500px]">
              <thead><tr className="border-b border-surface-container-high"><th className="font-table-header text-table-header text-on-surface-variant py-3 px-2">PRODUCTO</th><th className="font-table-header text-table-header text-on-surface-variant py-3 px-2 text-right">CANTIDAD</th><th className="font-table-header text-table-header text-on-surface-variant py-3 px-2 text-right">INGRESOS</th></tr></thead>
              <tbody>
                {salesMetrics.topProducts.map((product) => <tr key={product.name} className="border-b border-surface-container-high last:border-0 hover:bg-surface-container-low h-[56px]"><td className="py-3 px-2"><div className="flex items-center gap-3"><div className="w-10 h-10 rounded-md bg-surface-container flex items-center justify-center text-primary font-bold">{product.name[0]}</div><div><p className="font-medium text-on-background">{product.name}</p><p className="font-label-sm text-on-surface-variant">Categoría: {product.category}</p></div></div></td><td className="py-3 px-2 text-right">{product.quantity.toLocaleString('es-PE')}</td><td className="py-3 px-2 text-right font-semibold text-primary">{formatCurrency(product.revenue)}</td></tr>)}
                {salesMetrics.topProducts.length === 0 && <tr><td colSpan={3} className="py-12 text-center text-on-surface-variant">No hay ventas registradas en este período.</td></tr>}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  )
}

function Legend({ color, label }: { color: string; label: string }) {
  return <div className="flex items-center gap-2"><span className={`w-3 h-3 rounded-full ${color}`} /><span className="font-label-sm text-label-sm text-on-surface-variant">{label}</span></div>
}

function RiskLegend({ color, label, value }: { color: string; label: string; value: number }) {
  return <div className="flex justify-between items-center"><Legend color={color} label={label} /><span className="font-label-sm text-label-sm font-semibold">{value}%</span></div>
}
