"""Self-contained web fixtures, never generated cohorts or final model fitting."""

import copy
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import joblib
import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from app.api.dependencies import get_current_user
from app.api.routes import academic_ml_v6 as routes
from app.core.config import Settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.ml.features import FEATURE_NAMES
from app.models.user import UserRole
from app.services import academic_lab_v6 as lab

BASE = "/api/v1/academic-ml/v6"
ENDPOINTS = [("GET", "/summary"), ("GET", "/cases")] + [
    ("POST", "/evaluate/" + case["id"]) for case in lab.CASES
]


def forbidden(*args, **kwargs):
    raise AssertionError("Unexpected IO, inference, training or business side effect")


def encode(value):
    return json.dumps(value, allow_nan=False).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    installed_runtime_versions = lab.runtime_versions
    classifier = DummyClassifier(strategy="prior")
    model = Pipeline([("imputer", SimpleImputer()), ("classifier", classifier)])
    model.fit(np.zeros((4, 11)), [0, 0, 0, 1])
    stream = io.BytesIO()
    joblib.dump(model, stream)
    raw = {
        "accuracy": 0.25, "balanced_accuracy": 0.5, "precision": 0.25,
        "recall": 1.0, "f1": 0.4, "f2": 0.625, "roc_auc": 0.5,
        "brier": 0.1875, "confusion_matrix": [[0, 3], [0, 1]],
    }
    policy = {
        "metrics": {key: value for key, value in raw.items() if key not in (
            "balanced_accuracy", "roc_auc", "brier"
        )},
        "reviews": 4, "reviews_known": 3, "reviews_unknown": 1,
        "daily_max": 4, "capacity_respected": True,
        "daily": [{"private_queue": "must not be exposed"}],
    }
    frozen = {
        "version": lab.VERSION, "feature_names": list(lab.FEATURE_NAMES),
        "research_only": True,
        "global_winner": {
            "family": "tree", "params": {"family": "tree"}, "threshold": 0.2,
            "review_policy": copy.deepcopy(policy),
        },
    }
    provenance = {
        "runtime": {**lab.RUNTIME, "threadpoolctl": "3.7.0"},
        "source_anchors": {
            "evaluable": 45, "late": 8, "partial_payment_annotations": 10,
            "partial_payment_denominator": 48,
            "source_quality": "Recall and partial notebook review, approximate "
                           "and not independently audited",
            "private_verbose_source": "must not be exposed",
        },
    }
    report = {
        "version": lab.VERSION, "origen": "simulado", "research_only": True,
        "business_approval": False, "feature_names": list(lab.FEATURE_NAMES),
        "selection": copy.deepcopy(frozen), "provenance": copy.deepcopy(provenance),
        "development": {
            "study_rows": 545, "known_rows": 541, "unknown_rows": 4,
            "audits": [{"clients": 12}, {"clients": 12}],
        },
        "final": {"known_rows": 276, "study_rows": 280, "audit": {"clients": 12}},
        "models": {family: {
            "threshold": 0.2, "final": copy.deepcopy(raw),
            "review_policy": {"final": copy.deepcopy(policy)},
        } for family in lab.LABELS},
        "artifact_sha256": {"selected_model.joblib": digest(stream.getvalue())},
        "limits": ["Synthetic alternative histories, not real validation"],
    }
    features = dict.fromkeys(lab.FEATURE_NAMES, 0)
    features.update(
        requested_ratio=0.25, tenure_days=None, outstanding=0,
        completed_sales=6, paid_credits=6, paid_late=1, punctuality_rate=5 / 6,
    )
    data = {
        "pending_v6_report.json": report, "frozen_selection.json": frozen,
        "selected_model.joblib": stream.getvalue(),
        "illustrative_input.json": {"features": features}, "provenance.json": provenance,
    }

    def publish():
        contents = {name: value if isinstance(value, bytes) else encode(value)
                    for name, value in data.items()}
        for name, value in contents.items():
            (tmp_path / name).write_bytes(value)
        (tmp_path / "web_manifest.json").write_bytes(encode({
            "version": lab.VERSION,
            "files": {name: digest(value) for name, value in contents.items()},
        }))

    publish()
    monkeypatch.setattr(lab, "runtime_versions", lambda: dict(lab.RUNTIME))
    monkeypatch.setattr(routes, "get_settings", lambda: SimpleNamespace(
        academic_ml_v6_enabled=True, environment="staging", academic_ml_v6_dir=str(tmp_path)
    ))
    lab.validated_bundle.cache_clear()
    lab.load_model.cache_clear()
    yield SimpleNamespace(
        root=tmp_path, data=data, publish=publish, model=model,
        runtime_versions=installed_runtime_versions,
    )
    lab.validated_bundle.cache_clear()
    lab.load_model.cache_clear()


