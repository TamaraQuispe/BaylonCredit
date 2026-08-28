import { Link } from 'react-router-dom'
import Icon from '@/components/ui/Icon'
import Button from '@/components/ui/Button'
import { fiadoDetail } from '@/data/fiados'
import { formatCurrency } from '@/utils/format'

export default function DetalleFiadoPage() {
  const detail = fiadoDetail

  return (
    <div className="max-w-6xl mx-auto space-y-gutter">
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between border-b border-outline-variant pb-6">
        <div className="space-y-4">
          <Link
            to="/fiados"
            className="inline-flex items-center gap-2 text-on-surface-variant hover:text-primary transition-colors font-label-sm text-label-sm"
          >
            <Icon name="arrow_back" size="18px" />
            Volver al listado de Fiados
          </Link>
          <div className="flex items-center gap-4">
            <h1 className="font-h1-display text-h1-display text-on-surface">Detalle del Fiado</h1>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-secondary-container text-on-secondary-container font-label-sm text-label-sm">
              <span className="w-2 h-2 rounded-full bg-on-secondary-container" />
              Pago en proceso
            </span>
          </div>
          <p className="font-body-md text-body-md text-on-surface-variant">
            Referencia de crédito: {detail.code}
          </p>
        </div>
        <div>
          <Button variant="primary" size="lg" className="bg-primary-container">
            <span className="material-symbols-outlined fill-icon">payments</span>
            Registrar pago
          </Button>
        </div>
      </header>

      {/* KPI Bento Grid */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-stack-gap">
        <div className="bg-surface-container-lowest rounded-xl border-l-4 border-l-secondary-container border-y border-r border-outline-variant shadow-sm p-card-padding flex flex-col justify-between relative overflow-hidden">
          <div className="absolute -right-4 -top-4 text-surface-container-high opacity-50">
            <span className="material-symbols-outlined text-[120px]">account_balance_wallet</span>
          </div>
          <h3 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wide relative z-10">
            Saldo pendiente
          </h3>
          <div className="mt-4 relative z-10 flex items-baseline gap-2">
            <span className="font-h2-headline text-h2-headline text-secondary-container">
              {formatCurrency(detail.pendingAmount)}
            </span>
          </div>
        </div>

        <div className="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-card-padding flex flex-col justify-between">
          <h3 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wide">
            Monto original
          </h3>
          <div className="mt-4">
            <span className="font-h3-title text-h3-title text-on-surface">
              {formatCurrency(detail.originalAmount)}
            </span>
          </div>
        </div>

        <div className="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-card-padding flex flex-col justify-between">
          <h3 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wide">
            Monto pagado
          </h3>
          <div>
            <div className="flex items-center justify-between w-full">
              <span className="font-h3-title text-h3-title text-on-surface">
                {formatCurrency(detail.paidAmount)}
              </span>
              <span className="inline-flex items-center text-primary font-label-sm text-label-sm bg-surface-container-low px-2 py-1 rounded">
                {detail.paidPercent}%
              </span>
            </div>
            <div className="w-full bg-surface-container h-1.5 rounded-full mt-3 overflow-hidden">
              <div className="bg-primary h-full rounded-full" style={{ width: `${detail.paidPercent}%` }} />
            </div>
          </div>
        </div>
      </section>

      {/* Main details */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
        {/* Left column */}
        <div className="lg:col-span-5 space-y-stack-gap">
          {/* Client card */}
          <div className="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-card-padding">
            <h3 className="font-table-header text-table-header text-on-surface-variant mb-4 border-b border-outline-variant pb-2">
              Cliente
            </h3>
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-surface-container-high flex items-center justify-center text-primary font-bold text-xl">
                {detail.client.initials}
              </div>
              <div>
                <h4 className="font-h3-title text-h3-title text-on-surface">{detail.client.name}</h4>
                <p className="font-body-md text-body-md text-on-surface-variant flex items-center gap-1 mt-1">
                  <Icon name="call" size="16px" />
                  {detail.phone}
                </p>
                {detail.hasHistory && (
                  <p className="font-label-sm text-label-sm text-primary mt-1 cursor-pointer hover:underline">
                    Ver historial crediticio
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Dates card */}
          <div className="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-card-padding">
            <h3 className="font-table-header text-table-header text-on-surface-variant mb-4 border-b border-outline-variant pb-2">
              Fechas Clave
            </h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-2 text-on-surface-variant">
                  <Icon name="calendar_today" />
                  <span className="font-body-md text-body-md">Fecha de registro</span>
                </div>
                <span className="font-body-md text-body-md text-on-surface font-medium">
                  {detail.createdAt}
                </span>
              </div>
              <div className="flex justify-between items-center bg-surface-container-low p-2 rounded-lg -mx-2">
                <div className="flex items-center gap-2 text-on-surface-variant">
                  <Icon name="event_busy" />
                  <span className="font-body-md text-body-md">Fecha de vencimiento</span>
                </div>
                <span className="font-body-md text-body-md text-on-surface font-medium">
                  {detail.dueAt}
                </span>
              </div>
              <p className="font-label-sm text-label-sm text-on-surface-variant text-right">
                Faltan {detail.daysLeft} días
              </p>
            </div>
          </div>
        </div>

        {/* Right column: timeline */}
        <div className="lg:col-span-7 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-card-padding">
          <h3 className="font-table-header text-table-header text-on-surface-variant mb-6 border-b border-outline-variant pb-2 flex items-center justify-between">
            <span>Historial de Pagos</span>
            <span className="font-body-md text-body-md text-on-surface-variant normal-case font-normal">
              Estado actual del crédito
            </span>
          </h3>

          <div className="relative">
            <div className="absolute left-[11px] top-2 bottom-2 w-0.5 bg-outline-variant" />
            <div className="space-y-8 pt-2 pb-2">
              {detail.payments.map((payment) => {
                const isPending = payment.type === 'pending'
                return (
                  <div key={payment.title} className="relative pl-6">
                    <div
                      className={`absolute -left-[15px] top-0 bg-surface-container-lowest p-1 rounded-full border flex items-center justify-center ${
                        isPending ? 'border-outline border-dashed' : 'border-outline-variant'
                      }`}
                    >
                      <Icon
                        name={isPending ? 'hourglass_empty' : payment.amount < 0 ? 'payments' : 'check_circle'}
                        size="16px"
                        className={
                          isPending
                            ? 'text-outline'
                            : payment.amount < 0
                              ? 'text-primary'
                              : 'text-on-surface-variant'
                        }
                      />
                    </div>
                    <div
                      className={`flex justify-between items-start ${
                        !isPending && payment.amount < 0
                          ? 'bg-surface-container-low p-3 rounded-lg border border-surface-variant -ml-2 -mt-2'
                          : ''
                      } ${isPending ? 'opacity-50 grayscale' : ''}`}
                    >
                      <div>
                        <h4 className="font-h3-title text-h3-title text-on-surface text-[16px]">
                          {payment.title}
                        </h4>
                        <p className="font-body-md text-body-md text-on-surface-variant">
                          {payment.description}
                        </p>
                      </div>
                      <div className="text-right">
                        <span
                          className={`block font-body-md text-body-md font-medium ${
                            payment.amount < 0
                              ? 'text-primary'
                              : isPending
                                ? 'text-on-surface'
                                : 'text-on-surface'
                          }`}
                        >
                          {payment.amount < 0 ? `- ${formatCurrency(Math.abs(payment.amount))}` : formatCurrency(payment.amount)}
                        </span>
                        <span className="block font-label-sm text-label-sm text-on-surface-variant">
                          {payment.date}
                        </span>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
