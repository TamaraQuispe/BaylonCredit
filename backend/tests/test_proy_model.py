"""Unit contracts plus an explicit opt-in inference test of the frozen SVM."""

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.ml import proy_model as proy


def snapshot(**changes):
    values = dict(
        zip(proy.FEATURE_NAMES_PROY, [12, 12, 2, 0, 0, 0, 0, 0.25, 120, 10 / 12, 0], strict=True)
    )
    return {**values, **changes}


class FakeModel:
    classes_ = [0, 1]
    n_features_in_ = 11

    def __init__(self, output=None):
        self.output = output if output is not None else [[0.8, 0.2]]
        self.inputs = []

    def predict_proba(self, values):
        self.inputs.append(values)
        return self.output


@pytest.fixture
def fake_artifacts(tmp_path, monkeypatch):
    data = b"tiny trusted fake joblib, never unpickled"
    source = Path(proy.__file__).parent / "artifacts" / proy.META_NAME
    meta = json.loads(source.read_text())
    digest = hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(proy, "MODEL_SHA256", digest)
    meta["artifact_sha256"] = digest
    (tmp_path / proy.MODEL_NAME).write_bytes(data)
    (tmp_path / proy.META_NAME).write_text(json.dumps(meta))
    monkeypatch.setattr(proy, "_validate_runtime", lambda: None)
    model = FakeModel()
    calls = []

    def load(stream):
        calls.append(stream.read())
        return model

    monkeypatch.setitem(sys.modules, "joblib", SimpleNamespace(load=load))
    proy._deserialize.cache_clear()
    yield tmp_path, model, calls
    proy._deserialize.cache_clear()


@pytest.mark.parametrize(
    "changes,decision,reason",
    [
        ({"outstanding": 0.01, "paid_credits": None}, "BLOCKED_PENDING_BALANCE", "pending_debt"),
        ({"pending_current": 1}, "BLOCKED_PENDING_BALANCE", "pending_debt"),
        ({"pending_overdue": 1}, "BLOCKED_PENDING_BALANCE", "pending_debt"),
        ({"paid_credits": 0, "paid_late": 0}, "REQUIRES_OWNER_REVIEW", "no_paid_history"),
        ({"paid_credits": None}, "REQUIRES_OWNER_REVIEW", "invalid_snapshot"),
        ({"completed_sales": 11}, "REQUIRES_OWNER_REVIEW", "unsupported_training_domain"),
        ({"requested_ratio": 0.7}, "REQUIRES_OWNER_REVIEW", "unsupported_training_domain"),
        ({"requested_ratio": 0.01}, "REQUIRES_OWNER_REVIEW", "unsupported_training_domain"),
    ],
)
def test_gates_before_loader(monkeypatch, changes, decision, reason):
    monkeypatch.setattr(proy, "_load", lambda *_: pytest.fail("loader called"))
    result = proy.predict_proy(snapshot(**changes))
    assert (result["decision"], result["reason"]) == (decision, reason)
    assert result["probability"] is None and not result["model_called"]


@pytest.mark.parametrize(
    "changes",
    [
        {"tenure_days": True},
        {"paid_late": "2"},
        {"paid_late": 1.5},
        {"outstanding": -1},
        {"requested_ratio": 0},
        {"requested_ratio": 1.1},
        {"tenure_days": float("nan")},
        {"tenure_days": float("inf")},
        {"paid_late": 13},
        {"punctuality_rate": 0.4},
        {"utilization": 0.1},
        {"overdue_rate": 0.1},
        {"tenure_days": 10**1000},
        {"tenure_days": Decimal("1e-999")},
        {"outstanding": Decimal("-1e-999")},
        {"utilization": Decimal("1e-999")},
        {"overdue_rate": Decimal("1e-999")},
        {"completed_sales": 9007199254740993, "paid_credits": 9007199254740992,
         "paid_late": 0, "punctuality_rate": 1},
    ],
)
def test_invalid_snapshots_never_load(monkeypatch, changes):
    monkeypatch.setattr(proy, "_load", lambda *_: pytest.fail("loader called"))
    assert proy.predict_proy(snapshot(**changes))["reason"] == "invalid_snapshot"


@pytest.mark.parametrize("value", [None, [], {}, {"extra": 1}])
def test_unknown_snapshot(value):
    assert proy.predict_proy(value)["reason"] == "invalid_snapshot"


@pytest.mark.parametrize(
    "probability,decision", [(0.1, "MODEL_REVIEW_CANDIDATE"), (0.09, "BELOW_REVIEW_THRESHOLD")]
)
def test_explicit_prediction_and_cache(fake_artifacts, probability, decision):
    directory, model, calls = fake_artifacts
    model.output = [[1 - probability, probability]]
    for _ in range(2):
        result = proy.predict_proy(snapshot(), directory)
        assert result["decision"] == decision
        assert result["probability"] == probability
        assert result["predicted"] == int(probability >= 0.1)
        assert result["model_called"] and result["requires_human_decision"]
        assert not result["business_approval"] and not result["final_test_evaluated"]
        assert result["research_only"]
    assert len(calls) == 1
    assert model.inputs == [[list(snapshot().values())]] * 2


