import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import Button from '@/components/ui/Button'
import Icon from '@/components/ui/Icon'
import { useClientState } from '@/services/clientRepository'
import {
  localScoringService,
  type CreditEvaluation,
  type ScoreFactor,
  type StoredCreditEvaluation,
} from '@/services/scoringService'
import { useSettingsState } from '@/services/settingsRepository'
import type { RiskLevel } from '@/types'
import { formatCurrency } from '@/utils/format'

const riskLabel: Record<RiskLevel, string> = {
  'muy-bajo': 'Muy bajo',
  bajo: 'Bajo',
  medio: 'Medio',
  alto: 'Alto',
  critico: 'Crítico',
}

const riskTone: Record<RiskLevel, string> = {
  'muy-bajo': 'bg-green-50 text-green-700 border-green-200',
  bajo: 'bg-green-50 text-green-700 border-green-200',
  medio: 'bg-secondary-fixed text-on-secondary-fixed-variant border-secondary-fixed-dim',
  alto: 'bg-error-container text-on-error-container border-error/20',
  critico: 'bg-error-container text-on-error-container border-error/20',
}

type DecisionTone = 'positive' | 'warning' | 'negative'

interface DecisionPresentation {
  tone: DecisionTone
  icon: string
  eyebrow: string
  title: string
  description: string
}

