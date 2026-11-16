"""Prepare the two predeclared V5 development worlds, never fit or create FINAL."""

import argparse
import csv
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.ml.owner_settled_synthetic import (  # noqa: E402
    CLARIFICATION_SHA256,
    POLICY_VERSION,
    PROTOCOL_SHA256,
    generate_owner_settled_dataset,
    validate_owner_settled_dataset,
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def prepare(source, output):
    source = source.resolve(strict=True)
    assert output.parent.is_dir() and not output.exists()
    assert not output.resolve().is_relative_to(source)
    filenames = (
        "APF3_OWNER_ANCHORS_V4.json", "APF3_ALIGNED_V4_PROTOCOL.json",
        "APF3_OWNER_SETTLEMENT_CLARIFICATION.json", "APF3_SETTLED_V5_DATA_PROTOCOL.json",
    )
    inputs = {name: (source / name).read_bytes() for name in filenames}
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in inputs.items()}
    assert hashes[filenames[2]] == CLARIFICATION_SHA256
    assert hashes[filenames[3]] == PROTOCOL_SHA256
    anchors, base, clarification, protocol = [json.loads(inputs[name]) for name in filenames]
    assert protocol["version"] == POLICY_VERSION
    assert protocol["selection_protocol"] is None and protocol["final_seed"] is None
    assert protocol["final_dataset"] is None
    code = [
        Path(__file__),
        *[BACKEND / "app/ml" / name for name in (
            "owner_settled_synthetic.py", "owner_aligned_synthetic.py",
            "synthetic.py", "features.py", "outcomes.py",
        )],
    ]
    code_hashes = {str(path.resolve()): sha(path) for path in code}
    output.mkdir()
    for name, data in inputs.items():
        with (output / name).open("xb") as stream:
            stream.write(data)
    write(output / "preparation_plan.json", {
        "recorded_utc": datetime.now(UTC).isoformat(), "version": POLICY_VERSION,
        "input_sha256": hashes, "code_sha256": code_hashes,
        "candidates": protocol["development_candidates"], "final_seed": None,
        "models_authorized": False,
    })
    audits, all_rows = [], []
    for candidate in protocol["development_candidates"]:
        dataset = generate_owner_settled_dataset(
            anchors, base["simulation"], clarification, candidate["seed"], candidate["prefix"],
        )
        audit = validate_owner_settled_dataset(
            dataset, anchors, base["simulation"], clarification,
        )
        write(output / (candidate["prefix"] + "_transactions.json"), dataset)
        audits.append({"replica_id": candidate["prefix"], **audit})
        all_rows.extend(row for row in dataset["rows"] if row["phase"] == "study")
    known = [row for row in all_rows if row["late_payment"] is not None]
    for name, rows in (("desarrollo.csv", all_rows), ("desarrollo_etiquetado.csv", known)):
        assert rows
        with (output / name).open("x", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    write(output / "development_audits.json", audits)
    summary = {
        "version": POLICY_VERSION, "stage": "development_data_only",
        "study_rows": len(all_rows), "known_rows": len(known),
        "unknown_rows": len(all_rows) - len(known),
        "class_0": sum(row["late_payment"] == 0 for row in known),
        "class_1": sum(row["late_payment"] == 1 for row in known),
        "overdue_grants": sum(row["pending_overdue"] > 0 for row in all_rows),
        "settlement_policy_pass": all(a["settlement_policy_pass"] for a in audits),
        "coherence_accepted": False, "models_trained": False,
        "final_generated": False, "source_sha256": hashes, "code_sha256": code_hashes,
        "replicas": [{k: a[k] for k in (
            "replica_id", "study_loans", "study_label_counts", "mean_weekly_study_requests",
            "mean_weekly_study_grants", "mean_weekly_study_grant_clients", "adequacy",
            "settlement_policy_pass", "legacy_grant_scale_flag",
        )} for a in audits],
        "next_gate": (
            "Review the source units and granted scale before authorizing any new model protocol. "
            "No automatic acceptance from legacy tolerance."
        ),
    }
    assert all(sha(source / name) == digest for name, digest in hashes.items())
    assert all(sha(Path(path)) == digest for path, digest in code_hashes.items())
    write(output / "data_revision_report.json", summary)
    write(output / "manifest.json", {
        "files": {p.name: sha(p) for p in output.iterdir() if p.is_file()},
        "scope": "Data revision only; excludes manifest itself",
    })
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.sources, args.output_dir)