@pytest.mark.parametrize("warm_cache", [False, True])
def test_corruption_checked_even_after_cache(fake_artifacts, warm_cache):
    directory, _, calls = fake_artifacts
    if warm_cache:
        proy.predict_proy(snapshot(), directory)
    (directory / proy.MODEL_NAME).write_bytes(b"corrupt")
    with pytest.raises(proy.ProyModelUnavailable, match="SHA256"):
        proy.predict_proy(snapshot(), directory)
    assert len(calls) == int(warm_cache)


@pytest.mark.parametrize(
    "field,value",
    [
        ("artifact_name", "../other.joblib"),
        ("artifact_sha256", "0" * 64),
        ("model_version", "other"),
        ("runtime", {}),
        ("compatibility", {}),
        ("feature_names", []),
        ("business_approval", True),
        ("research_only", False),
    ],
)
def test_metadata_pins(fake_artifacts, field, value):
    directory, _, calls = fake_artifacts
    path = directory / proy.META_NAME
    meta = json.loads(path.read_text())
    meta[field] = value
    path.write_text(json.dumps(meta))
    with pytest.raises(proy.ProyModelUnavailable, match="Metadata"):
        proy.predict_proy(snapshot(), directory)
    assert calls == []


@pytest.mark.parametrize("parent,field,value", [
    ("compatibility", "production_authorized", 0),
    ("training_domain", "completed_sales_equals_paid_credits", 1),
    ("training_domain", "reference_cap_soles", 80.0),
    ("provenance", "authorization", {"stage": "dev_only_selection", "final_contacted": 0}),
])
def test_nested_metadata_types_are_not_coerced(fake_artifacts, parent, field, value):
    directory, _, calls = fake_artifacts
    path = directory / proy.META_NAME
    meta = json.loads(path.read_text())
    meta[parent][field] = value
    path.write_text(json.dumps(meta))
    with pytest.raises(proy.ProyModelUnavailable):
        proy.predict_proy(snapshot(), directory)
    assert not calls


@pytest.mark.parametrize("name", [proy.MODEL_NAME, proy.META_NAME])
def test_symlink_rejected(fake_artifacts, name):
    directory, _, calls = fake_artifacts
    path = directory / name
    target = directory / "target"
    path.rename(target)
    path.symlink_to(target)
    with pytest.raises(proy.ProyModelUnavailable):
        proy.predict_proy(snapshot(), directory)
    assert calls == []


