"""Materialize the V4 report from frozen evidence, without loading ML models."""

import argparse
import importlib.util
import json
import math
import re
import statistics
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from docx.table import Table
from docx.text.paragraph import Paragraph

SPEC = importlib.util.spec_from_file_location(
    "apf3_documents", Path(__file__).with_name("generate-apf3-report.py")
)
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)
documents, table = HELPER.documents, HELPER.table
digest, write_json, plt = HELPER.digest, HELPER.write_json, HELPER.plt
REPO = Path(__file__).resolve().parents[1]
NAME = HELPER.NAME  # The shared PDF renderer intentionally uses this basename.
OWNER_SHA = "45bc22a10ad5dccf323708b8aeabb780d8de4629ff5087cca2582c7dd055819f"


def verify_tables(text, report):
    """Compare every published raw/policy metric row at its printed precision."""
    checked = 0

    def check(cells, values):
        nonlocal checked
        assert len(cells) == len(values), (cells, values)
        for cell, value in zip(cells, values, strict=True):
            if isinstance(value, list):
                flat = [str(x) for row in value for x in row]
                assert cell == " / ".join(flat), (cell, value)
            else:
                places = len(cell.split(",")[1]) if "," in cell else 0
                assert cell == f"{value:.{places}f}".replace(".", ","), (
                    cell,
                    value,
                )
        checked += len(values)

    models = report["models"]
    names = {
        "\u00c1rbol": "tree",
        "SVM": "svm",
        "Dummy mayoritario": "most_frequent",
        "Dummy positivo": "constant_1",
        "Dummy siempre positivo": "constant_1",
        "Revisar todo": "constant_1",
    }
    primary = ["accuracy", "precision", "recall", "f1", "f2"]
    for block in text.split("\n\n"):
        if (
            not block.startswith("| Modelo")
            and not block.startswith("| Pol\u00edtica")
            and not block.startswith("| Candidato fijado")
        ):
            continue
        lines = block.splitlines()
        headers = [c.strip() for c in lines[0].strip("|").split("|")]
        for line in lines[2:]:
            cells = [c.strip() for c in line.strip("|").split("|")]
            family = next((v for k, v in names.items() if cells[0].startswith(k)), None)
            if family is None:
                continue
            model = models[family]
            if headers[1] == "Evaluaci\u00f3n":
                split = cells[1].split(",")[0].lower()
                metrics = model[split]
                if headers[2] == "Accuracy":
                    check(cells[2:], [metrics[k] for k in primary])
                else:
                    check(
                        cells[2:-1],
                        [
                            metrics[k]
                            for k in (
                                "balanced_accuracy",
                                "roc_auc",
                                "brier",
                                "confusion_matrix",
                            )
                        ],
                    )
                    assert int(cells[-1]) == sum(
                        metrics["confusion_matrix"][i][1] for i in (0, 1)
                    )
                    checked += 1
            elif headers[1] == "Accuracy":
                check(cells[1:], [model["final"][k] for k in primary])
            elif headers[1] == "Balanced accuracy":
                metrics = model["final"]
                check(
                    cells[1:-1],
                    [
                        metrics[k]
                        for k in (
                            "balanced_accuracy",
                            "roc_auc",
                            "brier",
                            "confusion_matrix",
                        )
                    ],
                )
                assert int(cells[-1]) == sum(
                    metrics["confusion_matrix"][i][1] for i in (0, 1)
                )
                checked += 1
            elif headers[1] == "Precisi\u00f3n":
                policy = model["review_policy"]["final"]
                check(
                    cells[1:],
                    [
                        policy["metrics"][k]
                        for k in ("precision", "recall", "f1", "f2", "accuracy")
                    ],
                )
            elif headers[1].startswith("Revisiones total"):
                policy = model["review_policy"]["final"]
                assert cells[1] == " / ".join(
                    str(policy[k])
                    for k in ("reviews", "reviews_known", "reviews_unknown")
                )
                check(
                    cells[2:],
                    [
                        policy["daily_max"],
                        policy["days_over_before_cap"],
                        policy["metrics"]["confusion_matrix"],
                    ],
                )
                checked += 3
            elif headers[0] == "Candidato fijado":
                policy = model["review_policy"]["oof"]
                check(
                    cells[3:],
                    [policy["metrics"][k] for k in ("precision", "recall", "f2")]
                    + [policy["reviews"]],
                )
            elif headers[1].startswith("Revisiones train"):
                for cell, key in zip(
                    cells[1:],
                    ("reviews", "daily_max", "days_over_before_cap"),
                    strict=True,
                ):
                    assert cell == " / ".join(
                        str(model["review_policy"][split][key])
                        for split in ("train", "oof")
                    )
                    checked += 2
    assert checked >= 200, checked
    return checked


