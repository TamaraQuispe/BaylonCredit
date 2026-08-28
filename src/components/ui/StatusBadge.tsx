import Badge, { type BadgeTone } from './Badge'

export type FiadoStatus = 'al-dia' | 'proximo-a-vencer' | 'vencido' | 'pagado'
export type InventoryStatus = 'disponible' | 'stock-bajo' | 'agotado'
export type GeneralStatus = 'activo' | 'inactivo'

type StatusKey = FiadoStatus | InventoryStatus | GeneralStatus

const fiadoMap: Record<FiadoStatus, { tone: BadgeTone; label: string }> = {
  'al-dia': { tone: 'primary', label: 'Al día' },
  'proximo-a-vencer': { tone: 'warning', label: 'Próximo a vencer' },
  vencido: { tone: 'danger', label: 'Vencido' },
  pagado: { tone: 'neutral', label: 'Pagado' },
}

const inventoryMap: Record<InventoryStatus, { tone: BadgeTone; label: string }> = {
  disponible: { tone: 'success', label: 'Disponible' },
  'stock-bajo': { tone: 'warning', label: 'Stock bajo' },
  agotado: { tone: 'danger', label: 'Agotado' },
}

const generalMap: Record<GeneralStatus, { tone: BadgeTone; label: string }> = {
  activo: { tone: 'success', label: 'Activo' },
  inactivo: { tone: 'disabled', label: 'Inactivo' },
}

interface StatusBadgeProps {
  status: StatusKey
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const config =
    fiadoMap[status as FiadoStatus] ??
    inventoryMap[status as InventoryStatus] ??
    generalMap[status as GeneralStatus]

  return <Badge tone={config.tone}>{config.label}</Badge>
}
