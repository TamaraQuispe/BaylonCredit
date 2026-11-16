"""Independent, prospective V6 Final orchestration. Import never generates or fits.

Only trusted local codepacks and joblib publishers are supported. Digests detect
changed evidence, not an attacker who can replace both evidence and manifests.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import json
import math
import sys
import types
from collections import Counter
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

VERSION = "academic-owner-pending-v6"
REVISION = "v6-final-r1"
DISPLAY_NAME = "V6 Final"
MODEL_PROTOCOL = "APF3_PENDING_V6_MODEL_PROTOCOL.json"
MODEL_PROTOCOL_SHA256 = "eb7fcd39f69be0115895cbb43b6d84e4488535646108bd6f21381d0fb1607923"
DEV = [{"seed": 2026112601, "prefix": "PND6F-R1-D1"},
       {"seed": 2026112602, "prefix": "PND6F-R1-D2"}]
FINAL = {"seed": 2026112603, "prefix": "PND6F-R1-T"}
CV = {"outer_seed": 2026112604, "inner_seed": 2026112605, "folds": 3}
REQUIRED_POLICIES = (
    "block_any_pending_balance", "require_paid_credit_history",
    "unknown_history_requires_owner_review", "debt_precedes_history",
    "blocked_or_manual_excluded_from_model_metrics",
)
SOURCES = {
    "APF3_OWNER_ANCHORS_V4.json":
        "81f858bc8827c88e41352745f65345a72d2b9d06361046bc86d3f07540806064",
    "APF3_OWNER_REVIEW_V5.json":
        "a72ea574fa2997d3477b0522c0044d590638957f0b5e553c31d97764df1a89a3",
    "APF3_PENDING_V6_DATA_PROTOCOL.json":
        "5f3cea3798b73d31cf8aea54dc6bc45341777871988f7ef68686d34287811431",
}
BACKEND = (Path(__file__).absolute().parents[1]
           if Path(__file__).parent.name == "scripts" else Path("/app"))
CODE_ROOT = (Path("/app") if Path("/app/scripts/academic_credit_pending_v6.py").is_file()
             else BACKEND)
FEATURE_NAMES = ["completed_sales", "paid_credits", "paid_late", "pending_overdue",
                 "pending_current", "outstanding", "utilization", "requested_ratio",
                 "tenure_days", "punctuality_rate", "overdue_rate"]
IDENTITY = {"version": VERSION, "revision_id": REVISION, "display_name": DISPLAY_NAME,
            "origen": "simulado", "research_only": True, "business_approval": False}


def checked_path(path, *, directory=False):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError(f"Symlinks are forbidden: {path}")
    if not (path.is_dir() if directory else path.is_file()):
        raise ValueError(f"Expected regular {'directory' if directory else 'file'}: {path}")
    return path.resolve()


def new_output(path, protected=(), *, directory=True):
    path = Path(path).absolute()
    checked_path(path.parent, directory=True)
    roots = [BACKEND.parent if BACKEND != Path("/app") else BACKEND,
             CODE_ROOT, Path("/revision"), *map(Path, protected)]
    if path.exists() or path.is_symlink():
        raise ValueError("Output must be new; evidence is never overwritten")
    path = path.resolve()
    if any(path.is_relative_to(root.resolve()) for root in roots):
        raise ValueError("Output is inside a protected root")
    if directory:
        path.mkdir()
    return path


def digest(path):
    return sha256(checked_path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(checked_path(path).read_bytes())


def write(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def copy(source, target):
    with Path(target).open("xb") as stream:
        stream.write(checked_path(source).read_bytes())


def inventory(directory):
    return {p.name: digest(p) for p in sorted(checked_path(directory, directory=True).iterdir())}


def verify(directory, expected):
    for name, value in expected.items():
        if Path(name).name != name or digest(Path(directory) / name) != value:
            raise ValueError(f"SHA256 mismatch: {name}")


def failure(output, stage, error):
    write(output / "failure.json", {**IDENTITY, "stage": stage, "error": repr(error),
                                    "retry": False, "no_reseed": True})


def helpers():
    """Use frozen helpers without executing the production app.ml initializer."""
    if "app.ml.model" in sys.modules:
        raise RuntimeError("Live production ML was already imported; use an isolated process")
    if "app.ml" not in sys.modules:
        package = types.ModuleType("app.ml")
        package.__path__ = [str(CODE_ROOT / "app/ml")]
        sys.modules["app.ml"] = package
    if str(CODE_ROOT) not in sys.path:
        sys.path.insert(0, str(CODE_ROOT))
    from app.ml import owner_pending_synthetic as simulator
    from scripts import academic_credit_pending_v6 as old

    if Path(old.__file__).resolve().parent != (CODE_ROOT / "scripts").resolve():
        raise ValueError("Old runner is not from the frozen code root")
    return old, simulator


def load_policy(path):
    path = checked_path(path)
    spec = importlib.util.spec_from_file_location("v6_final_pure_policy", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "pre_model_decision", None)):
        raise ValueError("Policy must export pre_model_decision")
    return module


def validate_numeric(data):
    features = data.get("features", data) if isinstance(data, dict) else None
    if (not isinstance(features, dict) or set(features) != set(FEATURE_NAMES)
            or ("features" in data and set(data) != {"features"})):
        raise ValueError("Expected exactly eleven features, no label")
    for name, value in features.items():
        if value is None:
            continue
        try:
            valid = type(value) in (int, float) and math.isfinite(value) and value >= 0
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError(f"Invalid numeric feature: {name}")
        if name in FEATURE_NAMES[:5] + ["tenure_days"] and int(value) != value:
            raise ValueError(f"Integral feature required: {name}")
        if name in ("utilization", "requested_ratio", "punctuality_rate", "overdue_rate"):
            if value > 1 or (name == "requested_ratio" and value == 0):
                raise ValueError(f"Invalid ratio: {name}")
    return features


def gate(data, policy):
    features = validate_numeric(data)
    decision = policy.pre_model_decision(features)
    if decision is None:
        old, _ = helpers()
        old.validate_features(features)
    return features, decision


def context(protocol_path, protocol_sha256, sources, policy_path):
    if not __debug__:
        raise RuntimeError("Assertions must be enabled for inherited audits")
    protocol_path = checked_path(protocol_path)
    sources = checked_path(sources, directory=True)
    if digest(protocol_path) != protocol_sha256:
        raise ValueError("Revision protocol SHA256 mismatch")
    revision = load(protocol_path)
    required = {"revision_id": REVISION, "display_name": DISPLAY_NAME, "version": VERSION,
                "development_replicas": DEV, "final_replica": FINAL, "cv": CV,
                "inherited_model_protocol_filename": MODEL_PROTOCOL,
                "inherited_model_protocol_sha256": MODEL_PROTOCOL_SHA256,
                "source_sha256": SOURCES, "no_reseed": True}
    for key, expected in required.items():
        if revision.get(key) != expected:
            raise ValueError(f"Revision protocol mismatch: {key}")
    if (not isinstance(revision.get("authorized_user_request"), str)
            or not revision["authorized_user_request"].strip()
            or not isinstance(revision.get("policies"), dict) or not revision["policies"]):
        raise ValueError("Explicit authorization and declared policies required")
    for name in REQUIRED_POLICIES:
        if revision["policies"].get(name) is not True:
            raise ValueError(f"Revision policy must be true: {name}")
    policy_sha256 = revision.get("policy_sha256")
    if (not isinstance(policy_sha256, str) or len(policy_sha256) != 64
            or any(c not in "0123456789abcdef" for c in policy_sha256)):
        raise ValueError("Revision must declare policy_sha256 as a lowercase SHA256 digest")
    if digest(policy_path) != policy_sha256:
        raise ValueError("Policy source SHA256 differs from revision policy_sha256")
    verify(sources, {**SOURCES, MODEL_PROTOCOL: MODEL_PROTOCOL_SHA256})
    inherited = load(sources / MODEL_PROTOCOL)
    old, simulator = helpers()
    if revision.get("runtime") != inherited["runtime"]:
        raise ValueError("Revision must retain inherited runtime")
    runtime = old.validate_runtime(revision["runtime"])
    for original, expected in old.freeze.audit.FROZEN_CODE.items():
        if digest(CODE_ROOT / original.removeprefix("/app/")) != expected:
            raise ValueError(f"Frozen generator dependency changed: {original}")
    paths = [Path(__file__), checked_path(policy_path), Path(old.__file__),
             Path(old.freeze.__file__), Path(old.freeze.audit.__file__), Path(old.v4.__file__),
             CODE_ROOT / "scripts/academic_credit_grouped_cv.py",
             *[CODE_ROOT / name.removeprefix("/app/") for name in old.freeze.audit.FROZEN_CODE]]
    evidence = {"protocol_sha256": protocol_sha256,
                "source_sha256": {**SOURCES, MODEL_PROTOCOL: MODEL_PROTOCOL_SHA256},
                "code_sha256": {str(p.absolute()): digest(p) for p in paths},
                "policy_sha256": policy_sha256, "runtime": runtime}
    effective = deepcopy(inherited)
    effective["revision_overrides"] = revision
    effective["cv"].update(CV)
    effective["cv"].update({"preferred_folds": 3, "fallback_folds": None,
                             "fold_source": "Fresh eligible-only planned_folds.json",
                             "fallback_policy": "Exactly three folds; stop, never reseed"})
    effective["final_replica"] = FINAL
    effective["development"] = {"replicas": [r["prefix"] for r in DEV],
                                  "row_scope": "Policy-eligible granted study rows only"}
    return revision, effective, evidence, old, simulator


def route(world, policy, simulator):
    clients = {c["client_id"]: c for c in world["clients"]}
    rows = {r["loan_id"]: r for r in world["rows"]}
    ledger, eligible = [], []
    for attempt in world["attempts"]:
        if attempt["phase"] != "study":
            continue
        at = datetime.fromisoformat(attempt["evaluated_at"])
        prior = [{**loan, "payments": [p for p in loan["payments"]
                                       if datetime.fromisoformat(p["at"]) < at]}
                 for loan in world["loans"] if datetime.fromisoformat(loan["evaluated_at"]) < at]
        sales = [s for s in world["sales"] if datetime.fromisoformat(s["at"]) < at]
        features = simulator._snapshot(clients[attempt["client_id"]], prior, sales, at,
                                       Decimal(attempt["requested_amount"]))
        features, decision = gate(features, policy)
        if attempt["granted"]:
            row = rows[attempt["loan_id"]]
            if any(row[n] != features[n] for n in FEATURE_NAMES):
                raise ValueError("Reconstructed attempt features differ from granted row")
            if row["late_payment"] is not None and type(row["late_payment"]) is not int:
                raise ValueError("Invalid target type")
            if row["late_payment"] not in (None, 0, 1):
                raise ValueError("Invalid target")
        outcome = (decision["decision"] if decision else "model_eligible" if attempt["granted"]
                   else "simulator_refused_model_eligible")
        if decision is None and attempt["granted"]:
            eligible.append(row)
        ledger.append({**{k: attempt[k] for k in (
            "attempt_id", "loan_id", "client_id", "replica_id", "evaluated_at", "granted",
            "refusal_reason")}, "features": features, "decision": outcome,
            "policy_decision": decision, "model_eligible": decision is None,
            "model_called": False, "probability": None})
    return eligible, ledger


def plan_folds(old, known, study):
    def split(indices, seed):
        result = old.freeze.audit.grouped_splits(known, indices, seed)
        if result["n_splits"] != 3:
            raise ValueError("Exactly three feasible folds required; no fallback or reseed")
        return result

    outer = split(range(len(known)), CV["outer_seed"])
    inner = [split(f["train_indices"], CV["inner_seed"]) for f in outer["folds"]]
    full = split(range(len(known)), CV["inner_seed"])
    assignments = {c: f["fold"] for f in outer["folds"] for c in f["validation_clients"]}
    if set(assignments) != {r["client_id"] for r in study}:
        raise ValueError("Unknown clients must have known-label grouped validation coverage")
    return {"outer": outer, "inner_sigmoid_by_outer_train": inner,
            "inner_sigmoid_full_train": full, "known_row_ids": [r["loan_id"] for r in known],
            "index_basis": ("Zero-based development_known.csv; "
                            "study indices use development_eligible.csv"),
            "unknown_study_validation": [
                {"study_index": i, "loan_id": r["loan_id"], "client_id": r["client_id"],
                 "outer_fold": assignments[r["client_id"]]}
                for i, r in enumerate(study) if r["late_payment"] is None],
            "fallback_policy": "Exactly three; no reseed"}


def csv_rows(path, rows):
    if not rows:
        raise ValueError("Empty eligible dataset; stop without reseeding")
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def summary(worlds, study, ledger, audits):
    outcomes = Counter(e["decision"] for e in ledger)
    return {"study_rows": len(study),
            "known_rows": sum(r["late_payment"] is not None for r in study),
            "unknown_rows": sum(r["late_payment"] is None for r in study),
            "total_attempts": sum(len(w["attempts"]) for w in worlds),
            "total_granted": sum(len(w["rows"]) for w in worlds),
            "study_attempts": len(ledger),
            "study_granted": sum(e["granted"] for e in ledger),
            "routing": {name: outcomes[name] for name in (
                "blocked_pending_balance", "requires_owner_review", "model_eligible",
                "simulator_refused_model_eligible")},
            "simulator_refusals": dict(Counter(e.get("refusal_reason") for e in ledger
                                               if not e["granted"])), "audits": audits,
            "metric_scope": ("Only policy-eligible granted study rows; "
                             "supervised metrics known only")}


def generate(spec, sources, simulator):
    anchors, review, data = [load(sources / name) for name in SOURCES]
    world = simulator.generate_owner_pending_dataset(
        anchors, data["simulation"], review, data, spec["seed"], spec["prefix"])
    return world


def audit_world(world, sources, simulator):
    anchors, review, data = [load(sources / name) for name in SOURCES]
    result = simulator.validate_owner_pending_dataset(
        world, anchors, data["simulation"], review, data)
    if result["hard_constraints_pass"] is not True:
        raise ValueError("Simulator hard validation failed")
    return result


def prepare_dev(protocol_path, protocol_sha256, sources, output_dir, policy_source):
    output = new_output(output_dir, (sources, Path(protocol_path).parent,
                                     Path(policy_source).parent))
    stage = "input_validation"
    try:
        revision, effective, evidence, old, simulator = context(
            protocol_path, protocol_sha256, sources, policy_source)
        policy = load_policy(policy_source)
        for name in [*SOURCES, MODEL_PROTOCOL]:
            copy(Path(sources) / name, output / name)
        copy(protocol_path, output / "revision_protocol.json")
        write(output / "effective_protocol.json", effective)
        write(output / "preparation_manifest.json", {**IDENTITY, **evidence,
              "development_replicas": DEV, "final_generated": False, "model_fit_performed": False,
              "frozen_utc": datetime.now(UTC).isoformat()})
        stage = "development_generation_routing_and_folds"
        worlds, study, ledger, audits = [], [], [], []
        seen_clients = set()
        for spec in DEV:
            world = generate(spec, output, simulator)
            write(output / f"{spec['prefix']}_transactions.json", world)
            roster = {c["client_id"] for c in world["clients"]}
            if seen_clients & roster:
                raise ValueError("Development replica client overlap")
            seen_clients.update(roster)
            audits.append(audit_world(world, output, simulator))
            rows, calls = route(world, policy, simulator)
            worlds.append(world)
            study.extend(rows)
            ledger.extend(calls)
        write(output / "development_audits.json", audits)
        write(output / "development_routing_ledger.json", ledger)
        known = [r for r in study if r["late_payment"] is not None]
        csv_rows(output / "development_raw.csv", [r for w in worlds for r in w["rows"]])
        csv_rows(output / "development_eligible.csv", study)
        csv_rows(output / "development_known.csv", known)
        write(output / "development_study_rows.json", study)
        write(output / "development_known_rows.json", known)
        write(output / "planned_folds.json", plan_folds(old, known, study))
        write(output / "development_summary.json", summary(worlds, study, ledger, audits))
        if context(protocol_path, protocol_sha256, sources, policy_source)[2] != evidence:
            raise ValueError("Preparation inputs changed during generation")
        write(output / "development_manifest.json", {**IDENTITY, "files": inventory(output)})
        return load(output / "development_summary.json")
    except Exception as error:
        failure(output, stage, error)
        raise


def verify_development(directory, evidence):
    manifest = load(directory / "development_manifest.json")
    if manifest["files"] != {k: v for k, v in inventory(directory).items()
                             if k != "development_manifest.json"}:
        raise ValueError("Development inventory SHA256 mismatch")
    prepared = load(directory / "preparation_manifest.json")
    if any(prepared.get(k) != v for k, v in evidence.items()):
        raise ValueError("Preparation code/policy/protocol/runtime changed")


def verify_freeze(directory, policy_source):
    directory = checked_path(directory, directory=True)
    frozen = load(directory / "freeze_before_final.json")
    verify(directory, frozen["files"])
    effective = load(directory / "effective_protocol.json")
    evidence = load(directory / "provenance.json")
    if digest(policy_source) != evidence["policy_sha256"]:
        raise ValueError("Policy SHA256 mismatch")
    for path, expected in evidence["code_sha256"].items():
        if digest(path) != expected:
            raise ValueError(f"Code SHA256 mismatch: {path}")
    old, _ = helpers()
    old.validate_runtime(effective["runtime"])
    verify(directory, {**SOURCES, MODEL_PROTOCOL: MODEL_PROTOCOL_SHA256})
    if digest(directory / "revision_protocol.json") != evidence["protocol_sha256"]:
        raise ValueError("Revision SHA256 mismatch")
    selection = load(directory / "frozen_selection.json")
    artifacts = load(directory / "artifact_manifest.json")
    if set(artifacts) != set(old.MODEL_FILES):
        raise ValueError("Incomplete artifact manifest")
    verify(directory, artifacts)
    if any(frozen["files"].get(k) != v for k, v in artifacts.items()):
        raise ValueError("Artifacts not frozen before final")
    if (selection.get("revision_id") != REVISION or selection.get("version") != VERSION
            or selection["feature_names"] != FEATURE_NAMES):
        raise ValueError("Artifact schema/revision mismatch")
    search = load(directory / "cv_search.json")
    for family in old.FAMILIES:
        entries = [e for c in search["candidates"] for e in c["threshold_results"]
                   if e["family"] == family]
        if selection["families"][family] != max(entries, key=old.rank):
            raise ValueError("Frozen family differs from search")
    winner = selection["global_winner"]
    if (winner != max(selection["families"].values(), key=old.rank)
            or winner["params"] not in old.candidate_grid(effective)
            or winner["threshold"] not in effective["thresholds"]
            or artifacts["selected_model.joblib"] != artifacts[f"{winner['family']}.joblib"]):
        raise ValueError("Frozen selection inconsistent")
    return selection


def predict(artifact_dir, input_data, policy_source):
    policy = load_policy(policy_source)
    features, decision = gate(input_data, policy)
    if decision is not None:
        return {**IDENTITY, **decision, "features": features, "model_called": False,
                "probability": None, "predicted": None, "review_policy_applied": False}
    selection = verify_freeze(Path(artifact_dir), policy_source)
    old, _ = helpers()
    model = old.joblib.load(io.BytesIO((Path(artifact_dir) / "selected_model.joblib").read_bytes()))
    if getattr(model, "n_features_in_", None) != 11 or list(model.classes_) != [0, 1]:
        raise ValueError("Model feature/class schema mismatch")
    winner = selection["global_winner"]
    score = float(old.checked_scores(model, old.v4.feature_matrix([features]))[0])
    return {**IDENTITY, "features": features, "family": winner["family"], "model_called": True,
            "probability": score, "threshold": winner["threshold"],
            "predicted": int(score >= winner["threshold"]), "known_label": None,
            "illustrative_only": True, "review_policy_applied": False}


def train_evaluate(protocol_path, protocol_sha256, development_dir, output_dir, policy_source):
    development = checked_path(development_dir, directory=True)
    output = new_output(output_dir, (development, Path(protocol_path).parent,
                                     Path(policy_source).parent))
    stage = "input_validation"
    try:
        revision, effective, evidence, old, simulator = context(
            protocol_path, protocol_sha256, development, policy_source)
        verify_development(development, evidence)
        policy = load_policy(policy_source)
        for name in [*SOURCES, MODEL_PROTOCOL, "revision_protocol.json",
                     "preparation_manifest.json",
                     "planned_folds.json", "development_manifest.json", "development_audits.json",
                     "development_summary.json", "development_study_rows.json",
                     "development_known_rows.json", "development_routing_ledger.json"]:
            copy(development / name, output / name)
        write(output / "effective_protocol.json", effective)
        provenance = {**IDENTITY, **evidence,
                      "development_manifest_sha256": digest(
                          development / "development_manifest.json"),
                      "source_anchors": load(development / "APF3_OWNER_ANCHORS_V4.json"),
                      "source_review": load(development / "APF3_OWNER_REVIEW_V5.json"),
                      "revision_protocol": revision, "historical_documents_unchanged": True}
        write(output / "provenance.json", provenance)
        worlds = [load(development / f"{r['prefix']}_transactions.json") for r in DEV]
        study = load(development / "development_study_rows.json")
        known = load(development / "development_known_rows.json")
        rebuilt, ledger = [], []
        for world in worlds:
            audit_world(world, development, simulator)
            rows, calls = route(world, policy, simulator)
            rebuilt.extend(rows)
            ledger.extend(calls)
        if (rebuilt != study or known != [r for r in study if r["late_payment"] is not None]
                or ledger != load(development / "development_routing_ledger.json")):
            raise ValueError("Development eligible routing mismatch")
        plan = plan_folds(old, known, study)
        if plan != load(development / "planned_folds.json"):
            raise ValueError("Saved folds differ from fixed eligible-only plan")
        stage = "oof_selection_and_refit"
        search, entries, baselines = [], [], {}
        spec = effective["review_policy"]
        for index, params in enumerate(old.candidate_grid(effective) +
                                       [{"family": n} for n in old.BASELINES]):
            scores, coverage, assignments = old.oof_predict(params, known, study, plan)
            thresholds = effective["thresholds"] if params["family"] in old.FAMILIES else [0.5]
            results = [{"family": params["family"], "candidate_index": index, "params": params,
                        "threshold": t, **old.evaluate_cached(study, scores, t, spec, assignments)}
                       for t in thresholds]
            item = {"candidate_index": index, "params": params, "threshold_results": results,
                    "oof_probabilities": scores.tolist(),
                    "oof_prediction_counts": coverage.tolist(),
                    "outer_fold": assignments.tolist()}
            if params["family"] in old.FAMILIES:
                search.append(item)
                entries.extend(results)
            else:
                baselines[params["family"]] = {**results[0], **item}
        write(output / "cv_search.json", {"candidates": search, "baselines": baselines,
              "study_loan_ids": [r["loan_id"] for r in study],
              "selection_optimism": effective["cv"]["selection_optimism"]})
        families = {n: max([e for e in entries if e["family"] == n], key=old.rank)
                    for n in old.FAMILIES}
        winner = max(families.values(), key=old.rank)
        choices = {**families, **baselines}
        x, y = old.matrix(known)
        import numpy as np

        groups = np.asarray([r["client_id"] for r in known])
        inner = old.local_inner(plan["inner_sigmoid_full_train"], range(len(known)), known)
        reports = {}
        for name, choice in choices.items():
            model = old.fit_model(choice["params"], x, y, groups, inner)
            with (output / f"{name}.joblib").open("xb") as stream:
                old.joblib.dump(model, stream)
            train = old.evaluate_cached(
                study, old.checked_scores(model, old.v4.feature_matrix(study)),
                choice["threshold"], spec)
            reports[name] = {"params": choice["params"], "threshold": choice["threshold"],
                             "train": train["metrics"], "oof": choice["metrics"],
                             "review_policy": {"train": train["review_policy"],
                                               "oof": choice["review_policy"]},
                             "artifact": f"{name}.joblib",
                             "interpretation": old.interpretation(model, name),
                             "train_note": ("Descriptive fitted predictions, "
                                            "not independent evaluation")}
        copy(output / f"{winner['family']}.joblib", output / "selected_model.joblib")
        selection = {**IDENTITY, "feature_names": FEATURE_NAMES, "families": families,
                     "global_winner": winner}
        write(output / "training_reports.json", reports)
        write(output / "frozen_selection.json", selection)
        artifacts = {n: digest(output / n) for n in old.MODEL_FILES}
        write(output / "artifact_manifest.json", artifacts)
        verify_development(development, evidence)
        if context(protocol_path, protocol_sha256, development, policy_source)[2] != evidence:
            raise ValueError("Inputs changed during fitting")
        write(output / "freeze_before_final.json", {**IDENTITY, "files": inventory(output),
              "frozen_utc": datetime.now(UTC).isoformat(), "final_generation_calls": 0,
              "final_prediction_calls": 0})
        stage = "freeze_verification"
        verify_freeze(output, policy_source)
        models = {n: old.joblib.load(io.BytesIO((output / f"{n}.joblib").read_bytes()))
                  for n in choices}
        stage = "final_generation_and_hard_audit"
        world = generate(FINAL, output, simulator)
        write(output / "final_transactions.json", world)
        final_audit = audit_world(world, output, simulator)
        write(output / "final_audits.json", final_audit)
        dev_clients = {c["client_id"] for w in worlds for c in w["clients"]}
        if dev_clients & {c["client_id"] for c in world["clients"]}:
            raise ValueError("Final and development clients overlap")
        final_rows, final_ledger = route(world, policy, simulator)
        write(output / "final_routing_before_scoring.json", final_ledger)
        csv_rows(output / "final_raw.csv", world["rows"])
        csv_rows(output / "final_eligible.csv", final_rows)
        stage = "final_cached_evaluation"
        results, calls = {}, {}
        xf = old.v4.feature_matrix(final_rows)
        for name, model in models.items():
            scores = old.checked_scores(model, xf)
            calls[name] = {"batch_calls": 1, "rows_scored": len(final_rows),
                           "unknown_rows_scored": sum(r["late_payment"] is None
                                                      for r in final_rows)}
            result = old.evaluate_cached(final_rows, scores, choices[name]["threshold"], spec,
                                         predictions=True)
            results[name] = {**result, "scores": scores.tolist(),
                             "score_loan_ids": [r["loan_id"] for r in final_rows]}
            write(output / f"final_cache_{name}.json", results[name])
            reports[name]["final"] = result["metrics"]
            reports[name]["review_policy"]["final"] = result["review_policy"]
            reports[name].update({k: result[k] for k in (
                "error_count", "error_cases", "error_cases_note")})
        by_loan = {r["loan_id"]: i for i, r in enumerate(final_rows)}
        for entry in final_ledger:
            if entry["loan_id"] in by_loan:
                i = by_loan[entry["loan_id"]]
                entry.update({"model_called": True,
                              "probability": results[winner["family"]]["scores"][i],
                              "model_probabilities": {n: r["scores"][i]
                                                      for n, r in results.items()}})
        write(output / "final_predictions.json", results)
        write(output / "final_call_ledger.json", calls)
        write(output / "final_routing_ledger.json", final_ledger)
        stage = "illustration_and_reporting"
        illustrative = effective["illustrative_input"]["features"]
        duplicate = any(all(r[n] == illustrative[n] for n in FEATURE_NAMES)
                        for w in [*worlds, world] for r in w["rows"])
        write(output / "illustrative_input.json", {"features": illustrative})
        example = ({"status": "omitted_duplicate", "distinctness_pass": False, **IDENTITY}
                   if duplicate else {**predict(output, illustrative, policy_source),
                                      "distinctness_pass": True, "requested_amount_pen": 20})
        write(output / "illustrative_output.json", example)
        final_summary = summary([world], final_rows, final_ledger, [final_audit])
        final_summary.update({"audit": final_audit, "source_clients_disjoint": True,
                              "call_ledger": calls, "routing_ledger": "final_routing_ledger.json",
                              "evaluation_batch_calls_per_model": dict.fromkeys(models, 1),
                              "generation_calls": 1})
        report = {**IDENTITY, "feature_names": FEATURE_NAMES, "provenance": provenance,
                  "selection": selection, "development": load(output / "development_summary.json"),
                  "final": final_summary, "models": reports,
                  "baseline_comparison": old.v4.baseline_comparison(reports, winner["family"]),
                  "illustrative_inference": example, "artifact_sha256": artifacts,
                  "limits": effective["limits"] + [effective["cv"]["selection_optimism"],
                      "Undefined precision uses zero_division=0; undefined ROC AUC is null",
                      "Blocked/manual attempts have null scores and never compete "
                      "for model alert capacity"]}
        write(output / "pending_v6_report.json", report)
        verify_freeze(output, policy_source)
        verify_development(development, evidence)
        write(output / "report_checks.json", {"freeze_unchanged": True,
              "development_unchanged": True,
              "clients_disjoint": True, "final_generation_calls": 1, "final_batch_calls": calls,
              "capacity_respected": all(r["review_policy"]["final"]["capacity_respected"]
                                        for r in reports.values()), "no_reseed": True})
        write(output / "final_manifest.json", {**IDENTITY, "files": inventory(output)})
        return report
    except Exception as error:
        failure(output, stage, error)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare-dev", "train-evaluate", "predict"):
        command = commands.add_parser(name)
        command.add_argument("--policy-source", type=Path, required=True)
        if name == "predict":
            for flag in ("artifact-dir", "input-json", "output-json"):
                command.add_argument(f"--{flag}", type=Path, required=True)
        else:
            command.add_argument("--protocol", type=Path, required=True)
            command.add_argument("--protocol-sha256", required=True)
            command.add_argument("--output-dir", type=Path, required=True)
            command.add_argument("--sources" if name == "prepare-dev" else "--development-dir",
                                 type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "predict":
        output = new_output(args.output_json, (args.artifact_dir, args.input_json.parent,
                            args.policy_source.parent), directory=False)
        result = predict(args.artifact_dir, load(args.input_json), args.policy_source)
        write(output, result)
    elif args.command == "prepare-dev":
        result = prepare_dev(args.protocol, args.protocol_sha256, args.sources,
                             args.output_dir, args.policy_source)
    else:
        report = train_evaluate(args.protocol, args.protocol_sha256, args.development_dir,
                                args.output_dir, args.policy_source)
        result = {**IDENTITY, "global_winner": report["selection"]["global_winner"]}
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
