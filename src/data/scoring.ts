export interface CreditProfile {
  id: string
  initials: string
  name: string
  document: string
  since: string
  score: number
  risk: 'Bajo' | 'Medio' | 'Alto'
  recommendedLimit: number
  suggestedRate: number
  paymentCapacity: number
  capacityTrend: string
  debtLevel: number
  punctuality: number
  factors: { label: string; value: string; percent: number; tone: 'primary' | 'warning' | 'success' }[]
  history: { date: string; score: number; requestedAmount: number; result: string; tone: 'success' | 'warning' | 'danger' }[]
}

export const creditProfiles: CreditProfile[] = [
  {
    id: 'score1', initials: 'JP', name: 'Juan Pérez Gonzáles', document: '45678912', since: '2021', score: 85, risk: 'Bajo', recommendedLimit: 2500, suggestedRate: 2.5, paymentCapacity: 1200, capacityTrend: '+12%', debtLevel: 24, punctuality: 98,
    factors: [
      { label: 'Ticket Promedio Mensual', value: 'S/ 450.00', percent: 75, tone: 'primary' },
      { label: 'Frecuencia de Compra', value: 'Alta (3.2 / sem)', percent: 90, tone: 'primary' },
      { label: 'Riesgo Sectorial (Retail)', value: 'Medio-Bajo', percent: 40, tone: 'warning' },
      { label: 'Atrasos Promedio', value: '1.2 Días', percent: 15, tone: 'success' },
    ],
    history: [
      { date: '15 Oct 2023', score: 85, requestedAmount: 2000, result: 'Aprobado', tone: 'success' },
      { date: '20 Jul 2023', score: 82, requestedAmount: 1500, result: 'Aprobado', tone: 'success' },
      { date: '10 Feb 2023', score: 68, requestedAmount: 3000, result: 'Req. Garantía', tone: 'warning' },
    ],
  },
  {
    id: 'score2', initials: 'MS', name: 'María Silva Rojas', document: '74125896', since: '2022', score: 72, risk: 'Medio', recommendedLimit: 1400, suggestedRate: 3.2, paymentCapacity: 780, capacityTrend: '+4%', debtLevel: 41, punctuality: 84,
    factors: [
      { label: 'Ticket Promedio Mensual', value: 'S/ 310.00', percent: 58, tone: 'primary' },
      { label: 'Frecuencia de Compra', value: 'Media (1.8 / sem)', percent: 62, tone: 'primary' },
      { label: 'Riesgo Sectorial (Retail)', value: 'Medio', percent: 55, tone: 'warning' },
      { label: 'Atrasos Promedio', value: '4.5 Días', percent: 38, tone: 'warning' },
    ],
    history: [
      { date: '12 Oct 2023', score: 72, requestedAmount: 1200, result: 'Aprobado', tone: 'success' },
      { date: '08 Jun 2023', score: 66, requestedAmount: 1800, result: 'Req. Garantía', tone: 'warning' },
    ],
  },
  {
    id: 'score3', initials: 'EV', name: "Bodega 'El Vecino' EIRL", document: '20601478521', since: '2020', score: 56, risk: 'Alto', recommendedLimit: 600, suggestedRate: 4.1, paymentCapacity: 520, capacityTrend: '-8%', debtLevel: 68, punctuality: 65,
    factors: [
      { label: 'Ticket Promedio Mensual', value: 'S/ 520.00', percent: 72, tone: 'primary' },
      { label: 'Frecuencia de Compra', value: 'Alta (2.9 / sem)', percent: 84, tone: 'primary' },
      { label: 'Riesgo Sectorial (Retail)', value: 'Medio-Alto', percent: 71, tone: 'warning' },
      { label: 'Atrasos Promedio', value: '12 Días', percent: 76, tone: 'warning' },
    ],
    history: [
      { date: '18 Sep 2023', score: 56, requestedAmount: 1500, result: 'Rechazado', tone: 'danger' },
      { date: '02 May 2023', score: 61, requestedAmount: 1000, result: 'Req. Garantía', tone: 'warning' },
    ],
  },
]
