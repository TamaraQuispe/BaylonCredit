"""Read-only V6 DEV gate: reconstruct saved events and plan CV, never fit or generate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.ml.features import FEATURE_NAMES  # noqa: E402
from app.ml.owner_pending_synthetic import (  # noqa: E402
    ROW_KEYS,
    validate_owner_pending_dataset,
)

INPUTS = {
    "APF3_OWNER_ANCHORS_V4.json":
        "81f858bc8827c88e41352745f65345a72d2b9d06361046bc86d3f07540806064",
    "APF3_OWNER_REVIEW_V5.json": "a72ea574fa2997d3477b0522c0044d590638957f0b5e553c31d97764df1a89a3",
    "APF3_PENDING_V6_DATA_PROTOCOL.json":
        "5f3cea3798b73d31cf8aea54dc6bc45341777871988f7ef68686d34287811431",
}
FROZEN_CODE = {
    "/app/scripts/prepare_pending_v6_data.py":
        "f718efd85668df2c34280787b01e1f5cbf67d26fa00885acf2dacbdf39b728d0",
    "/app/app/ml/owner_pending_synthetic.py":
        "1f122cea1fec04d416e31c62d36dea8882ff2b55b3956fa2969637776dca3e28",
    "/app/app/ml/owner_aligned_synthetic.py":
        "9fdb39dbcf33d507dc42876e53496841f79ec8c71a309ffbc8cc3b3224560a92",
    "/app/app/ml/synthetic.py":
        "b1c96b9a0a8135b74bf7d7115d0b08adbbd917e2bf7df01e9382c6ab91d29e78",
    "/app/app/ml/features.py":
        "ec22f6675b9eab61749a86a0ae613781503fab3905e80da08c73f7b8f568fcc1",
    "/app/app/ml/outcomes.py":
        "c385d1c91af185f305a7fc0429e0c937f5dc11df3ac5af515d810ce751ba59fc",
}
OUTER_SEED = 2026111801
INNER_SEED = 2026111802


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(directory):
    assert directory.is_dir()
    assert all(p.is_file() and not p.is_symlink() for p in directory.iterdir())
    return {p.name: sha(p) for p in sorted(directory.iterdir())}


def write_json(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


@contextmanager
def no_models_or_generation():
    """Fail closed on fitting, prediction or cohort generation, including indirect calls."""
    previous = sys.getprofile()

    def guard(frame, event, arg):
        if event == "call":
            name = frame.f_code.co_name
            if name in {
                "fit", "fit_transform", "fit_predict", "partial_fit", "predict",
                "predict_proba", "predict_log_proba", "decision_function",
            } or name.startswith("generate_owner_") or name == "generate_academic_dataset":
                raise RuntimeError(f"Forbidden in DEV audit: {name}")

    sys.setprofile(guard)
    try:
        yield
    finally:
        sys.setprofile(previous)


def grouped_splits(rows, indices, seed):
    # This is the only sklearn API used. No estimator is constructed or imported directly.
    from sklearn.model_selection import StratifiedGroupKFold

    indices = list(indices)
    assert len(indices) == len(set(indices)) and indices
    labels = [rows[i]["late_payment"] for i in indices]
    groups = [rows[i]["client_id"] for i in indices]
    assert set(labels) == {0, 1}
    rejected = []
    for count in (3, 2):
        try:
            assert len(set(groups)) >= count and min(Counter(labels).values()) >= count
            splits = []
            seen = []
            seen_clients = []
            cv = StratifiedGroupKFold(n_splits=count, shuffle=True, random_state=seed)
            iterator = cv.split([[0]] * len(indices), labels, groups)
            for fold, (train, validation) in enumerate(iterator):
                train = [indices[int(i)] for i in train]
                validation = [indices[int(i)] for i in validation]
                train_clients = sorted({rows[i]["client_id"] for i in train})
                validation_clients = sorted({rows[i]["client_id"] for i in validation})
                assert train and validation and set(train).isdisjoint(validation)
                assert set(train) | set(validation) == set(indices)
                assert set(train_clients).isdisjoint(validation_clients)
                train_counts = Counter(str(rows[i]["late_payment"]) for i in train)
                validation_counts = Counter(str(rows[i]["late_payment"]) for i in validation)
                assert set(train_counts) == set(validation_counts) == {"0", "1"}
                splits.append({
                    "fold": fold,
                    "train_indices": train,
                    "validation_indices": validation,
                    "train_clients": train_clients,
                    "validation_clients": validation_clients,
                    "train_size": len(train),
                    "validation_size": len(validation),
                    "train_class_counts": dict(train_counts),
                    "validation_class_counts": dict(validation_counts),
                    "train_minority": min(train_counts.values()),
                    "validation_minority": min(validation_counts.values()),
                })
                seen.extend(validation)
                seen_clients.extend(validation_clients)
            assert sorted(seen) == sorted(indices)
            assert len(seen_clients) == len(set(seen_clients)) == len(set(groups))
            return {"n_splits": count, "seed": seed, "rejected_feasibility": rejected,
                    "folds": splits, "every_row_once": True, "clients_disjoint": True}
        except (AssertionError, ValueError) as exc:
            rejected.append({"n_splits": count, "reason": str(exc) or "class/group feasibility"})
    raise ValueError(f"Grouped CV infeasible with fixed seed {seed}: {rejected}")


def plan_folds(known, study):
    outer = grouped_splits(known, range(len(known)), OUTER_SEED)
    inner = [
        {"outer_fold": fold["fold"],
         **grouped_splits(known, fold["train_indices"], INNER_SEED)}
        for fold in outer["folds"]
    ]
    full = grouped_splits(known, range(len(known)), INNER_SEED)
    client_fold = {client: f["fold"] for f in outer["folds"] for client in f["validation_clients"]}
    assert {r["client_id"] for r in study} == set(client_fold)
    unknown = []
    for index, row in enumerate(study):
        if row["late_payment"] is None:
            fold_id = client_fold[row["client_id"]]
            assert row["client_id"] not in outer["folds"][fold_id]["train_clients"]
            unknown.append({"study_index": index, "loan_id": row["loan_id"],
                            "client_id": row["client_id"], "outer_fold": fold_id})
    return {
        "index_basis": "Zero-based desarrollo_etiquetado.csv order; "
                       "unknown study_index uses desarrollo.csv",
        "known_row_ids": [r["loan_id"] for r in known],
        "outer": outer, "inner_sigmoid_by_outer_train": inner, "inner_sigmoid_full_train": full,
        "unknown_study_validation": unknown,
        "capacity_design": "Later OOF capacity competition includes known and unknown study rows "
                           "in their client's validation fold; "
                           "unknowns never train or score metrics. "
                           "No predictions or scores produced now.",
        "fallback_policy": "3 preferred, 2 only for class/group feasibility; "
                           "fixed seeds, no seed search",
    }


def faithful_csv(path, rows):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        assert len(reader.fieldnames) == len(ROW_KEYS) and set(reader.fieldnames) == ROW_KEYS
        actual = list(reader)
    expected = [{k: "" if v is None else str(v) for k, v in row.items()} for row in rows]
    assert actual == expected, f"CSV is not complete and faithful: {path.name}"
    assert len({row["loan_id"] for row in actual}) == len(actual)
    assert all(v != "" for row in actual for k, v in row.items() if k != "late_payment")


def quality_rows(study, known):
    result, duplicates = [], {}
    for scope, rows in (("study", study), ("known", known)):
        vectors = {}
        for name in FEATURE_NAMES:
            values = [row[name] for row in rows]
            assert all(type(v) in (int, float) and math.isfinite(v) for v in values)
            vectors[name] = values
            result.append({"scope": scope, "feature": name, "rows": len(rows),
                           "nulls": 0, "min": min(values), "max": max(values),
                           "nunique": len(set(values)), "constant": len(set(values)) == 1})
        duplicates[scope] = [[a, b] for n, a in enumerate(FEATURE_NAMES)
                             for b in FEATURE_NAMES[n + 1:] if vectors[a] == vectors[b]]
    return result, duplicates


def audit(source, sources, output):
    source, sources = source.resolve(strict=True), sources.resolve(strict=True)
    output = output.resolve()
    assert output.parent.is_dir() and not output.exists()
    assert not output.is_relative_to(source) and not output.is_relative_to(sources)
    before = inventory(source)
    protected = [BACKEND / p.removeprefix("/app/") for p in FROZEN_CODE]
    protected += [sources / name for name in INPUTS]
    protected += [BACKEND / "tests/fixtures" / name for name in INPUTS]
    protected += [Path(__file__), BACKEND / "tests/test_pending_v6_development_gate.py"]
    protected_before = {str(p): sha(p) for p in protected}
    assert len(before) == 12
    output.mkdir()
    # Persist the complete byte inventory before validation, even if a later hard check fails.
    write_json(output / "source-hashes-before.json", before)
    try:
        with no_models_or_generation():
            report, plan, quality = audit_contents(source, sources, before)
        after = inventory(source)
        assert before == after, "Source bytes/inventory changed"
        protected_after = {str(p): sha(p) for p in protected}
        assert protected_before == protected_after, "Code/docs/fixtures changed"
        report.update({"source_hashes_before": before, "source_hashes_after": after,
                       "protected_hashes_before": protected_before,
                       "protected_hashes_after": protected_after,
                       "source_unchanged": True, "technical_dev_gate_pass": True})
        write_json(output / "pliegues-planificados.json", plan)
        report["fold_plan_sha256"] = sha(output / "pliegues-planificados.json")
        with (output / "calidad-dev-v6.csv").open("x", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(quality[0]))
            writer.writeheader()
            writer.writerows(quality)
        write_json(output / "summaryauditoria-dev-v6.json", report)
        with (output / "README.md").open("x") as stream:
            stream.write(
                "# Auditoria DEV V6 sin modelos\n\n"
                "Estado: research_ready_with_declared_limits. Gate tecnico aprobado.\n"
                "545 filas study, 541 conocidas (454/87), 4 desconocidas, 24 clientes.\n"
                "Solo reconstruccion de mundos guardados y planificacion CV por cliente.\n"
                "Sin fitting, predicciones, scores, generacion de cohortes ni FINAL.\n"
                "El owner reviso 23 items muestrales V5, no todas las filas V6.\n"
                "No se declara coherencia empresarial global ni validacion predictiva real.\n"
                "Siguen sin medirse 75/25, corte 20:00, pool real, repago completo, "
                "estacionariedad, Beta y warmup. No se descartan features automaticamente.\n"
                "Listo para congelar por separado un protocolo de modelos, no para ejecutarlo.\n"
                "Indices y asignaciones unknown constan en pliegues-planificados.json.\n"
            )
        return report
    except Exception as exc:
        write_json(output / "audit-failure.json", {
            "technical_dev_gate_pass": False, "error": repr(exc),
            "source_hashes_before": before, "source_hashes_after": inventory(source),
        })
        raise


def audit_contents(source, sources, before):
    def load(name):
        return json.loads((source / name).read_bytes())

    manifest = load("manifest.json")
    assert manifest["files"] == {k: v for k, v in before.items() if k != "manifest.json"}
    expected_inventory = set(INPUTS) | {
        "manifest.json", "preparation_plan.json", "data_revision_report.json", "README.md",
        "development_audits.json", "desarrollo.csv", "desarrollo_etiquetado.csv",
        "PND6-D1_transactions.json", "PND6-D2_transactions.json",
    }
    assert set(before) == expected_inventory
    docs_fixtures = {}
    for name, digest in INPUTS.items():
        assert before[name] == digest
        docs_fixtures[name] = {
            "docs": sha(sources / name), "fixture": sha(BACKEND / "tests/fixtures" / name),
        }
        assert set(docs_fixtures[name].values()) == {digest}
    anchors, review, protocol = [load(name) for name in INPUTS]
    preparation, revision = load("preparation_plan.json"), load("data_revision_report.json")
    assert preparation["code_sha256"] == revision["code_sha256"] == FROZEN_CODE
    code = {}
    for original, digest in FROZEN_CODE.items():
        assert original.startswith("/app/")
        translated = BACKEND / original.removeprefix("/app/")
        assert sha(translated) == digest
        code[original] = {"backend_relative_path": str(translated.relative_to(BACKEND)),
                          "sha256": digest}
    assert preparation["input_sha256"] == revision["source_sha256"] == INPUTS
    assert preparation["candidates"] == protocol["development_candidates"]
    assert preparation["models_authorized"] is False and preparation["final_seed"] is None
    assert protocol["models_authorized"] is False and protocol["final_dataset"] is None
    assert revision["coherence_accepted"] is False
    assert revision["models_trained"] is False and revision["final_generated"] is False
    saved_audits, recomputed, study, rosters = load("development_audits.json"), [], [], []
    event_ids = set()
    partial = Counter()
    partial_by_phase = {phase: Counter() for phase in ("warmup", "study")}
    scenarios = {kind: Counter() for kind in ("planned", "observed")}
    for candidate in protocol["development_candidates"]:
        world = load(candidate["prefix"] + "_transactions.json")
        assert world["seed"] == candidate["seed"] and world["prefix"] == candidate["prefix"]
        roster = {c["client_id"] for c in world["clients"]}
        assert all(roster.isdisjoint(other) for other in rosters)
        rosters.append(roster)
        for collection, key in (("clients", "client_id"), ("loans", "loan_id"),
                                ("sales", "sale_id"), ("attempts", "attempt_id")):
            for item in world[collection]:
                assert item[key] not in event_ids
                event_ids.add(item[key])
        for loan in world["loans"]:
            for payment in loan["planned_payments"]:
                assert payment["payment_id"] not in event_ids
                event_ids.add(payment["payment_id"])
            partial["planned_two_payment_loans"] += len(loan["planned_payments"]) == 2
            partial["observed_two_payment_loans"] += len(loan["payments"]) == 2
            balance = Decimal(loan["amount"]) - sum(
                (Decimal(p["amount"]) for p in loan["payments"]), Decimal(0))
            partial["observed_settled_balance_zero"] += balance == 0
            partial["observed_part_paid_positive_balance"] += (
                Decimal(0) < balance < Decimal(loan["amount"]))
            phase_counts = partial_by_phase[loan["phase"]]
            phase_counts["planned_two_payment_loans"] += len(loan["planned_payments"]) == 2
            phase_counts["observed_two_payment_loans"] += len(loan["payments"]) == 2
            phase_counts["observed_settled_balance_zero"] += balance == 0
            phase_counts["observed_part_paid_positive_balance"] += (
                Decimal(0) < balance < Decimal(loan["amount"]))
            scenarios["planned"][loan["planned_scenario"]] += 1
        scenarios["observed"].update(row["scenario"] for row in world["rows"])
        rebuilt = {"replica_id": candidate["prefix"], **validate_owner_pending_dataset(
            world, anchors, protocol["simulation"], review, protocol)}
        recomputed.append(rebuilt)
        study.extend(r for r in world["rows"] if r["phase"] == "study")
    assert recomputed == saved_audits
    for original, rebuilt in zip(revision["replicas"], recomputed, strict=True):
        assert original == {k: rebuilt[k] for k in original}
    assert all(set(row) == ROW_KEYS for row in study)
    assert all(v is not None for row in study for k, v in row.items() if k != "late_payment")
    known = [r for r in study if r["late_payment"] is not None]
    counts = {"study_rows": len(study), "known_rows": len(known),
              "unknown_rows": len(study) - len(known),
              "class_0": sum(r["late_payment"] == 0 for r in known),
              "class_1": sum(r["late_payment"] == 1 for r in known)}
    assert counts == {"study_rows": 545, "known_rows": 541, "unknown_rows": 4,
                      "class_0": 454, "class_1": 87}
    assert counts == {k: revision[k] for k in counts}
    assert sum(map(len, rosters)) == 24
    assert revision["pending_grants"] == sum(a["pending_grants"] for a in recomputed) == 0
    assert revision["pending_policy_pass"] is True
    faithful_csv(source / "desarrollo.csv", study)
    faithful_csv(source / "desarrollo_etiquetado.csv", known)
    quality, duplicates = quality_rows(study, known)
    plan = plan_folds(known, study)
    return {
        "recorded_utc": datetime.now(UTC).isoformat(),
        "status": "research_ready_with_declared_limits", **counts, "clients": 24,
        "owner_all_rows_approved": False, "global_real_validation": False,
        "coherence_accepted": False, "models_trained": False, "final_generated": False,
        "predictive_model_direct_imports": [], "model_calls": 0, "fitting_calls": 0,
        "prediction_calls": 0, "cohort_generation_calls": 0,
        "execution_guard": "Python call profiler rejects fit/predict and owner cohort generation",
        "import_scope": "Only sklearn.model_selection.StratifiedGroupKFold directly; sklearn may "
                        "import internal estimator definitions. "
                        "app.models imports are ORM entities.",
        "runtime": {"python": sys.version, "scikit-learn": version("scikit-learn"),
                    "numpy": version("numpy")},
        "source_manifest_sha256": before["manifest.json"],
        "docs_fixtures_sha256": docs_fixtures, "source_code_provenance": code,
        "audit_script_sha256": sha(Path(__file__)),
        "audit_test_sha256": sha(BACKEND / "tests/test_pending_v6_development_gate.py"),
        "partial_and_settlement_counts_all_phases": dict(partial),
        "partial_and_settlement_counts_by_phase": partial_by_phase,
        "planned_vs_observed_scenario_counts_all_phases": scenarios,
        "settlement_rule_confirmed": "Any positive balance blocks, including not yet due; "
                                     "observed zero balance strictly before evaluation restores "
                                     "eligibility only, never automatic approval",
        "cv_summary": {
            "outer": [{k: v for k, v in fold.items() if not k.endswith("_indices")
                       and not k.endswith("_clients")} for fold in plan["outer"]["folds"]],
            "outer_n_splits": plan["outer"]["n_splits"],
            "inner_by_outer_n_splits": [s["n_splits"]
                                        for s in plan["inner_sigmoid_by_outer_train"]],
            "inner_full_n_splits": plan["inner_sigmoid_full_train"]["n_splits"],
        },
        "pending_grants": 0, "replica_audits": recomputed,
        "constant_features": {s: [q["feature"] for q in quality if q["scope"] == s
                                   and q["constant"]] for s in ("study", "known")},
        "exact_duplicate_features": duplicates, "features_dropped": [],
        "owner_review_scope": "23 intentional V5 sample items, not approval of all V6 rows",
        "unchanged_unknowns": ["75/25 scenario frequency", "hard 20:00 cutoff",
                               "real client pool", "full repayment/permanent loss",
                               "stationarity", "latent Beta distribution", "warmup length"],
        "limits": revision["limits"],
        "next_gate": "Ready to freeze a separately authorized model protocol with declared limits; "
                     "no business coherence or real predictive validation claimed",
    }, plan, quality


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True, help="Read-only docs directory")
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory only")
    args = parser.parse_args()
    result = audit(args.source, args.sources, args.output_dir)
    print(json.dumps({k: result[k] for k in (
        "status", "technical_dev_gate_pass", "study_rows", "known_rows", "unknown_rows",
        "class_0", "class_1", "clients", "source_manifest_sha256", "fold_plan_sha256",
    )}, indent=2))
