"""Build a review draft from frozen ML evidence; never train or reselect a model."""

import argparse
import base64
import csv
import hashlib
import json
import math
import re
import shutil
import statistics
from datetime import UTC, datetime
from pathlib import Path

import markdown
import matplotlib
import matplotlib.pyplot as plt
from docx import Document
from docx.oxml import OxmlElement
from docx.shared import Cm, Pt, RGBColor

plt.switch_backend("Agg")

REPO = Path(__file__).resolve().parents[1]
NAME = "APF3_TD_Grupo2_ML_Innovacion_Borrador"


def table(headers, rows):
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows),
        ]
    )


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    )


def add_text(paragraph, text):
    for part in re.split(r"(\*\*.*?\*\*|`[^`]+`)", text):
        run = paragraph.add_run(
            part.strip("*") if part.startswith("**") else part.strip("`")
        )
        if part.startswith("**"):
            run.bold = True
        elif part.startswith("`"):
            run.font.name = "Consolas"
            run.font.size = Pt(9)


def documents(text, output, *, name=NAME, expected_figures=3):
    pages = text.split("<!-- PAGE -->")
    ref = (
        next(
            index
            for index, page in enumerate(pages)
            if page.strip().startswith("# Referencias")
        )
        if "# Referencias" in text
        else None
    )
    if ref is not None:
        assert ref - 1 <= 15
    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin = section.bottom_margin = Cm(1.8)
    section.left_margin = section.right_margin = Cm(1.8)
    normal = document.styles["Normal"]
    normal.font.name, normal.font.size = "Calibri", Pt(10.5)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.06
    for style_name in ("Title", "Heading 1", "Heading 2"):
        document.styles[style_name].font.color.rgb = RGBColor.from_string("17375E")
    document.core_properties.title = "APF3 - Credify - Borrador académico sintético"
    document.core_properties.author = "Grupo 2"
    footer = section.footer.paragraphs[0]
    footer.text = "BORRADOR · Datos simulados · Grupo 2 | "
    field = OxmlElement("w:fldSimple")
    field.set(
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}instr", "PAGE"
    )
    footer._p.append(field)
    for index, page in enumerate(pages):
        if index:
            document.add_page_break()
        for block in page.strip().split("\n\n"):
            block = block.strip()
            if not block:
                continue
            if block.startswith("!["):
                match = re.fullmatch(r"!\[(.*?)\]\((.*?)\)", block)
                assert match, block
                picture = document.add_picture(str(output / match[2]), width=Cm(16))
                if picture.height > Cm(11):
                    picture.width = int(picture.width * Cm(11) / picture.height)
                    picture.height = Cm(11)
                add_text(document.add_paragraph(style="Caption"), match[1])
            elif block.startswith("|"):
                rows = [
                    [cell.strip() for cell in line.strip("|").split("|")]
                    for line in block.splitlines()
                ]
                item = document.add_table(rows=0, cols=len(rows[0]))
                item.style = "Light Shading Accent 1"
                for row in [rows[0], *rows[2:]]:
                    cells = item.add_row().cells
                    for cell, value in zip(cells, row, strict=True):
                        add_text(cell.paragraphs[0], value)
                        for run in cell.paragraphs[0].runs:
                            run.font.size = Pt(9)
                    item.rows[-1]._tr.get_or_add_trPr().append(
                        OxmlElement("w:cantSplit")
                    )
            elif block.startswith("```"):
                code = "\n".join(block.splitlines()[1:-1])
                if block.startswith("```json"):
                    code = json.dumps(json.loads(code), indent=2)
                paragraph = document.add_paragraph()
                run = paragraph.add_run(code)
                run.font.name, run.font.size = "Consolas", Pt(8)
            elif block.startswith("#"):
                for line in block.splitlines():
                    level, title = line.split(" ", 1)
                    document.add_heading(title, level=min(len(level), 2))
            elif re.match(r"\d+\. ", block):
                for line in block.splitlines():
                    add_text(
                        document.add_paragraph(style="List Number"),
                        re.sub(r"^\d+\. ", "", line),
                    )
            else:
                add_text(document.add_paragraph(), block.replace("\n", " "))
    destination = output / (name + ".docx")
    document.save(destination)
    reopened = Document(destination)
    assert len(reopened.inline_shapes) == expected_figures
    assert len(reopened.tables) == len(document.tables)
    rendered = []
    for index, page in enumerate(pages):
        content = markdown.markdown(page, extensions=["tables", "fenced_code"])
        rendered.append(
            f'<section class="page" data-page="{index}">{content}</section>'
        )
    markup = (
        """<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>APF3 - Credify - Borrador</title><style>
@page { size:A4; margin:18mm 18mm 20mm; }
* { box-sizing:border-box; } body { margin:0; color:#172334; font:10.5pt/1.25 Arial,sans-serif; }
.page { break-after:page; } .page:last-child { break-after:auto; }
h1 { font-size:17pt; color:#17375e; margin:0 0 12px; }
h2 { font-size:11.5pt; color:#17375e; margin:13px 0 7px; }
p { margin:0 0 9px; text-align:justify; } a { color:#17375e; }
table { width:100%; border-collapse:collapse; table-layout:fixed; margin:10px 0; font-size:8.7pt; }
th,td { border:1px solid #c9d4df; padding:5px; vertical-align:top; overflow-wrap:anywhere; }
th { background:#e8eef5; text-align:left; } tr { break-inside:avoid; }
img { display:block; max-width:100%; max-height:95mm; object-fit:contain; margin:auto; }
code { font:8.6pt Consolas,monospace; overflow-wrap:anywhere; }
pre { white-space:pre-wrap; overflow-wrap:anywhere; background:#f2f5f8; padding:8px; }
pre code { font-size:8pt; } ol { padding-left:20px; } li { margin-bottom:5px; }
.page:first-child h1 { margin-top:30mm; font-size:22pt; }
.page:first-child p { text-align:left; }
</style></head><body>"""
        + "\n".join(rendered)
        + "</body></html>"
    )
    for image in re.findall(r'src="([^"]+)"', markup):
        png = base64.b64encode((output / image).read_bytes()).decode()
        markup = markup.replace(f'src="{image}"', f'src="data:image/png;base64,{png}"')
    (output / (name + ".html")).write_text(markup)
    return {
        "planned_body_pages": ref - 1 if ref is not None else None,
        "planned_total_pages": len(pages),
        "word_tables": len(reopened.tables),
        "embedded_figures": len(reopened.inline_shapes),
    }


