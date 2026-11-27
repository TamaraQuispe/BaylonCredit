"""Explicit, research-only PROY inference. Not wired to any application route."""

import hashlib
import io
import json
import math
import os
import platform
import stat
from collections.abc import Mapping
from decimal import Decimal
from functools import lru_cache
from importlib import metadata
from pathlib import Path

from app.ml.proy_contract import (
    CONTRACT_VERSION,
    FEATURE_NAMES_PROY,
    FEATURE_SPECS,
    validate_feature_snapshot,
)

MODEL_SHA256 = "f89db794fc657c3c0f858b1392e26474bc15577facd38ac49355b19a6834db45"
SELECTION_SHA256 = "90548dcfc7562cf01a8175df99bd4884eee042c473b11818e7210afdec3d046c"
PROVENANCE_SHA256 = "a738b147775b574a968dfac55dbe5cd07f5f2b39bf57accac78be2e09703d4ee"
PROTOCOL_SHA256 = "b345352ae4c6539de9abfa0c6e40bdff3ec528ef966b95711d2631cdd50e14c0"
MODEL_NAME = "credit_proy_svm_v1.joblib"
META_NAME = "credit_proy_svm_v1_meta.json"
MODEL_VERSION = "credit-proy-svm-v1"
SOURCE_VERSION = "proy-credit-experiment-v1"
RUNTIME = {"python": "3.14.6", "sklearn": "1.9.1", "numpy": "2.5.5", "joblib": "1.6.0"}
COMPATIBILITY_SHA256 = "3daed68193f3cd328949e3b2412646394f1a82b6580bc094665107422924aa30"
_COMMON_RUNTIME = {
    "sklearn": "1.9.1", "joblib": "1.6.0", "scipy": "1.18.1",
    "threadpoolctl": "3.7.0", "python_implementation": "CPython",
}
TESTED_RUNTIMES = (
    {**_COMMON_RUNTIME, "python": "3.14.6", "numpy": "2.5.5",
     "system": "Darwin", "machine": "arm64"},
    {**_COMMON_RUNTIME, "python": "3.12.14", "numpy": "2.5.3",
     "system": "Linux", "machine": "aarch64"},
)
COMPATIBILITY = {
    "status": "experimentally_verified_for_exact_runtime_tuples_only",
    "evidence_sha256": COMPATIBILITY_SHA256,
    "tested_runtimes": list(TESTED_RUNTIMES),
    "production_authorized": False,
}
THRESHOLD = 0.1


class ProyModelUnavailable(RuntimeError):
    """Fail closed: no legacy fallback and no fabricated probability."""