@pytest.fixture
def authenticated():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="operator")
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as value:
        yield value


@pytest.fixture
def no_deserialization(monkeypatch):
    load = Mock(side_effect=forbidden)
    monkeypatch.setattr(joblib, "load", load)
    yield
    load.assert_not_called()


def test_settings_defaults_and_feature_contract():
    settings = Settings(_env_file=None)
    assert settings.academic_ml_v6_enabled is False
    assert settings.academic_ml_v6_dir == "/app/academic-v6"
    assert lab.FEATURE_NAMES == FEATURE_NAMES


@pytest.mark.parametrize("environment", ["development", "test", "production"])
def test_settings_restrict_enabled_to_staging(environment):
    with pytest.raises(ValueError, match="restricted to staging"):
        Settings(_env_file=None, environment=environment, academic_ml_v6_enabled=True)


def test_settings_staging_still_requires_jwt_secret():
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(_env_file=None, environment="staging", academic_ml_v6_enabled=True)
    assert Settings(_env_file=None, environment="staging", academic_ml_v6_enabled=True,
                    jwt_secret_key="configured-staging-secret").academic_ml_v6_enabled


@pytest.mark.parametrize(("method", "path"), ENDPOINTS)
async def test_http_requires_jwt_before_files(client, monkeypatch, method, path):
    monkeypatch.setattr(lab, "load_bundle", forbidden)
    assert (await client.request(method, BASE + path)).status_code == 401
    assert (await client.request(method, BASE + path,
                                 headers={"Authorization": "Bearer invalid"})).status_code == 401


@pytest.mark.parametrize("role", list(UserRole))
async def test_http_real_jwt_all_existing_roles(bundle, client, role, monkeypatch):
    user_id = uuid4()

    class ReadOnlyAuthDB:
        async def get(self, model, key):
            assert key == user_id
            return SimpleNamespace(id=user_id, role=role, is_active=True)

    async def auth_db():
        yield ReadOnlyAuthDB()

    # Do not override get_current_user: exercise the existing JWT guard.
    app.dependency_overrides[get_db] = auth_db
    token, _ = create_access_token(user_id, role)
    try:
        for method, path in ENDPOINTS:
            response = await client.request(method, BASE + path,
                                            headers={"Authorization": f"Bearer {token}"})
            assert response.status_code == 200, response.text
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.parametrize(("enabled", "environment"), [
    (False, "staging"), (False, "production"), (True, "production"),
    (True, "development"), (True, "test"),
])
async def test_flags_404_before_any_files(authenticated, client, monkeypatch, enabled, environment):
    monkeypatch.setattr(routes, "get_settings", lambda: SimpleNamespace(
        academic_ml_v6_enabled=enabled, environment=environment
    ))
    monkeypatch.setattr(lab, "load_bundle", forbidden)
    for method, path in ENDPOINTS:
        assert (await client.request(method, BASE + path)).status_code == 404


