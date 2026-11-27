"""Endpoint experimental PROY: apagado por defecto y solo demo de staging.

No aprueba ni crea creditos: persiste unicamente la traza de investigacion.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_roles
from app.core.config import get_settings
from app.db.session import get_db
from app.ml.proy_model import ProyModelUnavailable
from app.models.user import User, UserRole
from app.schemas.proy_experimental import (
    ProyExperimentalEvaluationRead,
    ProyExperimentalEvaluationRequest,
)
from app.services import proy_experimental as service

router = APIRouter(prefix="/proy-experimental", tags=["proy-experimental"])
can_run_experiment = require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.CREDIT)


def require_experimental_demo() -> None:
    settings = get_settings()
    if settings.environment != "staging" or not settings.proy_experimental_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint experimental PROY no habilitado",
        )


@router.post(
    "/evaluations",
    response_model=ProyExperimentalEvaluationRead,
    status_code=status.HTTP_201_CREATED,
)
async def evaluate_client_history(
    payload: ProyExperimentalEvaluationRequest,
    current_user: User = Depends(can_run_experiment),
    _: None = Depends(require_experimental_demo),
    db: AsyncSession = Depends(get_db),
) -> ProyExperimentalEvaluationRead:
    try:
        evaluation = await service.evaluate_client_history(
            db,
            client_id=payload.client_id,
            amount=payload.amount,
            created_by_id=current_user.id,
        )
    except service.ProyClientNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado"
        ) from None
    except ProyModelUnavailable:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Modelo PROY no disponible",
        ) from None
    await db.commit()
    await db.refresh(evaluation)
    return ProyExperimentalEvaluationRead.model_validate(evaluation)
