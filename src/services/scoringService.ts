import type { Cliente } from '@/data/clientes'
import type { RiskLevel } from '@/types'
import { apiRequest } from './apiClient'

export interface ScoreFactor {
  key: string
  label: string
  weight: number
  contribution: number
  description: string
}

export interface CreditEvaluation {
  score: number
  risk: RiskLevel
  defaultProbability: number
  recommendedLimit: number
  approved: boolean
  recommendation: string
  confidence?: number
  factors?: ScoreFactor[]
  calculatedAt: string
  responseTimeMs: number
}

export interface CreditScoringService {
  evaluate(client: Cliente, requestedAmount: number): Promise<CreditEvaluation>
}

interface ApiEvaluation {
  score: number
  risk: RiskLevel
  default_probability: number
  recommended_limit: string | number
  approved: boolean
  recommendation: string
  confidence?: number
  factors?: ScoreFactor[]
  calculated_at: string
  response_time_ms: number
}

function mapEvaluation(evaluation: ApiEvaluation): CreditEvaluation {
  return {
    score: evaluation.score,
    risk: evaluation.risk,
    defaultProbability: evaluation.default_probability,
    recommendedLimit: Number(evaluation.recommended_limit),
    approved: evaluation.approved,
    recommendation: evaluation.recommendation,
    confidence: evaluation.confidence,
    factors: evaluation.factors,
    calculatedAt: evaluation.calculated_at,
    responseTimeMs: evaluation.response_time_ms,
  }
}

export const localScoringService: CreditScoringService = {
  async evaluate(client, requestedAmount) {
    return mapEvaluation(await apiRequest<ApiEvaluation>('/credits/evaluate', {
      method: 'POST',
      body: JSON.stringify({ client_id: client.id, amount: requestedAmount }),
    }))
  },
}