async def test_summary_cases_contract_without_model_load(
    bundle, authenticated, client, no_deserialization
):
    response = await client.get(BASE + "/summary")
    assert response.status_code == 200
    summary = response.json()
    assert set(summary) == {
        "version", "data_source", "research_only", "business_approval", "selected_model",
        "threshold", "development_rows", "development_unknown", "development_clients",
        "final_labeled_rows", "final_unknown", "final_clients", "selection", "comparison",
        "source", "limitations", "disclaimer", "revision_id", "display_name",
        "training_scope", "routing",
    }
    assert summary["version"] == lab.VERSION and summary["selected_model"] == "tree"
    assert summary["revision_id"] == "v6-historical"
    assert summary["display_name"] == "V6 historico"
    assert summary["routing"] is None
    assert summary["training_scope"] == "historical_granted_known"
    assert summary["data_source"] == "synthetic" and summary["research_only"] is True
    assert summary["business_approval"] is False and summary["threshold"] == 0.2
    assert [summary[key] for key in (
        "development_rows", "development_unknown", "development_clients",
        "final_labeled_rows", "final_unknown", "final_clients"
    )] == [545, 4, 24, 276, 4, 12]
    assert summary["selection"] == {
        "metric": lab.SELECTION_METRIC, "oof_f2": 0.625,
    }
    assert summary["source"] == {
        "evaluable": 45, "late": 8, "partial_annotations": 10,
        "partial_denominator": 48,
        "quality": "Recall and partial notebook review, approximate and not independently audited",
    }
    for item in summary["comparison"]:
        assert set(item) == {"family", "label", "raw", "policy"}
        assert set(item["policy"]) == {
            "metrics", "reviews", "reviews_known", "reviews_unknown", "daily_max",
            "capacity_respected",
        }
        assert set(item["raw"]) == set(item["policy"]["metrics"]) == {
            "accuracy", "balanced_accuracy", "precision", "recall", "f1", "f2",
            "roc_auc", "brier", "confusion_matrix",
        }
        assert item["policy"]["metrics"]["roc_auc"] is None
        assert item["policy"]["metrics"]["balanced_accuracy"] is None
        assert item["policy"]["metrics"]["brier"] is None
    assert "private" not in response.text and "daily\":" not in response.text
    assert (await client.get(BASE + "/cases")).json() == [{
        "id": "illustrative-v6", "scenario": "Ejemplo nuevo sin etiqueta",
        "requested_amount": "20.00",
    }, {
        "id": "pending-balance-v6", "scenario": "Ejemplo ficticio con saldo pendiente",
        "requested_amount": "20.00",
    }, {
        "id": "no-history-v6", "scenario": "Ejemplo ficticio sin creditos pagados",
        "requested_amount": "20.00",
    }]


async def test_evaluate_contract_and_cache_no_fit(bundle, authenticated, client, monkeypatch):
    original = joblib.load
    loads = []

    def load(stream):
        assert isinstance(stream, io.BytesIO)
        loads.append(stream.getvalue())
        return original(stream)

    monkeypatch.setattr(joblib, "load", load)
    monkeypatch.setattr(Pipeline, "fit", forbidden)
    monkeypatch.setattr(DummyClassifier, "fit", forbidden)
    for _ in range(2):
        response = await client.post(BASE + "/evaluate/illustrative-v6")
        assert response.status_code == 200, response.text
        result = response.json()
        assert set(result) == {
            "case_id", "scenario", "data_source", "version", "research_only", "business_approval",
            "estimated_late_probability", "threshold", "predicted_late_payment",
            "actual_late_payment", "features", "review_policy_applied", "disclaimer",
            "decision", "reason", "requires_manual_review", "model_called",
        }
        assert result["case_id"] == "illustrative-v6"
        assert result["scenario"] == lab.CASE["scenario"]
        assert result["estimated_late_probability"] == 0.25
        assert result["threshold"] == 0.2 and result["predicted_late_payment"] == 1
        assert result["decision"] == "model_review_candidate"
        assert result["model_called"] is True and result["requires_manual_review"] is True
        assert result["reason"].isascii() and "revision humana" in result["reason"]
        assert result["actual_late_payment"] is None and result["review_policy_applied"] is False
        assert result["research_only"] is True and result["business_approval"] is False
        assert result["features"]["tenure_days"] is None
        assert list(result["features"]) == lab.FEATURE_NAMES
        assert "clientes reales" in result["disclaimer"]
        assert "cola de revision" in result["disclaimer"]
    assert len(loads) == 1
    assert lab.validated_bundle.cache_info().hits == 1


@pytest.mark.parametrize(
    "case_id", ["unknown", "FINAL-L1", "illustrative-v4", "selected_model.joblib"]
)
async def test_unknown_case_before_io(bundle, authenticated, client, monkeypatch, case_id):
    monkeypatch.setattr(lab, "load_bundle", forbidden)
    assert (await client.post(BASE + "/evaluate/" + case_id)).status_code == 404


@pytest.mark.parametrize("case_id", [case["id"] for case in lab.CASES])
@pytest.mark.parametrize("kwargs", [
    {"json": {}}, {"json": {"features": {}}}, {"content": b"not-json"},
    {"params": {"path": "/tmp/arbitrary"}},
    {"files": {"upload": ("input.json", b"{}")}},
])
async def test_arbitrary_inputs_rejected_before_io(
    bundle, authenticated, client, monkeypatch, kwargs, case_id
):
    monkeypatch.setattr(lab, "load_bundle", forbidden)
    assert (await client.post(BASE + "/evaluate/" + case_id, **kwargs)).status_code == 422


