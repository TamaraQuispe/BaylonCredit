import type { RiskLevel, FiadoStatus } from '@/types'

export interface Fiado {
  id: string
  code: string
  client: {
    initials: string
    name: string
    business: string
  }
  originalAmount: number
  pendingAmount: number
  paidAmount: number
  createdAt: string
  dueAt: string
  status: FiadoStatus
  risk: RiskLevel
  paidPercent: number
}

export interface FiadoDetail extends Fiado {
  phone: string
  hasHistory: boolean
  daysLeft: number
  payments: {
    title: string
    description: string
    amount: number
    date: string
    type: 'registered' | 'payment' | 'pending'
  }[]
}

export const fiadoStats = {
  totalToCollect: { label: 'Total por cobrar', value: 'S/ 45,230.00', detail: 'En 124 fiados activos', icon: 'account_balance_wallet', tone: 'primary-fixed' },
  alDia: { label: 'Deuda al día', value: 'S/ 32,150.00', detail: '71% del total', icon: 'check_circle', tone: 'highest' },
  vencida: { label: 'Deuda vencida', value: 'S/ 13,080.00', detail: '+5.2% esta semana', icon: 'warning', tone: 'error-container' },
  morosos: { label: 'Clientes morosos', value: '18', detail: 'Requieren gestión inmediata', icon: 'group_off', tone: 'secondary-container' },
}

export const fiados: Fiado[] = [
  {
    id: 'f1',
    code: 'F-2023-0892',
    client: {
      initials: 'CM',
      name: 'Carlos Mendoza',
      business: 'Bodega "El Sol"',
    },
    originalAmount: 1200,
    pendingAmount: 1200,
    paidAmount: 0,
    createdAt: '15/10/2023',
    dueAt: '15/11/2023',
    status: 'al-dia',
    risk: 'bajo',
    paidPercent: 0,
  },
  {
    id: 'f2',
    code: 'F-2023-0871',
    client: {
      initials: 'LP',
      name: 'Lucía Pérez',
      business: 'Minimarket "Los Pinos"',
    },
    originalAmount: 3500,
    pendingAmount: 2100,
    paidAmount: 1400,
    createdAt: '01/09/2023',
    dueAt: '01/10/2023',
    status: 'vencido',
    risk: 'alto',
    paidPercent: 40,
  },
  {
    id: 'f3',
    code: 'F-2023-0880',
    client: {
      initials: 'JR',
      name: 'Jorge Ramírez',
      business: 'Abarrotes "Don Jorge"',
    },
    originalAmount: 850,
    pendingAmount: 850,
    paidAmount: 0,
    createdAt: '20/09/2023',
    dueAt: '20/10/2023',
    status: 'proximo-a-vencer',
    risk: 'medio',
    paidPercent: 0,
  },
  {
    id: 'f4',
    code: 'F-2023-0855',
    client: {
      initials: 'MF',
      name: 'María Fernández',
      business: 'Licorería "La Cabaña"',
    },
    originalAmount: 2400,
    pendingAmount: 0,
    paidAmount: 2400,
    createdAt: '05/09/2023',
    dueAt: '05/10/2023',
    status: 'pagado',
    risk: 'muy-bajo',
    paidPercent: 100,
  },
]

export const fiadoDetail: FiadoDetail = {
  id: 'f-detail',
  code: 'F-2023-0892',
  client: {
    initials: 'CM',
    name: 'Carlos Mendoza Salas',
    business: 'Bodega "El Sol"',
  },
  originalAmount: 1200,
  pendingAmount: 450,
  paidAmount: 750,
  createdAt: '12 Oct 2023',
  dueAt: '30 Nov 2023',
  status: 'al-dia',
  risk: 'bajo',
  paidPercent: 62.5,
  phone: '+51 987 654 321',
  hasHistory: true,
  daysLeft: 14,
  payments: [
    {
      title: 'Fiado registrado',
      description: 'Crédito inicial aprobado.',
      amount: 1200,
      date: '12 Oct 2023, 10:30 AM',
      type: 'registered',
    },
    {
      title: 'Pago parcial',
      description: 'Transferencia bancaria.',
      amount: -400,
      date: '25 Oct 2023, 14:15 PM',
      type: 'payment',
    },
    {
      title: 'Pago parcial',
      description: 'Efectivo en ventanilla.',
      amount: -350,
      date: '10 Nov 2023, 09:45 AM',
      type: 'payment',
    },
    {
      title: 'Pago completado',
      description: 'Pendiente de cancelación total.',
      amount: 450,
      date: 'Restante',
      type: 'pending',
    },
  ],
}
