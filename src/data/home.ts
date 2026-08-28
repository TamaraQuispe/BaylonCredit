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