@pytest.mark.parametrize(("case_id", "decision"), [
    ("pending-balance-v6", "blocked_pending_balance"),
    ("no-history-v6", "requires_owner_review"),
])
async def test_fixed_gated_cases_never_load_or_fit(
    bundle, authenticated, client, monkeypatch, no_deserialization, case_id, decision
):
    with monkeypatch.context() as patch:
        load = Mock(side_effect=forbidden)
        patch.setattr(lab, "load_model", load)
        patch.setattr(Pipeline, "fit", forbidden)
        patch.setattr(Pipeline, "predict_proba", forbidden)
        patch.setattr(DummyClassifier, "fit", forbidden)
        response = await client.post(BASE + "/evaluate/" + case_id)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["case_id"] == case_id
        assert result["decision"] == decision
        assert result["model_called"] is False
        assert type(result["requires_manual_review"]) is bool
        if decision == "requires_owner_review":
            assert result["requires_manual_review"] is True
        assert result["reason"].isascii() and result["reason"]
        assert result["review_policy_applied"] is False
        assert result["business_approval"] is False
        for key in ("estimated_late_probability", "threshold", "predicted_late_payment",
                    "actual_late_payment"):
            assert result[key] is None
        expected = dict(bundle.data["illustrative_input.json"]["features"])
        if case_id == "pending-balance-v6":
            expected.update(pending_current=1, outstanding=20, utilization=0.25)
        else:
            expected.update(completed_sales=0, paid_credits=0, paid_late=0,
                            punctuality_rate=0, tenure_days=0)
        assert result["features"] == expected
        load.assert_not_called()


@pytest.mark.parametrize(("changes", "decision"), [
    *[({name: 1}, "blocked_pending_balance") for name in (
        "pending_overdue", "pending_current", "outstanding", "utilization", "overdue_rate"
    )],
    *[({name: None}, "requires_owner_review") for name in (
        "pending_overdue", "pending_current", "outstanding", "utilization", "overdue_rate",
        "paid_credits",
    )],
    ({"paid_credits": 0, "paid_late": 0}, "requires_owner_review"),
    ({"pending_current": 1, "paid_credits": 0, "paid_late": 0}, "blocked_pending_balance"),
    ({"outstanding": 20, "pending_overdue": None}, "blocked_pending_balance"),
])
async def test_gate_before_load_for_trusted_nulls_debt_and_no_history(
    bundle, authenticated, client, monkeypatch, no_deserialization, changes, decision
):
    bundle.data["illustrative_input.json"]["features"].update(changes)
    bundle.publish()
    with monkeypatch.context() as patch:
        load = Mock(side_effect=forbidden)
        patch.setattr(lab, "load_model", load)
        response = await client.post(BASE + "/evaluate/illustrative-v6")
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["decision"] == decision
        assert result["model_called"] is False
        assert type(result["requires_manual_review"]) is bool
        if decision == "requires_owner_review":
            assert result["requires_manual_review"] is True
        assert result["reason"].isascii() and result["reason"]
        for key in ("estimated_late_probability", "threshold", "predicted_late_payment",
                    "actual_late_payment"):
            assert result[key] is None
        load.assert_not_called()


def test_evaluate_validates_chosen_features_before_gate(bundle, monkeypatch):
    summary, features, model_bytes = lab.load_bundle(bundle.root)
    with monkeypatch.context() as patch:
        patch.setattr(lab, "pre_model_decision", forbidden)
        patch.setattr(lab, "load_model", forbidden)
        with pytest.raises(ValueError, match="Invalid academic V6 bundle"):
            lab.evaluate((summary, {**features, "requested_ratio": -1}, model_bytes))
        with pytest.raises(ValueError, match="Invalid academic V6 bundle"):
            lab.evaluate((summary, features, model_bytes), "unknown")


def test_default_evaluate_preserves_frozen_eligible_features(bundle):
    loaded = lab.load_bundle(bundle.root)
    original = dict(loaded[1])
    result = lab.evaluate(loaded)
    assert result["case_id"] == "illustrative-v6"
    assert result["features"] == original
    assert result["estimated_late_probability"] == 0.25
    for case in lab.CASES[1:]:
        lab.evaluate(loaded, case["id"])
    assert loaded[1] == original


@pytest.mark.parametrize("name", ["web_manifest.json", *lab.FILES])
async def test_missing_files_503_no_paths(bundle, authenticated, client, name):
    (bundle.root / name).unlink()
    for method, path in ENDPOINTS:
        response = await client.request(method, BASE + path)
        assert response.status_code == 503
        assert response.json() == {"detail": "Laboratorio academico V6 no disponible"}
        assert str(bundle.root) not in response.text


