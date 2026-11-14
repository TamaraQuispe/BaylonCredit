"""Check the generated draft's evidence, hashes, PDF pages and editable document."""

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

from docx import Document
from pypdf import PdfReader

NAME = "APF3_TD_Grupo2_ML_Innovacion_Borrador"


def verify(directory: Path) -> None:
    manifest = json.loads((directory / "manifest.json").read_text())
    for filename, expected in manifest["files"].items():
        assert (
            hashlib.sha256((directory / filename).read_bytes()).hexdigest() == expected
        ), filename
    for filename, expected in manifest["sources"].items():
        assert hashlib.sha256(Path(filename).read_bytes()).hexdigest() == expected, (
            filename
        )
    planned = json.loads((directory / "verificacion-informe.json").read_text())
    reader = PdfReader(directory / (NAME + ".pdf"))
    pages = [page.extract_text() for page in reader.pages]
    references = next(
        index for index, text in enumerate(pages) if text.startswith("Referencias")
    )
    body_pages = references - 1
    assert body_pages <= 15
    assert body_pages == planned["planned_body_pages"]
    assert len(pages) == planned["planned_total_pages"], (
        "Unexpected page spill or blank page"
    )
    text = "\n".join(pages)
    assert not re.search(r"\{\{\w+\}\}", text), "Unresolved template"
    for value in (
        "U23204737",
        "U23231338",
        "U23259768",
        "U23251279",
        "0.6626",
        "0.6738",
        "0.346413",
        "FINAL-L00003",
        "FINAL-L00004",
        "FINAL-L00012",
        "simulado",
    ):
        assert value in text, value
    document = Document(directory / (NAME + ".docx"))
    assert len(document.inline_shapes) == 3
    assert len(document.tables) == planned["word_tables"]
    word_text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    word_text += "\n".join(
        cell.text
        for table in document.tables
        for row in table.rows
        for cell in row.cells
    )
    assert not re.search(r"\{\{\w+\}\}", word_text)
    with (directory / "dataset_desarrollo_simulado.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1622 and all(row["origen"] == "simulado" for row in rows)
    assert sum(row["late_payment"] == "" for row in rows) == 24
    assert len({row["loan_id"] for row in rows}) == 1622
    result = {
        "passed": True,
        "pdf_total_pages": len(pages),
        "pdf_body_pages": body_pages,
        "cover_pages": 1,
        "reference_and_annex_pages": len(pages) - body_pages - 1,
        "word_tables": len(document.tables),
        "embedded_figures": len(document.inline_shapes),
        "synthetic_csv_rows": len(rows),
        "unlabeled_rows": 24,
        "file_hashes_checked": len(manifest["files"]),
        "sources_unchanged_checked": len(manifest["sources"]),
        "word_physical_pagination": "Not rendered; PDF page count is the verified count",
        "human_review": "Pending; this is technical verification only",
    }
    target = directory / "verificacion-final.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    manifest["files"][target.name] = hashlib.sha256(target.read_bytes()).hexdigest()
    (directory / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    verify(parser.parse_args().directory)