def generate(source, output, experiment, reproduction_path=None):
    assert source.is_file() and experiment.is_dir()
    assert output.resolve() != experiment.resolve()
    before = {p.name: digest(p) for p in experiment.iterdir() if p.is_file()}
    sources = {
        str(source): digest(source),
        str(Path(__file__).resolve()): digest(Path(__file__)),
    }
    sources[str(Path(HELPER.__file__).resolve())] = digest(Path(HELPER.__file__))

    def load(name):
        path = experiment / name
        sources[str(path)] = digest(path)
        return json.loads(path.read_text())

    report = load("aligned_v4_report.json")
    selection = load("frozen_selection.json")
    protocol = load("protocol.json")
    calibration = load("calibration.json")
    rows = load("development_rows.json")
    cache = load("final_predictions.json")
    artifact_manifest = load("artifact_manifest.json")
    folds = load("fold_audit.json")
    load("development_audits.json")
    load("final_audits.json")
    illustrative_input = load("illustrative_input.json")
    illustrative_output = load("illustrative_output.json")
    assert report["selection"] == selection
    assert report["version"] == protocol["version"] == "academic-owner-aligned-v4"
    assert report["origen"] == "simulado" and report["research_only"]
    assert not report["business_approval"]
    assert calibration == report["provenance"]["source_anchors"]
    assert calibration["source_docx_sha256"] == OWNER_SHA
    assert [
        calibration[k]
        for k in (
            "evaluable",
            "late",
            "partial_payment_annotations",
            "partial_payment_denominator",
        )
    ] == [45, 8, 10, 48]
    for name, expected in {**selection["decision_sha256"], **artifact_manifest}.items():
        assert before[name] == expected, name
    assert before["selected_model.joblib"] == before["svm.joblib"]
    assert selection["global_winner"]["family"] == "svm"
    assert selection["families"]["svm"]["threshold"] == 0.1
    assert len(rows) == 552
    assert len({r["loan_id"] for r in rows}) == len(rows)
    assert {r["replica_id"] for r in rows} == {"AL4-D1", "AL4-D2"}
    assert len({r["client_id"] for r in rows}) == 24
    assert sum(r["late_payment"] for r in rows) == 68
    for row in rows:
        assert row["origen"] == "simulado" and row["phase"] == "study"
        assert row["late_payment"] in (0, 1)
        assert all(
            math.isfinite(row[k]) and row[k] >= 0 for k in report["feature_names"]
        )
    models = report["models"]
    for family, model in models.items():
        assert cache[family]["metrics"] == model["final"]
        assert cache[family]["review_policy"] == model["review_policy"]["final"]
        assert cache[family]["error_cases"] == model["error_cases"]
        assert len(cache[family]["predictions"]) == 260
        assert sum(p["actual"] is not None for p in cache[family]["predictions"]) == 259
    assert models["svm"]["final"]["confusion_matrix"] == [[80, 114], [4, 61]]
    assert models["svm"]["review_policy"]["final"]["metrics"]["confusion_matrix"] == [
        [80, 114],
        [4, 61],
    ]
    assert models["tree"]["final"]["f2"] > models["svm"]["final"]["f2"]
    assert (
        models["svm"]["review_policy"]["oof"]["metrics"]["f2"]
        > models["tree"]["review_policy"]["oof"]["metrics"]["f2"]
    )
    assert folds["outer_fold_count"] == 3
    assert illustrative_output["known_label"] is None
    assert illustrative_input["features"] == protocol["illustrative_input"]
    text = source.read_text()
    metric_checks = verify_tables(text, report)
    for key, value in models["svm"]["interpretation"][
        "standardized_coefficients"
    ].items():
        assert f"| {key} | {value} |" in text
    for error in models["svm"]["error_cases"][:3]:
        assert error["loan_id"] in text and str(error["probability"]) in text

    evidence_path = (
        reproduction_path or output.parent / "verificacion-reproduccion.json"
    )
    evidence = json.loads(evidence_path.read_text())
    state_path = evidence_path.parent / "estado-artefactos.json"
    states = json.loads(state_path.read_text())["models"]
    sources[str(evidence_path)] = digest(evidence_path)
    sources[str(state_path)] = digest(state_path)
    checks = evidence["checks"]
    assert evidence["passed"] is True
    assert checks["full_report_except_time_and_artifact_serialization"] is True
    assert checks["selection"] is True and checks["illustrative_inference"] is True
    for group, count in (
        ("raw", 12),
        ("policy", 12),
        ("exact_file_sha256", 15),
        ("learned_artifact_state", 5),
    ):
        assert len(checks[group]) == count and all(
            v is True for v in checks[group].values()
        ), group
    for group in (
        "integrity",
        "decision_and_artifact_chains",
        "csv_scope",
        "inference_cli",
        "environment",
    ):
        assert all(v is True for v in checks[group].values()), group
    assert checks["negative_control_detects_metric_mismatch"] is True
    reproduced = evidence_path.parent / "reproduccion"
    for name in checks["exact_file_sha256"]:
        assert digest(experiment / name) == digest(reproduced / name), name
        sources[str(reproduced / name)] = digest(reproduced / name)
    assert set(states) == set(checks["learned_artifact_state"])
    for name, state in states.items():
        assert state["learned_state_equal"] is True
        assert state["state_sha256"][0] == state["state_sha256"][1]
        assert state["binary_equal"] is False
        for index, directory in enumerate((experiment, reproduced)):
            artifact = directory / (name + ".joblib")
            assert digest(artifact) == state["binary_sha256"][index]
            sources[str(artifact)] = digest(artifact)
    for family, model in models.items():
        result = evidence["results"]["models"][family]
        for split in ("train", "oof", "final"):
            assert result["raw"][split] == model[split]
            assert result["policy"][split] == model["review_policy"][split]["metrics"]
    # The frozen illustration adds descriptive metadata to the CLI output.
    assert illustrative_output["distinctness_pass"] is True
    assert illustrative_output["requested_amount_pen"] == 20
    assert evidence["results"]["inference"] == {
        k: v
        for k, v in illustrative_output.items()
        if k not in ("distinctness_pass", "requested_amount_pen")
    }
    assert len(evidence["methods"]["excluded_time_fields"]) == 3
    assert len(evidence["methods"]["derived_hash_exceptions"]) == 2
    reproduction = {
        "status": "technical_reproduction_verified_with_binary_caveat",
        "verified": True,
        "available_evidence": str(evidence_path),
        "evidence_sha256": digest(evidence_path),
        "artifact_state_evidence": str(state_path),
        "artifact_state_evidence_sha256": digest(state_path),
        "evidence_passed": True,
        "exact_raw_comparisons": 12,
        "exact_policy_comparisons": 12,
        "exact_file_sha256_matches": 15,
        "equal_learned_artifact_states": 5,
        "joblib_binary_equal": False,
        "excluded_time_fields": evidence["methods"]["excluded_time_fields"],
        "derived_hash_exceptions": evidence["methods"]["derived_hash_exceptions"],
        "independent_validation": False,
        "new_experiment_or_inference_for_report": False,
    }

    output.mkdir(parents=True, exist_ok=True)
    figures = output / "figuras"
    figures.mkdir(exist_ok=True)
    plt.rcParams.update(
        {"font.size": 10, "axes.spines.top": False, "axes.spines.right": False}
    )
    fig, ax = plt.subplots(figsize=(7.8, 2.3), layout="constrained")
    bars = ax.bar(
        ["Puntual (0)", "Atraso (1)"], [484, 68], color=["#246c67", "#b65e39"]
    )
    ax.bar_label(bars, padding=3)
    ax.set(
        title="DEV resuelto simulado | n=552 | D1 + D2 alternativos",
        ylabel="Fiados de estudio",
        ylim=(0, 565),
    )
    fig.savefig(figures / "eda_balance.png", dpi=180)
    plt.close(fig)
    history = [
        ("Sin pagos previos", [r for r in rows if r["paid_credits"] == 0]),
        (
            "Pagados sin atraso",
            [r for r in rows if r["paid_credits"] > 0 and r["paid_late"] == 0],
        ),
        ("Con pagos tard\u00edos", [r for r in rows if r["paid_late"] > 0]),
    ]
    exposure = [
        ("0-25 %", [r for r in rows if r["utilization"] <= 0.25]),
        (">25-50 %", [r for r in rows if 0.25 < r["utilization"] <= 0.5]),
        (">50 %", [r for r in rows if r["utilization"] > 0.5]),
    ]
    relationships = []
    fig, axes = plt.subplots(1, 2, figsize=(8, 2.9), layout="constrained")
    for ax, groups, title in zip(
        axes,
        (history, exposure),
        ("Historial previo", "Utilizaci\u00f3n previa"),
        strict=True,
    ):
        summary = []
        for label, group in groups:
            positives = sum(r["late_payment"] for r in group)
            summary.append(
                {
                    "band": label,
                    "n": len(group),
                    "late": positives,
                    "rate": positives / len(group) if group else None,
                }
            )
        for index, item in enumerate(summary):
            if item["rate"] is None:
                ax.text(index, 3, "Sin casos\n(no 0 %)", ha="center", fontsize=8)
            else:
                value = item["rate"] * 100
                ax.bar(index, value, color="#315b84")
                ax.text(
                    index,
                    value + 3,
                    f"{value:.1f}%\n{item['late']}/{item['n']}",
                    ha="center",
                    fontsize=8,
                )
        ax.set(
            xticks=range(3),
            xticklabels=[f"{s['band']}\nn={s['n']}" for s in summary],
            title=title,
            ylabel="Atraso (%)",
            ylim=(0, 100),
            xlim=(-0.6, 2.6),
        )
        ax.tick_params(axis="x", labelsize=7)
        relationships.append(summary)
    fig.suptitle("DEV resuelto simulado | n=552 | sin FINAL", fontsize=10)
    fig.savefig(figures / "eda_relaciones.png", dpi=180)
    plt.close(fig)
    matrix = models["svm"]["final"]["confusion_matrix"]
    fig, ax = plt.subplots(figsize=(6.3, 2.8), layout="constrained")
    ax.imshow(matrix, cmap="Blues", vmin=0, vmax=130, aspect="auto")
    for i in range(2):
        for j in range(2):
            ax.text(
                j,
                i,
                str(matrix[i][j]),
                ha="center",
                va="center",
                fontsize=18,
                color="white" if matrix[i][j] > 65 else "#172334",
            )
    ax.set(
        xticks=[0, 1],
        yticks=[0, 1],
        xticklabels=["Puntual (0)", "Atraso (1)"],
        yticklabels=["Puntual (0)", "Atraso (1)"],
        xlabel="Predicci\u00f3n al umbral 0,10",
        ylabel="Desenlace real simulado",
        title="FINAL AL4-T | SVM seleccionada | 259 conocidos\nBruta = pol\u00edtica top-5; 1 desconocido fuera de matriz",
    )
    fig.savefig(figures / "matriz_v4.png", dpi=180)
    plt.close(fig)

    descriptors = []
    for feature, unit in (
        ("requested_amount", "PEN"),
        ("paid_credits", "conteo"),
        ("paid_late", "conteo"),
        ("outstanding", "PEN"),
        ("utilization", "ratio"),
        ("punctuality_rate", "ratio"),
        ("tenure_days", "d\u00edas"),
    ):
        values = [float(r[feature]) for r in rows]
        descriptors.append(
            [
                f"{feature} ({unit})",
                *[
                    f"{v:.{4 if unit == 'ratio' else 2}f}".replace(".", ",")
                    for v in (
                        min(values),
                        statistics.mean(values),
                        statistics.median(values),
                        max(values),
                    )
                ],
            ]
        )

    def conclusion(groups):
        parts = []
        for item in groups:
            rate = (
                f"{item['rate'] * 100:.2f}".replace(".", ",") + " %"
                if item["rate"] is not None
                else "no estimable"
            )
            parts.append(f"{item['band']}: {rate} ({item['late']}/{item['n']})")
        return "DEV resuelto (n=552): " + "; ".join(parts) + "."

    substitutions = {
        "eda_table": "**Descriptivos DEV resuelto, n=552 por variable; origen 100 % simulado.**\n\n"
        + table(
            ["Variable (unidad)", "M\u00edn.", "Media", "Mediana", "M\u00e1x."],
            descriptors,
        ),
        "history_conclusion": conclusion(relationships[0])
        + " Las bandas vac\u00edas no acreditan comportamiento de clientes sin historial; las tasas observadas no son causales.",
        "exposure_conclusion": conclusion(relationships[1])
        + " Con 551 casos en la primera banda, uno en la segunda y ninguno en la tercera, no hay soporte para afirmar una tendencia general de riesgo por exposici\u00f3n.",
    }
    assert set(re.findall(r"\{\{(\w+)\}\}", text)) == set(substitutions)
    for key, value in substitutions.items():
        text = text.replace("{{" + key + "}}", value)
    # Close editorial TODOs only in the exported copy, keeping the source intact.
    edits = {
        "Los separadores no certifican p\u00e1ginas f\u00edsicas; la exportaci\u00f3n deber\u00e1 comprobar el m\u00e1ximo de 15 p\u00e1ginas de este bloque, sin desbordes tras insertar el EDA.": "Los separadores se contrastan con la exportaci\u00f3n PDF y su registro de paginaci\u00f3n; el l\u00edmite es 15 p\u00e1ginas de este bloque, sin desbordes tras insertar el EDA.",
        "Las figuras y la tabla se preparan durante el empaquetado desde ese cach\u00e9": "Las figuras y la tabla se han preparado durante el empaquetado desde ese cach\u00e9",
        "Los estad\u00edsticos descriptivos de la tabla deben conservar unidades y denominadores de DEV": "Los estad\u00edsticos descriptivos de la tabla conservan unidades y denominadores de DEV",
        "Los gr\u00e1ficos deben conservar denominadores por banda": "Los gr\u00e1ficos conservan denominadores por banda",
        "La matriz se construir\u00e1 desde la m\u00e9trica congelada de SVM, no mediante nuevas predicciones. La construcci\u00f3n e inserci\u00f3n de figuras queda fuera de esta edici\u00f3n documental.": "La matriz se construy\u00f3 desde la m\u00e9trica congelada de SVM, no mediante nuevas predicciones. Las tres figuras est\u00e1n insertadas en esta exportaci\u00f3n.",
        "Los tres placeholders DEV y la maquetaci\u00f3n deben cerrarse desde cach\u00e9s, sin reabrir selecci\u00f3n ni ocultar resultados desfavorables.": "Los tres campos EDA DEV se materializaron desde cach\u00e9s y la paginaci\u00f3n se controla en la exportaci\u00f3n, sin reabrir selecci\u00f3n ni ocultar resultados desfavorables.",
        "EDA y tres figuras | Inserci\u00f3n/generaci\u00f3n por empaquetado pendiente": "EDA y tres figuras | Materializados desde cach\u00e9s congelados",
        "crear \u00fanicamente el Markdown V4 solicitado": "crear el Markdown V4 de base y materializar su exportaci\u00f3n Word/HTML/PDF",
        "no modifica artefactos antiguos y no genera figuras": "no modifica artefactos del experimento; las tres figuras se generan exclusivamente desde cach\u00e9s congelados",
        "reproducci\u00f3n y paginaci\u00f3n pendientes": "reproducci\u00f3n t\u00e9cnica con salvedad binaria y paginaci\u00f3n PDF comprobadas",
        "Al redactar, el paquete consultado contiene `experimento/` y `README.md`; la ruta `codigo/scripts/` siguiente es la referencia de empaquetado que debe completar y comprobar la integraci\u00f3n principal.": "El c\u00f3digo y los datos est\u00e1n empaquetados; sus controles de integridad pasan en `verificacion-reproduccion.json`. Los comandos se indican desde la ra\u00edz del paquete, no desde `informe/`.",
        "La reproducci\u00f3n limpia permanece pendiente.": "La reproducci\u00f3n t\u00e9cnica est\u00e1 comprobada con salvedad binaria Joblib, no como validaci\u00f3n independiente (Anexo C).",
        "**La reproducci\u00f3n limpia V4 est\u00e1 pendiente**": "**La reproducci\u00f3n t\u00e9cnica V4 est\u00e1 comprobada con salvedad binaria Joblib**",
        "La web sigue v2 y la reproducci\u00f3n limpia est\u00e1 pendiente.": "La web sigue v2; la reproducci\u00f3n t\u00e9cnica est\u00e1 comprobada, sin identidad binaria Joblib ni validaci\u00f3n independiente.",
        "Son versiones de la corrida congelada, no evidencia de instalaci\u00f3n o reproducci\u00f3n limpia posterior.": "La verificaci\u00f3n posterior registra esas versiones en un entorno limpio, sin red durante la ejecuci\u00f3n, y `passed=true`.",
        "## C.1. Entorno y comandos documentados, no ejecutados aqu\u00ed": "## C.1. Reproducci\u00f3n t\u00e9cnica comprobada y comandos",
        "**Reproducci\u00f3n limpia: PENDIENTE.** Comando previsto desde la ra\u00edz del paquete, con c\u00f3digo y dependencias compatibles y destino nuevo:": "**Reproducci\u00f3n t\u00e9cnica comprobada:** 12 evaluaciones brutas y 12 de pol\u00edtica exactas; 15 archivos con SHA-256 iguales y cinco estados aprendidos iguales, seg\u00fan `verificacion-reproduccion.json` y `estado-artefactos.json`. **Los bytes de los cinco Joblib NO son iguales.** Se excluyen tres timestamps y dos hashes derivados; las cadenas locales de integridad pasan. No es validaci\u00f3n independiente. Comando desde la ra\u00edz del paquete, con destino nuevo:",
        "Ese comando s\u00ed genera y ajusta al repetir el protocolo cerrado: **no fue ejecutado para este informe**. Una comprobaci\u00f3n posterior deber\u00e1 comparar selecci\u00f3n, tablas train/OOF/FINAL, pol\u00edticas, auditor\u00edas e inferencia ilustrativa, sin cambiar criterios ni presentar la repetici\u00f3n t\u00e9cnica como otro test independiente. La integraci\u00f3n principal actualizar\u00e1 el estado \u00fanicamente despu\u00e9s de contar con evidencia.": "La ejecuci\u00f3n t\u00e9cnica separada repiti\u00f3 el protocolo fijo; selecci\u00f3n, auditor\u00edas e inferencia ilustrativa coinciden. Este generador solo lee su evidencia: no reentrena ni reabre selecci\u00f3n. Repetir FINAL no agrega otro test independiente.",
        "Modo exclusivamente de inferencia sobre artefacto local confiable, con flags existentes, tambi\u00e9n documentado sin ejecutarlo:": "Modo de inferencia local confiable, ya contrastado en la verificaci\u00f3n separada; se documenta sin reejecutarlo aqu\u00ed:",
        "La reproducci\u00f3n t\u00e9cnica pendiente solo verifica el dise\u00f1o fijo, no agrega evidencia externa ni elimina el optimismo de b\u00fasqueda OOF.": "La reproducci\u00f3n t\u00e9cnica documentada solo verifica el dise\u00f1o fijo, no agrega evidencia externa ni elimina el optimismo de b\u00fasqueda OOF. Se excluyen `report.generated_utc`, `provenance.recorded_utc`, `selection.frozen_utc` y los hashes derivados `selection.decision_sha256.provenance.json` y `artifact_manifest.frozen_selection.json`; no se afirma identidad binaria de los Joblib.",
        "| Reproducci\u00f3n limpia | PENDIENTE | Entorno nuevo y comparaci\u00f3n registrada del protocolo fijo |": "| Reproducci\u00f3n t\u00e9cnica | Comprobada, con salvedad binaria Joblib | 12 brutas + 12 pol\u00edticas, 15 SHA y cinco estados iguales; no validaci\u00f3n independiente |",
        "| Paginaci\u00f3n | Portada + 14 p\u00e1ginas manuales de cuerpo | Comprobar \u226415 p\u00e1ginas f\u00edsicas antes de referencias/anexos |": "| Paginaci\u00f3n PDF | Portada + 14 p\u00e1ginas de cuerpo; 25 en total | 15 antes de referencias/anexos; control A4 sin desbordes |",
        "El siguiente paso propuesto es verificar reproducci\u00f3n y entrega, luego cerrar normativa y dise\u00f1o de captura real": "El siguiente paso propuesto es completar revisi\u00f3n humana y archivo de entrega, y cerrar normativa y dise\u00f1o de captura real",
        "y dejar la reproducci\u00f3n limpia pendiente": "y cerrar la reproducci\u00f3n t\u00e9cnica solo con evidencia final, declarando su salvedad binaria",
    }
    for old, new in edits.items():
        assert old in text, old
        text = text.replace(old, new)
    text = text.replace(
        "## A.2. Hip\u00f3tesis cuantitativas no medidas",
        "<!-- PAGE -->\n\n# Anexo A. Supuestos cuantitativos\n\n## A.2. Hip\u00f3tesis cuantitativas no medidas",
    )
    assert not re.search(r"\{\{\w+\}\}", text)
    assert OWNER_SHA in text
    stale = re.search(
        r"reproducci[o\u00f3]n[^.\n|]{0,100}\bpendiente\b", text, re.IGNORECASE
    )
    assert stale is None, stale.group() if stale else None
    assert verify_tables(text, report) == metric_checks == 224
    (output / (NAME + ".md")).write_text(text)
    result = documents(text, output, name=NAME, expected_figures=3)
    assert result["planned_body_pages"] == 14
    # Local export styling only; shared document/render helpers stay unchanged.
    html_path = output / (NAME + ".html")
    markup = html_path.read_text()
    markup = markup.replace(
        "<title>APF3 - Credify - Borrador</title>",
        "<title>APF3 - Credify - Estudio alineado V4</title>",
    )
    markup, captions = re.subn(
        r'(<p><img alt="([^"]*)"[^>]*></p>)',
        lambda match: match[1] + f'<p class="figure-caption">{match[2]}</p>',
        markup,
    )
    assert captions == 3
    for index, page in enumerate(text.split("<!-- PAGE -->")):
        if page.strip().startswith("# Anexo"):
            markup = markup.replace(
                f'class="page" data-page="{index}"',
                f'class="page appendix" data-page="{index}"',
            )
    markup = markup.replace(
        "</style>",
        """
.appendix { font-size:9.5pt; line-height:1.18; }
.appendix table { font-size:8pt; margin:7px 0; }
.appendix th,.appendix td { padding:3px; }
.appendix p { margin-bottom:7px; }
.appendix h1 { font-size:16pt; margin-bottom:10px; }
.figure-caption { font-size:8.5pt; line-height:1.1; text-align:center; margin:4px 0 8px; }
</style>""",
    )
    html_path.write_text(markup)
    document = HELPER.Document(output / (NAME + ".docx"))
    document.core_properties.title = "APF3 - Credify - Estudio alineado V4 (simulado)"
    appendix = False
    for child in document.element.body:
        if child.tag.endswith("}p"):
            paragraph = Paragraph(child, document._body)
            if paragraph.text.startswith("Anexo A."):
                appendix = True
            if appendix and paragraph.style.name == "Normal":
                paragraph.paragraph_format.line_spacing = 1.0
                paragraph.paragraph_format.space_after = HELPER.Pt(4)
                for run in paragraph.runs:
                    run.font.size = HELPER.Pt(9.5)
        elif appendix and child.tag.endswith("}tbl"):
            for row in Table(child, document._body).rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        paragraph.paragraph_format.space_after = HELPER.Pt(3)
                        paragraph.paragraph_format.line_spacing = 1.0
                        for run in paragraph.runs:
                            run.font.size = HELPER.Pt(8)
    document.save(output / (NAME + ".docx"))
    after = {p.name: digest(p) for p in experiment.iterdir() if p.is_file()}
    assert after == before, "Frozen experiment files changed during report generation"
    assert all(digest(Path(path)) == sha for path, sha in sources.items())
    validation = {
        "generated_utc": datetime.now(UTC).isoformat(),
        **result,
        "report_version": report["version"],
        "source_markdown": str(source),
        "experiment_directory": str(experiment.resolve()),
        "source_owner_document_declared_sha256": OWNER_SHA,
        "private_owner_document_read_or_published": False,
        "eda_dataset": {
            "path": "experimento/development_rows.json",
            "scope": "DEV resolved study only",
            "n": 552,
            "class_0": 484,
            "class_1": 68,
            "clients": 24,
            "unknown_or_final_rows_used": False,
        },
        "relationships": {"history": relationships[0], "exposure": relationships[1]},
        "matrix": {
            "source": "aligned_v4_report.json models.svm.final.confusion_matrix",
            "dataset": "FINAL AL4-T, known labels",
            "threshold": 0.1,
            "values": matrix,
            "policy": "threshold then top-5 per replica/civil date; no SVM alerts removed",
        },
        "metric_cells_checked_against_json": metric_checks,
        "frozen_decision_and_artifact_hashes_checked": True,
        "experiment_sha256_before": before,
        "experiment_sha256_after": after,
        "sources_modified": False,
        "new_training": False,
        "new_predictions": False,
        "new_tuning": False,
        "reproduction": reproduction,
        "human_review": "pending",
        "word_physical_pagination": "not rendered in Microsoft Word; physical page counts apply to PDF only",
        "pdf_physical_pagination": "pending renderer and pypdf verification",
        "source_sha256": sources,
        "export_editorial_replacements": edits,
    }
    write_json(output / "verificacion-informe-v4.json", validation)
    manifest_path = output / "manifest.json"
    manifest = (
        json.loads(manifest_path.read_text())
        if manifest_path.is_file()
        else {"sources": {}, "files": {}}
    )
    manifest.setdefault("sources", {}).update(sources)
    owned = [NAME + ext for ext in (".md", ".docx", ".html")]
    owned += [
        "figuras/" + name
        for name in ("eda_balance.png", "eda_relaciones.png", "matriz_v4.png")
    ]
    owned.append("verificacion-informe-v4.json")
    manifest.setdefault("files", {}).update(
        {name: digest(output / name) for name in owned}
    )
    write_json(manifest_path, manifest)
    print(
        json.dumps(
            {
                k: validation[k]
                for k in (
                    "planned_body_pages",
                    "planned_total_pages",
                    "word_tables",
                    "embedded_figures",
                    "metric_cells_checked_against_json",
                    "reproduction",
                )
            },
            indent=2,
        )
    )


