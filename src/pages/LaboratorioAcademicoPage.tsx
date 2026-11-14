import { useEffect, useRef, useState } from 'react'
import Button from '@/components/ui/Button'
import Icon from '@/components/ui/Icon'
import { apiRequest } from '@/services/apiClient'
import { formatCurrency, formatDate } from '@/utils/format'

interface Metrics {
  accuracy: number | null
  balanced_accuracy: number | null
  precision: number | null
  recall: number | null
  f1: number | null
  roc_auc: number | null
  brier_score: number | null
  confusion_matrix: number[][]
}

interface Summary {
  version: string
  data_source: 'synthetic'
  selected_model: string
  threshold: number
  training_rows: number
  validation_rows: number
  final_labeled_rows: number
  final_clients: number
  comparison: {
    second_model: Metrics
    first_model_same_fresh_cohort: Metrics
    majority_baseline: Metrics
  }
}

interface AcademicCase {
  id: string
  scenario: string
  requested_amount: string
  due_date: string
}

interface Evaluation {
  case_id: string
  scenario: string
  data_source: 'synthetic'
  version: string
  estimated_late_probability: number
  threshold: number
  predicted_late_payment: 0 | 1
  actual_late_payment: 0 | 1
  features: Record<string, number>
  disclaimer: string
}

const metricLabels = [
  ['accuracy', 'Exactitud (accuracy)'],
  ['balanced_accuracy', 'Exactitud balanceada'],
  ['precision', 'Precisión'],
  ['recall', 'Sensibilidad (recall)'],
  ['f1', 'F1'],
  ['roc_auc', 'ROC AUC'],
  ['brier_score', 'Brier score (menor es mejor)'],
] as const

function metric(value: number | null) {
  return value == null ? 'No disponible' : value.toLocaleString('es-PE', { maximumFractionDigits: 4 })
}

function percent(value: number) {
  return value.toLocaleString('es-PE', { style: 'percent', maximumFractionDigits: 1 })
}

