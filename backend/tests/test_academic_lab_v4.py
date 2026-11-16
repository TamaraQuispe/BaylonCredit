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
from app.api.routes import academic_ml_v4 as routes
from app.core.config import Settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.ml.features import FEATURE_NAMES
from app.models.user import UserRole
from app.services import academic_lab_v4 as lab

BASE = "/api/v1/academic-ml/v4"
ENDPOINTS = [("GET", "/summary"), ("GET", "/cases"), ("POST", "/evaluate/illustrative-v4")]


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
            "family": "svm", "params": {"family": "svm"}, "threshold": 0.1,
            "review_policy": copy.deepcopy(policy),
        },
        "selection_metric": "Capped review-policy F2, no minimum precision floor",
    }
    provenance = {
        "runtime": dict(lab.RUNTIME), "feature_names": list(lab.FEATURE_NAMES),
        "source_anchors": {
            "evaluable": 45, "late": 8, "partial_payment_annotations": 10,
            "partial_payment_denominator": 48, "source_quality": "Approximate, not audited",
            "private_verbose_source": "must not be exposed",
        },
    }
    report = {
        "version": lab.VERSION, "origen": "simulado", "research_only": True,
        "business_approval": False, "feature_names": list(lab.FEATURE_NAMES),
        "selection": copy.deepcopy(frozen), "provenance": copy.deepcopy(provenance),
        "development": {
            "resolved_study_rows": 552, "unknown_study_rows": 7,
            "audits": [{"clients": 12}, {"clients": 12}],
        },
        "final": {"known_rows": 259, "study_rows": 260, "audit": {"clients": 12}},
        "models": {family: {
            "threshold": 0.1, "final": copy.deepcopy(raw),
            "review_policy": {"final": copy.deepcopy(policy)},
        } for family in lab.LABELS},
        "artifact_sha256": {"selected_model.joblib": digest(stream.getvalue())},
        "limitations": ["Synthetic alternative histories, not real validation"],
    }
    features = dict.fromkeys(lab.FEATURE_NAMES, 0)
    features.update(requested_ratio=0.25, tenure_days=None, outstanding=None)
    data = {
        "aligned_v4_report.json": report, "frozen_selection.json": frozen,
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
        academic_ml_v4_enabled=True, environment="staging", academic_ml_v4_dir=str(tmp_path)
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
    assert settings.academic_ml_v4_enabled is False
    assert settings.academic_ml_v4_dir == "/app/academic-v4"
    assert lab.FEATURE_NAMES == FEATURE_NAMES


@pytest.mark.parametrize("environment", ["development", "test", "production"])
def test_settings_restrict_enabled_to_staging(environment):
    with pytest.raises(ValueError, match="restricted to staging"):
        Settings(_env_file=None, environment=environment, academic_ml_v4_enabled=True)


def test_settings_staging_still_requires_jwt_secret():
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(_env_file=None, environment="staging", academic_ml_v4_enabled=True)
    assert Settings(_env_file=None, environment="staging", academic_ml_v4_enabled=True,
                    jwt_secret_key="configured-staging-secret").academic_ml_v4_enabled


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
        academic_ml_v4_enabled=enabled, environment=environment
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
        "source", "limitations", "disclaimer",
    }
    assert summary["version"] == lab.VERSION and summary["selected_model"] == "svm"
    assert summary["data_source"] == "synthetic" and summary["research_only"] is True
    assert summary["business_approval"] is False and summary["threshold"] == 0.1
    assert [summary[key] for key in (
        "development_rows", "development_unknown", "development_clients",
        "final_labeled_rows", "final_unknown", "final_clients"
    )] == [552, 7, 24, 259, 1, 12]
    assert summary["selection"]["oof_f2"] == 0.625
    assert summary["source"] == {
        "evaluable": 45, "late": 8, "partial_annotations": 10,
        "partial_denominator": 48, "quality": "Approximate, not audited",
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
        "id": "illustrative-v4", "scenario": "Ejemplo nuevo sin etiqueta",
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
        response = await client.post(BASE + "/evaluate/illustrative-v4")
        assert response.status_code == 200, response.text
        result = response.json()
        assert set(result) == {
            "case_id", "scenario", "data_source", "version", "research_only", "business_approval",
            "estimated_late_probability", "threshold", "predicted_late_payment",
            "actual_late_payment", "features", "review_policy_applied", "disclaimer",
        }
        assert result["case_id"] == "illustrative-v4"
        assert result["scenario"] == lab.CASE["scenario"]
        assert result["estimated_late_probability"] == 0.25
        assert result["threshold"] == 0.1 and result["predicted_late_payment"] == 1
        assert result["actual_late_payment"] is None and result["review_policy_applied"] is False
        assert result["research_only"] is True and result["business_approval"] is False
        assert result["features"]["tenure_days"] is None
        assert list(result["features"]) == lab.FEATURE_NAMES
        assert "top-5" in result["disclaimer"] and "clientes reales" in result["disclaimer"]
    assert len(loads) == 1
    assert lab.validated_bundle.cache_info().hits == 1


@pytest.mark.parametrize(
    "case_id", ["unknown", "FINAL-L1", "illustrative-v3", "selected_model.joblib"]
)
async def test_unknown_case_before_io(bundle, authenticated, client, monkeypatch, case_id):
    monkeypatch.setattr(lab, "load_bundle", forbidden)
    assert (await client.post(BASE + "/evaluate/" + case_id)).status_code == 404


@pytest.mark.parametrize("kwargs", [
    {"json": {}}, {"json": {"features": {}}}, {"content": b"not-json"},
    {"params": {"path": "/tmp/arbitrary"}},
    {"files": {"upload": ("input.json", b"{}")}},
])
async def test_arbitrary_inputs_rejected_before_io(
    bundle, authenticated, client, monkeypatch, kwargs
):
    monkeypatch.setattr(lab, "load_bundle", forbidden)
    assert (await client.post(BASE + "/evaluate/illustrative-v4", **kwargs)).status_code == 422


@pytest.mark.parametrize("name", ["web_manifest.json", *lab.FILES])
async def test_missing_files_503_no_paths(bundle, authenticated, client, name):
    (bundle.root / name).unlink()
    for method, path in ENDPOINTS:
        response = await client.request(method, BASE + path)
        assert response.status_code == 503
        assert response.json() == {"detail": "Laboratorio academico V4 no disponible"}
        assert str(bundle.root) not in response.text


@pytest.mark.parametrize("name", lab.FILES)
@pytest.mark.parametrize("warm_cache", [False, True])
async def test_corruption_hash_before_joblib_even_after_cache(
    bundle, authenticated, client, monkeypatch, name, warm_cache
):
    if warm_cache:
        assert (await client.post(BASE + "/evaluate/illustrative-v4")).status_code == 200
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
        manifest["version"] = "academic-v2"
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
    assert (await client.post(BASE + "/evaluate/illustrative-v4")).status_code == 503


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
    assert (await client.post(BASE + "/evaluate/illustrative-v4")).status_code == 503


@pytest.mark.parametrize(("file", "key", "value"), [
    ("aligned_v4_report.json", "version", "v2"),
    ("frozen_selection.json", "version", "v2"),
    ("aligned_v4_report.json", "research_only", False),
    ("frozen_selection.json", "research_only", False),
    ("aligned_v4_report.json", "business_approval", True),
    ("aligned_v4_report.json", "origen", "real"),
    ("aligned_v4_report.json", "feature_names", list(reversed(lab.FEATURE_NAMES))),
    ("frozen_selection.json", "feature_names", lab.FEATURE_NAMES[:-1]),
    ("provenance.json", "feature_names", list(reversed(lab.FEATURE_NAMES))),
    ("provenance.json", "runtime", {**lab.RUNTIME, "python": "0.0.0"}),
    ("aligned_v4_report.json", "artifact_sha256", {"selected_model.joblib": "0" * 64}),
    ("aligned_v4_report.json", "selection", {}),
    ("aligned_v4_report.json", "provenance", {}),
])
async def test_invalid_metadata_before_model(
    bundle, authenticated, client, no_deserialization, file, key, value
):
    bundle.data[file][key] = value
    bundle.publish()
    assert (await client.post(BASE + "/evaluate/illustrative-v4")).status_code == 503


@pytest.mark.parametrize(("key", "value"), [
    ("family", "tree"), ("threshold", -1), ("threshold", 1.1),
    ("threshold", None), ("threshold", True), ("threshold", "0.1"), ("threshold", 0.2),
])
async def test_invalid_selected_model(
    bundle, authenticated, client, no_deserialization, key, value
):
    frozen = bundle.data["frozen_selection.json"]
    frozen["global_winner"][key] = value
    bundle.data["aligned_v4_report.json"]["selection"] = copy.deepcopy(frozen)
    bundle.publish()
    assert (await client.post(BASE + "/evaluate/illustrative-v4")).status_code == 503


@pytest.mark.parametrize(("name", "value"), [
    ("completed_sales", True), ("completed_sales", 0.5), ("completed_sales", -1),
    ("completed_sales", "1"), ("tenure_days", 1.5), ("outstanding", -0.1),
    ("utilization", 1.1), ("requested_ratio", 0), ("requested_ratio", 1.1),
    ("punctuality_rate", 1.1), ("overdue_rate", -0.1), ("paid_late", 1),
])
async def test_invalid_feature_ranges_before_model(
    bundle, authenticated, client, no_deserialization, name, value
):
    bundle.data["illustrative_input.json"]["features"][name] = value
    bundle.publish()
    assert (await client.post(BASE + "/evaluate/illustrative-v4")).status_code == 503


@pytest.mark.parametrize("invalid", [{}, {"features": {}}, {"features": [], "label": 0}])
async def test_invalid_input_schema_before_model(
    bundle, authenticated, client, no_deserialization, invalid
):
    bundle.data["illustrative_input.json"] = invalid
    bundle.publish()
    assert (await client.post(BASE + "/evaluate/illustrative-v4")).status_code == 503


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
            b'"completed_sales": 0', b'"completed_sales": 1e999'
        )
    bundle.publish()
    assert (await client.post(BASE + "/evaluate/illustrative-v4")).status_code == 503