def verify_render(output):
    """Audit actual PDF pages and browser overflow at the printable A4 width."""
    from pypdf import PdfReader

    browser_check = r"""
import {readFile} from 'node:fs/promises';
import path from 'node:path';
const {chromium} = await import(process.env.PLAYWRIGHT_MODULE_PATH);
const browser = await chromium.launch();
try {
  const page = await browser.newPage({viewport:{width:658,height:1120}});
  await page.route('**/*', route => route.abort());
  await page.setContent(await readFile(process.argv[1], 'utf8'));
  await page.emulateMedia({media:'print'});
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => Promise.all([...document.images].map(i => i.decode())));
  const sections = await page.locator('.page').evaluateAll(elements => elements.map(element => {
    const rect = element.getBoundingClientRect();
    const overflow = [...element.querySelectorAll('*')].filter(e => {
      const r = e.getBoundingClientRect();
      return r.left < rect.left - 1 || r.right > rect.right + 1 || e.scrollWidth > e.clientWidth + 1;
    }).map(e => ({tag:e.tagName,text:e.textContent.slice(0,100)}));
    return {title:element.querySelector('h1,h2')?.textContent,height_px:Math.ceil(rect.height),width_px:Math.ceil(rect.width),horizontal_overflow:overflow};
  }));
  for (const [index,name] of [[4,'vista-eda-v4.png'],[10,'vista-matriz-v4.png'],[17,'vista-anexo-v4.png']]) {
    await page.locator('.page').nth(index).screenshot({path:path.join(process.argv[2],name)});
  }
  console.log(JSON.stringify({printable_height_px:259*96/25.4,sections}));
} finally { await browser.close(); }
"""
    audit = json.loads(
        subprocess.run(
            [
                "node",
                "--input-type=module",
                "-e",
                browser_check,
                str(output / (NAME + ".html")),
                str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    pdf = PdfReader(output / (NAME + ".pdf"))
    text = (output / (NAME + ".md")).read_text()
    sections = text.split("<!-- PAGE -->")
    assert len(pdf.pages) == len(sections), (len(pdf.pages), len(sections))

    def normalize(value):
        return re.sub(r"\W+", "", value).lower()

    for index, (page, section) in enumerate(zip(pdf.pages, sections, strict=True)):
        title = section.strip().splitlines()[0].lstrip("# ")
        assert normalize(title) in normalize(page.extract_text()), (index + 1, title)
    for section in audit["sections"]:
        assert section["height_px"] <= audit["printable_height_px"], section
        assert not section["horizontal_overflow"], section
    reference_index = next(
        i
        for i, section in enumerate(sections)
        if section.strip().startswith("# Referencias")
    )
    assert reference_index - 1 == 14
    assert reference_index <= 15
    audit.update(
        {
            "pdf_total_pages": len(pdf.pages),
            "body_pages": reference_index - 1,
            "cover_pages": 1,
            "references_start_page": reference_index + 1,
            "references_pages": 1,
            "appendix_pages": len(pdf.pages) - reference_index - 1,
            "pdf_section_titles_match_one_to_one": True,
            "pdf_a4_pages": all(
                abs(float(p.mediabox.width) - 595.28) < 1
                and abs(float(p.mediabox.height) - 841.89) < 1
                for p in pdf.pages
            ),
            "overflow": False,
        }
    )
    assert audit["pdf_a4_pages"]
    write_json(output / "verificacion-paginacion-v4.json", audit)
    validation_path = output / "verificacion-informe-v4.json"
    validation = json.loads(validation_path.read_text())
    validation["pdf_physical_pagination"] = {
        k: v for k, v in audit.items() if k != "sections"
    }
    validation["experiment_unchanged_at_pdf_verification"] = all(
        digest(Path(validation["experiment_directory"]) / name) == sha
        for name, sha in validation["experiment_sha256_before"].items()
    )
    assert validation["experiment_unchanged_at_pdf_verification"]
    assert all(
        digest(Path(path)) == sha for path, sha in validation["source_sha256"].items()
    )
    assert validation["metric_cells_checked_against_json"] == 224
    assert validation["embedded_figures"] == 3 and len(pdf.pages) == 25
    write_json(validation_path, validation)
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for name in (
        "verificacion-informe-v4.json",
        "verificacion-paginacion-v4.json",
        "vista-eda-v4.png",
        "vista-matriz-v4.png",
        "vista-anexo-v4.png",
    ):
        manifest["files"][name] = digest(output / name)
    write_json(manifest_path, manifest)
    print(json.dumps({k: v for k, v in audit.items() if k != "sections"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", type=Path, default=REPO / "docs/APF3_TD_Grupo2_ML_Innovacion_V4.md"
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--experiment-dir", type=Path)
    parser.add_argument("--reproduction-json", type=Path)
    parser.add_argument("--verify-render", action="store_true")
    args = parser.parse_args()
    if args.verify_render:
        verify_render(args.output_dir)
    else:
        generate(
            args.source,
            args.output_dir,
            args.experiment_dir or args.output_dir / "experimento",
            args.reproduction_json,
        )
