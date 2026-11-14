"""Read-only model demonstrations on pre-generated fictional cases, staging only."""

import hashlib
import json
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.ml.features import FEATURE_NAMES
from app.models.user import User

router = APIRouter(prefix="/academic-ml", tags=["academic-laboratory"])
DISCLAIMER = (
    "Datos sintéticos. Resultado experimental no calibrado para clientes reales. "
    "Esta consulta no crea créditos, no modifica el score ni autoriza fiados."
)


@lru_cache(maxsize=1)
def load_lab(directory: str):
    root = Path(directory)
    report = json.loads((root / "experiment_v2_report.json").read_text())
    cases = json.loads((root / "academic_lab_cases.json").read_text())
    artifact = root / "academic_model_v2.joblib"
    if report["data_source"] != "synthetic" or cases["data_source"] != "synthetic":
        raise ValueError("Only explicitly synthetic artifacts are allowed")
    if report["feature_names"] != FEATURE_NAMES:
        raise ValueError("Academic feature contract mismatch")
    if hashlib.sha256(artifact.read_bytes()).hexdigest() != report["artifact_sha256"]:
        raise ValueError("Academic artifact integrity check failed")
    # Only trusted deployment artifacts, never uploads or arbitrary client paths.
    model = joblib.load(artifact)
    if list(model.classes_) != [0, 1]:
        raise ValueError("Academic labels must be 0 and 1")
    return report, {item["id"]: item for item in cases["cases"]}, model


def laboratory():
    settings = get_settings()
    if not settings.academic_ml_lab_enabled or settings.environment != "staging":
        raise HTTPException(status_code=404, detail="Laboratorio académico no habilitado")
    try:
        return load_lab(settings.academic_ml_lab_dir)
    except (OSError, ValueError, KeyError, TypeError):
        raise HTTPException(status_code=503, detail="Laboratorio académico no disponible") from None


@router.get("/summary")
def summary(_: User = Depends(get_current_user), lab=Depends(laboratory)):
    report, _cases, _model = lab
    return {
        "version": report["version"],
        "data_source": "synthetic",
        "selected_model": report["chosen"]["model"],
        "threshold": report["chosen"]["threshold"],
        "training_rows": report["training_rows"],
        "validation_rows": report["validation_rows"],
        "final_labeled_rows": report["final_labeled_rows"],
        "final_clients": report["fresh_final_checks"]["clients"],
        "comparison": report["comparison_on_same_fresh_cohort"],
        "disclaimer": DISCLAIMER,
    }


@router.get("/cases")
def list_cases(_: User = Depends(get_current_user), lab=Depends(laboratory)):
    _report, cases, _model = lab
    return [
        {key: item[key] for key in ("id", "scenario", "requested_amount", "due_date")}
        for item in cases.values()
    ]


@router.post("/evaluate/{case_id}")
def evaluate(case_id: str, _: User = Depends(get_current_user), lab=Depends(laboratory)):
    report, cases, model = lab
    if case_id not in cases:
        raise HTTPException(status_code=404, detail="Caso sintético no encontrado")
    case = cases[case_id]
    vector = np.asarray([[case["features"][name] for name in FEATURE_NAMES]], dtype=float)
    probability = float(model.predict_proba(vector)[0][1])
    threshold = report["chosen"]["threshold"]
    return {
        "case_id": case_id,
        "scenario": case["scenario"],
        "data_source": "synthetic",
        "version": report["version"],
        "estimated_late_probability": probability,
        "threshold": threshold,
        "predicted_late_payment": int(probability >= threshold),
        "actual_late_payment": case["actual_late_payment"],
        "features": case["features"],
        "disclaimer": DISCLAIMER,
    }
