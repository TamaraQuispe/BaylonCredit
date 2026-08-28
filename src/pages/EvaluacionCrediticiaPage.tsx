import { useState } from 'react'
import Icon from '@/components/ui/Icon'
import { creditProfiles } from '@/data/scoring'
import { formatCurrency } from '@/utils/format'

const factorTone = {
  primary: 'bg-primary',
  warning: 'bg-yellow-400',
  success: 'bg-green-500',
}

const riskStyle = {
  Bajo: 'bg-green-50 text-green-700',
  Medio: 'bg-yellow-50 text-yellow-700',
  Alto: 'bg-error-container text-on-error-container',
}

export default function EvaluacionCrediticiaPage() {
  const [profileId, setProfileId] = useState(creditProfiles[0].id)
  const [adjustments, setAdjustments] = useState<Record<string, number>>({})
  const profile = creditProfiles.find((item) => item.id === profileId) ?? creditProfiles[0]
  const score = Math.min(profile.score + (adjustments[profile.id] ?? 0), 100)

  const runEvaluation = () => {
    setAdjustments((current) => ({ ...current, [profile.id]: (current[profile.id] ?? 0) + 1 }))
  }

  const downloadReport = () => {
    const report = [
      'BaylonCredit IA - Evaluación Crediticia',
      `Cliente: ${profile.name}`,
      `Documento: ${profile.document}`,
      `Puntaje: ${score}`,
      `Riesgo: ${profile.risk}`,
      `Límite recomendado: ${formatCurrency(profile.recommendedLimit)}`,
      `Tasa sugerida: ${profile.suggestedRate}% mensual`,
    ].join('\n')
    const url = URL.createObjectURL(new Blob([report], { type: 'text/plain;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `evaluacion-${profile.document}.txt`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="max-w-7xl mx-auto w-full">
      <div className="flex flex-col md:flex-row justify-between md:items-end gap-4 mb-8">
        <div>
          <h2 className="font-h1-display text-h1-display text-on-surface mb-2">Evaluación Crediticia IA</h2>
          <p className="font-body-lg text-body-lg text-on-surface-variant">
            Análisis de riesgo en tiempo real basado en historial transaccional.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button type="button" onClick={downloadReport} className="flex items-center gap-2 px-4 py-2 bg-white border border-outline-variant text-primary rounded font-label-sm text-label-sm shadow-sm hover:bg-surface-container-low">
            <Icon name="download" size="18px" /> Descargar Reporte
          </button>
          <button type="button" onClick={runEvaluation} className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded font-label-sm text-label-sm shadow-sm hover:bg-primary-container">
            <Icon name="add" size="18px" /> Nueva Evaluación
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="flex flex-col gap-6">
          <section className="bg-white rounded-xl shadow-sm border border-outline-variant p-card-padding">
            <label className="block font-label-sm text-label-sm text-on-surface-variant mb-2" htmlFor="credit-client">Cliente a evaluar</label>
            <select id="credit-client" value={profileId} onChange={(event) => setProfileId(event.target.value)} className="w-full bg-surface-container-low border border-outline-variant rounded-lg px-4 py-3 text-on-surface focus:ring-2 focus:ring-primary outline-none">
              {creditProfiles.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
            <div className="mt-4 pt-4 border-t border-outline-variant flex items-center gap-4">
              <div className="w-12 h-12 bg-surface-variant rounded-full flex items-center justify-center text-primary font-bold text-lg">{profile.initials}</div>
              <div>
                <h4 className="font-body-lg text-body-lg font-semibold text-on-surface">{profile.name}</h4>
                <p className="font-label-sm text-label-sm text-on-surface-variant">DNI/RUC: {profile.document} · Cliente desde {profile.since}</p>
              </div>
            </div>
          </section>

          <section className="bg-white rounded-xl shadow-sm border border-outline-variant p-card-padding flex flex-col items-center text-center relative overflow-hidden">
            <div className="absolute top-0 right-0 p-3 bg-surface-container-low rounded-bl-xl"><Icon name="psychology" size="18px" className="text-primary" filled /></div>
            <h3 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider mb-2">Puntaje Crediticio IA</h3>
            <div className="relative w-48 h-48">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36" aria-label={`Puntaje ${score}`}>
                <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#e5eeff" strokeWidth="3.8" />
                <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke={profile.risk === 'Bajo' ? '#10b981' : profile.risk === 'Medio' ? '#f59e0b' : '#ba1a1a'} strokeWidth="2.8" strokeLinecap="round" strokeDasharray={`${score}, 100`} />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center font-h1-display text-h1-display text-primary">{score}</span>
            </div>
            <div className={`mt-4 px-4 py-2 rounded-lg inline-flex items-center gap-2 ${riskStyle[profile.risk]}`}>
              <Icon name={profile.risk === 'Bajo' ? 'check_circle' : 'warning'} size="18px" />
              <span className="font-label-sm text-label-sm font-semibold">Riesgo {profile.risk}</span>
            </div>
            <div className="mt-6 w-full p-4 bg-surface-container-low rounded-lg border border-primary-fixed">
              <h4 className="font-label-sm text-label-sm text-primary uppercase mb-1">Recomendación de IA</h4>
              <p className="font-body-lg text-body-lg font-semibold text-on-surface">{profile.risk === 'Alto' ? 'Solicitar garantía para crédito de ' : 'Aprobar crédito hasta '}{formatCurrency(profile.recommendedLimit)}</p>
              <p className="font-label-sm text-label-sm text-on-surface-variant mt-2">Tasa sugerida: {profile.suggestedRate}% mensual.</p>
            </div>
          </section>
        </div>

        <div className="lg:col-span-2 flex flex-col gap-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <MetricCard label="Capacidad de pago" value={formatCurrency(profile.paymentCapacity)} trend={profile.capacityTrend} tone={profile.capacityTrend.startsWith('-') ? 'text-error' : 'text-green-600'} />
            <MetricCard label="Nivel de endeudamiento" value={`${profile.debtLevel}%`} trend="Estable" tone="text-yellow-600" />
            <MetricCard label="Historial de puntualidad" value={`${profile.punctuality}%`} trend="+2%" tone="text-green-600" />
          </div>

          <section className="bg-white rounded-xl shadow-sm border border-outline-variant p-card-padding">
            <h3 className="font-h3-title text-h3-title text-on-surface mb-6 border-b border-outline-variant pb-2">Desglose de Factores de Riesgo</h3>
            <div className="space-y-4">
              {profile.factors.map((factor) => (
                <div key={factor.label}>
                  <div className="flex justify-between font-label-sm text-label-sm mb-1">
                    <span className="text-on-surface-variant">{factor.label}</span>
                    <span className="text-on-surface font-semibold">{factor.value}</span>
                  </div>
                  <div className="w-full bg-surface-variant rounded-full h-2">
                    <div className={`h-2 rounded-full ${factorTone[factor.tone]}`} style={{ width: `${factor.percent}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="bg-white rounded-xl shadow-sm border border-outline-variant p-card-padding">
            <h3 className="font-h3-title text-h3-title text-on-surface mb-4">Historial de Evaluaciones</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse min-w-[560px]">
                <thead><tr className="border-b border-outline-variant font-table-header text-table-header text-on-surface-variant uppercase"><th className="py-3 px-2">Fecha</th><th className="py-3 px-2">Score</th><th className="py-3 px-2">Monto Solicitado</th><th className="py-3 px-2">Resultado</th></tr></thead>
                <tbody>
                  {(adjustments[profile.id] ? [{ date: 'Hoy', score, requestedAmount: profile.recommendedLimit, result: profile.risk === 'Alto' ? 'Req. Garantía' : 'Aprobado', tone: profile.risk === 'Alto' ? 'warning' as const : 'success' as const }, ...profile.history] : profile.history).map((entry, index) => (
                    <tr key={`${entry.date}-${index}`} className="border-b border-outline-variant last:border-0 hover:bg-surface-container-lowest">
                      <td className="py-3 px-2">{entry.date}</td><td className="py-3 px-2 font-semibold text-primary">{entry.score}</td><td className="py-3 px-2">{formatCurrency(entry.requestedAmount)}</td>
                      <td className="py-3 px-2"><span className={`px-2 py-1 rounded text-xs font-semibold ${entry.tone === 'success' ? 'bg-green-50 text-green-700' : entry.tone === 'warning' ? 'bg-yellow-50 text-yellow-700' : 'bg-error-container text-on-error-container'}`}>{entry.result}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}

function MetricCard({ label, value, trend, tone }: { label: string; value: string; trend: string; tone: string }) {
  return <div className="bg-white rounded-xl shadow-sm border border-outline-variant p-4"><h4 className="font-label-sm text-label-sm text-on-surface-variant mb-1">{label}</h4><div className="flex items-end justify-between gap-2"><span className="font-h2-headline text-h2-headline text-on-surface">{value}</span><span className={`flex items-center font-label-sm text-label-sm ${tone}`}><Icon name={trend === 'Estable' ? 'horizontal_rule' : 'trending_up'} size="16px" /> {trend}</span></div></div>
}
