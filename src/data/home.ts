import type { RiskLevel } from '@/types'

export interface StatData {
  label: string
  value: string
  detail?: string
  detailTone?: 'positive' | 'negative' | 'neutral'
  icon: string
  iconTone: 'primary' | 'secondary' | 'error' | 'tertiary' | 'success'
}

export const homeStats: StatData[] = [
  {
    label: 'Ventas de hoy',
    value: 'S/ 1,250.00',
    detail: '+5.2% vs ayer',
    detailTone: 'positive',
    icon: 'point_of_sale',
    iconTone: 'primary',
  },
  {
    label: 'Total fiado',
    value: 'S/ 4,800.00',
    detail: 'Actualmente',
    icon: 'account_balance_wallet',
    iconTone: 'secondary',
  },
  {
    label: 'Deuda vencida',
    value: 'S/ 650.00',
    detail: 'Requiere atención',
    detailTone: 'negative',
    icon: 'warning',
    iconTone: 'error',
  },
  {
    label: 'Clientes con deuda',
    value: '12',
    detail: '3 críticos',
    icon: 'group_remove',
    iconTone: 'tertiary',
  },
  {
    label: 'Pagos hoy',
    value: 'S/ 320.00',
    detail: 'Recibidos',
    icon: 'payments',
    iconTone: 'success',
  },
]

export interface CustomerAttention {
  id: string
  name: string
  fiado: string
  amount: number
  daysOverdue: number
  risk: RiskLevel
}

export const customersAttention: CustomerAttention[] = [
  { id: '1', name: 'María Gonzáles', fiado: 'F-2024-018', amount: 320, daysOverdue: 30, risk: 'critico' },
  { id: '2', name: 'Juan Pérez', fiado: 'F-2024-015', amount: 180, daysOverdue: 15, risk: 'alto' },
  { id: '3', name: 'Lucía Ramírez', fiado: 'F-2024-022', amount: 95, daysOverdue: 8, risk: 'medio' },
  { id: '4', name: 'Carlos Torres', fiado: 'F-2024-009', amount: 45, daysOverdue: 3, risk: 'bajo' },
]

export interface FiadoSegment {
  label: string
  value: string
  color: string
  percent: number
}

export const fiadoDonut: FiadoSegment[] = [
  { label: 'Al día', value: 'S/ 3,340.00', color: '#10b981', percent: 60 },
  { label: 'Próximo a vencer', value: 'S/ 1,050.00', color: '#f59e0b', percent: 25 },
  { label: 'Vencido', value: 'S/ 410.00', color: '#ba1a1a', percent: 15 },
]

export interface ActivityItem {
  id: string
  title: string
  description: string
  time: string
  icon: string
  tone: 'primary' | 'secondary' | 'error' | 'success'
}

export const recentActivity: ActivityItem[] = [
  {
    id: '1',
    title: 'Pago de S/ 200.00 registrado',
    description: 'María Gonzáles abonó a su fiado F-2024-018',
    time: 'Hace 10 min',
    icon: 'payments',
    tone: 'success',
  },
  {
    id: '2',
    title: 'Fiado vencido',
    description: 'El fiado F-2024-015 de Juan Pérez venció hoy',
    time: 'Hace 1 h',
    icon: 'warning',
    tone: 'error',
  },
  {
    id: '3',
    title: 'Nuevo cliente registrado',
    description: 'Lucía Ramírez se añadió a la lista de clientes',
    time: 'Hace 3 h',
    icon: 'person_add',
    tone: 'primary',
  },
  {
    id: '4',
    title: 'Nuevo fiado creado',
    description: 'Carlos Torres registró un fiado por S/ 45.00',
    time: 'Ayer',
    icon: 'receipt_long',
    tone: 'secondary',
  },
]
