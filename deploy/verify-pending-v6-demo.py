"""Check the delivered illustrative CLI and its latency, never train or score FINAL."""

import argparse
import hashlib
import json
import math
import resource
import statistics
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def benchmark(root):
    # Gated requests succeed even with no artifact directory: no model can be loaded.
    base_features = json.loads((root / "experimento/illustrative_input.json").read_text())["features"]
    guard_results = {}
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        for name, changes, decision in (
            ("pending", {"pending_current": 1, "outstanding": 20, "utilization": 0.25},
             "blocked_pending_balance"),
            ("no-history", {"completed_sales": 0, "paid_credits": 0, "paid_late": 0,
                            "punctuality_rate": 0}, "requires_owner_review"),
        ):
            source, target = folder / (name + "-input.json"), folder / (name + "-output.json")
            source.write_text(json.dumps({"features": {**base_features, **changes}}))
            checked = subprocess.run([
                sys.executable, "-I", "-B", str(root / "APF3_TD_Grupo2_ML_Innovacion.py"),
                "--predict-artifact-dir", str(folder / "artifacts-do-not-exist"),
                "--input-json", str(source), "--output-json", str(target),
            ], check=True, capture_output=True, text=True)
            value = json.loads(target.read_text())
            assert value == json.loads(checked.stdout)
            assert value["decision"] == decision and value["model_called"] is False
            assert value["business_approval"] is False
            assert all(value[key] is None for key in ("probability", "predicted", "threshold"))
            guard_results[name] = {key: value[key] for key in (
                "decision", "model_called", "requires_manual_review", "probability", "predicted"
            )}
    sys.path.insert(0, "/app")
    from scripts.academic_credit_pending_v6 import predict

    experiment = root / "experimento"
    before = {p.name: sha(p) for p in experiment.iterdir() if p.is_file()}
    entry = json.loads((experiment / "illustrative_input.json").read_text())
    expected = json.loads((experiment / "illustrative_output.json").read_text())
    assert expected["distinctness_pass"] and expected["known_label"] is None
    previous = sys.getprofile()

    def guard(frame, event, _arg):
        if event == "call" and (
            frame.f_code.co_name in {"fit", "fit_transform", "fit_predict", "partial_fit"}
            or frame.f_code.co_name.startswith("generate_owner_")
        ):
            raise RuntimeError("Training and generation are forbidden in demo verification")

    started = perf_counter()
    samples = []
    try:
        sys.setprofile(guard)
        result = predict(experiment, entry)
        cold = (perf_counter() - started) * 1000
        for _ in range(30):
            started = perf_counter()
            repeated = predict(experiment, entry)
            samples.append((perf_counter() - started) * 1000)
            assert repeated == result
    finally:
        sys.setprofile(previous)
    for key in ("probability", "threshold", "predicted", "known_label", "features",
                "feature_names", "research_only", "business_approval"):
        assert result[key] == expected[key], key
    assert before == {p.name: sha(p) for p in experiment.iterdir() if p.is_file()}
    return {
        "passed": True, "version": "academic-owner-pending-v6",
        "generated_utc": datetime.now(UTC).isoformat(),
        "scope": "Trusted local predict: integrity validation, deserialization and one illustrative vector",
        "not_measured": ["HTTP", "authentication", "database", "browser", "sustained load", "SLA"],
        "first_predict_ms": cold, "warm_calls": 30,
        "warm_ms": {
            "min": min(samples), "median": statistics.median(samples),
            "p95_nearest_rank": sorted(samples)[math.ceil(0.95 * len(samples)) - 1],
            "max": max(samples),
        },
        "samples_ms": samples,
        "peak_process_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "illustrative_result": result,
        "new_training": False, "final_prediction": False,
        "experiment_sha256_before": before, "experiment_sha256_after": before,
        "human_demo": "pending", "human_rehearsal": "pending",
        "pre_model_guards_verified": True, "pre_model_guards": guard_results,
    }


def verify(root, venv_parent, image, output):
    assert output.parent.is_dir() and not output.exists()
    root, venv_parent = root.resolve(strict=True), venv_parent.resolve(strict=True)
    script = Path(__file__).resolve()
    image_id = subprocess.run(
        ["docker", "image", "inspect", image, "--format", "{{.Id}}"],
        check=True, text=True, capture_output=True,
    ).stdout.strip()
    base = [
        "docker", "run", "--rm", "--pull", "never", "--network", "none", "--read-only",
        "--memory", "256m", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
        "--env", "OMP_NUM_THREADS=1", "--env", "OPENBLAS_NUM_THREADS=1",
        "--workdir", "/package", "--mount", f"type=bind,src={root},dst=/package,readonly",
        "--mount", f"type=bind,src={root / 'codigo'},dst=/app,readonly",
        "--mount", f"type=bind,src={venv_parent},dst=/repro-env,readonly",
        "--mount", f"type=bind,src={script.parent},dst=/tools,readonly",
        "--entrypoint", "/repro-env/venv/bin/python", image_id, "-I", "-B",
    ]
    cli = base + [
        "/package/APF3_TD_Grupo2_ML_Innovacion.py", "--predict-artifact-dir", "/package/experimento",
        "--input-json", "/package/experimento/illustrative_input.json",
        "--output-json", "/tmp/demo-v6-nueva.json",
    ]
    before = {p.name: sha(p) for p in (root / "experimento").iterdir() if p.is_file()}
    started = perf_counter()
    result = subprocess.run(cli, check=True, capture_output=True, text=True)
    seconds = perf_counter() - started
    cli_summary = json.loads(result.stdout)
    expected = json.loads((root / "experimento/illustrative_output.json").read_text())
    for key in ("version", "family", "probability", "threshold", "predicted"):
        assert cli_summary[key] == expected[key]
    command = base + ["/tools/" + script.name, "--inside", "--root", "/package"]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    latency = json.loads(result.stdout)
    assert latency["passed"]
    after = {p.name: sha(p) for p in (root / "experimento").iterdir() if p.is_file()}
    assert before == after == latency["experiment_sha256_before"]
    output.mkdir()
    common = {"tool_sha256": sha(script), "docker_image_id": image_id}
    records = {
        "prueba-cli-v6.json": {
            **common, "passed": True, "command": cli, "cli_summary": cli_summary,
            "docker_start_and_cli_seconds": seconds,
            "expected_output_sha256": sha(root / "experimento/illustrative_output.json"),
            "wrapper_sha256": sha(root / "APF3_TD_Grupo2_ML_Innovacion.py"),
            "policy_sha256": sha(root / "v6_policy.py"),
            "pre_model_guards_verified": latency["pre_model_guards_verified"],
            "experiment_unchanged": before == after, "new_training": False,
            "final_prediction": False, "human_demo": "pending",
        },
        "latency-v6.json": {**latency, **common, "command": command},
    }
    for name, record in records.items():
        with (output / name).open("x") as stream:
            json.dump(record, stream, indent=2, allow_nan=False)
            stream.write("\n")
    print(json.dumps({"passed": True, "cli_summary": cli_summary,
                      "docker_start_and_cli_seconds": seconds,
                      "first_predict_ms": latency["first_predict_ms"],
                      "warm_ms": latency["warm_ms"],
                      "peak_process_rss_kib": latency["peak_process_rss_kib"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--venv-parent", type=Path)
    parser.add_argument("--image", default="bayloncredit-api-training-test:latest")
    parser.add_argument("--inside", action="store_true")
    args = parser.parse_args()
    if args.inside:
        print(json.dumps(benchmark(args.root), indent=2, allow_nan=False))
    else:
        verify(args.root, args.venv_parent, args.image, args.output_dir)
