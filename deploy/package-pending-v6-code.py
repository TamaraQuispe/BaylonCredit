"""Prepare exact V6 academic sources only; never run an experiment or generate data."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shutil
from pathlib import Path

SCRIPTS = (
    "academic_credit_pending_v6",
    "academic_credit_aligned_v4",
    "academic_credit_grouped_cv",
    "freeze_pending_v6_model_protocol",
    "audit_pending_v6_development",
    "prepare_pending_v6_data",
)
ML_MODULES = (
    "features", "synthetic", "outcomes",
    "owner_pending_synthetic", "owner_aligned_synthetic",
)
INITIALIZER = '"""Isolated academic simulation package; no service initialization."""\n'
GENERATOR_SHA256 = "1f122cea1fec04d416e31c62d36dea8882ff2b55b3956fa2969637776dca3e28"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve(strict=True)
    backend = repo / "backend"
    output = args.output_dir.absolute()
    manifest_path = output.with_name(output.name + "-manifest.json")
    if not output.parent.is_dir():
        raise ValueError("Output parent must already exist")
    if any(path.exists() or path.is_symlink() for path in (output, manifest_path)):
        raise ValueError("Refusing to overwrite code directory or sibling manifest")
    output = output.resolve()
    if output == repo or repo in output.parents:
        raise ValueError("Output must be outside the source repository")

    # Read the frozen constants without importing the production package initializer.
    tree = ast.parse((backend / "scripts/audit_pending_v6_development.py").read_bytes())
    frozen = ast.literal_eval(next(
        node.value for node in tree.body if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "FROZEN_CODE"
                for target in node.targets)
    ))
    if frozen["/app/app/ml/owner_pending_synthetic.py"] != GENERATOR_SHA256:
        raise ValueError("Frozen generator contract changed")
    files = sorted({
        *(f"scripts/{name}.py" for name in SCRIPTS),
        *(f"app/ml/{name}.py" for name in ML_MODULES),
        "app/__init__.py", "app/db/__init__.py", "app/db/base.py",
        *(str(path.relative_to(backend)) for path in (backend / "app/models").glob("*.py")),
    })
    original = {name: sha(backend / name) for name in files}
    for name, digest in frozen.items():
        if original[name.removeprefix("/app/")] != digest:
            raise ValueError(f"Frozen source drift: {name}")
    initializer_source_sha = sha(backend / "app/ml/__init__.py")
    output.mkdir()
    for name in files:
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(backend / name, target)
        if sha(target) != original[name] or sha(backend / name) != original[name]:
            raise ValueError(f"Copy/source hash mismatch: {name}")
    (output / "app/ml/__init__.py").write_text(INITIALIZER, encoding="utf-8")
    inventory = {
        str(path.relative_to(output)): sha(path)
        for path in sorted(output.rglob("*")) if path.is_file()
    }
    manifest = {
        "version": "pending-v6-academic-code-1",
        "repo": str(repo), "code_directory": str(output), "mount_at": "/app",
        "scope": "Code packaging only; no fit, prediction, generation or experiment output",
        "failure_context": (
            "Reported actual attempt failed during imports before training/output: "
            "production app/ml initializer loads legacy model/config requiring Pydantic. "
            "This isolates imports, not experiment scope or the frozen protocol."
        ),
        "source_sha256": original,
        "files": inventory,
        "frozen_code_sha256": frozen,
        "exact_source_copies_verified": True,
        "initializer_exception": {
            "path": "app/ml/__init__.py",
            "original_sha256": initializer_source_sha,
            "packaged_sha256": inventory["app/ml/__init__.py"],
            "reason": "Support initializer only; no exports or legacy model/config loading",
            "frozen_generator_or_runner_provenance_source": False,
        },
        "fixtures": "Not needed by runner load_sources: it reads the saved fold plan/snapshot",
        "manifest_placement": "Sibling outside code inventory and runner hash scope",
    }
    with manifest_path.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({
        "code_directory": str(output), "manifest": str(manifest_path),
        "manifest_sha256": sha(manifest_path), "files": len(inventory),
        "exact_source_copies": len(original), "frozen_hashes_verified": len(frozen),
        "generator_sha256": GENERATOR_SHA256,
    }, indent=2))


if __name__ == "__main__":
    main()
