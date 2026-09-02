import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import Icon from '@/components/ui/Icon'
import RiskBadge from '@/components/ui/RiskBadge'
import { formatCurrency } from '@/utils/format'
import { useClientState } from '@/services/clientRepository'
import { creditRepository } from '@/services/creditRepository'
import { useSettingsState } from '@/services/settingsRepository'
import {
  localScoringService,
  type CreditEvaluation,
} from '@/services/scoringService'

function isoDate(date: Date) {
  const offset = date.getTimezoneOffset()
  return new Date(date.getTime() - offset * 60_000).toISOString().slice(0, 10)
}

const today = new Date()

export default function NuevoFiadoPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { clients } = useClientState()
  const { settings } = useSettingsState()
  const requestedClient = searchParams.get('cliente') ?? ''
  const [clientId, setClientId] = useState(
    clients.some((client) => client.id === requestedClient) ? requestedClient : '',
  )
  const [amount, setAmount] = useState('')
  const [creditDate, setCreditDate] = useState(isoDate(today))
  const [dueDate, setDueDate] = useState('')
  const [evaluation, setEvaluation] = useState<CreditEvaluation | null>(null)
  const dueDateEdited = useRef(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const client = clients.find((item) => item.id === clientId)
  const numericAmount = Number(amount)

  useEffect(() => {
    if (!clientId && clients.some((item) => item.id === requestedClient)) {
      setClientId(requestedClient)
    }
  }, [clientId, clients, requestedClient])

  useEffect(() => {
    if (dueDateEdited.current) return
    const next = new Date()
    next.setDate(next.getDate() + (settings?.defaultCreditTermDays ?? 15))
    setDueDate(isoDate(next))
  }, [settings])

  const invalidateEvaluation = () => {
    setEvaluation(null)
    setError('')
  }

  const evaluate = async (event: FormEvent) => {
    event.preventDefault()
    if (!client || numericAmount <= 0) {
      setError('Selecciona un cliente e ingresa un monto válido.')
      return
    }
    if (!creditDate || !dueDate || dueDate <= creditDate) {
      setError('La fecha de vencimiento debe ser posterior a la fecha del fiado.')
      return
    }

    setLoading(true)
    setError('')
    try {
      const result = await localScoringService.evaluate(client, numericAmount)
      setEvaluation(result)
    } catch {
      setError('No se pudo calcular el score. Inténtalo nuevamente.')
    } finally {
      setLoading(false)
    }
  }

  const confirmCredit = async () => {
    if (!client || !evaluation) return
    setLoading(true)
    setError('')
    try {
      const credit = await creditRepository.create({
        client,
        amount: numericAmount,
        creditDate,
        dueDate,
        evaluation,
      })
      navigate(`/fiados/${credit.id}`, { replace: true })
    } catch (creditError) {
      setError(creditError instanceof Error ? creditError.message : 'No se pudo registrar el fiado.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
        <div>
          <Link
            to="/fiados"
            className="inline-flex items-center gap-2 text-on-surface-variant hover:text-primary font-label-sm text-label-sm mb-3"
          >
            <Icon name="arrow_back" size="18px" /> Volver al control de fiados
          </Link>
          <h1 className="font-h1-display text-h1-display text-on-surface">Registrar nuevo fiado</h1>
          <p className="font-body-md text-body-md text-on-surface-variant mt-1">
            Evalúa el riesgo del cliente antes de confirmar el crédito.
          </p>
        </div>
        <div className="inline-flex items-center gap-2 px-3 py-2 bg-primary-fixed text-on-primary-fixed rounded-lg font-label-sm text-label-sm">
          <Icon name="psychology_alt" size="18px" /> Evaluación IA obligatoria
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-error-container text-on-error-container border border-error/20 rounded-lg flex items-center gap-2">
          <Icon name="error" size="20px" /> {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <form
          onSubmit={evaluate}
          className="lg:col-span-7 bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm p-6"
        >
          <h2 className="font-h3-title text-h3-title text-on-surface mb-6 flex items-center gap-2">
            <Icon name="receipt_long" className="text-primary" /> Datos del fiado
          </h2>

          <div className="space-y-5">
            <label className="flex flex-col gap-1.5 font-label-sm text-label-sm text-on-surface">
              Cliente
              <select
                required
                disabled={loading}
                value={clientId}
                onChange={(event) => {
                  setClientId(event.target.value)
                  invalidateEvaluation()
                }}
                className="h-11 px-4 rounded-lg bg-surface-bright border border-outline-variant text-on-surface focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary disabled:opacity-60"
              >
                <option value="">Seleccione un cliente...</option>
                {clients.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.business} · {item.name}
                  </option>
                ))}
              </select>
            </label>

            {client && (
              <div className="flex items-center gap-4 p-4 bg-surface-container-low rounded-lg border border-primary-fixed">
                <div className="w-12 h-12 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center font-bold">
                  {client.initials}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-on-surface truncate">{client.business}</p>
                  <p className="font-label-sm text-label-sm text-on-surface-variant">
                    {client.name} · DNI/RUC {client.document}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-label-sm text-label-sm text-on-surface-variant">Deuda actual</p>
                  <p className="font-medium text-on-surface">{formatCurrency(client.debt)}</p>
                </div>
              </div>
            )}

            <label className="flex flex-col gap-1.5 font-label-sm text-label-sm text-on-surface">
              Monto solicitado
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant font-body-lg text-body-lg">
                  S/
                </span>
                <input
                  required
                  disabled={loading}
                  type="number"
                  min="1"
                  step="0.01"
                  value={amount}
                  onChange={(event) => {
                    setAmount(event.target.value)
                    invalidateEvaluation()
                  }}
                  className="w-full h-12 pl-12 pr-4 rounded-lg bg-surface-bright border border-outline-variant text-on-surface font-h3-title text-h3-title focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary disabled:opacity-60"
                  placeholder="0.00"
                />
              </div>
            </label>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <label className="flex flex-col gap-1.5 font-label-sm text-label-sm text-on-surface">
                Fecha del fiado
                <input
                  required
                  disabled={loading}
                  type="date"
                  value={creditDate}
                  onChange={(event) => {
                    setCreditDate(event.target.value)
                    invalidateEvaluation()
                  }}
                  className="h-11 px-4 rounded-lg bg-surface-bright border border-outline-variant focus:outline-none focus:border-primary disabled:opacity-60"
                />
              </label>
              <label className="flex flex-col gap-1.5 font-label-sm text-label-sm text-on-surface">
                Fecha de vencimiento
                <input
                  required
                  disabled={loading}
                  type="date"
                  min={creditDate}
                  value={dueDate}
                  onChange={(event) => {
                    dueDateEdited.current = true
                    setDueDate(event.target.value)
                    invalidateEvaluation()
                  }}
                  className="h-11 px-4 rounded-lg bg-surface-bright border border-outline-variant focus:outline-none focus:border-primary disabled:opacity-60"
                />
              </label>
            </div>

            <button
              type="submit"
              disabled={loading || !client || numericAmount <= 0}
              className="w-full h-12 bg-primary-container text-on-primary rounded-lg font-medium flex items-center justify-center gap-2 hover:bg-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Icon
                name={loading ? 'progress_activity' : 'psychology_alt'}
                className={loading ? 'animate-spin' : ''}
              />
              {loading ? 'Calculando riesgo...' : evaluation ? 'Recalcular evaluación' : 'Calcular score y recomendación'}
            </button>
          </div>
        </form>

        <section className="lg:col-span-5 bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm p-6 flex flex-col">
          <h2 className="font-h3-title text-h3-title text-on-surface mb-6 flex items-center gap-2">
            <Icon name="verified_user" className="text-primary" /> Decisión crediticia
          </h2>

          {!evaluation ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center py-12 border-2 border-dashed border-outline-variant rounded-xl bg-surface-bright">
              <Icon name="query_stats" size="48px" className="text-outline mb-3" />
              <p className="font-medium text-on-surface">Evaluación pendiente</p>
              <p className="font-body-md text-body-md text-on-surface-variant mt-1 max-w-xs">
                Completa los datos y calcula el score antes de confirmar el fiado.
              </p>
            </div>
          ) : (
            <div className="flex-1 flex flex-col">
              <div className="flex items-center justify-between p-4 bg-surface-container-low rounded-xl border border-primary-fixed mb-5">
                <div>
                  <p className="font-label-sm text-label-sm text-on-surface-variant uppercase">Score Baylón</p>
                  <p className="font-h1-display text-h1-display text-primary">{evaluation.score}</p>
                </div>
                <div className="text-right">
                  <p className="font-label-sm text-label-sm text-on-surface-variant mb-1">Nivel de riesgo</p>
                  <RiskBadge level={evaluation.risk} />
                </div>
              </div>

              <div className="space-y-3 mb-5">
                <SummaryRow label="Monto solicitado" value={formatCurrency(numericAmount)} />
                <SummaryRow label="Límite recomendado" value={formatCurrency(evaluation.recommendedLimit)} strong />
                <SummaryRow label="Probabilidad de impago" value={`${evaluation.defaultProbability}%`} />
                <SummaryRow label="Tiempo de respuesta" value={`${evaluation.responseTimeMs} ms`} />
              </div>

              <div
                className={`p-4 rounded-lg border mb-5 ${
                  evaluation.approved
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                    : 'bg-secondary-fixed border-secondary-fixed-dim text-on-secondary-fixed'
                }`}
              >
                <p className="font-medium flex items-center gap-2 mb-1">
                  <Icon name={evaluation.approved ? 'check_circle' : 'warning'} size="20px" />
                  {evaluation.approved ? 'Recomendación favorable' : 'Requiere decisión manual'}
                </p>
                <p className="font-body-md text-body-md">{evaluation.recommendation}</p>
              </div>

              <p className="font-label-sm text-label-sm text-on-surface-variant mb-5">
                La recomendación apoya la decisión. El responsable del negocio conserva la decisión final.
              </p>

              <button
                type="button"
                onClick={confirmCredit}
                disabled={loading}
                className="mt-auto w-full h-12 bg-primary text-on-primary rounded-lg font-medium flex items-center justify-center gap-2 hover:bg-primary-container"
              >
                <Icon name="check_circle" /> Confirmar y registrar fiado
              </button>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

function SummaryRow({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-outline-variant/50">
      <span className="text-on-surface-variant">{label}</span>
      <span className={strong ? 'font-semibold text-primary' : 'font-medium text-on-surface'}>{value}</span>
    </div>
  )
}
