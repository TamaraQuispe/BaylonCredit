"""Development-only frozen SVM inference and fail-closed runtime comparison."""

import argparse
import csv
import hashlib
import io
import json
import math
import os
import platform
import sys
import warnings
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

ARTIFACT_SHA = "f89db794fc657c3c0f858b1392e26474bc15577facd38ac49355b19a6834db45"
CSV_SHA = "4099ddba545eea26681e133c84cbb705488cfe1922c7085ca4ac71ceefafc544"
FEATURES = ["completed_sales", "paid_credits", "paid_late", "pending_overdue",
            "pending_current", "outstanding", "utilization", "requested_ratio",
            "tenure_days", "punctuality_rate", "overdue_rate"]
ILLUSTRATIVE = [6.0, 6.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.25, 180.0, 5 / 6, 0.0]
MODEL = {"class": "sklearn.calibration.CalibratedClassifierCV", "method": "sigmoid",
         "ensemble": False, "pipeline": ["sklearn.impute._base.SimpleImputer",
         "sklearn.preprocessing._data.StandardScaler", "sklearn.svm._classes.SVC"],
         "imputer_strategy": "median", "C": 1.0, "kernel": "linear",
         "class_weight": "balanced", "probability": False}
COMMON_RUNTIME = {"sklearn": "1.9.1", "joblib": "1.6.0", "scipy": "1.18.1",
                  "threadpoolctl": "3.7.0", "python_implementation": "CPython"}
REFERENCE_RUNTIME = {**COMMON_RUNTIME, "python": "3.14.6", "numpy": "2.5.5",
                     "system": "Darwin", "machine": "arm64"}
CANDIDATE_RUNTIME = {**COMMON_RUNTIME, "python": "3.12.14", "numpy": "2.5.3",
                     "system": "Linux", "machine": "aarch64"}
# Servidor de staging: mismo stack que el candidato, otra arquitectura.
X86_64_RUNTIME = {**COMMON_RUNTIME, "python": "3.12.14", "numpy": "2.5.3",
                  "system": "Linux", "machine": "x86_64"}
TESTED_RUNTIMES = (REFERENCE_RUNTIME, CANDIDATE_RUNTIME, X86_64_RUNTIME)
SCOPE = {"research_only": True, "production_authorized": False,
         "final_test_evaluated": False, "final_contacted": False,
         "fit_calls": 0, "generation_calls": 0, "database_access": False,
         "labels_evaluated": False, "stage": "dev_only_selection"}
ENCODING_EXPLANATION = (
    "Only exact LabelEncoder.fit on frozen classes [0,1] inside calibrated predict_proba; "
    "class encoding only, no model, preprocessing, or calibration fitting"
)
IDENTITY = {"schema": "proy-runtime-probe-v1", "feature_names": FEATURES,
            "classes": [0, 1], "n_features": 11, "threshold": 0.1,
            "positive_label": 1, "negative_label": 0,
            "source": "PROY-P0-05", "model_version": "credit-proy-svm-v1",
            "model_identity": MODEL, "scope": SCOPE, "warnings": [],
            "artifact_before": ARTIFACT_SHA, "artifact_after": ARTIFACT_SHA,
            "csv_before": CSV_SHA, "csv_after": CSV_SHA,
            "internal_label_encoder_fit_allowance": True,
            "internal_label_encoder_fit_explanation": ENCODING_EXPLANATION,
            "learned_state_unchanged": True,
            "predict_proba_calls": {"development_batch": 1, "illustrative": 1}}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":"))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def write_new(path, value):
    require(path.parent.is_dir(), "Output parent must already exist")
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def validate_probe(probe, runtime):
    require(type(probe) is dict, "Probe must be an object")
    for key, expected in IDENTITY.items():
        require(canonical(probe.get(key)) == canonical(expected), "Invalid identity: " + key)
    require(probe.get("runtime") == runtime, "Runtime is not the exact tested tuple")
    before, after = probe.get("learned_state_before_sha256"), probe.get("learned_state_after_sha256")
    require(type(before) is str and len(before) == 64 and
            all(c in "0123456789abcdef" for c in before) and before == after,
            "Learned state changed or missing serialization hashes")
    require(type(probe.get("internal_label_encoder_fit_calls")) is int and
            probe["internal_label_encoder_fit_calls"] == 2, "Expected two internal class encoding calls")
    require(type(probe.get("recorded_utc")) is str, "Missing timestamp")
    instant = datetime.fromisoformat(probe["recorded_utc"])
    require(instant.utcoffset() is not None and instant.utcoffset().total_seconds() == 0,
            "Timestamp must be UTC")
    scores = probe.get("scores")
    require(type(scores) is list and len(scores) == 534, "Expected 534 development rows")
    seen = set()
    for row in scores + [probe.get("illustrative")]:
        require(type(row) is dict, "Invalid score row")
        loan_id = row.get("loan_id")
        require(type(loan_id) is str and loan_id and loan_id not in seen, "Invalid/duplicate loan ID")
        seen.add(loan_id)
        features = row.get("features")
        require(type(features) is list and len(features) == 11, "Invalid feature shape")
        require(all(type(x) in (int, float) and math.isfinite(x) for x in features),
                "Nonfinite/non-numeric feature")
        probabilities = row.get("proba")
        require(type(probabilities) is list and len(probabilities) == 2, "Invalid probability shape")
        require(all(type(x) in (int, float) and math.isfinite(x) and 0 <= x <= 1
                    for x in probabilities), "Invalid probability")
        require(math.isclose(sum(probabilities), 1.0, rel_tol=0, abs_tol=1e-12),
                "Probabilities must sum to one")
        require(type(row.get("predicted")) is int and
                row["predicted"] == int(probabilities[1] >= 0.1), "Class/threshold inconsistency")
    require(probe["illustrative"]["loan_id"] == "illustrative-six-paid-one-late" and
            probe["illustrative"]["features"] == ILLUSTRATIVE, "Invalid illustrative snapshot")