@pytest.mark.parametrize("probability", [0, 0.099, 0.1, 1])
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
    response = await client.post(BASE + "/evaluate/illustrative-v4")
    assert response.status_code == 200
    assert response.json()["estimated_late_probability"] == probability
    assert response.json()["predicted_late_payment"] == int(probability >= 0.1)
    assert len(calls) == 1 and calls[0].shape == (1, 11)


@pytest.mark.parametrize("classes", [[1, 0], [0], [1], [0, 2], [False, True], ["0", "1"]])
async def test_invalid_model_classes(bundle, authenticated, client, monkeypatch, classes):
    monkeypatch.setattr(joblib, "load", lambda _: SimpleNamespace(
        classes_=np.asarray(classes), n_features_in_=11, predict_proba=forbidden
    ))
    assert (await client.post(BASE + "/evaluate/illustrative-v4")).status_code == 503


@pytest.mark.parametrize("attributes", [
    {"n_features_in_": 10}, {"feature_names_in_": list(reversed(lab.FEATURE_NAMES))},
])
async def test_model_feature_contract(bundle, authenticated, client, monkeypatch, attributes):
    model = SimpleNamespace(classes_=np.array([0, 1]), n_features_in_=11, predict_proba=forbidden)
    for name, value in attributes.items():
        setattr(model, name, value)
    monkeypatch.setattr(joblib, "load", lambda _: model)
    assert (await client.post(BASE + "/evaluate/illustrative-v4")).status_code == 503


@pytest.mark.parametrize("probabilities", [
    [[0, float("nan")]], [[0, float("inf")]], [[0, -0.1]], [[0, 1.1]], [[0.5]], [0.5, 0.5],
])
async def test_invalid_probabilities_fail_closed(
    bundle, authenticated, client, monkeypatch, probabilities
):
    monkeypatch.setattr(joblib, "load", lambda _: SimpleNamespace(
        classes_=np.array([0, 1]), n_features_in_=11, predict_proba=lambda _: probabilities
    ))
    assert (await client.post(BASE + "/evaluate/illustrative-v4")).status_code == 503


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
    assert (await client.post(BASE + "/evaluate/illustrative-v4")).status_code == 503


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
    bundle.data["aligned_v4_report.json"]["artifact_sha256"]["selected_model.joblib"] = digest(
        bundle.data["selected_model.joblib"]
    )
    bundle.publish()
    assert (await client.get(BASE + "/summary")).status_code == 200
    assert (await client.post(BASE + "/evaluate/illustrative-v4")).status_code == 503


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
    assert not any(name and name.startswith((
        "scripts", "subprocess", "app.ml", "app.db", "app.services", "app.models"
    )) for name in imports)
