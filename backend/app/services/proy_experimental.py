"""Evaluacion experimental PROY sobre historial real (solo demo de staging).

Toma el historial de la base con los modulos congelados de features, aplica la
compuerta de saldo pendiente y llama al SVM exportado. Guarda la traza en
``proy_experimental_evaluations``; nunca aprueba, recomienda un monto ni crea un
fiado, y no escribe en ``credit_evaluations`` ni en la cola de revisiones.

Si el artefacto o el runtime no estan verificados, falla cerrado: no inventa
probabilidad ni cae al score antiguo.
"""

from decimal import Decimal
from uuid import UUID

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.features import collect_credit_features
from app.ml.proy_contract import CONTRACT_VERSION
from app.ml.proy_model import MODEL_VERSION, THRESHOLD
from app.ml.proy_model import predict_proy as predict_proy_snapshot
from app.models.client import Client
from app.models.proy_experimental import ProyExperimentalEvaluation
from app.models.settings import SETTINGS_ID, BusinessSettings
from app.schemas.proy_experimental import ProyExperimentalEvaluationRead
from app.services.credit_scoring import DEFAULT_MAX_CREDIT_AMOUNT
from app.services.proy_credit_policy import PENDING_BALANCE_BLOCK, gate_from_pending

POLICY_VERSION = "proy-pending-balance-v1"


class ProyClientNotFound(LookupError):
    """El cliente no existe o esta inactivo."""


def _blocked_snapshot_outcome() -> dict:
    # Misma forma que predict_proy para que la traza sea comparable.
    return {
        "decision": PENDING_BALANCE_BLOCK,
        "reason": "pending_debt",
        "probability": None,
        "threshold": THRESHOLD,
        "predicted": None,
        "model_called": False,
        "model_version": MODEL_VERSION,
        "schema_version": CONTRACT_VERSION,
    }


async def _max_credit_amount(db: AsyncSession) -> Decimal:
    policy = await db.get(BusinessSettings, SETTINGS_ID)
    return policy.max_credit_amount if policy else DEFAULT_MAX_CREDIT_AMOUNT


async def evaluate_client_history(
    db: AsyncSession,
    *,
    client_id: UUID,
    amount: Decimal,
    created_by_id: UUID | None,
) -> ProyExperimentalEvaluation:
    """Lee el historial, infiere si aplica y deja la traza sin aprobar nada."""
    client = await db.get(Client, client_id)
    if client is None or not client.is_active:
        raise ProyClientNotFound
    features = await collect_credit_features(
        db, client, amount, await _max_credit_amount(db)
    )
    snapshot = {
        "completed_sales": features.completed_sales,
        "paid_credits": features.paid_credits,
        "paid_late": features.paid_late,
        "pending_overdue": features.pending_overdue,
        "pending_current": features.pending_current,
        "outstanding": features.outstanding,
        "utilization": features.utilization,
        "requested_ratio": features.requested_ratio,
        "tenure_days": features.tenure_days,
        "punctuality_rate": features.punctuality_rate,
        "overdue_rate": features.overdue_rate,
    }
    gate = gate_from_pending(features.outstanding)
    outcome = (
        _blocked_snapshot_outcome()
        if gate.decision == PENDING_BALANCE_BLOCK
        # La inferencia es sincrona y puede deserializar el artefacto: fuera del loop.
        else await run_in_threadpool(predict_proy_snapshot, snapshot)
    )
    evaluation = ProyExperimentalEvaluation(
        client_id=client.id,
        created_by_id=created_by_id,
        requested_amount=amount,
        pending_amount=gate.pending_amount,
        decision=outcome["decision"],
        reason=outcome["reason"],
        probability=outcome["probability"],
        threshold=Decimal(str(outcome["threshold"])),
        predicted=outcome["predicted"],
        model_called=outcome["model_called"],
        model_version=outcome["model_version"],
        schema_version=outcome["schema_version"],
        policy_version=POLICY_VERSION,
        feature_snapshot={name: float(value) for name, value in snapshot.items()},
    )
    db.add(evaluation)
    await db.flush()
    return evaluation


def serialize(evaluation: ProyExperimentalEvaluation) -> ProyExperimentalEvaluationRead:
    return ProyExperimentalEvaluationRead(
        id=evaluation.id,
        client_id=evaluation.client_id,
        requested_amount=evaluation.requested_amount,
        pending_amount=evaluation.pending_amount,
        decision=evaluation.decision,
        reason=evaluation.reason,
        probability=evaluation.probability,
        threshold=evaluation.threshold,
        predicted=evaluation.predicted,
        model_called=evaluation.model_called,
        model_version=evaluation.model_version,
        schema_version=evaluation.schema_version,
        policy_version=evaluation.policy_version,
        feature_snapshot=evaluation.feature_snapshot,
        created_at=evaluation.created_at,
    )
