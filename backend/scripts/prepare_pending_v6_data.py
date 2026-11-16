"""Prepare only the two predeclared V6 DEV histories, never models or FINAL."""

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

from app.ml.owner_pending_synthetic import (  # noqa: E402
    POLICY_VERSION,
    PROTOCOL_SHA256,
    REVIEW_SHA256,
    _validate_inputs,
    generate_owner_pending_dataset,
    validate_owner_pending_dataset,
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
        "APF3_OWNER_ANCHORS_V4.json",
        "APF3_OWNER_REVIEW_V5.json",
        "APF3_PENDING_V6_DATA_PROTOCOL.json",
    )
    inputs = {name: (source / name).read_bytes() for name in filenames}
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in inputs.items()}
    assert (
        hashes[filenames[0]] == "81f858bc8827c88e41352745f65345a72d2b9d06361046bc86d3f07540806064"
    )
    assert hashes[filenames[1]] == REVIEW_SHA256
    assert hashes[filenames[2]] == PROTOCOL_SHA256
    anchors, review, protocol = [json.loads(inputs[name]) for name in filenames]
    simulation = protocol["simulation"]
    _validate_inputs(anchors, simulation, review, protocol)
    assert protocol["final_dataset"] is None
    code = [
        Path(__file__),
        *[
            BACKEND / "app/ml" / name
            for name in (
                "owner_pending_synthetic.py",
                "owner_aligned_synthetic.py",
                "synthetic.py",
                "features.py",
                "outcomes.py",
            )
        ],
    ]
    code_hashes = {str(path.resolve()): sha(path) for path in code}
    output.mkdir()
    for name, data in inputs.items():
        with (output / name).open("xb") as stream:
            stream.write(data)
    write(
        output / "preparation_plan.json",
        {
            "recorded_utc": datetime.now(UTC).isoformat(),
            "version": POLICY_VERSION,
            "input_sha256": hashes,
            "code_sha256": code_hashes,
            "candidates": protocol["development_candidates"],
            "final_seed": None,
            "models_authorized": False,
            "due_cutoff_status": "TEAM ASSUMPTION: hard 20:00 cutoff, not exact owner confirmation",
        },
    )
    audits, all_rows = [], []
    for candidate in protocol["development_candidates"]:
        dataset = generate_owner_pending_dataset(
            anchors,
            simulation,
            review,
            protocol,
            candidate["seed"],
            candidate["prefix"],
        )
        audit = validate_owner_pending_dataset(dataset, anchors, simulation, review, protocol)
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
        "version": POLICY_VERSION,
        "stage": "development_data_only",
        "study_rows": len(all_rows),
        "known_rows": len(known),
        "unknown_rows": len(all_rows) - len(known),
        "class_0": sum(row["late_payment"] == 0 for row in known),
        "class_1": sum(row["late_payment"] == 1 for row in known),
        "pending_grants": sum(a["pending_grants"] for a in audits),
        "pending_policy_pass": all(a["pending_policy_pass"] for a in audits),
        "coherence_accepted": False,
        "models_trained": False,
        "final_generated": False,
        "source_sha256": hashes,
        "code_sha256": code_hashes,
        "replicas": [
            {
                k: a[k]
                for k in (
                    "replica_id",
                    "clients",
                    "requests",
                    "all_loans",
                    "warmup_loans",
                    "study_loans",
                    "study_label_counts",
                    "mean_weekly_study_requests",
                    "mean_weekly_study_grants",
                    "mean_weekly_study_grant_clients",
                    "amount_precision_counts",
                    "adequacy",
                    "source_review_classifications",
                    "legacy_grant_scale_flag",
                )
            }
            for a in audits
        ],
        "limits": [
            "23 intentional V5 sample classifications, not approval of all V6 rows",
            "12 clients per example history, not a measured fixed real population",
            "20:00 hard due cutoff is a TEAM ASSUMPTION; grace never relabels lateness",
            "0.75 rounded / 0.25 exact-price scenario is a TEAM ASSUMPTION, not measured",
            "Observed whole/.50 counts include coincidentally rounded exact-price draws",
            "Finite complete-payment plans do not estimate permanent loss",
            "Scale flags and adequacy are descriptive, not global coherence acceptance",
        ],
        "next_gate": (
            "Review DEV data before any separately authorized model protocol; no reseeding"
        ),
    }
    with (output / "README.md").open("x") as stream:
        stream.write(
            "# Pending V6 DEV Data\n\n"
            "Fictional development data only. No models, FINAL, or production changes.\n"
            "See data_revision_report.json for counts and limitations and development_audits.json "
            "for weekly requests/grants, payment hours and source sample classifications.\n"
            "Source review concerns 23 intentional V5 sample items, not all V6 rows.\n"
            "Hard 20:00 cutoff and 0.75/0.25 amount mixture are TEAM ASSUMPTIONS.\n"
            "12 clients are an example pool, not a measured real fixed population.\n"
            "No global coherence acceptance or predictive validation is claimed.\n"
        )
    assert all(sha(source / name) == digest for name, digest in hashes.items())
    assert all(sha(Path(path)) == digest for path, digest in code_hashes.items())
    write(output / "data_revision_report.json", summary)
    write(
        output / "manifest.json",
        {
            "files": {p.name: sha(p) for p in output.iterdir() if p.is_file()},
            "scope": "Data revision only; excludes manifest itself; no private DOCX copied",
        },
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.sources, args.output_dir)