def test_runtime_rechecked_before_deserialization(fake_artifacts, monkeypatch):
    directory, _, calls = fake_artifacts
    # Restore the actual validator, while simulating the exact recorded versions.
    spec = importlib.util.spec_from_file_location("proy_runtime_test", proy.__file__)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(proy, "_validate_runtime", module._validate_runtime)
    monkeypatch.setattr(module.platform, "python_version", lambda: "3.13.0")
    monkeypatch.setattr(module.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(module.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(module.platform, "python_implementation", lambda: "CPython")
    monkeypatch.setattr(
        module.metadata,
        "version",
        lambda name: {"scikit-learn": "1.9.1", "numpy": "2.5.5", "joblib": "1.6.0",
                      "scipy": "1.18.1", "threadpoolctl": "3.7.0"}[name],
    )
    with pytest.raises(proy.ProyModelUnavailable, match="compatibility BLOCKED"):
        proy.predict_proy(snapshot(), directory)
    assert calls == []
    monkeypatch.setattr(module.platform, "python_version", lambda: "3.14.6")
    proy.predict_proy(snapshot(), directory)
    monkeypatch.setattr(module.platform, "python_version", lambda: "3.13.0")
    with pytest.raises(proy.ProyModelUnavailable, match="compatibility BLOCKED"):
        proy.predict_proy(snapshot(), directory)
    assert len(calls) == 1


@pytest.mark.parametrize("runtime", proy.TESTED_RUNTIMES)
def test_only_exact_verified_runtime_tuples_are_allowed(monkeypatch, runtime):
    monkeypatch.setattr(proy.platform, "python_version", lambda: runtime["python"])
    monkeypatch.setattr(proy.platform, "system", lambda: runtime["system"])
    monkeypatch.setattr(proy.platform, "machine", lambda: runtime["machine"])
    monkeypatch.setattr(
        proy.platform, "python_implementation", lambda: runtime["python_implementation"]
    )
    versions = {"scikit-learn": runtime["sklearn"], **{
        name: runtime[name] for name in ("numpy", "joblib", "scipy", "threadpoolctl")}}
    monkeypatch.setattr(proy.metadata, "version", versions.__getitem__)
    proy._validate_runtime()
    for key in ("scipy", "numpy", "threadpoolctl", "scikit-learn", "joblib"):
        current = versions[key]
        versions[key] = "0.0.0"
        with pytest.raises(proy.ProyModelUnavailable, match="compatibility BLOCKED"):
            proy._validate_runtime()
        versions[key] = current
    monkeypatch.setattr(proy.platform, "machine", lambda: "x86_64")
    with pytest.raises(proy.ProyModelUnavailable, match="compatibility BLOCKED"):
        proy._validate_runtime()


@pytest.mark.parametrize(
    "output",
    [
        [[float("nan"), 0.1]],
        [[float("inf"), 0]],
        [[-0.1, 1.1]],
        [[0.2, 0.2]],
        [[1]],
        [[0.8, 0.2], [0.8, 0.2]],
        [0.8, 0.2],
        [["bad", 0.2]],
    ],
)
def test_malformed_output(fake_artifacts, output):
    directory, model, _ = fake_artifacts
    model.output = output
    with pytest.raises(proy.ProyModelUnavailable):
        proy.predict_proy(snapshot(), directory)


@pytest.mark.parametrize(
    "field,value", [("classes_", [1, 0]), ("n_features_in_", 10), ("predict_proba", None)]
)
def test_model_interface(fake_artifacts, field, value):
    directory, model, _ = fake_artifacts
    setattr(model, field, value)
    with pytest.raises(proy.ProyModelUnavailable, match="Invalid model"):
        proy.predict_proy(snapshot(), directory)


def test_no_legacy_fallback(fake_artifacts, monkeypatch):
    from app.ml import model as legacy

    monkeypatch.setattr(
        legacy, "predict_default_probability", lambda *_: pytest.fail("legacy inference")
    )
    directory, model, _ = fake_artifacts
    proy.predict_proy(snapshot(), directory)
    model.output = [[0.1, 0.1]]
    with pytest.raises(proy.ProyModelUnavailable):
        proy.predict_proy(snapshot(), directory)


def test_mixed_decimal_history_is_valid_without_silent_projection(fake_artifacts):
    directory, _, _ = fake_artifacts
    result = proy.predict_proy(snapshot(paid_credits=Decimal("12"), paid_late=2.0), directory)
    assert result["model_called"] is True


def test_generator_cli_and_source_unchanged(tmp_path):
    root = Path(__file__).resolve().parents[2]
    source = root / "entregables/PROY_Grupo2/materiales/experiment/p0-05"
    if not source.is_dir():
        pytest.skip("Academic source not mounted; run with read-only source mount")
    before = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source.iterdir()
        if path.is_file()
    }
    command = [
        sys.executable,
        str(root / "deploy/prepare-proy-svm-artifact.py"),
        "--source",
        str(source),
        "--artifact-dir",
        str(tmp_path),
        "--compatibility-record",
        str(root / "docs/PROY_SVM_COMPATIBILIDAD.json"),
    ]
    subprocess.run(command, check=True, capture_output=True)
    assert (
        hashlib.sha256((tmp_path / proy.MODEL_NAME).read_bytes()).hexdigest() == proy.MODEL_SHA256
    )
    expected_meta = Path(proy.__file__).parent / "artifacts" / proy.META_NAME
    generated_meta = json.loads((tmp_path / proy.META_NAME).read_text())
    assert generated_meta == json.loads(expected_meta.read_text())
    assert subprocess.run(command, capture_output=True).returncode != 0
    after = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source.iterdir()
        if path.is_file()
    }
    assert before == after


@pytest.mark.skipif(os.environ.get("PROY_REAL_MODEL_TEST") != "1",
                    reason="Explicit trusted-artifact inference test; no fitting or FINAL")
def test_real_loader_on_verified_runtime(monkeypatch):
    from app.ml import model as legacy

    monkeypatch.setattr(
        legacy, "predict_default_probability", lambda *_: pytest.fail("legacy call")
    )
    source = Path(proy.__file__).parent / "artifacts" / proy.MODEL_NAME
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    proy._validate_runtime()
    proy._deserialize.cache_clear()
    features = snapshot(completed_sales=6, paid_credits=6, paid_late=1,
                        tenure_days=180, punctuality_rate=5 / 6)
    result = proy.predict_proy(features)
    assert result["probability"] == pytest.approx(0.13741099608146004, rel=0, abs=1e-12)
    assert result["predicted"] == 1 and result["threshold"] == 0.1
    assert result["model_version"] == proy.MODEL_VERSION
    assert result["model_called"] and result["requires_human_decision"]
    assert result["research_only"] and not result["business_approval"]
    assert not result["final_test_evaluated"]
    monkeypatch.setattr(proy, "_load", lambda *_: pytest.fail("Gated case loaded artifact"))
    for changed, decision in (
        ({"outstanding": 0.01}, "BLOCKED_PENDING_BALANCE"),
        ({"paid_credits": 0}, "REQUIRES_OWNER_REVIEW"),
        ({"completed_sales": 0}, "REQUIRES_OWNER_REVIEW"),
    ):
        gated = proy.predict_proy({**features, **changed})
        assert gated["decision"] == decision and not gated["model_called"]
        assert gated["probability"] is None
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before == proy.MODEL_SHA256
    proy._deserialize.cache_clear()
