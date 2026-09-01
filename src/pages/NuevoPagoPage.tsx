import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import Icon from '@/components/ui/Icon'
import { formatCurrency } from '@/utils/format'
import { useClientState } from '@/services/clientRepository'
import {
  creditRepository,
  useCreditState,
  type StoredPayment,
} from '@/services/creditRepository'

function isoDate(date: Date) {
  const offset = date.getTimezoneOffset()
  return new Date(date.getTime() - offset * 60_000).toISOString().slice(0, 10)
}

const riskLabels = {
  'muy-bajo': 'Muy bajo',
  bajo: 'Bajo',
  medio: 'Medio',
  alto: 'Alto',
  critico: 'Crítico',
}

export default function NuevoPagoPage() {
  const [searchParams] = useSearchParams()
  const { clients } = useClientState()
  const { credits } = useCreditState()
  const requestedClient = searchParams.get('cliente') ?? ''
  const requestedCredit = searchParams.get('fiado') ?? ''
  const payableCredits = credits.filter((credit) => credit.clientId && credit.pendingAmount > 0)
  const availableClients = clients.filter((client) =>
    payableCredits.some((credit) => credit.clientId === client.id),
  )
  const initialClientId = availableClients.some((client) => client.id === requestedClient)
    ? requestedClient
    : ''
  const initialClientCredits = payableCredits.filter((credit) => credit.clientId === initialClientId)
  const initialSelected = initialClientCredits.some((credit) => credit.id === requestedCredit)
    ? [requestedCredit]
    : initialClientCredits.map((credit) => credit.id)
  const initialAmount = initialClientCredits
    .filter((credit) => initialSelected.includes(credit.id))
    .reduce((sum, credit) => sum + credit.pendingAmount, 0)

  const [clientId, setClientId] = useState(initialClientId)
  const [selectedCredits, setSelectedCredits] = useState(initialSelected)
  const [amount, setAmount] = useState(initialAmount)
  const [paymentDate, setPaymentDate] = useState(isoDate(new Date()))
  const [method, setMethod] = useState('Transferencia')
  const [reference, setReference] = useState('')
  const [completedPayment, setCompletedPayment] = useState<StoredPayment | null>(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const client = clients.find((item) => item.id === clientId)
  const clientCredits = payableCredits.filter((credit) => credit.clientId === clientId)
  const totalDebt = clientCredits.reduce((sum, credit) => sum + credit.pendingAmount, 0)
  const selectedTotal = clientCredits
    .filter((credit) => selectedCredits.includes(credit.id))
    .reduce((sum, credit) => sum + credit.pendingAmount, 0)
  const newBalance = Math.max(totalDebt - amount, 0)

  const selectClient = (id: string) => {
    const nextCredits = payableCredits.filter((credit) => credit.clientId === id)
    const nextSelection = nextCredits.map((credit) => credit.id)
    setClientId(id)
    setSelectedCredits(nextSelection)
    setAmount(nextCredits.reduce((sum, credit) => sum + credit.pendingAmount, 0))
    setError('')
  }

  useEffect(() => {
    if (clientId || !clients.some((item) => item.id === requestedClient)) return
    const nextCredits = credits.filter(
      (credit) => credit.clientId === requestedClient && credit.pendingAmount > 0,
    )
    if (nextCredits.length === 0) return
    const nextSelection = nextCredits.some((credit) => credit.id === requestedCredit)
      ? [requestedCredit]
      : nextCredits.map((credit) => credit.id)
    setClientId(requestedClient)
    setSelectedCredits(nextSelection)
    setAmount(
      nextCredits
        .filter((credit) => nextSelection.includes(credit.id))
        .reduce((sum, credit) => sum + credit.pendingAmount, 0),
    )
  }, [clientId, clients, credits, requestedClient, requestedCredit])

  const toggleCredit = (creditId: string) => {
    const next = selectedCredits.includes(creditId)
      ? selectedCredits.filter((id) => id !== creditId)
      : [...selectedCredits, creditId]
    setSelectedCredits(next)
    setAmount(
      clientCredits
        .filter((credit) => next.includes(credit.id))
        .reduce((sum, credit) => sum + credit.pendingAmount, 0),
    )
    setError('')
  }

  const selectAll = () => {
    setSelectedCredits(clientCredits.map((credit) => credit.id))
    setAmount(totalDebt)
  }

  const applyPayment = async () => {
    if (!client || amount <= 0 || selectedCredits.length === 0) {
      setError('Selecciona al menos un fiado e ingresa un monto válido.')
      return
    }
    if (amount > selectedTotal) {
      setError('El pago no puede superar el saldo de los fiados seleccionados.')
      return
    }
    if (!paymentDate) {
      setError('Selecciona la fecha del pago.')
      return
    }
    if (paymentDate > isoDate(new Date())) {
      setError('La fecha del pago no puede estar en el futuro.')
      return
    }

    let remaining = amount
    const allocations = clientCredits
      .filter((credit) => selectedCredits.includes(credit.id))
      .map((credit) => {
        const applied = Math.min(credit.pendingAmount, remaining)
        remaining = Number((remaining - applied).toFixed(2))
        return { creditId: credit.id, amount: applied }
      })
      .filter((allocation) => allocation.amount > 0)

    try {
      setSaving(true)
      const payment = await creditRepository.applyPayment({
        client,
        allocations,
        paymentDate,
        method,
        reference: reference.trim() || undefined,
      })
      setCompletedPayment(payment)
      setError('')
    } catch (paymentError) {
      setError(paymentError instanceof Error ? paymentError.message : 'No se pudo registrar el pago.')
    } finally {
      setSaving(false)
    }
  }

  const reset = () => {
    setClientId('')
    setSelectedCredits([])
    setAmount(0)
    setReference('')
    setCompletedPayment(null)
    setError('')
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-8">
        <h2 className="font-h1-display text-h1-display text-on-surface mb-2">Registrar Pago</h2>
        <p className="font-body-lg text-body-lg text-on-surface-variant">
          Aplica un pago total o parcial a los fiados pendientes de un cliente.
        </p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-error-container text-on-error-container border border-error/20 rounded-lg flex items-center gap-2">
          <Icon name="error" size="20px" /> {error}
        </div>
      )}

      {completedPayment && client ? (
        <div className="flex flex-col items-center justify-center p-12 bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm text-center max-w-2xl mx-auto mt-12">
          <div className="w-20 h-20 bg-green-100 text-green-600 rounded-full flex items-center justify-center mb-6">
            <Icon name="task_alt" size="40px" filled />
          </div>
          <h2 className="font-h2-headline text-h2-headline text-on-surface mb-2">
            Pago registrado correctamente
          </h2>
          <p className="font-body-lg text-body-lg text-on-surface-variant mb-2">
            El pago de <strong className="text-on-surface">{formatCurrency(completedPayment.amount)}</strong>{' '}
            fue aplicado a <strong className="text-on-surface">{client.business}</strong>.
          </p>
          <p className="font-body-md text-body-md text-on-surface-variant mb-8">
            Nuevo saldo total: {formatCurrency(completedPayment.remainingBalance)}
          </p>
          <div className="flex flex-col sm:flex-row gap-4">
            <button type="button" onClick={reset} className="px-6 py-2 border border-outline-variant bg-surface-bright hover:bg-surface-container rounded-lg font-medium">
              Registrar otro pago
            </button>
            <Link to="/pagos" className="px-6 py-2 bg-primary-container text-on-primary rounded-lg font-medium flex items-center justify-center gap-2">
              <Icon name="receipt" size="18px" /> Ver comprobante
            </Link>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-7">
            <section className="bg-surface-container-lowest border border-outline-variant rounded-xl p-card-padding shadow-sm">
              <h3 className="font-h3-title text-h3-title text-on-surface mb-4">Información del Cliente</h3>
              <label className="block font-label-sm text-label-sm text-on-surface-variant mb-1" htmlFor="payment-client">
                Cliente con deuda
              </label>
              <div className="relative mb-6">
                <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant">
                  <Icon name="person_search" />
                </span>
                <select
                  id="payment-client"
                  value={clientId}
                  onChange={(event) => selectClient(event.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-surface-bright border border-outline-variant rounded-lg text-on-surface focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none"
                >
                  <option value="">Seleccione un cliente...</option>
                  {availableClients.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.business} · {item.name}
                    </option>
                  ))}
                </select>
              </div>

              {availableClients.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-8 text-center border-2 border-dashed border-outline-variant rounded-lg bg-surface-bright">
                  <Icon name="receipt_long" size="48px" className="text-outline mb-2" />
                  <p className="text-on-surface-variant mb-4">No existen fiados pendientes asociados a clientes.</p>
                  <Link to="/fiados/nuevo" className="text-primary font-medium hover:underline">Registrar el primer fiado</Link>
                </div>
              ) : !client ? (
                <div className="flex flex-col items-center justify-center py-8 text-center border-2 border-dashed border-outline-variant rounded-lg bg-surface-bright">
                  <Icon name="person_off" size="48px" className="text-outline mb-2" />
                  <p className="text-on-surface-variant">Selecciona un cliente para consultar sus fiados pendientes.</p>
                </div>
              ) : (
                <div>
                  <div className="flex items-center gap-4 mb-6 p-4 bg-surface-container-low rounded-lg border border-primary-fixed">
                    <div className="w-12 h-12 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center font-h3-title text-h3-title">
                      {client.initials}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="font-body-lg text-body-lg font-semibold text-on-surface truncate">{client.business}</h4>
                      <p className="font-label-sm text-label-sm text-on-surface-variant">{client.name} · DNI/RUC {client.document}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-label-sm text-label-sm text-on-surface-variant">Riesgo IA</p>
                      <span className="inline-flex px-2 py-0.5 rounded-full bg-surface-container text-primary font-label-sm text-label-sm font-semibold">
                        {riskLabels[client.risk]}
                      </span>
                    </div>
                  </div>

                  <h4 className="font-body-lg text-body-lg font-semibold text-on-surface mb-3 flex items-center gap-2">
                    <Icon name="receipt_long" size="20px" className="text-primary" /> Fiados Pendientes
                  </h4>
                  <div className="border border-outline-variant rounded-lg overflow-hidden bg-surface-bright">
                    <div className="overflow-x-auto">
                      <table className="w-full text-left min-w-[500px]">
                        <thead className="bg-surface-container">
                          <tr>
                            <th className="p-3 w-12" />
                            <th className="p-3 font-table-header text-table-header text-on-surface-variant uppercase">Fecha</th>
                            <th className="p-3 font-table-header text-table-header text-on-surface-variant uppercase">Fiado</th>
                            <th className="p-3 font-table-header text-table-header text-on-surface-variant uppercase text-right">Saldo</th>
                          </tr>
                        </thead>
                        <tbody>
                          {clientCredits.map((credit) => (
                            <tr key={credit.id} className="border-b border-outline-variant last:border-0 hover:bg-surface-container-lowest">
                              <td className="p-3 text-center">
                                <input type="checkbox" checked={selectedCredits.includes(credit.id)} onChange={() => toggleCredit(credit.id)} className="rounded border-outline-variant text-primary focus:ring-primary" />
                              </td>
                              <td className="p-3">{credit.createdAt}</td>
                              <td className="p-3"><Link to={`/fiados/${credit.id}`} className="text-primary hover:underline">{credit.code}</Link></td>
                              <td className="p-3 font-semibold text-right">{formatCurrency(credit.pendingAmount)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="bg-surface-container-low p-3 border-t border-outline-variant flex flex-col sm:flex-row justify-between gap-2">
                      <span className="font-label-sm text-label-sm text-on-surface-variant">{selectedCredits.length} seleccionados de {clientCredits.length}</span>
                      <span className="text-on-surface-variant">Subtotal: <strong className="font-h3-title text-h3-title text-primary">{formatCurrency(selectedTotal)}</strong></span>
                    </div>
                  </div>
                </div>
              )}
            </section>
          </div>

          <div className="lg:col-span-5">
            <section className="bg-surface-container-lowest border border-outline-variant rounded-xl p-card-padding shadow-sm">
              <h3 className="font-h3-title text-h3-title text-on-surface mb-6">Detalles del Pago</h3>
              <label className="block font-label-sm text-label-sm text-on-surface-variant mb-2" htmlFor="payment-amount">Monto a Pagar</label>
              <div className="relative flex items-center mb-2">
                <span className="absolute left-4 font-h2-headline text-h2-headline text-on-surface-variant">S/</span>
                <input id="payment-amount" disabled={!client || selectedCredits.length === 0} value={amount || ''} onChange={(event) => setAmount(Math.min(Number(event.target.value), selectedTotal))} type="number" min="0.01" step="0.01" max={selectedTotal} className="w-full pl-12 pr-4 py-4 text-right bg-surface-bright border-2 border-outline-variant rounded-lg font-h1-display text-h1-display focus:border-primary outline-none disabled:opacity-50" placeholder="0.00" />
              </div>
              <div className="flex gap-2 mb-5">
                <button type="button" disabled={!client} onClick={selectAll} className="px-3 py-1 bg-surface-container rounded font-label-sm text-label-sm text-primary disabled:opacity-50">Deuda total</button>
                <button type="button" disabled={!client || selectedCredits.length === 0} onClick={() => setAmount(selectedTotal)} className="px-3 py-1 border border-outline-variant rounded font-label-sm text-label-sm text-on-surface-variant disabled:opacity-50">Selección</button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
                <label className="font-label-sm text-label-sm text-on-surface-variant">Fecha del pago
                  <input disabled={!client} type="date" max={isoDate(new Date())} value={paymentDate} onChange={(event) => setPaymentDate(event.target.value)} className="w-full mt-1 px-3 py-2 bg-surface-bright border border-outline-variant rounded-lg text-on-surface disabled:opacity-50" />
                </label>
                <label className="font-label-sm text-label-sm text-on-surface-variant">Método de Pago
                  <select disabled={!client} value={method} onChange={(event) => setMethod(event.target.value)} className="w-full mt-1 px-3 py-2 bg-surface-bright border border-outline-variant rounded-lg text-on-surface disabled:opacity-50"><option>Transferencia</option><option>Efectivo</option><option>Yape/Plin</option></select>
                </label>
              </div>
              <label className="block font-label-sm text-label-sm text-on-surface-variant mb-6">Referencia (opcional)
                <input disabled={!client} value={reference} onChange={(event) => setReference(event.target.value)} className="w-full mt-1 px-3 py-2 bg-surface-bright border border-outline-variant rounded-lg disabled:opacity-50" placeholder="# Operación" />
              </label>

              <div className="border-t border-outline-variant pt-5 space-y-3">
                <h4 className="font-table-header text-table-header text-on-surface-variant uppercase">Resumen Dinámico</h4>
                <SummaryRow label="Saldo Anterior (Total)" value={formatCurrency(totalDebt)} />
                <SummaryRow label="Pago a Aplicar" value={`- ${formatCurrency(amount)}`} valueClass="text-green-600 font-semibold" />
                <div className="flex justify-between items-center pt-3 border-t border-dashed border-outline-variant">
                  <span className="font-body-lg text-body-lg font-semibold">Nuevo Saldo</span>
                  <span className="font-h3-title text-h3-title font-bold text-primary">{formatCurrency(newBalance)}</span>
                </div>
              </div>
              <button type="button" disabled={saving || !client || selectedCredits.length === 0 || amount <= 0} onClick={applyPayment} className="w-full mt-8 bg-primary-container text-on-primary font-body-lg font-semibold py-4 rounded-lg flex items-center justify-center gap-2 hover:bg-primary disabled:opacity-50 disabled:cursor-not-allowed">
                <Icon name={saving ? 'progress_activity' : 'check_circle'} size="20px" className={saving ? 'animate-spin' : ''} /> {saving ? 'Registrando...' : 'Confirmar Pago'}
              </button>
            </section>
          </div>
        </div>
      )}
    </div>
  )
}

function SummaryRow({ label, value, valueClass = 'text-on-surface' }: { label: string; value: string; valueClass?: string }) {
  return <div className="flex justify-between items-center"><span className="text-on-surface-variant">{label}</span><span className={valueClass}>{value}</span></div>
}