def compare_probes(reference, candidate):
    """Pure comparison: no model, file, application, or ML imports."""
    validate_probe(reference, REFERENCE_RUNTIME)
    if candidate.get("runtime") not in TESTED_RUNTIMES:
        raise ValueError("Untested runtime: " + str(candidate.get("runtime")))
    validate_probe(candidate, candidate["runtime"])
    deltas = []
    for left, right in zip(reference["scores"] + [reference["illustrative"]],
                           candidate["scores"] + [candidate["illustrative"]], strict=True):
        require(left["loan_id"] == right["loan_id"], "Loan ID/order mismatch")
        require(left["features"] == right["features"], "Snapshot mismatch")
        require(left["predicted"] == right["predicted"], "Predicted class changed")
        delta = [abs(a - b) for a, b in zip(left["proba"], right["proba"], strict=True)]
        deltas.append({"loan_id": left["loan_id"], "absolute_delta": delta,
                       "predicted": left["predicted"]})
    maximum = max(max(row["absolute_delta"]) for row in deltas)
    return {"compatible": maximum <= 1e-12, "absolute_tolerance": 1e-12,
            "relative_tolerance": 0, "classes_match": True,
            "max_absolute_delta": maximum, "per_row_deltas": deltas,
            "development_rows": 534, "illustrative_rows": 1}


def make_profile_guard(label_encoder_class, state):
    """Allow only class encoding on the frozen model's calibrated prediction stack."""
    def guard(frame, event, arg):
        if event != "call":
            return
        name = frame.f_code.co_name.lower().lstrip("_")
        if not (name.startswith(("fit", "generate")) or name == "partial_fit"):
            return
        model = state.get("model")
        labels = frame.f_locals.get("y")
        if (model is not None and frame.f_code is label_encoder_class.fit.__code__
                and type(frame.f_locals.get("self")) is label_encoder_class
                and type(labels) is type(model.classes_)
                and getattr(labels, "shape", None) == (2,)
                and list(labels) == list(model.classes_) == [0, 1]):
            caller = frame.f_back
            immediate_calibration = (caller is not None
                and caller.f_globals.get("__name__") == "sklearn.calibration"
                and caller.f_code.co_name == "predict_proba")
            while caller is not None and immediate_calibration:
                if (caller.f_globals.get("__name__") == "sklearn.calibration"
                        and caller.f_code.co_name == "predict_proba"
                        and caller.f_locals.get("self") is model):
                    state["internal_label_encoder_fit_calls"] += 1
                    return
                caller = caller.f_back
        raise RuntimeError("Fitting/generation forbidden: " + name + " in " +
                           frame.f_globals.get("__name__", "unknown"))
    return guard


