"""Package immutable CV3 evidence and standalone offline sources, without fitting models."""

import argparse
import csv
import hashlib
import importlib.util
import json
import shutil
import statistics
from pathlib import Path

import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]


def package(root: Path, source: Path):
    experiment = root / "experimento"
    report = json.loads((experiment / "grouped_cv_report.json").read_text())
    provenance = report["provenance"]
    code = root / "codigo"
    for folder in (
        code / "scripts",
        code / "app/ml",
        code / "app/db",
        code / "app/models",
        root / "datos",
        root / "informe/figuras",
    ):
        folder.mkdir(parents=True, exist_ok=True)
    files = [
        "app/__init__.py",
        "app/db/__init__.py",
        "app/db/base.py",
        "scripts/academic_credit_grouped_cv.py",
        *(f"app/ml/{name}.py" for name in ("features", "synthetic", "outcomes")),
    ]
    files.extend(
        str(path.relative_to(REPO / "backend"))
        for path in (REPO / "backend/app/models").glob("*.py")
    )
    for filename in files:
        shutil.copyfile(REPO / "backend" / filename, code / filename)
    # The academic package must not prime the application's unrelated legacy model.
    (code / "app/ml/__init__.py").write_text(
        '"""Isolated academic simulation package; no service initialization."""\n'
    )
    for name, filename in {
        "runner": "scripts/academic_credit_grouped_cv.py",
        **{name: f"app/ml/{name}.py" for name in ("features", "synthetic", "outcomes")},
    }.items():
        assert (
            hashlib.sha256((code / filename).read_bytes()).hexdigest()
            == provenance["code_sha256"][name]
        )
    assert (
        hashlib.sha256(source.read_bytes()).hexdigest() == provenance["source_sha256"]
    )
    shutil.copyfile(source, root / "datos/ledger_desarrollo_original.json")
    development = json.loads((experiment / "development_rows.json").read_text())
    final = json.loads((experiment / "final_transactions.json").read_text())["rows"]
    for filename, rows in (("desarrollo.csv", development), ("final.csv", final)):
        keys = ["origen", *[key for key in rows[0] if key != "origen"]]
        with (root / "datos" / filename).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=keys)
            writer.writeheader()
            writer.writerows({**row, "origen": "simulado"} for row in rows)
    (root / "requirements.txt").write_text(
        "scikit-learn==1.9.1\nnumpy==2.5.3\nscipy==1.18.1\njoblib==1.6.0\n"
        "threadpoolctl==3.7.0\nSQLAlchemy==2.0.54\ngreenlet==3.5.6\ntyping_extensions==4.16.0\n"
        "cloudpickle==3.1.2\nnarwhals==2.28.0\n"
    )

    spec = importlib.util.spec_from_file_location(
        "report_layout", REPO / "deploy/generate-apf3-report.py"
    )
    layout = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(layout)
    plt.switch_backend("Agg")
    plt.rcParams.update(
        {"font.size": 10, "axes.spines.top": False, "axes.spines.right": False}
    )
    fig, ax = plt.subplots(figsize=(7.8, 2.7), layout="constrained")
    counts = [
        sum(row["late_payment"] == label for row in development) for label in (0, 1)
    ]
    bars = ax.bar(["Puntual (0)", "Atraso (1)"], counts, color=["#246c67", "#b65e39"])
    ax.bar_label(bars, padding=3)
    ax.set(
        ylabel="Fiados de desarrollo",
        ylim=(0, max(counts) * 1.15),
        title="Datos simulados · CV3",
    )
    fig.savefig(root / "informe/figuras/eda_balance.png", dpi=180)
    plt.close(fig)
    grouped = [
        [
            ("Sin pagos previos", [r for r in development if r["paid_credits"] == 0]),
            (
                "Pagados sin atraso",
                [
                    r
                    for r in development
                    if r["paid_credits"] > 0 and r["paid_late"] == 0
                ],
            ),
            ("Con pagos tardíos", [r for r in development if r["paid_late"] > 0]),
        ],
        [
            ("0–25 %", [r for r in development if r["utilization"] <= 0.25]),
            (">25–50 %", [r for r in development if 0.25 < r["utilization"] <= 0.5]),
            (">50 %", [r for r in development if r["utilization"] > 0.5]),
        ],
    ]
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.1), layout="constrained")
    conclusions = []
    for ax, groups, title in zip(
        axes, grouped, ("Historial previo", "Utilización previa"), strict=True
    ):
        rates = [
            100 * statistics.mean(r["late_payment"] for r in rows) for _, rows in groups
        ]
        bars = ax.bar(
            [f"{name}\nn={len(rows)}" for name, rows in groups], rates, color="#315b84"
        )
        ax.bar_label(bars, fmt="%.1f%%", padding=3, fontsize=9)
        ax.set(title=title, ylabel="Atraso (%)", ylim=(0, max(rates) + 16))
        ax.tick_params(axis="x", labelsize=8)
        conclusions.append(
            "; ".join(
                f"{name}: {rate:.2f} % (n={len(rows)})"
                for (name, rows), rate in zip(groups, rates, strict=True)
            )
            + "."
        )
    fig.savefig(root / "informe/figuras/eda_relaciones.png", dpi=180)
    plt.close(fig)
    matrix = report["models"][report["selection"]["global_winner"]["family"]]["final"][
        "confusion_matrix"
    ]
    fig, ax = plt.subplots(figsize=(5, 3), layout="constrained")
    ax.imshow(matrix, cmap="Blues")
    for row in range(2):
        for column in range(2):
            ax.text(
                column,
                row,
                str(matrix[row][column]),
                ha="center",
                va="center",
                color="white" if matrix[row][column] > 400 else "black",
                fontsize=15,
            )
    ax.set(
        xticks=[0, 1],
        yticks=[0, 1],
        xticklabels=["Puntual", "Atraso"],
        yticklabels=["Puntual", "Atraso"],
        xlabel="Predicción",
        ylabel="Desenlace",
        title="Árbol CV3 · Umbral 0,70",
    )
    fig.savefig(root / "informe/figuras/matriz_v3.png", dpi=180)
    plt.close(fig)
    summary = []
    for field in (
        "requested_amount",
        "paid_credits",
        "paid_late",
        "outstanding",
        "utilization",
        "tenure_days",
    ):
        values = [float(row[field]) for row in development]
        summary.append(
            [
                field,
                f"{min(values):.2f}",
                f"{statistics.mean(values):.2f}",
                f"{statistics.median(values):.2f}",
                f"{max(values):.2f}",
            ]
        )
    text = (REPO / "docs/APF3_TD_Grupo2_ML_Innovacion_CV3.md").read_text()
    for key, value in {
        "eda_table": layout.table(
            ["Variable", "Mín.", "Media", "Mediana", "Máx."], summary
        ),
        "history_conclusion": conclusions[0],
        "exposure_conclusion": conclusions[1],
    }.items():
        assert "{{" + key + "}}" in text
        text = text.replace("{{" + key + "}}", value)
    (root / "informe" / (layout.NAME + ".md")).write_text(text)
    checks = layout.documents(text, root / "informe")
    layout.write_json(root / "informe/verificacion-informe.json", checks)
    layout.write_json(root / "informe/manifest.json", {"files": {}, "sources": {}})
    print(
        json.dumps(
            {
                "packaged_source_files": len(files),
                "development_rows": len(development),
                "final_rows_including_unresolved": len(final),
                **checks,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    package(args.root, args.source)
