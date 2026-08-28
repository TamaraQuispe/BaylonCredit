import { useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '@/components/ui/Icon'
import { paymentClients } from '@/data/pagos'
import { formatCurrency } from '@/utils/format'

export default function NuevoPagoPage() {
  const [clientId, setClientId] = useState('')
  const [selectedCredits, setSelectedCredits] = useState<string[]>([])
  const [amount, setAmount] = useState(0)
  const [success, setSuccess] = useState(false)

  const client = paymentClients.find((item) => item.id === clientId)
  const totalDebt = client?.credits.reduce((sum, credit) => sum + credit.amount, 0) ?? 0
  const selectedTotal =
    client?.credits
      .filter((credit) => selectedCredits.includes(credit.id))
      .reduce((sum, credit) => sum + credit.amount, 0) ?? 0
  const newBalance = Math.max(totalDebt - amount, 0)

  const selectClient = (id: string) => {
    const nextClient = paymentClients.find((item) => item.id === id)
    const initialSelection = nextClient?.credits.slice(0, 2).map((credit) => credit.id) ?? []
    const initialAmount =
      nextClient?.credits.slice(0, 2).reduce((sum, credit) => sum + credit.amount, 0) ?? 0
    setClientId(id)
    setSelectedCredits(initialSelection)
    setAmount(initialAmount)
  }

  const toggleCredit = (creditId: string) => {
    if (!client) return
    const next = selectedCredits.includes(creditId)
      ? selectedCredits.filter((id) => id !== creditId)
      : [...selectedCredits, creditId]
    setSelectedCredits(next)
    setAmount(
      client.credits
        .filter((credit) => next.includes(credit.id))
        .reduce((sum, credit) => sum + credit.amount, 0),
    )
  }

  const reset = () => {
    setClientId('')
    setSelectedCredits([])
    setAmount(0)
    setSuccess(false)
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-8">
        <h2 className="font-h1-display text-h1-display text-on-surface mb-2">Registrar Pago</h2>
        <p className="font-body-lg text-body-lg text-on-surface-variant">
          Aplica un pago a la deuda acumulada de un cliente.
        </p>
      </div>

      {success && client ? (
        <div className="flex flex-col items-center justify-center p-12 bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm text-center max-w-2xl mx-auto mt-12">
          <div className="w-20 h-20 bg-green-100 text-green-600 rounded-full flex items-center justify-center mb-6">
            <Icon name="task_alt" size="40px" filled />
          </div>
          <h2 className="font-h2-headline text-h2-headline text-on-surface mb-2">Pago registrado correctamente</h2>
          <p className="font-body-lg text-body-lg text-on-surface-variant mb-8">
            El pago de <strong className="text-on-surface">{formatCurrency(amount)}</strong> fue aplicado a la cuenta de <strong className="text-on-surface">{client.name}</strong>.
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
              <label className="block font-label-sm text-label-sm text-on-surface-variant mb-1" htmlFor="payment-client">Buscar Cliente</label>
              <div className="relative mb-6">
                <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant"><Icon name="person_search" /></span>
                <select
                  id="payment-client"
                  value={clientId}
                  onChange={(event) => selectClient(event.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-surface-bright border border-outline-variant rounded-lg text-on-surface focus:border-primary focus:ring-2 focus:ring-primary/20 appearance-none outline-none"
                >
                  <option value="">Seleccione un cliente...</option>
                  {paymentClients.map((item) => <option key={item.id} value={item.id}>{item.name} - DNI/RUC: {item.document}</option>)}
                </select>
              </div>

              {!client ? (
                <div className="flex flex-col items-center justify-center py-8 text-center border-2 border-dashed border-outline-variant rounded-lg bg-surface-bright">
                  <Icon name="person_off" size="48px" className="text-outline mb-2" />
                  <p className="text-on-surface-variant">Selecciona un cliente para ver su deuda total y fiados pendientes.</p>
                </div>
              ) : (
                <div>
                  <div className="flex items-center gap-4 mb-6 p-4 bg-surface-container-low rounded-lg border border-primary-fixed">
                    <div className="w-12 h-12 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center font-h3-title text-h3-title">{client.initials}</div>
                    <div className="flex-1">
                      <h4 className="font-body-lg text-body-lg font-semibold text-on-surface">{client.name}</h4>
                      <p className="font-label-sm text-label-sm text-on-surface-variant">DNI/RUC: {client.document} · {client.profile}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-label-sm text-label-sm text-on-surface-variant">Riesgo IA</p>
                      <span className="inline-flex px-2 py-0.5 rounded-full bg-surface-container text-primary font-label-sm text-label-sm font-semibold">{client.risk}</span>
                    </div>
                  </div>
                  <h4 className="font-body-lg text-body-lg font-semibold text-on-surface mb-3 flex items-center gap-2"><Icon name="receipt_long" size="20px" className="text-primary" /> Fiados Pendientes</h4>
                  <div className="border border-outline-variant rounded-lg overflow-hidden bg-surface-bright">
                    <div className="overflow-x-auto">
                      <table className="w-full text-left min-w-[480px]">
                        <thead className="bg-surface-container">
                          <tr>
                            <th className="p-3 w-12" />
                            <th className="p-3 font-table-header text-table-header text-on-surface-variant uppercase">Fecha</th>
                            <th className="p-3 font-table-header text-table-header text-on-surface-variant uppercase">Documento</th>
                            <th className="p-3 font-table-header text-table-header text-on-surface-variant uppercase text-right">Monto</th>
                          </tr>
                        </thead>
                        <tbody>
                          {client.credits.map((credit) => (
                            <tr key={credit.id} className="border-b border-outline-variant last:border-0 hover:bg-surface-container-lowest">
                              <td className="p-3 text-center"><input type="checkbox" checked={selectedCredits.includes(credit.id)} onChange={() => toggleCredit(credit.id)} className="rounded border-outline-variant text-primary focus:ring-primary" /></td>
                              <td className="p-3">{credit.date}</td>
                              <td className="p-3">{credit.document}</td>
                              <td className="p-3 font-semibold text-right">{formatCurrency(credit.amount)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="bg-surface-container-low p-3 border-t border-outline-variant flex flex-col sm:flex-row justify-between gap-2">
                      <span className="font-label-sm text-label-sm text-on-surface-variant">{selectedCredits.length} seleccionados de {client.credits.length}</span>
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
                <input
                  id="payment-amount"
                  disabled={!client}
                  value={amount || ''}
                  onChange={(event) => setAmount(Math.min(Number(event.target.value), totalDebt))}
                  type="number"
                  min="0"
                  max={totalDebt}
                  className="w-full pl-12 pr-4 py-4 text-right bg-surface-bright border-2 border-outline-variant rounded-lg font-h1-display text-h1-display focus:border-primary outline-none disabled:opacity-50"
                  placeholder="0.00"
                />
              </div>
              <div className="flex gap-2 mb-5">
                <button type="button" disabled={!client} onClick={() => setAmount(totalDebt)} className="px-3 py-1 bg-surface-container rounded font-label-sm text-label-sm text-primary disabled:opacity-50">Total</button>
                <button type="button" disabled={!client} onClick={() => setAmount(selectedTotal)} className="px-3 py-1 border border-outline-variant rounded font-label-sm text-label-sm text-on-surface-variant disabled:opacity-50">Selección</button>
              </div>
              <div className="grid grid-cols-2 gap-4 mb-6">
                <label className="font-label-sm text-label-sm text-on-surface-variant">Método de Pago
                  <select disabled={!client} className="w-full mt-1 px-3 py-2 bg-surface-bright border border-outline-variant rounded-lg text-on-surface disabled:opacity-50"><option>Transferencia</option><option>Efectivo</option><option>Yape/Plin</option></select>
                </label>
                <label className="font-label-sm text-label-sm text-on-surface-variant">Referencia
                  <input disabled={!client} className="w-full mt-1 px-3 py-2 bg-surface-bright border border-outline-variant rounded-lg disabled:opacity-50" placeholder="# Operación" />
                </label>
              </div>
              <div className="border-t border-outline-variant pt-5 space-y-3">
                <h4 className="font-table-header text-table-header text-on-surface-variant uppercase">Resumen Dinámico</h4>
                <SummaryRow label="Saldo Anterior (Total)" value={formatCurrency(totalDebt)} />
                <SummaryRow label="Pago a Aplicar" value={`- ${formatCurrency(amount)}`} valueClass="text-green-600 font-semibold" />
                <div className="flex justify-between items-center pt-3 border-t border-dashed border-outline-variant">
                  <span className="font-body-lg text-body-lg font-semibold">Nuevo Saldo</span>
                  <span className="font-h3-title text-h3-title font-bold text-primary">{formatCurrency(newBalance)}</span>
                </div>
              </div>
              <button type="button" disabled={!client || amount <= 0} onClick={() => setSuccess(true)} className="w-full mt-8 bg-primary-container text-on-primary font-body-lg font-semibold py-4 rounded-lg flex items-center justify-center gap-2 hover:bg-primary disabled:opacity-50 disabled:cursor-not-allowed">
                <Icon name="check_circle" size="20px" /> Confirmar Pago
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