@pytest.mark.parametrize("name", lab.FILES)
@pytest.mark.parametrize("warm_cache", [False, True])
async def test_corruption_hash_before_joblib_even_after_cache(
    bundle, authenticated, client, monkeypatch, name, warm_cache
):
    if warm_cache:
        assert (await client.post(BASE + "/evaluate/illustrative-v6")).status_code == 200
    load = Mock(side_effect=forbidden)
    monkeypatch.setattr(joblib, "load", load)
    path = bundle.root / name
    path.write_bytes(path.read_bytes() + b" ")
    for method, path in ENDPOINTS:
        assert (await client.request(method, BASE + path)).status_code == 503
    load.assert_not_called()


@pytest.mark.parametrize("change", ["version", "extra_file", "missing_file", "path", "bad_hash"])
async def test_manifest_contract(bundle, authenticated, client, no_deserialization, change):
    path = bundle.root / "web_manifest.json"
    manifest = json.loads(path.read_bytes())
    if change == "version":
        manifest["version"] = "academic-v4"
    elif change == "extra_file":
        manifest["files"]["unexpected.json"] = "0" * 64
    elif change == "missing_file":
        manifest["files"].pop("illustrative_input.json")
    elif change == "path":
        manifest["files"]["../selected_model.joblib"] = manifest["files"].pop(
            "selected_model.joblib"
        )
    else:
        manifest["files"]["selected_model.joblib"] = "not-a-sha256"
    path.write_bytes(encode(manifest))
    assert (await client.post(BASE + "/evaluate/illustrative-v6")).status_code == 503


@pytest.mark.parametrize(
    "name", ["web_manifest.json", *[n for n in lab.FILES if n.endswith("json")]]
)
@pytest.mark.parametrize("invalid", [b"{", b"[]", b'{"x":NaN}', b'{"x":1,"x":2}'])
async def test_malformed_json_503(
    bundle, authenticated, client, no_deserialization, name, invalid
):
    bundle.data[name] = invalid
    bundle.publish()
    if name == "web_manifest.json":
        (bundle.root / name).write_bytes(invalid)
    assert (await client.post(BASE + "/evaluate/illustrative-v6")).status_code == 503


@pytest.mark.parametrize(("file", "key", "value"), [
    ("pending_v6_report.json", "version", "v2"),
    ("frozen_selection.json", "version", "v2"),
    ("pending_v6_report.json", "research_only", False),
    ("frozen_selection.json", "research_only", False),
    ("pending_v6_report.json", "business_approval", True),
    ("pending_v6_report.json", "origen", "real"),
    ("pending_v6_report.json", "feature_names", list(reversed(lab.FEATURE_NAMES))),
    ("frozen_selection.json", "feature_names", lab.FEATURE_NAMES[:-1]),
    ("provenance.json", "runtime", {**lab.RUNTIME, "python": "0.0.0"}),
    ("pending_v6_report.json", "artifact_sha256", {"selected_model.joblib": "0" * 64}),
    ("pending_v6_report.json", "selection", {}),
    ("pending_v6_report.json", "provenance", {}),
])
async def test_invalid_metadata_before_model(
    bundle, authenticated, client, no_deserialization, file, key, value
):
    bundle.data[file][key] = value
    bundle.publish()
    assert (await client.post(BASE + "/evaluate/illustrative-v6")).status_code == 503


@pytest.mark.parametrize(("key", "value"), [
    ("family", "svm"), ("threshold", -1), ("threshold", 1.1),
    ("threshold", None), ("threshold", True), ("threshold", "0.2"), ("threshold", 0.1),
])
async def test_invalid_selected_model(
    bundle, authenticated, client, no_deserialization, key, value
):
    frozen = bundle.data["frozen_selection.json"]
    frozen["global_winner"][key] = value
    bundle.data["pending_v6_report.json"]["selection"] = copy.deepcopy(frozen)
    bundle.publish()
    assert (await client.post(BASE + "/evaluate/illustrative-v6")).status_code == 503


@pytest.mark.parametrize(("name", "value"), [
    ("completed_sales", True), ("completed_sales", 0.5), ("completed_sales", -1),
    ("completed_sales", "1"), ("tenure_days", 1.5), ("outstanding", -0.1),
    ("utilization", 1.1), ("requested_ratio", 0), ("requested_ratio", 1.1),
    ("punctuality_rate", 1.1), ("overdue_rate", -0.1), ("paid_late", 7),
])
async def test_invalid_feature_ranges_before_model(
    bundle, authenticated, client, no_deserialization, name, value
):
    bundle.data["illustrative_input.json"]["features"][name] = value
    bundle.publish()
    assert (await client.post(BASE + "/evaluate/illustrative-v6")).status_code == 503


