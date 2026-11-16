"""Self-contained split/guard tests; optional real-data read-only integration."""

import csv
import os
from pathlib import Path

import pytest

from scripts import audit_pending_v6_development as gate


def tiny_rows(groups=12):
    return [{"client_id": f"C{g}", "loan_id": f"L{g}-{label}", "late_payment": label}
            for g in range(groups) for label in (0, 1)]


def test_grouped_nested_plan_unknowns_and_determinism():
    rows = tiny_rows()
    study = rows + [{"client_id": "C0", "loan_id": "U0", "late_payment": None}]
    with gate.no_models_or_generation():
        plan = gate.plan_folds(rows, study)
        assert plan == gate.plan_folds(rows, study)
    assert plan["outer"]["n_splits"] == 3
    assert plan["inner_sigmoid_full_train"]["n_splits"] == 3
    unknown = plan["unknown_study_validation"][0]
    fold = plan["outer"]["folds"][unknown["outer_fold"]]
    assert "C0" in fold["validation_clients"] and "C0" not in fold["train_clients"]
    for splits in [plan["outer"], plan["inner_sigmoid_full_train"],
                   *plan["inner_sigmoid_by_outer_train"]]:
        assert splits["every_row_once"] and splits["clients_disjoint"]
        for f in splits["folds"]:
            assert set(f["train_class_counts"]) == set(f["validation_class_counts"]) == {"0", "1"}
            assert set(f["train_clients"]).isdisjoint(f["validation_clients"])


def test_fallback_only_feasibility_and_failure():
    rows = tiny_rows(2)
    split = gate.grouped_splits(rows, range(len(rows)), gate.OUTER_SEED)
    assert split["n_splits"] == 2 and len(split["rejected_feasibility"]) == 1
    with pytest.raises(ValueError, match="infeasible"):
        gate.grouped_splits(tiny_rows(1), range(2), gate.OUTER_SEED)
    with pytest.raises(AssertionError):
        gate.grouped_splits([r for r in rows if r["late_payment"] == 0], range(2), gate.OUTER_SEED)


def test_unknown_without_known_client_fails():
    rows = tiny_rows()
    with pytest.raises(AssertionError):
        gate.plan_folds(rows, rows + [{"client_id": "NEW", "loan_id": "U", "late_payment": None}])


@pytest.mark.parametrize("method", ["fit", "predict", "predict_proba", "fit_transform",
                                   "generate_owner_pending_dataset", "generate_academic_dataset"])
def test_no_model_or_generation_guard(method):
    # Named spies without importing or constructing any estimator.
    namespace = {}
    exec(f"def {method}():\n    raise AssertionError('body must never execute')", namespace)
    with pytest.raises(RuntimeError, match="Forbidden"), gate.no_models_or_generation():
        namespace[method]()


def test_quality_constants_duplicates_no_drop():
    rows = [{name: 0 for name in gate.FEATURE_NAMES} for _ in range(4)]
    rows[0][gate.FEATURE_NAMES[0]] = 1
    quality, duplicates = gate.quality_rows(rows, rows)
    assert len(quality) == 2 * len(gate.FEATURE_NAMES)
    assert len([q for q in quality if q["constant"]]) == 2 * (len(gate.FEATURE_NAMES) - 1)
    assert [gate.FEATURE_NAMES[1], gate.FEATURE_NAMES[2]] in duplicates["study"]
    rows[0][gate.FEATURE_NAMES[0]] = float("inf")
    with pytest.raises(AssertionError):
        gate.quality_rows(rows, rows)


def test_csv_complete_faithful_and_tamper(tmp_path):
    rows = [{k: 0 for k in gate.ROW_KEYS}]
    rows[0]["late_payment"] = None
    path = tmp_path / "rows.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=sorted(gate.ROW_KEYS))
        writer.writeheader()
        writer.writerows(rows)
    gate.faithful_csv(path, rows)
    with pytest.raises(AssertionError):
        gate.faithful_csv(path, rows * 2)
    rows[0]["outstanding"] = 1
    with pytest.raises(AssertionError):
        gate.faithful_csv(path, rows)


def test_real_read_only_audit_if_requested(tmp_path, monkeypatch):
    source = os.environ.get("PENDING_V6_AUDIT_SOURCE")
    if not source:
        pytest.skip("Set PENDING_V6_AUDIT_SOURCE for saved-world integration; never generates data")
    from app.ml import owner_pending_synthetic as pending

    def forbidden(*args, **kwargs):
        pytest.fail("No future cohort generation or generator decision calls allowed")

    for name in ("generate_owner_pending_dataset", "_refusal", "_outcome"):
        monkeypatch.setattr(pending, name, forbidden)
    sources = Path(os.environ.get("PENDING_V6_AUDIT_DOCS", str(gate.BACKEND.parent / "docs")))
    before = gate.inventory(Path(source))
    report = gate.audit(Path(source), sources, tmp_path / "audit")
    assert report["technical_dev_gate_pass"] and report["source_unchanged"]
    assert not report["owner_all_rows_approved"] and not report["global_real_validation"]
    assert report["fitting_calls"] == report["prediction_calls"] == 0
    assert gate.inventory(Path(source)) == before
