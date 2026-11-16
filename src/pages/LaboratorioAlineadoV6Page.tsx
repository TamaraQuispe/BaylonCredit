import { useEffect, useRef, useState } from 'react'
import Button from '@/components/ui/Button'
import Icon from '@/components/ui/Icon'
import { apiRequest } from '@/services/apiClient'
import { formatCurrency } from '@/utils/format'

interface Metrics {
  accuracy: number | null
  balanced_accuracy: number | null
  precision: number | null
  recall: number | null
  f1: number | null
  f2: number | null
  roc_auc: number | null
  brier: number | null
  confusion_matrix: number[][]
}

interface ResearchContext {
  version: 'academic-owner-pending-v6'
  data_source: 'synthetic'
  research_only: true
  business_approval: false
}

interface Summary extends ResearchContext {
  revision_id: string
  display_name: string
  selected_model: 'tree' | 'svm'
  training_scope: 'eligible_known_only' | 'historical_granted_known'
  routing: Record<'development' | 'final', {
    study_attempts: number
    blocked_pending_balance: number
    requires_owner_review: number
    model_eligible: number
    simulator_refused_model_eligible: number
  }> | null
  threshold: number
  development_rows: number
  development_unknown: number
  development_clients: number
  final_labeled_rows: number
  final_unknown: number
  final_clients: number
  selection: { metric: string; oof_f2: number }
  comparison: {
    family: 'svm' | 'tree' | 'most_frequent' | 'constant_1'
    label: string
    raw: Metrics
    policy: {
      metrics: Metrics
      reviews: number
      reviews_known: number
      reviews_unknown: number
      daily_max: number
      capacity_respected: boolean
    }
  }[]
  source: {
    evaluable: number
    late: number
    partial_annotations: number
    partial_denominator: number
    quality: string
  }
  limitations: string[]
  disclaimer: string
}

interface AcademicCase {
  id: 'illustrative-v6' | 'pending-balance-v6' | 'no-history-v6'
  scenario: string
  requested_amount: '20.00'
}

interface Evaluation extends ResearchContext {
  case_id: string
  scenario: string
  estimated_late_probability: number | null
  threshold: number | null
  predicted_late_payment: 0 | 1 | null
  decision: 'blocked_pending_balance' | 'requires_owner_review' | 'model_review_candidate' | 'below_review_threshold'
  reason: string
  model_called: boolean
  requires_manual_review: boolean
  actual_late_payment: null
  features: Record<string, number | null>
  review_policy_applied: false
  disclaimer: string
}

const metricLabels = [
  ['accuracy', 'Exactitud (accuracy)'],
  ['balanced_accuracy', 'Exactitud balanceada'],
  ['precision', 'Precisión'],
  ['recall', 'Sensibilidad (recall)'],
  ['f1', 'F1'],
  ['f2', 'F2'],
  ['roc_auc', 'ROC AUC'],
  ['brier', 'Brier (menor es mejor)'],
] as const

const caseIds = ['illustrative-v6', 'pending-balance-v6', 'no-history-v6']

function metric(value: number | null) {
  return value == null ? 'No disponible' : value.toLocaleString('es-PE', { maximumFractionDigits: 4 })
}

function percent(value: number) {
  return value.toLocaleString('es-PE', { style: 'percent', maximumFractionDigits: 1 })
}

function isFiniteMetric(value: number | null) {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1
}

function isResearchOnly(value: ResearchContext) {
  return value.version === 'academic-owner-pending-v6' && value.data_source === 'synthetic'
    && value.research_only === true && value.business_approval === false
}

