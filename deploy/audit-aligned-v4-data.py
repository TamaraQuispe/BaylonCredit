"""Post hoc descriptive DEV audit. No models, generation, selection or FINAL EDA.

The two relationships below are fixed before analysis, not selected by effect.
Only FINAL CSV schema/count/unknown accounting is read, never its distributions.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import itertools
import json
import math
import shutil
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path

import numpy as np

RELATIONSHIPS = (
    "paid_late == 0 versus paid_late > 0; outcome late_payment, resolved DEV only",
    "tenure_days versus completed_sales; fixed bands 30..119, 120..239, >=240",
)
EXPECTATION = "Mayor exposicion temporal al calendario puede acumular mas operaciones."
BANDS = (("30..119", 30, 120), ("120..239", 120, 240), (">=240", 240, math.inf))
CONSIGNA_CRITERIA = (
    "Escala del negocio",
    "Rangos/unidades",
    "Consistencia l\u00f3gica/temporal",
    "Relaciones plausibles",
    "Se\u00f1al ni nula ni perfecta",
    "Coherencia con APF2",
    "Mezcla real+simulado",
)
REPO = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path("/Users/tamaraalison/Downloads/APF3_Grupo2_Alineado_V4")
DEFAULT_ROOT = Path("/Users/tamaraalison/Downloads/APF3_Grupo2_Entrega_V4")


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def require(value, message):
    if not value:
        raise ValueError(message)


def csv_scope(path):
    # FINAL is intentionally reduced to schema and accounting, not numeric EDA.
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        header = reader.fieldnames
        n = unknown = 0
        for row in reader:
            require(
                set(row) == set(header) and None not in row.values(), "Malformed CSV"
            )
            require(
                row["phase"] == "study" and row["origen"] == "simulado",
                "CSV scope drift",
            )
            require(row["late_payment"] in ("", "0", "1"), "Invalid CSV target")
            n += 1
            unknown += row["late_payment"] == ""
    return {"header": header, "study": n, "unknown": unknown, "known": n - unknown}


def feature_names(path):
    # Read the contract without importing SQLAlchemy, services or ML modules.
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "FEATURE_NAMES"
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise ValueError("FEATURE_NAMES contract missing")


def dictionary(header, features, simulation):
    counts = {
        "completed_sales": "Ventas de credito previas observadas; V4 no inventa ventas al contado",
        "paid_credits": "Creditos previos totalmente pagados al evaluar",
        "paid_late": "Creditos previos pagados con algun pago posterior al vencimiento",
        "pending_overdue": "Creditos previos con saldo y vencimiento anterior al dia evaluado",
        "pending_current": "Creditos previos con saldo y vencimiento no anterior al dia evaluado",
    }
    specs = {
        name: (
            "float64 integral",
            "operaciones",
            "MVP >=0; V4 >=0; limite por eventos previos; paid_late <= paid_credits",
            desc,
        )
        for name, desc in counts.items()
    }
    specs.update(
        {
            "outstanding": (
                "float64",
                "PEN",
                "MVP >=0; V4 0..75 y outstanding + requested_amount <=80",
                "Saldo de creditos previos al evaluar",
            ),
            "utilization": (
                "float64",
                "proporcion",
                "MVP >=0, puede >1; V4 0..0.9375",
                "outstanding / credit_cap; MVP cap=0 devuelve 0, no observado V4",
            ),
            "requested_ratio": (
                "float64",
                "proporcion",
                "MVP >=0, puede >1; V4 0.0625..0.625",
                "requested_amount / credit_cap; MVP cap=0 devuelve 1, no observado V4",
            ),
            "tenure_days": (
                "float64 integral",
                "dias civiles",
                "MVP >=0; V4 fecha evaluacion - registro; edad inicial 0..180, mas calendario transcurrido",
                "Dias desde registro; no equivale a dias de historia observada",
            ),
            "punctuality_rate": (
                "float64",
                "proporcion",
                "0..1",
                "(paid_credits - paid_late) / paid_credits; sin pagados =0 por convencion, no puntualidad observada",
            ),
            "overdue_rate": (
                "float64",
                "proporcion",
                "0..1",
                "pending_overdue / (pending_current + pending_overdue); sin activos =0 por convencion",
            ),
            "late_payment": (
                "int nullable",
                "clase",
                "0, 1 o vacio",
                "0 pagado a tiempo; 1 pago tardio o saldo vencido al corte; desconocido sin resolucion al corte",
            ),
            "origen": (
                "string",
                "categoria",
                "simulado",
                "Procedencia sintetica, nunca cliente real",
            ),
            "loan_id": (
                "string",
                "identificador",
                "unico por prestamo; prefijo replica",
                "Identificador ficticio del prestamo evaluado",
            ),
            "client_id": (
                "string",
                "identificador",
                "12 clientes por replica; se repite en prestamos",
                "Grupo de dependencia; no predictor",
            ),
            "replica_id": (
                "string",
                "identificador",
                "DEV AL4-D1/AL4-D2; FINAL AL4-T",
                "Historia alternativa, no sucursal simultanea",
            ),
            "phase": (
                "string",
                "categoria",
                "study en ambos CSV; warmup solo transacciones",
                "Fase de calendario",
            ),
            "evaluated_at": (
                "ISO datetime",
                "hora civil America/Lima",
                f"{simulation['study_start']}..{simulation['observed_on']}",
                "Instante anterior al nuevo credito; snapshot sin futuro",
            ),
            "due_date": (
                "ISO date",
                "dia civil",
                "evaluated_at.date + 1 dia",
                "Vencimiento contractual; gracia no cambia etiqueta",
            ),
            "observed_on": (
                "ISO date",
                "dia civil",
                simulation["observed_on"],
                "Corte de observacion",
            ),
            "requested_amount": (
                "decimal string JSON / decimal CSV",
                "PEN",
                "5..50; <=80-outstanding; dos decimales",
                "Importe concedido; metadato, representado en predictor requested_ratio",
            ),
            "credit_cap": (
                "decimal string JSON / decimal CSV",
                "PEN",
                "80.00",
                "Tope por cliente; denominador de ratios",
            ),
            "pending_at_cutoff": (
                "decimal string JSON / decimal CSV",
                "PEN",
                "0..requested_amount",
                "Saldo al corte, posterior a evaluar; PROHIBIDO como predictor",
            ),
            "scenario": (
                "string",
                "categoria",
                "on_time, late, unresolved y variantes partial_",
                "Desenlace observado al corte, no plan; PROHIBIDO como predictor",
            ),
        }
    )
    require(
        set(header) == set(specs),
        "Dictionary must cover exactly every original CSV column",
    )
    require(set(features) <= set(header), "Feature schema mismatch")
    return [
        {
            "columna": name,
            "rol": "predictor"
            if name in features
            else "target"
            if name == "late_payment"
            else "metadata",
            "tipo": specs[name][0],
            "unidad": specs[name][1],
            "rango_contrato": specs[name][2],
            "politica_nulos": (
                "JSON null / CSV vacio: conservar en CSV; excluir de supervision; no imputar target"
                if name == "late_payment"
                else "No permitido V4; no imputar en esta auditoria"
            ),
            "definicion": specs[name][3],
            "alcance": "datos/desarrollo.csv y datos/final.csv",
        }
        for name in header
    ]


def quality(rows, features, worlds):
    clients = {c["client_id"]: c for w in worlds for c in w["clients"]}
    loans = {
        c["client_id"]: [
            loan
            for w in worlds
            for loan in w["loans"]
            if loan["client_id"] == c["client_id"]
        ]
        for c in clients.values()
    }
    sales = {
        c["client_id"]: [
            s for w in worlds for s in w["sales"] if s["client_id"] == c["client_id"]
        ]
        for c in clients.values()
    }
    expected = {}
    for row in rows:
        at = row["evaluated_at"]
        previous = [loan for loan in loans[row["client_id"]] if loan["evaluated_at"] < at]
        balances = {
            loan["loan_id"]: Decimal(loan["amount"])
            - sum(
                (Decimal(p["amount"]) for p in loan["payments"] if p["at"] <= at),
                Decimal(0),
            )
            for loan in previous
        }
        paid = [loan for loan in previous if balances[loan["loan_id"]] == 0]
        active = [loan for loan in previous if balances[loan["loan_id"]] > 0]
        late = sum(
            any(p["at"] <= at and p["at"][:10] > loan["due_date"] for p in loan["payments"])
            for loan in paid
        )
        overdue = sum(loan["due_date"] < at[:10] for loan in active)
        outstanding = sum((balances[loan["loan_id"]] for loan in active), Decimal(0))
        cap = Decimal(clients[row["client_id"]]["credit_cap"])
        expected[row["loan_id"]] = {
            "completed_sales": sum(s["at"] < at for s in sales[row["client_id"]]),
            "paid_credits": len(paid),
            "paid_late": late,
            "pending_overdue": overdue,
            "pending_current": len(active) - overdue,
            "outstanding": float(outstanding),
            "utilization": float(outstanding / cap),
            "requested_ratio": float(Decimal(row["requested_amount"]) / cap),
            "tenure_days": (
                date.fromisoformat(at[:10])
                - date.fromisoformat(clients[row["client_id"]]["registered_on"])
            ).days,
            "punctuality_rate": (len(paid) - late) / len(paid) if paid else 0,
            "overdue_rate": overdue / len(active) if active else 0,
        }
    stats = {}
    for name in features:
        null = nonfinite = invalid_type = invalid_range = snapshot_mismatch = 0
        finite = []
        for row in rows:
            value = row.get(name)
            if value is None:
                null += 1
                continue
            if type(value) not in (int, float):
                invalid_type += 1
                continue
            if not math.isfinite(value):
                nonfinite += 1
                continue
            finite.append(value)
            at = row["evaluated_at"]
            previous = [
                loan for loan in loans[row["client_id"]] if loan["evaluated_at"] < at
            ]
            prior_sales = sum(s["at"] < at for s in sales[row["client_id"]])
            upper = {
                "completed_sales": prior_sales,
                "paid_credits": len(previous),
                "paid_late": row["paid_credits"],
                "pending_overdue": len(previous),
                "pending_current": len(previous),
                "outstanding": 80 - float(row["requested_amount"]),
                "utilization": (80 - float(row["requested_amount"])) / 80,
                "requested_ratio": 50 / 80,
                "punctuality_rate": 1,
                "overdue_rate": 1,
                "tenure_days": (
                    date.fromisoformat(at[:10])
                    - date.fromisoformat(clients[row["client_id"]]["registered_on"])
                ).days,
            }[name]
            low = 5 / 80 if name == "requested_ratio" else 0
            integral = name in (
                "completed_sales",
                "paid_credits",
                "paid_late",
                "pending_overdue",
                "pending_current",
                "tenure_days",
            )
            integer_ok = not integral or float(value).is_integer()
            invalid_range += not (low <= value <= upper and integer_ok)
            snapshot_mismatch += abs(value - expected[row["loan_id"]][name]) >= 1e-9
        if finite:
            q1, median, q3 = map(
                float, np.quantile(finite, [0.25, 0.5, 0.75], method="linear")
            )
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            description = {
                "n": len(finite),
                "min": min(finite),
                "max": max(finite),
                "mean": float(np.mean(finite)),
                "median": median,
                "q1": q1,
                "q3": q3,
                "iqr": iqr,
                "lower_fence": lower,
                "upper_fence": upper,
                "below_fence": sum(v < lower for v in finite),
                "above_fence": sum(v > upper for v in finite),
            }
        else:
            description = {"n": 0}
        stats[name] = dict(
            null=null,
            nonfinite=nonfinite,
            invalid_type=invalid_type,
            invalid_range=invalid_range,
            snapshot_mismatch=snapshot_mismatch,
            **description,
        )
    ids = Counter(r["loan_id"] for r in rows)
    vectors = Counter(tuple(r[f] for f in features) for r in rows)
    return {
        "n": len(rows),
        "clients": len({r["client_id"] for r in rows}),
        "nulls_by_column": {
            name: sum(r.get(name) is None for r in rows) for name in rows[0]
        },
        "duplicate_loan_ids": {k: n for k, n in ids.items() if n > 1},
        "duplicate_loan_id_excess": sum(n - 1 for n in ids.values()),
        "duplicate_feature_vector_groups": sum(n > 1 for n in vectors.values()),
        "duplicate_feature_vector_rows": sum(n for n in vectors.values() if n > 1),
        "duplicate_feature_vector_excess": sum(n - 1 for n in vectors.values()),
        "features": stats,
        "policy": "IQR 1.5, quantiles lineales; solo descripcion; ninguna exclusion, deduplicacion ni imputacion",
    }


def relationships(rows):
    first = []
    for label, predicate in (
        ("Sin atraso previo", lambda r: r["paid_late"] == 0),
        ("Con atraso previo", lambda r: r["paid_late"] > 0),
    ):
        group = [r for r in rows if predicate(r)]
        late = sum(r["late_payment"] == 1 for r in group)
        first.append(
            {
                "group": label,
                "n": len(group),
                "late": late,
                "rate": late / len(group) if group else None,
                "clients": len({r["client_id"] for r in group}),
            }
        )
    bands = []
    for label, low, high in BANDS:
        group = [r for r in rows if low <= r["tenure_days"] < high]
        values = [r["completed_sales"] for r in group]
        bands.append(
            {
                "band": label,
                "n": len(group),
                "clients": len({r["client_id"] for r in group}),
                "median_sales": float(np.median(values)) if values else None,
                "q1_sales": float(np.quantile(values, 0.25)) if values else None,
                "q3_sales": float(np.quantile(values, 0.75)) if values else None,
            }
        )
    medians = [b["median_sales"] for b in bands]
    monotonic = (
        all(v is not None for v in medians)
        and all(a <= b for a, b in itertools.pairwise(medians))
        and medians[-1] > medians[0]
    )
    return {
        "declared": RELATIONSHIPS,
        "expectation": EXPECTATION,
        "first": first,
        "second": bands,
        "outside_bands": sum(r["tenure_days"] < 30 for r in rows),
        "monotonic_medians": monotonic,
        "conclusion": (
            "Las medianas apoyan la direccion esperada en estas filas sinteticas."
            if monotonic
            else "Las medianas NO muestran la relacion creciente esperada en las tres bandas; no se confirma la segunda hipotesis y no se busca otra favorable."
        ),
        "limits": "Filas repetidas por cliente, bandas con clientes compartidos; no observaciones independientes. Sin p-valores ni causalidad ni validacion predictiva. Antiguedad de registro aleatoria y warmup comun limitan exposicion efectivamente observada; solo ventas de credito. Distribuciones y heterogeneidad latente son supuestos, no mediciones del negocio.",
    }


def figure(path, rows, relation):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), layout="constrained")
    first = relation["first"]
    axes[0].bar(
        [g["group"] for g in first],
        [100 * g["rate"] for g in first],
        color=["#357592", "#b66539"],
    )
    for i, g in enumerate(first):
        axes[0].text(
            i,
            100 * g["rate"] + 0.7,
            f"{g['late']}/{g['n']} = {100 * g['rate']:.2f}%",
            ha="center",
        )
    axes[0].set(
        ylabel="Nuevo atraso (%)",
        ylim=(0, max(100 * g["rate"] for g in first) + 7),
        title="A. Historial y nuevo atraso",
    )
    for replica in sorted({r["replica_id"] for r in rows}):
        group = [r for r in rows if r["replica_id"] == replica]
        axes[1].scatter(
            [r["tenure_days"] for r in group],
            [r["completed_sales"] for r in group],
            s=15,
            alpha=0.45,
            label=f"{replica}: n={len(group)}",
        )
    for boundary in (120, 240):
        axes[1].axvline(boundary, color="gray", linestyle=":", linewidth=1)
    annotation = "\n".join(
        f"{b['band']} dias: n={b['n']}, clientes={b['clients']}, mediana={b['median_sales']:g}"
        for b in relation["second"]
    )
    axes[1].text(
        0.03,
        0.97,
        annotation,
        transform=axes[1].transAxes,
        va="top",
        fontsize=8,
        bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "none"},
    )
    axes[1].set(
        xlabel="Antiguedad de registro (dias)",
        ylabel="Ventas de credito previas observadas",
        title="B. Antiguedad y volumen historico",
    )
    axes[1].legend(loc="lower right", fontsize=8)
    fig.suptitle(
        f"DEV congelado: {len(rows)} prestamos resueltos, 24 clientes, 2 historias alternativas\nPost hoc descriptivo; dependencia intracliente; sin inferencia causal",
        fontsize=11,
    )
    fig.savefig(
        path, dpi=180, metadata={"Software": "BaylonCredit DEV descriptive audit"}
    )
    plt.close(fig)


def run(source, root):
    require(root.is_dir(), "Delivery ROOT must already exist")
    exp = source / "experimento"
    files = [
        exp / name
        for name in (
            "development_rows.json",
            "development_transactions.json",
            "development_audits.json",
            "protocol.json",
            "calibration.json",
            "aligned_v4_report.json",
        )
    ]
    files += [source / "datos" / name for name in ("desarrollo.csv", "final.csv")]
    apf2_sources = [
        REPO / "docs/APF2_Cierre_de_Pendientes.md",
        REPO / "docs/APF2_Validacion_y_Artefactos.md",
    ]
    files += apf2_sources
    files += [
        REPO / "backend/app/ml" / name
        for name in (
            "features.py",
            "synthetic.py",
            "owner_aligned_synthetic.py",
            "outcomes.py",
        )
    ]
    # Hash all frozen experiment bytes, including opaque artifacts, never deserialize them.
    frozen = sorted(p for p in exp.iterdir() if p.is_file())
    before = {str(p): sha(p) for p in sorted(set(files + frozen))}
    rows = load(exp / "development_rows.json")
    worlds = load(exp / "development_transactions.json")["replicas"]
    audits = load(exp / "development_audits.json")
    protocol = load(exp / "protocol.json")
    calibration = load(exp / "calibration.json")
    features = feature_names(REPO / "backend/app/ml/features.py")
    scopes = {
        name: csv_scope(source / "datos" / name)
        for name in ("desarrollo.csv", "final.csv")
    }
    require(
        scopes["desarrollo.csv"]["header"] == scopes["final.csv"]["header"],
        "CSV headers differ",
    )
    study = [r for w in worlds for r in w["rows"] if r["phase"] == "study"]
    resolved = [r for r in study if r["late_payment"] is not None]
    unknown = [r for r in study if r["late_payment"] is None]
    require(
        resolved == rows and len(rows) == 552 and len(unknown) == 7,
        "Frozen DEV accounting mismatch",
    )
    require(
        scopes["desarrollo.csv"]["study"] == len(study) == 559, "DEV CSV count mismatch"
    )
    require(
        scopes["desarrollo.csv"]["unknown"] == len(unknown),
        "DEV unknown count mismatch",
    )
    require(scopes["final.csv"]["study"] == 260, "FINAL schema accounting mismatch")
    with (source / "datos/desarrollo.csv").open(newline="", encoding="utf-8") as stream:
        exported = list(csv.DictReader(stream))
    require(
        exported
        == [{k: "" if v is None else str(v) for k, v in r.items()} for r in study],
        "DEV CSV does not exactly match frozen transactions",
    )
    for w, audit in zip(worlds, audits, strict=True):
        require(
            audit["source_vs_assumptions"]["owner_declared"] == calibration,
            "Saved source anchors differ",
        )
        require(
            audit["source_vs_assumptions"]["simulation_assumptions"]
            == protocol["simulation"],
            "Saved assumptions differ",
        )
        require(
            audit["study_loans"] == sum(r["phase"] == "study" for r in w["rows"]),
            "Saved audit count drift",
        )
    entries = dictionary(
        scopes["desarrollo.csv"]["header"], features, protocol["simulation"]
    )
    q = quality(rows, features, worlds)
    all_q = quality(study, features, worlds)
    rel = relationships(rows)
    # Project the saved report immediately onto DEV OOF only. No FINAL metrics,
    # cached predictions or artifacts are used to assess this criterion.
    saved_report = load(exp / "aligned_v4_report.json")
    family = saved_report["selection"]["global_winner"]["family"]
    signal = {
        "family": family,
        "scope": "DEV resolved OOF review policy only",
        "source": "aligned_v4_report.json: models/<family>/review_policy/oof/metrics",
        "metrics": saved_report["models"][family]["review_policy"]["oof"]["metrics"],
        "dummy_oof_f2": {
            name: saved_report["models"][name]["review_policy"]["oof"]["metrics"]["f2"]
            for name in ("most_frequent", "constant_1")
        },
        "limit": "OOF reutilizado para seleccion: optimista, no evaluacion independiente ni validacion real",
    }
    del saved_report
    require(signal["metrics"]["n"] == len(rows), "DEV OOF denominator mismatch")
    require(
        [(g["late"], g["n"]) for g in rel["first"]] == [(8, 218), (60, 334)],
        "First fixed relationship does not reproduce frozen DEV",
    )
    unknown_audit = []
    by_loan = {loan["loan_id"]: loan for w in worlds for loan in w["loans"]}
    for r in unknown:
        loan = by_loan[r["loan_id"]]
        pending = Decimal(loan["amount"]) - sum(
            (Decimal(p["amount"]) for p in loan["payments"]), Decimal(0)
        )
        verified = (
            pending == Decimal(r["pending_at_cutoff"])
            and pending > 0
            and r["due_date"] >= r["observed_on"]
        )
        require(verified, "Unknown outcome inconsistent with observed payments/cutoff")
        unknown_audit.append(
            {
                k: r[k]
                for k in (
                    "loan_id",
                    "client_id",
                    "replica_id",
                    "evaluated_at",
                    "due_date",
                    "observed_on",
                    "pending_at_cutoff",
                    "late_payment",
                )
            }
            | {"verified_unresolved": verified, "excluded_supervised": True}
        )
    out = root / "anexos/datos"
    require(
        not out.resolve().is_relative_to(source.resolve()),
        "Never write into frozen source package",
    )
    out.mkdir(parents=True, exist_ok=True)
    with (out / "diccionario-datos.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=list(entries[0]))
        writer.writeheader()
        writer.writerows(entries)
    dictionary_md = (
        "# Diccionario completo V4\n\n24 columnas originales, mismo orden en ambos CSV. DEV: 559 filas (552 conocidas, 7 desconocidas). FINAL: "
        + str(scopes["final.csv"]["study"])
        + " filas; "
        + str(scopes["final.csv"]["unknown"])
        + " desconocidas. FINAL solo esquema y conteos, no EDA.\n\n"
    )
    dictionary_md += "Metadatos no entran al vector de once predictores. Rangos de contrato no son rangos observados; estos se guardan por separado en calidad-dev-v4.json. Convenciones de ratios no son observaciones. Tipos CSV son representaciones textuales, tipos indicados son logicos/JSON.\n\n"
    columns = list(entries[0])
    dictionary_md += (
        "| "
        + " | ".join(columns)
        + " |\n| "
        + " | ".join("---" for _ in columns)
        + " |\n"
    )
    dictionary_md += (
        "\n".join("| " + " | ".join(str(e[k]) for k in columns) + " |" for e in entries)
        + "\n"
    )
    (out / "diccionario-datos.md").write_text(dictionary_md, encoding="utf-8")
    calibration_constraints = [
        (
            "1. Escala semanal",
            "Aproximados declarados: 12 fiados/9 clientes; tolerancias de equipo 25%/2, no forzar aprobaciones",
            [
                {
                    "replica": w["replica_id"],
                    "mean_grants": a["mean_weekly_study_grants"],
                    "mean_clients": a["mean_weekly_study_grant_clients"],
                    "saved_pass": a["grant_scale_pass"],
                }
                for w, a in zip(worlds, audits, strict=True)
            ],
        ),
        (
            "2. Importes y exposicion",
            "Anclas 5..50 PEN, tope 80; distribucion lognormal es supuesto",
            [a["amount_summary"] for a in audits],
        ),
        (
            "3. Plazo y pagos",
            "Plazo 1 dia; pagos positivos sin sobrepago; gracia no convierte atraso en puntual",
            [a["hard_constraints_pass"] for a in audits],
        ),
        (
            "4. Visitas y calendario",
            "Ancla visitas 3..14 dias, usual 7; rotacion, 12 clientes y warmup son supuestos",
            [a["visit_gaps"] for a in audits],
        ),
        (
            "5. Atrasos y heterogeneidad",
            "8/45 evaluables es ancla parcial no auditada, no frecuencia forzada; Beta concentracion 3 y estabilidad por cliente son supuestos",
            [a["study_label_counts"] for a in audits],
        ),
        (
            "6. Abonos y politica",
            "10/48 anotaciones; independencia, fraccion 0.5 y pagos completos futuros son supuestos; sin inventar perdida permanente ni excepciones cuantificadas",
            protocol["simulation"]["overdue_policy"],
        ),
        (
            "7. Temporalidad y procedencia",
            "Snapshots solo eventos anteriores; unknown excluido supervision; historias alternativas sinteticas no volumen real; fuente hipotetica anterior excluida",
            {
                "saved_hard_constraints": [a["hard_constraints_pass"] for a in audits],
                "source_docx_sha256": audits[0]["source_vs_assumptions"][
                    "source_docx_sha256"
                ],
            },
        ),
    ]
    scalar_errors = sum(s["invalid_range"] for s in all_q["features"].values())
    snapshot_errors = sum(s["snapshot_mismatch"] for s in all_q["features"].values())
    type_errors = sum(s["invalid_type"] for s in all_q["features"].values())
    nonfinite = sum(s["nonfinite"] for s in all_q["features"].values())
    tn, fp = signal["metrics"]["confusion_matrix"][0]
    fn, tp = signal["metrics"]["confusion_matrix"][1]
    principal = [
        {
            "criterion": CONSIGNA_CRITERIA[0],
            "evidence": "DEV: 2 historias alternativas, 12 clientes/replica; medias semanales "
            + "; ".join(
                f"{w['replica_id']}: {a['mean_weekly_study_grants']:.4f} fiados/{a['mean_weekly_study_grant_clients']:.4f} clientes"
                for w, a in zip(worlds, audits, strict=True)
            ),
            "assessment": "Alineacion aproximada con 12 fiados/9 clientes por semana; no sumar replicas como volumen real.",
            "source": "development_audits.json: weekly_stats, mean_weekly_study_*; calibration.json",
        },
        {
            "criterion": CONSIGNA_CRITERIA[1],
            "evidence": f"559 DEV: {scalar_errors} violaciones de rango por predictor, {type_errors} de tipo y {nonfinite} no finitos; PEN, dias, conteos y proporciones en diccionario.",
            "assessment": "Importes 5..50 PEN, exposicion <=80; contrato MVP puede admitir ratios >1, V4 acotado; cercas IQR no son exclusiones.",
            "source": "quality_all_study.features; diccionario-datos.csv; development_audits.json",
        },
        {
            "criterion": CONSIGNA_CRITERIA[2],
            "evidence": f"559 DEV: {snapshot_errors} discrepancias en once snapshots reconstruidos; plazo 1 dia y pagos auditados; 7 unknown verificados y excluidos de supervision.",
            "assessment": "Eventos observados, sin planes futuros; tolerancia <1e-9 del validador; auditorias guardadas no son validacion independiente.",
            "source": "quality_all_study.features; unknowns; development_audits.json: hard_constraints_pass",
        },
        {
            "criterion": CONSIGNA_CRITERIA[3],
            "evidence": "DEV resuelto: nuevo atraso "
            + " frente a ".join(f"{g['late']}/{g['n']}" for g in rel["first"])
            + "; medianas ventas/antiguedad "
            + "/".join(f"{b['median_sales']:g}" for b in rel["second"])
            + f"; {rel['outside_bands']} fila fuera de bandas, conservada.",
            "assessment": rel["conclusion"]
            + " Dependencia intracliente; no causalidad ni segunda fuente independiente.",
            "source": "relationships; development_rows.json; eda_relaciones_entrega.png",
        },
        {
            "criterion": CONSIGNA_CRITERIA[4],
            "evidence": f"DEV OOF guardado {family}, n={signal['metrics']['n']}: F2={signal['metrics']['f2']:.9f}; Dummy constante 1={signal['dummy_oof_f2']['constant_1']:.9f}, mayoritario={signal['dummy_oof_f2']['most_frequent']:.9f}; TN/FP/FN/TP={tn}/{fp}/{fn}/{tp}.",
            "assessment": "Se observa discriminacion parcial con errores, no senal nula ni separacion perfecta; OOF reutilizado para seleccionar es optimista, no prueba utilidad real.",
            "source": signal["source"],
        },
        {
            "criterion": CONSIGNA_CRITERIA[5],
            "evidence": "APF2: captura real consentida prevista de 30-50 fiados en 4-6 semanas; cierre documentado: 0 elegibles exportados. V4: 552 etiquetas DEV sinteticas; completed_sales restringido a ventas ligadas a credito, MVP contaba ventas registradas sin ese filtro.",
            "assessment": "Cambio de fuente, volumen y cobertura declarado: no cumple captura real prevista. Cero elegibles es evidencia del cierre original, no consulta de DB actual ni ausencia de operaciones.",
            "source": "APF2_Validacion_y_Artefactos.md: H2/contrato; APF2_Cierre_de_Pendientes.md: tabla 1; features.py/synthetic.py y diccionario V4",
        },
        {
            "criterion": CONSIGNA_CRITERIA[6],
            "evidence": f"DEV: {len(study)}/{len(study)} filas origen=simulado; 0 filas reales. Declaracion del propietario aporta agregados, no snapshots reales.",
            "assessment": "No aplica: 100% sintetico; no existe mezcla ni contraste real/simulado. No inferir equivalencia con datos reales.",
            "source": "development_transactions.json; calibration.json: not_a_training_dataset",
        },
    ]
    report = "# Datos: cierre descriptivo V4 SOLO DEV\n\nAnalisis post hoc congelado. No fit, predict, carga joblib, nuevos datos, nuevas features, cambios de runner/protocolo ni seleccion. No se abre DOCX privado. Auditorias guardadas son evidencia historica, no una nueva validacion independiente.\n\n## Ficha En Seis Pasos\n\n"
    steps = [
        "1. Delimitar: prestamos concedidos study; warmup solo contexto para snapshots. CSV DEV completo 559; supervision 552; 7 desconocidos conservados y auditados.",
        "2. Identificar fuente: calibration.json y source_vs_assumptions de development_audits.json; anclas agregadas parciales del propietario, no filas reales ni verdad auditada. Hash del DOCX, sin abrirlo.",
        "3. Operacionalizar: diccionario de las 24 columnas originales y once predictores; tipos, unidades, rangos MVP/V4, null policy y metadatos posteriores al desenlace excluidos.",
        "4. Comprobar calidad: nulos, IDs repetidos, vectores coincidentes, no finitos, rangos y estadisticos IQR por feature; conservar coincidencias legitimas y valores extremos, sin exclusion ni imputacion.",
        "5. Contrastar coherencia: ficha principal con los siete criterios exactos de la consigna 4.2; restricciones de calibracion separadas como detalle. Distinguir anclas, aproximaciones y supuestos; no regenerar para mejorar ajuste.",
        "6. Describir dos relaciones declaradas en el script: reportar magnitud, denominadores y resultado adverso si aparece; sin busqueda de alternativas, causalidad ni independencia ficticia.",
    ]
    report += "\n\n".join(steps) + "\n\n## Ficha Principal: Consigna 4.2\n\n"
    report += "Siete criterios originales de la consigna, solo evidencia DEV y cierre APF2 documentado. Tabla principal compacta; las restricciones de calibracion siguientes son detalle de negocio, no sustituyen estos criterios.\n\n"
    report += "| Criterio original | Evidencia trazable | Lectura y limite |\n| --- | --- | --- |\n"
    for item in principal:
        report += (
            f"| {item['criterion']} | {item['evidence']} | {item['assessment']} |\n"
        )
    report += (
        "\nFuentes: development_audits.json, calidad por predictor y relaciones DEV de este anexo; aligned_v4_report.json solo models/"
        + family
        + "/review_policy/oof/metrics (552 resueltos, no 559); APF2_Cierre_de_Pendientes.md tabla 1 y APF2_Validacion_y_Artefactos.md H2/contrato. Todas hasheadas antes/despues. Sin metricas FINAL ni consulta a la DB actual.\n\n## Restricciones de calibraci\u00f3n\n\nControles de negocio detallados; no son los siete criterios de la consigna. Los resumenes transaccionales guardados pueden incluir warmup como contexto, no como filas de estudio.\n\n"
    )
    for title, rationale, evidence in calibration_constraints:
        report += f"### {title}\n\n{rationale}. Evidencia guardada: `{json.dumps(evidence, ensure_ascii=True)}`.\n\n"
    report += "## Calidad DEV\n\n"
    report += f"Supervisadas n={q['n']}; clientes={q['clients']}; nulos totales={sum(q['nulls_by_column'].values())}; IDs duplicados excedentes={q['duplicate_loan_id_excess']}; grupos de vectores repetidos={q['duplicate_feature_vector_groups']}, filas implicadas={q['duplicate_feature_vector_rows']}, excedentes={q['duplicate_feature_vector_excess']}. No se borra ninguna fila.\n\n"
    report += "| Feature | Min | Max | Mediana | Q1 | Q3 | IQR | Bajo/alto IQR | Nulos | No finitos | Tipo/rango invalido | Snapshot distinto |\n| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |\n"
    for name, s in q["features"].items():
        report += f"| {name} | {s['min']:g} | {s['max']:g} | {s['median']:g} | {s['q1']:g} | {s['q3']:g} | {s['iqr']:g} | {s['below_fence']}/{s['above_fence']} | {s['null']} | {s['nonfinite']} | {s['invalid_type']}/{s['invalid_range']} | {s['snapshot_mismatch']} |\n"
    report += "\nLas cercas IQR son descriptivas: con IQR=0, cualquier valor diferente puede quedar fuera; no equivale a error. quality_all_study incluye los 559, con exactamente 7 targets nulos. Se reconstruyen los once snapshots desde pagos/ventas observados del cache (sin usar planes futuros), con la misma tolerancia absoluta <1e-9 del validador V4; rango invalido y snapshot distinto son conteos separados, no sumar como filas distintas. Los contratos completos de cronologia y politicas constan ademas en auditorias guardadas y su fuente hasheada.\n\n## Desconocidos\n\n"
    report += "\n".join(
        f"- `{r['loan_id']}`: vence {r['due_date']}, corte {r['observed_on']}, saldo {r['pending_at_cutoff']}; sin resolucion al corte; excluido supervision."
        for r in unknown_audit
    )
    report += "\n\n## Dos Relaciones Fijas\n\n"
    report += (
        "A. Historial paid_late y nuevo late_payment, sobre 552 resueltos: "
        + "; ".join(
            f"{g['group']}: {g['late']}/{g['n']} ({100 * g['rate']:.6f}%), {g['clients']} clientes"
            for g in rel["first"]
        )
        + ". Asociacion sintetica, compatible con propension latente estable supuesta; no demuestra riesgo real ni causalidad.\n\n"
    )
    report += (
        "B. "
        + EXPECTATION
        + " Relacion de negocio de apoyo, no senal causal de riesgo ni segunda fuente independiente. Bandas fijadas antes del calculo:\n\n"
    )
    report += "| Antiguedad | n prestamos | Clientes distintos | Mediana ventas | Q1 | Q3 |\n| --- | ---: | ---: | ---: | ---: | ---: |\n"
    for b in rel["second"]:
        report += f"| {b['band']} | {b['n']} | {b['clients']} | {b['median_sales']} | {b['q1_sales']} | {b['q3_sales']} |\n"
    report += f"\nFuera de bandas (<30 dias): {rel['outside_bands']}. {rel['conclusion']}\n\n{rel['limits']} No se presenta paid_late/paid_credits ni puntualidad derivada del mismo historial como evidencia independiente.\n\n"
    report += (
        "## Replica E Integridad\n\nSemillas congeladas (no se usan para generar): "
        + ", ".join(f"{w['replica_id']}={w['seed']}" for w in worlds)
        + ". Calculo determinista sin semilla nueva, sin Spearman/p-valores ni muestreo. El JSON guarda resumenes por replica y SHA256 antes/despues de todas las fuentes y de todo experimento congelado (artefactos opacos solo hash).\n\nFigura exacta: `eda_relaciones_entrega.png`, dos paneles, solo DEV resuelto. FINAL se lee solo para encabezado/conteos/desconocidos; no distribuciones ni relaciones.\n"
    )
    figure(out / "eda_relaciones_entrega.png", rows, rel)
    after = {str(p): sha(p) for p in sorted(set(files + frozen))}
    require(before == after, "Frozen source changed during audit")
    report += "\nIntegridad antes/despues: todos los hashes iguales.\n"
    (out / "coherencia-datos.md").write_text(report, encoding="utf-8")
    result = {
        "scope": "post hoc DEV only; FINAL schema/accounting only",
        "csv": scopes,
        "quality_supervised": q,
        "quality_all_study": all_q,
        "unknowns": unknown_audit,
        "relationships": rel,
        "per_replica": [
            {
                "replica": w["replica_id"],
                "seed": w["seed"],
                "study": sum(r["phase"] == "study" for r in w["rows"]),
                "saved_audit": a,
                "relationships": relationships(
                    [r for r in rows if r["replica_id"] == w["replica_id"]]
                ),
            }
            for w, a in zip(worlds, audits, strict=True)
        ],
        "consigna_section": "4.2",
        "coherence_criteria": principal,
        "dev_signal_saved": signal,
        "apf2_scope": "Original documented closure and planned real capture only; no current DB query",
        "apf2_sources": [str(p) for p in apf2_sources],
        "calibration_constraints": [
            {"criterion": t, "rationale": r, "saved_evidence": e}
            for t, r, e in calibration_constraints
        ],
        "source_sha256_before": before,
        "source_sha256_after": after,
        "frozen_unchanged": before == after,
        "script_sha256": sha(Path(__file__)),
        "numpy_version": np.__version__,
    }
    with (out / "calidad-dev-v4.json").open("w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=True, allow_nan=False)
        stream.write("\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    result = run(args.source.resolve(), args.root.resolve())
    shutil.copyfile(
        args.root / "anexos/datos/coherencia-datos.md",
        REPO / "docs/APF3_Datos_Cierre_V4.md",
    )
    print(
        json.dumps(
            {
                "output": str(args.root / "anexos/datos"),
                "csv": {
                    k: {a: b for a, b in v.items() if a != "header"}
                    for k, v in result["csv"].items()
                },
                "quality": {
                    k: v
                    for k, v in result["quality_supervised"].items()
                    if k not in ("features", "nulls_by_column")
                },
                "relationships": result["relationships"],
                "frozen_unchanged": result["frozen_unchanged"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
