"""Create editable slides, speaker notes and blank validation forms from frozen evidence."""

import argparse
import base64
import hashlib
import html
import importlib.util
import json
import re
import shutil
import statistics
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
from docx import Document as WordDocument
from docx.shared import Pt as WordPt
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_AUTO_SIZE, PP_ALIGN
from pptx.util import Inches, Pt

REPO = Path(__file__).resolve().parents[1]
NAME = "APF3_TD_Grupo2_ML_Innovacion"
NAVY, PAPER, INK, TEAL, COPPER = "10283F", "F6F3EB", "172B3A", "236F69", "A85632"
TIMES = [30, 30, 75, 75, 75, 75, 40, 40, 70, 60, 60, 45, 45]
OWNERS = [
    "Omara",
    "Omara",
    "Omara",
    "César",
    "César",
    "Omara",
    "Tamara",
    "César",
    "Tamara",
    "Pablo",
    "Tamara",
    "Pablo",
    "Pablo",
]


def parse_notes(text):
    main = text.split("# Preguntas difíciles", 1)[0]
    parts = re.split(r"(?m)^## (\d+)\. (.+)\n", main)
    slides = []
    for index in range(1, len(parts), 3):
        number, title, body = parts[index : index + 3]
        timing = re.search(
            r"\*\*Tiempo:\*\* (\d+) s \| \*\*Expositor propuesto:\*\* (.+)", body
        )
        assert timing
        plain = re.sub(r"```.*?```", "", body, flags=re.S)
        spoken = "\n\n".join(
            block.strip()
            for block in plain.split("\n\n")
            if block.strip() and not block.strip().startswith(("**", "|"))
        )
        actions = re.findall(r"\*\*Acción:\*\* ([^\n]+)", body)
        slides.append(
            {
                "number": int(number),
                "title": title,
                "seconds": int(timing[1]),
                "owner": timing[2],
                "notes": body.strip(),
                "spoken": spoken,
                "first_action": actions[0] if actions else "",
            }
        )
    assert len(slides) == 13
    assert [slide["seconds"] for slide in slides] == TIMES and sum(TIMES) == 720
    assert [slide["owner"] for slide in slides] == OWNERS
    return slides


