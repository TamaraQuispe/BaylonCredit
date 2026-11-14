"""Verify cached CV3 evidence and documents, then archive; never load or fit a model."""

import argparse
import csv
import hashlib
import json
import math
import re
import zipfile
from pathlib import Path

from docx import Document
from pypdf import PdfReader

NAME = "APF3_TD_Grupo2_ML_Innovacion_Borrador"


def verify(root: Path):
    experiment = root / "experimento"
    report = json.loads((experiment / "grouped_cv_report.json").read_text())
    frozen = json.loads((experiment / "frozen_selection.json").read_text())
    assert report["selection"] == frozen
    provenance = report["provenance"]
    assert (
        hashlib.sha256((experiment / "protocol.json").read_bytes()).hexdigest()
        == provenance["protocol_sha256"]
    )
    assert (
        hashlib.sha256(
            (root / "datos/ledger_desarrollo_original.json").read_bytes()
        ).hexdigest()
        == provenance["source_sha256"]
    )
    for name, expected in report["artifact_sha256"].items():
        assert hashlib.sha256((experiment / name).read_bytes()).hexdigest() == expected
    for name, filename in {
        "runner": "scripts/academic_credit_grouped_cv.py",
        **{n: f"app/ml/{n}.py" for n in ("features", "synthetic", "outcomes")},
    }.items():
        assert (
            hashlib.sha256((root / "codigo" / filename).read_bytes()).hexdigest()
            == provenance["code_sha256"][name]
        )
    development = json.loads((experiment / "development_rows.json").read_text())
    audit = json.loads((experiment / "fold_audit.json").read_text())
    coverage = [0] * len(development)
    for outer, calibration in zip(
        audit["outer"], audit["svm_outer_training_calibration"], strict=True
    ):
        train, validation = (
            set(outer["train_indices"]),
            set(outer["validation_indices"]),
        )
        assert not train & validation and train | validation == set(
            range(len(development))
        )
        assert not set(outer["train_client_ids"]) & set(outer["validation_client_ids"])
        for index in validation:
            coverage[index] += 1
        for inner in calibration["folds"]:
            assert (
                set(inner["train_indices"]) | set(inner["validation_indices"]) == train
            )
            assert not set(inner["train_client_ids"]) & set(
                inner["validation_client_ids"]
            )
    assert coverage == [1] * len(development)
    final = json.loads((experiment / "final_transactions.json").read_text())["rows"]
    assert not {r["client_id"] for r in development} & {r["client_id"] for r in final}
    cached = json.loads((experiment / "final_predictions.json").read_text())
    for name, saved in cached.items():
        matrix = [[0, 0], [0, 0]]
        threshold = report["models"][name]["threshold"]
        for row in saved["predictions"]:
            assert row["predicted"] == int(row["probability"] >= threshold)
            matrix[row["actual"]][row["predicted"]] += 1
        value = report["models"][name]["final"]
        assert matrix == value["confusion_matrix"]
        tn, fp = matrix[0]
        fn, tp = matrix[1]
        precision = tp / (tp + fp) if tp + fp else 0
        recall = tp / (tp + fn) if tp + fn else 0
        f2 = 5 * tp / (5 * tp + 4 * fn + fp) if 5 * tp + 4 * fn + fp else 0
        for key, result in (("precision", precision), ("recall", recall), ("f2", f2)):
            assert math.isclose(value[key], result, abs_tol=1e-12)
        assert value["n"] == tn + fp + fn + tp == len(saved["predictions"])
    repro = json.loads(
        (root / "reproduccion/verificacion-reproduccion.json").read_text()
    )
    assert repro["passed"] and repro["clean_venv_no_system_site_packages"]
    assert (
        repro["all_12_metric_sets_identical"]
        and not repro["independent_new_validation"]
    )
    reproduced = json.loads(
        (root / "reproduccion/experimento/grouped_cv_report.json").read_text()
    )
    for name in report["models"]:
        for split in ("train", "oof", "final"):
            assert report["models"][name][split] == reproduced["models"][name][split]
    assert report["illustrative_inference"] == reproduced["illustrative_inference"]
    csv_counts = {}
    for filename, expected in (
        ("desarrollo.csv", len(development)),
        ("final.csv", len(final)),
    ):
        with (root / "datos" / filename).open() as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == expected and all(
            row["origen"] == "simulado" for row in rows
        )
        csv_counts[filename] = len(rows)
    pages = [
        page.extract_text()
        for page in PdfReader(root / "informe" / (NAME + ".pdf")).pages
    ]
    references = next(
        index for index, text in enumerate(pages) if text.startswith("Referencias")
    )
    assert references - 1 <= 15
    full_text = "\n".join(pages)
    assert not re.search(r"\{\{\w+\}\}", full_text)
    for value in (
        "U23204737",
        "U23231338",
        "U23259768",
        "U23251279",
        "0,14133",
        "0,73114",
    ):
        assert value in full_text, value
    document = Document(root / "informe" / (NAME + ".docx"))
    assert len(document.inline_shapes) == 3
    checks = {
        "passed": True,
        "cv_outer_folds": len(audit["outer"]),
        "oof_every_row_predicted_once": True,
        "group_disjoint": True,
        "final_metrics_verified_from_cached_predictions_only": True,
        "clean_reproduction_identical": True,
        "csv_rows": csv_counts,
        "pdf_total_pages": len(pages),
        "pdf_body_pages": references - 1,
        "word_tables": len(document.tables),
        "figures": len(document.inline_shapes),
        "new_model_evaluation_during_verification": False,
        "human_review": "Pending; technical verification only",
    }
    (root / "verificacion-paquete.json").write_text(json.dumps(checks, indent=2) + "\n")
    paths = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.name != "manifest.json"
    ]
    manifest = {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    archive = root.with_suffix(".zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        for path in [*paths, root / "manifest.json"]:
            handle.write(path, arcname=str(Path(root.name) / path.relative_to(root)))
    with zipfile.ZipFile(archive) as handle:
        assert handle.testzip() is None
    print(
        json.dumps(
            {**checks, "zip": str(archive), "zip_bytes": archive.stat().st_size},
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    verify(parser.parse_args().root)
