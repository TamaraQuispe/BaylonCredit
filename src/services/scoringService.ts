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
  modelVersion?: string
  aiExplanation?: string
  aiRiskFactors?: string[]
  aiRecommendations?: string[]
  aiStatus?: 'disabled' | 'pending' | 'completed' | 'failed'
  aiModel?: string
  aiPromptVersion?: string
  aiGeneratedAt?: string
  calculatedAt: string
  responseTimeMs: number
}

export interface StoredCreditEvaluation extends CreditEvaluation {
  id: string
  clientId: string
  clientName: string
  requestedAmount: number
  modelVersion: string
  source: string
}

export interface EvaluationSummary {
  totalClients: number
  evaluatedClients: number
  coveragePercent: number
}

export interface CreditScoringService {
  evaluate(client: Cliente, requestedAmount: number): Promise<CreditEvaluation>
  listEvaluations(clientId?: string): Promise<StoredCreditEvaluation[]>
  getEvaluationSummary(): Promise<EvaluationSummary>
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
  model_version?: string
  ai_explanation?: string | null
  ai_risk_factors?: string[] | null
  ai_recommendations?: string[] | null
  ai_status?: 'disabled' | 'pending' | 'completed' | 'failed'
  ai_model?: string | null
  ai_prompt_version?: string | null
  ai_generated_at?: string | null
  calculated_at: string
  response_time_ms: number
}

interface ApiStoredEvaluation extends ApiEvaluation {
  id: string
  client_id: string
  client_name: string
  requested_amount: string | number
  model_version: string
  source: string
}

interface ApiEvaluationSummary {
  total_clients: number
  evaluated_clients: number
  coverage_percent: number
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
    modelVersion: evaluation.model_version,
    aiExplanation: evaluation.ai_explanation ?? undefined,
    aiRiskFactors: evaluation.ai_risk_factors ?? undefined,
    aiRecommendations: evaluation.ai_recommendations ?? undefined,
    aiStatus: evaluation.ai_status,
    aiModel: evaluation.ai_model ?? undefined,
    aiPromptVersion: evaluation.ai_prompt_version ?? undefined,
    aiGeneratedAt: evaluation.ai_generated_at ?? undefined,
    calculatedAt: evaluation.calculated_at,
    responseTimeMs: evaluation.response_time_ms,
  }
}

export async function listEvaluations(clientId?: string): Promise<StoredCreditEvaluation[]> {
  const query = new URLSearchParams({ limit: '100' })
  if (clientId) query.set('client_id', clientId)
  const evaluations = await apiRequest<ApiStoredEvaluation[]>(`/credits/evaluations?${query}`)
  return evaluations.map((evaluation) => ({
    ...mapEvaluation(evaluation),
    id: evaluation.id,
    clientId: evaluation.client_id,
    clientName: evaluation.client_name,
    requestedAmount: Number(evaluation.requested_amount),
    modelVersion: evaluation.model_version,
    source: evaluation.source,
  }))
}

export async function getEvaluationSummary(): Promise<EvaluationSummary> {
  const summary = await apiRequest<ApiEvaluationSummary>('/credits/evaluations/summary')
  return {
    totalClients: summary.total_clients,
    evaluatedClients: summary.evaluated_clients,
    coveragePercent: summary.coverage_percent,
  }
}

export const localScoringService: CreditScoringService = {
  async evaluate(client, requestedAmount) {
    return mapEvaluation(await apiRequest<ApiEvaluation>('/credits/evaluate', {
      method: 'POST',
      body: JSON.stringify({ client_id: client.id, amount: requestedAmount }),
    }))
  },
  listEvaluations,
  getEvaluationSummary,
}
