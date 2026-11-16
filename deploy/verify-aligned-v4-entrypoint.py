"""Check the delivered CLI on its illustrative input, offline and read-only."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from time import perf_counter


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root, output, image):
    root = root.resolve(strict=True)
    assert output.parent.is_dir() and not output.exists()
    frozen = json.loads((root / "manifest-paquete.json").read_text())["experiment_sha256"]
    before = {name: sha(root / "experimento" / name) for name in frozen}
    assert before == frozen
    expected = json.loads((root / "experimento/illustrative_output.json").read_text())
    image_id = subprocess.run(
        ["docker", "image", "inspect", image, "--format", "{{.Id}}"],
        check=True, text=True, capture_output=True,
    ).stdout.strip()
    command = [
        "docker", "run", "--rm", "--pull", "never", "--network", "none",
        "--read-only", "--memory", "256m", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges", "--tmpfs", "/tmp:rw,noexec,nosuid,size=32m",
        "--env", "OMP_NUM_THREADS=1", "--env", "OPENBLAS_NUM_THREADS=1",
        "--env", "PYTHONPATH=/package/codigo", "--workdir", "/package",
        "--mount", f"type=bind,src={root},dst=/package,readonly",
        "--entrypoint", "python", image_id, "-B",
        "/package/APF3_TD_Grupo2_ML_Innovacion.py",
        "--predict-artifact-dir", "/package/experimento",
        "--input-json", "/package/experimento/illustrative_input.json",
        "--output-json", "/tmp/illustrative-new-output.json",
    ]
    started = perf_counter()
    process = subprocess.run(command, check=True, capture_output=True, text=True)
    elapsed = perf_counter() - started
    result = json.loads(process.stdout)
    for key in ("features", "feature_names", "probability", "threshold", "predicted",
                "known_label", "research_only", "business_approval"):
        assert result[key] == expected[key], key
    assert before == {name: sha(root / "experimento" / name) for name in frozen}
    record = {
        "status": "passed", "command": command, "docker_image_id": image_id,
        "container_start_and_cli_seconds": elapsed,
        "timing_scope": "Docker startup + CLI imports, model load and one illustrative prediction",
        "result": result, "new_training": False, "final_inference": False,
        "experiment_unchanged": True, "human_demo": "pending",
        "entrypoint_sha256": sha(root / "APF3_TD_Grupo2_ML_Innovacion.py"),
        "expected_output_sha256": sha(root / "experimento/illustrative_output.json"),
        "tool_sha256": sha(Path(__file__)),
    }
    with output.open("x") as stream:
        json.dump(record, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": "passed", "probability": result["probability"],
                      "container_start_and_cli_seconds": elapsed}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image", default="credify-demo-academic-api:v4")
    args = parser.parse_args()
    verify(args.root, args.output, args.image)