function isMetricsShape(value: Metrics, policy = false) {
  return isFiniteMetric(value.accuracy) && (isFiniteMetric(value.balanced_accuracy) || policy && value.balanced_accuracy === null)
    && isFiniteMetric(value.precision) && isFiniteMetric(value.recall)
    && isFiniteMetric(value.f1) && isFiniteMetric(value.f2)
    && (value.roc_auc === null || isFiniteMetric(value.roc_auc))
    && (isFiniteMetric(value.brier) || policy && value.brier === null)
    && Array.isArray(value.confusion_matrix) && value.confusion_matrix.length === 2
    && value.confusion_matrix.every((row) => Array.isArray(row) && row.length === 2
       && row.every((cell) => Number.isInteger(cell) && cell >= 0))
    && (policy || value.roc_auc !== null || value.confusion_matrix.some((row) => row[0] + row[1] === 0))
}

export default function LaboratorioAlineadoV6Page() {
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
          apiRequest<Summary>('/academic-ml/v6/summary', { signal: controller.signal }),
          apiRequest<AcademicCase[]>('/academic-ml/v6/cases', { signal: controller.signal }),
        ])
        if (!active) return
        if (!isResearchOnly(nextSummary) || !['tree', 'svm'].includes(nextSummary.selected_model)
          || !isFiniteMetric(nextSummary.threshold)
          || !nextSummary.revision_id?.trim() || !nextSummary.display_name?.trim()
          || !Number.isFinite(nextSummary.selection.oof_f2)
          || nextSummary.comparison.length !== 4
          || !['svm', 'tree', 'most_frequent', 'constant_1'].every((family) =>
            nextSummary.comparison.some((model) => model.family === family))
          || !nextSummary.comparison.every((model) => isMetricsShape(model.raw) && isMetricsShape(model.policy.metrics, true))) {
          throw new Error('El resumen no corresponde al experimento sintético V6 acordado.')
        }
        if (nextSummary.training_scope === 'eligible_known_only') {
          if (!nextSummary.routing || !(['development', 'final'] as const).every((cohort) => {
            const routing = nextSummary.routing![cohort]
            return routing && Object.values(routing).every((value) => Number.isInteger(value) && value >= 0)
              && routing.study_attempts === routing.blocked_pending_balance + routing.requires_owner_review + routing.model_eligible
              && routing.model_eligible - routing.simulator_refused_model_eligible === (cohort === 'development'
                ? nextSummary.development_rows : nextSummary.final_labeled_rows + nextSummary.final_unknown)
          })) throw new Error('El enrutamiento de elegibilidad V6 es inconsistente.')
        } else if (nextSummary.training_scope !== 'historical_granted_known' || nextSummary.routing !== null) {
          throw new Error('El alcance de entrenamiento V6 no está declarado.')
        }
        // These examples are fixed policy scenarios, never final-test rows or free input.
        if (nextCases.length !== caseIds.length || new Set(nextCases.map((item) => item.id)).size !== caseIds.length
          || nextCases.some((item) => !caseIds.includes(item.id) || item.requested_amount !== '20.00')) {
          throw new Error('Solo se admiten los tres escenarios ficticios V6 de S/ 20.00.')
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
      evaluationRequest.current = null
    }
  }, [retry])

  function selectCase(nextId: string) {
    evaluationRequest.current?.abort()
    evaluationRequest.current = null
    setEvaluating(false)
    setCaseId(nextId)
    setResult(undefined)
    setEvaluationError(undefined)
  }

  async function evaluate() {
    if (!selectedCase || !caseIds.includes(selectedCase.id) || loading || loadError || evaluationRequest.current) return
    const controller = new AbortController()
    evaluationRequest.current = controller
    setEvaluating(true)
    setResult(undefined)
    setEvaluationError(undefined)
    try {
      const evaluation = await apiRequest<Evaluation>(`/academic-ml/v6/evaluate/${encodeURIComponent(selectedCase.id)}`, {
        method: 'POST',
        signal: controller.signal,
      })
      if (controller.signal.aborted) return
      const validPrediction = evaluation.model_called === true
        && selectedCase.id === 'illustrative-v6'
        && evaluation.requires_manual_review === true
        && evaluation.threshold === summary?.threshold
        && typeof evaluation.threshold === 'number'
        && typeof evaluation.estimated_late_probability === 'number'
        && Number.isFinite(evaluation.estimated_late_probability)
        && evaluation.estimated_late_probability >= 0 && evaluation.estimated_late_probability <= 1
        && evaluation.predicted_late_payment === Number(evaluation.estimated_late_probability >= evaluation.threshold)
        && evaluation.decision === (evaluation.predicted_late_payment === 1 ? 'model_review_candidate' : 'below_review_threshold')
      const validGate = evaluation.model_called === false
        && evaluation.estimated_late_probability === null && evaluation.threshold === null
        && evaluation.predicted_late_payment === null
        && ((selectedCase.id === 'pending-balance-v6' && evaluation.decision === 'blocked_pending_balance'
          && evaluation.requires_manual_review === false)
          || (selectedCase.id === 'no-history-v6' && evaluation.decision === 'requires_owner_review'
            && evaluation.requires_manual_review === true))
      if (!isResearchOnly(evaluation) || evaluation.case_id !== selectedCase.id
        || evaluation.actual_late_payment !== null || evaluation.review_policy_applied !== false
        || typeof evaluation.reason !== 'string' || !evaluation.reason.trim()
        || !(validPrediction || validGate)) {
        throw new Error('La respuesta no corresponde al escenario V6 y sus reglas previas al modelo.')
      }
      setResult(evaluation)
    } catch (error: unknown) {
      if (!controller.signal.aborted) {
        setEvaluationError(error instanceof Error ? error.message : 'No se pudo evaluar el caso.')
      }
    } finally {
      if (evaluationRequest.current === controller) {
        evaluationRequest.current = null
        if (!controller.signal.aborted) setEvaluating(false)
      }
    }
  }

  return (
    <div className="max-w-7xl mx-auto w-full min-w-0 pb-12 space-y-6 text-on-surface [overflow-wrap:anywhere]">
      <header>
        <p className="font-label-sm text-label-sm uppercase tracking-wider text-primary font-semibold mb-2">Investigaci&oacute;n sint&eacute;tica &middot; V6 independiente</p>
        <h1 className="font-h1-display text-h1-display">Laboratorio acad&eacute;mico ML V6</h1>
        <p className="text-on-surface-variant mt-2">Experimento con predeclaraci&oacute;n separada sobre mundos sint&eacute;ticos; la selecci&oacute;n se congel&oacute; en desarrollo y no se rehace con el test final.</p>
      </header>

      <section className="rounded-xl border border-secondary-fixed-dim bg-secondary-fixed text-on-secondary-fixed-variant p-5 md:p-6" aria-label="Aviso del laboratorio V6">
        <div className="flex items-start gap-3">
          <Icon name="science" className="shrink-0" />
          <div className="space-y-2">
            <p className="font-semibold">Solo investigaci&oacute;n: datos sint&eacute;ticos; no aprueba ni rechaza cr&eacute;ditos, no asigna cupos.</p>
            <p>Una se&ntilde;al del modelo solo indica un posible candidato a revisi&oacute;n. No es una decisi&oacute;n comercial ni valida clientes reales.</p>
          </div>
        </div>
      </section>

      {loading && <p role="status" className="flex items-center gap-2 text-on-surface-variant"><Icon name="progress_activity" className="animate-spin" /> Cargando resumen y caso ficticio...</p>}
      {!loading && loadError && (
        <section className="rounded-xl border border-outline-variant bg-surface-container-lowest p-5 space-y-3">
          <p role="alert" className="text-error">No se pudo cargar el laboratorio: {loadError}</p>
          <Button variant="outline" onClick={() => setRetry((value) => value + 1)}>Reintentar carga</Button>
        </section>
      )}

      {!loading && !loadError && summary && (
        <>
          <section className="rounded-xl border border-outline-variant bg-surface-container-lowest shadow-card p-5 md:p-6 space-y-4">
            <h2 className="font-h3-title text-h3-title">{summary.display_name}: {summary.selected_model === 'svm' ? 'SVM' : 'Arbol de decision'} seleccionado en desarrollo</h2>
            <p className="text-on-surface-variant">Versi&oacute;n: {summary.version} &middot; Revisi&oacute;n: {summary.revision_id} &middot; Fuente: sint&eacute;tica &middot; Umbral: {percent(summary.threshold)}</p>
            <p>Selecci&oacute;n por F2 OOF de pol&iacute;tica en desarrollo ({summary.selection.metric}); F2 OOF: <strong>{metric(summary.selection.oof_f2)}</strong>. Comparaci&oacute;n FINAL raw: {summary.comparison.filter((model) => model.family === 'svm' || model.family === 'tree').map((model) => `${model.label}: F2 ${metric(model.raw.f2)}`).join('; ')}. FINAL no se usa para volver a seleccionar el modelo, aunque otra familia obtenga mayor F2; las diferencias no prueban superioridad estad&iacute;stica.</p>
            <p className="text-on-surface-variant">La OOF se reutiliz&oacute; para elegir configuraci&oacute;n y umbral, as&iacute; que el ganador OOF es optimista; la calibraci&oacute;n sigmoid interna no equivale a una evaluaci&oacute;n anidada independiente de hiperpar&aacute;metros. El artefacto congelado se reutiliza tal cual, sin reentrenar; el ejemplo ilustrativo no es una validaci&oacute;n independiente.</p>
            <p className="text-on-surface-variant">Desarrollo y evaluaci&oacute;n final son mundos sint&eacute;ticos separados. No se suman como operaciones reales del negocio. Las probabilidades se calibran en datos sint&eacute;ticos, no en la poblaci&oacute;n real.</p>
            <p className="text-on-surface-variant">El modelo seleccionado no representa reglas aprobadas del negocio y no tiene aprobaci&oacute;n del propietario. Cualquier saldo positivo, vencido o vigente, bloquea la evaluaci&oacute;n antes del modelo.</p>
            {summary.training_scope === 'eligible_known_only' && summary.routing && <div className="space-y-2">
              <p>Entrenamiento, calibraci&oacute;n y m&eacute;tricas supervisadas: solo otorgamientos elegibles con desenlace conocido. Las m&eacute;tricas FINAL son condicionales a elegibilidad, no describen todas las solicitudes.</p>
              {(['development', 'final'] as const).map((cohort) => <p key={cohort}>
                {cohort === 'development' ? 'DEV' : 'FINAL'}: {summary.routing![cohort].study_attempts} solicitudes de estudio; {summary.routing![cohort].blocked_pending_balance} bloqueadas por saldo; {summary.routing![cohort].requires_owner_review} revisiones obligatorias del propietario; {summary.routing![cohort].model_eligible} elegibles; {summary.routing![cohort].simulator_refused_model_eligible} rechazos adicionales del simulador entre elegibles.
              </p>)}
              <p>Cero revisiones obligatorias en estudio no elimina la regla: el warmup simula primeros fiados autorizados por el propietario y sus pagos previos aportan historial. Esos primeros fiados no entrenan ni punt&uacute;an el modelo; las revisiones obligatorias tampoco forman parte de la cola de alertas del modelo.</p>
            </div>}
            <dl className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {[
                [summary.training_scope === 'eligible_known_only' ? 'Filas elegibles de desarrollo' : 'Filas de desarrollo', summary.development_rows],
                ['Desenlaces desconocidos en desarrollo', summary.development_unknown],
                ['Clientes sintéticos de desarrollo', summary.development_clients],
                [summary.training_scope === 'eligible_known_only' ? 'Filas finales elegibles etiquetadas' : 'Filas finales etiquetadas', summary.final_labeled_rows],
                ['Desenlaces desconocidos finales', summary.final_unknown],
                ['Clientes sintéticos finales', summary.final_clients],
              ].map(([label, value]) => (
                <div key={label} className="min-w-0 rounded-lg bg-surface-container-low p-3">
                  <dt className="text-sm text-on-surface-variant">{label}</dt>
                  <dd className="font-semibold mt-1">{Number(value).toLocaleString('es-PE')}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section className="min-w-0 rounded-xl border border-outline-variant bg-surface-container-lowest shadow-card p-5 md:p-6 space-y-5">
            <h2 className="font-h3-title text-h3-title">Comparaci&oacute;n de cuatro familias</h2>
            <p className="text-on-surface-variant">Resultados finales precalculados y en cach&eacute;; consultar esta p&aacute;gina no ejecuta inferencia sobre el test final. Escala de 0 a 1; F2 prioriza recall frente a precisi&oacute;n. Las m&eacute;tricas usan desenlaces conocidos: desconocido no significa ausencia de atraso.</p>
            <MetricsTable comparison={summary.comparison} mode="raw" />
            <p className="text-on-surface-variant">Raw aplica el umbral de cada modelo sin l&iacute;mite diario. La pol&iacute;tica simula revisiones con un tope diario predeclarado por modelo; sus m&eacute;tricas no son intercambiables con las raw.</p>
            <MetricsTable comparison={summary.comparison} mode="policy" />
            <div className="overflow-x-auto" role="region" aria-label="Capacidad de revisiones simuladas" tabIndex={0}>
              <table className="w-full min-w-[740px] text-sm text-left border-collapse">
                <caption className="text-left font-semibold mb-3">Revisiones simuladas: conocidas y desconocidas</caption>
                <thead><tr className="border-b border-outline-variant">
                  {['Familia', 'Revisiones', 'Con desenlace conocido', 'Con desenlace desconocido', 'Máximo diario', 'Respeta capacidad'].map((label) => <th key={label} scope="col" className="p-3">{label}</th>)}
                </tr></thead>
                <tbody>{summary.comparison.map((model) => (
                  <tr key={model.family} className="border-b border-outline-variant">
                    <th scope="row" className="p-3 font-medium">{model.label} ({model.family})</th>
                    <td className="p-3">{model.policy.reviews}</td>
                    <td className="p-3">{model.policy.reviews_known}</td>
                    <td className="p-3">{model.policy.reviews_unknown}</td>
                    <td className="p-3">{model.policy.daily_max}</td>
                    <td className="p-3">{model.policy.capacity_respected ? 'Sí' : 'No'}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <p className="text-on-surface-variant">La pol&iacute;tica de revisi&oacute;n es una simulaci&oacute;n agregada por &eacute;poca y fecha civil Lima, no una cola operativa. Un score individual no aplica esa pol&iacute;tica ni reserva una revisi&oacute;n. La capacidad es una estimaci&oacute;n, no una medici&oacute;n de productividad, y respetarla no valida la cola ni su utilidad.</p>
          </section>

          <section className="rounded-xl border border-outline-variant bg-surface-container-lowest shadow-card p-5 md:p-6 space-y-3">
            <h2 className="font-h3-title text-h3-title">Fuente y l&iacute;mites</h2>
            <p><strong>{summary.source.late}/{summary.source.evaluable}</strong> atrasos entre anotaciones evaluables; <strong>{summary.source.partial_annotations}/{summary.source.partial_denominator}</strong> anotaciones con abonos parciales. Son indicadores distintos, con denominadores distintos; no se suman ni se sustituyen entre s&iacute;.</p>
            <p>Desenlaces desconocidos en la fuente: {summary.source.partial_denominator - summary.source.evaluable}. Quedan fuera del denominador de atrasos, no se convierten en casos sin atraso. Un abono parcial no determina por s&iacute; solo el desenlace.</p>
            <p>La revisi&oacute;n del propietario cubre una muestra intencional V5 de 23 elementos (12 fiados, 4 rechazos, 4 semanas y 3 supuestos), no todas las filas V6 ni el modelo. Las referencias agregadas provienen de la declaraci&oacute;n original; ninguna de las dos es un conjunto de entrenamiento ni evidencia auditada del rendimiento de las filas generadas.</p>
            <p>La regla de elegibilidad cambi&oacute;: cualquier saldo pendiente, vencido o vigente, impide un nuevo fiado. Un abono parcial o un acuerdo no bastan; la liquidaci&oacute;n completa debe observarse estrictamente antes de evaluar y solo restablece la elegibilidad, nunca aprueba la operaci&oacute;n.</p>
            <p><strong>Reglas previas a la predicci&oacute;n V6:</strong> con saldo pendiente, la solicitud queda bloqueada sin ejecutar el modelo. Sin fiados completamente pagados, se exige revisi&oacute;n del propietario y no se calcula una probabilidad. Solo con deuda cero e historial pagado se consulta el modelo; la decisi&oacute;n final sigue siendo humana.</p>
            <p className="text-on-surface-variant">Calidad de la fuente: {summary.source.quality}</p>
            <p className="text-on-surface-variant">Las referencias agregadas orientan el generador; no son un conjunto de entrenamiento de clientes reales ni evidencia auditada de rendimiento.</p>
            <ul className="list-disc pl-5 space-y-2 text-on-surface-variant">
              {summary.limitations.map((limitation, index) => <li key={index}>{limitation}</li>)}
            </ul>
            <p className="font-medium">{summary.disclaimer}</p>
          </section>

          <section className="rounded-xl border border-outline-variant bg-surface-container-lowest shadow-card p-5 md:p-6" aria-busy={evaluating}>
            <h2 className="font-h3-title text-h3-title">Consultar escenarios ficticios V6</h2>
            <p className="text-on-surface-variant mt-2">Tres ejemplos: historial pagado sin deuda, saldo pendiente y ausencia de historial pagado. Sin etiquetas de desenlace ni datos de clientes reales. No admite entradas libres. Las variables se muestran despu&eacute;s de evaluar las reglas.</p>
            <div className="flex flex-col sm:flex-row sm:items-end gap-4 mt-5">
              <label className="block min-w-0 flex-1 font-label-sm text-label-sm">
                Caso ficticio
                <select value={caseId} disabled={cases.length === 0} onChange={(event) => selectCase(event.target.value)} className="mt-2 w-full min-w-0 h-12 bg-surface-container-low border border-outline-variant rounded-lg px-3 text-on-surface focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none disabled:opacity-60">
                  <option value="">{cases.length ? 'Selecciona el escenario' : 'No hay casos ficticios disponibles'}</option>
                  {cases.map((item) => <option key={item.id} value={item.id}>{item.id} &middot; {item.scenario.replace(/_/g, ' ')}</option>)}
                </select>
              </label>
              <Button size="lg" disabled={!selectedCase || evaluating} onClick={() => void evaluate()}>
                <Icon name={evaluating ? 'progress_activity' : 'science'} size="20px" className={evaluating ? 'animate-spin' : ''} />
                {evaluating ? 'Evaluando...' : evaluationError ? 'Reintentar evaluación' : 'Evaluar caso ficticio'}
              </Button>
            </div>
            {selectedCase && <p className="mt-3 text-on-surface-variant">Monto ficticio: {formatCurrency(Number(selectedCase.requested_amount))}. Sin fecha de vencimiento ni desenlace observado.</p>}
            {evaluating && <p role="status" className="mt-4 text-on-surface-variant">Comprobando las reglas previas al modelo V6...</p>}
            {evaluationError && <p role="alert" className="mt-4 text-error">{evaluationError} Reintenta manualmente si deseas volver a consultar.</p>}
            {result && result.case_id === caseId && (
              <div className="mt-5 border-t border-outline-variant pt-5 space-y-4" role="status">
                <h3 className="font-semibold">Resultado ficticio: {result.scenario}</h3>
                <p className="text-sm text-on-surface-variant">{result.version} &middot; Datos sint&eacute;ticos &middot; Solo investigaci&oacute;n</p>
                <p className="font-semibold">{result.decision === 'blocked_pending_balance' ? 'Solicitud bloqueada por saldo pendiente' : result.decision === 'requires_owner_review' ? 'Revisión obligatoria del propietario' : 'Reglas previas cumplidas: señal experimental del modelo'}</p>
                <p>{result.reason}</p>
                {!result.model_called && <p className="rounded-lg bg-surface-container-low p-4">Modelo no ejecutado. No se calculan probabilidad, puntaje ni predicci&oacute;n. {result.decision === 'blocked_pending_balance' ? 'Debe liquidarse todo el saldo antes de volver a evaluar; un abono o acuerdo no habilita otro fiado.' : 'El propietario debe revisar el primer fiado; no hay aprobaci&oacute;n autom&aacute;tica ni monto inicial recomendado por V6.'}</p>}
                {result.model_called && result.estimated_late_probability !== null && result.threshold !== null && <dl className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                  <div className="rounded-lg bg-surface-container-low p-4">
                    <dt className="text-on-surface-variant">Probabilidad estimada de atraso</dt>
                    <dd className="font-h2-headline text-h2-headline mt-2">{percent(result.estimated_late_probability)}</dd>
                    <dd className="text-sm text-on-surface-variant mt-1">Calibraci&oacute;n sint&eacute;tica, no poblacional real.</dd>
                  </div>
                  <div className="rounded-lg bg-surface-container-low p-4">
                    <dt className="text-on-surface-variant">Se&ntilde;al individual del modelo</dt>
                    <dd className="font-semibold mt-2">{result.predicted_late_payment === 1 ? 'Candidato a revisión por umbral' : 'Por debajo del umbral de revisión'}</dd>
                    <dd className="text-sm text-on-surface-variant mt-1">Umbral: {percent(result.threshold)}. No aplica pol&iacute;tica diaria.</dd>
                  </div>
                  <div className="rounded-lg bg-surface-container-low p-4">
                    <dt className="text-on-surface-variant">Desenlace del caso</dt>
                    <dd className="font-semibold mt-2">Desenlace desconocido</dd>
                    <dd className="text-sm text-on-surface-variant mt-1">Sin etiqueta: no puede comprobarse acierto ni ausencia de atraso.</dd>
                  </div>
                </dl>}
                <p className="text-on-surface-variant">{result.disclaimer}</p>
                <details className="rounded-lg border border-outline-variant p-4">
                  <summary className="cursor-pointer font-semibold focus:outline-none focus:ring-2 focus:ring-primary/30">Variables sint&eacute;ticas utilizadas</summary>
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

function MetricsTable({ comparison, mode }: { comparison: Summary['comparison']; mode: 'raw' | 'policy' }) {
  const title = mode === 'raw' ? 'Raw: sin política de revisión' : 'Política con tope diario: métricas precalculadas'
  return (
    <div className="overflow-x-auto" role="region" aria-label={title} tabIndex={0}>
      <table className="w-full min-w-[760px] table-fixed text-sm text-left border-collapse">
        <caption className="text-left font-semibold mb-3">{title}</caption>
        <thead><tr className="border-b border-outline-variant">
          <th scope="col" className="py-3 pr-3">M&eacute;trica</th>
          {comparison.map((model) => <th scope="col" key={model.family} className="p-3 align-top">{model.label} ({model.family})</th>)}
        </tr></thead>
        <tbody>
          {metricLabels.map(([key, label]) => (
            <tr key={key} className="border-b border-outline-variant">
              <th scope="row" className="py-3 pr-3 font-medium">{label}</th>
              {comparison.map((model) => <td key={model.family} className="p-3 tabular-nums">{metric((mode === 'raw' ? model.raw : model.policy.metrics)[key])}</td>)}
            </tr>
          ))}
          <tr>
            <th scope="row" className="py-3 pr-3 font-medium">Matriz de confusión<br /><span className="text-on-surface-variant text-xs">Filas: real 0/1; columnas: predicción 0/1</span></th>
            {comparison.map((model) => <td key={model.family} className="p-3 align-top tabular-nums">[{(mode === 'raw' ? model.raw : model.policy.metrics).confusion_matrix.map((row) => `[${row.join(', ')}]`).join(', ')}]</td>)}
          </tr>
        </tbody>
      </table>
    </div>
  )
}
