import type { Cliente } from '@/data/clientes'
import type { RiskLevel } from '@/types'

export interface CreditEvaluation {
  score: number
  risk: RiskLevel
  defaultProbability: number
  recommendedLimit: number
  approved: boolean
  recommendation: string
  calculatedAt: string
  responseTimeMs: number
}

export interface CreditScoringService {
  evaluate(client: Cliente, requestedAmount: number): Promise<CreditEvaluation>
}

const riskBase: Record<RiskLevel, number> = {
  'muy-bajo': 94,
  bajo: 86,
  medio: 70,
  alto: 52,
  critico: 38,
}

function riskFromScore(score: number): RiskLevel {
  if (score >= 88) return 'muy-bajo'
  if (score >= 76) return 'bajo'
  if (score >= 61) return 'medio'
  if (score >= 46) return 'alto'
  return 'critico'
}

export const localScoringService: CreditScoringService = {
  async evaluate(client, requestedAmount) {
    const startedAt = performance.now()
    await new Promise((resolve) => window.setTimeout(resolve, 650))

    const debtPenalty = Math.min(client.debt / 250, 22)
    const amountPenalty = Math.min(requestedAmount / 300, 18)
    const loyaltyBonus = Math.min(client.purchases / 45, 7)
    const score = Math.round(
      Math.max(30, Math.min(98, riskBase[client.risk] - debtPenalty - amountPenalty + loyaltyBonus)),
    )
    const risk = riskFromScore(score)
    const recommendedLimit = Math.max(
      50,
      Math.round((client.purchases * 8 + score * 12 - client.debt * 0.2) / 50) * 50,
    )
    const approved = requestedAmount <= recommendedLimit && !['alto', 'critico'].includes(risk)

    return {
      score,
      risk,
      defaultProbability: Math.max(2, 100 - score),
      recommendedLimit,
      approved,
      recommendation: approved
        ? `Se recomienda aprobar el fiado hasta ${recommendedLimit.toLocaleString('es-PE', { style: 'currency', currency: 'PEN' })}.`
        : `El monto supera el límite recomendado de ${recommendedLimit.toLocaleString('es-PE', { style: 'currency', currency: 'PEN' })}. Requiere decisión manual.`,
      calculatedAt: new Date().toISOString(),
      responseTimeMs: Math.round(performance.now() - startedAt),
    }
  },
}
