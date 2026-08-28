import Badge, { type BadgeTone } from './Badge'

export type RiskLevel = 'muy-bajo' | 'bajo' | 'medio' | 'alto' | 'critico'

const riskMap: Record<RiskLevel, { tone: BadgeTone; label: string }> = {
  'muy-bajo': { tone: 'neutral', label: 'Muy Bajo' },
  bajo: { tone: 'neutral', label: 'Bajo' },
  medio: { tone: 'warning', label: 'Medio' },
  alto: { tone: 'danger', label: 'Alto' },
  critico: { tone: 'danger', label: 'Crítico' },
}

interface RiskBadgeProps {
  level: RiskLevel
}

export default function RiskBadge({ level }: RiskBadgeProps) {
  const config = riskMap[level]
  return <Badge tone={config.tone}>{config.label}</Badge>
}
