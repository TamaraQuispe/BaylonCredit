"""Export only V4 speaker notes from frozen evidence; never build a deck or run ML."""

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from pypdf import PdfReader

REPO = Path(__file__).resolve().parents[1]
NAME = "APF3_Grupo2_Guion_12min"
FINAL_SHA = "86831dabd16b66499afbea6cc7f621c6dba5827367ae2526c788396900872558"
OWNER_SHA = "45bc22a10ad5dccf323708b8aeabb780d8de4629ff5087cca2582c7dd055819f"


def generate(root, source, playwright_module):
    modules = []
    for filename in ("generate-apf3-defense.py", "generate-apf3-report.py"):
        spec = importlib.util.spec_from_file_location(
            filename, REPO / "deploy" / filename
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules.append(module)
    defense, helper = modules
    sources = {}

    def read(path):
        path = path.resolve()
        content = path.read_bytes()
        sources[str(path)] = hashlib.sha256(content).hexdigest()
        return content.decode("utf-8")

    def load(relative):
        return json.loads(read(root / relative))

    read(Path(__file__))
    for module in modules:
        read(Path(module.__file__))
    text = read(source)
    notes = defense.parse_notes(text)
    assert [n["number"] for n in notes] == list(range(1, 14))
    words = sum(len(re.findall(r"\S+", n["spoken"])) for n in notes)
    assert 1250 <= words <= 1450, words
    assert sum(n["seconds"] for n in notes) == 720
    assert len(re.findall(r"(?m)^## \d+\. ", text)) == 13
    questions = text.split("# Preguntas difíciles y respuestas breves", 1)[1].split(
        "# Lista de revisión humana pendiente", 1
    )[0]
    qa = re.findall(
        r"(?m)^\*\*¿.*?(?=\n\n\*\*¿|\Z)", questions.strip(), flags=re.DOTALL
    )
    assert len(qa) == 18
    assert not re.search(r"\{\{\w+\}\}", text)
    assert not re.search(
        r"reproducci[oó]n[^.\n;]{0,60}(?:sigue|permanece) pendiente",
        text,
        re.IGNORECASE,
    )
    assert OWNER_SHA in text and FINAL_SHA in text
    reproduction = load("verificacion-reproduccion.json")
    assert (
        sources[str((root / "verificacion-reproduccion.json").resolve())] == FINAL_SHA
    )
    assert reproduction["passed"] is True
    checks = reproduction["checks"]
    for key, count in (
        ("exact_file_sha256", 15),
        ("raw", 12),
        ("policy", 12),
        ("learned_artifact_state", 5),
    ):
        assert len(checks[key]) == count and all(
            v is True for v in checks[key].values()
        )
    for key in (
        "full_report_except_time_and_artifact_serialization",
        "selection",
        "illustrative_inference",
        "negative_control_detects_metric_mismatch",
    ):
        assert checks[key] is True
    for key in (
        "integrity",
        "decision_and_artifact_chains",
        "csv_scope",
        "inference_cli",
        "environment",
    ):
        assert all(v is True for v in checks[key].values())
    for filename in checks["exact_file_sha256"]:
        assert read(root / "experimento" / filename) == read(
            root / "reproduccion" / filename
        )
    states = load("estado-artefactos.json")["models"]
    assert states == reproduction["artifact_serialization"]["models"]
    assert set(states) == set(checks["learned_artifact_state"])
    for name, state in states.items():
        assert state["learned_state_equal"] is True and state["binary_equal"] is False
        assert state["state_sha256"][0] == state["state_sha256"][1]
        for index, directory in enumerate(("experimento", "reproduccion")):
            path = root / directory / (name + ".joblib")
            sources[str(path.resolve())] = helper.digest(path)
            assert sources[str(path.resolve())] == state["binary_sha256"][index]
    report = load("experimento/aligned_v4_report.json")
    rows = load("experimento/development_rows.json")
    selection = load("experimento/frozen_selection.json")
    calibration = load("experimento/calibration.json")
    illustration = load("experimento/illustrative_output.json")
    entry = load("experimento/illustrative_input.json")
    verification = load("informe/verificacion-informe-v4.json")
    report_text = read(root / "informe/APF3_TD_Grupo2_ML_Innovacion_Borrador.md")
    runner = read(root / "codigo/scripts/academic_credit_aligned_v4.py")
    assert "--predict-artifact-dir" in runner and "--output-json" in runner
    assert (
        report["version"]
        == verification["report_version"]
        == "academic-owner-aligned-v4"
    )
    assert calibration["source_docx_sha256"] == OWNER_SHA
    assert verification["source_owner_document_declared_sha256"] == OWNER_SHA
    assert [
        calibration[k]
        for k in (
            "evaluable",
            "late",
            "partial_payment_annotations",
            "partial_payment_denominator",
        )
    ] == [45, 8, 10, 48]
    assert not re.search(r"\{\{\w+\}\}", report_text)
    assert "| paid_credits (conteo) | 2,00 |" in report_text
    assert verification["embedded_figures"] == 3
    assert verification["metric_cells_checked_against_json"] == 224
    assert verification["reproduction"]["verified"] is True
    assert verification["pdf_physical_pagination"]["overflow"] is False
    assert len(rows) == 552 and sum(r["late_payment"] for r in rows) == 68
    assert min(r["paid_credits"] for r in rows) == 2
    groups = [
        [r for r in rows if r["paid_credits"] == 0],
        [r for r in rows if r["paid_credits"] > 0 and r["paid_late"] == 0],
        [r for r in rows if r["paid_late"] > 0],
        [r for r in rows if r["utilization"] <= 0.25],
        [r for r in rows if 0.25 < r["utilization"] <= 0.5],
        [r for r in rows if r["utilization"] > 0.5],
    ]
    relationships = verification["relationships"]
    for group, band in zip(
        groups, relationships["history"] + relationships["exposure"], strict=True
    ):
        late = sum(r["late_payment"] for r in group)
        assert (len(group), late, late / len(group) if group else None) == (
            band["n"],
            band["late"],
            band["rate"],
        )
    assert [len(g) for g in groups] == [0, 218, 334, 551, 1, 0]
    assert selection == report["selection"]
    assert selection["global_winner"]["family"] == "svm"
    assert selection["global_winner"]["threshold"] == 0.1
    assert report["models"]["svm"]["final"]["confusion_matrix"] == [[80, 114], [4, 61]]
    metric_lines = [
        line for line in notes[6]["notes"].splitlines() if line.startswith("| ")
    ][2:]
    for line, family in zip(
        metric_lines, ("svm", "tree", "most_frequent", "constant_1"), strict=True
    ):
        cells = [c.strip() for c in line.strip("|").split("|")][1:]
        metrics = report["models"][family]["final"]
        assert cells == [
            f"{metrics[k]:.5f}".replace(".", ",")
            for k in ("precision", "recall", "f1", "f2", "accuracy")
        ]
    for family, model in report["models"].items():
        for split in ("train", "oof", "final"):
            assert (
                reproduction["results"]["models"][family]["raw"][split] == model[split]
            )
            assert (
                reproduction["results"]["models"][family]["policy"][split]
                == model["review_policy"][split]["metrics"]
            )
    demo_blocks = re.findall(r"```(\w+)\n(.*?)\n```", notes[8]["notes"], re.DOTALL)
    (command,) = [value for kind, value in demo_blocks if kind == "bash"]
    assert (
        command
        == "python codigo/scripts/academic_credit_aligned_v4.py --predict-artifact-dir experimento --input-json experimento/illustrative_input.json --output-json demo_inferencia_nueva.json"
    )
    demo_json = [json.loads(value) for kind, value in demo_blocks if kind == "json"]
    assert demo_json[0] == entry and len(entry["features"]) == 11
    assert all(illustration[k] == v for k, v in demo_json[1].items())
    assert reproduction["results"]["inference"] == {
        k: v
        for k, v in illustration.items()
        if k not in ("distinctness_pass", "requested_amount_pen")
    }

    elapsed = 0
    timeline = []
    planned = Counter()
    for note in notes:
        end = elapsed + note["seconds"]
        timeline.append(
            [
                str(note["number"]),
                note["owner"],
                f"{elapsed // 60:02}:{elapsed % 60:02} - {end // 60:02}:{end % 60:02}",
                str(note["seconds"]),
            ]
        )
        planned[note["owner"]] += note["seconds"]
        elapsed = end
    team = text.split("| Integrante |", 1)[1].split("\n\n", 1)[0]
    pages = [
        "# Guion de sustentación APF3 · Grupo 2\n\n"
        "**V4 · 12 minutos · 13 intervenciones.** Roles propuestos, no actas de contribución. "
        "Revisión individual, ensayo y demo humana pendientes.\n\n"
        + "| Integrante |"
        + team
        + "\n\n"
        + helper.table(
            ["Diap.", "Expositor propuesto", "Ventana", "Segundos"], timeline
        )
        + f"\n\n**Texto hablado:** {words} palabras, medidas con `parse_notes` actual. "
        "720 segundos planificados: 670 hablados y 50 de operación. Diapositiva 9: 20 hablados + 50 en vivo. Preguntas fuera del cronómetro.\n\n"
        "**Cierre técnico, no humano:** reproducción final passed=true; 15 SHA, 12 brutas, 12 políticas y cinco estados aprendidos exactos. Bytes Joblib NO iguales. "
        "CLI aislada comprobada, sin acreditar ensayo ni validación independiente. Fuente comercial exclusiva: declaración actual de Rildo; formulario hipotético excluido.\n\n"
        "**Fuentes y huellas:** informe materializado, su verificación, cachés congelados y verificación final; rutas y SHA-256 completos en `plan-notas-v4.json`."
    ]
    for start, end in ((0, 3), (3, 6), (6, 9), (9, 13)):
        chunks = [f"# Intervenciones {start + 1} a {end}"]
        for note in notes[start:end]:
            support = note["first_action"]
            if note["number"] == 4:
                support += " Historial DEV: 8/218 y 60/334; sin historial n=0 (no estimable). Exposición 68/551, 0/1 y n=0: sin tendencia general."
            chunks.append(
                f"## {note['number']}. {note['title']}\n\n"
                f"**Tiempo:** {note['seconds']} s · **Expositor propuesto:** {note['owner']}\n\n"
                f"{note['spoken']}\n\n**Apoyo no hablado:** {support}"
            )
        pages.append("\n\n".join(chunks))
    for index in range(3):
        pages.append(
            f"# Preguntas difíciles {index + 1}/3\n\n**Fuera de los 720 segundos.**\n\n"
            + "\n\n".join(qa[index * 6 : (index + 1) * 6])
        )
    pages.append(
        "# Demo local: instrucciones, no acta\n\n"
        "**Pendiente de realización humana.** La CLI técnica aislada fue comprobada sin red sobre artefactos originales y reproducidos; sus salidas coinciden. "
        "Eso no acredita ensayo, duración real ni éxito futuro en el equipo de exposición. No se ejecuta ML para exportar este guion.\n\n"
        "**Secuencia fija:** 20 segundos hablados + 50 de operación: entrada 10, comando 10, salida 20 y límites 10. "
        "Desde la raíz del paquete, con dependencias compatibles, código y artefactos confiables. Verificar manifiesto y salida libre; si existe, elegir otro nombre nuevo, sin borrar evidencia.\n\n"
        f"```bash\n{command}\n```\n\n"
        "**Entrada ficticia:** once campos, sin etiqueta conocida.\n\n"
        + "```json\n"
        + json.dumps(entry, ensure_ascii=False)
        + "\n```\n\n"
        "**Salida de respaldo, no recién ejecutada:** score 0,11922453881690649, umbral 0,10, predicción 1. "
        "No prueba acierto, no aprueba ni rechaza. Solo el umbral; revisión efectiva requiere cola completa por réplica/fecha.\n\n"
        "**Fallback:** si falla o falta entorno, declarar ejecución en vivo fallida/no realizada y mostrar "
        "`experimento/illustrative_output.json` rotulado resultado previamente guardado. Si no es verificable, reconocerlo en los mismos 50 segundos. "
        "Una grabación auténtica se identifica como grabada, no en vivo.\n\n"
        "**Prohibido durante la demo:** entrenar, generar datos, reproducir, reajustar o predecir casos FINAL. "
        "No inventar terminal, capturas ni éxito. Web heredada v2 no es evidencia de integración V4.\n\n"
        "**Salvedad técnica:** tres timestamps y dos hashes derivados excluidos de la comparación; cadenas locales verificadas. "
        "Estados aprendidos exactos no significan igualdad de bytes Joblib. Repetición del protocolo fijo, no validación independiente."
    )
    review = text.split("# Lista de revisión humana pendiente", 1)[1].strip()
    # Blank lines preserve separate checklist entries in both shared document formats.
    review = re.sub(r"\n(?=- \[ \])", "\n\n", review)
    pages.append("# Revisión humana pendiente\n\n" + review)
    compact = "\n\n<!-- PAGE -->\n\n".join(pages)
    assert len(re.findall(r"(?m)^## \d+\. ", compact)) == 13
    assert len(re.findall(r"(?m)^\*\*¿", compact)) == 18
    output = root / "sustentacion"
    output.mkdir(exist_ok=True)
    (output / (NAME + ".md")).write_text(compact, encoding="utf-8")
    (output / "Guion_completo_con_indicaciones.md").write_text(text, encoding="utf-8")
    result = helper.documents(compact, output, name=NAME, expected_figures=0)
    html_path = output / (NAME + ".html")
    markup = html_path.read_text().replace(
        "APF3 - Credify - Borrador", "APF3 - Grupo 2 - Guion V4"
    )
    markup = markup.replace(
        "<p><strong>Apoyo no hablado:</strong>",
        '<p class="support"><strong>Apoyo no hablado:</strong>',
    )
    markup = markup.replace(
        "</style>",
        """
body{width:174mm;font:10pt/1.18 Arial,sans-serif}
.page{display:flow-root}p{margin:0 0 6px}h1{font-size:16pt;margin:0 0 10px}
h2{font-size:11.5pt;margin:10px 0 6px}th,td{padding:4px}
.page:first-child h1{margin-top:0;font-size:17pt}
pre{margin:6px 0;padding:6px}pre code{font-size:8pt}
.support{font-size:9pt;line-height:1.16}
.page:nth-child(5){font-size:9.5pt;line-height:1.16}
</style>""",
    )
    html_path.write_text(markup, encoding="utf-8")
    document = helper.Document(output / (NAME + ".docx"))
    document.core_properties.title = "APF3 - Grupo 2 - Guion V4 - 12 minutos"
    document.styles["Normal"].font.size = helper.Pt(10)
    document.styles["Normal"].paragraph_format.space_after = helper.Pt(4)
    footer = document.sections[0].footer.paragraphs[0]
    footer.runs[
        0
    ].text = "V4 · Datos simulados · Roles propuestos · Revisión humana pendiente | "
    document.save(output / (NAME + ".docx"))
    browser_script = r"""
import {readFile} from 'node:fs/promises';
const {chromium} = await import(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const browser = await chromium.launch();
try {
  const page = await browser.newPage({viewport:{width:794,height:1123},serviceWorkers:'block'});
  const requests = [];
  await page.route('**/*', route => {requests.push(route.request().url()); return route.abort();});
  await page.setContent(await readFile(process.argv[1], 'utf8'));
  await page.emulateMedia({media:'print'});
  await page.evaluate(() => document.fonts.ready);
  const sections = await page.locator('.page').evaluateAll(elements => elements.map(element => {
    const rect = element.getBoundingClientRect();
    const overflow = [...element.querySelectorAll('*')].filter(e => {
      const r = e.getBoundingClientRect();
      return r.left < rect.left - 1 || r.right > rect.right + 1 || e.scrollWidth > e.clientWidth + 1;
    }).map(e => ({tag:e.tagName,text:e.textContent.slice(0,100)}));
    return {title:element.querySelector('h1,h2')?.textContent,height_px:Math.ceil(rect.height),width_px:Math.ceil(rect.width),horizontal_overflow:overflow};
  }));
  const printable = 259 * 96 / 25.4;
  if (requests.length || sections.some(s => s.height_px > printable || s.horizontal_overflow.length)) {
    throw Error(JSON.stringify({requests,printable_height_px:printable,sections}));
  }
  await page.pdf({path:process.argv[2],preferCSSPageSize:true,printBackground:true,
    displayHeaderFooter:true,headerTemplate:'<div></div>',
    footerTemplate:'<div style="font:8px Arial;color:#526572;width:100%;text-align:center">Guion V4 · Roles propuestos · Revisión humana pendiente | <span class="pageNumber"></span> / <span class="totalPages"></span></div>'});
  console.log(JSON.stringify({offline:true,external_requests:requests,printable_height_px:printable,sections}));
} finally {await browser.close();}
"""
    environment = dict(os.environ)
    if playwright_module:
        environment["PLAYWRIGHT_MODULE_PATH"] = playwright_module
    process = subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            browser_script,
            str(html_path),
            str(output / (NAME + ".pdf")),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    if process.returncode:
        raise RuntimeError(process.stderr)
    audit = json.loads(process.stdout)
    pdf = PdfReader(output / (NAME + ".pdf"))
    assert len(pdf.pages) == len(pages) == len(audit["sections"])

    def normalize(value):
        return re.sub(r"\W+", "", value).lower()

    for page, section in zip(pdf.pages, audit["sections"], strict=True):
        assert normalize(section["title"]) in normalize(page.extract_text())
        assert abs(float(page.mediabox.width) - 595.28) < 1
        assert abs(float(page.mediabox.height) - 841.89) < 1
    pdf_text = "\n".join(page.extract_text() for page in pdf.pages)
    for note in notes:
        for paragraph in note["spoken"].split("\n\n"):
            assert normalize(paragraph) in normalize(pdf_text), note["number"]
    assert all(normalize(item) in normalize(pdf_text) for item in qa)
    assert normalize("experimento/illustrative_output.json") in normalize(pdf_text)
    assert normalize("academic_credit_aligned_v4.py") in normalize(pdf_text)
    assert (
        output / "Guion_completo_con_indicaciones.md"
    ).read_bytes() == source.read_bytes()
    assert all(helper.digest(Path(path)) == sha for path, sha in sources.items()), (
        "Source changed during export; rerun against the current snapshot"
    )
    owned = [NAME + ext for ext in (".md", ".docx", ".html", ".pdf")] + [
        "Guion_completo_con_indicaciones.md"
    ]
    plan = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "name": NAME,
        "slides": 13,
        "interventions": 13,
        "planned_seconds": 720,
        "spoken_planned_seconds": 670,
        "live_inference_reserved_seconds": 50,
        "slide_9": {"spoken_seconds": 20, "live_seconds": 50},
        "spoken_words": words,
        "word_count_method": "Current generate-apf3-defense.py parse_notes; re.findall(r'\\S+', spoken)",
        "spoken_words_range": [1250, 1450],
        "question_count": 18,
        "planned_speaker_seconds": dict(planned),
        "slides_data": [
            {k: n[k] for k in ("number", "title", "owner", "seconds")}
            | {"spoken_words": len(n["spoken"].split())}
            for n in notes
        ],
        "human_review": "pending",
        "human_rehearsal": "pending",
        "human_demo": "not performed; instructions only",
        "roles": "proposed; not records of past contribution or consent",
        "technical_cli_verified": True,
        "independent_validation": False,
        "reproduction": {
            "passed": True,
            "sha256": FINAL_SHA,
            "exact_file_sha256": 15,
            "raw": 12,
            "policy": 12,
            "equal_learned_states": 5,
            "joblib_binary_equal": False,
            "excluded_time_fields": reproduction["methods"]["excluded_time_fields"],
            "derived_hash_exceptions": reproduction["methods"][
                "derived_hash_exceptions"
            ],
        },
        "report_verification_reproduction_digest_matches_current": verification[
            "reproduction"
        ]["evidence_sha256"]
        == FINAL_SHA,
        "reproduction_authority": "Final root/verificacion-reproduccion.json; do not inherit an older digest from report verification",
        "owner_declared_source_sha256": OWNER_SHA,
        "private_owner_document_read_or_published": False,
        "eda": {
            "dataset": "DEV resolved only",
            "n": 552,
            "paid_credits_min": 2,
            "relationships": relationships,
            "exposure_trend_supported": False,
        },
        "metric_cells_checked": 20,
        "new_training": False,
        "new_predictions": False,
        "deck_generated": False,
        "report_rematerialized": False,
        "figures_generated": 0,
        "source_sha256": sources,
        "files_sha256": {name: helper.digest(output / name) for name in owned},
        "documents": result,
        "render": {
            **audit,
            "pdf_pages": len(pdf.pages),
            "pdf_a4": True,
            "pdf_titles_match_one_to_one": True,
            "all_spoken_and_qa_text_present": True,
            "overflow": False,
            "word_physical_pagination": "not rendered in Microsoft Word; page counts apply to PDF",
        },
    }
    helper.write_json(output / "plan-notas-v4.json", plan)
    print(
        json.dumps(
            {
                "files": owned + ["plan-notas-v4.json"],
                "output": str(output),
                "spoken_words": words,
                "pdf_pages": len(pdf.pages),
                "slides": 13,
                "seconds": 720,
                "qa": 18,
                "overflow": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument(
        "--source", type=Path, default=REPO / "docs/APF3_Guion_Sustentacion_V4.md"
    )
    parser.add_argument(
        "--playwright-module",
        help="Local Playwright ESM path; no installation or network fetch",
    )
    args = parser.parse_args()
    generate(args.root.resolve(), args.source.resolve(), args.playwright_module)
