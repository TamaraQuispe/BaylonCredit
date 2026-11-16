"""Build an editable V4 deck from frozen JSON; never load or fit ML models."""

import argparse
import importlib.util
import json
from pathlib import Path

import matplotlib.pyplot as plt
from pptx import Presentation


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


LAYOUT = module("v4_layout", "generate-apf3-report.py")
NOTES = module("v4_notes", "generate-apf3-defense.py")
RENDER = module("v4_slides", "slide-renderer.py")
NAME = "APF3_TD_Grupo2_ML_Innovacion"
TEAL, COPPER, MUTED = "236F69", "A85632", "526572"


def generate(root):
    experiment = root / "experimento"
    output = root / "sustentacion"
    output.mkdir(exist_ok=True)
    (output / "figuras").mkdir(exist_ok=True)
    source = Path(__file__).resolve().parents[1] / "docs/APF3_Guion_Sustentacion_V4.md"
    before = {p.name: LAYOUT.digest(p) for p in experiment.iterdir() if p.is_file()}
    report = json.loads((experiment / "aligned_v4_report.json").read_text())
    verification = json.loads((root / "verificacion-reproduccion.json").read_text())
    assert verification["passed"]
    assert report["selection"]["global_winner"]["family"] == "svm"
    models = report["models"]
    anchors = report["provenance"]["source_anchors"]
    notes = NOTES.parse_notes(source.read_text())
    rows = json.loads((experiment / "development_rows.json").read_text())
    input_data = json.loads((experiment / "illustrative_input.json").read_text())
    illustration = json.loads((experiment / "illustrative_output.json").read_text())
    eda = json.loads((root / "informe/verificacion-informe-v4.json").read_text())
    assert eda["reproduction"]["verified"]
    assert len(rows) == 552 and sum(r["late_payment"] for r in rows) == 68
    plt.switch_backend("Agg")
    plt.rcParams.update({"font.size": 14, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(12, 3.6), layout="constrained")
    for ax, groups, title in zip(
        axes,
        eda["relationships"].values(),
        ("Historial previo", "Utilizaci\u00f3n previa"),
        strict=True,
    ):
        for index, group in enumerate(groups):
            if group["rate"] is None:
                ax.text(index, 4, "Sin casos", ha="center", fontsize=13)
            else:
                rate = 100 * group["rate"]
                ax.bar(index, rate, color="#" + TEAL)
                ax.text(index, rate + 4, f"{rate:.1f}%", ha="center", fontsize=14)
        ax.set(
            title=title,
            ylabel="Atraso (%)",
            xticks=range(3),
            xticklabels=[f"{g['band']}\nn={g['n']}" for g in groups],
            ylim=(0, 115),
            xlim=(-0.6, 2.6),
        )
        ax.tick_params(axis="x", labelsize=12)
    figure = output / "figuras/eda_presentacion.png"
    fig.savefig(figure, dpi=150, facecolor="#F6F3EB")
    plt.close(fig)
    deck = []

    def slide(title, dark=False):
        item = {**notes[len(deck)], "title": title, "dark": dark, "elements": []}
        deck.append(item)
        return item

    def text(item, value, x, y, w, h, size=23, **style):
        item["elements"].append(
            dict(kind="text", text=value, x=x, y=y, w=w, h=h, size=size, **style)
        )

    def rect(item, x, y, w, h, fill):
        item["elements"].append(dict(kind="rect", x=x, y=y, w=w, h=h, fill=fill))

    def table(item, headers, values, y, widths, row_height=0.64, size=18):
        item["elements"].append(
            dict(
                kind="table",
                headers=headers,
                rows=values,
                x=0.65,
                y=y,
                w=sum(widths),
                h=row_height * (len(values) + 1),
                widths=widths,
                row_height=row_height,
                size=size,
            )
        )

    def image(item, path, x, y, w, h):
        item["elements"].append(dict(kind="image", path=str(path), x=x, y=y, w=w, h=h))

    def number(value):
        return f"{value:.5f}".replace(".", ",")

    item = slide("Fiado a un d\u00eda\nDel registro a la revisi\u00f3n", True)
    text(item, item["title"], 0.68, 1.1, 9, 1.65, 38, bold=True)
    text(item, "Cervecer\u00eda Bayl\u00f3n / Credify", 0.7, 3, 9, 0.5, 25)
    text(item, "V4", 10, 1.2, 2.5, 1, 66, color="E3AA7A", bold=True)
    text(item, "APF1: problema  >  APF2: MVP  >  APF3: evidencia ML", 0.7, 3.75, 12, 0.5, 20)
    text(
        item,
        "Omara Yamileth Bayl\u00f3n Vila / U23231338\n"
        "Tamara Alison Cove\u00f1as Quispe / U23204737\n"
        "C\u00e9sar Augusto Daniel Paredes Paredes / U23259768\n"
        "Pablo Enrique Yman Avila / U23251279",
        0.7,
        4.75,
        8.4,
        1.4,
        17,
    )
    text(
        item,
        "Registros ficticios\nDecisi\u00f3n humana\nUtilidad por demostrar",
        9.3,
        4.75,
        3.3,
        1.4,
        21,
        color="E3AA7A",
    )

    item = slide("Predecir atraso, no p\u00e9rdida definitiva")
    text(item, "1 fiado = 1 fila", 0.7, 1.85, 7, 0.7, 34, bold=True, color=TEAL)
    text(item, "Target: late_payment\n1 = atraso; 0 = puntual", 0.7, 2.9, 6.8, 1.1, 27)
    text(
        item,
        "Vence al d\u00eda siguiente.\nLa gracia de 3 d\u00edas no cambia la etiqueta.",
        0.7,
        4.45,
        7.1,
        1.1,
        23,
    )
    rect(item, 8.5, 1.9, 3.9, 3.95, "E8DFD0")
    text(item, "5 % referencial", 8.75, 2.2, 3.4, 0.6, 26, bold=True, color=COPPER)
    text(
        item,
        "P\u00e9rdida mensual estimada / ventas del mes.\n\nNo es prevalencia ni meta alcanzada.",
        8.75,
        3.15,
        3.3,
        2.4,
        21,
    )
    text(
        item,
        "Solo informaci\u00f3n previa al otorgamiento. Clasificaci\u00f3n supervisada binaria.",
        0.7,
        6.25,
        12,
        0.5,
        20,
        color=MUTED,
    )

    item = slide("Tres historias ficticias, no actividad real sumada")
    values = []
    for label, audit in [
        *[(f"DEV D{i + 1}", a) for i, a in enumerate(report["development"]["audits"])],
        ("FINAL", report["final"]["audit"]),
    ]:
        labels = audit["study_label_counts"]
        values.append(
            [
                label,
                audit["clients"],
                audit["study_loans"],
                f"{labels['0']} / {labels['1']}",
                labels["None"],
                audit["warmup_loans"],
            ]
        )
    table(
        item,
        ["Universo", "Clientes", "Estudio", "Clases 0 / 1", "Sin label", "Warmup"],
        values,
        1.95,
        [2, 1.6, 1.6, 2.4, 1.8, 2.6],
        0.7,
        19,
    )
    text(
        item,
        "DEV: 552 conocidos, 24 clientes\nFINAL: 259 conocidos, 12 clientes nuevos",
        0.7,
        5.1,
        8.5,
        1.1,
        26,
        bold=True,
        color=TEAL,
    )
    text(
        item,
        "Warmup excluido del entrenamiento. Desconocidos no se etiquetan como puntuales.\nCero filas reales de clientes: la fuente aporta agregados, no un dataset supervisado.",
        0.7,
        6.25,
        12,
        0.6,
        17,
        color=MUTED,
    )

    item = slide("Fuente separada del EDA de desarrollo")
    text(
        item,
        f"Rildo: {anchors['late']}/{anchors['evaluable']} evaluables = 17,78 %; abonos 10/48. Fuente parcial, no auditada.",
        0.7,
        1.65,
        12,
        0.5,
        21,
        color=TEAL,
        bold=True,
    )
    text(
        item,
        "Montos S/ 5-50; cupo S/ 80. DEV: 484 puntuales + 68 atrasos, 100 % simulado.",
        0.7,
        2.3,
        12,
        0.55,
        21,
    )
    image(item, figure, 0.7, 3, 11.9, 3.57)
    text(
        item,
        "Sin casos sin historial; exposici\u00f3n 551/1/0: no hay soporte para una tendencia general.",
        0.7,
        6.65,
        12,
        0.3,
        16,
        color=COPPER,
    )

    item = slide("Agrupar por cliente y ajustar dentro de cada fold")
    table(
        item,
        ["Modelos U3", "Preprocesamiento", "Referencia"],
        [
            ["\u00c1rbol + SVM lineal", "Mediana + StandardScaler", "2 Dummy"],
            ["12 + 6 configuraciones", "11 predictores previos", "Mayor\u00eda / positivo"],
        ],
        1.8,
        [3.6, 4.8, 3.6],
        0.7,
        19,
    )
    text(item, "3 folds externos por cliente", 0.7, 4, 11.9, 0.55, 30, bold=True, color=TEAL)
    text(
        item,
        "Por fold: 368 filas / 16 clientes entrenan; 184 / 8 validan.\nSVM: calibraci\u00f3n sigmoide con 3 folds internos agrupados.",
        0.7,
        4.85,
        12,
        1.1,
        23,
    )
    text(
        item,
        "OOF se reutiliza para seleccionar: hay optimismo. No es evaluaci\u00f3n anidada independiente.\nD2 tiene 27 atrasos; combinar historias no elimina esa reserva.",
        0.7,
        6.3,
        12,
        0.65,
        17,
        color=COPPER,
    )

    item = slide("SVM elegida antes de generar FINAL", True)
    text(
        item,
        "Umbral  >  ordenar score  >  hasta 5 / r\u00e9plica / fecha",
        0.7,
        1.8,
        12,
        0.65,
        26,
        color="E3AA7A",
        bold=True,
    )
    text(item, "F2 = 5TP / (5TP + 4FN + FP)", 0.7, 2.9, 12, 0.65, 31, bold=True)
    text(item, "F2 OOF de pol\u00edtica", 0.7, 4, 5, 0.5, 23)
    for x, family, label in [(0.7, "svm", "SVM / seleccionada"), (7.0, "tree", "\u00c1rbol")]:
        score = models[family]["review_policy"]["oof"]["metrics"]["f2"]
        text(item, number(score), x, 4.65, 5, 0.8, 42, bold=True, color="E3AA7A")
        text(item, label, x, 5.6, 5, 0.5, 22)
    text(
        item,
        "C=1 / balanced / umbral 0,10. 18 configuraciones x 7 umbrales.\nSin piso de precisi\u00f3n; F2 es propuesta investigativa, no meta comercial aprobada.",
        0.7,
        6.35,
        12,
        0.6,
        17,
    )

    item = slide("FINAL bruto: mismo conjunto, sin confundir pol\u00edticas")
    table(
        item,
        ["Modelo", "Precisi\u00f3n", "Recall", "F1", "F2", "Accuracy"],
        [
            [
                label,
                *[
                    number(models[family]["final"][key])
                    for key in ("precision", "recall", "f1", "f2", "accuracy")
                ],
            ]
            for family, label in [
                ("svm", "SVM elegida"),
                ("tree", "\u00c1rbol"),
                ("most_frequent", "Mayor\u00eda"),
                ("constant_1", "Positivo bruto"),
            ]
        ],
        1.95,
        [2.7, 1.9, 1.85, 1.85, 1.85, 1.85],
        0.7,
        18,
    )
    baseline = models["constant_1"]["review_policy"]["final"]["metrics"]
    text(
        item,
        f"Positivo con tope: F2 {number(baseline['f2'])} / recall {number(baseline['recall'])}.",
        0.7,
        5.9,
        12,
        0.5,
        23,
        bold=True,
        color=TEAL,
    )
    text(
        item,
        "259 etiquetas conocidas. \u00c1rbol tiene mayor F2 final; no cambia la selecci\u00f3n OOF.\nSVM y \u00e1rbol no pierden alertas por el tope en este FINAL.",
        0.7,
        6.5,
        12,
        0.5,
        17,
        color=MUTED,
    )

    item = slide("61 atrasos detectados, 114 falsas alertas")
    image(item, root / "informe/figuras/matriz_v4.png", 0.65, 2.1, 7.1, 3.16)
    text(item, "4 omitidos de 65", 8.1, 2.2, 4.5, 0.6, 28, bold=True, color=COPPER)
    error = next(e for e in models["svm"]["error_cases"] if e["loan_id"] == "AL4-T-L00045")
    assert error["actual"] == 1 and error["predicted"] == 0
    text(
        item,
        f"Caso ficticio del cach\u00e9:\n{error['loan_id']}\n\nScore {error['probability']:.5f} < 0,10\nReal 1 / predicho 0",
        8.1,
        3.25,
        4.4,
        2.5,
        21,
    )
    text(
        item,
        "Historial puntual no garantiza el siguiente pago.\nNo se vuelve a inferir FINAL ni se reajusta con sus errores.",
        0.7,
        6.1,
        12,
        0.85,
        23,
        color=TEAL,
    )

    item = slide("Demo: ejemplo nuevo, ficticio y sin etiqueta")
    fields = list(input_data["features"].items())
    for start, x in [(0, 0.7), (6, 7.0)]:
        subset = fields[start : start + 6]
        text(
            item,
            "\n".join(f"{key}: {value}" for key, value in subset),
            x,
            1.9,
            5.6,
            2.5,
            18,
            mono=True,
        )
    rect(item, 0.7, 4.75, 11.9, 1.25, "E1ECE6")
    score = f"{illustration['probability']:.10f}".replace(".", ",")
    text(
        item,
        f"Score {score} > 0,10 : predicci\u00f3n 1",
        0.95,
        4.95,
        11.4,
        0.45,
        26,
        bold=True,
        color=TEAL,
    )
    text(
        item,
        "Candidata a revisi\u00f3n; no aprobaci\u00f3n ni rechazo. Ratio 0,25 x S/ 80 = S/ 20.",
        0.95,
        5.55,
        11.4,
        0.35,
        18,
    )
    text(
        item,
        "20 s hablados + 50 s de operaci\u00f3n. Comando completo en el guion.\nSi falla: declarar el fallo y mostrar illustrative_output.json como resultado guardado.",
        0.7,
        6.3,
        12,
        0.65,
        18,
        color=MUTED,
    )

    item = slide("Menos revisiones, m\u00e1s omisiones: costo no medido")
    policy = models["svm"]["review_policy"]["final"]
    dummy = models["constant_1"]["review_policy"]["final"]
    table(
        item,
        ["Pol\u00edtica FINAL", "Revisiones", "Conocidas + ?", "FN"],
        [
            [
                label,
                p["reviews"],
                f"{p['reviews_known']} + {p['reviews_unknown']}",
                p["metrics"]["confusion_matrix"][1][0],
            ]
            for label, p in [("SVM", policy), ("Todo con tope", dummy)]
        ],
        1.9,
        [4.2, 2.6, 3.4, 1.8],
        0.75,
        21,
    )
    delta = dummy["reviews"] - policy["reviews"]
    text(
        item,
        f"{delta} x 2 = {delta * 2} minutos hipot\u00e9ticos",
        0.7,
        4.75,
        12,
        0.7,
        34,
        bold=True,
        color=TEAL,
    )
    text(
        item,
        "24 semanas ficticias completas + 3 d\u00edas. Tres omisiones adicionales.\nCapacidad estimada, no cronometrada; solo fiados elegibles otorgados.",
        0.7,
        5.8,
        12,
        0.95,
        23,
    )

    item = slide("Contrato local comprobado; la web sigue en v2")
    for x, title, detail in [
        (0.7, "JSON", "11 campos del MVP"),
        (5.0, "CLI V4", "Pipeline + manifiesto"),
        (9.1, "JSON", "Score / umbral / clase"),
    ]:
        rect(item, x, 2, 3.5, 1.65, "E1ECE6")
        text(item, title, x + 0.2, 2.2, 3.1, 0.5, 29, bold=True, color=TEAL)
        text(item, detail, x + 0.2, 2.95, 3.1, 0.5, 18)
    text(item, ">", 4.4, 2.5, 0.5, 0.5, 27)
    text(item, ">", 8.6, 2.5, 0.5, 0.5, 27)
    text(
        item,
        "Reproducci\u00f3n aislada: datos, m\u00e9tricas y estados aprendidos exactos.\nJoblib: bytes distintos; salvedad y cadenas locales documentadas.",
        0.7,
        4.3,
        12,
        1.1,
        24,
        color=TEAL,
        bold=True,
    )
    text(
        item,
        "Compartir esquema no acredita despliegue web V4. Sin medir latencia o disponibilidad.\nCargar solo artefactos confiables: un hash no vuelve seguro un Joblib desconocido.",
        0.7,
        6,
        12,
        0.9,
        20,
    )

    item = slide("Privacidad y supuestos: una fuente no valida todo")
    text(
        item,
        "Ley N.\u00b0 29733\nD.S. N.\u00b0 016-2024-JUS",
        0.7,
        2.05,
        5.3,
        1.3,
        30,
        bold=True,
        color=TEAL,
    )
    text(
        item,
        "Finalidad y base jur\u00eddica.\nInformaci\u00f3n, accesos y conservaci\u00f3n.\nDerechos ARCO y proveedores.\nNo publicar la ficha privada.",
        0.7,
        4,
        5.3,
        2.2,
        23,
    )
    rect(item, 6.7, 1.9, 0.04, 4.7, COPPER)
    text(item, "Hip\u00f3tesis no medidas", 7.1, 2.05, 5.5, 0.55, 28, bold=True, color=COPPER)
    text(
        item,
        "12 clientes / mundo y warmup.\nBeta(8/45 x 3, 37/45 x 3).\nSigmas log: montos 0,45; demora 0,55.\nEstabilidad entre meses ficticios.\nContado no cuantificado ni modelado.",
        7.1,
        3.2,
        5.45,
        2.9,
        23,
    )
    text(
        item,
        "Datos ficticios y hashes no certifican cumplimiento, consentimiento ni utilidad real.",
        0.7,
        6.6,
        12,
        0.35,
        18,
        color=MUTED,
    )

    item = slide("Alineaci\u00f3n parcial no es validaci\u00f3n real", True)
    text(
        item,
        "F2 supera ambas referencias\nsolo en esta simulaci\u00f3n.",
        0.7,
        2,
        12,
        1.5,
        36,
        bold=True,
        color="E3AA7A",
    )
    text(
        item,
        "Fuente: 8/45 = 17,78 %\nDEV: 68/552 = 12,32 % / FINAL: 65/259 = 25,10 %",
        0.7,
        4.1,
        12,
        1.1,
        26,
    )
    text(
        item,
        "Sin forzar tasas ni cambiar semilla. SVM conserva 114 FP y 4 FN.\nPendientes: revisi\u00f3n individual, ensayo y captura real autorizada.\nNo activar producci\u00f3n. Preguntas: 5 minutos.",
        0.7,
        5.7,
        12,
        1.25,
        22,
    )

    elapsed = 0
    for item in deck:
        stamp = f"{elapsed // 60:02}:{elapsed % 60:02} - "
        elapsed += item["seconds"]
        stamp += f"{elapsed // 60:02}:{elapsed % 60:02}"
        color = "C8D6DF" if item["dark"] else MUTED
        text(item, "UTP / GRUPO 2 / V4", 0.65, 0.25, 5, 0.25, 10, color=color, bold=True)
        text(
            item,
            f"{item['owner']} / {stamp} / {item['number']:02}/13",
            7.2,
            0.25,
            5.4,
            0.25,
            10,
            color=color,
            align="right",
        )
        if item["number"] != 1:
            text(item, item["title"], 0.65, 0.8, 12.05, 0.75, 29, bold=True)
        text(
            item,
            "Datos simulados / Reparto propuesto / Revisi\u00f3n humana pendiente",
            0.65,
            7.15,
            12,
            0.2,
            9,
            color=color,
        )
    assert len(deck) == 13 and elapsed == 720
    RENDER.export_slides(deck, output, name=NAME)
    presentation = Presentation(output / (NAME + ".pptx"))
    assert len(presentation.slides) == 13
    for native, item in zip(presentation.slides, deck, strict=True):
        assert native.notes_slide.notes_text_frame.text == item["notes"]
    sources = [
        source,
        Path(__file__),
        Path(RENDER.__file__),
        Path(NOTES.__file__),
        Path(LAYOUT.__file__),
        root / "verificacion-reproduccion.json",
        root / "informe/verificacion-informe-v4.json",
    ]
    assert before == {p.name: LAYOUT.digest(p) for p in experiment.iterdir() if p.is_file()}
    metadata = {
        "slides": 13,
        "planned_seconds": elapsed,
        "live_inference_reserved_seconds": 50,
        "planned_speaker_seconds": {
            owner: sum(n["seconds"] for n in notes if n["owner"] == owner)
            for owner in dict.fromkeys(n["owner"] for n in notes)
        },
        "spoken_words": sum(len(n["spoken"].split()) for n in notes),
        "human_rehearsal": "Pending; technical CLI verification is not a human rehearsal",
        "roles": "Proposed, not evidence of past contribution",
        "new_training": False,
        "new_predictions": False,
        "experiment_unchanged": True,
        "experiment_sha256": before,
        "source_sha256": {str(p): LAYOUT.digest(p) for p in sources},
        "slides_data": [{k: n[k] for k in ("number", "title", "owner", "seconds")} for n in deck],
    }
    LAYOUT.write_json(output / "plan-sustentacion.json", metadata)
    print(
        json.dumps(
            {
                k: metadata[k]
                for k in ("slides", "planned_seconds", "spoken_words", "experiment_unchanged")
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    generate(parser.parse_args().root)
