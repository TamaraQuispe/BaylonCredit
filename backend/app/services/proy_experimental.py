"""Evaluacion experimental PROY sobre historial real (solo demo de staging).

Toma el historial con los modulos congelados de features y llama al SVM, que
resuelve la compuerta de saldo pendiente antes de cargar el artefacto. Guarda la
traza en ``proy_experimental_evaluations``; nunca aprueba, recomienda un monto ni
crea un fiado, y no escribe en ``credit_evaluations`` ni en la cola de revisiones.

Si el artefacto o el runtime no estan verificados, falla cerrado: no inventa
probabilidad ni cae al score antiguo.
"""

from decimal import Decimal
from uuid import UUID

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.features import collect_credit_features
from app.ml.proy_model import predict_proy
from app.models.client import Client
from app.models.proy_experimental import ProyExperimentalEvaluation
from app.models.settings import SETTINGS_ID, BusinessSettings
from app.services.credit_scoring import DEFAULT_MAX_CREDIT_AMOUNT

POLICY_VERSION = "proy-pending-balance-v1"


class ProyClientNotFound(LookupError):
    """El cliente no existe o esta inactivo."""


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
    policy = await db.get(BusinessSettings, SETTINGS_ID)
    features = await collect_credit_features(
        db,
        client,
        amount,
        policy.max_credit_amount if policy else DEFAULT_MAX_CREDIT_AMOUNT,
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
    # La inferencia es sincrona y puede deserializar el artefacto: fuera del loop.
    outcome = await run_in_threadpool(predict_proy, snapshot)
    evaluation = ProyExperimentalEvaluation(
        client_id=client.id,
        created_by_id=created_by_id,
        requested_amount=amount,
        pending_amount=features.outstanding,
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
