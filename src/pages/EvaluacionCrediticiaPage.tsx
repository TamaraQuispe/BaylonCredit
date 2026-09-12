import { useEffect, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import Icon from '@/components/ui/Icon'
import { useClientState } from '@/services/clientRepository'
import {
  localScoringService,
  type CreditEvaluation,
  type StoredCreditEvaluation,
} from '@/services/scoringService'
import type { RiskLevel } from '@/types'
import { formatCurrency } from '@/utils/format'

const riskStyle: Record<RiskLevel, string> = {
  'muy-bajo': 'bg-green-50 text-green-700',
  bajo: 'bg-green-50 text-green-700',
  medio: 'bg-yellow-50 text-yellow-700',
  alto: 'bg-error-container text-on-error-container',
  critico: 'bg-error-container text-on-error-container',
}

const riskLabel: Record<RiskLevel, string> = {
  'muy-bajo': 'Muy bajo',
  bajo: 'Bajo',
  medio: 'Medio',
  alto: 'Alto',
  critico: 'Crítico',
}

function formatDate(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat('es-PE', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback
}

export default function EvaluacionCrediticiaPage() {
  const [searchParams] = useSearchParams()
  const { clients, loading: clientsLoading, error: clientsError } = useClientState()
  const [clientId, setClientId] = useState(searchParams.get('cliente') ?? '')
  const [amount, setAmount] = useState('')
  const [result, setResult] = useState<CreditEvaluation>()
  const [resultAmount, setResultAmount] = useState(0)
  const [evaluationLoading, setEvaluationLoading] = useState(false)
  const [evaluationError, setEvaluationError] = useState<string>()
  const [history, setHistory] = useState<StoredCreditEvaluation[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState<string>()
  const selectedClient = clients.find((client) => client.id === clientId) ?? clients[0]
  const selectedClientId = selectedClient?.id
  const numericAmount = Number(amount)

  useEffect(() => {
    if (!selectedClientId) return
    let active = true
    setHistoryLoading(true)
    setHistoryError(undefined)
    localScoringService.listEvaluations(selectedClientId)
      .then((evaluations) => {
        if (active) setHistory(evaluations)
      })
      .catch((error: unknown) => {
        if (active) {
          setHistory([])
          setHistoryError(errorMessage(error, 'No se pudo cargar el historial.'))
        }
      })
      .finally(() => {
        if (active) setHistoryLoading(false)
      })
    return () => {
      active = false
    }
  }, [selectedClientId])

  const selectClient = (nextClientId: string) => {
    setClientId(nextClientId)
    setResult(undefined)
    setEvaluationError(undefined)
  }

  const runEvaluation = async (event: FormEvent) => {
    event.preventDefault()
    if (!selectedClient || !Number.isFinite(numericAmount) || numericAmount <= 0) {
      setEvaluationError('Selecciona un cliente e ingresa un monto mayor a cero.')
      return
    }
    setEvaluationLoading(true)
    setEvaluationError(undefined)
    try {
      const evaluation = await localScoringService.evaluate(selectedClient, numericAmount)
      setResult(evaluation)
      setResultAmount(numericAmount)
      try {
        setHistory(await localScoringService.listEvaluations(selectedClient.id))
        setHistoryError(undefined)
      } catch (error: unknown) {
        setHistoryError(errorMessage(error, 'La evaluación se guardó, pero no se pudo actualizar el historial.'))
      }
    } catch (error: unknown) {
      setEvaluationError(errorMessage(error, 'No se pudo ejecutar la evaluación.'))
    } finally {
      setEvaluationLoading(false)
    }
  }

  const downloadReport = () => {
    if (!result || !selectedClient) return
    const factors = result.factors?.map((factor) =>
      `${factor.label}: ${factor.contribution} de ${factor.weight}. ${factor.description}`,
    ) ?? []
    const report = [
      'Credify - Evaluación Crediticia',
      `Cliente: ${selectedClient.name}`,
      `Negocio: ${selectedClient.business}`,
      `Documento: ${selectedClient.document}`,
      `Monto solicitado: ${formatCurrency(resultAmount)}`,
      `Puntaje: ${result.score}`,
      `Riesgo: ${riskLabel[result.risk]}`,
      `Probabilidad de impago: ${result.defaultProbability}%`,
      `Límite recomendado: ${formatCurrency(result.recommendedLimit)}`,
      `Decisión: ${result.approved ? 'Aprobado' : 'No aprobado'}`,
      `Recomendación: ${result.recommendation}`,
      ...(result.aiExplanation ? [`Explicación IA: ${result.aiExplanation}`] : []),
      ...(result.aiRiskFactors?.map((factor) => `Factor IA: ${factor}`) ?? []),
      ...(result.aiRecommendations?.map((item) => `Acción sugerida: ${item}`) ?? []),
      `Confianza: ${result.confidence ?? 'No disponible'}${result.confidence !== undefined ? '%' : ''}`,
      `Modelo: ${result.modelVersion ?? 'No disponible'}`,
      `Calculado: ${formatDate(result.calculatedAt)}`,
      '',
      'Factores:',
      ...(factors.length ? factors : ['No se recibieron factores.']),
    ].join('\n')
    const url = URL.createObjectURL(new Blob([report], { type: 'text/plain;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `evaluacion-${selectedClient.document}.txt`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="max-w-7xl mx-auto w-full">
      <div className="flex flex-col md:flex-row justify-between md:items-end gap-4 mb-8">
        <div>
          <h2 className="font-h1-display text-h1-display text-on-surface mb-2">Evaluación Crediticia IA</h2>
          <p className="font-body-lg text-body-lg text-on-surface-variant">Análisis de riesgo en tiempo real basado en datos reales del cliente.</p>
        </div>
        <button type="button" onClick={downloadReport} disabled={!result} className="flex items-center justify-center gap-2 px-4 py-2 bg-white border border-outline-variant text-primary rounded font-label-sm text-label-sm shadow-sm hover:bg-surface-container-low disabled:opacity-50 disabled:cursor-not-allowed">
          <Icon name="download" size="18px" /> Descargar Reporte
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="flex flex-col gap-6">
          <form id="credit-evaluation-form" onSubmit={runEvaluation} className="bg-white rounded-xl shadow-sm border border-outline-variant p-card-padding">
            <label className="block font-label-sm text-label-sm text-on-surface-variant mb-2" htmlFor="credit-client">Cliente a evaluar</label>
            <select id="credit-client" value={selectedClientId ?? ''} onChange={(event) => selectClient(event.target.value)} disabled={clientsLoading || clients.length === 0 || evaluationLoading} className="w-full bg-surface-container-low border border-outline-variant rounded-lg px-4 py-3 text-on-surface focus:ring-2 focus:ring-primary outline-none disabled:opacity-60">
              {clients.length === 0 && <option value="">No hay clientes disponibles</option>}
              {clients.map((client) => <option key={client.id} value={client.id}>{client.business} · {client.name}</option>)}
            </select>
            {clientsLoading && <p className="mt-3 text-sm text-on-surface-variant">Cargando clientes...</p>}
            {clientsError && <p className="mt-3 text-sm text-error" role="alert">{clientsError}</p>}
            {selectedClient && (
              <div className="mt-4 pt-4 border-t border-outline-variant flex items-center gap-4">
                <div className="w-12 h-12 shrink-0 bg-surface-variant rounded-full flex items-center justify-center text-primary font-bold text-lg">{selectedClient.initials}</div>
                <div className="min-w-0">
                  <h4 className="font-body-lg text-body-lg font-semibold text-on-surface truncate">{selectedClient.business}</h4>
                  <p className="font-label-sm text-label-sm text-on-surface-variant">{selectedClient.name} · DNI/RUC: {selectedClient.document}</p>
                </div>
              </div>
            )}
            <label className="block font-label-sm text-label-sm text-on-surface-variant mt-5 mb-2" htmlFor="requested-amount">Monto solicitado</label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant">S/</span>
              <input id="requested-amount" type="number" min="0.01" step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} placeholder="0.00" className="w-full bg-surface-container-low border border-outline-variant rounded-lg pl-12 pr-4 py-3 text-on-surface focus:ring-2 focus:ring-primary outline-none" />
            </div>
            {evaluationError && <p className="mt-3 text-sm text-error" role="alert">{evaluationError}</p>}
            <button type="submit" disabled={evaluationLoading || !selectedClient} className="mt-5 w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary text-white rounded-lg font-label-sm text-label-sm shadow-sm hover:bg-primary-container disabled:opacity-60 disabled:cursor-not-allowed">
              <Icon name={evaluationLoading ? 'progress_activity' : 'psychology'} size="18px" className={evaluationLoading ? 'animate-spin' : ''} />
              {evaluationLoading ? 'Evaluando...' : result ? 'Recalcular evaluación' : 'Ejecutar evaluación'}
            </button>
          </form>

          <ScoreCard result={result} />
        </div>

        <div className="lg:col-span-2 flex flex-col gap-6">
          {result ? (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <MetricCard label="Monto solicitado" value={formatCurrency(resultAmount)} detail={result.approved ? 'Aprobado' : 'No aprobado'} tone={result.approved ? 'text-green-600' : 'text-error'} />
                <MetricCard label="Probabilidad de impago" value={`${result.defaultProbability}%`} detail={`Riesgo ${riskLabel[result.risk].toLowerCase()}`} tone={result.risk === 'alto' || result.risk === 'critico' ? 'text-error' : 'text-on-surface-variant'} />
                <MetricCard label="Confianza del modelo" value={result.confidence !== undefined ? `${result.confidence}%` : '—'} detail={`${result.responseTimeMs} ms`} tone="text-on-surface-variant" />
              </div>

              <section className="bg-white rounded-xl shadow-sm border border-outline-variant p-card-padding">
                <h3 className="font-h3-title text-h3-title text-on-surface mb-2">Decisión del motor de riesgo</h3>
                <p className="font-body-lg text-body-lg text-on-surface">{result.recommendation}</p>
                <p className="font-label-sm text-label-sm text-on-surface-variant mt-2">Límite recomendado: <strong className="text-primary">{formatCurrency(result.recommendedLimit)}</strong> · Modelo: {result.modelVersion ?? 'No disponible'} · Calculado {formatDate(result.calculatedAt)}</p>
              </section>

              <AiAnalysis result={result} />

              <section className="bg-white rounded-xl shadow-sm border border-outline-variant p-card-padding">
                <h3 className="font-h3-title text-h3-title text-on-surface mb-6 border-b border-outline-variant pb-2">Desglose de Factores de Riesgo</h3>
                {result.factors?.length ? <FactorList factors={result.factors} /> : <EmptyState icon="insights" message="El modelo no devolvió factores para esta evaluación." compact />}
              </section>
            </>
          ) : (
            <section className="bg-white rounded-xl shadow-sm border border-outline-variant p-card-padding min-h-64 flex items-center justify-center">
              <EmptyState icon="query_stats" message="Selecciona un cliente, ingresa el monto y ejecuta la evaluación para ver el resultado real." />
            </section>
          )}

          <section className="bg-white rounded-xl shadow-sm border border-outline-variant p-card-padding">
            <h3 className="font-h3-title text-h3-title text-on-surface mb-4">Historial de Evaluaciones</h3>
            {historyLoading ? <EmptyState icon="progress_activity" message="Cargando historial..." compact spin /> : historyError ? <EmptyState icon="error" message={historyError} compact error /> : history.length === 0 ? <EmptyState icon="history" message="Este cliente todavía no tiene evaluaciones registradas." compact /> : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse min-w-[640px]">
                  <thead><tr className="border-b border-outline-variant font-table-header text-table-header text-on-surface-variant uppercase"><th className="py-3 px-2">Fecha</th><th className="py-3 px-2">Score</th><th className="py-3 px-2">Monto solicitado</th><th className="py-3 px-2">Límite</th><th className="py-3 px-2">Resultado</th></tr></thead>
                  <tbody>{history.map((entry) => (
                    <tr key={entry.id} className="border-b border-outline-variant last:border-0 hover:bg-surface-container-lowest">
                      <td className="py-3 px-2">{formatDate(entry.calculatedAt)}</td>
                      <td className="py-3 px-2 font-semibold text-primary">{entry.score}</td>
                      <td className="py-3 px-2">{formatCurrency(entry.requestedAmount)}</td>
                      <td className="py-3 px-2">{formatCurrency(entry.recommendedLimit)}</td>
                      <td className="py-3 px-2"><span className={`px-2 py-1 rounded text-xs font-semibold ${entry.approved ? 'bg-green-50 text-green-700' : 'bg-error-container text-on-error-container'}`}>{entry.approved ? 'Aprobado' : 'No aprobado'}</span></td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}

function AiAnalysis({ result }: { result: CreditEvaluation }) {
  if (result.aiStatus === 'disabled' || !result.aiStatus) return null
  if (result.aiStatus === 'pending') {
    return <section className="bg-white rounded-xl shadow-sm border border-outline-variant p-card-padding"><EmptyState icon="auto_awesome" message="Generando explicación con IA..." compact spin /></section>
  }
  if (result.aiStatus === 'failed') {
    return <section className="bg-white rounded-xl shadow-sm border border-outline-variant p-card-padding"><EmptyState icon="info" message="La decisión se calculó correctamente, pero la explicación de IA no estuvo disponible." compact /></section>
  }
  return (
    <section className="bg-white rounded-xl shadow-sm border border-outline-variant p-card-padding">
      <h3 className="font-h3-title text-h3-title text-on-surface mb-2 flex items-center gap-2"><Icon name="auto_awesome" className="text-primary" /> Explicación de IA</h3>
      <p className="font-body-lg text-body-lg text-on-surface">{result.aiExplanation}</p>
      {result.aiRiskFactors?.length ? <div className="mt-4"><h4 className="font-label-sm text-label-sm text-on-surface-variant uppercase mb-2">Factores relevantes</h4><ul className="list-disc pl-5 space-y-1 text-on-surface">{result.aiRiskFactors.map((factor) => <li key={factor}>{factor}</li>)}</ul></div> : null}
      {result.aiRecommendations?.length ? <div className="mt-4"><h4 className="font-label-sm text-label-sm text-on-surface-variant uppercase mb-2">Acciones sugeridas</h4><ul className="list-disc pl-5 space-y-1 text-on-surface">{result.aiRecommendations.map((item) => <li key={item}>{item}</li>)}</ul></div> : null}
      <p className="font-label-sm text-label-sm text-on-surface-variant mt-4">Modelo: {result.aiModel ?? 'OpenRouter'} · Esta explicación no modifica la decisión crediticia.</p>
    </section>
  )
}

function ScoreCard({ result }: { result?: CreditEvaluation }) {
  if (!result) return null
  const stroke = result.risk === 'muy-bajo' || result.risk === 'bajo' ? '#10b981' : result.risk === 'medio' ? '#f59e0b' : '#ba1a1a'
  return (
    <section className="bg-white rounded-xl shadow-sm border border-outline-variant p-card-padding flex flex-col items-center text-center relative overflow-hidden">
      <div className="absolute top-0 right-0 p-3 bg-surface-container-low rounded-bl-xl"><Icon name="psychology" size="18px" className="text-primary" filled /></div>
      <h3 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider mb-2">Puntaje Crediticio IA</h3>
      <div className="relative w-44 h-44">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36" aria-label={`Puntaje ${result.score}`}>
          <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#e5eeff" strokeWidth="3.8" />
          <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke={stroke} strokeWidth="2.8" strokeLinecap="round" strokeDasharray={`${Math.max(0, Math.min(result.score, 100))}, 100`} />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center font-h1-display text-h1-display text-primary">{result.score}</span>
      </div>
      <div className={`mt-4 px-4 py-2 rounded-lg inline-flex items-center gap-2 ${riskStyle[result.risk]}`}><Icon name={result.approved ? 'check_circle' : 'warning'} size="18px" /><span className="font-label-sm text-label-sm font-semibold">Riesgo {riskLabel[result.risk]}</span></div>
    </section>
  )
}

function FactorList({ factors }: { factors: NonNullable<CreditEvaluation['factors']> }) {
  return <div className="space-y-5">{factors.map((factor) => {
    const percent = factor.weight > 0 ? Math.max(0, Math.min(100, Math.round((factor.contribution / factor.weight) * 100))) : 0
    const tone = percent >= 80 ? 'bg-green-500' : percent >= 50 ? 'bg-yellow-400' : 'bg-error'
    return <div key={factor.key}><div className="flex justify-between gap-4 font-label-sm text-label-sm mb-1"><span className="text-on-surface font-medium">{factor.label}</span><span className="text-on-surface-variant whitespace-nowrap">{factor.contribution} de {factor.weight}</span></div><div className="w-full bg-surface-variant rounded-full h-2"><div className={`h-2 rounded-full ${tone}`} style={{ width: `${percent}%` }} /></div><p className="font-label-sm text-label-sm text-on-surface-variant mt-1">{factor.description}</p></div>
  })}</div>
}

function MetricCard({ label, value, detail, tone }: { label: string; value: string; detail: string; tone: string }) {
  return <div className="bg-white rounded-xl shadow-sm border border-outline-variant p-4"><h4 className="font-label-sm text-label-sm text-on-surface-variant mb-1">{label}</h4><div className="flex items-end justify-between gap-2"><span className="font-h2-headline text-h2-headline text-on-surface">{value}</span><span className={`font-label-sm text-label-sm ${tone}`}>{detail}</span></div></div>
}

function EmptyState({ icon, message, compact = false, spin = false, error = false }: { icon: string; message: string; compact?: boolean; spin?: boolean; error?: boolean }) {
  return <div className={`flex flex-col items-center justify-center text-center ${compact ? 'py-8' : 'py-12'}`}><Icon name={icon} size={compact ? '32px' : '48px'} className={`${error ? 'text-error' : 'text-outline'} mb-3 ${spin ? 'animate-spin' : ''}`} /><p className={error ? 'text-error' : 'text-on-surface-variant'}>{message}</p></div>
}
