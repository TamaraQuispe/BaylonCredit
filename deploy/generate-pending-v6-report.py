"""Export the frozen V6 study. No estimator imports, inference or data generation."""

import argparse
import copy
import csv
import hashlib
import importlib.util
import json
import os
import re
import statistics
import subprocess
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from docx import Document
from pypdf import PdfReader

REPO = Path(__file__).resolve().parents[1]
NAME = "APF3_TD_Grupo2_ML_Innovacion"
SPEC = importlib.util.spec_from_file_location(
    "document_export", Path(__file__).with_name("generate-apf3-report.py")
)
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)
table, plt = HELPER.table, HELPER.plt
FAMILIES = ("tree", "svm", "most_frequent", "constant_1")
LABELS = ("Arbol seleccionado", "SVM", "Dummy mayoritario", "Dummy constante 1")
METRICS = ("precision", "recall", "f1", "f2", "accuracy")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def fmt(value):
    return f"{value:.8f}"


def metric_table(summary, mode, splits):
    rows = []
    for family, label in zip(FAMILIES, LABELS, strict=True):
        for split in splits:
            item = summary["models"][family][mode][split]
            metrics = item if mode == "raw" else item["metrics"]
            rows.append([label, split, *[fmt(metrics[k]) for k in METRICS]])
    return table([f"Modelo {mode.upper()}", "Particion", "Precision", "Recall", "F1", "F2", "Accuracy"], rows)


def verify_metric_tables(text, summary):
    """Parse printed cells independently, including every policy queue count."""
    count = 0
    for block in text.split("\n\n"):
        if not block.startswith("| Modelo "):
            continue
        lines = block.splitlines()
        header = [x.strip() for x in lines[0].strip("|").split("|")]
        for line in lines[2:]:
            cells = [x.strip() for x in line.strip("|").split("|")]
            family = FAMILIES[LABELS.index(cells[0])]
            split = cells[1]
            if header[0] in ("Modelo RAW", "Modelo POLICY"):
                mode = header[0].split()[1].lower()
                item = summary["models"][family][mode][split]
                metrics = item if mode == "raw" else item["metrics"]
                expected = [fmt(metrics[k]) for k in METRICS]
            elif header[0] == "Modelo COLA":
                item = summary["models"][family]["policy"][split]
                expected = [str(item[k]) for k in (
                    "reviews", "reviews_known", "reviews_unknown", "daily_max",
                    "days_over_before_cap", "minutes_hypothetical",
                )]
                expected.append(" / ".join(str(v) for row in item["metrics"]["confusion_matrix"] for v in row))
            else:
                continue
            assert cells[2:] == expected, (header, cells, expected)
            count += len(expected)
    assert count >= 204, count
    return count


