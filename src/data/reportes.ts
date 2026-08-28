export type ReportPeriod = 'hoy' | 'semana' | 'mes'

export interface ReportData {
  label: string
  kpis: {
    sales: number
    credit: number
    recovered: number
    overdue: number
    delinquency: number
  }
  salesTrend: number
  creditTrend: number
  recoveredTrend: number
  overdueTrend: number
  bars: { label: string; cash: number; credit: number }[]
  risk: { low: number; medium: number; high: number; total: number }
  delinquency: number[]
}

export const reportsByPeriod: Record<ReportPeriod, ReportData> = {
  hoy: {
    label: 'Hoy',
    kpis: { sales: 1250, credit: 480, recovered: 320, overdue: 650, delinquency: 8.2 },
    salesTrend: 5, creditTrend: 2, recoveredTrend: 4, overdueTrend: -1,
    bars: [
      { label: '08h', cash: 25, credit: 10 }, { label: '10h', cash: 52, credit: 18 },
      { label: '12h', cash: 76, credit: 32 }, { label: '14h', cash: 48, credit: 40 },
      { label: '16h', cash: 86, credit: 24 }, { label: '18h', cash: 62, credit: 30 },
    ],
    risk: { low: 64, medium: 23, high: 13, total: 342 },
    delinquency: [9, 8, 8.5, 7.8, 8.1, 8.2],
  },
  semana: {
    label: 'Esta semana',
    kpis: { sales: 11240, credit: 3280, recovered: 2410, overdue: 1890, delinquency: 9.1 },
    salesTrend: 9, creditTrend: 3, recoveredTrend: 6, overdueTrend: 1,
    bars: [
      { label: 'Lun', cash: 60, credit: 20 }, { label: 'Mar', cash: 75, credit: 25 },
      { label: 'Mié', cash: 40, credit: 60 }, { label: 'Jue', cash: 90, credit: 15 },
      { label: 'Vie', cash: 80, credit: 35 }, { label: 'Sáb', cash: 65, credit: 30 },
      { label: 'Dom', cash: 30, credit: 10 },
    ],
    risk: { low: 61, medium: 24, high: 15, total: 342 },
    delinquency: [8.4, 8.6, 8.8, 8.7, 9, 9.1],
  },
  mes: {
    label: 'Este mes',
    kpis: { sales: 45230, credit: 12850, recovered: 8420, overdue: 4430, delinquency: 9.8 },
    salesTrend: 12, creditTrend: 4, recoveredTrend: 8, overdueTrend: 2,
    bars: [
      { label: 'Sem 1', cash: 62, credit: 24 }, { label: 'Sem 2', cash: 78, credit: 35 },
      { label: 'Sem 3', cash: 70, credit: 29 }, { label: 'Sem 4', cash: 92, credit: 41 },
    ],
    risk: { low: 60, medium: 25, high: 15, total: 342 },
    delinquency: [6.8, 7.4, 8.2, 7.8, 9.1, 9.8],
  },
}

export const topProducts = [
  { name: 'Cerveza Cristal 650ml', category: 'Bebidas', quantity: 1245, revenue: 8715 },
  { name: 'Cerveza Pilsen 650ml', category: 'Bebidas', quantity: 980, revenue: 6860 },
  { name: 'Agua San Mateo 2.5L', category: 'Bebidas', quantity: 850, revenue: 2550 },
  { name: 'Coca Cola 3L', category: 'Bebidas', quantity: 720, revenue: 6480 },
  { name: 'Arroz Costeño 1kg', category: 'Abarrotes', quantity: 510, revenue: 2142 },
]
