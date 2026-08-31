import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '@/components/ui/Icon'
import { formatCurrency } from '@/utils/format'
import { useCreditState } from '@/services/creditRepository'

export default function PagosPage() {
  const [search, setSearch] = useState('')
  const { payments } = useCreditState()
  const filteredPayments = useMemo(() => {
    const term = search.trim().toLowerCase()
    return payments.filter(
      (payment) =>
        !term ||
        payment.client.toLowerCase().includes(term) ||
        payment.creditCode.toLowerCase().includes(term),
    )
  }, [payments, search])

  return (
    <div>
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h2 className="font-h2-headline text-h2-headline text-on-surface">Registro de pagos</h2>
          <p className="font-body-md text-body-md text-on-surface-variant mt-1">
            Consulta y gestiona los abonos realizados por los clientes.
          </p>
        </div>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <div className="relative group">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant group-focus-within:text-primary">
              <Icon name="search" size="18px" />
            </span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="pl-10 pr-4 py-2 border border-outline-variant rounded-lg bg-surface-container-lowest text-on-surface focus:outline-none focus:ring-2 focus:ring-primary w-full md:w-64 shadow-sm"
              placeholder="Buscar cliente..."
            />
          </div>
          <Link
            to="/pagos/nuevo"
            className="bg-primary-container text-white px-5 py-2.5 rounded-lg font-label-sm text-label-sm uppercase tracking-wide hover:shadow-md hover:bg-primary transition-all flex items-center justify-center gap-2"
          >
            <Icon name="add" size="18px" /> Registrar pago
          </Link>
        </div>
      </div>

      <div className="bg-surface-container-lowest border border-surface-container-high shadow-sm rounded-xl overflow-hidden">
        <div className="overflow-x-auto w-full">
          <table className="w-full text-left border-collapse min-w-[900px]">
            <thead>
              <tr className="border-b border-surface-container-high bg-surface-bright">
                <th className="font-table-header text-table-header text-on-surface-variant py-4 px-6 uppercase">Cliente</th>
                <th className="font-table-header text-table-header text-on-surface-variant py-4 px-6 uppercase text-right">Monto pagado</th>
                <th className="font-table-header text-table-header text-on-surface-variant py-4 px-6 uppercase">Fiado relacionado</th>
                <th className="font-table-header text-table-header text-on-surface-variant py-4 px-6 uppercase">Fecha de pago</th>
                <th className="font-table-header text-table-header text-on-surface-variant py-4 px-6 uppercase text-right">Saldo restante</th>
                <th className="font-table-header text-table-header text-on-surface-variant py-4 px-6 uppercase">Registrado por</th>
                <th className="py-4 px-6 w-12" />
              </tr>
            </thead>
            <tbody className="font-body-md text-body-md text-on-surface">
              {filteredPayments.map((payment) => (
                <tr key={payment.id} className="border-b border-surface-container-high hover:bg-surface-container-low transition-colors h-[56px] group last:border-0">
                  <td className="py-3 px-6 font-medium">{payment.client}</td>
                  <td className="py-3 px-6 text-right font-semibold text-primary-container">{formatCurrency(payment.amount)}</td>
                  <td className="py-3 px-6">
                    <div className="flex flex-col">
                      <span>{payment.creditCode}</span>
                      <span className="font-label-sm text-label-sm text-on-surface-variant">{payment.creditDate}</span>
                    </div>
                  </td>
                  <td className="py-3 px-6">{payment.paidAt}</td>
                  <td className="py-3 px-6 text-right text-on-surface-variant">{formatCurrency(payment.remainingBalance)}</td>
                  <td className="py-3 px-6">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-full bg-surface-dim flex items-center justify-center text-xs font-medium">{payment.initials}</div>
                      {payment.registeredBy}
                    </div>
                  </td>
                  <td className="py-3 px-6 text-right">
                    {payment.creditIds[0] ? (
                      <Link
                        to={`/fiados/${payment.creditIds[0]}`}
                        className="text-on-surface-variant hover:text-primary opacity-100 sm:opacity-0 group-hover:opacity-100"
                        aria-label="Ver fiado relacionado"
                      >
                        <Icon name="visibility" size="18px" />
                      </Link>
                    ) : (
                      <Icon name="more_vert" size="18px" className="text-on-surface-variant" />
                    )}
                  </td>
                </tr>
              ))}
              {filteredPayments.length === 0 && (
                <tr><td colSpan={7} className="py-14 text-center text-on-surface-variant">No se encontraron pagos.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="border-t border-surface-container-high px-6 py-4 flex items-center justify-between bg-surface-bright/50">
          <span className="font-label-sm text-label-sm text-on-surface-variant">Mostrando {filteredPayments.length} de {payments.length} registros</span>
          <div className="flex items-center gap-2">
            <button type="button" disabled className="p-1 rounded text-on-surface-variant disabled:opacity-50"><Icon name="chevron_left" size="18px" /></button>
            <span className="font-label-sm text-label-sm text-on-surface font-medium px-2">1</span>
            <button type="button" className="p-1 rounded text-on-surface-variant hover:bg-surface-container-high"><Icon name="chevron_right" size="18px" /></button>
          </div>
        </div>
      </div>
    </div>
  )
}
