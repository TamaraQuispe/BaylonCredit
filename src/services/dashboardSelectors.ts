import type { ActivityEntry } from '@/components/dashboard/ActivityFeed'
import type { CustomerAttention, FiadoSegment } from '@/data/home'
import type { RiskLevel } from '@/types'
import { formatCurrency } from '@/utils/format'
import type { StoredClient } from './clientRepository'
import type { StoredCredit, StoredPayment } from './creditRepository'
import type { StoredSale } from './salesRepository'

interface DashboardMetrics {
  totalPending: number
  totalOverdue: number
  totalRecovered: number
  paymentsToday: number
  activeCredits: number
  clientsWithDebt: number
  criticalClients: number
  delinquencyRate: number
  attention: CustomerAttention[]
  fiadoSegments: FiadoSegment[]
  recentActivity: ActivityEntry[]
  risk: {
    low: number
    medium: number
    high: number
    total: number
  }
}

const DAY_IN_MS = 86_400_000

function parseStoredDate(value: string): Date | null {
  if (/^\d{4}-\d{2}-\d{2}T/.test(value)) {
    const timestamp = new Date(value)
    return Number.isNaN(timestamp.getTime()) ? null : timestamp
  }
  const iso = value.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (iso) return new Date(Number(iso[1]), Number(iso[2]) - 1, Number(iso[3]))

  const local = value.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/)
  if (local) return new Date(Number(local[3]), Number(local[2]) - 1, Number(local[1]))

  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

function getDaysOverdue(dueAt: string, today: Date) {
  const dueDate = parseStoredDate(dueAt)
  if (!dueDate) return 0
  dueDate.setHours(0, 0, 0, 0)
  return Math.max(0, Math.floor((today.getTime() - dueDate.getTime()) / DAY_IN_MS))
}

function percentage(value: number, total: number) {
  return total > 0 ? Number(((value / total) * 100).toFixed(1)) : 0
}

function activityTime(timestamp: number, now: Date) {
  if (!timestamp) return 'Fecha no disponible'
  const difference = Math.max(0, now.getTime() - timestamp)
  const minutes = Math.floor(difference / 60_000)
  if (minutes < 1) return 'Ahora'
  if (minutes < 60) return `Hace ${minutes} min`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `Hace ${hours} h`
  const days = Math.floor(hours / 24)
  if (days <= 7) return `Hace ${days} d`
  return new Intl.DateTimeFormat('es-PE').format(new Date(timestamp))
}

function selectRecentActivity(
  credits: StoredCredit[],
  payments: StoredPayment[],
  clients: StoredClient[],
  sales: StoredSale[],
  now: Date,
): ActivityEntry[] {
  const entries: Array<ActivityEntry & { timestamp: number }> = [
    ...sales.map((sale) => ({
      id: `activity-${sale.id}`,
      title: `Venta de ${formatCurrency(sale.total)} registrada`,
      description: `${sale.code} · ${sale.paymentMode === 'contado' ? 'Venta al contado' : `Fiado a ${sale.clientName}`}`,
      time: '',
      icon: 'point_of_sale',
      tone: 'primary' as const,
      timestamp: parseStoredDate(sale.createdAt)?.getTime() ?? 0,
    })),
    ...payments.map((payment) => ({
      id: `activity-${payment.id}`,
      title: `Pago de ${formatCurrency(payment.amount)} registrado`,
      description: `${payment.client} abonó a ${payment.creditCode || 'su deuda pendiente'}`,
      time: '',
      icon: 'payments',
      tone: 'success' as const,
      timestamp: parseStoredDate(payment.paymentDate)?.getTime() ?? parseStoredDate(payment.paidAt)?.getTime() ?? 0,
    })),
    ...credits.map((credit) => ({
      id: `activity-${credit.id}`,
      title: `Fiado de ${formatCurrency(credit.originalAmount)} registrado`,
      description: `${credit.client.business} · ${credit.code}`,
      time: '',
      icon: 'receipt_long',
      tone: 'secondary' as const,
      timestamp: parseStoredDate(credit.createdAt)?.getTime() ?? 0,
    })),
    ...clients.map((client) => ({
      id: `activity-${client.id}`,
      title: 'Cliente registrado',
      description: `${client.business} se añadió a la cartera de clientes`,
      time: '',
      icon: 'person_add',
      tone: 'primary' as const,
      timestamp: parseStoredDate(client.registeredAt)?.getTime() ?? 0,
    })),
  ]

  return entries
    .sort((a, b) => b.timestamp - a.timestamp)
    .slice(0, 5)
    .map(({ timestamp, ...entry }) => ({ ...entry, time: activityTime(timestamp, now) }))
}