function getDecision(result: CreditEvaluation): DecisionPresentation {
  if (result.approved && ['muy-bajo', 'bajo'].includes(result.risk)) {
    return {
      tone: 'positive',
      icon: 'check_circle',
      eyebrow: 'Resultado favorable',
      title: 'Crédito recomendado',
      description: 'El monto evaluado se encuentra dentro del límite y del nivel de riesgo aceptable.',
    }
  }
  if (result.approved) {
    return {
      tone: 'warning',
      icon: 'verified_user',
      eyebrow: 'Requiere seguimiento',
      title: 'Recomendado con condiciones',
      description: 'Puede aprobarse, manteniendo el monto y el plazo sugeridos por la política vigente.',
    }
  }
  if (['alto', 'critico'].includes(result.risk)) {
    return {
      tone: 'negative',
      icon: 'block',
      eyebrow: 'Riesgo fuera de política',
      title: 'Crédito no recomendado',
      description: 'Los factores registrados superan el nivel de riesgo aceptado por el negocio.',
    }
  }
  return {
    tone: 'warning',
    icon: 'tune',
    eyebrow: 'Ajuste recomendado',
    title: 'Revisa monto y condiciones',
    description: 'El cliente puede volver a evaluarse con un monto menor o condiciones más conservadoras.',
  }
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
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { clients, loading: clientsLoading, error: clientsError } = useClientState()
  const { settings } = useSettingsState()
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
  const hasPendingRecalculation = Boolean(
    result && Number.isFinite(numericAmount) && numericAmount > 0 && numericAmount !== resultAmount,
  )

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
    setAmount('')
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
      `Decisión: ${result.approved ? 'Recomendado' : 'No recomendado'}`,
      `Recomendación: ${result.recommendation}`,
      ...(result.aiExplanation ? [`Explicación IA: ${result.aiExplanation}`] : []),
      ...(result.aiRiskFactors?.map((factor) => `Factor IA: ${factor}`) ?? []),
      ...(result.aiRecommendations?.map((item) => `Acción sugerida: ${item}`) ?? []),
      `Confianza técnica: ${result.confidence ?? 'No disponible'}${result.confidence !== undefined ? '%' : ''}`,
      `Modelo: ${result.modelVersion ?? 'No disponible'}`,
      `Calculado: ${formatDate(result.calculatedAt)}`,
      '',
      'Factores:',
      ...(factors.length ? factors : ['No se recibieron factores.']),
      '',
      'La evaluación apoya la decisión del negocio, pero no garantiza el pago.',
    ].join('\n')
    const url = URL.createObjectURL(new Blob([report], { type: 'text/plain;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `evaluacion-${selectedClient.document}.txt`
    link.click()
    URL.revokeObjectURL(url)
  }

  const createCredit = () => {
    if (!selectedClient || !result) return
    const query = new URLSearchParams({
      cliente: selectedClient.id,
      monto: String(resultAmount),
    })
    navigate(`/creditos/nuevo?${query}`)
  }

  return (
    <div className="max-w-7xl mx-auto w-full pb-36 md:pb-24">
      <div className="flex flex-col md:flex-row justify-between md:items-end gap-4 mb-7">
        <div>
          <p className="font-label-sm text-label-sm uppercase tracking-wider text-primary font-semibold mb-2">
            Decisión basada en historial real
          </p>
          <h1 className="font-h1-display text-h1-display text-on-surface">Evaluación crediticia</h1>
          <p className="font-body-lg text-body-lg text-on-surface-variant mt-1 max-w-2xl">
            Evalúa el monto, entiende los factores y toma una decisión con evidencia registrada.
          </p>
        </div>
        <Button variant="outline" onClick={downloadReport} disabled={!result}>
          <Icon name="download" size="18px" /> Descargar resumen
        </Button>
      </div>

      <form onSubmit={runEvaluation} className="bg-surface-container-lowest rounded-xl shadow-card border border-outline-variant p-5 md:p-6 mb-6">
        <div className="flex items-center justify-between gap-4 mb-5">
          <div>
            <h2 className="font-h3-title text-h3-title text-on-surface">Simulador de monto</h2>
            <p className="text-on-surface-variant mt-1">Cada cálculo se registra y utiliza información real del cliente.</p>
          </div>
          <span className="hidden sm:inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-primary-fixed text-on-primary-fixed font-label-sm text-label-sm">
            <Icon name="shield" size="18px" /> Evaluación auditable
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.4fr)_minmax(220px,0.7fr)_auto] gap-4 items-end">
          <label className="block font-label-sm text-label-sm text-on-surface">
            Cliente a evaluar
            <select
              value={selectedClientId ?? ''}
              onChange={(event) => selectClient(event.target.value)}
              disabled={clientsLoading || clients.length === 0 || evaluationLoading}
              className="mt-2 w-full h-12 bg-surface-container-low border border-outline-variant rounded-lg px-4 text-on-surface focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none disabled:opacity-60"
            >
              {clients.length === 0 && <option value="">No hay clientes disponibles</option>}
              {clients.map((client) => <option key={client.id} value={client.id}>{client.business} · {client.name}</option>)}
            </select>
          </label>

          <label className="block font-label-sm text-label-sm text-on-surface">
            Monto a evaluar
            <div className="relative mt-2">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant font-semibold">S/</span>
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                placeholder="0.00"
                className="w-full h-12 bg-surface-container-low border border-outline-variant rounded-lg pl-12 pr-4 text-on-surface focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
              />
            </div>
          </label>

          <Button type="submit" size="lg" disabled={evaluationLoading || !selectedClient} className="w-full lg:w-auto">
            <Icon name={evaluationLoading ? 'progress_activity' : result ? 'refresh' : 'query_stats'} size="20px" className={evaluationLoading ? 'animate-spin' : ''} />
            {evaluationLoading ? 'Calculando...' : result ? 'Recalcular' : 'Evaluar crédito'}
          </Button>
        </div>

        {selectedClient && (
          <div className="mt-4 pt-4 border-t border-outline-variant flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-10 h-10 shrink-0 bg-primary-fixed rounded-full flex items-center justify-center text-on-primary-fixed font-bold">{selectedClient.initials}</div>
              <div className="min-w-0">
                <p className="font-semibold text-on-surface truncate">{selectedClient.business}</p>
                <p className="font-label-sm text-label-sm text-on-surface-variant truncate">{selectedClient.name} · DNI/RUC {selectedClient.document}</p>
              </div>
            </div>
            {result && (
              <div className="flex flex-wrap gap-2" aria-label="Montos rápidos">
                {[0.5, 1, 1.2].map((ratio) => {
                  const quickAmount = Math.max(1, Math.round(result.recommendedLimit * ratio))
                  return (
                    <button
                      key={ratio}
                      type="button"
                      onClick={() => setAmount(String(quickAmount))}
                      className="px-3 py-1.5 rounded-lg border border-outline-variant bg-surface-container-lowest text-primary hover:bg-primary-fixed font-label-sm text-label-sm transition-colors"
                    >
                      {ratio === 1 ? 'Límite sugerido' : `${Math.round(ratio * 100)}%`} · {formatCurrency(quickAmount)}
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {clientsLoading && <p className="mt-3 text-sm text-on-surface-variant">Cargando clientes...</p>}
        {clientsError && <p className="mt-3 text-sm text-error" role="alert">{clientsError}</p>}
        {evaluationError && <p className="mt-3 text-sm text-error" role="alert">{evaluationError}</p>}
        {hasPendingRecalculation && (
          <p className="mt-3 text-sm text-on-secondary-fixed-variant flex items-center gap-2" role="status">
            <Icon name="info" size="18px" /> El monto cambió. Pulsa “Recalcular” para actualizar la decisión.
          </p>
        )}
      </form>

      {result && selectedClient ? (
        <EvaluationResult
          result={result}
          resultAmount={resultAmount}
          termDays={settings?.defaultCreditTermDays ?? 30}
        />
      ) : (
        <section className="bg-surface-container-lowest rounded-xl shadow-card border border-outline-variant min-h-72 flex items-center justify-center p-6 mb-6">
          <EmptyState
            icon="query_stats"
            title="Aún no hay una evaluación"
            message="Selecciona un cliente, ingresa el monto y ejecuta el análisis para ver una decisión explicada."
          />
        </section>
      )}

      <HistorySection history={history} loading={historyLoading} error={historyError} />

      {result && selectedClient && (
        <div className="fixed md:left-[260px] left-0 right-0 bottom-0 z-30 px-4 md:px-container-padding pb-3 pointer-events-none">
          <div className="max-w-7xl mx-auto bg-surface-container-lowest/95 backdrop-blur border border-outline-variant shadow-[0_-8px_30px_rgba(11,28,48,0.12)] rounded-xl p-3 md:p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 pointer-events-auto">
            <div className="flex items-center gap-3 min-w-0">
              <span className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${result.approved ? 'bg-green-50 text-green-700' : 'bg-error-container text-on-error-container'}`}>
                <Icon name={result.approved ? 'verified' : 'warning'} size="22px" />
              </span>
              <div className="min-w-0">
                <p className="font-semibold text-on-surface truncate">{result.approved ? 'Evaluación favorable' : 'Evaluación fuera de política'}</p>
                <p className="font-label-sm text-label-sm text-on-surface-variant truncate">
                  {formatCurrency(resultAmount)} evaluados · límite {formatCurrency(result.recommendedLimit)} · riesgo {riskLabel[result.risk].toLowerCase()}
                </p>
              </div>
            </div>
            <div className="flex gap-2 w-full md:w-auto">
              <Button variant="outline" onClick={downloadReport} className="flex-1 md:flex-none">
                <Icon name="download" size="18px" /> Resumen
              </Button>
              <Button onClick={createCredit} className="flex-1 md:flex-none">
                <Icon name={result.approved ? 'add_card' : 'rule'} size="18px" />
                {result.approved ? 'Crear crédito' : 'Revisar excepción'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function EvaluationResult({ result, resultAmount, termDays }: { result: CreditEvaluation; resultAmount: number; termDays: number }) {
  const decision = getDecision(result)
  const toneClasses: Record<DecisionTone, { panel: string; icon: string; accent: string }> = {
    positive: {
      panel: 'bg-green-50 border-green-200',
      icon: 'bg-green-600 text-white',
      accent: 'text-green-700',
    },
    warning: {
      panel: 'bg-secondary-fixed border-secondary-fixed-dim',
      icon: 'bg-secondary text-on-secondary',
      accent: 'text-on-secondary-fixed-variant',
    },
    negative: {
      panel: 'bg-error-container border-error/20',
      icon: 'bg-error text-on-error',
      accent: 'text-on-error-container',
    },
  }
  const tone = toneClasses[decision.tone]

  return (
    <div className="space-y-6 mb-6">
      <section className="grid grid-cols-1 lg:grid-cols-12 bg-surface-container-lowest rounded-xl shadow-card border border-outline-variant overflow-hidden">
        <div className={`lg:col-span-5 p-6 md:p-8 border-b lg:border-b-0 lg:border-r ${tone.panel}`}>
          <div className="flex items-start gap-4">
            <span className={`w-14 h-14 rounded-xl flex items-center justify-center shrink-0 shadow-sm ${tone.icon}`}>
              <Icon name={decision.icon} size="30px" />
            </span>
            <div>
              <p className={`font-label-sm text-label-sm uppercase tracking-wider font-bold ${tone.accent}`}>{decision.eyebrow}</p>
              <h2 className="font-h2-headline text-h2-headline text-on-surface mt-1">{decision.title}</h2>
              <p className="text-on-surface-variant mt-2 leading-relaxed">{decision.description}</p>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 mt-7">
            <DecisionStat label="Score" value={`${result.score}/100`} />
            <DecisionStat label="Riesgo" value={riskLabel[result.risk]} />
            <DecisionStat label="Impago est." value={`${result.defaultProbability}%`} />
          </div>

          <div className="mt-5 pt-4 border-t border-on-surface/10 flex items-start gap-2 text-on-surface-variant">
            <Icon name="gavel" size="18px" className="mt-0.5 shrink-0" />
            <p className="font-label-sm text-label-sm">Esta estimación apoya la decisión del negocio, pero no garantiza el pago.</p>
          </div>
        </div>

        <div className="lg:col-span-7 p-6 md:p-8">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <div className="flex items-center gap-2">
              <Icon name="auto_awesome" className="text-primary" size="22px" />
              <h2 className="font-h3-title text-h3-title text-on-surface">Explicación de la evaluación</h2>
            </div>
            <span className={`px-3 py-1 rounded-full border font-label-sm text-label-sm font-semibold ${riskTone[result.risk]}`}>
              Riesgo {riskLabel[result.risk].toLowerCase()}
            </span>
          </div>
          <AiExplanation result={result} />
        </div>
      </section>

      <section>
        <div className="flex items-end justify-between gap-4 mb-3">
          <div>
            <h2 className="font-h3-title text-h3-title text-on-surface">Condiciones recomendadas</h2>
            <p className="text-on-surface-variant mt-1">Los datos esenciales para decidir esta operación.</p>
          </div>
          <span className="hidden sm:block font-label-sm text-label-sm text-on-surface-variant">Política vigente del negocio</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricCard
            icon="payments"
            label="Monto evaluado"
            value={formatCurrency(resultAmount)}
            detail={result.approved ? 'Dentro de política' : 'Requiere ajuste'}
            tone={result.approved ? 'positive' : 'warning'}
          />
          <MetricCard
            icon="account_balance_wallet"
            label="Límite recomendado"
            value={formatCurrency(result.recommendedLimit)}
            detail={resultAmount <= result.recommendedLimit ? 'No superar este monto' : `Exceso de ${formatCurrency(resultAmount - result.recommendedLimit)}`}
            tone="primary"
          />
          <MetricCard
            icon="calendar_month"
            label="Plazo configurado"
            value={`${termDays} días`}
            detail="Según política del negocio"
            tone="neutral"
          />
        </div>
      </section>

      <section className="bg-surface-container-lowest rounded-xl shadow-card border border-outline-variant p-5 md:p-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2 mb-5">
          <div>
            <h2 className="font-h3-title text-h3-title text-on-surface">Evidencia de la decisión</h2>
            <p className="text-on-surface-variant mt-1">Factores calculados exclusivamente con información registrada.</p>
          </div>
          <span className="font-label-sm text-label-sm text-on-surface-variant">Modelo {result.modelVersion ?? 'no disponible'} · {result.responseTimeMs} ms</span>
        </div>
        {result.factors?.length ? <FactorGrid factors={result.factors} /> : <EmptyState icon="insights" title="Sin factores disponibles" message="El motor no devolvió el desglose de esta evaluación." compact />}
      </section>
    </div>
  )
}

function AiExplanation({ result }: { result: CreditEvaluation }) {
  if (result.aiStatus === 'pending') {
    return <EmptyState icon="progress_activity" title="Generando explicación" message="La decisión ya fue calculada. Estamos preparando el resumen en lenguaje sencillo." compact spin />
  }
  if (result.aiStatus === 'failed') {
    return (
      <div>
        <p className="font-body-lg text-body-lg text-on-surface leading-relaxed">{result.recommendation}</p>
        <p className="mt-4 flex items-center gap-2 text-on-surface-variant font-label-sm text-label-sm"><Icon name="info" size="18px" /> La explicación adicional no estuvo disponible; la decisión del motor permanece válida.</p>
      </div>
    )
  }

  const explanation = result.aiExplanation || result.recommendation
  return (
    <div>
      <p className="font-body-lg text-body-lg text-on-surface leading-relaxed">{explanation}</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-5">
        <InsightList
          title="Factores a considerar"
          icon="manage_search"
          items={result.aiRiskFactors?.length ? result.aiRiskFactors : result.factors?.filter((factor) => factor.category === 'riesgo').slice(0, 3).map((factor) => factor.description) ?? []}
        />
        <InsightList
          title="Acciones sugeridas"
          icon="task_alt"
          items={result.aiRecommendations?.length ? result.aiRecommendations : [result.recommendation]}
        />
      </div>
      <p className="font-label-sm text-label-sm text-on-surface-variant mt-5 pt-4 border-t border-outline-variant">
        {result.aiStatus === 'completed' ? `Explicación: ${result.aiModel ?? 'OpenRouter'}. ` : ''}La capa explicativa no modifica el score ni la decisión.
      </p>
    </div>
  )
}

function InsightList({ title, icon, items }: { title: string; icon: string; items: string[] }) {
  return (
    <div className="bg-surface-container-low rounded-lg p-4">
      <h3 className="font-semibold text-on-surface flex items-center gap-2 mb-3"><Icon name={icon} size="19px" className="text-primary" /> {title}</h3>
      {items.length ? (
        <ul className="space-y-2">
          {items.map((item) => <li key={item} className="flex items-start gap-2 text-on-surface-variant"><span className="w-1.5 h-1.5 rounded-full bg-primary mt-2 shrink-0" /> <span>{item}</span></li>)}
        </ul>
      ) : <p className="text-on-surface-variant">No se registraron observaciones adicionales.</p>}
    </div>
  )
}

function FactorGrid({ factors }: { factors: ScoreFactor[] }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3">
      {factors.map((factor) => {
        const percent = factor.weight > 0 ? Math.max(0, Math.min(100, Math.round((factor.contribution / factor.weight) * 100))) : 0
        const positive = factor.category === 'positivo'
        return (
          <article key={factor.key} className="rounded-lg border border-outline-variant p-4 bg-surface-container-lowest">
            <div className="flex items-start justify-between gap-2">
              <span className={`w-9 h-9 rounded-lg flex items-center justify-center ${positive ? 'bg-green-50 text-green-700' : 'bg-secondary-fixed text-on-secondary-fixed-variant'}`}>
                <Icon name={positive ? 'trending_up' : 'priority_high'} size="20px" />
              </span>
              <span className="font-label-sm text-label-sm text-on-surface-variant">{factor.contribution}/{factor.weight}</span>
            </div>
            <h3 className="font-semibold text-on-surface mt-3">{factor.label}</h3>
            <p className="font-label-sm text-label-sm text-on-surface-variant mt-1 min-h-12">{factor.description}</p>
            <div className="h-1.5 bg-surface-container-high rounded-full mt-4 overflow-hidden" aria-label={`${percent}% del aporte disponible`}>
              <div className={`h-full rounded-full ${positive ? 'bg-primary' : 'bg-secondary'}`} style={{ width: `${percent}%` }} />
            </div>
          </article>
        )
      })}
    </div>
  )
}

function DecisionStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-surface-container-lowest/70 rounded-lg p-3 border border-white/60">
      <p className="font-label-sm text-label-sm text-on-surface-variant">{label}</p>
      <p className="font-semibold text-on-surface mt-1 truncate">{value}</p>
    </div>
  )
}

function MetricCard({ icon, label, value, detail, tone }: { icon: string; label: string; value: string; detail: string; tone: 'positive' | 'warning' | 'primary' | 'neutral' }) {
  const styles = {
    positive: 'bg-green-50 text-green-700',
    warning: 'bg-secondary-fixed text-on-secondary-fixed-variant',
    primary: 'bg-primary-fixed text-on-primary-fixed-variant',
    neutral: 'bg-surface-container-high text-on-surface-variant',
  }
  return (
    <article className="bg-surface-container-lowest rounded-xl shadow-card border border-outline-variant p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-label-sm text-label-sm text-on-surface-variant">{label}</p>
          <p className="font-h2-headline text-h2-headline text-on-surface mt-2">{value}</p>
        </div>
        <span className={`w-10 h-10 rounded-lg flex items-center justify-center ${styles[tone]}`}><Icon name={icon} size="22px" /></span>
      </div>
      <p className="font-label-sm text-label-sm text-on-surface-variant mt-3 pt-3 border-t border-outline-variant">{detail}</p>
    </article>
  )
}

function HistorySection({ history, loading, error }: { history: StoredCreditEvaluation[]; loading: boolean; error?: string }) {
  return (
    <details className="bg-surface-container-lowest rounded-xl shadow-card border border-outline-variant group" open={history.length > 0}>
      <summary className="p-5 md:p-6 cursor-pointer list-none flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="w-10 h-10 rounded-lg bg-primary-fixed text-on-primary-fixed-variant flex items-center justify-center"><Icon name="history" size="21px" /></span>
          <div>
            <h2 className="font-h3-title text-h3-title text-on-surface">Historial de evaluaciones</h2>
            <p className="font-label-sm text-label-sm text-on-surface-variant mt-0.5">{history.length} evaluaciones registradas para este cliente</p>
          </div>
        </div>
        <Icon name="expand_more" className="text-on-surface-variant transition-transform group-open:rotate-180" />
      </summary>
      <div className="px-5 md:px-6 pb-5 md:pb-6 border-t border-outline-variant pt-4">
        {loading ? <EmptyState icon="progress_activity" title="Cargando historial" message="Consultando evaluaciones registradas..." compact spin /> : error ? <EmptyState icon="error" title="No se pudo cargar" message={error} compact error /> : history.length === 0 ? <EmptyState icon="history" title="Sin evaluaciones anteriores" message="La primera evaluación aparecerá aquí después de ejecutarse." compact /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[680px]">
              <thead><tr className="border-b border-outline-variant font-table-header text-table-header text-on-surface-variant uppercase"><th className="py-3 px-2">Fecha</th><th className="py-3 px-2">Score</th><th className="py-3 px-2">Monto</th><th className="py-3 px-2">Límite</th><th className="py-3 px-2">Riesgo</th><th className="py-3 px-2">Decisión</th></tr></thead>
              <tbody>{history.map((entry) => (
                <tr key={entry.id} className="border-b border-outline-variant last:border-0 hover:bg-surface-container-low">
                  <td className="py-3 px-2 whitespace-nowrap">{formatDate(entry.calculatedAt)}</td>
                  <td className="py-3 px-2 font-semibold text-primary">{entry.score}</td>
                  <td className="py-3 px-2">{formatCurrency(entry.requestedAmount)}</td>
                  <td className="py-3 px-2">{formatCurrency(entry.recommendedLimit)}</td>
                  <td className="py-3 px-2"><span className={`inline-flex px-2 py-1 rounded border text-xs font-semibold ${riskTone[entry.risk]}`}>{riskLabel[entry.risk]}</span></td>
                  <td className="py-3 px-2"><span className={`inline-flex px-2 py-1 rounded text-xs font-semibold ${entry.approved ? 'bg-green-50 text-green-700' : 'bg-error-container text-on-error-container'}`}>{entry.approved ? 'Recomendado' : 'No recomendado'}</span></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>
    </details>
  )
}

function EmptyState({ icon, title, message, compact = false, spin = false, error = false }: { icon: string; title: string; message: string; compact?: boolean; spin?: boolean; error?: boolean }) {
  return (
    <div className={`flex flex-col items-center justify-center text-center ${compact ? 'py-5' : 'py-12'}`}>
      <Icon name={icon} size={compact ? '32px' : '48px'} className={`${error ? 'text-error' : 'text-outline'} mb-3 ${spin ? 'animate-spin' : ''}`} />
      <p className={`font-semibold ${error ? 'text-error' : 'text-on-surface'}`}>{title}</p>
      <p className={`mt-1 max-w-md ${error ? 'text-on-error-container' : 'text-on-surface-variant'}`}>{message}</p>
    </div>
  )
}