@pytest.mark.parametrize("invalid", [{}, {"features": {}}, {"features": [], "label": 0}])
async def test_invalid_input_schema_before_model(
    bundle, authenticated, client, no_deserialization, invalid
):
    bundle.data["illustrative_input.json"] = invalid
    bundle.publish()
    assert (await client.post(BASE + "/evaluate/illustrative-v6")).status_code == 503


@pytest.mark.parametrize("change", ["missing", "extra", "label", "nonfinite"])
async def test_exact_trusted_feature_input(
    bundle, authenticated, client, no_deserialization, change
):
    value = bundle.data["illustrative_input.json"]
    if change == "missing":
        value["features"].pop("paid_credits")
    elif change == "extra":
        value["features"]["unknown"] = 0
    elif change == "label":
        value["late_payment"] = 0
    else:
        bundle.data["illustrative_input.json"] = encode(value).replace(
            b'"completed_sales": 6', b'"completed_sales": 1e999'
        )
    bundle.publish()
    assert (await client.post(BASE + "/evaluate/illustrative-v6")).status_code == 503


@pytest.mark.parametrize("probability", [0, 0.199, 0.2, 1])
async def test_single_trusted_vector_nulls_positive_class_and_threshold(
    bundle, authenticated, client, monkeypatch, probability
):
    calls = []

    def predict(vector):
        calls.append(vector)
        expected = [np.nan if value is None else float(value) for value in
                    bundle.data["illustrative_input.json"]["features"].values()]
        np.testing.assert_allclose(vector, [expected], equal_nan=True)
        return [[1 - probability, probability]]

    monkeypatch.setattr(joblib, "load", lambda _: SimpleNamespace(
        classes_=np.array([0, 1]), n_features_in_=11, predict_proba=predict
    ))
    response = await client.post(BASE + "/evaluate/illustrative-v6")
    assert response.status_code == 200
    assert response.json()["estimated_late_probability"] == probability
    assert response.json()["predicted_late_payment"] == int(probability >= 0.2)
    assert response.json()["decision"] == (
        "model_review_candidate" if probability >= 0.2 else "below_review_threshold"
    )
    assert response.json()["requires_manual_review"] is True
    assert response.json()["model_called"] is True
    assert len(calls) == 1 and calls[0].shape == (1, 11)


@pytest.mark.parametrize("classes", [[1, 0], [0], [1], [0, 2], [False, True], ["0", "1"]])
async def test_invalid_model_classes(bundle, authenticated, client, monkeypatch, classes):
    monkeypatch.setattr(joblib, "load", lambda _: SimpleNamespace(
        classes_=np.asarray(classes), n_features_in_=11, predict_proba=forbidden
    ))
    assert (await client.post(BASE + "/evaluate/illustrative-v6")).status_code == 503


@pytest.mark.parametrize("attributes", [
    {"n_features_in_": 10}, {"feature_names_in_": list(reversed(lab.FEATURE_NAMES))},
])
async def test_model_feature_contract(bundle, authenticated, client, monkeypatch, attributes):
    model = SimpleNamespace(classes_=np.array([0, 1]), n_features_in_=11, predict_proba=forbidden)
    for name, value in attributes.items():
        setattr(model, name, value)
    monkeypatch.setattr(joblib, "load", lambda _: model)
    assert (await client.post(BASE + "/evaluate/illustrative-v6")).status_code == 503


@pytest.mark.parametrize("probabilities", [
    [[0, float("nan")]], [[0, float("inf")]], [[0, -0.1]], [[0, 1.1]], [[0.5]], [0.5, 0.5],
])
async def test_invalid_probabilities_fail_closed(
    bundle, authenticated, client, monkeypatch, probabilities
):
    monkeypatch.setattr(joblib, "load", lambda _: SimpleNamespace(
        classes_=np.array([0, 1]), n_features_in_=11, predict_proba=lambda _: probabilities
    ))
    assert (await client.post(BASE + "/evaluate/illustrative-v6")).status_code == 503


