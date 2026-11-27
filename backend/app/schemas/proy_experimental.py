from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ProyExperimentalEvaluationRequest(BaseModel):
    client_id: UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class ProyExperimentalEvaluationRead(BaseModel):
    id: UUID
    client_id: UUID
    requested_amount: Decimal
    pending_amount: Decimal
    decision: str
    reason: str
    probability: float | None
    threshold: Decimal
    predicted: int | None
    model_called: bool
    model_version: str
    schema_version: str
    policy_version: str
    feature_snapshot: dict[str, float]
    research_only: Literal[True] = True
    business_approval: Literal[False] = False
    final_test_evaluated: Literal[False] = False
    requires_human_decision: Literal[True] = True
    created_at: datetime
