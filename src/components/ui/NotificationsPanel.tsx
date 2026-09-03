import Icon from './Icon'
import CurrencyDisplay from './CurrencyDisplay'
import type { StoredCredit } from '@/services/creditRepository'

interface NotificationsPanelProps {
  credits: StoredCredit[]
  open: boolean
  onClose: () => void
  onViewFiado: (id: string) => void
}

interface NotificationItem {
  id: string
  creditId: string
  title: string
  description: string
  amount?: number
  tone: 'danger' | 'warning' | 'info'
  risk?: string
}

const DAY_IN_MS = 86_400_000

function parseDate(value: string): Date | null {
  const iso = value.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (iso) return new Date(Number(iso[1]), Number(iso[2]) - 1, Number(iso[3]))
  const local = value.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/)
  if (local) return new Date(Number(local[3]), Number(local[2]) - 1, Number(local[1]))
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

function buildNotifications(credits: StoredCredit[]): NotificationItem[] {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const items: NotificationItem[] = []

  credits
    .filter((credit) => credit.pendingAmount > 0)
    .forEach((credit) => {
      const dueDate = parseDate(credit.dueAt)
      const overdueDays = dueDate
        ? Math.max(0, Math.floor((today.getTime() - dueDate.getTime()) / DAY_IN_MS))
        : 0
      const highRisk = credit.risk === 'alto' || credit.risk === 'critico'

      if (credit.status === 'vencido' || overdueDays > 0) {
        items.push({
          id: `vencido-${credit.id}`,
          creditId: credit.id,
          title: `Fiado vencido${overdueDays > 0 ? ` · ${overdueDays} d` : ''}`,
          description: `${credit.client.business} · ${credit.code} · ${overdueDays > 0 ? `${overdueDays} días de retraso` : 'mora'}`,
          amount: credit.pendingAmount,
          tone: 'danger',
          risk: credit.risk,
        })
      } else if (credit.status === 'proximo-a-vencer') {
        items.push({
          id: `proximo-${credit.id}`,
          creditId: credit.id,
          title: 'Vence pronto',
          description: `${credit.client.business} · ${credit.code} vence en breve`,
          amount: credit.pendingAmount,
          tone: 'warning',
          risk: credit.risk,
        })
      } else if (highRisk) {
        items.push({
          id: `riesgo-${credit.id}`,
          creditId: credit.id,
          title: 'Riesgo elevado',
          description: `${credit.client.business} · ${credit.code} presenta riesgo ${credit.risk}`,
          amount: credit.pendingAmount,
          tone: 'warning',
          risk: credit.risk,
        })
      } else {
        items.push({
          id: `pendiente-${credit.id}`,
          creditId: credit.id,
          title: 'Fiado en curso',
          description: `${credit.client.business} · ${credit.code}`,
          amount: credit.pendingAmount,
          tone: 'info',
          risk: credit.risk,
        })
      }
    })

  return items.sort((a, b) => (a.tone === 'danger' ? -1 : 0) - (b.tone === 'danger' ? -1 : 0) || (b.amount ?? 0) - (a.amount ?? 0))
}

export default function NotificationsPanel({ credits, open, onClose, onViewFiado }: NotificationsPanelProps) {
  if (!open) return null
  const items = buildNotifications(credits)
  const dangerCount = items.filter((item) => item.tone === 'danger').length

  return (
    <div className="fixed inset-0 z-50 bg-on-surface/40 backdrop-blur-sm flex items-center justify-center">
      <div className="bg-surface-container-lowest rounded-xl p-6 w-full max-w-lg mx-4 shadow-lg border border-outline-variant">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-3">
            <Icon name="notifications" size="26px" />
            <h3 className="font-h3-title text-h3-title text-on-surface">Notificaciones</h3>
            {dangerCount > 0 && (
              <span className="text-label-sm rounded-full bg-error px-2 py-0.5 text-on-error font-medium">
                {dangerCount}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-on-surface-variant hover:text-on-surface transition-colors p-1 rounded hover:bg-surface-container-high"
            aria-label="Cerrar notificaciones"
          >
            <Icon name="close" />
          </button>
        </div>
        <p className="font-body-sm text-body-sm text-on-surface-variant mb-3">
          {items.length > 0
            ? `Tienes ${items.length} aviso${items.length === 1 ? '' : 's'} sobre tu cartera de fiados.`
            : 'No hay notificaciones pendientes. Todos los fiados están al día.'}
        </p>

        {items.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-on-surface-variant">
            <Icon name="notifications_off" size="40px" />
            <p className="mt-2 font-body-md text-body-md text-on-surface-variant">Todo en orden</p>
          </div>
        ) : (
          <ul className="divide-y divide-outline-variant max-h-80 overflow-y-auto">
            {items.map((item) => (
              <li key={item.id} className="flex items-start gap-3 py-3">
                <span
                  className={`mt-1 w-2.5 h-2.5 rounded-full shrink-0 ${
                    item.tone === 'danger'
                      ? 'bg-error'
                      : item.tone === 'warning'
                        ? 'bg-amber-400'
                        : 'bg-primary'
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-1">
                    <p className="font-body-sm font-medium text-on-surface truncate">{item.title}</p>
                    {item.amount !== undefined && (
                      <CurrencyDisplay value={item.amount} className="font-body-sm text-body-sm text-on-surface-variant" />
                    )}
                  </div>
                  <p className="font-body-sm text-body-sm text-on-surface-variant truncate">{item.description}</p>
                </div>
                <button
                  type="button"
                  onClick={() => onViewFiado(item.creditId)}
                  className="text-on-surface-variant hover:text-primary text-sm underline-offset-2 hover:underline text-xs"
                  aria-label={`Ver fiado de ${item.creditId}`}
                >
                  Ver
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}