@pytest.mark.parametrize("version", list(lab.RUNTIME))
async def test_actual_runtime_mismatch_before_deserialization(
    bundle, authenticated, client, monkeypatch, no_deserialization, version
):
    monkeypatch.setattr(lab, "runtime_versions", bundle.runtime_versions)
    if version == "python":
        monkeypatch.setattr(lab.platform, "python_version", lambda: "unsupported")
    else:
        module = {"sklearn": lab.sklearn, "numpy": np, "scipy": lab.scipy, "joblib": joblib}
        monkeypatch.setattr(module[version], "__version__", "unsupported")
    assert (await client.post(BASE + "/evaluate/illustrative-v6")).status_code == 503


def test_runtime_versions_reads_installed_packages():
    import platform

    import scipy
    import sklearn

    assert lab.runtime_versions() == {
        "python": platform.python_version(), "sklearn": sklearn.__version__,
        "numpy": np.__version__, "scipy": scipy.__version__, "joblib": joblib.__version__,
    }


async def test_trusted_but_unreadable_pickle_is_503(bundle, authenticated, client):
    bundle.data["selected_model.joblib"] = b"not a pickle"
    bundle.data["pending_v6_report.json"]["artifact_sha256"]["selected_model.joblib"] = digest(
        bundle.data["selected_model.joblib"]
    )
    bundle.publish()
    assert (await client.get(BASE + "/summary")).status_code == 200
    assert (await client.post(BASE + "/evaluate/illustrative-v6")).status_code == 503


async def test_routes_never_call_business_or_database_writes(
    bundle, authenticated, client, monkeypatch
):
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services import ai_credit, audit, credit_scoring, whatsapp

    for name in ("add", "add_all", "commit", "flush", "execute", "delete"):
        monkeypatch.setattr(AsyncSession, name, forbidden)
    for module, names in (
        (credit_scoring, ("evaluate_credit", "evaluate_and_record")),
        (audit, ("add_audit_log",)),
        (ai_credit, ("enqueue_ai_explanation", "dispatch_ai_explanation")),
        (whatsapp, ("enqueue_evaluation_notification", "dispatch_evaluation_notification",
                    "send_template_message", "enqueue_payment_confirmation")),
    ):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    for method, path in ENDPOINTS:
        assert (await client.request(method, BASE + path)).status_code == 200


def test_service_has_no_runner_generator_or_business_imports():
    import ast

    source = ast.parse(Path(lab.__file__).read_text())
    imports = [node.module for node in ast.walk(source) if isinstance(node, ast.ImportFrom)]
    imports += [alias.name for node in ast.walk(source) if isinstance(node, ast.Import)
                for alias in node.names]
    assert "app.services.academic_v6_policy" in imports
    assert not any(name and name != "app.services.academic_v6_policy" and name.startswith((
        "scripts", "subprocess", "app.ml", "app.db", "app.services", "app.models"
    )) for name in imports)


@pytest.fixture
def final_bundle(bundle):
    report = bundle.data["pending_v6_report.json"]
    frozen = bundle.data["frozen_selection.json"]
    provenance = bundle.data["provenance.json"]
    for value in (report, frozen, provenance):
        value.update(revision_id="v6-final-r1", display_name="V6 Final")
    winner = frozen["global_winner"]
    winner.update(family="svm", threshold=0.1,
                  params={"family": "svm", "C": 1, "class_weight": "balanced"})
    winner["review_policy"]["metrics"]["f2"] = 0.5523672883787661
    report["selection"] = copy.deepcopy(frozen)
    report["provenance"] = copy.deepcopy(provenance)
    report["models"]["svm"]["threshold"] = 0.1
    report["artifact_sha256"]["svm.joblib"] = report["artifact_sha256"]["selected_model.joblib"]
    report["final"] = {"known_rows": 275, "unknown_rows": 2, "study_rows": 277,
                       "audits": [{"clients": 12}]}
    report["development"].update(study_rows=541, known_rows=534, unknown_rows=7)
    for name, blocked in (("development", 45), ("final", 15)):
        cohort = report[name]
        cohort["study_attempts"] = cohort["study_rows"] + blocked
        cohort["routing"] = {
            "blocked_pending_balance": blocked, "requires_owner_review": 0,
            "model_eligible": cohort["study_rows"], "simulator_refused_model_eligible": 0,
            "private_ledger": ["never expose"],
        }
    bundle.publish()
    return bundle