def probe(artifact, development_csv):
    # Thread limits must precede all numerical imports.
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                 "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS", "BLIS_NUM_THREADS"):
        os.environ[name] = "1"
    require(not any(name == "app" or name.startswith("app.") for name in sys.modules),
            "Application modules are forbidden")
    artifact_bytes = artifact.read_bytes()
    csv_bytes = development_csv.read_bytes()
    require(sha(artifact_bytes) == ARTIFACT_SHA, "Artifact SHA mismatch before load")
    require(sha(csv_bytes) == CSV_SHA, "Development CSV SHA mismatch before load")
    rows = list(csv.DictReader(io.StringIO(csv_bytes.decode("utf-8"))))
    require(len(rows) == 534, "Expected 534 development rows")
    snapshots = [[float(row[name]) for name in FEATURES] for row in rows]

    class NoApplicationImports:
        def find_spec(self, fullname, path=None, target=None):
            if fullname == "app" or fullname.startswith("app."):
                raise RuntimeError("Application import forbidden: " + fullname)

    blocker = NoApplicationImports()
    old_profile = sys.getprofile()
    sys.meta_path.insert(0, blocker)
    try:
        import joblib
        import numpy as np
        import sklearn.calibration
        import sklearn.impute
        import sklearn.pipeline
        import sklearn.preprocessing
        import sklearn.svm

        state = {"model": None, "internal_label_encoder_fit_calls": 0}
        sys.setprofile(make_profile_guard(sklearn.preprocessing.LabelEncoder, state))
        with warnings.catch_warnings():
            # Any warning, including sklearn version warnings, blocks evidence.
            warnings.simplefilter("error")
            model = joblib.load(io.BytesIO(artifact_bytes))
            class_name = lambda obj: type(obj).__module__ + "." + type(obj).__name__
            require(class_name(model) == MODEL["class"], "Not calibrated SVM")
            require(list(model.classes_) == [0, 1] and model.n_features_in_ == 11,
                    "Invalid model classes/features")
            require(len(model.calibrated_classifiers_) == 1, "Unexpected calibration ensemble")
            pipeline = model.calibrated_classifiers_[0].estimator
            steps = [step for _, step in pipeline.steps]
            svc = steps[-1]
            actual_model = {"class": class_name(model), "method": model.method,
                            "ensemble": model.ensemble, "pipeline": [class_name(s) for s in steps],
                            "imputer_strategy": steps[0].strategy, "C": svc.C,
                            "kernel": svc.kernel, "class_weight": svc.class_weight,
                            "probability": svc.probability}
            require(actual_model == MODEL, "Frozen model identity mismatch: " + str(actual_model))
            state["model"] = model
            before_buffer = io.BytesIO()
            joblib.dump(model, before_buffer)
            before_sha = sha(before_buffer.getvalue())
            batches = [model.predict_proba(np.asarray(snapshots, dtype=float)),
                       model.predict_proba(np.asarray([ILLUSTRATIVE], dtype=float))]
            require(batches[0].shape == (534, 2) and batches[1].shape == (1, 2),
                    "Invalid inference output shape")
            after_buffer = io.BytesIO()
            joblib.dump(model, after_buffer)
            after_sha = sha(after_buffer.getvalue())
            require(before_sha == after_sha, "Model serialization changed during prediction")
    finally:
        sys.setprofile(old_profile)
        sys.meta_path.remove(blocker)
    require(not any(name == "app" or name.startswith("app.") for name in sys.modules),
            "Application module imported")
    runtime = {"python": platform.python_version(), "system": platform.system(),
               "machine": platform.machine(), "python_implementation": platform.python_implementation()}
    for key, package in (("sklearn", "scikit-learn"), ("numpy", "numpy"), ("joblib", "joblib"),
                         ("scipy", "scipy"), ("threadpoolctl", "threadpoolctl")):
        runtime[key] = metadata.version(package)
    def score(loan_id, features, probabilities):
        values = [float(x) for x in probabilities]
        return {"loan_id": loan_id, "features": features, "proba": values,
                "predicted": int(values[1] >= 0.1)}
    result = {**IDENTITY, "recorded_utc": timestamp(), "runtime": runtime,
              "learned_state_before_sha256": before_sha, "learned_state_after_sha256": after_sha,
              "internal_label_encoder_fit_calls": state["internal_label_encoder_fit_calls"],
              "scores": [score(row["loan_id"], features, probabilities)
                         for row, features, probabilities in zip(rows, snapshots, batches[0], strict=True)],
              "illustrative": score("illustrative-six-paid-one-late", ILLUSTRATIVE, batches[1][0]),
              "artifact_after": sha(artifact.read_bytes()), "csv_after": sha(development_csv.read_bytes())}
    require(runtime in TESTED_RUNTIMES, "Untested runtime: " + str(runtime))
    validate_probe(result, runtime)
    return result


