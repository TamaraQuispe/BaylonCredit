"""Copy only the locally trusted V6 Final r1 web inputs; stdlib, no ML loading."""

import argparse
import importlib.util
import json
import re
from pathlib import Path

# Reuse byte/path/JSON safety helpers, not the historical 57-file preparer.
spec = importlib.util.spec_from_file_location(
    "historical_preparer", Path(__file__).with_name("prepare-aligned-v6-lab.py")
)
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
require, read_bytes, safe_path, sha, object_json = (
    legacy.require, legacy.read_bytes, legacy.safe_path, legacy.sha, legacy.object_json
)
FILES = legacy.FILES
PINS = {
    "final_manifest.json": "471e5bd3849e8ee8f2d79254823eb4dcfd7a679d67b49efc6257d467224a06cf",
    "freeze_before_final.json": "2faccb7cf2248a4eed21753b6b6dc336f82aaea5e1b19a589a912974d5837f7d",
}


def prepare(source, destination):
    source, destination = safe_path(source), safe_path(destination)
    require(source.is_dir(), "Experiment directory missing")
    require(not destination.exists(), "Destination must be a new directory; never overwrite")
    require(not destination.is_relative_to(source), "Destination cannot be inside experiment")
    pinned = {}
    for name, expected in PINS.items():
        data = read_bytes(source / name)
        require(sha(data) == expected, f"Untrusted revision: {name}")
        pinned[name] = object_json(data)
    manifest, freeze = pinned["final_manifest.json"], pinned["freeze_before_final.json"]
    for value in (manifest, freeze):
        require(value["version"] == legacy.VERSION and value["revision_id"] == "v6-final-r1"
                and value["display_name"] == "V6 Final", "Revision mismatch")
    hashes = manifest["files"]
    require(freeze["final_generation_calls"] == freeze["final_prediction_calls"] == 0,
            "FINAL was not frozen before scoring")
    require(all(hashes.get(name) == expected for name, expected in freeze["files"].items()),
            "Freeze changed after FINAL")
    contents = {}
    for name, expected in hashes.items():
        require(Path(name).name == name and name not in (".", "..")
                and re.fullmatch(r"[0-9a-f]{64}", expected), "Unsafe manifest entry")
        contents[name] = read_bytes(source / name)
        require(sha(contents[name]) == expected, f"SHA256 mismatch: {name}")
    report, frozen, provenance, artifacts, protocol, search = (
        object_json(contents[name]) for name in (
            legacy.REPORT, "frozen_selection.json", "provenance.json",
            "artifact_manifest.json", "effective_protocol.json", "cv_search.json",
        )
    )
    require(report["selection"] == frozen and report["provenance"] == provenance,
            "Report selection/provenance mismatch")
    for value in (report, frozen, provenance):
        require(value["revision_id"] == "v6-final-r1" and value["display_name"] == "V6 Final"
                and value["version"] == legacy.VERSION and value["origen"] == "simulado"
                and value["research_only"] is True and value["business_approval"] is False,
                "Research revision mismatch")
    require(report["feature_names"] == frozen["feature_names"]
            == protocol["feature_names"] == list(legacy.ILLUSTRATIVE), "Feature mismatch")
    require({key: provenance["runtime"].get(key) for key in legacy.RUNTIME} == legacy.RUNTIME,
            "Runtime mismatch")
    require(report["artifact_sha256"] == artifacts, "Artifact manifest mismatch")
    for name, expected in artifacts.items():
        require(hashes.get(name) == expected, f"Artifact mismatch: {name}")
    require(provenance["protocol_sha256"] == hashes["revision_protocol.json"],
            "Revision protocol mismatch")
    for name, expected in provenance["source_sha256"].items():
        require(hashes.get(name) == expected, f"Source signature mismatch: {name}")
    require(provenance["source_anchors"] == object_json(contents["APF3_OWNER_ANCHORS_V4.json"]),
            "Source anchors mismatch")
    require(provenance["code_sha256"]["/revision/academic_credit_pending_v6_final.py"]
            == "eac29527d158918b21c4a9bd88e447913ed113e902ce6f050e3246dfde2ac034"
            and provenance["code_sha256"]["/revision/policy.py"] == provenance["policy_sha256"]
            == "418af45fcdc1a5d952daac7aa5139bfa87d2a66ef126255f306cff3c66591f1f",
            "Frozen runner/policy signatures mismatch")
    winner = frozen["global_winner"]
    family = winner["family"]
    require(family == winner["params"]["family"] == "svm", "Unexpected exact-revision winner")
    require(winner == frozen["families"][family], "Family selection mismatch")
    candidates = [result for candidate in search["candidates"]
                  for result in candidate["threshold_results"]]
    require(winner in candidates and all(winner["review_policy"]["metrics"]["f2"]
            >= result["review_policy"]["metrics"]["f2"] for result in candidates),
            "Winner does not match development grid")
    require(report["models"][family]["threshold"] == winner["threshold"],
            "Frozen threshold mismatch")
    require(hashes["selected_model.joblib"] == hashes[family + ".joblib"]
            == artifacts["selected_model.joblib"], "Selected family artifact mismatch")
    require(object_json(contents["illustrative_input.json"]) == {"features": legacy.ILLUSTRATIVE}
            and protocol["illustrative_input"]["features"] == legacy.ILLUSTRATIVE,
            "Frozen illustrative input mismatch")

    # All validation precedes output creation. Exclusive writes never replace a bundle.
    require(destination.parent.is_dir(), "Destination parent must already exist")
    destination.mkdir()
    for name in FILES:
        with (destination / name).open("xb") as stream:
            stream.write(contents[name])
    web_manifest = {"version": legacy.VERSION, "files": {name: hashes[name] for name in FILES}}
    with (destination / "web_manifest.json").open("x", encoding="ascii") as stream:
        stream.write(json.dumps(web_manifest, indent=2) + "\n")
    for name in FILES:
        require(sha(read_bytes(destination / name)) == hashes[name], f"Copy mismatch: {name}")
    return {"destination": str(destination), "revision_id": "v6-final-r1",
            "experiment_hashes_checked": len(hashes), "web_manifest": web_manifest,
            "web_manifest_sha256": sha(read_bytes(destination / "web_manifest.json")),
            "model_loaded": False, "inference_executed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Trusted local experiment directory")
    parser.add_argument("--destination", type=Path, required=True, help="Fresh local web bundle")
    args = parser.parse_args()
    try:
        result = prepare(args.source, args.destination)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Preparation refused: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