def generate(root: Path):
    output = root / "sustentacion"
    for folder in (output, output / "figuras", output / "evidencias"):
        folder.mkdir(parents=True, exist_ok=True)
    for stale in ("Heading 2.docx", "Heading 2.html"):
        (output / stale).unlink(missing_ok=True)
    report = json.loads((root / "experimento/grouped_cv_report.json").read_text())
    rows = json.loads((root / "experimento/development_rows.json").read_text())
    source = (REPO / "docs/APF3_Guion_Sustentacion_CV3.md").read_text()
    notes = parse_notes(source)
    tree = report["models"]["tree"]["final"]
    assert tree["confusion_matrix"] == [[660, 35], [333, 45]]
    assert report["selection"]["global_winner"]["threshold"] == 0.7

    plt.switch_backend("Agg")
    plt.rcParams.update(
        {
            "font.size": 14,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "#" + PAPER,
            "axes.facecolor": "#" + PAPER,
        }
    )
    groups = [
        [
            ("Sin pagos\nprevios", [r for r in rows if r["paid_credits"] == 0]),
            (
                "Pagados sin\natraso",
                [r for r in rows if r["paid_credits"] > 0 and r["paid_late"] == 0],
            ),
            ("Con pagos\ntardíos", [r for r in rows if r["paid_late"] > 0]),
        ],
        [
            ("0–25 %", [r for r in rows if r["utilization"] <= 0.25]),
            (">25–50 %", [r for r in rows if 0.25 < r["utilization"] <= 0.5]),
            (">50 %", [r for r in rows if r["utilization"] > 0.5]),
        ],
    ]
    fig, axes = plt.subplots(1, 2, figsize=(12, 3.8), layout="constrained")
    for ax, grouped, title in zip(
        axes, groups, ("Historial previo", "Utilización previa"), strict=True
    ):
        rates = [
            100 * statistics.mean(row["late_payment"] for row in values)
            for _, values in grouped
        ]
        bars = ax.bar(
            [f"{label}\nn={len(values)}" for label, values in grouped],
            rates,
            color="#" + TEAL,
        )
        ax.bar_label(bars, fmt="%.1f%%", fontsize=15, padding=4)
        ax.set(title=title, ylabel="Atraso (%)", ylim=(0, 58))
        ax.tick_params(axis="x", labelsize=12)
    figure = output / "figuras/eda_presentacion.png"
    fig.savefig(figure, dpi=150)
    plt.close(fig)

    deck = []

    def slide(title, *, dark=False):
        item = {**notes[len(deck)], "title": title, "dark": dark, "elements": []}
        deck.append(item)
        return item

    def text(
        item,
        value,
        x,
        y,
        w,
        h,
        size=21,
        *,
        color=None,
        bold=False,
        align="left",
        mono=False,
    ):
        item["elements"].append(
            {
                "kind": "text",
                "text": value,
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "size": size,
                "bold": bold,
                "color": color or ("FFFFFF" if item["dark"] else INK),
                "align": align,
                "mono": mono,
            }
        )

    def rect(item, x, y, w, h, fill):
        item["elements"].append(
            {"kind": "rect", "x": x, "y": y, "w": w, "h": h, "fill": fill}
        )

    def table(item, headers, data, x, y, widths, row_height=0.57, size=18):
        item["elements"].append(
            {
                "kind": "table",
                "headers": headers,
                "rows": data,
                "x": x,
                "y": y,
                "w": sum(widths),
                "h": row_height * (len(data) + 1),
                "widths": widths,
                "row_height": row_height,
                "size": size,
            }
        )

    item = slide("Fiado a un día\nDel registro a la evaluación", dark=True)
    text(item, item["title"], 0.65, 1.15, 8.7, 1.6, 36, bold=True)
    text(item, "Cervecería Baylón · Credify", 0.68, 3.0, 8, 0.5, 23, color="C8D6DF")
    text(item, "CV3", 9.75, 1.5, 2.7, 1.1, 67, color="E3AA7A", bold=True)
    text(
        item,
        "Omara Yamileth Baylón Vila · U23231338\n"
        "Tamara Alison Coveñas Quispe · U23204737\n"
        "César Augusto Daniel Paredes Paredes · U23259768\n"
        "Pablo Enrique Yman Avila · U23251279",
        0.68,
        4.3,
        6.9,
        1.65,
        17,
    )
    rect(item, 8.6, 4.35, 0.035, 1.65, "E3AA7A")
    text(
        item,
        "Registros ficticios\nDecisión humana\nUtilidad por demostrar",
        8.9,
        4.4,
        3.75,
        1.5,
        20,
    )
    text(
        item,
        "APF1: diagnóstico  →  APF2: registro  →  APF3: comparación",
        0.68,
        6.45,
        12,
        0.35,
        15,
        color="C8D6DF",
    )

    item = slide("Problema ML ≠ indicador financiero")
    text(item, "Una fila = un fiado evaluado", 0.7, 1.65, 6.1, 0.55, 25, bold=True)
    text(
        item,
        "late_payment\n0: pago completo dentro del plazo\n1: atraso al vencimiento contractual",
        0.7,
        2.5,
        6.15,
        1.75,
        22,
    )
    text(
        item,
        "Apoyar una revisión antes de fiar.\nNo aprobar ni rechazar automáticamente.",
        0.7,
        4.8,
        6.3,
        1.1,
        21,
        color=TEAL,
        bold=True,
    )
    rect(item, 7.4, 1.8, 0.025, 4.5, "C9D3D4")
    text(item, "5 %", 8.0, 1.85, 4.5, 1.0, 54, color=COPPER, bold=True)
    text(
        item,
        "Pérdida mensual estimada\n÷ ventas del mismo mes × 100",
        8.0,
        3.1,
        4.6,
        1.0,
        22,
    )
    text(
        item,
        "Referencia por experiencia.\nSin corroboración contable específica.\n"
        "No es prevalencia ni meta de accuracy.",
        8.0,
        4.7,
        4.6,
        1.35,
        18,
    )

    item = slide("Datos trazables, pero todos ficticios")
    text(item, "DESARROLLO", 0.75, 1.65, 5, 0.35, 16, color=TEAL, bold=True)
    text(item, "1289", 0.7, 2.15, 5.1, 1, 60, bold=True)
    text(item, "fiados etiquetados · 125 clientes", 0.75, 3.4, 5.6, 0.5, 21)
    text(
        item,
        "943 train + 346 validación originales\nSin el test antiguo ni la cohorte final v2",
        0.75,
        4.35,
        5.55,
        1,
        19,
    )
    rect(item, 6.6, 1.7, 0.025, 3.8, "C9D3D4")
    text(item, "FINAL NUEVO CV3", 7.1, 1.65, 5.1, 0.35, 16, color=TEAL, bold=True)
    text(item, "1073", 7.05, 2.15, 5.3, 1, 60, bold=True)
    text(item, "evaluables · 120 clientes en la cohorte", 7.1, 3.4, 5.55, 0.7, 20)
    text(
        item,
        "1091 fiados − 18 sin desenlace\n695 puntuales + 378 atrasados",
        7.1,
        4.35,
        5.5,
        1,
        20,
    )
    text(
        item,
        "Exclusiones de la fuente: 309 del test antiguo + 24 sin etiqueta = 333",
        0.75,
        6.0,
        11.9,
        0.65,
        19,
        color=COPPER,
    )

    item = slide("EDA de desarrollo: señal, no causalidad")
    text(
        item,
        "877 puntuales (68,04 %)  |  412 atrasos (31,96 %)  |  n = 1289",
        0.7,
        1.5,
        12,
        0.45,
        19,
    )
    item["elements"].append(
        {
            "kind": "image",
            "path": str(figure),
            "x": 0.6,
            "y": 2.05,
            "w": 12.1,
            "h": 3.85,
        }
    )
    text(
        item,
        "Más historial tardío y mayor utilización se asocian con atraso en la simulación.",
        0.7,
        6.0,
        11.9,
        0.7,
        19,
        color=TEAL,
        bold=True,
    )

    item = slide("Comparar sin mezclar clientes entre pliegues")
    for x, heading, body in (
        (
            0.7,
            "1 · Preparar",
            "11 variables del snapshot\nImputación por mediana\nStandardScaler dentro de cada fit",
        ),
        (
            4.8,
            "2 · Seleccionar",
            "5 folds por cliente\nÁrbol + SVM lineal\n18 configuraciones × 7 umbrales",
        ),
        (
            8.85,
            "3 · Evaluar",
            "Selección guardada primero\nCohorte final común después\n2 referencias Dummy",
        ),
    ):
        text(item, heading, x, 2.0, 3.8, 0.55, 25, bold=True, color=TEAL)
        rect(item, x, 2.8, 3.7, 0.025, "C9D3D4")
        text(item, body, x, 3.1, 3.75, 1.9, 20)
    text(
        item,
        "SVM: calibración sigmoide en 3 folds internos también agrupados.",
        0.7,
        5.6,
        12,
        0.5,
        21,
    )
    text(
        item,
        "Calibración anidada ≠ evaluación anidada independiente de hiperparámetros.",
        0.7,
        6.3,
        12,
        0.45,
        17,
        color=COPPER,
    )

    item = slide("El criterio se fijó antes del test")
    text(item, "Maximizar F2", 0.75, 1.8, 6.2, 0.7, 35, bold=True)
    text(item, "5TP / (5TP + 4FN + FP)", 0.75, 2.85, 6.5, 0.6, 26, color=TEAL)
    text(item, "Sujeto a precisión ≥ 0,50", 0.75, 3.85, 6.35, 0.6, 27, bold=True)
    text(
        item,
        "Piso provisional: al menos tantas\nalertas correctas como falsas.",
        0.75,
        4.8,
        6.3,
        1.0,
        21,
    )
    rect(item, 7.55, 1.85, 0.025, 4.05, "C9D3D4")
    text(item, "ÁRBOL ELEGIDO EN OOF", 8.0, 1.9, 4.6, 0.4, 16, color=TEAL, bold=True)
    text(
        item,
        "Profundidad 3\nHoja mínima 16\nPesos balanced\nUmbral 0,70",
        8.0,
        2.7,
        4.5,
        2.25,
        24,
    )
    text(
        item,
        "Supuesto técnico, no costo, capacidad ni meta acordada con el propietario.",
        0.75,
        6.25,
        11.9,
        0.5,
        18,
        color=COPPER,
    )

    item = slide("Mismo final para los cuatro modelos")
    names = {
        "tree": "Árbol · τ 0,70",
        "svm": "SVM · τ 0,50",
        "most_frequent": "Siempre puntual",
        "constant_1": "Siempre atraso",
    }
    data = [
        [
            names[name],
            *(
                f"{report['models'][name]['final'][key]:.4f}".replace(".", ",")
                for key in ("precision", "recall", "f1", "f2", "accuracy")
            ),
        ]
        for name in names
    ]
    table(
        item,
        ["Modelo", "Precisión", "Recall", "F1", "F2", "Accuracy"],
        data,
        0.65,
        1.8,
        [3.0, 1.8, 1.8, 1.8, 1.8, 1.8],
        size=17,
    )
    text(item, "11,90 % de recall", 0.75, 5.1, 8, 0.75, 34, color=COPPER, bold=True)
    text(
        item,
        "El árbol no ofrece buena cobertura. El Dummy positivo supera su F2, "
        "pero no el piso de precisión.",
        0.75,
        6.0,
        11.9,
        0.65,
        19,
    )

    item = slide("333 atrasos quedaron sin alerta")
    table(
        item,
        ["Desenlace / predicción", "Sin alerta", "Alerta"],
        [["Puntual", "660", "35"], ["Atraso", "333", "45"]],
        0.65,
        2.0,
        [3.1, 1.65, 1.65],
        row_height=0.85,
        size=22,
    )
    text(item, "Filas: desenlace · Columnas: predicción", 0.7, 5.0, 6.2, 0.6, 16)
    text(
        item,
        "CASO GUARDADO · CV3-L00015",
        7.5,
        1.95,
        5.1,
        0.55,
        18,
        color=TEAL,
        bold=True,
    )
    text(
        item,
        "Historial previo favorable\nPuntaje: 0,3301 < 0,70\nPredicción 0 · Desenlace 1",
        7.5,
        2.9,
        5.0,
        1.7,
        22,
    )
    text(
        item,
        "Hipótesis: cambio de conducta\no señal insuficiente.\nNo se reajusta con este caso.",
        7.5,
        5.0,
        5.0,
        1.25,
        20,
        color=COPPER,
    )

    item = slide("Inferencia ilustrativa: ejecutar, no reentrenar")
    text(
        item,
        "Entrada nueva · 11 campos · sin etiqueta conocida",
        0.7,
        1.65,
        11.9,
        0.5,
        22,
        bold=True,
    )
    text(
        item,
        "3 ventas · 2 fiados pagados · 1 tardío\nSin deuda · solicitud/cupo = 0,25",
        0.7,
        2.5,
        7.3,
        1.1,
        22,
    )
    text(item, "0,4560", 9.0, 2.2, 3.6, 0.95, 43, color=TEAL, bold=True)
    text(item, "< 0,70 → predicción 0", 8.5, 3.35, 4.1, 0.5, 20)
    rect(item, 0.65, 4.3, 12.05, 1.65, NAVY)
    command = " \\\n".join(
        [
            "python codigo/scripts/academic_credit_grouped_cv.py",
            "  --predict-artifact-dir experimento",
            "  --input-json experimento/illustrative_input.json",
            "  --output-json demo_inferencia_nueva.json",
        ]
    )
    text(item, command, 0.88, 4.5, 11.5, 1.2, 14, color="FFFFFF", mono=True)
    text(
        item,
        "Resultado guardado para respaldo. En vivo: 50 s. Predicción 0 no garantiza cobro.",
        0.7,
        6.25,
        11.9,
        0.5,
        17,
        color=COPPER,
    )

    item = slide("Métrica predictiva ≠ beneficio financiero")
    text(item, "80 alertas", 0.75, 1.9, 6.0, 0.75, 39, bold=True)
    text(
        item,
        "45 correctas · 35 falsas\n333 atrasos omitidos",
        0.75,
        3.0,
        5.95,
        1.15,
        25,
        color=COPPER,
    )
    text(
        item,
        "No demuestra ahorro, recuperación\nni reducción del 5 % referencial.",
        0.75,
        5.0,
        6,
        1.0,
        21,
    )
    rect(item, 7.1, 1.95, 0.025, 4.3, "C9D3D4")
    text(
        item,
        "ANTES DE EVALUAR IMPACTO",
        7.65,
        1.95,
        4.9,
        0.5,
        17,
        color=TEAL,
        bold=True,
    )
    text(
        item,
        "Acción humana: por definir\nCapacidad K: por verificar\n"
        "Costos FP/FN: por justificar\nMeta: propuesta pendiente",
        7.65,
        2.9,
        4.9,
        2.5,
        22,
    )

    item = slide("Contrato del MVP, inferencia local CV3")
    for x, title, body in (
        (
            0.7,
            "JSON de entrada",
            "11 campos APF2\nHistorial previo al fiado\nSin late_payment",
        ),
        (
            4.85,
            "Pipeline guardado",
            "Imputar → escalar → árbol\nHash y orden de campos\nUmbral congelado",
        ),
        (
            9.0,
            "JSON de salida",
            "Puntaje + predicción\nEtiqueta desconocida\nSin crear un crédito",
        ),
    ):
        text(item, title, x, 2.0, 3.65, 0.6, 24, color=TEAL, bold=True)
        text(item, body, x, 3.0, 3.65, 1.7, 20)
    rect(item, 0.7, 5.3, 11.9, 0.025, "C9D3D4")
    text(
        item, "HOY: función y CLI CV3 verificadas", 0.7, 5.65, 11.8, 0.5, 24, bold=True
    )
    text(
        item,
        "La web sigue en v2. Integración web CV3 y aceptación humana: pendientes.",
        0.7,
        6.35,
        11.8,
        0.45,
        18,
        color=COPPER,
    )

    item = slide("Normativa: controles acotados, no conformidad")
    text(
        item,
        "Ley N.° 29733 · D.S. N.° 016-2024-JUS",
        0.7,
        1.55,
        12,
        0.45,
        21,
        color=TEAL,
        bold=True,
    )
    text(item, "En este experimento", 0.7, 2.55, 5.9, 0.6, 26, bold=True)
    text(
        item,
        "Datos ficticios\nOnce predictores, sin DNI\nInferencia local\nIntegridad por hashes",
        0.7,
        3.45,
        5.9,
        2.2,
        23,
    )
    text(item, "Antes de datos reales", 7.1, 2.55, 5.5, 0.6, 26, bold=True)
    text(
        item,
        "Finalidad y base jurídica\nAviso / consentimiento, si aplica\n"
        "Conservación, ARCO y seguridad\nRevisión de proveedores",
        7.1,
        3.45,
        5.5,
        2.2,
        21,
    )
    text(
        item,
        "La revisión individual del grupo sigue pendiente; la IA y los tests no la sustituyen.",
        0.7,
        6.25,
        12,
        0.5,
        18,
        color=COPPER,
    )

    item = slide("Método corregido. Utilidad por demostrar.", dark=True)
    for x, title, body in (
        (0.75, "Representatividad", "Calibrar parámetros con\nfuente verificable."),
        (
            4.95,
            "Baja detección",
            "No automatizar el fiado.\nRevisar objetivo y costos.",
        ),
        (9.0, "Confusión de versiones", "Web v2 ≠ CLI CV3.\nMantener trazabilidad."),
    ):
        text(item, title, x, 2.15, 3.65, 0.75, 21, color="E3AA7A", bold=True)
        text(item, body, x, 3.2, 3.6, 1.5, 21)
    text(
        item,
        "Fuentes → meta justificada → revisión humana → ensayo",
        0.75,
        5.15,
        11.9,
        0.9,
        27,
        bold=True,
    )
    text(
        item,
        "Cualquier nueva selección necesita otro test no consultado. Preguntas: 5 minutos.",
        0.75,
        6.35,
        11.9,
        0.5,
        17,
        color="C8D6DF",
    )

    presentation = Presentation()
    presentation.slide_width, presentation.slide_height = Inches(13.333333), Inches(7.5)
    elapsed = 0
    rendered = []
    for item in deck:
        bg = NAVY if item["dark"] else PAPER
        owner = item["owner"]
        stamp = (
            f"{elapsed // 60:02}:{elapsed % 60:02}–"
            f"{(elapsed + item['seconds']) // 60:02}:{(elapsed + item['seconds']) % 60:02}"
        )
        text(
            item,
            "UTP / GRUPO 2 / CV3",
            0.65,
            0.25,
            5.3,
            0.25,
            10,
            color="C8D6DF" if item["dark"] else TEAL,
            bold=True,
        )
        text(
            item,
            f"{owner} · {stamp} · {item['number']:02}/13",
            8.5,
            0.25,
            4.15,
            0.25,
            10,
            align="right",
        )
        if item["number"] != 1:
            text(item, item["title"], 0.65, 0.8, 12.05, 0.65, 30, bold=True)
        text(
            item,
            "Datos simulados · Reparto y tiempos propuestos · Revisión humana pendiente",
            0.65,
            7.1,
            12.05,
            0.22,
            9.5,
            color="C8D6DF" if item["dark"] else "526572",
        )
        native = presentation.slides.add_slide(presentation.slide_layouts[6])
        native.background.fill.solid()
        native.background.fill.fore_color.rgb = RGBColor.from_string(bg)
        native.notes_slide.notes_text_frame.text = item["notes"]
        elements = []
        for element in item["elements"]:
            x, y, w, h = [element[key] for key in ("x", "y", "w", "h")]
            assert x >= 0 and y >= 0 and x + w <= 13.34 and y + h <= 7.5, element
            style = (
                f"left:{x * 96}px;top:{y * 96}px;width:{w * 96}px;height:{h * 96}px;"
            )
            if element["kind"] == "rect":
                shape = native.shapes.add_shape(
                    MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h)
                )
                shape.fill.solid()
                shape.fill.fore_color.rgb = RGBColor.from_string(element["fill"])
                shape.line.fill.background()
                elements.append(
                    f'<div class="shape" style="{style}background:#{element["fill"]}"></div>'
                )
            elif element["kind"] == "image":
                native.shapes.add_picture(
                    element["path"],
                    Inches(x),
                    Inches(y),
                    width=Inches(w),
                    height=Inches(h),
                )
                image = base64.b64encode(Path(element["path"]).read_bytes()).decode()
                elements.append(
                    f'<img class="shape" style="{style}" src="data:image/png;base64,{image}">'
                )
            elif element["kind"] == "text":
                shape = native.shapes.add_textbox(
                    Inches(x), Inches(y), Inches(w), Inches(h)
                )
                frame = shape.text_frame
                frame.word_wrap, frame.auto_size = True, MSO_AUTO_SIZE.NONE
                frame.margin_left = frame.margin_right = frame.margin_top = (
                    frame.margin_bottom
                ) = 0
                for index, line in enumerate(element["text"].split("\n")):
                    paragraph = (
                        frame.paragraphs[0] if index == 0 else frame.add_paragraph()
                    )
                    paragraph.text, paragraph.line_spacing = line, 1.08
                    paragraph.space_before = paragraph.space_after = Pt(0)
                    paragraph.alignment = (
                        PP_ALIGN.RIGHT if element["align"] == "right" else PP_ALIGN.LEFT
                    )
                    paragraph.font.name = "Consolas" if element["mono"] else "Arial"
                    paragraph.font.size = Pt(element["size"])
                    paragraph.font.bold = element["bold"]
                    paragraph.font.color.rgb = RGBColor.from_string(element["color"])
                font = "Consolas,monospace" if element["mono"] else "Arial,sans-serif"
                elements.append(
                    f'<div class="shape txt" style="{style}font:{element["size"]}pt/1.08 {font};'
                    f"font-weight:{700 if element['bold'] else 400};color:#{element['color']};"
                    f'text-align:{element["align"]}">{html.escape(element["text"])}</div>'
                )
            else:
                data = [element["headers"], *element["rows"]]
                grid = native.shapes.add_table(
                    len(data), len(data[0]), Inches(x), Inches(y), Inches(w), Inches(h)
                ).table
                for column, width in zip(grid.columns, element["widths"], strict=True):
                    column.width = Inches(width)
                html_rows = []
                for row_index, values in enumerate(data):
                    fill = (
                        NAVY
                        if row_index == 0
                        else "E1ECE6"
                        if row_index == 1
                        else "EFE9DF"
                    )
                    color = "FFFFFF" if row_index == 0 else INK
                    html_cells = []
                    for column_index, value in enumerate(values):
                        cell = grid.cell(row_index, column_index)
                        cell.text = str(value)
                        cell.fill.solid()
                        cell.fill.fore_color.rgb = RGBColor.from_string(fill)
                        cell.margin_left = cell.margin_right = Inches(0.1)
                        cell.margin_top = cell.margin_bottom = Inches(0.08)
                        paragraph = cell.text_frame.paragraphs[0]
                        paragraph.line_spacing = 1.08
                        paragraph.space_before = paragraph.space_after = Pt(0)
                        paragraph.font.name, paragraph.font.size = (
                            "Arial",
                            Pt(element["size"]),
                        )
                        paragraph.font.bold = row_index == 0
                        paragraph.font.color.rgb = RGBColor.from_string(color)
                        html_cells.append(
                            f'<div style="width:{element["widths"][column_index] * 96}px;'
                            f"background:#{fill};color:#{color};"
                            f'font-weight:{700 if row_index == 0 else 400}">'
                            f"{html.escape(str(value))}</div>"
                        )
                    html_rows.append(
                        '<div class="tr">' + "".join(html_cells) + "</div>"
                    )
                elements.append(
                    f'<div class="shape tbl" style="{style}font-size:{element["size"]}pt;'
                    f'--rh:{element["row_height"] * 96}px">'
                    + "".join(html_rows)
                    + "</div>"
                )
        rendered.append(
            f'<section class="slide" data-number="{item["number"]}" style="background:#{bg}">'
            + "".join(elements)
            + "</section>"
        )
        elapsed += item["seconds"]
    presentation.save(output / (NAME + ".pptx"))
    reopened = Presentation(output / (NAME + ".pptx"))
    assert len(reopened.slides) == 13
    assert all(slide.notes_slide.notes_text_frame.text for slide in reopened.slides)
    css = """@page{size:13.333333in 7.5in;margin:0}*{box-sizing:border-box}
body{margin:0;font-family:Arial,sans-serif}
.slide{width:1280px;height:720px;position:relative;break-after:page;overflow:hidden}
.slide:last-child{break-after:auto}.shape{position:absolute}.txt{white-space:pre-wrap;overflow-wrap:normal}
.tbl .tr{display:flex;height:var(--rh)}
.tbl .tr>div{padding:8px 10px;border:1px solid #f6f3eb;line-height:1.08;overflow-wrap:normal}
"""
    (output / (NAME + ".html")).write_text(
        '<!doctype html><html lang="es"><meta charset="utf-8"><title>APF3 CV3</title><style>'
        + css
        + "</style><body>"
        + "".join(rendered)
        + "</body></html>"
    )
    planned = Counter()
    for item in notes:
        planned[item["owner"]] += item["seconds"]
    metadata = {
        "slides": 13,
        "planned_seconds": elapsed,
        "live_inference_reserved_seconds": 50,
        "planned_speaker_seconds": dict(planned),
        "spoken_words": sum(len(re.findall(r"\S+", item["spoken"])) for item in notes),
        "human_rehearsal": "Pending",
        "roles": "Proposed; not evidence of past contribution",
        "source_report": "experimento/grouped_cv_report.json",
        "source_report_sha256": hashlib.sha256(
            (root / "experimento/grouped_cv_report.json").read_bytes()
        ).hexdigest(),
        "slides_data": [
            {key: item[key] for key in ("number", "title", "owner", "seconds")}
            for item in notes
        ],
    }
    (output / "plan-sustentacion.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
    )

    spec = importlib.util.spec_from_file_location(
        "layout", REPO / "deploy/generate-apf3-report.py"
    )
    layout = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(layout)
    compact = [
        "# Guion de sustentación APF3 · Grupo 2\n\n"
        "**Plan:** 12 minutos, 13 diapositivas. Incluye 50 segundos de operación en vivo. "
        "Reparto propuesto; ensayo y revisión humana pendientes.\n\n"
        + layout.table(
            ["Diapositiva", "Expositor", "Segundos"],
            [[n["number"], n["owner"], n["seconds"]] for n in notes],
        )
    ]
    for begin, end in ((0, 3), (3, 6), (6, 9), (9, 13)):
        chunks = []
        for note in notes[begin:end]:
            chunks.append(
                f"## {note['number']}. {note['title']}\n\n"
                f"**Tiempo:** {note['seconds']} s · **Expositor propuesto:** {note['owner']}\n\n"
                f"{note['spoken']}\n\n**Apoyo:** {note['first_action']}"
            )
        compact.append("\n\n".join(chunks))
    questions = source.split("# Preguntas difíciles y respuestas breves", 1)[1].split(
        "# Lista de revisión humana pendiente", 1
    )[0]
    items = re.findall(r"(?m)^\*\*¿.*?(?=\n\n\*\*¿|\Z)", questions.strip(), flags=re.S)
    assert len(items) == 12
    compact.extend(
        [
            "# Preguntas difíciles · 1/2\n\n" + "\n\n".join(items[:6]),
            "# Preguntas difíciles · 2/2\n\n" + "\n\n".join(items[6:]),
            "# Demo y revisión humana\n\n**En vivo:** 20 segundos hablados + 50 de operación. "
            "Mostrar entrada, ejecutar solo inferencia y explicar salida sin garantía de cobro.\n\n"
            "```bash\npython codigo/scripts/academic_credit_grouped_cv.py "
            "--predict-artifact-dir experimento --input-json experimento/illustrative_input.json "
            "--output-json demo_inferencia_nueva.json\n```\n\n"
            "**Contingencia:** declarar el fallo y mostrar "
            "experimento/illustrative_prediction.json "
            "como resultado guardado, no como ejecución en vivo. Usar una salida nueva; "
            "no borrar evidencia.\n\n"
            + source.split("# Lista de revisión humana pendiente", 1)[1],
        ]
    )
    guion = "\n\n<!-- PAGE -->\n\n".join(compact)
    form = (REPO / "docs/APF3_Ficha_Calibracion_y_Meta_CV3.md").read_text()
    owner_form = (REPO / "docs/APF3_Ficha_Propietario_Baylon.md").read_text()
    for filename, content in (
        ("APF3_Grupo2_Guion_12min", guion),
        ("APF3_Grupo2_Ficha_Calibracion_Meta", form),
        ("APF3_Ficha_Propietario_Baylon", owner_form),
    ):
        (output / (filename + ".md")).write_text(content)
        layout.documents(content, output, name=filename, expected_figures=0)
        path = output / (filename + ".html")
        markup = path.read_text().replace(
            "margin-top:30mm; font-size:22pt;", "margin-top:0; font-size:17pt;"
        )
        compact_style = """<style>
body{font:10pt/1.16 Arial,sans-serif}p{margin-bottom:5px}
h1{font-size:15pt;margin-bottom:8px}h2{font-size:11.5pt;margin:8px 0 5px}
h3{font-size:10.5pt;margin:7px 0 4px}th,td{padding:4px}
</style>"""
        markup = markup.replace("</head>", compact_style + "</head>")
        path.write_text(markup)
        editable = WordDocument(output / (filename + ".docx"))
        editable.styles["Normal"].font.size = WordPt(10)
        editable.styles["Normal"].paragraph_format.space_after = WordPt(4)
        editable.save(output / (filename + ".docx"))
    shutil.copyfile(
        REPO / "docs/APF3_Guion_Sustentacion_CV3.md",
        output / "Guion_completo_con_indicaciones.md",
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    generate(parser.parse_args().root)
