import type { RiskLevel } from '@/types'

export interface Cliente {
  id: string
  initials: string
  business: string
  name: string
  document: string
  phone: string
  purchases: number
  debt: number
  status: 'al-dia' | 'vencido' | 'sin-deuda' | 'pendiente'
  risk: RiskLevel
}

export const clients: Cliente[] = [
  {
    id: 'c1',
    initials: 'JR',
    business: 'Bodega Don Pepe',
    name: 'José Ramírez',
    document: '10458923451',
    phone: '987 654 321',
    purchases: 142,
    debt: 1250,
    status: 'al-dia',
    risk: 'bajo',
  },
  {
    id: 'c2',
    initials: 'MM',
    business: 'Minimarket María',
    name: 'María Mendoza',
    document: '42567812',
    phone: '945 123 789',
    purchases: 56,
    debt: 4800.5,
    status: 'vencido',
    risk: 'alto',
  },
  {
    id: 'c3',
    initials: 'CR',
    business: 'Distribuidora Central',
    name: 'Carlos Ruiz',
    document: '20123456781',
    phone: '999 888 777',
    purchases: 312,
    debt: 0,
    status: 'sin-deuda',
    risk: 'muy-bajo',
  },
  {
    id: 'c4',
    initials: 'LF',
    business: 'Licorería El Faro',
    name: 'Luis Torres',
    document: '41238904',
    phone: '911 222 333',
    purchases: 89,
    debt: 850.2,
    status: 'pendiente',
    risk: 'medio',
  },
  {
    id: 'c5',
    initials: 'PH',
    business: 'Comercial Los Andes',
    name: 'Pedro Huamán',
    document: '20876543219',
    phone: '977 665 544',
    purchases: 205,
    debt: 3100,
    status: 'al-dia',
    risk: 'bajo',
  },
]

export interface ClientProfile {
  initials: string
  name: string
  document: string
  phone: string
  since: string
  kpis: {
    deudaActual: number
    totalComprado: number
    totalFiado: number
    fiadosPagados: number
    pagosAtrasados: number
  }
  credit: {
    score: number
    risk: string
    defaultProbability: number
    recommendedLimit: number
    apt: boolean
  }
  history: {
    date: string
    description: string
    amount: number
    status: 'Pagado' | 'Fiado Pdto.'
  }[]
}

export const clientProfile: ClientProfile = {
  initials: 'JR',
  name: 'José Ramírez',
  document: '45678912',
  phone: '987 654 321',
  since: '15/03/2021',
  kpis: {
    deudaActual: 45.5,
    totalComprado: 1250,
    totalFiado: 380,
    fiadosPagados: 12,
    pagosAtrasados: 1,
  },
  credit: {
    score: 86,
    risk: 'BAJO',
    defaultProbability: 18,
    recommendedLimit: 150,
    apt: true,
  },
  history: [
    { date: '12/10/2023', description: 'Compra de Cerveza Cristal (Caja) x2', amount: 110, status: 'Pagado' },
    { date: '05/10/2023', description: 'Pilsen Callao 650ml x6', amount: 42, status: 'Fiado Pdto.' },
    { date: '28/09/2023', description: 'Gaseosa Inka Kola 3L + Snacks', amount: 25.5, status: 'Pagado' },
    { date: '15/09/2023', description: 'Cuzqueña Trigo x4', amount: 28, status: 'Pagado' },
  ],
}