def read_json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=unique)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("probe")
    run.add_argument("--artifact", type=Path, required=True)
    run.add_argument("--development-csv", type=Path, required=True)
    comparison = commands.add_parser("compare")
    comparison.add_argument("--reference", type=Path, required=True)
    comparison.add_argument("--candidate", type=Path, required=True)
    comparison.add_argument("--previous-failed-attempt", type=Path)
    for command in (run, comparison):
        command.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    require(args.output_json.parent.is_dir() and not args.output_json.exists()
            and not args.output_json.is_symlink(), "Output must be NEW in an existing directory")
    record = {"schema": "proy-runtime-compatibility-v1", "recorded_utc": timestamp(),
              "scope": SCOPE, "compatible": False,
              "unsupported": ["x86_64", "all other untested runtime/platform tuples"]}
    try:
        if args.command == "probe":
            record = probe(args.artifact, args.development_csv)
        else:
            if args.previous_failed_attempt is not None:
                previous_bytes = args.previous_failed_attempt.read_bytes()
                previous = read_json(previous_bytes)
                require(previous.get("compatible") is False and "Fitting/generation forbidden: fit"
                        in previous.get("blocker", ""), "Not the expected failed instrumentation attempt")
                record.update({"previous_failed_attempt_sha256": sha(previous_bytes),
                               "previous_failed_attempt_cause":
                               "Instrumentation false block of internal class encoding, not model incompatibility"})
            reference_bytes = args.reference.read_bytes()
            candidate_bytes = args.candidate.read_bytes()
            record["probes"] = {"reference": {"name": args.reference.name, "sha256": sha(reference_bytes)},
                                "candidate": {"name": args.candidate.name, "sha256": sha(candidate_bytes)}}
            reference, candidate = read_json(reference_bytes), read_json(candidate_bytes)
            for name, result in (("reference", reference), ("candidate", candidate)):
                require(not result.get("blocker"), name + " probe failed: " + str(result.get("blocker")))
            record.update(compare_probes(reference, candidate))
            record.update({"artifact_sha256": ARTIFACT_SHA, "development_csv_sha256": CSV_SHA,
                           "feature_names": FEATURES, "model_identity": MODEL, "classes": [0, 1],
                           "threshold": 0.1, "reference_runtime": reference["runtime"],
                           "internal_label_encoder_fit_allowance": True,
                           "internal_label_encoder_fit_explanation": ENCODING_EXPLANATION,
                           "learned_state_unchanged": True,
                           "learned_state_serialization": {
                               name: {key: result[key] for key in (
                                   "learned_state_before_sha256", "learned_state_after_sha256",
                                   "internal_label_encoder_fit_calls")}
                               for name, result in (("reference", reference), ("candidate", candidate))},
                           "candidate_runtime": candidate["runtime"],
                           "illustrative": {"reference": reference["illustrative"],
                                            "candidate": candidate["illustrative"]},
                           "tested_runtime_whitelist": list(TESTED_RUNTIMES)
                           if record["compatible"] else [],
                           "unsupported": ["x86_64", "all other untested runtime/platform tuples"],
                           "attribution": "Python and NumPy changed together; no single-variable attribution"})
            if not record["compatible"]:
                record["blocker"] = "Probability delta exceeds absolute tolerance"
    except Exception as exc:
        record.update({"compatible": False, "blocker": type(exc).__name__ + ": " + str(exc),
                       "tested_runtime_whitelist": []})
        write_new(args.output_json, record)
        print(record["blocker"], file=sys.stderr)
        return 1
    write_new(args.output_json, record)
    print(json.dumps({"output": args.output_json.name, "sha256": sha(args.output_json.read_bytes()),
                      "compatible": record.get("compatible"),
                      "max_absolute_delta": record.get("max_absolute_delta"),
                      "illustrative": record.get("illustrative")}, allow_nan=False))
    return int(args.command == "compare" and not record["compatible"])


if __name__ == "__main__":
    sys.exit(main())
