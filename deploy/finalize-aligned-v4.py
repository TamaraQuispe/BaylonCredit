"""Validate frozen V4 deliverables and publish a new ZIP, without running ML/tools.

Requires python-docx, python-pptx and pypdf in the document venv. External source
paths recorded by the generators must still exist for source-hash validation.
No generator, reproduction command, verifier, browser, backend or git is invoked.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile

from docx import Document
from pptx import Presentation
from pypdf import PdfReader

DEFAULT_ROOT = Path("/Users/tamaraalison/Downloads/APF3_Grupo2_Alineado_V4")
FINAL_SHA = "86831dabd16b66499afbea6cc7f621c6dba5827367ae2526c788396900872558"
OWNER_SHA = "45bc22a10ad5dccf323708b8aeabb780d8de4629ff5087cca2582c7dd055819f"
REPORT = "APF3_TD_Grupo2_ML_Innovacion_Borrador"
DECK = "APF3_TD_Grupo2_ML_Innovacion"
NOTES = "APF3_Grupo2_Guion_12min"
HISTORY = "historial-documental-inicial"
CACHES = {"__pycache__", ".cache", ".ruff_cache", ".pytest_cache", ".mypy_cache"}
LEGACY = (
    *(REPORT + ext for ext in (".docx", ".html", ".md", ".pdf")),
    "figuras",
    "manifest.json",
    "verificacion-informe-v4.json",
    "verificacion-paginacion-v4.json",
    "verificacion-render.json",
    *(f"vista-{name}.png" for name in ("anexo-v4", "eda-v4", "eda", "matriz-v4")),
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf-8"
    )


def relative(name):
    path = PurePosixPath(name)
    require(
        bool(name)
        and not path.is_absolute()
        and ".." not in path.parts
        and "\\" not in name
        and path.as_posix() == name
        and name != ".",
        f"Unsafe relative path: {name!r}",
    )
    return path


def inventory(root):
    files = {}
    for directory, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in CACHES)
        for name in [*dirs, *names]:
            if name == ".DS_Store" or name in CACHES or name.endswith((".pyc", ".pyo")):
                continue
            path = Path(directory, name)
            require(not path.is_symlink(), f"Symlink forbidden: {path}")
            require(path.is_file() or path.is_dir(), f"Non-regular entry: {path}")
            require(
                "ficha_propietario" not in name.casefold(),
                f"Private owner source must not be packaged: {path}",
            )
            if path.is_file():
                files[path.relative_to(root).as_posix()] = path
    return dict(sorted(files.items()))


def check_hashes(base, mapping):
    require(isinstance(mapping, dict) and bool(mapping), f"Empty hash map: {base}")
    for name, expected in mapping.items():
        relative(name)
        require(
            isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected),
            f"Invalid SHA256: {name}",
        )
        path = base / name
        require(
            path.is_file() and digest(path) == expected,
            f"SHA256 mismatch/missing: {path}",
        )


def all_true(value, label):
    require(isinstance(value, dict) and bool(value), f"Empty checks: {label}")
    for key, item in value.items():
        if isinstance(item, dict):
            all_true(item, f"{label}/{key}")
        else:
            require(item is True, f"Failed check: {label}/{key}")


def normalize(text):
    return re.sub(r"\W+", "", text).lower()


def pdf_pages(path, count, width, height):
    pdf = PdfReader(path)
    require(
        not pdf.is_encrypted and len(pdf.pages) == count,
        f"PDF pages/encryption: {path}",
    )
    texts = []
    for index, page in enumerate(pdf.pages, 1):
        for box in (page.mediabox, page.cropbox):
            require(
                abs(float(box.width) - width) < 1
                and abs(float(box.height) - height) < 1,
                f"PDF dimensions, page {index}: {path}",
            )
        require(
            not page.rotation and float(page.get("/UserUnit", 1)) == 1,
            f"Unexpected PDF rotation/scale: {path}, page {index}",
        )
        texts.append(page.extract_text() or "")
    return texts


def check_sections(audit, texts):
    sections = audit["sections"]
    require(len(sections) == len(texts), "Render section/page count differs")
    for section, text in zip(sections, texts, strict=True):
        require(
            section["horizontal_overflow"] == []
            and 0 < section["height_px"] <= audit["printable_height_px"],
            f"Render overflow: {section['title']}",
        )
        require(
            normalize(section["title"]) in normalize(text),
            f"PDF section title missing: {section['title']}",
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    root = parser.parse_args().root.expanduser().resolve(strict=True)
    require(root.is_dir(), f"Not a directory: {root}")
    zip_path = root.parent / (root.name + ".zip")
    sha_path = zip_path.with_suffix(".zip.sha256")
    for path in (
        zip_path,
        sha_path,
        root / "manifest-entrega.json",
        root / "verificacion-entrega.json",
    ):
        require(not os.path.lexists(path), f"Refusing to overwrite: {path}")

    files = inventory(root)
    required = [
        "README.md",
        "manifest-paquete.json",
        "reproducir-v4.py",
        "requirements.txt",
        "verificacion-reproduccion.json",
        "estado-artefactos.json",
        "entorno-verificacion.json",
        "entorno-reproduccion.json",
        "entorno-empaquetado.json",
        "comandos-reproduccion.json",
        "inferencia-original.json",
        "inferencia-reproduccion.json",
        "informe/manifest.json",
        "informe/verificacion-informe-v4.json",
        "informe/verificacion-paginacion-v4.json",
        "informe/verificacion-render.json",
        "sustentacion/plan-notas-v4.json",
        "sustentacion/plan-sustentacion.json",
        "sustentacion/revision-diseno.json",
        "sustentacion/Guion_completo_con_indicaciones.md",
        *(f"informe/{REPORT}{ext}" for ext in (".md", ".docx", ".html", ".pdf")),
        *(f"sustentacion/{NOTES}{ext}" for ext in (".md", ".docx", ".html", ".pdf")),
        *(f"sustentacion/{DECK}{ext}" for ext in (".pptx", ".html", ".pdf")),
        *(f"sustentacion/vistas/{index:02}.png" for index in range(1, 14)),
        *(f"reproduccion-comando-{index}.log" for index in range(1, 4)),
    ]
    require(
        all(name in files for name in required),
        f"Missing deliverables: {sorted(set(required) - files.keys())}",
    )
    initial = {name: digest(path) for name, path in files.items()}
    require(
        OWNER_SHA not in initial.values(),
        "Private owner document bytes found in package",
    )
    log = [
        "Preflight: required deliverables, regular paths and private-source exclusion passed."
    ]
    package = load(root / "manifest-paquete.json")
    frozen = package["experiment_sha256"]
    require(len(frozen) == 24, "Expected 24 frozen experiment files")
    for directory, field in (
        ("experimento", "experiment_sha256"),
        ("codigo", "code_sha256"),
        ("datos", "data_sha256"),
        ("", "support_sha256"),
    ):
        mapping = package[field]
        check_hashes(root / directory, mapping)
        if directory:
            actual = {
                name.removeprefix(directory + "/")
                for name in files
                if name.startswith(directory + "/")
            }
            require(
                actual == set(mapping), f"Unmanifested/missing files in {directory}"
            )

    report_audit = load(root / "informe/verificacion-informe-v4.json")
    old_root = Path(report_audit["experiment_directory"]).parent
    source_snapshot = {}

    def check_sources(mapping):
        require(isinstance(mapping, dict) and bool(mapping), "Missing source hash map")
        require(
            FINAL_SHA in mapping.values(),
            "Source map omits final verification fingerprint",
        )
        for name, expected in mapping.items():
            path = Path(name)
            if path.is_absolute():
                if path.is_relative_to(old_root):
                    path = root / path.relative_to(old_root)
            else:
                path = root / relative(name)
            require(
                "ficha_propietario" not in path.name.casefold()
                and expected != OWNER_SHA,
                f"Refusing to read private owner source: {name}",
            )
            require(
                path.is_file() and digest(path) == expected,
                f"Source changed/missing (regenerate its deliverable first): {path}",
            )
            source_snapshot[path] = expected

    evidence = load(root / "verificacion-reproduccion.json")
    require(
        initial["verificacion-reproduccion.json"] == FINAL_SHA
        and evidence["passed"] is True,
        "Final verification evidence SHA256/passed differs",
    )
    checks = evidence["checks"]
    all_true(checks, "reproduction")
    counts = {
        "raw": 12,
        "policy": 12,
        "exact_file_sha256": 15,
        "learned_artifact_state": 5,
    }
    for key, count in counts.items():
        require(len(checks[key]) == count, f"Wrong verification count: {key}")
    for name in checks["exact_file_sha256"]:
        require(
            digest(root / "experimento" / relative(name))
            == digest(root / "reproduccion" / name),
            f"Reproduction bytes differ: {name}",
        )
    models = {"tree", "svm", "most_frequent", "constant_1", "selected_model"}
    states = load(root / "estado-artefactos.json")["models"]
    require(
        set(states) == models == set(checks["learned_artifact_state"])
        and states == evidence["artifact_serialization"]["models"],
        "Learned-state evidence differs",
    )
    for name, state in states.items():
        require(
            state["learned_state_equal"] is True
            and state["binary_equal"] is False
            and len(state["state_sha256"]) == 2
            and state["state_sha256"][0] == state["state_sha256"][1],
            f"Invalid learned-state/binary caveat: {name}",
        )
        require(
            state["binary_sha256"]
            == [
                digest(root / folder / (name + ".joblib"))
                for folder in ("experimento", "reproduccion")
            ],
            f"Artifact changed since final verification: {name}",
        )
    for folder in ("experimento", "reproduccion"):
        base = root / folder
        artifacts = load(base / "artifact_manifest.json")
        require(
            set(artifacts)
            == {name + ".joblib" for name in models} | {"frozen_selection.json"},
            f"Artifact keys differ: {folder}",
        )
        check_hashes(base, artifacts)
        selection = load(base / "frozen_selection.json")
        check_hashes(base, selection["decision_sha256"])
        experiment_report = load(base / "aligned_v4_report.json")
        require(
            selection == experiment_report["selection"],
            f"Selection/report differ: {folder}",
        )
        require(
            artifacts["selected_model.joblib"] == artifacts["svm.joblib"],
            "Selected model differs",
        )
        for family, model in experiment_report["models"].items():
            for split in ("train", "oof", "final"):
                recorded = evidence["results"]["models"][family]
                require(
                    recorded["raw"][split] == model[split]
                    and recorded["policy"][split]
                    == model["review_policy"][split]["metrics"],
                    f"Metrics differ from final evidence: {folder}/{family}/{split}",
                )
    runtime = load(root / "entorno-verificacion.json")
    require(
        runtime == evidence["verification_runtime"] and runtime["clean_venv"] is True,
        "Current-at-verification clean environment evidence differs",
    )
    require(
        runtime["python"] == "3.12.14"
        and runtime["prefix"] != runtime["base_prefix"]
        and "include-system-site-packages = false" in runtime["venv_config"],
        "Unclean environment",
    )
    for name in ("entorno-empaquetado.json", "entorno-reproduccion.json"):
        historical = load(root / name)
        for key in ("python", "packages"):
            require(
                runtime[key] == historical[key], f"Environment mismatch: {name}/{key}"
            )
    require(
        all(
            p["location"].startswith(runtime["prefix"] + "/")
            for p in runtime["packages"].values()
        ),
        "System packages in verification environment",
    )
    log.append(
        "Existing final evidence read only: 12 raw, 12 policy, 15 files, 5 learned states; no rerun."
    )

    report_manifest = load(root / "informe/manifest.json")
    require(
        {
            name.removeprefix("informe/")
            for name in required
            if name.startswith("informe/") and name != "informe/manifest.json"
        }
        <= report_manifest["files"].keys(),
        "Report manifest omits a deliverable",
    )
    check_hashes(root / "informe", report_manifest["files"])
    require(
        report_manifest["sources"] == report_audit["source_sha256"],
        "Report source maps differ",
    )
    check_sources(report_manifest["sources"])
    check_sources(report_audit["source_sha256"])
    require(
        report_audit["experiment_sha256_before"]
        == frozen
        == report_audit["experiment_sha256_after"],
        "Report frozen snapshot differs",
    )
    require(
        report_audit["reproduction"]["evidence_sha256"] == FINAL_SHA
        and report_audit["reproduction"]["verified"] is True
        and report_audit["reproduction"]["evidence_passed"] is True,
        "Report cites stale evidence",
    )
    for key in (
        "sources_modified",
        "new_training",
        "new_predictions",
        "new_tuning",
        "private_owner_document_read_or_published",
    ):
        require(report_audit[key] is False, f"Report invariant failed: {key}")
    require(
        report_audit["frozen_decision_and_artifact_hashes_checked"] is True
        and report_audit["experiment_unchanged_at_pdf_verification"] is True
        and report_audit["planned_body_pages"] == 14
        and report_audit["planned_total_pages"] == 25,
        "Report checks/pages differ",
    )
    pagination = load(root / "informe/verificacion-paginacion-v4.json")
    physical = {key: value for key, value in pagination.items() if key != "sections"}
    require(
        physical == report_audit["pdf_physical_pagination"],
        "Report pagination evidence differs",
    )
    require(
        pagination["body_pages"] == 14
        and pagination["body_pages"] <= 15
        and pagination["pdf_total_pages"] == 25
        and pagination["references_start_page"] == 16
        and pagination["cover_pages"] == 1
        and pagination["references_pages"] == 1
        and pagination["appendix_pages"] == 9
        and pagination["pdf_a4_pages"] is True
        and pagination["overflow"] is False
        and pagination["pdf_section_titles_match_one_to_one"] is True,
        "Report pagination failed",
    )
    report_texts = pdf_pages(root / "informe" / (REPORT + ".pdf"), 25, 595.28, 841.89)
    check_sections(pagination, report_texts)
    render = load(root / "informe/verificacion-render.json")
    require(len(render["pages"]) == 25, "Report render count differs")
    for page, text in zip(render["pages"], report_texts, strict=True):
        require(
            normalize(page["title"]) in normalize(text), "Report render title differs"
        )
    for prefix, name in (("informe", REPORT), ("sustentacion", NOTES)):
        document = Document(root / prefix / (name + ".docx"))
        require(bool(document.paragraphs), f"Empty DOCX: {name}")
        for section in document.sections:
            require(
                abs(section.page_width.mm - 210) < 1
                and abs(section.page_height.mm - 297) < 1,
                f"DOCX section is not A4: {name}",
            )
        if prefix == "informe":
            require(
                len(document.inline_shapes) == report_audit["embedded_figures"] == 3
                and len(document.tables) == report_audit["word_tables"],
                "Report DOCX objects differ",
            )
    log.append(
        "Report: relative manifest and current sources, 14 body/25 A4 PDF pages, no overflow."
    )

    notes_plan = load(root / "sustentacion/plan-notas-v4.json")
    deck_plan = load(root / "sustentacion/plan-sustentacion.json")
    check_sources(notes_plan["source_sha256"])
    check_sources(deck_plan["source_sha256"])
    require(
        {NOTES + ext for ext in (".md", ".docx", ".html", ".pdf")}
        | {"Guion_completo_con_indicaciones.md"}
        <= notes_plan["files_sha256"].keys(),
        "Notes output hash map omits a deliverable",
    )
    check_hashes(root / "sustentacion", notes_plan["files_sha256"])
    require(
        deck_plan["experiment_sha256"] == frozen
        and deck_plan["experiment_unchanged"] is True,
        "Deck frozen snapshot differs",
    )
    require(
        notes_plan["reproduction"]["sha256"] == FINAL_SHA
        and notes_plan["report_verification_reproduction_digest_matches_current"]
        is True,
        "Notes cite stale reproduction evidence",
    )
    for plan in (notes_plan, deck_plan):
        require(
            plan["slides"] == 13
            and plan["planned_seconds"] == 720
            and plan["spoken_words"] == 1329
            and plan["live_inference_reserved_seconds"] == 50,
            "Deck/notes timing or word count differs",
        )
        require(
            plan["new_training"] is False and plan["new_predictions"] is False,
            "ML rerun declared",
        )
    require(
        notes_plan["question_count"] == 18
        and notes_plan["interventions"] == 13
        and notes_plan["spoken_planned_seconds"] == 670
        and notes_plan["slide_9"] == {"spoken_seconds": 20, "live_seconds": 50}
        and notes_plan["private_owner_document_read_or_published"] is False,
        "Notes plan differs",
    )
    text = (root / "sustentacion/Guion_completo_con_indicaciones.md").read_text(
        encoding="utf-8"
    )
    parts = re.split(
        r"(?m)^## (\d+)\. (.+)\n", text.split("# Preguntas dif\u00edciles", 1)[0]
    )
    notes = []
    for index in range(1, len(parts), 3):
        number, title, body = parts[index : index + 3]
        timing = re.search(
            r"\*\*Tiempo:\*\* (\d+) s \| \*\*Expositor propuesto:\*\* (.+)", body
        )
        require(timing is not None, f"Missing note timing: {number}")
        plain = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
        spoken = "\n\n".join(
            block.strip()
            for block in plain.split("\n\n")
            if block.strip() and not block.strip().startswith(("**", "|"))
        )
        notes.append(
            {
                "number": int(number),
                "title": title,
                "seconds": int(timing[1]),
                "owner": timing[2],
                "notes": body.strip(),
                "spoken": spoken,
                "spoken_words": len(re.findall(r"\S+", spoken)),
            }
        )
    require(
        [n["number"] for n in notes] == list(range(1, 14)), "Expected 13 ordered notes"
    )
    require(
        sum(n["seconds"] for n in notes) == 720
        and sum(n["spoken_words"] for n in notes) == 1329,
        "Actual notes timing/words differ",
    )
    speaker_seconds = Counter()
    for note in notes:
        speaker_seconds[note["owner"]] += note["seconds"]
    for plan in (notes_plan, deck_plan):
        require(
            dict(speaker_seconds) == plan["planned_speaker_seconds"],
            "Speaker times differ",
        )
        require(len(plan["slides_data"]) == 13, "Slide metadata count differs")
        for actual, planned in zip(notes, plan["slides_data"], strict=True):
            keys = (
                ("number", "owner", "seconds", "spoken_words", "title")
                if plan is notes_plan
                else ("number", "owner", "seconds")
            )
            require(
                all(actual[k] == planned[k] for k in keys),
                "Slide/notes metadata differs",
            )
    questions = text.split("# Preguntas dif\u00edciles y respuestas breves", 1)[
        1
    ].split("# Lista de revisi\u00f3n humana pendiente", 1)[0]
    qa = re.findall(
        r"(?m)^\*\*\u00bf.*?(?=\n\n\*\*\u00bf|\Z)", questions.strip(), flags=re.DOTALL
    )
    compact = (root / "sustentacion" / (NOTES + ".md")).read_text(encoding="utf-8")
    require(
        len(qa) == 18 and len(re.findall(r"(?m)^\*\*\u00bf", compact)) == 18,
        "Expected 18 questions",
    )
    require(
        FINAL_SHA in text and OWNER_SHA in text and not re.search(r"\{\{\w+\}\}", text),
        "Notes missing source fingerprints or contain placeholders",
    )
    notes_texts = pdf_pages(
        root / "sustentacion" / (NOTES + ".pdf"), 10, 595.28, 841.89
    )
    notes_pdf = normalize("\n".join(notes_texts))
    for chunk in [*qa, *(p for n in notes for p in n["spoken"].split("\n\n"))]:
        require(
            normalize(chunk) in notes_pdf and normalize(chunk) in normalize(compact),
            "Spoken paragraph/question missing from notes PDF/Markdown",
        )
    notes_render = notes_plan["render"]
    require(
        notes_render["pdf_pages"] == 10
        and notes_render["pdf_a4"] is True
        and notes_render["overflow"] is False
        and notes_render["offline"] is True
        and notes_render["external_requests"] == []
        and notes_render["pdf_titles_match_one_to_one"] is True
        and notes_render["all_spoken_and_qa_text_present"] is True,
        "Notes render checks failed",
    )
    check_sections(notes_render, notes_texts)

    presentation = Presentation(root / "sustentacion" / (DECK + ".pptx"))
    require(len(presentation.slides) == 13, "Expected 13 editable PPTX slides")
    require(
        abs(presentation.slide_width / 914400 * 96 - 1280) < 1
        and abs(presentation.slide_height / 914400 * 96 - 720) < 1,
        "PPTX canvas differs",
    )
    # CSS pixels are 96 dpi; PDF points are 72 dpi, hence 1280x720 -> 960x540.
    deck_texts = pdf_pages(root / "sustentacion" / (DECK + ".pdf"), 13, 960, 540)
    html = (root / "sustentacion" / (DECK + ".html")).read_text(encoding="utf-8")
    css = re.sub(r"\s+", "", html)
    require(
        re.search(r"@page\{size:13\.33333\d*in7\.5in;margin:0", css)
        and ".slide{width:1280px;height:720px;" in css
        and len(re.findall(r'<section class="slide"', html)) == 13,
        "Deck HTML print scale differs",
    )
    design = load(root / "sustentacion/revision-diseno.json")
    require(design["overflows"] == [], "Deck design has overflows")
    editable_counts = []
    for slide, note, planned, pdf_text in zip(
        presentation.slides, notes, deck_plan["slides_data"], deck_texts, strict=True
    ):
        require(
            slide.has_notes_slide
            and slide.notes_slide.notes_text_frame.text == note["notes"],
            f"PPTX notes differ: {note['number']}",
        )
        native_texts = []
        for shape in slide.shapes:
            require(
                shape.left >= 0
                and shape.top >= 0
                and shape.left + shape.width <= presentation.slide_width + 2
                and shape.top + shape.height <= presentation.slide_height + 2,
                f"PPTX shape out of bounds: {note['number']}",
            )
            if shape.has_text_frame:
                native_texts.extend(
                    p.text for p in shape.text_frame.paragraphs if p.text.strip()
                )
            if shape.has_table:
                native_texts.extend(
                    c.text
                    for row in shape.table.rows
                    for c in row.cells
                    if c.text.strip()
                )
        require(
            len(native_texts) >= 3,
            f"Slide is not editable native text: {note['number']}",
        )
        require(
            normalize(planned["title"]) in normalize("\n".join(native_texts)),
            "PPTX title differs",
        )
        for value in [planned["title"], *native_texts]:
            require(
                normalize(value) in normalize(pdf_text),
                f"PPTX/PDF text differs on slide {note['number']}: {value[:100]}",
            )
        editable_counts.append(len(native_texts))
    log.append(
        "Defense: 13 editable slides with exact notes; 720 seconds/1329 words/18 Q&A; 10 A4 notes pages."
    )
    log.append(
        "Deck PDF: 13 pages, 960x540 pt = 1280x720 CSS px; empty recorded design overflows."
    )

    # Only these initial documentary outputs move; each historical manifest keeps
    # its own relative file paths valid. Its old source hashes are historical.
    moving = [name for name in LEGACY if (root / name).exists()]
    require(
        not any(
            PurePosixPath(name).parts[0] in moving for name in package["support_sha256"]
        ),
        "Main package manifest now references an obsolete root file; refusing to move it",
    )
    history_readme = (
        "# Historial documental inicial\n\n"
        "superados, no usar para entrega; actuales informe/\n\n"
        "Originales conservados sin cambiar sus bytes. El manifest.json de esta carpeta\n"
        "describe la generacion inicial y sus fuentes antiguas, no la entrega actual.\n"
        "Informe actual: [informe](../informe/). Sustentacion actual: [sustentacion](../sustentacion/).\n"
    )
    require(
        not (root / HISTORY).exists(),
        f"History destination already exists: {root / HISTORY}",
    )
    publication = {}
    for name, path in files.items():
        first = PurePosixPath(name).parts[0]
        target = HISTORY + "/" + name if first in moving else name
        publication[target] = path
    for name in report_manifest["files"]:
        require(
            "informe/" + name in publication, "Report manifest file not in publication"
        )
    readme = (root / "README.md").read_text(encoding="utf-8")
    require(
        "<!-- aligned-v4-final-delivery -->" not in readme, "README already finalized"
    )
    readme = readme.replace("No se ha creado ZIP.", "").rstrip() + (
        "\n\n<!-- aligned-v4-final-delivery -->\n\n## Entrega documental V4\n\n"
        f"- [Informe PDF](informe/{REPORT}.pdf), [Word](informe/{REPORT}.docx) "
        "y [manifiesto](informe/manifest.json): 14 paginas de cuerpo, 25 A4 en PDF.\n"
        f"- [Presentacion editable](sustentacion/{DECK}.pptx) y "
        f"[PDF de 13 diapositivas](sustentacion/{DECK}.pdf).\n"
        f"- [Guion PDF](sustentacion/{NOTES}.pdf) y "
        "[plan de notas](sustentacion/plan-notas-v4.json): 10 paginas A4, 18 preguntas.\n"
        f"- [Historial inicial]({HISTORY}/README.md): originales superados, no usar para entrega.\n"
        "- [Manifiesto global](manifest-entrega.json) y [verificacion](verificacion-entrega.json).\n\n"
        f"ZIP publicado como `../{zip_path.name}`; SHA-256 en `../{sha_path.name}`. "
        "Su publicacion exige CRC y cotejo SHA-256 de todos los archivos descomprimidos. "
        "El checksum queda fuera del ZIP para evitar autorreferencia.\n\n"
        "Verificacion tecnica, no revision humana: revision individual, ensayo y demo humana "
        "siguen pendientes. Roles propuestos. No es validacion independiente ni aprobacion comercial. "
        "Se conservan las salvedades Joblib, tres timestamps y dos hashes derivados. "
        "Este cierre no reejecuta ML ni el verificador de reproduccion; conserva sus bytes y fecha.\n"
    )
    log.append(f"Archiving only allowlisted initial outputs: {moving}")

    with tempfile.TemporaryDirectory(
        prefix=".finalize-v4-", dir=root.parent
    ) as temporary:
        stage = Path(temporary)
        (stage / "README.md").write_text(readme, encoding="utf-8")
        (stage / "history-README.md").write_text(history_readme, encoding="utf-8")
        publication["README.md"] = stage / "README.md"
        publication[HISTORY + "/README.md"] = stage / "history-README.md"
        verification = {
            "generated_utc": datetime.now(UTC).isoformat(),
            "passed": True,
            "scope": "Document/integrity preflight; ZIP publication gated by CRC and full SHA256 readback",
            "counts": {
                **counts,
                "experiment_frozen_files": 24,
                "report_body_pages": 14,
                "report_pdf_pages": 25,
                "slides": 13,
                "planned_seconds": 720,
                "spoken_words": 1329,
                "questions": 18,
                "notes_pdf_pages": 10,
                "editable_text_objects_per_slide": editable_counts,
                "package_files_including_manifests": len(publication) + 2,
            },
            "methods": {
                "integrity": "SHA256 of actual bytes; generator schemas checked without invoking them",
                "sources": "All current report/notes/deck source maps; external paths required; root paths remapped",
                "pdf": "pypdf page count, MediaBox/CropBox, unit scale, per-page text and render section limits",
                "pptx": "python-pptx native editable text/tables, bounds, exact speaker notes and PDF text",
                "spoken": "Same fenced-code/block filtering as parse_notes; re.findall(r'\\S+', spoken)",
                "zip": "Root-prefixed paths, ZipFile.testzip() is None; SHA256 via ZipFile.open, no disk extraction",
                "publication": "Staged archive checked before mutations; exclusive ZIP/checksum, no overwrite",
            },
            "limits": [
                "No human review, rehearsal, demo or independent validation is certified.",
                "DOCX/PPTX are not rendered in native Microsoft Office; recorded overflow audit is read only.",
                "Environment is the clean runtime recorded by final evidence, not a fresh runtime probe.",
                "Five learned states equal; five Joblib binaries differ. No model is deserialized here.",
                "Hashes detect change, not publisher identity; no digital signature.",
            ],
            "excluded_time_fields": evidence["methods"]["excluded_time_fields"],
            "derived_hash_exceptions": evidence["methods"]["derived_hash_exceptions"],
            "final_evidence_sha256": FINAL_SHA,
            "frozen_experiment_sha256": frozen,
            "main_manifest_sha256": initial["manifest-paquete.json"],
            "source_files_checked": len(source_snapshot),
            "archived_root_entries": moving,
            "excluded": sorted(CACHES) + [".DS_Store", "*.pyc", "*.pyo"],
            "human_review": "pending",
            "human_rehearsal": "pending",
            "human_demo": "pending",
            "logs": log,
        }
        write_json(stage / "verificacion-entrega.json", verification)
        publication["verificacion-entrega.json"] = stage / "verificacion-entrega.json"
        manifest_files = {
            name: digest(path) for name, path in sorted(publication.items())
        }
        manifest = {
            "version": "aligned-v4-final-delivery-1",
            "algorithm": "sha256",
            "files": manifest_files,
            "excludes_self": "manifest-entrega.json",
            "excludes": verification["excluded"],
        }
        write_json(stage / "manifest-entrega.json", manifest)
        publication["manifest-entrega.json"] = stage / "manifest-entrega.json"
        manifest_sha = digest(stage / "manifest-entrega.json")
        candidate = stage / "delivery.zip"
        with ZipFile(candidate, "x", ZIP_DEFLATED, compresslevel=9) as archive:
            for name, path in sorted(publication.items()):
                archive.write(path, root.name + "/" + name)
        with ZipFile(candidate) as archive:
            expected_names = {root.name + "/" + name for name in publication}
            require(
                len(archive.namelist()) == len(expected_names)
                and set(archive.namelist()) == expected_names,
                "ZIP path inventory differs",
            )
            require(archive.testzip() is None, "ZIP CRC test failed")
            archived_manifest = json.loads(
                archive.read(root.name + "/manifest-entrega.json")
            )
            require(archived_manifest == manifest, "Archived global manifest differs")
            for name, expected in {
                **manifest_files,
                "manifest-entrega.json": manifest_sha,
            }.items():
                with archive.open(root.name + "/" + name) as stream:
                    require(
                        hashlib.file_digest(stream, "sha256").hexdigest() == expected,
                        f"ZIP SHA256 mismatch: {name}",
                    )
            # Explicitly bind both local artifact manifests to the decompressed bytes.
            for folder in ("experimento", "reproduccion"):
                artifacts = json.loads(
                    archive.read(f"{root.name}/{folder}/artifact_manifest.json")
                )
                for name, expected in artifacts.items():
                    require(
                        manifest_files[f"{folder}/{name}"] == expected,
                        f"Archived artifact manifest mismatch: {folder}/{name}",
                    )
        require(
            {name: digest(path) for name, path in inventory(root).items()} == initial,
            "Package changed during finalization; nothing published",
        )
        require(
            all(
                path.is_file() and digest(path) == sha
                for path, sha in source_snapshot.items()
            ),
            "Source changed during finalization; nothing published",
        )
        checksum = digest(candidate)
        (stage / "delivery.sha256").write_text(
            f"{checksum}  {zip_path.name}\n", encoding="ascii"
        )
        # Back up only the README being replaced. On a publication error restore
        # our moves/writes, never delete or rewrite any frozen/source artifact.
        os.link(root / "README.md", stage / "original-README.md")
        moved, created = [], []
        replaced_readme = False
        made_history = False
        try:
            (root / HISTORY).mkdir()
            made_history = True
            for name in moving:
                (root / name).rename(root / HISTORY / name)
                moved.append(name)
            for name, staged in (
                (HISTORY + "/README.md", stage / "history-README.md"),
                ("verificacion-entrega.json", stage / "verificacion-entrega.json"),
                ("manifest-entrega.json", stage / "manifest-entrega.json"),
            ):
                os.link(staged, root / name)
                created.append(root / name)
            os.replace(stage / "README.md", root / "README.md")
            replaced_readme = True
            actual = inventory(root)
            require(
                set(actual) == set(publication), "Published directory inventory differs"
            )
            require(
                all(
                    digest(actual[name]) == sha for name, sha in manifest_files.items()
                ),
                "Published directory SHA256 differs",
            )
            require(
                digest(root / "manifest-entrega.json") == manifest_sha,
                "Global manifest changed",
            )
            check_hashes(root / "experimento", frozen)
            require(
                digest(root / "manifest-paquete.json")
                == initial["manifest-paquete.json"]
                and digest(root / "verificacion-reproduccion.json") == FINAL_SHA,
                "Protected evidence changed",
            )
            os.link(candidate, zip_path)
            created.append(zip_path)
            os.link(stage / "delivery.sha256", sha_path)
            created.append(sha_path)
        except BaseException:
            for path in reversed(created):
                path.unlink()
            if replaced_readme:
                os.replace(stage / "original-README.md", root / "README.md")
            for name in reversed(moved):
                (root / HISTORY / name).rename(root / name)
            if made_history:
                (root / HISTORY).rmdir()
            raise
    print(
        json.dumps(
            {
                "passed": True,
                "zip": str(zip_path),
                "sha256": checksum,
                "checksum_file": str(sha_path),
                "files": len(publication),
                "zip_testzip": None,
                "zip_sha256_readback": True,
                "human_review": "pending",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        print(f"Finalization aborted: {error}", file=sys.stderr)
        sys.exit(1)