export default function LaboratorioAcademicoPage() {
  const [summary, setSummary] = useState<Summary>()
  const [cases, setCases] = useState<AcademicCase[]>([])
  const [caseId, setCaseId] = useState('')
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string>()
  const [retry, setRetry] = useState(0)
  const [result, setResult] = useState<Evaluation>()
  const [evaluating, setEvaluating] = useState(false)
  const [evaluationError, setEvaluationError] = useState<string>()
  const evaluationRequest = useRef<AbortController | null>(null)
  const selectedCase = cases.find((item) => item.id === caseId)

  useEffect(() => {
    let active = true
    const controller = new AbortController()
    async function load() {
      setLoading(true)
      setLoadError(undefined)
      try {
        const [nextSummary, nextCases] = await Promise.all([
          apiRequest<Summary>('/academic-ml/summary', { signal: controller.signal }),
          apiRequest<AcademicCase[]>('/academic-ml/cases', { signal: controller.signal }),
        ])
        if (!active) return
        if (nextSummary.data_source !== 'synthetic') {
          throw new Error('El laboratorio solo admite datos sintéticos.')
        }
        setSummary(nextSummary)
        setCases(nextCases)
        setCaseId('')
        setResult(undefined)
      } catch (error: unknown) {
        if (active) setLoadError(error instanceof Error ? error.message : 'No se pudo cargar el laboratorio.')
      } finally {
        if (active) setLoading(false)
      }
    }
    void load()
    return () => {
      active = false
      controller.abort()
      evaluationRequest.current?.abort()
    }
  }, [retry])

  async function evaluate() {
    if (!selectedCase || loading || evaluationRequest.current) return
    const controller = new AbortController()
    evaluationRequest.current = controller
    setEvaluating(true)
    setResult(undefined)
    setEvaluationError(undefined)
    try {
      const evaluation = await apiRequest<Evaluation>(`/academic-ml/evaluate/${encodeURIComponent(selectedCase.id)}`, {
        method: 'POST',
        signal: controller.signal,
      })
      if (controller.signal.aborted) return
      if (evaluation.case_id !== selectedCase.id || evaluation.data_source !== 'synthetic') {
        throw new Error('La respuesta no corresponde al caso sintético seleccionado.')
      }
      setResult(evaluation)
    } catch (error: unknown) {
      if (!controller.signal.aborted) {
        setEvaluationError(error instanceof Error ? error.message : 'No se pudo evaluar el caso. Inténtalo de nuevo.')
      }
    } finally {
      if (!controller.signal.aborted) setEvaluating(false)
      if (evaluationRequest.current === controller) evaluationRequest.current = null
    }
  }

  const models = summary ? [
    { label: 'Modelo v2', metrics: summary.comparison.second_model },
    { label: 'Modelo v1 en la misma cohorte nueva', metrics: summary.comparison.first_model_same_fresh_cohort },
    { label: 'Referencia de clase mayoritaria', metrics: summary.comparison.majority_baseline },
  ] : []

  return (
    <div className="max-w-7xl mx-auto w-full min-w-0 pb-12 space-y-6 text-on-surface [overflow-wrap:anywhere]">
      <div>
        <p className="font-label-sm text-label-sm uppercase tracking-wider text-primary font-semibold mb-2">Experimento sintético · Solo consulta</p>
        <h1 className="font-h1-display text-h1-display">Laboratorio académico ML</h1>
        <p className="text-on-surface-variant mt-2">Explora el segundo experimento y sus límites, sin modificar clientes ni créditos.</p>
      </div>

      <section className="rounded-xl border border-secondary-fixed-dim bg-secondary-fixed text-on-secondary-fixed-variant p-5 md:p-6" aria-label="Aviso del laboratorio">
        <div className="flex items-start gap-3">
          <Icon name="science" className="shrink-0" />
          <div>
            <p className="font-semibold">Laboratorio académico: datos sintéticos; no aprueba créditos ni valida clientes reales</p>
            <p className="mt-2">El modelo tiene alcance limitado. Sus resultados no son recomendaciones de crédito ni evidencia de rendimiento en población real.</p>
          </div>
        </div>
      </section>

      {loading && <p role="status" className="flex items-center gap-2 text-on-surface-variant"><Icon name="progress_activity" className="animate-spin" /> Cargando resumen y casos sintéticos...</p>}
      {!loading && loadError && (
        <section className="rounded-xl border border-outline-variant bg-surface-container-lowest p-5 space-y-3">
          <p role="alert" className="text-error">No se pudo cargar el laboratorio: {loadError}</p>
          <Button variant="outline" onClick={() => setRetry((value) => value + 1)}><Icon name="refresh" size="18px" /> Reintentar carga</Button>
        </section>
      )}

      {!loading && !loadError && summary && (
        <>
          <section className="rounded-xl border border-outline-variant bg-surface-container-lowest shadow-card p-5 md:p-6">
            <h2 className="font-h3-title text-h3-title">Modelo v2: {summary.selected_model}</h2>
            <p className="text-on-surface-variant mt-2">Versión {summary.version} · Fuente: datos sintéticos · Umbral de atraso: {percent(summary.threshold)}</p>
            <dl className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-5">
              {[
                ['Filas de entrenamiento', summary.training_rows],
                ['Filas de validación', summary.validation_rows],
                ['Filas finales etiquetadas', summary.final_labeled_rows],
                ['Clientes sintéticos finales', summary.final_clients],
              ].map(([label, value]) => (
                <div key={label} className="min-w-0 rounded-lg bg-surface-container-low p-3">
                  <dt className="text-sm text-on-surface-variant">{label}</dt>
                  <dd className="font-semibold mt-1">{Number(value).toLocaleString('es-PE')}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section className="min-w-0 rounded-xl border border-outline-variant bg-surface-container-lowest shadow-card p-5 md:p-6">
            <h2 className="font-h3-title text-h3-title">Comparación en la cohorte sintética final</h2>
            <p className="mt-2 text-on-surface-variant">Las métricas se muestran en escala de 0 a 1. Un mejor resultado aislado no implica un mejor modelo para todos los objetivos.</p>
            <div className="overflow-x-auto mt-5" role="region" aria-label="Tabla comparativa de modelos" tabIndex={0}>
              <table className="w-full min-w-[580px] table-fixed text-sm text-left border-collapse">
                <caption className="sr-only">Métricas de los tres modelos en la misma cohorte sintética</caption>
                <thead><tr className="border-b border-outline-variant">
                  <th scope="col" className="py-3 pr-3">Métrica</th>
                  {models.map((model) => <th scope="col" key={model.label} className="p-3 align-top">{model.label}</th>)}
                </tr></thead>
                <tbody>
                  {metricLabels.map(([key, label]) => (
                    <tr key={key} className="border-b border-outline-variant">
                      <th scope="row" className="py-3 pr-3 font-medium">{label}</th>
                      {models.map((model) => <td key={model.label} className="p-3 tabular-nums">{metric(model.metrics[key])}</td>)}
                    </tr>
                  ))}
                  <tr>
                    <th scope="row" className="py-3 pr-3 font-medium">Matriz de confusión</th>
                    {models.map((model) => <td key={model.label} className="p-3 align-top tabular-nums">[{model.metrics.confusion_matrix.map((row) => `[${row.join(', ')}]`).join(', ')}]</td>)}
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="mt-4 rounded-lg bg-surface-container-low p-4 text-on-surface-variant space-y-2">
              <p className="font-semibold text-on-surface">Intercambios y limitaciones de esta cohorte</p>
              {(['recall', 'f1'] as const).map((key) => {
                const current = summary.comparison.second_model[key]
                const first = summary.comparison.first_model_same_fresh_cohort[key]
                return <p key={key}>{key === 'recall' ? 'Recall' : 'F1'} de v2: {metric(current)}, frente a {metric(first)} de v1. {current != null && first != null && current < first ? 'Es menor en v2; esta métrica no mejoró.' : 'Debe interpretarse junto con el resto de métricas, sin asumir una mejora general.'}</p>
              })}
              <p>Exactitud de v2: {metric(summary.comparison.second_model.accuracy)}, frente a {metric(summary.comparison.majority_baseline.accuracy)} de la referencia mayoritaria. {summary.comparison.second_model.accuracy != null && summary.comparison.majority_baseline.accuracy != null && summary.comparison.second_model.accuracy < summary.comparison.majority_baseline.accuracy ? 'La exactitud de v2 está por debajo de la referencia mayoritaria.' : 'Esta comparación no demuestra utilidad para decisiones reales.'}</p>
              <p>Un recall menor implica más atrasos no detectados; F1 resume precisión y recall. No se ha demostrado calibración de las probabilidades ni validez en clientes reales.</p>
            </div>
          </section>

          <section className="rounded-xl border border-outline-variant bg-surface-container-lowest shadow-card p-5 md:p-6" aria-busy={evaluating}>
            <h2 className="font-h3-title text-h3-title">Consultar un caso sintético</h2>
            <p className="text-on-surface-variant mt-2">Selecciona un escenario predefinido. La estimación y el desenlace simulado se revelan solo al evaluar.</p>
            <div className="flex flex-col sm:flex-row sm:items-end gap-4 mt-5">
              <label className="block min-w-0 flex-1 font-label-sm text-label-sm">
                Caso sintético
                <select
                  value={caseId}
                  disabled={evaluating || cases.length === 0}
                  onChange={(event) => {
                    setCaseId(event.target.value)
                    setResult(undefined)
                    setEvaluationError(undefined)
                  }}
                  className="mt-2 w-full min-w-0 h-12 bg-surface-container-low border border-outline-variant rounded-lg px-3 text-on-surface focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none disabled:opacity-60"
                >
                  <option value="">{cases.length ? 'Selecciona un escenario' : 'No hay casos sintéticos disponibles'}</option>
                  {cases.map((item) => <option key={item.id} value={item.id}>{item.id} · {item.scenario.replace(/_/g, ' ')}</option>)}
                </select>
              </label>
              <Button size="lg" disabled={!selectedCase || evaluating} onClick={() => void evaluate()}>
                <Icon name={evaluating ? 'progress_activity' : 'science'} size="20px" className={evaluating ? 'animate-spin' : ''} />
                {evaluating ? 'Evaluando...' : 'Evaluar caso sintético'}
              </Button>
            </div>
            {selectedCase && <p className="mt-3 text-on-surface-variant">Monto simulado: {formatCurrency(Number(selectedCase.requested_amount))} · Vencimiento: {formatDate(selectedCase.due_date)}</p>}
            {evaluating && <p role="status" className="mt-4 text-on-surface-variant">Consultando el modelo académico...</p>}
            {evaluationError && <p role="alert" className="mt-4 text-error">{evaluationError} Puedes reintentar con el botón de evaluación.</p>}
            {result && result.case_id === caseId && (
              <div className="mt-5 border-t border-outline-variant pt-5 space-y-4" role="status">
                <h3 className="font-semibold">Resultado sintético: {result.scenario}</h3>
                <p className="text-sm text-on-surface-variant">Versión {result.version} · Fuente: datos sintéticos</p>
                <dl className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="rounded-lg bg-surface-container-low p-4">
                    <dt className="text-on-surface-variant">Riesgo estimado de atraso (no calibrado)</dt>
                    <dd className="font-h2-headline text-h2-headline mt-2">{percent(result.estimated_late_probability)}</dd>
                  </div>
                  <div className="rounded-lg bg-surface-container-low p-4">
                    <dt className="text-on-surface-variant">Predicción del modelo</dt>
                    <dd className="font-semibold mt-2">{result.predicted_late_payment === 1 ? 'Atraso estimado' : 'Sin atraso estimado'}</dd>
                    <dd className="text-sm text-on-surface-variant mt-1">Umbral: {percent(result.threshold)}</dd>
                  </div>
                  <div className="rounded-lg bg-surface-container-low p-4">
                    <dt className="text-on-surface-variant">Desenlace del caso simulado</dt>
                    <dd className="font-semibold mt-2">{result.actual_late_payment === 1 ? 'Hubo atraso simulado' : 'No hubo atraso simulado'}</dd>
                    <dd className="text-sm text-on-surface-variant mt-1">Etiqueta sintética, no un pago de cliente real.</dd>
                  </div>
                </dl>
                <p className="text-on-surface-variant">{result.disclaimer}</p>
                <details className="rounded-lg border border-outline-variant p-4">
                  <summary className="cursor-pointer font-semibold">Variables sintéticas utilizadas</summary>
                  <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4">
                    {Object.entries(result.features).map(([name, value]) => (
                      <div key={name} className="min-w-0"><dt className="text-sm text-on-surface-variant">{name}</dt><dd className="font-medium">{metric(value)}</dd></div>
                    ))}
                  </dl>
                </details>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
