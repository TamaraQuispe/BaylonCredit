"""Freeze the prospective V6 model specification; never execute a model experiment."""

from __future__ import annotations

import argparse
import csv
import json
import platform
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from importlib.metadata import version
from itertools import product
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from scripts import audit_pending_v6_development as audit  # noqa: E402

MODEL_PROTOCOL = "APF3_PENDING_V6_MODEL_PROTOCOL.json"
AUDIT_FILES = {"calidad-dev-v6.csv", "pliegues-planificados.json", "README.md",
               "source-hashes-before.json", "summaryauditoria-dev-v6.json"}
EARLIER_SEEDS = {2026112101, 2026112102, 2026112103, 2026111501, 2026111502,
                 2026111701, 2026111702}
UNKNOWN_POLICY = (
    "Assign each unknown study row to its client's held-out outer fold. Fit on known training "
    "rows only; score both known and unknown held-out cases. Unknowns compete for daily "
    "capacity, but never enter supervised metrics or calibration."
)
QUEUE_SCOPE = (
    "Compute held-out daily queues per outer fold, replica and Lima date; folds have separate "
    "models, so do not pretend their capacity competition is one deployable full-cohort queue. "
    "Report this limitation."
)
RUNTIME = {"python": "3.12.14", "sklearn": "1.9.1", "numpy": "2.5.3",
           "scipy": "1.18.1", "joblib": "1.6.0", "threadpoolctl": "3.7.0"}
FROZEN_KEYS = {
    "development_manifest_sha256", "development_complete_csv_sha256",
    "development_labeled_csv_sha256", "development_gate_sha256", "fold_plan_sha256",
    "anchors_sha256", "owner_review_sha256", "data_protocol_sha256", "generator_sha256",
    "data_preparation_script_sha256",
}


