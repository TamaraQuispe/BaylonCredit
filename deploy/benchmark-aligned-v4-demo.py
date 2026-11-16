"""Measure only the trusted illustrative example; never train or predict FINAL."""

import argparse
import hashlib
import json
import math
import resource
import statistics
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter


def measure(bundle, repetitions):
    sys.path.insert(0, "/app")
    from app.services import academic_lab_v4 as lab

    def hashes():
        return {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(bundle.iterdir()) if p.is_file()
        }

    before = hashes()
    lab.validated_bundle.cache_clear()
    lab.load_model.cache_clear()
    started = perf_counter()
    loaded = lab.load_bundle(str(bundle))
    load_ms = (perf_counter() - started) * 1000
    started = perf_counter()
    result = lab.evaluate(loaded)
    cold_ms = (perf_counter() - started) * 1000
    samples = []
    for _ in range(repetitions):
        started = perf_counter()
        repeated = lab.evaluate(lab.load_bundle(str(bundle)))
        samples.append((perf_counter() - started) * 1000)
        assert repeated == result
    assert result["estimated_late_probability"] == 0.11922453881690649
    assert result["actual_late_payment"] is None
    assert not result["business_approval"] and not result["review_policy_applied"]
    assert hashes() == before
    ordered = sorted(samples)
    return {
        "status": "passed",
        "generated_utc": datetime.now(UTC).isoformat(),
        "scope": "Service load_bundle + evaluate; one fixed illustrative vector only",
        "not_measured": ["HTTP/auth/network/browser latency", "sustained concurrency", "SLA"],
        "runtime": lab.runtime_versions(),
        "case_id": result["case_id"],
        "probability": result["estimated_late_probability"],
        "threshold": result["threshold"],
        "predicted": result["predicted_late_payment"],
        "known_label": None,
        "research_only": True,
        "business_approval": False,
        "new_training": False,
        "final_inference": False,
        "bundle_validation_cold_ms": load_ms,
        "model_load_and_first_prediction_ms": cold_ms,
        "warm_service_calls": repetitions,
        "warm_service_ms": {
            "min": min(samples), "median": statistics.median(samples),
            "p95_nearest_rank": ordered[math.ceil(0.95 * repetitions) - 1],
            "max": max(samples),
        },
        "samples_ms": samples,
        "peak_process_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "bundle_sha256": before,
        "bundle_unchanged": True,
        "human_rehearsal": "pending",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--image", default="credify-demo-academic-api:v4")
    parser.add_argument("--repetitions", type=int, default=30)
    parser.add_argument("--inside-container", action="store_true")
    args = parser.parse_args()
    assert 1 <= args.repetitions <= 100
    if args.inside_container:
        print(json.dumps(measure(args.bundle, args.repetitions), indent=2, allow_nan=False))
        return
    assert args.output and args.output.parent.is_dir() and not args.output.exists()
    bundle = args.bundle.resolve(strict=True)
    script = Path(__file__).resolve()
    image_id = subprocess.run(
        ["docker", "image", "inspect", args.image, "--format", "{{.Id}}"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    command = [
        "docker", "run", "--rm", "--network", "none", "--read-only",
        "--memory", "256m", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
        "--env", "OMP_NUM_THREADS=1", "--env", "OPENBLAS_NUM_THREADS=1",
        "--mount", f"type=bind,src={bundle},dst=/bundle,readonly",
        "--mount", f"type=bind,src={script.parent},dst=/tools,readonly",
        "--entrypoint", "python", image_id, "-B", "/tools/" + script.name,
        "--inside-container", "--bundle", "/bundle", "--repetitions", str(args.repetitions),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    evidence = json.loads(result.stdout)
    evidence["docker_image_id"] = image_id
    evidence["command"] = command
    evidence["tool_sha256"] = hashlib.sha256(script.read_bytes()).hexdigest()
    with args.output.open("x") as stream:
        json.dump(evidence, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: evidence[key] for key in (
        "status", "warm_service_ms", "model_load_and_first_prediction_ms",
        "bundle_validation_cold_ms", "peak_process_rss_kib", "final_inference",
    )}, indent=2))


if __name__ == "__main__":
    main()