def generate(source, output, workshop):
    output.mkdir(parents=True, exist_ok=True)
    for folder in ("figuras", "evidencias", "artefactos", "codigo"):
        (output / folder).mkdir(exist_ok=True)
    original = source / "ejecucion-02"
    final = source / "experimento-v2"
    first = json.loads((original / "academic_synthetic_report.json").read_text())
    report = json.loads((final / "experiment_v2_report.json").read_text())
    inspection = json.loads(
        (output / "evidencias/academic_artifact_inspection.json").read_text()
    )
    assert digest(final / "academic_model_v2.joblib") == report["artifact_sha256"]
    assert inspection["artifact"]["sha256"] == report["artifact_sha256"]
    assert inspection["artifact"]["report_sha256"] == digest(
        final / "experiment_v2_report.json"
    )
    for filename, expected in first["sha256"].items():
        assert digest(original / filename) == expected
    ledger = json.loads((original / "synthetic_transactions.json").read_text())
    rows = ledger["rows"]
    assert len(rows) == 1622 and len({row["loan_id"] for row in rows}) == len(rows)
    features = report["feature_names"]
    assert len(features) == 11
    ranges = {"missing_predictors": 0, "nonfinite_predictors": 0, "invalid_ranges": 0}
    for row in rows:
        assert row["data_source"] == "synthetic"
        for feature in features:
            value = row.get(feature)
            ranges["missing_predictors"] += value is None
            ranges["nonfinite_predictors"] += value is not None and not math.isfinite(
                value
            )
            ranges["invalid_ranges"] += value is not None and value < 0
        for feature in (
            "utilization",
            "requested_ratio",
            "punctuality_rate",
            "overdue_rate",
        ):
            ranges["invalid_ranges"] += row[feature] > 1
        ranges["invalid_ranges"] += row["paid_late"] > row["paid_credits"]
    assert not any(ranges.values()), ranges
    train = [
        row
        for row in rows
        if row["split"] == "train" and row["late_payment"] is not None
    ]
    assert len(train) == 943 and sum(row["late_payment"] for row in train) == 316
    fields = ["origen", *rows[0]]
    with (output / "dataset_desarrollo_simulado.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({"origen": "simulado", **row} for row in rows)
    matplotlib.rcParams.update(
        {"font.size": 10, "axes.spines.top": False, "axes.spines.right": False}
    )
    fig, ax = plt.subplots(figsize=(7.8, 2.7), layout="constrained")
    bars = ax.bar(
        ["Puntual (0)", "Atraso (1)"], [627, 316], color=["#246c67", "#b65e39"]
    )
    ax.bar_label(bars, padding=3)
    ax.set(
        ylabel="Fiados de entrenamiento",
        ylim=(0, 720),
        title="Datos simulados · n = 943",
    )
    fig.savefig(output / "figuras/eda_balance.png", dpi=180)
    plt.close(fig)
    history = [
        ("Sin pagos previos", [r for r in train if r["paid_credits"] == 0]),
        (
            "Pagados sin atraso",
            [r for r in train if r["paid_credits"] > 0 and r["paid_late"] == 0],
        ),
        ("Con pagos tardíos", [r for r in train if r["paid_late"] > 0]),
    ]
    exposure = [
        ("0–25 %", [r for r in train if r["utilization"] <= 0.25]),
        (">25–50 %", [r for r in train if 0.25 < r["utilization"] <= 0.5]),
        (">50 %", [r for r in train if r["utilization"] > 0.5]),
    ]
    relationship_rows = []
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.1), layout="constrained")
    for ax, groups, title in zip(
        axes,
        (history, exposure),
        ("Historial previo", "Utilización previa"),
        strict=True,
    ):
        rates = [
            100 * statistics.mean(r["late_payment"] for r in group)
            for _, group in groups
        ]
        bars = ax.bar(
            [f"{name}\nn={len(group)}" for name, group in groups],
            rates,
            color="#315b84",
        )
        ax.bar_label(bars, fmt="%.1f%%", padding=3, fontsize=9)
        ax.set(title=title, ylabel="Atraso (%)", ylim=(0, max(rates) + 16))
        ax.tick_params(axis="x", labelsize=8)
        for (name, group), rate in zip(groups, rates, strict=True):
            relationship_rows.append([title, name, len(group), f"{rate:.2f} %"])
    fig.savefig(output / "figuras/eda_relaciones.png", dpi=180)
    plt.close(fig)
    description = []
    for feature in (
        "requested_amount",
        "paid_credits",
        "paid_late",
        "outstanding",
        "utilization",
        "punctuality_rate",
        "tenure_days",
    ):
        values = [float(row[feature]) for row in train]
        description.append(
            [
                feature,
                f"{min(values):.2f}",
                f"{statistics.mean(values):.2f}",
                f"{statistics.median(values):.2f}",
                f"{max(values):.2f}",
            ]
        )
    error_report = json.loads((final / "final_errors_not_for_tuning.json").read_text())
    fresh = json.loads((final / "fresh_synthetic_transactions.json").read_text())
    assert not any(
        all(row[name] == inspection["input"]["features"][name] for name in features)
        for row in rows + fresh["rows"]
    ), "Illustrative input must differ from every existing simulated dataset row"
    final_rows = {row["loan_id"]: row for row in fresh["rows"]}
    selected_errors = [error_report["examples"][index] for index in (0, 1, 3)]
    assert (
        final_rows[selected_errors[0]["loan_id"]]["client_id"]
        == final_rows[selected_errors[1]["loan_id"]]["client_id"]
    )
    hypotheses = [
        "Un pago previo puntual no anticipa un cambio de conducta.",
        "La exposición compartida puede disparar una falsa alerta.",
        "Historial corto y pago en abonos pueden ocultar el atraso.",
    ]
    errors = [
        [
            item["loan_id"],
            final_rows[item["loan_id"]]["client_id"],
            item["error"],
            f"{item['estimated_probability']:.4f}",
            item["actual"],
            hypothesis,
        ]
        for item, hypothesis in zip(selected_errors, hypotheses, strict=True)
    ]
    comparisons = report["comparison_on_same_fresh_cohort"]
    metric_rows = [
        [name, *(f"{comparisons[model][key]:.4f}" for model in comparisons)]
        for name, key in (
            ("Accuracy", "accuracy"),
            ("Precision", "precision"),
            ("Recall", "recall"),
            ("F1", "f1"),
            ("Balanced accuracy", "balanced_accuracy"),
            ("ROC-AUC", "roc_auc"),
            ("Brier", "brier_score"),
        )
    ]
    assert comparisons["second_model"]["confusion_matrix"] == [[543, 178], [183, 166]]
    actions = {
        "paid_late": "Revisar atrasos históricos, no sancionar automáticamente.",
        "completed_sales": "Comprobar regularidad; no aprobar solo por compras.",
        "overdue_rate": "Revisar vencidos activos y su contexto.",
        "pending_current": "Contrastar obligaciones aún dentro de plazo.",
        "tenure_days": "Auditar el efecto de antigüedad; no usarlo como sanción.",
    }
    coefficient_rows = [
        [
            item["feature"],
            f"{item['standardized_coefficient']:+.4f}",
            f"{item['odds_ratio_exp_coefficient']:.4f}",
            actions[item["feature"]],
        ]
        for item in sorted(
            inspection["coefficients"],
            key=lambda item: abs(item["standardized_coefficient"]),
            reverse=True,
        )[:5]
    ]
    substitutions = {
        "train_negative_pct": f"{627 / 943 * 100:.2f}",
        "train_positive_pct": f"{316 / 943 * 100:.2f}",
        "descriptives_table": table(
            ["Variable", "Mín.", "Media", "Mediana", "Máx."], description
        ),
        "relationships_table": table(
            ["Relación", "Grupo", "n", "Atraso"], relationship_rows
        ),
        "history_conclusion": f"Sin pagos previos: {relationship_rows[0][3]}; pagados sin atraso: "
        f"{relationship_rows[1][3]}; con pagos tardíos: {relationship_rows[2][3]}.",
        "exposure_conclusion": f"Las tres bandas presentan {relationship_rows[3][3]}, "
        f"{relationship_rows[4][3]} y {relationship_rows[5][3]} de atraso.",
        "metrics_table": table(
            ["Métrica", "V2", "V1 en el mismo final", "Mayoritaria"], metric_rows
        ),
        "errors_table": table(
            ["Fiado", "Cliente ficticio", "Error", "P(atraso)", "Target", "Hipótesis"],
            errors,
        ),
        "coefficients_table": table(
            ["Variable", "Coef.", "exp(coef.)", "Acción sugerida"], coefficient_rows
        ),
        "new_probability": f"{inspection['output']['probability_class_1']:.6f}",
        "latency_median": f"{inspection['latency']['median_ms']:.4f}",
        "latency_p95": f"{inspection['latency']['p95_ms']:.4f}",
    }
    text = (REPO / "docs" / (NAME + ".md")).read_text()
    for key, value in substitutions.items():
        assert "{{" + key + "}}" in text, key
        text = text.replace("{{" + key + "}}", value)
    assert not re.search(r"\{\{\w+\}\}", text)
    sources = {}

    def attach(path, target):
        sources[str(path)] = digest(path)
        shutil.copyfile(path, output / target)

    for filename in (
        "experiment_v2_report.json",
        "protocol.json",
        "frozen_selection.json",
        "validation_search.json",
        "final_errors_not_for_tuning.json",
    ):
        attach(final / filename, "evidencias/" + filename)
    attach(
        original / "academic_synthetic_report.json",
        "evidencias/academic_synthetic_report.json",
    )
    attach(
        final / "evidencias-demo/verificacion-laboratorio.json",
        "evidencias/verificacion-laboratorio.json",
    )
    attach(
        final / "evidencias-demo/laboratorio-desktop.png",
        "figuras/laboratorio-desktop.png",
    )
    attach(
        final / "evidencias-demo/laboratorio-mobile.png",
        "evidencias/laboratorio-mobile.png",
    )
    attach(final / "academic_model_v2.joblib", "artefactos/academic_model_v2.joblib")
    for filename in ("experiment_v2_report.json", "academic_lab_cases.json"):
        attach(final / filename, "artefactos/" + filename)
    attach(
        REPO / "backend/scripts/inspect_academic_artifact.py",
        "codigo/inspect_academic_artifact.py",
    )
    attach(
        workshop / "verificacion-ejecucion.json", "evidencias/verificacion-taller.json"
    )
    attach(
        workshop / "S14A_TallerML_Grupo2_Colab.ipynb",
        "evidencias/S14A_TallerML_Grupo2_Colab.ipynb",
    )
    sources[str(original / "synthetic_transactions.json")] = digest(
        original / "synthetic_transactions.json"
    )
    sources[str(final / "fresh_synthetic_transactions.json")] = digest(
        final / "fresh_synthetic_transactions.json"
    )
    sources[str(REPO / "docs" / (NAME + ".md"))] = digest(
        REPO / "docs" / (NAME + ".md")
    )
    write_json(
        output / "entrada_inferencia_ilustrativa.json", inspection["input"]["features"]
    )
    (output / "requirements-inferencia.txt").write_text(
        "scikit-learn==1.9.1\nnumpy==2.5.3\njoblib==1.6.0\nscipy==1.18.1\n"
    )
    (output / (NAME + ".md")).write_text(text)
    validation = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "synthetic_rows": len(rows),
        "unknown_target_rows": sum(r["late_payment"] is None for r in rows),
        "training_eda_rows": len(train),
        "checks": ranges,
        "source_sha256": sources,
        "workshop_separate_from_project": True,
        "new_training": False,
        "sources_modified": False,
        "human_review": "pending",
    }
    validation.update(documents(text, output))
    write_json(output / "verificacion-informe.json", validation)
    files = {
        str(path.relative_to(output)): digest(path)
        for path in output.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    }
    write_json(output / "manifest.json", {"sources": sources, "files": files})
    print(json.dumps(validation, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--workshop-dir", required=True, type=Path)
    args = parser.parse_args()
    generate(args.source, args.output_dir, args.workshop_dir)