export function selectDashboardMetrics(
  credits: StoredCredit[],
  payments: StoredPayment[],
  clients: StoredClient[],
  sales: StoredSale[] = [],
  now = new Date(),
): DashboardMetrics {
  const today = new Date(now)
  today.setHours(0, 0, 0, 0)
  const activeCredits = credits.filter((credit) => credit.pendingAmount > 0)
  const overdueCredits = activeCredits.filter((credit) => credit.status === 'vencido')
  const totalPending = activeCredits.reduce((sum, credit) => sum + credit.pendingAmount, 0)
  const totalOverdue = overdueCredits.reduce((sum, credit) => sum + credit.pendingAmount, 0)
  const totalRecovered = payments.reduce((sum, payment) => sum + payment.amount, 0)
  const paymentsToday = payments
    .filter((payment) => {
      const date = parseStoredDate(payment.paymentDate)
      return date?.toDateString() === today.toDateString()
    })
    .reduce((sum, payment) => sum + payment.amount, 0)
  const debtorKeys = new Set(activeCredits.map((credit) => credit.clientId ?? credit.client.business))
  const criticalKeys = new Set(
    activeCredits
      .filter((credit) => credit.risk === 'alto' || credit.risk === 'critico')
      .map((credit) => credit.clientId ?? credit.client.business),
  )

  const attention = overdueCredits
    .map((credit) => ({
      id: credit.id,
      name: credit.client.business,
      fiado: credit.code,
      amount: credit.pendingAmount,
      daysOverdue: getDaysOverdue(credit.dueAt, today),
      risk: credit.risk,
    }))
    .sort((a, b) => b.daysOverdue - a.daysOverdue || b.amount - a.amount)
    .slice(0, 5)

  const amountsByStatus = {
    current: activeCredits
      .filter((credit) => credit.status === 'al-dia')
      .reduce((sum, credit) => sum + credit.pendingAmount, 0),
    upcoming: activeCredits
      .filter((credit) => credit.status === 'proximo-a-vencer')
      .reduce((sum, credit) => sum + credit.pendingAmount, 0),
    overdue: totalOverdue,
  }
  const fiadoSegments: FiadoSegment[] = [
    { label: 'Al día', value: formatCurrency(amountsByStatus.current), color: '#10b981', percent: percentage(amountsByStatus.current, totalPending) },
    { label: 'Próximo a vencer', value: formatCurrency(amountsByStatus.upcoming), color: '#f59e0b', percent: percentage(amountsByStatus.upcoming, totalPending) },
    { label: 'Vencido', value: formatCurrency(amountsByStatus.overdue), color: '#ba1a1a', percent: percentage(amountsByStatus.overdue, totalPending) },
  ]

  const latestRisk = new Map<string, RiskLevel>()
  credits.forEach((credit) => {
    if (credit.clientId && !latestRisk.has(credit.clientId)) latestRisk.set(credit.clientId, credit.risk)
  })
  const riskCounts = clients.reduce(
    (counts, client) => {
      const risk = latestRisk.get(client.id) ?? client.risk
      if (risk === 'muy-bajo' || risk === 'bajo') counts.low += 1
      else if (risk === 'medio') counts.medium += 1
      else counts.high += 1
      return counts
    },
    { low: 0, medium: 0, high: 0 },
  )

  return {
    totalPending,
    totalOverdue,
    totalRecovered,
    paymentsToday,
    activeCredits: activeCredits.length,
    clientsWithDebt: debtorKeys.size,
    criticalClients: criticalKeys.size,
    delinquencyRate: percentage(totalOverdue, totalPending),
    attention,
    fiadoSegments,
    recentActivity: selectRecentActivity(credits, payments, clients, sales, now),
    risk: {
      low: percentage(riskCounts.low, clients.length),
      medium: percentage(riskCounts.medium, clients.length),
      high: percentage(riskCounts.high, clients.length),
      total: clients.length,
    },
  }
}
