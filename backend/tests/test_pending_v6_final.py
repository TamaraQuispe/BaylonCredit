"""Tiny mocked worlds only; never prepare real DEV, fit a real model, or generate FINAL."""

import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from scripts import academic_credit_pending_v6_final as runner

POLICY = Path(__file__).parents[1] / "app/services/academic_v6_policy.py"
APPROVED_POLICY_SHA256 = "418af45fcdc1a5d952daac7aa5139bfa87d2a66ef126255f306cff3c66591f1f"


def isolated(test):
    """Run helper-dependent tests in a fresh interpreter, even during combined collection."""
    if os.environ.get("V6_FINAL_ISOLATED_TEST") == "1":
        return test

    def run_in_subprocess(request):
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             f"{Path(__file__).absolute()}::{request.node.name}"],
            env={**os.environ, "V6_FINAL_ISOLATED_TEST": "1", "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True, text=True, timeout=120, check=False)
        assert result.returncode == 0, result.stdout + result.stderr

    return run_in_subprocess


def features():
    return dict(zip(runner.FEATURE_NAMES, [6, 6, 1, 0, 0, 0, 0, .25, 60, 5 / 6, 0], strict=True))


def rows(prefix):
    known = [{**features(), "client_id": f"{prefix}-C{c}", "loan_id": f"{prefix}-L{c}-{label}",
              "replica_id": prefix, "late_payment": label, "phase": "study", "origen": "simulado",
              "evaluated_at": "2026-01-10T09:00:00", "tenure_days": 100 + c}
             for c in range(9) for label in (0, 1)]
    return known + [{**known[0], "loan_id": f"{prefix}-U", "late_payment": None},
                    {**known[0], "loan_id": f"{prefix}-M", "paid_credits": 0,
                     "completed_sales": 0, "paid_late": 0, "punctuality_rate": 0},
                    {**known[0], "loan_id": f"{prefix}-B", "outstanding": 1}]


@pytest.mark.parametrize("change,decision", [
    ({"pending_current": 1}, "blocked_pending_balance"),
    ({"outstanding": 0.5}, "blocked_pending_balance"),
    ({"outstanding": None}, "requires_owner_review"),
    ({"paid_credits": 0}, "requires_owner_review"),
    ({"paid_credits": None}, "requires_owner_review"),
])
def test_actual_gate_never_loads_model(tmp_path, monkeypatch, change, decision):
    monkeypatch.setattr(runner, "verify_freeze", lambda *_: pytest.fail("no artifacts for guards"))
    result = runner.predict(tmp_path, {**features(), **change}, POLICY)
    assert result["decision"] == decision
    assert result["model_called"] is False and result["probability"] is None


@pytest.mark.parametrize("value", [True, "1", float("nan"), float("inf"), -1, 10**999])
def test_numeric_validation_precedes_policy(monkeypatch, value):
    policy = SimpleNamespace(pre_model_decision=lambda _: pytest.fail("invalid input reached gate"))
    with pytest.raises(ValueError):
        runner.gate({**features(), "outstanding": value}, policy)


@isolated
def test_snapshot_strict_time_and_initial_manual_history():
    _, simulator = runner.helpers()
    client = {"client_id": "UNIT-C", "registered_on": "2026-01-01", "credit_cap": "80"}
    loan = {"loan_id": "UNIT-L", "client_id": "UNIT-C", "evaluated_at": "2026-01-02T09:00:00",
            "due_date": "2026-01-03", "amount": "20", "payments": [
                {"at": "2026-01-03T09:00:00", "amount": "20"}],
            "authorization_tags": ["simulated_owner_review"]}
    sale = {"client_id": "UNIT-C", "at": "2026-01-02T09:01:00"}
    world = {"clients": [client], "loans": [loan], "sales": [sale], "rows": [], "attempts": []}
    times = ["2026-01-02T09:00:00", "2026-01-03T09:00:00", "2026-01-03T09:00:01"]
    for i, at in enumerate(times):
        world["attempts"].append({"attempt_id": f"UNIT-A{i}", "loan_id": None,
            "client_id": "UNIT-C", "replica_id": "UNIT", "evaluated_at": at,
            "requested_amount": "20", "phase": "study", "granted": False,
            "refusal_reason": "fixture"})
    eligible, ledger = runner.route(world, runner.load_policy(POLICY), simulator)
    assert eligible == []
    assert [e["decision"] for e in ledger] == ["requires_owner_review", "blocked_pending_balance",
                                               "simulator_refused_model_eligible"]
    assert [e["features"]["paid_credits"] for e in ledger] == [0, 0, 1]
    assert [e["features"]["outstanding"] for e in ledger] == [0, 20, 0]
    assert all(not e["model_called"] and e["probability"] is None for e in ledger)


@isolated
def test_three_fold_plan_client_disjoint_unknown_covered(monkeypatch):
    old, _ = runner.helpers()
    study = rows("UNIT")[:-2]
    known = [r for r in study if r["late_payment"] is not None]
    plan = runner.plan_folds(old, known, study)
    assert plan["outer"]["n_splits"] == 3
    for fold in plan["outer"]["folds"]:
        assert set(fold["train_clients"]).isdisjoint(fold["validation_clients"])
    assert plan["unknown_study_validation"][0]["client_id"] == study[-1]["client_id"]
    broken = study + [{**study[-1], "client_id": "UNIT-unknown-only"}]
    with pytest.raises(ValueError, match="Unknown clients"):
        runner.plan_folds(old, known, broken)
    monkeypatch.setattr(old.freeze.audit, "grouped_splits", lambda *_: {"n_splits": 2})
    with pytest.raises(ValueError, match="three"):
        runner.plan_folds(old, known, study)


class FakeModel:
    n_features_in_ = 11
    classes_ = np.array([0, 1])

    def predict_proba(self, x):
        return np.tile([.4, .6], (len(x), 1))


@pytest.fixture
def experiment(tmp_path, monkeypatch):
    old, simulator = runner.helpers()
    sources = tmp_path / "sources"
    sources.mkdir()
    # Test patches replace only external identity/runtime/generation gates, not orchestration.
    inherited = {"runtime": {}, "feature_names": runner.FEATURE_NAMES,
                 "tree": {"max_depth": [2, 3, 4], "min_samples_leaf": [8, 16],
                          "class_weight": [None, "balanced"], "random_state": 42},
                 "svm": {"C": [.1, 1., 10.], "class_weight": [None, "balanced"],
                         "kernel": "linear", "probability": False, "random_state": 42},
                 "thresholds": [.1, .2, .3, .4, .5, .6, .7],
                 "review_policy": {"daily_cap": 5, "minutes_per_case": 2},
                 "cv": {"selection_optimism": "Fixture OOF selection is optimistic"},
                 "illustrative_input": {"features": features()}, "limits": ["Fixture only"]}
    for name in [*runner.SOURCES, runner.MODEL_PROTOCOL]:
        runner.write(sources / name, inherited if name == runner.MODEL_PROTOCOL else {})
    protocol = sources / "protocol.json"
    runner.write(protocol, {"fixture": True})
    evidence = {"protocol_sha256": runner.digest(protocol),
                "source_sha256": {n: runner.digest(sources / n) for n in runner.SOURCES},
                "policy_sha256": runner.digest(POLICY), "code_sha256": {}, "runtime": {}}

    def context(*_):
        return {}, deepcopy(inherited), deepcopy(evidence), old, simulator

    monkeypatch.setattr(runner, "context", context)
    monkeypatch.setattr(old, "validate_runtime", lambda _: {})
    monkeypatch.setattr(runner, "SOURCES", evidence["source_sha256"])
    monkeypatch.setattr(runner, "MODEL_PROTOCOL_SHA256",
                        runner.digest(sources / runner.MODEL_PROTOCOL))
    monkeypatch.setattr(old, "interpretation", lambda *_: {"fixture": True})
    monkeypatch.setattr(runner, "audit_world", lambda *_: {"hard_constraints_pass": True,
                        "adequacy": {"adequate": False}, "legacy_grant_scale_flag": False})
    events, fits, final_scores = [], [], []
    output = tmp_path / "trained"

    def generate(spec, *_):
        events.append(spec["prefix"])
        if spec == runner.FINAL:
            runner.verify_freeze(output, POLICY)
            assert len(fits) == 64  # 20 candidates x three folds, plus four refits.
            assert final_scores == []
        study = rows(spec["prefix"])
        return {"rows": study, "clients": [{"client_id": r["client_id"]} for r in study[:18:2]],
                "attempts": [{} for _ in study]}

    def route(world, policy, _):
        eligible, ledger = [], []
        for row in world["rows"]:
            f, decision = runner.gate({n: row[n] for n in runner.FEATURE_NAMES}, policy)
            if decision is None:
                eligible.append(row)
            ledger.append({"loan_id": row["loan_id"], "granted": True, "features": f,
                           "decision": decision["decision"] if decision else "model_eligible",
                           "model_called": False, "probability": None})
        return eligible, ledger

    def fit(params, x, y, groups, inner):
        assert set(y) == {0, 1} and len(y) == len(groups) == len(x)
        assert all(x[:, 1] > 0) and all(x[:, 5] == 0)
        assert inner is not None and len(inner) == 3
        fits.append(len(y))
        return FakeModel()

    original_scores = old.checked_scores

    def scores(model, x):
        if runner.FINAL["prefix"] in events:
            final_scores.append(len(x))
        return original_scores(model, x)

    monkeypatch.setattr(runner, "generate", generate)
    monkeypatch.setattr(runner, "route", route)
    monkeypatch.setattr(old, "fit_model", fit)
    monkeypatch.setattr(old, "checked_scores", scores)
    dev = tmp_path / "development"
    runner.prepare_dev(protocol, evidence["protocol_sha256"], sources, dev, POLICY)
    return SimpleNamespace(protocol=protocol, sha=evidence["protocol_sha256"], sources=sources,
                           dev=dev, output=output, events=events, fits=fits, scores=final_scores,
                           evidence=evidence, old=old)


def run(experiment):
    e = experiment
    return runner.train_evaluate(e.protocol, e.sha, e.dev, e.output, POLICY)


@isolated
def test_freeze_before_final_once_eligible_metrics_and_null_guards(experiment):
    e = experiment
    assert e.fits == [] and e.events == [r["prefix"] for r in runner.DEV]
    before = runner.inventory(e.dev)
    report = run(e)
    assert e.events == [r["prefix"] for r in runner.DEV] + [runner.FINAL["prefix"]]
    assert e.scores == [19, 19, 19, 19, 1]  # Last is distinct illustrative inference, not cohort.
    assert report["final"]["study_rows"] == 19
    assert report["final"]["known_rows"] == 18 and report["final"]["unknown_rows"] == 1
    assert report["final"]["study_granted"] == 21
    assert report["final"]["audit"]["adequacy"]["adequate"] is False
    assert report["final"]["audit"]["legacy_grant_scale_flag"] is False
    assert runner.inventory(e.dev) == before
    search = runner.load(e.output / "cv_search.json")
    assert len(search["candidates"]) == 18
    assert sum(len(c["threshold_results"]) for c in search["candidates"]) == 126
    for model in report["models"].values():
        assert model["final"]["n"] == 18
        assert model["review_policy"]["final"]["capacity_respected"]
    ledger = runner.load(e.output / "final_routing_ledger.json")
    assert all(not r["model_called"] and r["probability"] is None for r in ledger[-2:])
    assert runner.load(e.output / "final_manifest.json")["revision_id"] == runner.REVISION


@isolated
def test_changed_policy_or_code_refused_before_fit(experiment):
    e = experiment
    e.evidence["policy_sha256"] = "changed"
    with pytest.raises(ValueError, match="changed"):
        run(e)
    assert e.fits == [] and runner.FINAL["prefix"] not in e.events
    assert runner.load(e.output / "failure.json")["stage"] == "input_validation"


@isolated
def test_final_failure_retained_no_retry(experiment, monkeypatch):
    e = experiment
    original = runner.audit_world

    def audit(world, *args):
        if world["rows"][0]["replica_id"] == runner.FINAL["prefix"]:
            raise ValueError("hard audit fixture failure")
        return original(world, *args)

    monkeypatch.setattr(runner, "audit_world", audit)
    with pytest.raises(ValueError, match="hard audit"):
        run(e)
    assert e.events.count(runner.FINAL["prefix"]) == 1 and e.scores == []
    assert (e.output / "final_transactions.json").is_file()
    assert runner.load(e.output / "failure.json")["retry"] is False


@isolated
def test_tampered_artifact_refused_before_deserialization(experiment, monkeypatch):
    e = experiment
    run(e)
    # Deliberate corruption of this test's disposable artifact, never source artifacts.
    with (e.output / "selected_model.joblib").open("ab") as stream:
        stream.write(b"tamper")
    monkeypatch.setattr(e.old.joblib, "load",
                        lambda *_: pytest.fail("deserialized tampered artifact"))
    with pytest.raises(ValueError, match="SHA256"):
        runner.predict(e.output, features(), POLICY)


@isolated
def test_damaged_freeze_stops_before_final_generation(experiment, monkeypatch):
    e = experiment
    original = runner.verify_freeze

    def damaged(directory, policy):
        with (directory / "selected_model.joblib").open("ab") as stream:
            stream.write(b"damaged before final")
        return original(directory, policy)

    monkeypatch.setattr(runner, "verify_freeze", damaged)
    with pytest.raises(ValueError, match="SHA256"):
        run(e)
    assert runner.FINAL["prefix"] not in e.events
    assert runner.load(e.output / "failure.json")["stage"] == "freeze_verification"


@isolated
def test_single_class_and_unknown_metrics_from_cache_only():
    old, _ = runner.helpers()
    study = [{**r, "late_payment": 1} for r in rows("UNIT")[:-2]]
    result = old.evaluate_cached(study, np.zeros(len(study)), .5,
                                 {"daily_cap": 5, "minutes_per_case": 2}, predictions=True)
    assert result["metrics"]["roc_auc"] is None
    assert result["error_count"] == len(study)
    assert [r["loan_id"] for r in result["error_cases"]] == sorted(r["loan_id"] for r in study)[:10]
    study = [{**r, "late_payment": None} for r in study]
    result = old.evaluate_cached(study, np.ones(len(study)), .5,
                                 {"daily_cap": 5, "minutes_per_case": 2})
    assert result["metrics"]["n"] == 0 and result["metrics"]["roc_auc"] is None
    assert result["review_policy"]["reviews_unknown"] == 5


@isolated
def test_empty_eligible_final_fails_without_retry(experiment, monkeypatch):
    e = experiment
    original = runner.route

    def route(world, *args):
        eligible, ledger = original(world, *args)
        if world["rows"][0]["replica_id"] == runner.FINAL["prefix"]:
            return [], ledger
        return eligible, ledger

    monkeypatch.setattr(runner, "route", route)
    with pytest.raises(ValueError, match="Empty eligible"):
        run(e)
    assert e.events.count(runner.FINAL["prefix"]) == 1 and e.scores == []
    assert runner.load(e.output / "failure.json")["retry"] is False


def test_input_protocol_sha_checked_before_helpers(tmp_path, monkeypatch):
    protocol = tmp_path / "revision.json"
    runner.write(protocol, {})
    monkeypatch.setattr(runner, "helpers", lambda: pytest.fail("bad protocol reached helpers"))
    with pytest.raises(ValueError, match="protocol SHA256"):
        runner.context(protocol, "wrong", tmp_path, POLICY)


def revision_protocol():
    return {**runner.IDENTITY, "authorized_user_request": "Authorized V6 Final research retraining",
            "development_replicas": runner.DEV, "final_replica": runner.FINAL, "cv": runner.CV,
            "inherited_model_protocol_filename": runner.MODEL_PROTOCOL,
            "inherited_model_protocol_sha256": runner.MODEL_PROTOCOL_SHA256,
            "source_sha256": runner.SOURCES, "no_reseed": True,
            "policy_sha256": APPROVED_POLICY_SHA256,
            "policies": {**dict.fromkeys(runner.REQUIRED_POLICIES, True),
                         "explanation": "Additional explanatory strings are allowed"}}


@pytest.mark.parametrize("declared", [None, "", "not-a-digest", "0" * 64])
def test_real_context_policy_digest_required_before_sources(tmp_path, monkeypatch, declared):
    revision = revision_protocol()
    if declared is None:
        del revision["policy_sha256"]
    else:
        revision["policy_sha256"] = declared
    protocol = tmp_path / "revision.json"
    runner.write(protocol, revision)
    monkeypatch.setattr(runner, "verify",
                        lambda *_: pytest.fail("read sources before policy check"))
    with pytest.raises(ValueError, match="policy_sha256"):
        runner.context(protocol, runner.digest(protocol), tmp_path, POLICY)


def test_real_context_unapproved_callable_rejected_before_import(tmp_path, monkeypatch):
    protocol = tmp_path / "revision.json"
    runner.write(protocol, revision_protocol())
    unapproved = tmp_path / "unapproved.py"
    with unapproved.open("x") as stream:
        stream.write("raise AssertionError('Unapproved policy executed')\n"
                     "def pre_model_decision(features): return None\n")
    monkeypatch.setattr(runner, "verify",
                        lambda *_: pytest.fail("read sources before policy check"))
    with pytest.raises(ValueError, match="Policy source SHA256"):
        runner.context(protocol, runner.digest(protocol), tmp_path, unapproved)


@pytest.mark.parametrize("name", runner.REQUIRED_POLICIES)
@pytest.mark.parametrize("value", [False, 1, "true", None])
def test_real_context_requires_exact_policy_booleans(tmp_path, monkeypatch, name, value):
    revision = revision_protocol()
    if value is None:
        del revision["policies"][name]
    else:
        revision["policies"][name] = value
    protocol = tmp_path / "revision.json"
    runner.write(protocol, revision)
    monkeypatch.setattr(runner, "verify",
                        lambda *_: pytest.fail("unapproved policy reached sources"))
    with pytest.raises(ValueError, match=f"Revision policy must be true: {name}"):
        runner.context(protocol, runner.digest(protocol), tmp_path, POLICY)


def test_real_context_success_without_generation_in_subprocess(tmp_path):
    sources = Path(__file__).parents[2] / "docs"
    if not (sources / runner.MODEL_PROTOCOL).is_file():
        pytest.skip("Exact frozen source docs unavailable; mount repo docs for context validation")
    revision = revision_protocol()
    revision["runtime"] = runner.load(sources / runner.MODEL_PROTOCOL)["runtime"]
    protocol = tmp_path / "revision.json"
    runner.write(protocol, revision)
    result = subprocess.run(
        [sys.executable, "-c", """
import sys
from pathlib import Path
from scripts import academic_credit_pending_v6_final as runner

def guard(frame, event, arg):
    if event == 'call' and (frame.f_code.co_name.startswith('generate_owner_')
                           or frame.f_code.co_name == 'generate_academic_dataset'
                           or frame.f_code.co_name in ('fit', 'predict', 'predict_proba')):
        raise AssertionError('Context validation attempted generation or modeling')

sys.setprofile(guard)
try:
    revision, effective, evidence, old, simulator = runner.context(
        Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]))
except ValueError as error:
    if str(error).startswith('Frozen runtime mismatch:'):
        print(str(error))
        sys.exit(77)
    raise
assert 'app.ml.model' not in sys.modules
assert evidence['policy_sha256'] == revision['policy_sha256']
assert effective['tree'] == runner.load(Path(sys.argv[3]) / runner.MODEL_PROTOCOL)['tree']
print('Real context validated; no generation or fitting')
""", str(protocol), runner.digest(protocol), str(sources), str(POLICY)],
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True, text=True, timeout=60, check=False)
    if result.returncode == 77:
        pytest.skip(f"Real context requires pinned inherited runtime: {result.stdout.strip()}")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Real context validated; no generation or fitting" in result.stdout


def test_live_production_ml_guard_is_preserved(monkeypatch):
    monkeypatch.setitem(sys.modules, "app.ml.model", SimpleNamespace())
    with pytest.raises(RuntimeError, match="Live production ML was already imported"):
        runner.helpers()


def test_existing_output_and_symlinks_refused(tmp_path):
    with pytest.raises(ValueError, match="new"):
        runner.new_output(tmp_path)
    link = tmp_path / "link"
    link.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="Symlinks"):
        runner.new_output(link / "new")


def test_cli_requires_explicit_policy_source():
    with pytest.raises(SystemExit):
        runner.main(["predict", "--artifact-dir", "absent", "--input-json", "absent",
                     "--output-json", "absent"])
