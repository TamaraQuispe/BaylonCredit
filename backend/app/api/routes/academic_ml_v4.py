"""Authenticated staging-only V4 research, independent of the V2 laboratory."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.services import academic_lab_v4 as lab

router = APIRouter(
    prefix="/academic-ml/v4",
    tags=["academic-laboratory-v4"],
    dependencies=[Depends(get_current_user)],
)


def laboratory_directory():
    settings = get_settings()
    if not settings.academic_ml_v4_enabled or settings.environment != "staging":
        raise HTTPException(status_code=404, detail="Laboratorio academico V4 no habilitado")
    return settings.academic_ml_v4_dir


def consult(operation, *args):
    try:
        return operation(*args)
    except Exception:
        # Pickle/runtime/schema failures must never expose paths or partial output.
        raise HTTPException(
            status_code=503, detail="Laboratorio academico V4 no disponible"
        ) from None


@router.get("/summary")
def summary(directory: str = Depends(laboratory_directory)):
    return consult(lab.load_bundle, directory)[0]


@router.get("/cases")
def cases(directory: str = Depends(laboratory_directory)):
    consult(lab.load_bundle, directory)
    return [lab.CASE]


@router.post("/evaluate/{case_id}")
async def evaluate(case_id: str, request: Request, directory: str = Depends(laboratory_directory)):
    if case_id != lab.CASE["id"]:
        raise HTTPException(status_code=404, detail="Caso sintetico no encontrado")
    if await request.body() or request.query_params:
        raise HTTPException(status_code=422, detail="Esta consulta no acepta entradas")
    bundle = await run_in_threadpool(consult, lab.load_bundle, directory)
    return await run_in_threadpool(consult, lab.evaluate, bundle)