async def test_final_svm_summary_and_closed_cases(final_bundle, authenticated, client, monkeypatch):
    monkeypatch.setattr(joblib, "load", forbidden)
    response = await client.get(BASE + "/summary")
    assert response.status_code == 200, response.text
    summary = response.json()
    assert summary["revision_id"] == "v6-final-r1" and summary["display_name"] == "V6 Final"
    assert summary["selected_model"] == "svm" and summary["threshold"] == 0.1
    assert summary["selection"]["oof_f2"] == 0.5523672883787661
    assert summary["training_scope"] == "eligible_known_only"
    assert summary["final_labeled_rows"] == 275 and summary["final_unknown"] == 2
    assert summary["routing"]["final"] == {
        "study_attempts": 292, "blocked_pending_balance": 15, "requires_owner_review": 0,
        "model_eligible": 277, "simulator_refused_model_eligible": 0,
    }
    assert "private_ledger" not in response.text
    for case in lab.CASES[1:]:
        result = await client.post(BASE + "/evaluate/" + case["id"])
        assert result.status_code == 200 and result.json()["model_called"] is False


@pytest.mark.parametrize("threshold", [0.1, 0.35])
def test_final_declared_threshold_and_matching_artifact(final_bundle, threshold):
    report = final_bundle.data["pending_v6_report.json"]
    frozen = final_bundle.data["frozen_selection.json"]
    frozen["global_winner"]["threshold"] = threshold
    report["selection"] = copy.deepcopy(frozen)
    report["models"]["svm"]["threshold"] = threshold
    final_bundle.publish()
    result = lab.evaluate(lab.load_bundle(final_bundle.root))
    assert result["model_called"] is True
    assert result["estimated_late_probability"] == 0.25
    assert result["threshold"] == threshold
    assert result["predicted_late_payment"] == int(0.25 >= threshold)


@pytest.mark.parametrize("change", ["artifact", "threshold", "revision", "routing"])
def test_final_inconsistent_metadata_rejected(final_bundle, no_deserialization, change):
    report = final_bundle.data["pending_v6_report.json"]
    if change == "artifact":
        report["artifact_sha256"]["svm.joblib"] = "0" * 64
    elif change == "threshold":
        report["models"]["svm"]["threshold"] = 0.2
    elif change == "revision":
        report["revision_id"] = "unknown"
    else:
        report["final"]["routing"]["model_eligible"] = 278
    final_bundle.publish()
    with pytest.raises(ValueError):
        lab.load_bundle(final_bundle.root)


@pytest.mark.parametrize(
    "name", ["accuracy", "balanced_accuracy", "precision", "recall", "f1", "f2", "brier"]
)
def test_raw_null_metrics_rejected_except_undefined_auc(bundle, name):
    report = bundle.data["pending_v6_report.json"]
    report["models"]["svm"]["final"][name] = None
    bundle.publish()
    with pytest.raises(ValueError):
        lab.load_bundle(bundle.root)


def test_raw_undefined_auc_preserved_as_null(final_bundle):
    raw = final_bundle.data["pending_v6_report.json"]["models"]["svm"]["final"]
    raw.update(roc_auc=None, confusion_matrix=[[3, 1], [0, 0]])
    final_bundle.publish()
    summary, _, _ = lab.load_bundle(final_bundle.root)
    assert summary["comparison"][0]["raw"]["roc_auc"] is None


def test_raw_null_auc_with_both_labels_is_invalid(final_bundle):
    final_bundle.data["pending_v6_report.json"]["models"]["svm"]["final"]["roc_auc"] = None
    final_bundle.publish()
    with pytest.raises(ValueError):
        lab.load_bundle(final_bundle.root)


def test_final_loader_does_not_force_winning_family(final_bundle):
    report = final_bundle.data["pending_v6_report.json"]
    frozen = final_bundle.data["frozen_selection.json"]
    frozen["global_winner"].update(family="tree", params={"family": "tree"}, threshold=0.4)
    report["selection"] = copy.deepcopy(frozen)
    report["models"]["tree"]["threshold"] = 0.4
    report["artifact_sha256"]["tree.joblib"] = report["artifact_sha256"]["selected_model.joblib"]
    final_bundle.publish()
    loaded = lab.load_bundle(final_bundle.root)
    assert loaded[0]["selected_model"] == "tree"
    assert lab.evaluate(loaded)["threshold"] == 0.4


def test_historical_report_display_name_is_preserved(bundle):
    bundle.data["pending_v6_report.json"]["display_name"] = "V6 historical archive"
    bundle.publish()
    summary, _, _ = lab.load_bundle(bundle.root)
    assert summary["revision_id"] == "v6-historical"
    assert summary["display_name"] == "V6 historical archive"
