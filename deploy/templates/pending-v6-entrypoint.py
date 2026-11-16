"""Validate V6 inference and apply business guards before the unchanged frozen runner."""
import argparse
import json
import math
import sys
from pathlib import Path

# Isolated Python omits the script directory; trust only this package's sibling policy.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v6_policy import pre_model_decision

APPLIED_DOMAIN = (5 / 80, 50 / 80)
COUNT_FIELDS = (
    "completed_sales", "paid_credits", "paid_late", "pending_overdue",
    "pending_current", "tenure_days",
)


def _load_input(path):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        data = json.loads(Path(path).read_bytes(), object_pairs_hook=unique_object)
    except OSError as exc:
        raise ValueError(f"Input is unavailable or unreadable: {path}") from exc
    if not isinstance(data, dict):
        raise ValueError("Input must be an object with exactly eleven features")
    features = data.get("features", data)
    if "features" in data and set(data) != {"features"}:
        raise ValueError("Input wrapper must contain only features")
    if not isinstance(features, dict):
        raise ValueError("Input must contain exactly eleven features")
    return features


def validate_input(features):
    expected = {
        "completed_sales", "paid_credits", "paid_late", "pending_overdue",
        "pending_current", "outstanding", "utilization", "requested_ratio",
        "tenure_days", "punctuality_rate", "overdue_rate",
    }
    if set(features) != expected:
        raise ValueError("Input must contain exactly eleven features, no label")
    for name, value in features.items():
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a finite nonnegative number or null")
        try:
            valid = value >= 0 and math.isfinite(float(value))
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError(f"{name} must be a finite nonnegative number or null")
        if name in COUNT_FIELDS and int(value) != value:
            raise ValueError(f"{name} must be integral")
        if name in {"utilization", "punctuality_rate", "overdue_rate"} and value > 1:
            raise ValueError(f"{name} outside allowed ratio range")
    requested = features["requested_ratio"]
    if requested is None or not APPLIED_DOMAIN[0] <= requested <= APPLIED_DOMAIN[1]:
        raise ValueError(
            "requested_ratio outside the V6 amount domain: 5..50 PEN on an 80 PEN cap"
        )
    completed, paid, late = (features[n] for n in
                             ("completed_sales", "paid_credits", "paid_late"))
    if paid is not None and late is not None and late > paid:
        raise ValueError("paid_late cannot exceed paid_credits")
    if completed is not None and paid is not None and completed != paid:
        raise ValueError("completed_sales must equal paid_credits in this credit-only example")
    punctuality = features["punctuality_rate"]
    if paid is not None and late is not None and punctuality is not None:
        expected = (paid - late) / paid if paid else 0.0
        if not math.isclose(punctuality, expected, rel_tol=0, abs_tol=1e-9):
            raise ValueError("punctuality_rate is inconsistent with paid history")


def inference_input(argv):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for flag in ("development-dir", "protocol-dir", "output-dir", "predict-artifact-dir",
                 "input-json", "output-json"):
        parser.add_argument(f"--{flag}", type=Path)
    args = parser.parse_args(argv)
    experiment = (args.development_dir, args.protocol_dir, args.output_dir)
    if args.predict_artifact_dir is None:
        if any(value is None for value in experiment) or any(
                value is not None for value in (args.input_json, args.output_json)):
            parser.error("Experiment requires development-dir/protocol-dir/output-dir only")
        return None
    if args.input_json is None or args.output_json is None or any(
            value is not None for value in experiment):
        parser.error("Inference requires input/output JSON and no experiment flags")
    root = Path(__file__).resolve().parent
    output = args.output_json.resolve()
    protected = (root / "codigo", root / "backend", args.predict_artifact_dir.resolve())
    if (args.output_json.exists() or args.output_json.is_symlink()
            or not output.parent.is_dir() or output == args.input_json.resolve()
            or any(output.is_relative_to(path) for path in protected)):
        parser.error("Inference output must be new, with an existing parent outside source/input/artifacts")
    features = _load_input(args.input_json)
    validate_input(features)
    return args, features


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        inference = inference_input(argv)
        if inference is not None:
            args, features = inference
            decision = pre_model_decision(features)
            if decision is not None:
                result = {
                    "version": "academic-owner-pending-v6", "origen": "simulado",
                    "research_only": True, "business_approval": False,
                    "model_called": False, **decision, "probability": None,
                    "predicted": None, "threshold": None, "features": features,
                }
                with args.output_json.open("x", encoding="utf-8") as stream:
                    json.dump(result, stream, indent=2, allow_nan=False)
                    stream.write("\n")
                print(json.dumps(result, indent=2, allow_nan=False))
                return
    except (ValueError, OSError) as error:
        print(f"V6 input rejected: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    sys.dont_write_bytecode = True
    code = Path(__file__).absolute().parent / "codigo"
    sys.path.insert(0, str(code))
    runner = code / "scripts/academic_credit_pending_v6.py"
    sys.argv = [str(runner), *argv]
    import runpy

    runpy.run_path(str(runner), run_name="__main__")


if __name__ == "__main__":
    main()