def generate(root, consigna, apf2):
    out = root / "informe"
    data = root / "anexos/datos"
    legal = root / "anexos/normativa-ia"
    for folder in (out, data, legal):
        folder.mkdir(parents=True, exist_ok=True)
    (out / "figuras").mkdir(exist_ok=True)
    sources = {}

    def load(relative):
        path = root / relative
        sources[relative] = sha(path)
        return json.loads(path.read_text())

    report = load("experimento/pending_v6_report.json")
    summary = load("resumen-v6.json")
    repro = load("verificacion-reproduccion.json")
    protocol = load("experimento/protocol.json")
    load("experimento/data_protocol.json")
    review = load("experimento/owner_review.json")
    load("experimento/development_rows.json")
    dev = load("experimento/development_study_rows.json")
    audits = load("experimento/development_audits.json")
    final_audit = load("experimento/final_audits.json")
    gate = load("experimento/development_gate.json")
    inference = load("inferencia-original.json")
    reproduced = load("inferencia-reproduccion.json")
    integration_loaded = [(relative, load(relative)) for relative in (
        "anexos/integracion/prueba-cli-v6.json", "anexos/integracion/latency-v6.json",
    )]
    cli, latency = [value for _, value in integration_loaded]
    assert cli["passed"] and latency["passed"] and cli["experiment_unchanged"]
    assert latency["experiment_sha256_before"] == latency["experiment_sha256_after"]
    for key in ("family", "probability", "threshold", "predicted"):
        assert cli["cli_summary"][key] == latency["illustrative_result"][key] == inference[key]
    assert latency["warm_calls"] == len(latency["samples_ms"]) == 30
    assert latency["warm_ms"]["median"] == statistics.median(latency["samples_ms"])
    assert latency["warm_ms"]["p95_nearest_rank"] == sorted(latency["samples_ms"])[28]
    assert latency["warm_ms"]["max"] == max(latency["samples_ms"])
    assert "256m" in cli["command"] and "256m" in latency["command"]
    assert cli["wrapper_sha256"] == sha(root / "APF3_TD_Grupo2_ML_Innovacion.py")
    assert cli["expected_output_sha256"] == sha(root / "experimento/illustrative_output.json")
    rss_mib = latency["peak_process_rss_kib"] / 1024
    nominal_margin_mib = 256 - rss_mib
    load("experimento/frozen_selection.json")
    load("experimento/freeze_before_final.json")
    load("experimento/fold_audit.json")
    load("experimento/final_call_ledger.json")
    load("entorno-reproduccion.json")
    assert repro["passed"] and repro["joblib_binary_equal"]
    assert inference == reproduced
    for family in FAMILIES:
        for split in ("train", "oof", "final"):
            assert summary["models"][family]["raw"][split] == report["models"][family][split]
            for key, value in summary["models"][family]["policy"][split].items():
                assert value == report["models"][family]["review_policy"][split][key]
    for path in (consigna, apf2, Path(__file__), Path(HELPER.__file__)):
        sources["fuente-local/" + path.name] = sha(path)
    # Source PDFs are read for verification but never copied (APF2 includes private signatures).
    consigna_text = "\n".join(p.extract_text() for p in PdfReader(consigna).pages)
    apf2_pdf = PdfReader(apf2)
    assert "15 páginas" in consigna_text
    assert "Tabla 17" in apf2_pdf.pages[9].extract_text()
    assert "B.4" in apf2_pdf.pages[19].extract_text()
    before = {str(p.relative_to(root)): sha(p) for p in (root / "experimento").iterdir() if p.is_file()}
    features = report["feature_names"]
    known = [r for r in dev if r["late_payment"] is not None]
    assert len(known) == 541 and len(dev) == 545
    csv_path = root / "datos/desarrollo.csv"
    sources["datos/desarrollo.csv"] = sha(csv_path)
    with csv_path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        header = reader.fieldnames
        csv_rows = list(reader)
    assert len(header) == 24 and len(csv_rows) == 545
    constants = [f for f in features if len({r[f] for r in known}) == 1]
    assert constants == summary["constant_features"]
    numeric = features + ["requested_amount", "credit_cap", "pending_at_cutoff"]
    quality = {
        "scope": "DEV known study only; warmup and FINAL excluded", "n": len(known),
        "nulls_by_column": {k: sum(r.get(k) is None or r.get(k) == "" for r in known) for k in header},
        "duplicate_loan_id_excess": len(known) - len({r["loan_id"] for r in known}),
        "duplicate_feature_vector_excess": len(known) - len({tuple(r[f] for f in features) for r in known}),
        "constants": constants, "completed_sales_equals_paid_credits": all(r["completed_sales"] == r["paid_credits"] for r in known),
        "iqr": {},
    }
    for feature in numeric:
        values = sorted(float(r[feature]) for r in known)
        q1, _, q3 = statistics.quantiles(values, n=4, method="inclusive")
        iqr = q3 - q1
        quality["iqr"][feature] = {"min": min(values), "max": max(values), "mean": statistics.mean(values),
            "q1": q1, "q3": q3, "lower": q1 - 1.5 * iqr, "upper": q3 + 1.5 * iqr,
            "outliers": sum(v < q1 - 1.5 * iqr or v > q3 + 1.5 * iqr for v in values), "action": "retain"}
    quality["amount_precision_study"] = {}
    for replica in ("PND6-D1", "PND6-D2"):
        rows = [r for r in dev if r["replica_id"] == replica]
        rounded = sum(Decimal(str(r["requested_amount"])) % Decimal("0.50") == 0 for r in rows)
        quality["amount_precision_study"][replica] = {"study": len(rows), "whole_or_half": rounded, "other_exact_cents": len(rows) - rounded}
    bands = [("30..119", 30, 120), ("120..239", 120, 240), (">=240", 240, float("inf"))]
    relation = []
    for label, low, high in bands:
        rows = [r for r in known if low <= r["tenure_days"] < high]
        relation.append({"band": label, "n": len(rows), "sales_mean": statistics.mean(r["completed_sales"] for r in rows)})
    history = []
    for label, test in (("Sin atraso previo", lambda r: r["paid_late"] == 0), ("Con atraso previo", lambda r: r["paid_late"] > 0)):
        rows = [r for r in known if test(r)]
        history.append({"group": label, "n": len(rows), "late": sum(r["late_payment"] for r in rows), "rate": statistics.mean(r["late_payment"] for r in rows)})
    quality["relations_dev_only"] = {"history": history, "tenure": relation}
    assert sum(r["n"] for r in relation) == len(known)
    assert sum(r["n"] for r in history) == len(known)
    assert all(a["hard_constraints_pass"] and a["pending_grants"] == 0 for a in [*audits, final_audit])
    assert gate["technical_dev_gate_pass"] and not gate["coherence_accepted"]
    assert protocol["candidate_count"] == {"tree": 12, "svm": 6, "thresholds_per_candidate": 7, "configuration_threshold_pairs": 126}
    quality["row_rule_violations"] = {
        "origen_not_simulado": sum(r["origen"] != "simulado" for r in known),
        "amount_outside_5_50_pen": sum(not 5 <= float(r["requested_amount"]) <= 50 for r in known),
        "cap_not_80_pen": sum(float(r["credit_cap"]) != 80 for r in known),
        "negative_counts": sum(any(r[f] < 0 for f in ("paid_credits", "paid_late", "tenure_days", "completed_sales")) for r in known),
        "paid_late_exceeds_paid_credits": sum(r["paid_late"] > r["paid_credits"] for r in known),
        "positive_pending_input": sum(any(r[f] != 0 for f in constants) for r in known),
        "requested_ratio_mismatch": sum(abs(r["requested_ratio"] - float(r["requested_amount"]) / 80) > 1e-10 for r in known),
        "punctuality_rate_mismatch": sum(abs(r["punctuality_rate"] - ((r["paid_credits"] - r["paid_late"]) / r["paid_credits"] if r["paid_credits"] else 0)) > 1e-10 for r in known),
        "temporal_order": sum(not r["evaluated_at"][:10] < r["due_date"] <= r["observed_on"] for r in known),
    }
    assert not any(quality["row_rule_violations"].values())
    dump(data / "auditoria-calidad-dev-v6.json", quality)
    descriptions = {
        "loan_id": ("texto", "ID ficticio", "Identificador unico del fiado", "PND6-*"),
        "client_id": ("texto", "ID ficticio", "Cliente; solo agrupacion CV", "PND6-*-C*"),
        "replica_id": ("categoria", "historia", "Mundo alternativo; no sucursal", "PND6-D1/D2/T"),
        "origen": ("categoria", "origen", "Procedencia rotulada", "simulado"),
        "phase": ("categoria", "fase", "CSV supervisado de estudio", "study"),
        "evaluated_at": ("datetime ISO", "America/Lima", "Instante del snapshot previo", "Anterior a vencimiento y corte"),
        "due_date": ("fecha ISO", "dia civil Lima", "Vencimiento contractual", "Dia siguiente a evaluacion"),
        "observed_on": ("fecha ISO", "dia civil Lima", "Corte de observacion", "2026-09-30"),
        "requested_amount": ("decimal(2)", "PEN", "Monto solicitado", "[5,50]"),
        "credit_cap": ("decimal(2)", "PEN", "Cupo supuesto", "80"),
        "pending_at_cutoff": ("decimal(2)", "PEN", "Saldo al corte; excluido del modelo", "[0,50]"),
        "scenario": ("categoria", "escenario", "Plan simulado; excluido del modelo", "on_time/late/partial_*"),
        "completed_sales": ("numero entero", "ventas", "Ventas de credito completadas previas; no todas las ventas MVP", ">=0; igual a paid_credits"),
        "paid_credits": ("numero entero", "fiados", "Fiados liquidados antes de evaluar", ">=0"),
        "paid_late": ("numero entero", "fiados", "Liquidados tarde antes de evaluar", "[0,paid_credits]"),
        "pending_overdue": ("numero entero", "fiados", "Saldo previo vencido", "0 en dominio V6 elegible"),
        "pending_current": ("numero entero", "fiados", "Saldo previo vigente", "0 en dominio V6 elegible"),
        "outstanding": ("decimal", "PEN", "Deuda previa total", "0 en dominio V6 elegible"),
        "utilization": ("decimal", "proporcion", "outstanding / 80", "0 en dominio V6 elegible"),
        "requested_ratio": ("decimal", "proporcion", "requested_amount / 80", "[0.0625,0.625]"),
        "tenure_days": ("numero entero", "dias", "Antiguedad desde registro ficticio", ">=0"),
        "punctuality_rate": ("decimal", "proporcion", "(paid_credits-paid_late)/paid_credits; sin historial=0", "[0,1]"),
        "overdue_rate": ("decimal", "proporcion", "Vencidos/activos; sin activos=0", "0 en dominio V6 elegible"),
        "late_payment": ("binario nullable", "clase", "0 puntual; 1 atraso desde vencimiento; no perdida definitiva", "0/1/vacio si inmaduro"),
    }
    dictionary = []
    for column in header:
        dtype, unit, description, valid = descriptions[column]
        observed = quality["iqr"].get(column)
        observed_text = f'{observed["min"]:g}..{observed["max"]:g}' if observed else " / ".join(sorted({str(r[column]) for r in known}))
        if column not in numeric:
            observed_text = observed_text if len(observed_text) < 120 else "Ver CSV; identificador/fecha no predictora"
        dictionary.append([column, dtype, unit, description, valid,
            "Etiqueta inmadura: excluir de metricas, no imputar" if column == "late_payment" else "No nulo; entrada incompleta no es evidencia; mediana solo entrenamiento",
            observed_text])
    dictionary_md = "# Diccionario V6: 24 columnas\n\nUnidad: un fiado otorgado evaluado, snapshot anterior. Rangos observados solo DEV conocido (541). Los metadatos no son predictores.\n\n" + table(["Variable", "Tipo", "Unidad", "Descripcion", "Rango valido", "Politica de nulos", "Observado DEV"], dictionary)
    (data / "diccionario-v6.md").write_text(dictionary_md + "\n")
    dump(data / "diccionario-v6.json", {"header": header, "columns": [dict(zip(["variable", "type", "unit", "description", "valid_range", "null_policy", "observed_dev"], row, strict=True)) for row in dictionary]})
    dump(legal / "revision-propietario-sanitizada-v6.json", review)
    # Only the already sanitized aggregate source is copied, never a raw Word/PDF.
    assert review["source_docx_sha256"].startswith("82d4")
    edition = datetime.now(UTC).isoformat()
    sections = []

    def page(text):
        sections.append(text.strip())

    team = table(["Integrante", "Codigo"], [
        ["Omara Yamileth Baylón Vila", "U23231338"], ["Tamara Alison Coveñas Quispe", "U23204737"],
        ["César Augusto Daniel Paredes Paredes", "U23259768"], ["Pablo Enrique Yman Avila", "U23251279"]])
    page(f"""# Machine Learning para priorizar la revision del fiado a un dia

## Cerveceria Baylon | Credify | APF3 Grupo 2

Universidad Tecnologica del Peru. Facultad de Ingenieria de Sistemas e Informatica.

Caso 4: Scoring crediticio alternativo con IA para el fiado y microcredito MYPE.

{team}

Docente: Caman Sanchez, Richard Enrique. Seccion 35036. Periodo 2026-2. Lima, Peru.

**Edicion documental V6:** {edition}. Datos simulados. Revision humana grupal pendiente.

**Ejecucion experimental conservada:** {report['provenance']['recorded_utc']}. Esta fecha no es la de edicion ni una nueva validacion independiente.

Informe sustentado en evidencia congelada, sin nuevas llamadas al modelo. La demo V6 esta publicada y autenticada; los artefactos y codigo se entregan localmente. No se publican fuentes privadas ni firmas.
""")
    page("""# 1. Resumen ejecutivo y problema ML

## Continuidad APF1 y APF2

Cerveceria Baylon, negocio familiar de San Martin de Porres operado por dos propietarios, administra fiados a un dia. APF1 identifico registro manual y ausencia de evaluacion sistematica; APF2 construyo Credify con clientes, evaluacion por reglas, fiados, abonos e historial (React, FastAPI, PostgreSQL). Se conservan equipo, empresa, problema e indicadores de cobertura de registro y evaluacion. Lean Startup orienta construir-medir-aprender y Kanban organiza el trabajo (Ries, 2011; Anderson, 2010). La URL heredada es https://demo-credify.168-75-71-113.sslip.io; su laboratorio V6 esta disponible con datos sinteticos y acceso autenticado. El acceso docente corresponde al usuario `docente@example.com`; no es una cuenta de produccion ni acredita aceptacion comercial.

La brecha sigue siendo el historial real elegible: APF2 documento cero filas exportables al cierre, no ausencia de operaciones. El 5 % mensual declarado es perdida estimada/ventas del mes, no atraso ni probabilidad; no calibra el modelo. No se consulto la base real actual.

## Formulacion y criterio de exito

**Para el propietario, el modelo clasificara el atraso de un fiado a un dia con el proposito de priorizar revision humana. F2 de politica es el criterio tecnico academico; la meta de menor tiempo exige comparar la carga medida antes y despues, registrando FN y FP.** Cada fila es un fiado otorgado, no una persona independiente. `late_payment=1` significa atraso contractual, no perdida permanente; 0 significa liquidacion completa hasta vencimiento inclusive. Sin desenlace suficiente, la etiqueta queda desconocida.

Se estudia clasificacion binaria supervisada, coherente con el contrato de APF2. La accion prevista es mostrar candidato a REVIEW en evaluacion crediticia, nunca aprobar automaticamente. Cualquier saldo previo positivo impide nuevo fiado; liquidarlo solo restablece elegibilidad para evaluar.

El equipo priorizo cualitativamente evitar atrasos omitidos (FN), reconociendo el costo de falsas alertas (FP). F2 pondera recall; beta=2 es decision academica, no costo monetario medido ni preferencia aprobada por el propietario. El arbol gano por F2 OOF de politica; la superioridad final de SVM no cambia la seleccion. El resultado permite estudiar una cola de revision, no demostrar ahorro ni confianza crediticia real.

**Baseline declarado por Rildo, por memoria y no cronometrado.** En una semana normal atiende alrededor de 14 solicitudes; otorga unos 12 fiados a 9 clientes y rechaza cerca de 2, generalmente por deuda pendiente. Revisar una solicitud le toma aproximadamente entre 1 y 3 minutos segun conozca al cliente y la deuda; calcula unos 25-35 minutos semanales en total. Resumen sanitizado: [anexos/datos/rildo-baseline.json](../anexos/datos/rildo-baseline.json). Esta es una aproximacion autoinformada, no una medicion con cronometro. La meta propuesta debe comparar esta referencia con el piloto; cinco revisiones/dia y dos minutos/caso no son una referencia validada.
""")
    trace = [
        ["11 variables de snapshot", "credit_evaluations.feature_snapshot", "Mismo esquema numerico; eventos simulados"],
        ["completed_sales", "Ventas completadas del MVP", "V6 solo ventas ligadas a credito; igual a paid_credits, no ventas al contado"],
        ["paid_credits; paid_late", "Creditos y pagos previos", "Solo liquidaciones observadas estrictamente antes de evaluar"],
        ["pending_overdue/current; outstanding; utilization; overdue_rate", "Saldos/activos", "Cinco constantes cero por elegibilidad V6; no fabricar variacion"],
        ["requested_ratio; tenure_days; punctuality_rate", "Solicitud, alta e historial", "Monto/80; dias; proporcion historica. Cupo y altas ficticios"],
        ["late_payment", "Vencimiento y pagos", "Mismo atraso contractual, no defaulted; desconocidos separados"],
        ["Fuente/volumen", "30-50 fiados reales en 4-6 semanas", "0 elegibles al cierre APF2; DEV 545 estudio/541 conocidos; no sustituye piloto"],
        ["12 a 24 columnas", "11 variables + target APF2", "12 metadatos agregados para origen, fechas y trazabilidad, excluidos del modelo"],
        ["Particion", "APF2 preveia temporal o por cliente", "CV agrupada por cliente y FINAL disjunto; no validacion temporal prospectiva"],
    ]
    page("# 2. Dataset, coherencia y preprocesamiento\n\n## 2.1. Trazabilidad del contrato\n\nFuente primaria: APF2 original, Tabla 17, pagina fisica 10/impresa 9, y Anexo B.4, fisica 20/impresa 19 (Grupo 2, 2026). El flujo cliente > evaluacion > fiado > pagos genera snapshots y desenlaces. Se declara el cambio de fuente real prevista a simulacion academica, sin afirmar captura real ni autorizacion docente adicional.\n\n" + table(["Campo/elemento APF2", "Fuente prevista", "Aplicacion/cambio V6"], trace) + "\n\nEl diccionario completo de las 24 columnas, tipos, unidades, dominios y nulos esta en Anexo A y `anexos/datos/diccionario-v6.json`. Se conservan las once entradas del contrato; los campos de escenario, saldo al corte, fechas e identificadores nunca alimentan el aprendizaje.")
    counts = table(["Historia", "Clientes", "Warmup", "Estudio", "Conocidos 0/1", "Desconocidos"], [
        [a.get("replica_id", "PND6-T"), a["clients"], a["warmup_loans"], a["study_loans"], f'{a["study_label_counts"]["0"]}/{a["study_label_counts"]["1"]}', a["study_label_counts"]["None"]]
        for a in summary["audit_summary"]])
    page(f"""## 2.2. Origen, escala y simulacion congelada

Todas las filas llevan `origen=simulado`. DEV son dos historias alternativas: 545 fiados de estudio, 541 conocidos (454/87), cuatro desconocidos, 24 clientes ficticios y 91 fiados de calentamiento. FINAL es una tercera historia: 280 de estudio, 276 conocidos (243/33), cuatro desconocidos, 12 clientes y 46 de calentamiento. No se suman como volumen real ni como sucursales simultaneas.

{counts}

Despues de ver la demo, el propietario indico que Credify tiene potencial y que el ejercicio academico es razonable, pero que antes de utilizarlo necesitaria mas pruebas y comprobar que funcione correctamente. Resumen: [anexos/normativa-ia/rildo-aceptacion-parcial-v6.json](../anexos/normativa-ia/rildo-aceptacion-parcial-v6.json). Esto solo describe interes y aceptacion parcial. La respuesta posterior endurecio el alcance: es una autorizacion prospectiva, condicionada a pruebas adicionales y confiabilidad. Resumen: [autorizacion condicionada sanitizada](../anexos/normativa-ia/rildo-autorizacion-condicionada-v6.json).

Rildo tambien declaro el baseline semanal anterior y reviso 23 elementos intencionales V5 (12 fiados, cuatro rechazos, cuatro semanas y tres supuestos), no todas las filas V6 ni el modelo. Su aclaracion impide nuevo fiado con **cualquier saldo positivo**, incluso vigente; abono o acuerdo no bastan y la liquidacion debe observarse antes de evaluar. La fuente revisada ya esta recibida; no se exige repetir aprobacion para describir la variacion semanal derivada. Revision de fuente no equivale a validacion grupal ni aceptacion global.

Los agregados base proceden de recuerdo y revision parcial de cuaderno: 48 anotaciones, 45 evaluables, ocho tardias y tres desconocidas; no son filas de entrenamiento. La referencia usual de 12 fiados/9 clientes admite variacion. Doce clientes forman un grupo de ejemplo con rotacion, no una poblacion real fija.

El protocolo de datos conserva lognormal truncada de montos S/5..50 (localizacion S/20, sigma 0.45), cupo S/80, heterogeneidad Beta (concentracion 3), abonos con probabilidad supuesta 10/48, fraccion 0.5 y atrasos de 1..15 dias. La mezcla 75 % redondeado a soles/.50 y 25 % precio exacto es **supuesto del equipo**, no frecuencia declarada; precios exactos estan permitidos. Pagos variados en 08:00..12:00 y 16:00..20:00; corte duro 20:00 es supuesto del equipo. Gracia de tres dias no convierte atraso en puntualidad. Los planes finitos de liquidacion no estiman perdida permanente.

Semillas y distribuciones completas estan en `experimento/data_protocol.json` y `protocol.json`; FINAL usa 2026111901 tras congelar seleccion. Este generador documental no simula datos.
""")
    quality_rows = [
        ["Escala del negocio", "Referencia habitual aproximada: 12 fiados / 9 clientes por semana completa", "Medias por cada una de las 24 semanas completas: ; " + "; ".join(f'{a.get("replica_id", "T")}: {a["mean_weekly_study_grants"]:.3f} fiados / {a["mean_weekly_study_grant_clients"]:.3f} clientes' for a in summary["audit_summary"])],
        ["Rangos y unidades", "Montos 5..50 PEN; cupo 80; ratios 0..1", "Tres historias: hard_constraints_pass=true; detalle DEV en anexo"],
        ["Consistencia logica y temporal", "Saldo previo bloquea; pagos anteriores; no sobrepago", "0 otorgamientos con pendiente en D1, D2 y T; hard pass en las tres"],
        ["Relaciones plausibles", "Historia de atraso/target y antiguedad/ventas", "Dos relaciones DEV conocido, Figura 2; no EDA de desenlaces FINAL"],
        ["Señal ni nula ni perfecta", "Contrastar Dummy y auditar fuga", "F2 OOF arbol 0.59757943; accuracy 0.55268022, no separacion perfecta"],
        ["Coherencia con APF2", "Campos y cambios explicitos", "11 entradas preservadas; ventas restringidas a credito; fuente simulada"],
        ["Mezcla real + simulado", "Comparacion por origen", "No aplica: 100 % simulado, cero filas reales"],
    ]
    page("## 2.3. Ficha de coherencia: siete criterios de la consigna\n\n" + table(["Criterio", "Verificacion", "Evidencia y resultado"], quality_rows) + f"\n\n**Limpieza reconstruida solo en DEV conocido (n=541).** Nulos por columna: {sum(quality['nulls_by_column'].values())}; duplicados por loan_id excedentes: {quality['duplicate_loan_id_excess']}; vectores repetidos excedentes: {quality['duplicate_feature_vector_excess']}. Los vectores iguales no se borran automaticamente: pueden ser fiados distintos del mismo historial. Cuatro etiquetas desconocidas DEV no se imputan ni puntuan; si compiten en cola.\n\nSe calcularon cercas IQR 1.5 por variable; los extremos se retienen al ser valores plausibles y limitados por reglas, no errores probados. No se recorta la distribucion para mejorar resultados. Anexo B incluye conteos, rangos, cuartiles y decision por columna.\n\nLos hard pass son controles tecnicos: integridad, rangos, reglas y temporalidad. `coherence_accepted=false` no significa datos incoherentes; significa que no existe aceptacion del propietario sobre todas las filas V6 ni validacion de rendimiento real. Rildo reviso y corrigio una muestra intencional; ese aporte valida reglas y plausibilidad, no convierte las 545 observaciones en datos auditados negocio por negocio. La escala de otorgamientos puede ser menor a la solicitud tipica por bloqueo de pendientes. Se preserva la advertencia de escala heredada, sin regenerar ni ajustar semillas.")
    fig, ax = plt.subplots(figsize=(7, 2.8))
    ax.bar(["Puntual (0)", "Atraso (1)"], [454, 87], color=["#234b63", "#bd6739"])
    for i, n in enumerate((454, 87)):
        ax.text(i, n + 8, str(n), ha="center")
    ax.set_ylabel("Fiados DEV conocidos")
    fig.tight_layout()
    fig.savefig(out / "figuras/balance-v6.png", dpi=160)
    plt.close(fig)
    stats_rows = [[f, *[f'{quality["iqr"][f][k]:.3f}' for k in ("min", "q1", "mean", "q3", "max")]] for f in ("requested_amount", "paid_credits", "paid_late", "tenure_days", "punctuality_rate")]
    page("## 2.4. EDA de desarrollo: balance y estadisticos\n\n![Figura 1. Balance en DEV conocido: 454 puntuales y 87 atrasos; cuatro etiquetas inmaduras fuera de metricas.](figuras/balance-v6.png)\n\n" + table(["Variable", "Min", "Q1", "Media", "Q3", "Max"], stats_rows) + "\n\nEl atraso representa 87/541 = 16.0813 % de las observaciones DEV conocidas. El desbalance hace inadecuado usar solo accuracy: Dummy mayoritario no detecta atrasos. Se comparan precision, recall, F1 y F2; class_weight y umbrales fueron predeclarados. No se aplica sobremuestreo. Los estadisticos describen transacciones sinteticas repetidas, no una muestra independiente de personas.\n\nLa elegibilidad produce cinco entradas constantemente cero y `completed_sales == paid_credits`. Se mantienen para respetar el contrato, pero no se atribuye capacidad explicativa a la deuda ni importancia independiente a variables duplicadas.")
    fig, axes = plt.subplots(1, 2, figsize=(9, 3))
    axes[0].bar(["Sin atraso\nprevio", "Con atraso\nprevio"], [r["rate"] for r in history], color="#234b63")
    axes[0].set_ylabel("Proporcion late_payment=1")
    axes[1].bar([r["band"] for r in relation], [r["sales_mean"] for r in relation], color="#bd6739")
    axes[1].set_ylabel("Media completed_sales")
    axes[1].set_xlabel("Antiguedad, dias")
    fig.tight_layout()
    fig.savefig(out / "figuras/relaciones-v6.png", dpi=160)
    plt.close(fig)
    page("## 2.5. Dos relaciones esperadas del negocio\n\n![Figura 2. Historia de atraso frente a atraso actual y antiguedad frente a ventas de credito; solo DEV conocido.](figuras/relaciones-v6.png)\n\n" + table(["Historia previa", "n", "Atrasos actuales", "Proporcion"], [[r["group"], r["n"], r["late"], fmt(r["rate"])] for r in history]) + "\n\n" + table(["Banda predefinida (dias)", "n", "Media ventas completadas"], [[r["band"], r["n"], fmt(r["sales_mean"])] for r in relation]) + "\n\n**Interpretacion.** Se espera que antecedentes tardios contengan señal de comportamiento futuro, sin determinarlo: ambos grupos pueden fallar o cumplir. El grafico cuantifica esa asociacion dentro del simulador, no causalidad ni validez externa. Una mayor antiguedad permite acumular ventas completadas, pero la rotacion y los bloqueos tambien influyen. Las bandas 30..119, 120..239 y >=240 fueron fijadas para describir DEV, no optimizadas con FINAL.\n\nSe usan antecedentes ya observados, nunca pagos futuros del propio fiado. Estas dos relaciones complementan el balance y justifican explorar historial y antiguedad; no permiten recomendar variar deuda pendiente ni inventar ventas al contado.")
    page("""# 3. Modelado y comparacion

## 3.1. Preparacion y prevencion de fuga

Se conserva un Pipeline fresco por pliegue: `SimpleImputer(strategy=median)` y `StandardScaler`, tambien para Dummy y arbol; SVM lo requiere por su margen. Las once variables son numericas, por lo que no hay codificacion categorica ni one-hot. Origen, ID y fechas son metadatos. La mediana y el escalado se ajustan exclusivamente en entrenamiento conocido, nunca con FINAL o etiquetas desconocidas. Una entrada de entrenamiento completamente ausente detiene la ejecucion.

`punctuality_rate=(paid_credits-paid_late)/paid_credits` es una variable derivada interpretable; sin denominador vale cero por convencion, no por puntualidad demostrada. `requested_ratio=monto/80` normaliza la solicitud. Los snapshots preceden al otorgamiento; se excluyen target, pagos futuros, escenario, saldo al corte, propension latente y scores previos. La lista congelada no se cambia despues de OOF/FINAL.

## 3.2. Particion y comparabilidad

StratifiedGroupKFold agrupa por client_id, con tres pliegues externos e internos guardados; semillas externas 2026111801 e internas 2026111802. Las validaciones externas tienen 182, 179 y 180 filas conocidas (minoritarias 29, 30 y 28); cada cliente queda en un solo lado. No es una division 80/20: entrenamiento externo contiene 359, 362 y 361 filas. Se reutiliza el plan exacto, sin buscar semillas por resultados.

Los desconocidos se asignan al pliegue del cliente, compiten por capacidad y no calibran ni entran a metricas. FINAL mantiene IDs disjuntos y se genero solo despues de congelar modelo y umbral. Hubo un lote por familia sobre 280 filas; el analisis documental solo reutiliza sus resultados guardados.

## 3.3. Modelos de Unidad 3

Arbol de decision: reglas explicables y limites de profundidad/hoja para un conjunto pequeño. SVM lineal: margen regularizado, con calibracion sigmoid interna por grupos (`ensemble=false`); no usa `probability=true`. Dos Dummy comparables: mayoritario y constante 1. Todos comparten filas, pliegues, transformacion y politica de capacidad. El escalado tambien se conserva en el arbol para igualdad del procedimiento, no por necesidad matematica.

El estudio evalua nuevos clientes sinteticos del mismo simulador; no certifica generalizacion temporal ni real. Filas repetidas no son 541 personas independientes.
""")
    overfit = metric_table(summary, "raw", ("train", "oof"))
    page("## 3.4. Busqueda congelada y sobreajuste\n\nGrilla arbol: profundidad {2,3,4}, hoja minima {8,16}, peso {None,balanced}: 12 configuraciones. SVM: C={0.1,1,10}, peso {None,balanced}, kernel lineal: seis. Siete umbrales {0.1,...,0.7} producen 126 pares configuracion-umbral. Dummy usa 0.5. Se maximiza F2 OOF de politica; desempates: recall, precision, F1, menos revisiones, orden declarado de grilla, cercania a 0.5 y menor umbral. No se exigio precision minima.\n\n**Gano arbol, candidato indice 9, profundidad 4, hoja 8, balanced, random_state=42, umbral 0.2.** F2 OOF de politica 0.59757943 frente a SVM 0.59654631 (C=1, balanced, umbral 0.1). La diferencia es pequeña; no implica superioridad estadistica.\n\n" + overfit + f"\n\nCaida F2 RAW train-OOF del arbol: {fmt(summary['models']['tree']['raw']['train']['f2'] - summary['models']['tree']['raw']['oof']['f2'])}; OOF-FINAL: {fmt(summary['models']['tree']['raw']['oof']['f2'] - summary['models']['tree']['raw']['final']['f2'])}. Profundidad y hoja limitadas reducen complejidad; no eliminan optimismo. En SVM, C regulariza y la calibracion usa particiones internas del entrenamiento.\n\nOOF se reutilizo para elegir configuracion y umbral: su ganador es optimista; calibracion interna no equivale a evaluacion anidada independiente de hiperparametros. El deterioro FINAL se reporta sin reseleccion ni nuevos ajustes.")
    page("# 4. Evaluacion e interpretacion de negocio\n\n## 4.1. Resultados RAW en FINAL intacto\n\n" + metric_table(summary, "raw", ("final",)) + "\n\nMetricas en 276 etiquetas conocidas; clase positiva=atraso. Precision indefinida usa zero_division=0. Cuatro desconocidos no se convierten en puntuales.\n\n![Figura 3. Matriz FINAL del arbol: real por filas y predicho por columnas, orden 0/1.](figuras/matriz-v6.png)\n\nEl arbol detecta 29/33 atrasos (recall 0.87878788), omite cuatro y produce 162 FP, con 81 TN. Precision 0.15183246 y accuracy 0.39855072 reflejan carga alta de falsas alertas. La SVM obtiene mejor F2 FINAL (0.53278689), pero **no se selecciona con el test**. Dummy mayoritario logra accuracy 0.88043478 con F2=0: demuestra por que accuracy no basta. Los 33 atrasos satisfacen el minimo orientativo de 30, no suficiencia para validar personas reales ni intervalos independientes.")
    fig, ax = plt.subplots(figsize=(5, 2.7))
    matrix = summary["models"]["tree"]["raw"]["final"]["confusion_matrix"]
    ax.imshow(matrix, cmap="Blues")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(matrix[i][j]), ha="center", va="center", color="white" if matrix[i][j] > 100 else "black")
    ax.set(xticks=[0, 1], yticks=[0, 1], xlabel="Predicho", ylabel="Real")
    fig.tight_layout()
    fig.savefig(out / "figuras/matriz-v6.png", dpi=160)
    plt.close(fig)
    queue_rows = []
    for family, label in zip(FAMILIES, LABELS, strict=True):
        item = summary["models"][family]["policy"]["final"]
        queue_rows.append([label, "final", *[item[k] for k in ("reviews", "reviews_known", "reviews_unknown", "daily_max", "days_over_before_cap", "minutes_hypothetical")], " / ".join(str(v) for row in item["metrics"]["confusion_matrix"] for v in row)])
    queue_table = table(["Modelo COLA", "Particion", "Total", "Conocidas", "Sin etiqueta", "Max/dia", "Dias sobre antes", "Min supuestos", "TN/FP/FN/TP"], queue_rows)
    page("## 4.2. Politica operativa y comparacion con revisar todo\n\nPrimero umbral, luego score descendente e ID ficticio como desempate, maximo cinco por replica y fecha civil Lima. Dos minutos por caso y capacidad cinco/dia son estimaciones, no tiempos observados. La cola cubre fiados otorgados simulados, no toda solicitud, cobranza o trabajo obligatorio.\n\n" + metric_table(summary, "policy", ("final",)) + "\n\n" + queue_table + "\n\nEl arbol genera 193 revisiones: 191 conocidas y dos desconocidas. Dummy constante produce 277: 273 conocidas y cuatro desconocidas. Son **84 revisiones menos y 168 minutos hipoteticos**, no ahorro demostrado. Los FN pasan de cero con Dummy limitado a cuatro con arbol; los FP bajan de 240 a 162. Dummy RAW tiene F2 0.40441176, mientras su politica limitada tiene 0.40740741: no se confunden denominadores ni decisiones.\n\nLa politica del arbol supera descriptivamente ambas referencias en F2 y respeta capacidad, pero revisar tanto con precision baja puede ser inviable para el usuario. La utilidad no esta validada ni el costo de omitir cuatro atrasos acordado. Las colas OOF se separan por pliegue, replica y dia; no representan competencia conjunta de todos los casos bajo un solo modelo desplegado.")
    errors = sorted(report["models"]["tree"]["error_cases"], key=lambda r: r["loan_id"])[:3]
    dump(data / "tres-errores-cache-v6.json", errors)
    error_table = table(["Caso", "Real/predicho/review", "Score", "Hipotesis, no causalidad"], [
        [e["loan_id"], f'{e["actual"]}/{e["predicted"]}/{e["review"]}', fmt(e["probability"]), h]
        for e, h in zip(errors, ["Tres pagos previos tardios no impiden un pago puntual nuevo", "Poco historial pese a puntualidad: hoja amplia y umbral bajo", "Historia mixta no determina desenlace; alerta sin atraso"], strict=True)])
    feature_errors = table(["Entrada", *[e["loan_id"] for e in errors]], [[f, *[f'{e["features"][f]:.8g}' for e in errors]] for f in features])
    page("## 4.3. Tres errores del cache, sin segunda prediccion\n\nSe muestran los primeros tres errores ordenados por loan_id del reporte congelado, no casos elegidos por conveniencia. Son FP RAW y de politica.\n\n" + error_table + "\n\n" + feature_errors + "\n\nTodos los valores son ficticios. Las hipotesis explican limitaciones plausibles, no causas demostradas. El score del tercer error coincide con el ejemplo CLI, pero sus once entradas son distintas: igualdad de score de hoja no implica duplicacion del vector. Los cuatro FN totales se conservan en la matriz y no se ocultan por mostrar estos tres FP deterministas.")
    coefficients = report["models"]["svm"]["interpretation"]["standardized_coefficients"]
    page("## 4.4. Interpretacion y accion concreta\n\nEl arbol utiliza `punctuality_rate <= 0.911067` en la raiz. Entre antecedentes menos puntuales separa `tenure_days <= 317.5` y `punctuality_rate <= 0.305556`; para antecedentes puntuales considera antiguedad 196.5 dias, solicitud/80 y pagos previos 4.5. Son cortes aprendidos, no reglas aprobadas del negocio. Anexo C conserva el texto real de las reglas en unidades originales. La clase de hoja por defecto no sustituye el umbral 0.2 aplicado al score.\n\n" + table(["Hallazgo", "Lectura prudente", "Accion propuesta"], [
        ["Puntualidad e historial", "Asociacion dentro del simulador", "Revisar pagos anteriores y corregir registros antes de mostrar alerta"],
        ["Antiguedad y pocos pagos", "Historial limitado no es solvencia ni causalidad", "Mostrar cantidad de evidencia y reservar decision al propietario"],
        ["Solicitud/80", "Cupo 80 es supuesto", "Confirmar monto/cupo real antes de integrar, sin recomendar modificarlo por este estudio"],
        ["Cinco constantes y dos duplicadas", "Sin evidencia de variacion de deuda", "Bloquear pendientes fuera del modelo; no interpretar su importancia"],
    ]) + "\n\nCoeficientes reales de SVM (margen estandarizado, no probabilidades):\n\n" + table(["Variable", "Coeficiente"], [[k, fmt(coefficients[k])] for k in ("punctuality_rate", "paid_late", "tenure_days", "completed_sales", "paid_credits", "requested_ratio")]) + "\n\nPuntualidad tiene coeficiente negativo y paid_late positivo; los duplicados reparten contribucion y las cinco constantes tienen coeficiente cero. No son efectos causales. Para una persona no tecnica: el modelo señala que historial merece mirar primero, pero muchas alertas seran puntuales y algunas tardias se omitiran. No estima perdida definitiva ni autoriza fiar.")
    cli_command = (
        "python APF3_TD_Grupo2_ML_Innovacion.py \\\n"
        "  --predict-artifact-dir experimento \\\n"
        "  --input-json experimento/illustrative_input.json \\\n"
        "  --output-json inferencia-demo-v6-nueva.json"
    )
    # Match the frozen CLI's actual flag names rather than documenting a guessed API.
    runner = root / "codigo/scripts/academic_credit_pending_v6.py"
    sources[str(runner.relative_to(root))] = sha(runner)
    runner_text = runner.read_text()
    assert '"input-json"' in runner_text and '"output-json"' in runner_text
    page(
        "# 5. Integracion con el MVP\n\n## Contrato y reglas previas al modelo V6\n\n"
        "Flujo: once campos ficticios > validacion > reglas del propietario > Pipeline exportado, "
        "solo si es elegible > score/umbral > candidato a REVIEW. CLI y laboratorio web V6 "
        "autenticado aplican las mismas reglas, sin modificar el experimento congelado.\n\n"
        "**Saldo pendiente:** cualquier saldo positivo, vigente o vencido, bloquea con "
        "`decision=blocked_pending_balance`. Abono o acuerdo no bastan. **Sin fiados pagados:** "
        "`decision=requires_owner_review`; exige revision del propietario. Si falta confirmar "
        "deuda cero o historial, tambien se deriva a revision. En ambos estados "
        "`model_called=false`, probabilidad, umbral y prediccion son nulos. La deuda tiene prioridad.\n\n"
        "Solo deuda cero confirmada e historial pagado permiten consultar el arbol. Ninguna "
        "salida aprueba creditos, asigna cupo ni garantiza pago. La web ofrece tres ejemplos "
        "cerrados: `illustrative-v6`, `pending-balance-v6` y `no-history-v6`, sin entradas libres.\n\n"
        "Ejemplo elegible S/20 sobre cupo S/80, sin PII ni etiqueta conocida:\n\n```json\n"
        + json.dumps({"features": summary["illustrative_inference"]["features"]}, ensure_ascii=False, separators=(",", ":"))
        + "\n```\n\nComando desde la raiz con dependencias preparadas; no entrena:\n\n```bash\n"
        + cli_command + "\n```\n\nSalida elegible sin cambios: tree, score `0.7171978005286032`, "
        "umbral `0.2`, predicted=1, research_only=true, business_approval=false. Es candidato a "
        "REVIEW, no aprobacion ni DEFAULT real. La cola diaria no se aplica a una solicitud aislada.\n\n"
        "La prueba CLI acredita ambos bloqueos sin directorio de artefactos: no puede cargar "
        "modelo. El ejemplo elegible conserva su salida exacta. La reproduccion historica "
        "mantiene 47 archivos deterministas, 12 RAW y 12 politicas exactas y cinco Joblib "
        "binariamente iguales. Estas reglas son una capa previa, no un nuevo entrenamiento "
        "ni una reevaluacion de FINAL; las metricas publicadas pertenecen al experimento original.\n\n"
        "La demo en `/laboratorio-academico/v6` no crea creditos. El primer fiado transaccional "
        "requiere excepcion administrativa justificada y auditada; el laboratorio solo muestra "
        "la derivacion humana. Para PROY faltan adaptador transaccional V6, cola compartida y "
        "validacion con datos reales. Esta exportacion no modifica produccion."
    )
    sections[-1] += (
        f"\n\n**Viabilidad medida V6 (Anexo G).** Docker + CLI: {cli['docker_start_and_cli_seconds']:.6f} s. "
        f"Prediccion local con verificacion de hashes y deserializacion: primera {latency['first_predict_ms']:.3f} ms; "
        f"30 llamadas calientes, mediana {latency['warm_ms']['median']:.3f} ms, p95 {latency['warm_ms']['p95_nearest_rank']:.3f} ms "
        f"y maximo {latency['warm_ms']['max']:.3f} ms. RSS pico {latency['peak_process_rss_kib']} KiB "
        f"({rss_mib:.2f} MiB) en contenedor limitado a 256 MiB: diferencia nominal {nominal_margin_mib:.2f} MiB, "
        "margen estrecho que no equivale a memoria libre del contenedor. Solo este caso en venv limpio; "
        "no se midieron HTTP, concurrencia ni SLA, ni se certifica produccion."
    )
    normative = table(["Requisito de la norma", "Decision/control", "Evidencia y limite"], [
        ["Ley 29733: finalidad y proporcionalidad", "Solo once variables transaccionales; IDs fuera del modelo", "codigo/scripts/academic_credit_pending_v6.py; experimento/protocol.json feature_policy"],
        ["Ley 29733: minimizacion y proteccion", "CSV 100 % simulado; fuente de revision sanitizada; no Word ni firmas", "datos/desarrollo.csv origen; anexos/normativa-ia/revision-propietario-sanitizada-v6.json"],
        ["Seguridad y trazabilidad", "Hashes, protocolo y reproduccion; cargar solo Joblib confiable", "experimento/artifact_manifest.json; verificacion-reproduccion.json"],
        ["Consentimiento/finalidad antes de clientes reales", "Persistir fecha, alcance y version; pendiente del piloto real", "APF2 Tabla 16/US09; no exigible como nueva autorizacion para filas ficticias"],
        ["Conservacion, ARCO y proveedores", "Definir plazos, borrado y contratos antes de produccion", "Brecha futura; archivar no equivale a borrar; no certificacion legal"],
    ])
    risks = table(["Riesgo", "Prob./impacto", "Responsable propuesto", "Mitigacion"], [
        ["Poca generalizacion; repeticion sintetica", "Alta/Alto", "Cesar Paredes", "Piloto real consentido con desenlaces maduros; nuevo test prospectivo"],
        ["Carga de FP y FN omitidos", "Alta/Alto", "Omara Baylon", "Medir minutos y consecuencias; acordar tolerancia antes de uso real"],
        ["Fallo de integracion o version", "Media/Alto", "Tamara Coveñas", "Versionar adaptador y contrato; conservar fallback y logs"],
        ["Privacidad y revisiones incompletas", "Media/Alto", "Pablo Yman", "Revisar normativa, prompts y trazabilidad; completar revision grupal"],
    ])
    page("# 6. Normativa y proyeccion a PROY\n\nSe mantiene el marco de APF1/APF2: Ley N.° 29733 y D.S. N.° 016-2024-JUS. Es herencia documental, no nueva consulta de vigencia legal ni certificacion integral. La autorizacion del propietario para revisar ejemplos no equivale a consentimiento de clientes reales.\n\n" + normative + "\n\n## Riesgos y plan propuesto\n\n" + risks + "\n\nProbabilidades y responsables son propuesta de seguimiento, no tareas ya aceptadas. PROY: integrar snapshot y cola REVIEW, ensayar con usuario, completar controles legales antes de clientes reales y medir un piloto autorizado. Reentrenar solo con nuevo protocolo, desenlaces suficientes y test no consultado; nunca retocar este FINAL.")
    page("""# 7. Conclusiones

V6 aporta una cadena ejecutable y reproducida desde el contrato de datos hasta un modelo exportado y una llamada CLI real. Se compararon dos modelos de Unidad 3 y dos referencias triviales bajo un procedimiento congelado. El arbol seleccionado por desarrollo supera ambas referencias en F2 de politica FINAL y respeta la capacidad supuesta. SVM obtiene mejor F2 en FINAL, sin alterar la seleccion previa.

El beneficio tecnico es disponer de evidencia y priorizacion reproducible, no de un sistema crediticio validado. Detectar 29 de 33 atrasos cuesta 162 falsas alertas conocidas y cuatro omisiones. Frente a Dummy limitado se reducen 84 revisiones, pero los 168 minutos asociados son hipoteticos. El alto burden de alertas y su precision baja impiden concluir utilidad empresarial aprobada.

La regla de no fiar con cualquier saldo pendiente esta reflejada en los datos; las cinco variables de pendiente constantes y la duplicacion ventas/pagos limitan el aprendizaje. No se inventaron variaciones ni se imputaron targets inmaduros. Los 33 casos minoritarios finales cumplen el minimo orientativo, sin convertir transacciones repetidas en personas independientes. Los hard pass no cambian `coherence_accepted=false`.

**Meta de negocio propuesta para piloto, no aprobada:** medir ANTES minutos de revisar todos los casos elegibles y DESPUES minutos de la politica en periodos comparables; exigir menos tiempo, maximo cinco alertas/dia y registrar FN/FP con desenlaces maduros y sus consecuencias. No hay costos acordados ni referencia cronometrada; el exito tecnico no demuestra mejora de cobertura real ni reduccion de la perdida mensual del APF1.

Rildo se muestra dispuesto a autorizar Credify solo como herramienta de apoyo, bajo su revision y conservando la decision final. La autorizacion es prospectiva y condicionada a mas pruebas y confiabilidad comprobada. No autoriza produccion inmediata, decisiones automaticas ni sustituye la revision grupal, la revision de PROY ni un piloto autorizado.

El siguiente paso para PROY es conectar V6 al flujo transaccional, completar la gobernanza para datos reales y medir utilidad prospectiva. CLI y laboratorio web sintetico aplican los controles previos de saldo pendiente e historial pagado; esto no valida el modelo ni autoriza produccion. La revision final de los cuatro integrantes permanece pendiente.
""")
    assert len(sections) == 16, len(sections)
    page("""# Referencias

Anderson, D. J. (2010). *Kanban: Successful evolutionary change for your technology business*. Blue Hole Press.

Congreso de la Republica del Peru. (2011). *Ley N.° 29733, Ley de Proteccion de Datos Personales*. Diario Oficial El Peruano.

Grupo 2. (2026). *Propuesta metodologica de innovacion y hoja de ruta agil para la MiPYME: MVP de la aplicacion Credify para el fiado a un dia en Cerveceria Baylon* [Informe APF2, Universidad Tecnologica del Peru]. Tabla 17 y Anexo B.4.

Ministerio de Justicia y Derechos Humanos. (2024). *Decreto Supremo N.° 016-2024-JUS, que aprueba el Reglamento de la Ley N.° 29733*. https://www.gob.pe/institucion/anpd/normas-legales/6554453-16-2024-jus

Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D., Brucher, M., Perrot, M., & Duchesnay, E. (2011). Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research, 12*, 2825-2830. https://jmlr.org/papers/v12/pedregosa11a.html

Ries, E. (2011). *The lean startup: How today's entrepreneurs use continuous innovation to create radically successful businesses*. Crown Business.

Universidad Tecnologica del Peru. (2026). *Consigna APF3: Solucion de Machine Learning para la MiPYME, 2026-2* [Consigna del curso Innovacion y Transformacion Digital].

Documentacion tecnica: scikit-learn, Pipeline y validacion agrupada, https://scikit-learn.org/stable/modules/cross_validation.html; Joblib, persistencia de objetos confiables, https://joblib.readthedocs.io/en/stable/persistence.html. Fuentes documentales; no se declara consulta web fresca ni evidencia sectorial no aportada.
""")
    for start in range(0, 24, 6):
        page(f"# Anexo A. Diccionario completo ({start + 1}-{start + 6}/24)\n\nUnidad de observacion: fiado otorgado con snapshot anterior. Rango observado: solo DEV conocido (541). Nulos de features: mediana ajustada solo en entrenamiento; target desconocido nunca se imputa.\n\n" + table(["Variable / tipo / unidad", "Descripcion y rango valido", "Observado DEV"], [[f'{r[0]} / {r[1]} / {r[2]}', f'{r[3]}. {r[4]}', r[6]] for r in dictionary[start:start + 6]]) + "\n\nDominio de inferencia V6: elegible sin saldo previo, cinco variables pendientes cero y ventas de credito iguales a paid_credits. Un pendiente positivo debe bloquearse por regla antes del modelo, no extrapolar su score. El CSV guarda numeros integrales como float; el tipo semantico es conteo entero. Campos no predictores se usan solo para trazabilidad.")
    page("# Anexo B. Auditoria DEV y precision de montos\n\n" + table(["Variable", "Cerca inferior", "Cerca superior", "Fuera IQR", "Decision"], [[f, f'{v["lower"]:.4f}', f'{v["upper"]:.4f}', v["outliers"], "Retener"] for f, v in quality["iqr"].items()]) + "\n\nConteos de precision sobre **todas las filas de estudio DEV**, incluidos desconocidos, excluido calentamiento:\n\n" + table(["Historia", "Estudio", "Entero/.50", "Otros centimos exactos"], [[k, v["study"], v["whole_or_half"], v["other_exact_cents"]] for k, v in quality["amount_precision_study"].items()]) + "\n\nNo confundir con amount_precision_counts de la auditoria transaccional, que incluye warmup. El JSON propio `anexos/datos/auditoria-calidad-dev-v6.json` conserva nulos por cada columna, duplicados por ID/vector y cercas IQR. Los extremos no se eliminan por ser estadisticamente raros. La validez de reglas no demuestra representatividad global.")
    rules = report["models"]["tree"]["interpretation"]["raw_unit_rules"]
    page("# Anexo C. Reglas reales exportadas\n\nUnidades originales despues de imputacion mediana de entrenamiento; no causalidad. Estas clases de hoja no sustituyen clasificacion por score >=0.2.\n\n```text\n" + rules + "```\n\nFuente: experimento/pending_v6_report.json, models.tree.interpretation. No se cargo Joblib para extraerlas ni se ejecuto segunda inferencia. SVM describe margen estandarizado; intercepto " + fmt(report["models"]["svm"]["interpretation"]["intercept"]) + ".")
    page("# Anexo D. Reproduccion, trazabilidad y ambiente\n\n" + table(["Control guardado", "Resultado"], [
        ["verificacion-reproduccion.json passed", str(repro["passed"])],
        ["Archivos deterministas SHA exactos", len(repro["checks"]["exact_file_sha256"])],
        ["Comparaciones RAW / politica", f'{len(repro["checks"]["raw"])}/{len(repro["checks"]["policy"])}'],
        ["Cinco Joblib binarios / estados", "Iguales / iguales"],
        ["Ejemplo distinto y CLI original/reproduccion", "Exactos, sin etiqueta conocida"],
        ["Control negativo de metricas en reproduccion", str(repro["checks"]["negative_metric_control"])],
    ]) + "\n\n" + table(["Fuente congelada", "SHA-256"], [[k, report["provenance"]["input_sha256"][k]] for k in ("protocol.json", "data_protocol.json", "owner_review.json")]) + "\n\nEl protocolo de modelado eb7f... es posterior al protocolo de datos 5f3c... y anterior al entrenamiento/final; no reescribe su autorizacion historica. La revision sanitizada a72e... referencia Word privado 82d4...: no se entrega el original ni firmas.\n\nRuntime experimental: Python 3.12.14, sklearn 1.9.1, numpy 2.5.3, scipy 1.18.1, joblib 1.6.0 y threadpoolctl 3.7.0. Requirements y entorno limpio estan en la raiz; entorno de exportacion documental es separado. Reproduccion es replay fijo, no nueva prueba independiente.")
    page("# Anexo E. Prompts y asistencia de IA\n\nHerramienta: OpenCode. Modelo de esta asistencia: `openai/gpt-6.1-sol`. Apoyo declarado en codigo, preparacion/auditoria de datos simulados, modelado, depuracion, metricas, redaccion y exportacion documental. Los artefactos congelados, no el texto generado, son fuente de cifras.\n\nPrompts literales visibles transmitidos en el contexto del usuario, sin inventar fechas ni historial completo:\n\n" + table(["Texto literal", "Procedencia y alcance"], [
        ["ya hazlo todo correctamente", "Literal exigido por el usuario en el contexto actual; no acredita revision humana completada"],
        ["ya haz el siguiente paso", "Contexto previo proporcionado por el usuario; sin fecha disponible"],
        ["que sigue?", "Contexto previo proporcionado por el usuario; sin fecha disponible"],
        ["IMPLEMENTA y EJECUTA nuevo informeV6 contra consigna ORIGINAL", "Extracto literal inicial del encargo actual; restricciones completas aplicadas al generador"],
        ["Rerenderregenerate ownreport docs+outputsconarchivo read cached no predictcalls.", "Extracto literal del encargo de actualizacion: leer evidencia CLI/latencia, sin nuevas predicciones ni cambios del protocolo congelado"],
    ]) + "\n\nVerificacion tecnica aplicada: cotejo de JSON completo y resumen, tablas RAW/politica/colas a precision impresa, control negativo con metrica alterada, integridad de fuentes y exportacion offline A4. Estas comprobaciones automatizadas **no son validacion humana**. La reproduccion preexistente acredita codigo/artefactos; este proceso no entreno ni predijo.\n\n" + table(["Integrante", "Revision propuesta", "Validacion humana V6"], [
        ["Omara Baylon", "Fuente propietaria, problema y utilidad", "PENDIENTE"], ["Tamara Coveñas", "Codigo, integracion y reproduccion", "PENDIENTE"],
        ["Cesar Paredes", "Datos, limpieza y metricas", "PENDIENTE"], ["Pablo Yman", "Consigna, normativa y prompts", "PENDIENTE"],
    ]) + "\n\nCada persona debe contrastar las fuentes y registrar correcciones reales antes de afirmar validacion final. No se reutiliza como aprobacion V6 la constancia historica APF2 ni la revision muestral V5 de Rildo.")
    page("# Anexo F. Matriz normativa y continuidad de controles\n\n" + normative + "\n\nLa finalidad actual es investigacion academica sobre transacciones ficticias. No se solicita nuevo consentimiento de clientes para inventar ejemplos academicos ni se declara captacion real. Para un piloto personal real quedan pendientes aviso de privacidad, constancia versionada, retencion/eliminacion, atencion ARCO y condiciones de proveedores. No basta omitir DNI para garantizar anonimato de datos reales.\n\nControles heredados del MVP: autenticacion/roles, hash Argon2, HTTPS y separacion de demo/produccion constan en APF2. No se presentan como nuevas pruebas de este generador ni como endpoint V6. La evidencia ejecutable entregada de V6 esta en codigo/scripts y experimento; el informe no necesita GitHub ni publicacion.\n\nEl Word de revision y los PDF con firmas permanecen privados. Se entrega solo revision estructurada sanitizada con reglas y agregados; su hash permite rastrear la fuente sin divulgar firmas ni identidades de clientes.")
    integration_rows = [
        ["Docker + CLI raiz", f"{cli['docker_start_and_cli_seconds']:.6f}", "s"],
        ["Primera prediccion local", f"{latency['first_predict_ms']:.3f}", "ms"],
        ["Llamadas calientes", str(latency["warm_calls"]), "llamadas"],
        ["Mediana caliente", f"{latency['warm_ms']['median']:.3f}", "ms"],
        ["p95 caliente (nearest rank)", f"{latency['warm_ms']['p95_nearest_rank']:.3f}", "ms"],
        ["Maximo caliente", f"{latency['warm_ms']['max']:.3f}", "ms"],
        ["RSS pico del proceso", str(latency["peak_process_rss_kib"]), "KiB"],
        ["RSS convertido", f"{rss_mib:.2f}", "MiB"],
        ["Limite del contenedor", "256", "MiB"],
        ["Diferencia nominal limite - RSS", f"{nominal_margin_mib:.2f}", "MiB"],
    ]
    integration_table = table(["Medicion V6", "Valor", "Unidad"], integration_rows)
    page("# Anexo G. Integracion y viabilidad V6 ejecutadas\n\nFuentes: `anexos/integracion/prueba-cli-v6.json` y `anexos/integracion/latency-v6.json`, ambas passed=true. La CLI elegible devuelve p=0.7171978005286032, umbral=0.2 y predicted=1. Ejemplo ficticio, candidato a REVIEW, no aprobacion.\n\n" + integration_table
         + "\n\nLa prediccion local incluye integridad/hash chain, deserializacion y un vector ilustrativo; no es solo el recorrido del arbol. Docker + CLI incluye arranque. El registro conserva 30 muestras y p95 nearest rank, sin red, contenedor read-only de 256m y venv congelado.\n\n"
         "El RSS pico se convierte con 1024 KiB/MiB. Su margen nominal frente a 256 MiB es estrecho y no mide memoria libre ni pico total del contenedor. Solo acredita este caso; no certifica capacidad, margen seguro ni concurrencia. El benchmark no mide HTTP, autenticacion, DB, navegador, carga sostenida ni SLA. Ensayo humano pendiente.\n\n"
         "Ambas reglas previas pasan sin directorio de artefactos: `model_called=false`, sin probabilidad ni prediccion. Instrucciones y ejemplos: `anexos/revision/REGLAS_PREVIAS_V6.md`. El registro separado `anexos/integracion/despliegue-reglas-v6.json` conserva las pruebas publicas y la incidencia de recuperacion del despliegue; no es un benchmark ni validacion predictiva.\n\nHashes SHA-256 de los registros leidos:\n\n"
         + table(["Registro", "SHA-256"], [[path, sources[path]] for path, _ in integration_loaded])
         + "\n\nLa exportacion solo lee evidencia: no reejecuta prediccion ni benchmark, no entrena ni modifica protocolo, modelo o FINAL.")
    page("# Anexo H. Metricas RAW completas\n\nMisma precision que las tablas del cuerpo; train y OOF n=541, FINAL n=276.\n\n" + metric_table(summary, "raw", ("train", "oof", "final")))
    page("# Anexo H. Metricas de politica completas\n\nAcciones despues del tope; desconocidos compiten en cola pero no en metricas.\n\n" + metric_table(summary, "policy", ("train", "oof", "final")))
    for split in ("train", "oof", "final"):
        rows = []
        for family, label in zip(FAMILIES, LABELS, strict=True):
            item = summary["models"][family]["policy"][split]
            rows.append([label, split, *[item[k] for k in ("reviews", "reviews_known", "reviews_unknown", "daily_max", "days_over_before_cap", "minutes_hypothetical")], " / ".join(str(v) for row in item["metrics"]["confusion_matrix"] for v in row)])
        page("# Anexo H. Conteos de cola: " + split + "\n\n" + table(["Modelo COLA", "Particion", "Total", "Conocidas", "Sin etiqueta", "Max/dia", "Dias sobre antes", "Min supuestos", "TN/FP/FN/TP"], rows) + "\n\nTrain es desempeño de reajuste; OOF separa por pliegue, replica y dia; FINAL por replica y dia. Las historias alternativas no se suman como volumen empresarial. Dos minutos por caso y cinco por dia son supuestos, no ahorro medido.")
    page("# Anexo I. Conteos de consistencia reconstruidos\n\nSolo DEV conocido de estudio, n=541. No se usa FINAL para elegir reglas ni hacer EDA de desenlaces.\n\n" + table(["Control ejecutado", "Violaciones"], [[k, v] for k, v in quality["row_rule_violations"].items()]) + "\n\nEstos conteos complementan los hard pass transaccionales guardados y la ficha de siete criterios; no constituyen aceptacion global por el propietario. La coherencia con APF2 requiere leer los cambios de fuente y alcance de ventas, no solo aprobar reglas numericas.")
    text = "\n\n<!-- PAGE -->\n\n".join(sections) + "\n"
    printed_integration = next(block for block in text.split("\n\n") if block.startswith("| Medicion V6 |"))
    parsed_integration = [[c.strip() for c in line.strip("|").split("|")] for line in printed_integration.splitlines()[2:]]
    assert parsed_integration == integration_rows
    count = verify_metric_tables(text, summary)
    changed = copy.deepcopy(summary)
    changed["models"]["tree"]["raw"]["final"]["f2"] += 0.01
    try:
        verify_metric_tables(text, changed)
    except AssertionError:
        negative = True
    else:
        raise AssertionError("Altered metric was not detected")
    source_md = REPO / "docs/APF3_TD_Grupo2_ML_Innovacion_V6.md"
    source_md.write_text(text)
    (out / (NAME + ".md")).write_text(text)
    (legal / "normativa-y-prompts-v6.md").write_text("\n\n".join(p for p in sections if p.startswith(("# Anexo E.", "# Anexo F."))) + "\n")
    document_check = HELPER.documents(text, out, name=NAME, expected_figures=3)
    doc = Document(out / (NAME + ".docx"))
    doc.core_properties.title = "APF3 Credify V6: estudio sintetico"
    doc.sections[0].footer.paragraphs[0].text = "Datos simulados | Grupo 2 | V6"
    doc.save(out / (NAME + ".docx"))
    markdown_tables = []
    for block in text.split("\n\n"):
        if block.startswith("|"):
            lines = block.splitlines()
            markdown_tables.append([[c.strip() for c in line.strip("|").split("|")] for line in [lines[0], *lines[2:]]])
    native_tables = [[[c.text for c in row.cells] for row in t.rows] for t in doc.tables]
    assert native_tables == markdown_tables
    html_path = out / (NAME + ".html")
    html_path.write_text(html_path.read_text().replace("<title>APF3 - Credify - Borrador</title>", "<title>APF3 Credify V6</title>"))
    js = r"""
import {readFile} from 'node:fs/promises';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE_PATH);
const browser=await chromium.launch();
try {
 const page=await browser.newPage({viewport:{width:658,height:1120}});
 await page.route('**/*',route=>route.abort());
 await page.setContent(await readFile(process.argv[1],'utf8'));
 await page.emulateMedia({media:'print'});
 await page.evaluate(()=>document.fonts.ready);
 await page.evaluate(()=>Promise.all([...document.images].map(i=>i.decode())));
 const checks=await page.locator('.page').evaluateAll(es=>es.map(e=>{
  const box=e.getBoundingClientRect();
  const walker=document.createTreeWalker(e,NodeFilter.SHOW_TEXT); let node; const overflow=[];
  while((node=walker.nextNode())) {if(!node.textContent.trim())continue;
   const range=document.createRange();range.selectNodeContents(node);
   for(const r of range.getClientRects())if(r.left<box.left-1||r.right>box.right+1)overflow.push(node.textContent.slice(0,80));
  }
  return {title:e.querySelector('h1,h2')?.textContent,height:box.height,width:box.width,text_overflow:overflow};
 }));
 await page.pdf({path:process.argv[2],preferCSSPageSize:true,printBackground:true,
 displayHeaderFooter:true,headerTemplate:'<div></div>',
 footerTemplate:'<div style="font:8px Arial;width:100%;text-align:center">Datos simulados | Grupo 2 | <span class="pageNumber"></span> / <span class="totalPages"></span></div>'});
 console.log(JSON.stringify(checks));
} finally {await browser.close();}
"""
    env = os.environ.copy()
    env.setdefault("PLAYWRIGHT_MODULE_PATH", "/var/folders/sx/_6ljw37n2_j9hk2f_vtqplj40000gn/T/opencode/apf3-render/node_modules/playwright/index.mjs")
    result = subprocess.run(["node", "--input-type=module", "-e", js, str(html_path), str(out / (NAME + ".pdf"))], env=env, capture_output=True, text=True, check=True)
    layout = json.loads(result.stdout)
    pdf = PdfReader(out / (NAME + ".pdf"))
    pdf_text = [p.extract_text() for p in pdf.pages]
    normalized_pdf = re.sub(r"\s+", "", "".join(pdf_text))
    printed_cells = 0
    for rows in markdown_tables:
        for row in rows:
            for cell in row:
                normalized_cell = re.sub(r"\s+", "", cell.replace("`", "").replace("*", ""))
                assert normalized_cell in normalized_pdf, cell
                printed_cells += 1
    ref = next(i for i, t in enumerate(pdf_text) if t.startswith("Referencias"))
    verification = {
        "edition_utc": edition, "experiment_recorded_utc": report["provenance"]["recorded_utc"],
        "body_pages": ref - 1, "total_pages": len(pdf.pages), "planned_pages": len(sections),
        "tables_metric_cells_checked": count, "negative_control_metric_detected": negative,
        "all_native_tables_equal_markdown": True, "all_pdf_table_cells_present": printed_cells,
        "documents": document_check, "layout": layout,
        "integration_sources_loaded": [p for p, _ in integration_loaded],
        "integration_measurement_cells_checked": sum(len(row) for row in parsed_integration),
        "integration_sources_unchanged": all(sha(root / path) == sources[path] for path, _ in integration_loaded),
        "source_read_sha256": sources, "fit_calls": 0, "predict_calls": 0, "dataset_generation_calls": 0,
        "human_validation": "PENDIENTE: cuatro integrantes", "private_word_copied": False,
        "experiment_unchanged": before == {str(p.relative_to(root)): sha(p) for p in (root / "experimento").iterdir() if p.is_file()},
    }
    verification["passed"] = (verification["body_pages"] <= 15 and len(pdf.pages) == len(sections)
        and all(x["height"] <= 980 and not x["text_overflow"] for x in layout)
        and verification["experiment_unchanged"] and verification["integration_sources_unchanged"])
    dump(out / "verificacion-informe-v6.json", verification)
    manifest_files = [p for folder in (out, data, legal) for p in folder.rglob("*") if p.is_file() and p.name != "manifest-informe-v6.json"]
    dump(out / "manifest-informe-v6.json", {"edition_utc": edition, "source_read_sha256": sources,
        "source_markdown_sha256": sha(source_md), "files": {str(p.relative_to(root)): sha(p) for p in manifest_files}})
    assert verification["passed"], json.dumps({"body": ref - 1, "actual": len(pdf.pages), "planned": len(sections), "overflow": [x for x in layout if x["height"] > 980 or x["text_overflow"]]}, ensure_ascii=False)
    print(json.dumps({"passed": True, "body_pages": ref - 1, "total_pages": len(pdf.pages), "metric_cells": count, "files": len(manifest_files) + 1, "integration_sources": verification["integration_sources_loaded"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.home() / "Downloads/APF3_Grupo2_Entrega_V6")
    parser.add_argument("--consigna", type=Path, default=Path.home() / "Downloads/Innovacion_TD_Consigna_APF3.pdf")
    parser.add_argument("--apf2", type=Path, default=Path.home() / "Downloads/APF2_TD_Grupo2_MVP_Innovación.pdf")
    args = parser.parse_args()
    generate(args.root, args.consigna, args.apf2)