def validate_protocol(protocol, expected_hashes):
    assert set(protocol["frozen_inputs"]) == FROZEN_KEYS
    assert protocol["frozen_inputs"] == expected_hashes, "Frozen input hash mismatch"
    assert all(re.fullmatch(r"[0-9a-f]{64}", h) for h in expected_hashes.values())
    assert protocol["stage"] == (
        "prospective_model_protocol_after_DEV_review_before_any_V6_fit_or_FINAL")
    assert protocol["current_action"] == (
        "Freeze protocol and verify inputs only. No V6 fit, final generation, artifact promotion, "
        "deployment or production change is performed in this step."
    )
    assert protocol["feature_names"] == list(audit.FEATURE_NAMES)
    assert len(protocol["feature_names"]) == 11
    assert protocol["feature_policy"]["constant_features"] == [
        "pending_overdue", "pending_current", "outstanding", "utilization", "overdue_rate"]
    assert protocol["preprocessing"] == ["SimpleImputer(strategy=median)", "StandardScaler"]
    assert protocol["cv"]["group"] == protocol["svm_calibration"]["group"] == "client_id"
    assert protocol["cv"]["outer_seed"] == audit.OUTER_SEED
    assert protocol["cv"]["inner_seed"] == audit.INNER_SEED
    assert protocol["cv"]["preferred_folds"] == 3 and protocol["cv"]["fallback_folds"] == 2
    assert protocol["cv"]["unknown_oof"] == UNKNOWN_POLICY
    assert protocol["cv"]["oof_queue_scope"] == QUEUE_SCOPE
    assert protocol["tree"] == {"max_depth": [2, 3, 4], "min_samples_leaf": [8, 16],
                                "class_weight": [None, "balanced"], "random_state": 42}
    assert protocol["svm"] == {"kernel": "linear", "C": [0.1, 1.0, 10.0],
                               "class_weight": [None, "balanced"], "probability": False,
                               "random_state": 42}
    assert protocol["svm_calibration"]["method"] == "sigmoid"
    assert protocol["svm_calibration"]["ensemble"] is False
    assert protocol["thresholds"] == [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
    assert protocol["candidate_count"] == {"tree": 12, "svm": 6, "thresholds_per_candidate": 7,
                                           "configuration_threshold_pairs": 126}
    final = protocol["final_replica"]
    assert final["seed"] not in EARLIER_SEEDS | {audit.OUTER_SEED, audit.INNER_SEED, 42}
    assert final["seed"] == 2026111901 and final["prefix"] == "PND6-T"
    assert final["status_at_protocol_freeze"] == "Not generated or inspected"
    assert protocol["runtime"] == RUNTIME
    assert protocol["review_policy"]["daily_cap"] == 5
    assert protocol["review_policy"]["minutes_per_case"] == 2
    assert list(protocol["illustrative_input"]["features"]) == list(audit.FEATURE_NAMES)
    # Plain configuration tuples only: no sklearn imports or estimator construction.
    tree = [("tree", depth, leaf, weight) for depth, leaf, weight in product(
        protocol["tree"]["max_depth"], protocol["tree"]["min_samples_leaf"],
        protocol["tree"]["class_weight"])]
    svm = [("svm", c, weight) for c, weight in product(
        protocol["svm"]["C"], protocol["svm"]["class_weight"])]
    pairs = [(configuration, threshold) for configuration in tree + svm
             for threshold in protocol["thresholds"]]
    assert len(tree) == 12 and len(svm) == 6 and len(pairs) == len(set(pairs)) == 126
    return pairs


def validate_saved_folds(plan, known, study):
    assert set(plan) == {"index_basis", "known_row_ids", "outer", "inner_sigmoid_by_outer_train",
                         "inner_sigmoid_full_train", "unknown_study_validation",
                         "capacity_design", "fallback_policy"}
    assert plan["index_basis"] == (
        "Zero-based desarrollo_etiquetado.csv order; unknown study_index uses desarrollo.csv")
    assert plan["known_row_ids"] == [r["loan_id"] for r in known]
    assert len(set(plan["known_row_ids"])) == len(known)

    def validate_split(split, indices, seed, nested=False):
        keys = {"n_splits", "seed", "rejected_feasibility", "folds", "every_row_once",
                "clients_disjoint"} | ({"outer_fold"} if nested else set())
        assert set(split) == keys
        assert split["n_splits"] == len(split["folds"]) == 3
        assert split["seed"] == seed and split["rejected_feasibility"] == []
        assert split["every_row_once"] is True and split["clients_disjoint"] is True
        seen, seen_clients = [], []
        for number, fold in enumerate(split["folds"]):
            assert set(fold) == {"fold", "train_indices", "validation_indices", "train_clients",
                                 "validation_clients", "train_size", "validation_size",
                                 "train_class_counts", "validation_class_counts",
                                 "train_minority", "validation_minority"}
            assert fold["fold"] == number
            train, validation = fold["train_indices"], fold["validation_indices"]
            assert len(train) == len(set(train)) and len(validation) == len(set(validation))
            assert set(train).isdisjoint(validation)
            assert set(train) | set(validation) == set(indices)
            for side in ("train", "validation"):
                subset = fold[side + "_indices"]
                assert subset and all(type(i) is int and 0 <= i < len(known) for i in subset)
                clients = sorted({known[i]["client_id"] for i in subset})
                counts = dict(Counter(str(known[i]["late_payment"]) for i in subset))
                assert set(counts) == {"0", "1"}
                assert fold[side + "_clients"] == clients
                assert fold[side + "_size"] == len(subset)
                assert fold[side + "_class_counts"] == counts
                assert fold[side + "_minority"] == min(counts.values())
            assert set(fold["train_clients"]).isdisjoint(fold["validation_clients"])
            seen.extend(validation)
            seen_clients.extend(fold["validation_clients"])
        assert sorted(seen) == sorted(indices)
        assert len(seen_clients) == len(set(seen_clients))

    validate_split(plan["outer"], range(len(known)), audit.OUTER_SEED)
    inner = plan["inner_sigmoid_by_outer_train"]
    assert len(inner) == 3
    for number, split in enumerate(inner):
        assert split["outer_fold"] == number
        validate_split(split, plan["outer"]["folds"][number]["train_indices"],
                       audit.INNER_SEED, nested=True)
    validate_split(plan["inner_sigmoid_full_train"], range(len(known)), audit.INNER_SEED)
    client_fold = {c: f["fold"] for f in plan["outer"]["folds"] for c in f["validation_clients"]}
    assert {r["client_id"] for r in study} == set(client_fold)
    expected = [{"study_index": i, "loan_id": r["loan_id"], "client_id": r["client_id"],
                 "outer_fold": client_fold[r["client_id"]]}
                for i, r in enumerate(study) if r["late_payment"] is None]
    assert plan["unknown_study_validation"] == expected
    return {"outer_folds": 3, "inner_by_outer": [3, 3, 3], "inner_full": 3,
            "validated_partitions": 15, "known_coverage": len(known),
            "unknown_assignments": len(expected), "client_disjoint": True}


def read_rows(path):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        assert len(reader.fieldnames) == len(audit.ROW_KEYS)
        assert set(reader.fieldnames) == audit.ROW_KEYS
        rows = list(reader)
    for row in rows:
        assert None not in row and all(isinstance(v, str) for v in row.values())
        assert all(v != "" for k, v in row.items() if k != "late_payment")
        row["late_payment"] = None if row["late_payment"] == "" else int(row["late_payment"])
        assert row["late_payment"] in (None, 0, 1)
        for name in audit.FEATURE_NAMES:
            row[name] = float(row[name])
    assert len({r["loan_id"] for r in rows}) == len(rows)
    return rows


@audit.no_models_or_generation()
def freeze(source, saved_audit, sources, output):
    if not __debug__:
        raise RuntimeError("Validation requires Python assertions enabled")
    source, saved_audit, sources = [p.resolve(strict=True) for p in (source, saved_audit, sources)]
    output = output.resolve()
    assert output.parent.is_dir() and not output.exists(), "Output must be a new directory"
    assert all(not output.is_relative_to(p) for p in (source, saved_audit, sources, BACKEND))
    before, audit_before = audit.inventory(source), audit.inventory(saved_audit)
    assert set(audit_before) == AUDIT_FILES
    expected_names = set(audit.INPUTS) | {
        "manifest.json", "preparation_plan.json", "data_revision_report.json", "README.md",
        "development_audits.json", "desarrollo.csv", "desarrollo_etiquetado.csv",
        "PND6-D1_transactions.json", "PND6-D2_transactions.json"}
    assert set(before) == expected_names and len(before) == 12
    protected = [sources / n for n in (*audit.INPUTS, MODEL_PROTOCOL)]
    protected += [BACKEND / p.removeprefix("/app/") for p in audit.FROZEN_CODE]
    protected += [Path(audit.__file__), Path(__file__),
                  BACKEND / "tests/test_pending_v6_model_protocol.py",
                  BACKEND / "tests/test_pending_v6_development_gate.py"]
    protected_before = {str(p): audit.sha(p) for p in protected}

    def load(directory, name):
        return json.loads((directory / name).read_bytes())

    protocol = load(sources, MODEL_PROTOCOL)
    manifest = load(source, "manifest.json")
    assert manifest["files"] == {n: h for n, h in before.items() if n != "manifest.json"}
    preparation = load(source, "preparation_plan.json")
    revision = load(source, "data_revision_report.json")
    data_protocol = load(source, "APF3_PENDING_V6_DATA_PROTOCOL.json")
    gate = load(saved_audit, "summaryauditoria-dev-v6.json")
    plan = load(saved_audit, "pliegues-planificados.json")
    expected_hashes = dict(zip(
        ["development_manifest_sha256", "development_complete_csv_sha256",
         "development_labeled_csv_sha256", "development_gate_sha256", "fold_plan_sha256",
         "anchors_sha256", "owner_review_sha256", "data_protocol_sha256", "generator_sha256",
         "data_preparation_script_sha256"],
        [before["manifest.json"], before["desarrollo.csv"], before["desarrollo_etiquetado.csv"],
         audit_before["summaryauditoria-dev-v6.json"], audit_before["pliegues-planificados.json"],
         *[before[n] for n in audit.INPUTS],
         audit.FROZEN_CODE["/app/app/ml/owner_pending_synthetic.py"],
         audit.FROZEN_CODE["/app/scripts/prepare_pending_v6_data.py"]], strict=True))
    pairs = validate_protocol(protocol, expected_hashes)
    for name, digest in audit.INPUTS.items():
        assert before[name] == audit.sha(sources / name) == digest
    assert preparation["code_sha256"] == revision["code_sha256"] == audit.FROZEN_CODE
    provenance = {}
    for original, digest in audit.FROZEN_CODE.items():
        assert original.startswith("/app/")
        actual = BACKEND / original.removeprefix("/app/")
        assert audit.sha(actual) == digest
        provenance[original] = {"actual_path": str(actual), "sha256": digest}
    assert gate["source_code_provenance"] == {
        original: {"backend_relative_path": original.removeprefix("/app/"), "sha256": digest}
        for original, digest in audit.FROZEN_CODE.items()}
    assert preparation["input_sha256"] == revision["source_sha256"] == audit.INPUTS
    assert preparation["models_authorized"] is data_protocol["models_authorized"] is False
    assert preparation["final_seed"] is data_protocol["final_seed"] is None
    assert data_protocol["selection_protocol"] is data_protocol["final_dataset"] is None
    assert preparation["candidates"] == data_protocol["development_candidates"]
    assert protocol["final_replica"]["seed"] not in {c["seed"] for c in preparation["candidates"]}
    assert revision["coherence_accepted"] is False
    assert revision["models_trained"] is revision["final_generated"] is False
    assert gate["status"] == "research_ready_with_declared_limits"
    assert gate["technical_dev_gate_pass"] is gate["source_unchanged"] is True
    for key in ("coherence_accepted", "owner_all_rows_approved", "global_real_validation",
                "models_trained", "final_generated"):
        assert gate[key] is False
    for key in ("model_calls", "fitting_calls", "prediction_calls", "cohort_generation_calls"):
        assert gate[key] == 0
    assert gate["source_hashes_before"] == gate["source_hashes_after"] == before
    assert load(saved_audit, "source-hashes-before.json") == before
    assert gate["source_manifest_sha256"] == before["manifest.json"]
    assert gate["fold_plan_sha256"] == audit_before["pliegues-planificados.json"]
    assert gate["audit_script_sha256"] == audit.sha(Path(audit.__file__))
    assert gate["audit_test_sha256"] == audit.sha(
        BACKEND / "tests/test_pending_v6_development_gate.py")
    study = read_rows(source / "desarrollo.csv")
    known = read_rows(source / "desarrollo_etiquetado.csv")
    assert known == [r for r in study if r["late_payment"] is not None]
    counts = {"study_rows": len(study), "known_rows": len(known),
              "unknown_rows": len(study) - len(known),
              "class_0": sum(r["late_payment"] == 0 for r in known),
              "class_1": sum(r["late_payment"] == 1 for r in known),
              "clients": len({r["client_id"] for r in study})}
    assert counts == {"study_rows": 545, "known_rows": 541, "unknown_rows": 4,
                      "class_0": 454, "class_1": 87, "clients": 24}
    assert counts == {k: gate[k] for k in counts}
    development = {**counts, "labeled_rows": counts["known_rows"]}
    assert all(protocol["development"][k] == development[k] for k in
               ("study_rows", "labeled_rows", "unknown_rows", "class_0", "class_1", "clients"))
    prefix = protocol["final_replica"]["prefix"]
    assert all(not r[k].startswith(prefix) for r in study for k in ("loan_id", "client_id"))
    assert {r["replica_id"] for r in study} == set(protocol["development"]["replicas"])
    folds = validate_saved_folds(plan, known, study)
    quality, duplicates = audit.quality_rows(study, known)
    with (saved_audit / "calidad-dev-v6.csv").open(newline="") as stream:
        saved_quality = list(csv.DictReader(stream))
    assert len(saved_quality) == len(quality) == 22
    for saved, actual in zip(saved_quality, quality, strict=True):
        assert set(saved) == set(actual)
        for key, value in actual.items():
            if type(value) in (int, float):
                assert float(saved[key]) == value
            else:
                assert saved[key] == str(value)
    constants = {scope: [q["feature"] for q in quality if q["scope"] == scope and q["constant"]]
                 for scope in ("study", "known")}
    assert constants == gate["constant_features"]
    assert all(names == protocol["feature_policy"]["constant_features"]
               for names in constants.values())
    assert duplicates == gate["exact_duplicate_features"]
    assert all(["completed_sales", "paid_credits"] in pairs for pairs in duplicates.values())
    assert gate["features_dropped"] == []
    illustrative = protocol["illustrative_input"]["features"]
    illustrative_duplicate = any(all(r[n] == illustrative[n] for n in audit.FEATURE_NAMES)
                                for r in study)
    runtime = {"python": platform.python_version(), **{
        key: version("scikit-learn" if key == "sklearn" else key)
        for key in RUNTIME if key != "python"}}
    assert runtime == protocol["runtime"], "Runtime version mismatch"
    assert before == audit.inventory(source) and audit_before == audit.inventory(saved_audit)
    assert protected_before == {str(p): audit.sha(p) for p in protected}
    output.mkdir()
    copies = {MODEL_PROTOCOL: sources / MODEL_PROTOCOL,
              **{n: source / n for n in audit.INPUTS},
              **{n: saved_audit / n for n in ("pliegues-planificados.json",
                  "summaryauditoria-dev-v6.json", "calidad-dev-v6.csv")}}
    for name, original in copies.items():
        with (output / name).open("xb") as stream:
            stream.write(original.read_bytes())
        assert audit.sha(output / name) == audit.sha(original)
    report = {
        "frozen_utc": datetime.now(UTC).isoformat(),
        "status": "research_ready_with_declared_limits", "technical_dev_gate_pass": True,
        "model_experiment_specification_ready": True, "model_fit_performed": False,
        "final_generated": False, "models_authorized": False, "owner_approved_all_data": False,
        "business_approval": False, "coherence_accepted": False,
        "model_calls": 0, "fitting_calls": 0, "prediction_calls": 0, "cohort_generation_calls": 0,
        "model_protocol_sha256": audit.sha(sources / MODEL_PROTOCOL),
        "protocol": protocol, "runtime_probe": runtime, "counts": counts, "fold_audit": folds,
        "constant_features": constants, "exact_duplicate_features": duplicates,
        "features_retained": list(audit.FEATURE_NAMES), "features_dropped": [],
        "illustrative_input_duplicate_in_dev": illustrative_duplicate,
        "illustrative_input_final_distinctness": "Not checked: FINAL does not exist",
        "illustrative_inference_performed": False,
        "configuration_threshold_tuples": pairs, "frozen_inputs_verified": expected_hashes,
        "source_code_provenance": provenance,
        "source_paths": {"development": str(source), "saved_audit": str(saved_audit),
                         "docs": str(sources), "backend": str(BACKEND)},
        "source_hashes_before": before, "audit_hashes_before": audit_before,
        "protected_hashes_before": protected_before,
        "checklist": {k: True for k in (
            "ten_frozen_inputs_match", "manifest_exact_eleven_members", "saved_folds_validated",
            "unknowns_held_out_by_client", "fold_specific_future_capacity_declared",
            "eleven_feature_contract_no_metadata_leak", "quality_csv_recomputed",
            "grid_12_tree_6_svm_126_pairs", "final_seed_and_prefix_disjoint",
            "historical_data_protocol_preserved", "runtime_versions_match")},
        "validation_methods": "SHA256 raw bytes; CSV contract/counts/quality; saved index/client "
                              "validation without CV recreation; importlib.metadata runtime probe",
        "execution_guard": "audit.no_models_or_generation profiler around freeze and CLI; "
                           "no estimator imports, construction, joblib loading or model runner",
        "authorization": "User authorized snapshot and audit only; research technical readiness, "
                         "not training, FINAL, commercial use, promotion or deployment",
        "current_action": protocol["current_action"],
    }
    report["source_hashes_after"] = audit.inventory(source)
    report["audit_hashes_after"] = audit.inventory(saved_audit)
    report["protected_hashes_after"] = {str(p): audit.sha(p) for p in protected}
    assert report["source_hashes_after"] == before
    assert report["audit_hashes_after"] == audit_before
    assert report["protected_hashes_after"] == protected_before
    audit.write_json(output / "preparation_plan.json", report)
    with (output / "README.md").open("x") as stream:
        stream.write(
            "# Frozen prospective V6 model protocol\n\n"
            "Current user-authorized action: snapshot and audit only. No fit or generation.\n"
            "Technical research gate passed with declared limits; models_authorized=false.\n"
            "The future model runner is NOT implemented and cannot execute this protocol yet.\n"
            "This is not the later freeze_before_final gate: OOF search, winners and refitted\n"
            "artifacts do not exist here. No FINAL dataset or model artifact is generated.\n"
            "Historical data protocol is unchanged; modeling is a separate prospective spec.\n"
            "Owner review is a V5 sample, not approval of all V6 data or business authorization.\n"
            "Unknown OOF rows belong to their client's fold and future fold-specific capacity,\n"
            "never training, calibration or supervised metrics. Cross-fold queues are not pooled.\n"
            "Only protocols, review, anchors, folds, audit summary and quality are copied.\n"
            "DEV (12 files) and saved audit (5 files) remain read-only and hash-verified.\n"
            "Repeat execution requires a NEW output directory; overwrites are refused.\n")
    audit.write_json(output / "manifest.json", {"files": audit.inventory(output)})
    return report


@audit.no_models_or_generation()
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--audit-source", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    report = freeze(args.source, args.audit_source, args.sources, args.output_dir)
    print(json.dumps({k: report[k] for k in ("status", "model_protocol_sha256", "counts",
        "fold_audit", "model_fit_performed", "final_generated",
        "model_experiment_specification_ready")},
        indent=2))


if __name__ == "__main__":
    main()