def _typed_equal(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(
            _typed_equal(actual[key], value) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _typed_equal(left, right) for left, right in zip(actual, expected, strict=True)
        )
    return actual == expected


def _read_regular(path: Path) -> bytes:
    # O_NOFOLLOW also protects against replacement by a symlink between checks.
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ProyModelUnavailable(f"Not a regular file: {path.name}")
        return stream.read()


def _validate_runtime() -> None:
    actual = {
        "python": platform.python_version(), "system": platform.system(),
        "machine": platform.machine(), "python_implementation": platform.python_implementation(),
    }
    for name, package in (
        ("sklearn", "scikit-learn"), ("numpy", "numpy"), ("joblib", "joblib"),
        ("scipy", "scipy"), ("threadpoolctl", "threadpoolctl"),
    ):
        actual[name] = metadata.version(package)
    if actual not in TESTED_RUNTIMES:
        raise ProyModelUnavailable(
            f"Runtime compatibility BLOCKED: unverified tuple {actual}. "
            "Only the experimentally tested environments are accepted; no legacy fallback."
        )


@lru_cache(maxsize=1)
def _deserialize(model_bytes: bytes):
    import joblib

    model = joblib.load(io.BytesIO(model_bytes))
    if (
        list(getattr(model, "classes_", [])) != [0, 1]
        or getattr(model, "n_features_in_", None) != 11
        or not callable(getattr(model, "predict_proba", None))
    ):
        raise ProyModelUnavailable("Invalid model classes, feature count or predict_proba")
    return model


def _load(artifact_dir=None):
    try:
        directory = (
            Path(artifact_dir) if artifact_dir is not None else Path(__file__).parent / "artifacts"
        )
        meta = json.loads(_read_regular(directory / META_NAME))
        expected = {
            "artifact_name": MODEL_NAME,
            "artifact_sha256": MODEL_SHA256,
            "model_version": MODEL_VERSION,
            "source_version": SOURCE_VERSION,
            "schema_version": CONTRACT_VERSION,
            "feature_names": list(FEATURE_NAMES_PROY),
            "family": "svm",
            "threshold": THRESHOLD,
            "runtime": RUNTIME,
            "compatibility": COMPATIBILITY,
            "frozen_selection_sha256": SELECTION_SHA256,
            "source_provenance_sha256": PROVENANCE_SHA256,
            "protocol_sha256": PROTOCOL_SHA256,
            "research_only": True,
            "business_approval": False,
            "final_contacted": False,
            "final_test_evaluated": False,
            "stage": "dev_only_selection",
            "public": True,
            "source": "academic/proy-p05",
            "training_domain": {
                "completed_sales_equals_paid_credits": True,
                "requested_ratio_min": 5 / 80,
                "requested_ratio_max": 50 / 80,
                "reference_cap_soles": 80,
                "not_a_business_limit": True,
            },
        }
        if any(not _typed_equal(meta.get(key), value) for key, value in expected.items()):
            raise ProyModelUnavailable("Metadata does not match pinned PROY identity/provenance")
        provenance = meta.get("provenance", {})
        if (
            provenance.get("version") != SOURCE_VERSION
            or provenance.get("runtime") != RUNTIME
            or provenance.get("protocol_sha256") != PROTOCOL_SHA256
            or not _typed_equal(
                provenance.get("authorization"),
                {"stage": "dev_only_selection", "final_contacted": False},
            )
        ):
            raise ProyModelUnavailable("Invalid source provenance")
        model_bytes = _read_regular(directory / MODEL_NAME)
        if hashlib.sha256(model_bytes).hexdigest() != MODEL_SHA256:
            raise ProyModelUnavailable("Artifact SHA256 mismatch before deserialization")
        _validate_runtime()
        return _deserialize(model_bytes)
    except ProyModelUnavailable:
        raise
    except Exception as exc:
        raise ProyModelUnavailable(f"PROY artifact unavailable: {exc}") from exc


def predict_proy(snapshot, artifact_dir=None) -> dict:
    """Only an explicit call can infer; every result still needs a human decision."""
    result = {
        "decision": "REQUIRES_OWNER_REVIEW",
        "reason": "invalid_snapshot",
        "probability": None,
        "threshold": THRESHOLD,
        "predicted": None,
        "family": "svm",
        "model_version": MODEL_VERSION,
        "schema_version": CONTRACT_VERSION,
        "model_called": False,
        "business_approval": False,
        "research_only": True,
        "final_test_evaluated": False,
        "requires_human_decision": True,
    }
    if not isinstance(snapshot, Mapping):
        return result
    # Known debt takes precedence even if another field is missing or malformed.
    for name in ("outstanding", "pending_overdue", "pending_current"):
        raw = snapshot.get(name)
        if type(raw) not in (int, float, Decimal):
            continue
        try:
            known_debt = math.isfinite(raw) and raw > 0
        except (ValueError, OverflowError):
            known_debt = False
        if known_debt:
            return {**result, "decision": "BLOCKED_PENDING_BALANCE", "reason": "pending_debt"}
    if set(snapshot) != set(FEATURE_NAMES_PROY):
        return result
    if any(type(value) not in (int, float, Decimal) for value in snapshot.values()):
        return result
    try:
        for spec in FEATURE_SPECS:
            raw = snapshot[spec.name]
            if not math.isfinite(raw) or raw < 0 or (spec.integer and raw != int(raw)):
                return result
            if spec.integer and raw > 2**53:
                return result
            if raw != 0 and float(raw) == 0:
                return result
        if validate_feature_snapshot(snapshot):
            return result
        values = {name: float(snapshot[name]) for name in FEATURE_NAMES_PROY}
    except (ValueError, TypeError, OverflowError):
        return result
    paid = snapshot["paid_credits"]
    if paid <= 0:
        return {**result, "reason": "no_paid_history"}
    if (
        snapshot["paid_late"] > paid
        or not 0 < values["requested_ratio"] <= 1
        or not math.isclose(
            values["punctuality_rate"],
            float((Decimal(str(paid)) - Decimal(str(snapshot["paid_late"]))) / Decimal(str(paid))),
            rel_tol=0, abs_tol=1e-8,
        )
        or snapshot["overdue_rate"] != 0
        or snapshot["utilization"] != 0
    ):
        return result
    # Live direct credits need not equal sales; never project them into this training domain.
    if snapshot["completed_sales"] != paid or not 5 / 80 <= snapshot["requested_ratio"] <= 50 / 80:
        return {**result, "reason": "unsupported_training_domain"}
    model = _load(artifact_dir)
    try:
        import numpy as np

        output = np.asarray(
            model.predict_proba([[values[name] for name in FEATURE_NAMES_PROY]]), dtype=float
        )
        if (
            output.shape != (1, 2)
            or not np.isfinite(output).all()
            or (output < 0).any()
            or (output > 1).any()
            or not math.isclose(float(output.sum()), 1.0, rel_tol=0, abs_tol=1e-8)
        ):
            raise ProyModelUnavailable("Invalid predict_proba output")
        probability = float(output[0, 1])
    except ProyModelUnavailable:
        raise
    except Exception as exc:
        raise ProyModelUnavailable(f"PROY inference unavailable: {exc}") from exc
    predicted = int(probability >= THRESHOLD)
    return {
        **result,
        "decision": "MODEL_REVIEW_CANDIDATE" if predicted else "BELOW_REVIEW_THRESHOLD",
        "reason": "human_decision_required",
        "probability": probability,
        "predicted": predicted,
        "model_called": True,
    }
