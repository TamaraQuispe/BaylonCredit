import { useState } from 'react'
import { Link, Navigate, useParams } from 'react-router-dom'
import Icon from '@/components/ui/Icon'
import { clientProfile, clients } from '@/data/clientes'
import { formatCurrency } from '@/utils/format'
import { useCreditState } from '@/services/creditRepository'

type HistoryTab = 'compras' | 'fiados' | 'pagos'

const tabs: { key: HistoryTab; label: string }[] = [
  { key: 'compras', label: 'Historial de compras' },
  { key: 'fiados', label: 'Historial de fiados' },
  { key: 'pagos', label: 'Historial de pagos' },
]

export default function DetalleClientePage() {
  const [activeTab, setActiveTab] = useState<HistoryTab>('compras')
  const { id } = useParams()
  const { credits } = useCreditState()
  const client = clients.find((item) => item.id === id)

  if (!client) return <Navigate to="/clientes" replace />

  const clientCredits = credits.filter((credit) => credit.clientId === client.id)
  const latestEvaluation = clientCredits.find((credit) => credit.evaluation)?.evaluation
  const scoreByRisk = { 'muy-bajo': 92, bajo: 84, medio: 68, alto: 50, critico: 36 }
  const score = latestEvaluation?.score ?? scoreByRisk[client.risk]
  const risk = latestEvaluation?.risk.toUpperCase() ?? client.risk.toUpperCase()
  const additionalDebt = clientCredits.reduce((sum, credit) => sum + credit.pendingAmount, 0)
  const totalFiado = clientCredits.reduce((sum, credit) => sum + credit.originalAmount, 0)
  const displayedHistory =
    activeTab === 'compras'
      ? clientProfile.history
      : activeTab === 'fiados'
        ? clientCredits.map((credit) => ({
            date: credit.createdAt,
            description: `Fiado ${credit.code}`,
            amount: credit.originalAmount,
            status: credit.status === 'pagado' ? 'Pagado' : 'Fiado Pdto.',
          }))
        : clientCredits.flatMap((credit) =>
            credit.timeline
              .filter((entry) => entry.type === 'payment')
              .map((entry) => ({
                date: entry.date,
                description: `${entry.title} · ${credit.code}`,
                amount: Math.abs(entry.amount),
                status: 'Pagado' as const,
              })),
          )

  const kpis = [
    { label: 'Deuda actual', value: formatCurrency(client.debt + additionalDebt), tone: 'text-error' },
    { label: 'Total comprado', value: `${client.purchases} compras`, tone: 'text-on-background' },
    { label: 'Total fiado', value: formatCurrency(totalFiado), tone: 'text-on-background' },
    { label: 'Fiados pagados', value: String(clientCredits.filter((credit) => credit.status === 'pagado').length), tone: 'text-emerald-600' },
    { label: 'Pagos atrasados', value: String(clientCredits.filter((credit) => credit.status === 'vencido').length), tone: 'text-amber-600' },
  ]

  return (
    <div>
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-surface-container-high flex items-center justify-center text-primary-container font-h2-headline text-h2-headline">
            {client.initials}
          </div>
          <div>
            <h2 className="font-h1-display text-h3-title font-bold text-on-background">
              {client.name}
            </h2>
            <div className="flex flex-wrap items-center gap-4 mt-1 text-on-surface-variant font-body-md text-body-md">
              <span className="flex items-center gap-1">
                <Icon name="badge" size="18px" /> DNI/RUC: {client.document}
              </span>
              <span className="flex items-center gap-1">
                <Icon name="call" size="18px" /> {client.phone}
              </span>
              <span className="flex items-center gap-1">
                <Icon name="calendar_today" size="18px" /> Cliente registrado
              </span>
            </div>
          </div>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link
            to="/evaluacion-crediticia"
            className="bg-white border border-outline-variant text-primary-container hover:bg-surface-container-low transition-colors px-4 py-2 rounded font-label-sm text-label-sm font-semibold flex items-center gap-2"
          >
            <Icon name="psychology_alt" size="18px" /> Evaluar nuevamente
          </Link>
          <Link
            to={`/fiados/nuevo?cliente=${client.id}`}
            className="bg-primary-container text-white hover:bg-primary transition-colors shadow-sm px-4 py-2 rounded font-label-sm text-label-sm font-semibold flex items-center gap-2"
          >
            <Icon name="receipt_long" size="18px" /> Registrar fiado
          </Link>
          <Link
            to="/pagos/nuevo"
            className="bg-white border border-outline-variant text-primary-container hover:bg-surface-container-low transition-colors px-4 py-2 rounded font-label-sm text-label-sm font-semibold flex items-center gap-2"
          >
            <Icon name="payments" size="18px" /> Registrar pago
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        {kpis.map((kpi) => (
          <div
            key={kpi.label}
            className="bg-surface-container-lowest p-card-padding rounded-lg border border-surface-container-high shadow-sm flex flex-col justify-center"
          >
            <p className="font-label-sm text-label-sm text-on-surface-variant mb-1 uppercase tracking-wider">
              {kpi.label}
            </p>
            <p className={`font-h2-headline text-h2-headline font-bold ${kpi.tone}`}>{kpi.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <section className="bg-surface-container-lowest p-card-padding rounded-lg border border-primary/20 shadow-sm relative overflow-hidden">
          <div className="absolute top-0 left-0 w-1 h-full bg-primary-container" />
          <h3 className="font-h3-title text-h3-title text-primary-container flex items-center gap-2 mb-6">
            <Icon name="psychology_alt" /> Evaluación crediticia
          </h3>

          <div className="flex justify-center mb-6 relative">
            <svg className="w-40 h-40 -rotate-90" viewBox="0 0 36 36" aria-label={`Puntaje ${score}`}>
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="#e5eeff"
                strokeWidth="3.8"
              />
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="#10b981"
                strokeWidth="3.8"
                strokeLinecap="round"
                strokeDasharray={`${score}, 100`}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="font-h1-display text-h1-display text-primary-container">
                {score}
              </span>
              <span className="font-label-sm text-[10px] text-on-surface-variant uppercase tracking-wide">
                Puntaje Baylón
              </span>
            </div>
          </div>

          <div className="space-y-4">
            <CreditRow label="Nivel de riesgo">
              <span className="bg-emerald-100 text-emerald-800 font-label-sm text-label-sm px-2 py-1 rounded font-bold">
                {risk}
              </span>
            </CreditRow>
            <CreditRow label="Probabilidad de impago">
              <span className="font-semibold text-on-background">{latestEvaluation?.defaultProbability ?? 100 - score}%</span>
            </CreditRow>
            <CreditRow label="Límite recomendado">
              <span className="font-bold text-primary-container">
                {formatCurrency(latestEvaluation?.recommendedLimit ?? Math.max(100, score * 10))}
              </span>
            </CreditRow>
          </div>

          {(latestEvaluation?.approved ?? !['alto', 'critico'].includes(client.risk)) && (
            <div className="mt-6 bg-surface-container-low p-4 rounded-lg border border-primary-fixed">
              <p className="font-body-md text-body-md font-medium text-primary-container flex items-start gap-2">
                <Icon name="check_circle" size="20px" />
                Cliente apto para recibir un nuevo fiado
              </p>
            </div>
          )}
          <p className="mt-6 font-label-sm text-label-sm text-outline italic text-xs">
            * Esta recomendación se genera a partir del historial. La decisión final corresponde al
            responsable del negocio.
          </p>
        </section>

        <section className="lg:col-span-2 bg-surface-container-lowest rounded-lg border border-surface-container-high shadow-sm flex flex-col overflow-hidden">
          <div className="flex border-b border-outline-variant/50 overflow-x-auto no-scrollbar">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={`px-6 py-4 font-label-sm text-label-sm whitespace-nowrap transition-colors ${
                  activeTab === tab.key
                    ? 'font-semibold text-primary-container border-b-2 border-primary-container bg-surface-container-low'
                    : 'font-medium text-on-surface-variant hover:text-primary-container hover:bg-surface-container-highest'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[620px]">
              <thead>
                <tr className="border-b border-surface-container-high">
                  <th className="py-3 px-6 font-table-header text-table-header text-on-surface-variant uppercase">Fecha</th>
                  <th className="py-3 px-6 font-table-header text-table-header text-on-surface-variant uppercase">Descripción</th>
                  <th className="py-3 px-6 font-table-header text-table-header text-on-surface-variant uppercase text-right">Monto</th>
                  <th className="py-3 px-6 font-table-header text-table-header text-on-surface-variant uppercase text-center">Estado</th>
                </tr>
              </thead>
              <tbody className="font-body-md text-body-md">
                {displayedHistory.map((entry) => (
                  <tr key={`${entry.date}-${entry.description}`} className="border-b border-surface-container-high hover:bg-surface-container-low transition-colors h-[56px] last:border-0">
                    <td className="py-3 px-6 text-on-background">{entry.date}</td>
                    <td className="py-3 px-6 text-on-background">{entry.description}</td>
                    <td className="py-3 px-6 text-on-background font-medium text-right">
                      {formatCurrency(entry.amount)}
                    </td>
                    <td className="py-3 px-6 text-center">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          entry.status === 'Pagado'
                            ? 'bg-surface-container-high text-primary-container'
                            : 'bg-error-container text-on-error-container'
                        }`}
                      >
                        {entry.status}
                      </span>
                    </td>
                  </tr>
                ))}
                {displayedHistory.length === 0 && (
                  <tr>
                    <td colSpan={4} className="py-12 px-6 text-center text-on-surface-variant">
                      No hay registros en este historial.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="p-4 border-t border-surface-container-high flex justify-center">
            <button
              type="button"
              className="text-primary-container font-label-sm text-label-sm font-semibold hover:underline flex items-center gap-1"
            >
              Ver historial completo <Icon name="arrow_forward" size="16px" />
            </button>
          </div>
        </section>
      </div>
    </div>
  )
}

function CreditRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between items-center border-b border-outline-variant/30 pb-2">
      <span className="font-body-md text-body-md text-on-surface-variant">{label}</span>
      {children}
    </div>
  )
}
