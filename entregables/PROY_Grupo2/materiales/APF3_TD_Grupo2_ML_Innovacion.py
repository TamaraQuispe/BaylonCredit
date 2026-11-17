#!/usr/bin/env python3
"""APF3 Grupo 2: reproduccion ejecutable de V6 Final.

Python normal: python APF3_TD_Grupo2_ML_Innovacion.py
Offline: --archive /ruta/APF3_Grupo2_V6_Final.zip --runtime-python /venv/bin/python
Por defecto ENTRENA; no muestra resultados antiguos como si fueran entrenamiento.
La primera ejecucion necesita red para ZIP, uv, Python y paquetes. Despues del
bootstrap el ML usa solo archivos locales, sin API, BD, credenciales ni servicios.
Repetir semillas conocidas verifica reproducibilidad, NO una evaluacion independiente.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

ARCHIVE_URL = (
    "https://raw.githubusercontent.com/TamaraQuispe/BaylonCredit/"
    "927db56e0645c718c4342782a6e28bde89ce602c/entregables/APF3_Grupo2_V6_Final.zip"
)
ARCHIVE_SHA256 = "d3095eae427a4d67927d820d1951b36cbeef339adad10edc89bd40cfdde500f6"
PROTOCOL_SHA256 = "7e489955792aab975c8ff14a95a77e70095a1c8a2ed1682847851773b8922541"
PINS = {
    "sources/APF3_PENDING_V6_FINAL_PROTOCOL.json": PROTOCOL_SHA256,
    "revision/academic_credit_pending_v6_final.py":
        "eac29527d158918b21c4a9bd88e447913ed113e902ce6f050e3246dfde2ac034",
    "revision/policy.py": "418af45fcdc1a5d952daac7aa5139bfa87d2a66ef126255f306cff3c66591f1f",
    "experiment/final_manifest.json":
        "471e5bd3849e8ee8f2d79254823eb4dcfd7a679d67b49efc6257d467224a06cf",
    "experiment/freeze_before_final.json":
        "2faccb7cf2248a4eed21753b6b6dc336f82aaea5e1b19a589a912974d5837f7d",
}
REQUIREMENTS = (
    "scikit-learn==1.9.1", "numpy==2.5.3", "scipy==1.18.1",
    "joblib==1.6.0", "threadpoolctl==3.7.0", "SQLAlchemy==2.0.54",
    "matplotlib==3.11.2",
)
FAMILIES = ("tree", "svm", "most_frequent", "constant_1")
METRICS = ("precision", "recall", "f1", "f2", "accuracy", "roc_auc", "brier")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"Clave JSON duplicada: {key}")
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda value: require(False, f"JSON no finito: {value}"))


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=True, allow_nan=False)
        stream.write("\n")


def safe_name(name):
    require(isinstance(name, str) and name and "\\" not in name and ":" not in name
            and "\x00" not in name, f"Ruta ZIP insegura: {name!r}")
    p = PurePosixPath(name)
    require(not p.is_absolute() and ".." not in p.parts and p.as_posix() == name
            and name != ".", f"Ruta ZIP insegura: {name!r}")
    for part in p.parts:
        lower = part.lower()
        require(not lower.startswith(".env") and lower not in {
            "__pycache__", ".cache", ".pytest_cache", ".git", ".ds_store",
            "credentials.json", "secrets.json", "id_rsa", "id_ed25519",
        } and not lower.endswith((".pem", ".key", ".pyc", ".pyo")),
            f"Secreto/cache prohibido: {name}")
    return name


def scan_zip(data, depth=0):
    """Preflight completo, incluidos documentos Office; ningun write de miembros."""
    require(depth < 5, "ZIP anidado demasiado profundo")
    files = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        items = archive.infolist()
        require(len(items) < 10000 and sum(i.file_size for i in items) < 512_000_000,
                "ZIP excede limites de seguridad")
        names = set()
        for item in items:
            name = safe_name(item.filename.rstrip("/"))
            require(name not in names, f"Miembro duplicado: {name}")
            names.add(name)
            mode = item.external_attr >> 16
            require(not stat.S_ISLNK(mode) and stat.S_IFMT(mode) in
                    (0, stat.S_IFREG, stat.S_IFDIR), f"Miembro no regular: {name}")
            require(not item.flag_bits & 1, "ZIP cifrado no permitido")
            if item.is_dir():
                continue
            content = archive.read(item)
            signatures = (rb"-----BEGIN " + rb"(?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"
                          rb"|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}"
                          rb"|sk-(?:proj-|or-v1-)[A-Za-z0-9_-]{20,}")
            require(not re.search(signatures, content), f"Secreto detectado: {name}")
            if name.lower().endswith((".zip", ".docx", ".pptx")):
                scan_zip(content, depth + 1)
            files[name] = content
    return files


def check_hashes(files, expected, exact=False):
    require(isinstance(expected, dict) and expected, "Inventario vacio")
    if exact:
        require(set(files) == set(expected), "Inventario incompleto o con extras")
    for name, digest in expected.items():
        safe_name(name)
        require(isinstance(digest, str) and re.fullmatch("[0-9a-f]{64}", digest),
                f"Digest invalido: {name}")
        require(name in files and sha(files[name]) == digest, f"SHA256 incorrecto: {name}")


def verify_archive(data):
    # Carga/validacion: el pin externo autentica incluso al propio manifiesto.
    require(sha(data) == ARCHIVE_SHA256, "SHA256 del ZIP no confiable; no se extrajo ni ejecuto nada")
    packed = scan_zip(data)
    prefix = "APF3_Grupo2_V6_Final/"
    require(all(n.startswith(prefix) for n in packed), "Raiz inesperada del ZIP")
    files = {n[len(prefix):]: value for n, value in packed.items()}
    manifest = load(files["manifest-v6-final.json"])
    check_hashes({n: v for n, v in files.items() if n != "manifest-v6-final.json"},
                 manifest["files"], exact=True)
    check_hashes(files, PINS)
    # Solo integridad de evidencia historica; sus resultados NO entran al entrenamiento.
    for folder, manifest_name in (("experiment", "final_manifest.json"),
                                   ("development", "development_manifest.json")):
        subset = {n[len(folder) + 1:]: v for n, v in files.items() if n.startswith(folder + "/")}
        check_hashes({n: v for n, v in subset.items() if n != manifest_name},
                     load(subset[manifest_name])["files"], exact=True)
    freeze = load(files["experiment/freeze_before_final.json"])
    check_hashes({n.removeprefix("experiment/"): v for n, v in files.items()
                  if n.startswith("experiment/")}, freeze["files"])
    require(freeze["final_generation_calls"] == freeze["final_prediction_calls"] == 0,
            "FINAL presente antes del freeze publicado")
    require(sum(n.startswith("codigo-base/") for n in files) == 21, "Codepack no tiene 21 archivos")
    return files


def new_workspace(requested):
    if requested is None:
        return Path(tempfile.mkdtemp(prefix="apf3-v6-final-", dir="/content" if Path("/content").is_dir() else None)).resolve()
    path = Path(os.path.abspath(requested))
    require(not any(p.is_symlink() for p in (path, *path.parents)), "Work-dir no admite symlinks")
    require(path.parent.is_dir(), "El padre de work-dir debe existir")
    if path.exists():
        require(path.is_dir() and not any(path.iterdir()), "Work-dir debe ser nuevo o vacio")
    else:
        path.mkdir()
    return path.resolve()


def runtime_python(work, supplied):
    if supplied:
        python = Path(supplied).absolute()
        require(python.is_file(), "No existe --runtime-python")
        return python
    # Bootstrap stdlib: ni pip global ni cambio de paquetes/kernel Colab.
    target = work / "bootstrap"
    subprocess.run([sys.executable, "-m", "pip", "--isolated", "install", "--target", str(target),
                    "--no-cache-dir", "uv>=0.9,<1"], check=True)
    env = os.environ.copy()
    env.update(PYTHONPATH=str(target), UV_PYTHON_INSTALL_DIR=str(work / "managed-python"),
               UV_PYTHON_BIN_DIR=str(work / "python-bin"),
               UV_CACHE_DIR=str(work / "uv-cache"), UV_NO_CONFIG="1")
    uv = [sys.executable, "-m", "uv"]
    subprocess.run(uv + ["python", "install", "3.12.14"], env=env, check=True)
    subprocess.run(uv + ["venv", "--python", "3.12.14", "--managed-python", str(work / "venv")],
                   env=env, check=True)
    python = work / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    subprocess.run(uv + ["pip", "install", "--python", str(python), *REQUIREMENTS], env=env, check=True)
    return python


# Preproceso/CV/entrenamiento/evaluacion: se delegan al runner inmutable, no se
# reimplementa ML. Imputacion mediana y StandardScaler dentro de cada Pipeline;
# tres folds por cliente tambien en calibracion sigmoid, 12 arboles + 6 SVM,
# siete umbrales, dos Dummy. Solo etiquetas conocidas ajustan el modelo. La
# seleccion usa F2 OOF con cupo, NO FINAL. Artifacts + seleccion congelan antes
# de generar FINAL una vez y puntuar un batch por familia, sin retune/reseed.
DRIVER = r'''
import importlib.util
import importlib.metadata
import json
from pathlib import Path
import sys

source, outputs, protocol_sha = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
runner_path = source / "revision/academic_credit_pending_v6_final.py"
spec = importlib.util.spec_from_file_location("apf3_frozen_runner", runner_path)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
runner.CODE_ROOT = source / "codigo-base"
runner.BACKEND = runner.CODE_ROOT
policy = source / "revision/policy.py"
protocol = source / "sources/APF3_PENDING_V6_FINAL_PROTOCOL.json"
revision = runner.load(protocol)
old, _ = runner.helpers()
runtime = old.validate_runtime(revision["runtime"])
if importlib.metadata.version("SQLAlchemy") != "2.0.54":
    raise ValueError("SQLAlchemy debe ser 2.0.54")
runner.write(outputs / "runtime.json", {**runtime, "SQLAlchemy": "2.0.54"})

# Guards ANTES de ajustar cualquier modelo: directorio de artefactos inexistente.
base = runner.load(source / "sources/APF3_PENDING_V6_MODEL_PROTOCOL.json")["illustrative_input"]["features"]
guards = []
for updates, expected in (({"outstanding": 30, "pending_current": 1}, "blocked_pending_balance"),
                           ({"completed_sales": 0, "paid_credits": 0, "paid_late": 0,
                             "punctuality_rate": 0}, "requires_owner_review")):
    result = runner.predict(outputs / "NO_EXISTE", {**base, **updates}, policy)
    if result["decision"] != expected or result["model_called"] or result["probability"] is not None:
        raise ValueError("Fallo de guard pre-modelo")
    guards.append(result)
runner.write(outputs / "guard_cases.json", guards)
print("Runtime validado; guards sin artefacto aprobados. Generando DEV...", flush=True)
runner.prepare_dev(protocol, protocol_sha, source / "sources", outputs / "development", policy)
print("DEV auditado. Entrenando arbol, SVM y baselines; luego freeze y FINAL...", flush=True)
report = runner.train_evaluate(protocol, protocol_sha, outputs / "development", outputs / "experiment", policy)
# Inferencia/exportacion: carga selected_model.joblib NUEVO mediante verify_freeze.
example = runner.predict(outputs / "experiment", base, policy)
if not example["model_called"]:
    raise ValueError("Ejemplo elegible no invoco modelo nuevo")
runner.write(outputs / "new_example.json", example)
runner.write(outputs / "new_example_input.json", {"features": base})
runner.write(outputs / "execution.json", {"training_executed": True,
    "fixed_procedure_replay": True, "independent_evaluation": False,
    "old_final_supplied_to_training": False, "runtime": runtime,
    "final_checks": runner.load(outputs / "experiment/report_checks.json")})
print("Entrenamiento y FINAL terminados; artefacto nuevo verificado y cargado.", flush=True)
'''


def results(work, files):
    outputs = work / "outputs"
    report = load((outputs / "experiment/pending_v6_report.json").read_bytes())
    # Primer acceso a metricas/resultados originales: solo DESPUES del nuevo test.
    original = load(files["experiment/pending_v6_report.json"])
    differences = []
    rows = []
    for family in FAMILIES:
        model, previous = report["models"][family], original["models"][family]
        for split in ("train", "oof", "final"):
            for scope, actual, expected in (
                ("raw", model[split], previous[split]),
                ("policy", model["review_policy"][split], previous["review_policy"][split]),
            ):
                if actual != expected:
                    differences.append({"family": family, "split": split, "scope": scope,
                                        "actual": actual, "published": expected})
            rows.append({"family": family, "split": split, "threshold": model["threshold"],
                         **{k: model[split].get(k) for k in METRICS},
                         "confusion_matrix": model[split]["confusion_matrix"],
                         "policy_f2": model["review_policy"][split]["metrics"]["f2"]})
    winner = report["selection"]["global_winner"]
    old_winner = original["selection"]["global_winner"]
    selection_match = winner == old_winner
    with (outputs / "comparison.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    write_json(outputs / "published_comparison.json", {
        "archive_sha256": ARCHIVE_SHA256, "exact_raw_and_policy_reports": not differences,
        "selection_matches": selection_match, "differences": differences,
        "note": "Numerical differences are reported, never patched or used to force the winner."})
    chosen = report["models"][winner["family"]]
    summary = {"archive_url": ARCHIVE_URL, "archive_sha256": ARCHIVE_SHA256,
               "protocol_sha256": PROTOCOL_SHA256, "training_executed": True,
               "independent_evaluation": False, "selected_family": winner["family"],
               "threshold": winner["threshold"], "development": report["development"],
               "final": report["final"], "metrics": chosen["final"],
               "error_cases": chosen["error_cases"][:3],
               "published_reports_match": not differences and selection_match,
                "limits": report["limits"],
                "group_review": "Realizada por los cuatro integrantes del Grupo 2"}
    write_json(outputs / "summary.json", summary)
    print("\nAPF3 V6 FINAL | DATOS 100% SINTETICOS | REPRODUCCION, NO NUEVA VALIDACION")
    print("Familia         split    umbral precision recall    F1        F2        accuracy  F2-cupo")
    for row in rows:
        print(f"{row['family']:<15} {row['split']:<8} {row['threshold']:<6.2f} "
              + " ".join(f"{row[k]:.6f}" for k in ("precision", "recall", "f1", "f2", "accuracy", "policy_f2")))
    print(f"\nSeleccion OOF: {winner['family']}; umbral={winner['threshold']}; "
          f"CM FINAL [0,1]={chosen['final']['confusion_matrix']}")
    for name in ("development", "final"):
        data = report[name]
        print(f"{name}: elegibles={data['study_rows']}, conocidos={data['known_rows']}, "
              f"desconocidos={data['unknown_rows']}; routing={data['routing']}")
    print("Cero remisiones manuales observadas no elimina la regla: warmup aporta historial pagado; "
          "los casos sin historial se comprueban ademas con predict sin artefacto.")
    print("Semillas fijas DEV 2026112601/02; FINAL 2026112603; CV 2026112604/05; "
          "sin reseed, sin tuning sobre FINAL. 2 desconocidos elegibles no son clase cero.")
    print("Comparacion publicada raw/policy/seleccion:", summary["published_reports_match"],
          "| discrepancias:", len(differences))
    print("Tres errores ilustrativos (no analisis causal):", json.dumps(summary["error_cases"], ensure_ascii=True))
    print("Guards y nueva inferencia:", json.dumps(load((outputs / "guard_cases.json").read_bytes())
          + [load((outputs / "new_example.json").read_bytes())], ensure_ascii=True))
    evidence = load(files["support/review-v6-final-deployment-sanitized.json"])
    write_json(outputs / "integration_evidence.json", evidence)
    print("Integracion: evidencia publicada verificada por hash, NO comprobacion live:", evidence.get("url"))
    print("Normativa: uso academico, no aprobacion crediticia ni beneficio comercial demostrado. "
          "Para datos reales: Ley peruana 29733, consentimiento/base legal, minimizacion, "
          "seguridad y revision humana; este replay no certifica cumplimiento legal.")
    print("Revision humana del proyecto: realizada por los cuatro integrantes del Grupo 2.")
    print("Limites del protocolo:", json.dumps(report["limits"], ensure_ascii=True))
    print("Resultados:", outputs)
    print("Modelo nuevo:", outputs / "experiment/selected_model.joblib")
    return report


# Este suplemento se ejecuta DESPUES del replay/freeze en el MISMO Python aislado.
# No importa el runner ni lee FINAL ni artefactos de modelos.
EDA_DRIVER = r'''
from collections import Counter
import csv
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

outputs = Path(sys.argv[1])
features = ("completed_sales", "paid_credits", "paid_late", "pending_overdue",
            "pending_current", "outstanding", "utilization", "requested_ratio",
            "tenure_days", "punctuality_rate", "overdue_rate")
with (outputs / "development/development_eligible.csv").open(newline="", encoding="utf-8") as stream:
    rows = list(csv.DictReader(stream))
assert all(r["late_payment"] in ("0", "1", "") for r in rows)
known = [r for r in rows if r["late_payment"] in ("0", "1")]
counts = Counter(r["late_payment"] or "unknown" for r in rows)
assert len(known) == 534 and counts["unknown"] == 7, "DEV no coincide con el protocolo fijo"

def save_csv(name, records):
    with (outputs / name).open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

def save_json(name, value):
    with (outputs / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=True, allow_nan=False)
        stream.write("\n")

descriptives = []
for feature in features:
    values = np.array([float(r[feature]) for r in known if r[feature] != ""])
    assert np.isfinite(values).all()
    stats = dict.fromkeys(("min", "p25", "median", "p75", "max", "mean", "std"))
    if len(values):
        stats.update(zip(("min", "p25", "median", "p75", "max"),
                         map(float, np.quantile(values, [0, .25, .5, .75, 1]))))
        stats["mean"] = float(values.mean())
        stats["std"] = float(values.std(ddof=1)) if len(values) > 1 else None
    descriptives.append({"feature": feature, "count": len(values),
                         "missing": len(known) - len(values), **stats})
save_csv("eda_dev_descriptives.csv", descriptives)
save_csv("eda_dev_target_counts.csv", [
    {"target": label, "count": counts[label], "denominator": len(known) if label != "unknown" else len(rows),
     "denominator_scope": "known_DEV" if label != "unknown" else "all_eligible_DEV"}
    for label in ("0", "1", "unknown")])

# Agrupaciones descriptivas fijas; no buscan cortes que optimicen una metrica.
pairs = [r for r in known if r["tenure_days"] != "" and r["completed_sales"] != ""]
x = np.array([float(r["tenure_days"]) for r in pairs])
y = np.array([float(r["completed_sales"]) for r in pairs])
corr = float(np.corrcoef(x, y)[0, 1]) if len(x) > 1 and x.std() > 0 and y.std() > 0 else None
groups = []
for lower, upper in ((0, 90), (90, 180), (180, 365), (365, None)):
    subset = [r for r in pairs if float(r["tenure_days"]) >= lower
              and (upper is None or float(r["tenure_days"]) < upper)]
    groups.append({"relationship": "tenure_vs_completed_sales", "group": f"[{lower},{upper if upper else 'inf'})",
                   "count": len(subset), "denominator": len(pairs),
                   "mean_completed_sales": float(np.mean([float(r["completed_sales"]) for r in subset])) if subset else None,
                   "late_count": None, "late_rate": None})
paid_rows = [r for r in known if r["paid_late"] != ""]
for prior_late in (False, True):
    subset = [r for r in paid_rows if (float(r["paid_late"]) > 0) == prior_late]
    late = sum(r["late_payment"] == "1" for r in subset)
    groups.append({"relationship": "prior_paid_late_vs_observed_late", "group": "yes" if prior_late else "no",
                   "count": len(subset), "denominator": len(subset), "mean_completed_sales": None,
                   "late_count": late, "late_rate": late / len(subset) if subset else None})
save_csv("eda_dev_relationships.csv", groups)
no, yes = groups[-2:]
delta = yes["late_rate"] - no["late_rate"] if yes["count"] and no["count"] else None
conclusions = [
    f"Pearson tenure_days/completed_sales = {corr}; pares completos n={len(pairs)}. "
    + ("Asociacion lineal positiva." if corr is not None and corr > 0 else
       "Asociacion lineal negativa." if corr is not None and corr < 0 else "Sin asociacion lineal estimable distinta de cero."),
    f"Tasa de atraso observado: historial paid_late>0={yes['late_rate']} (n={yes['count']}), "
    f"sin ese historial={no['late_rate']} (n={no['count']}); diferencia si-no={delta}. "
    + ("Mayor tasa con historial." if delta is not None and delta > 0 else
       "Menor tasa con historial." if delta is not None and delta < 0 else "No se observa una tasa mayor con historial.")]
caveats = ["EDA descriptiva post hoc, posterior al freeze/replay; no seleccion ni retune.",
           "Datos 100% sinteticos, no datos reales ni evidencia causal o beneficio comercial.",
           "534 etiquetas DEV conocidas; 7 nulas excluidas de estadisticas y relaciones, nunca clase 0.",
           "Observaciones repetidas por cliente; asociaciones no independientes, sin pruebas inferenciales.",
           "Pearson no implica monotonia; medias por intervalos no prueban tendencia creciente.",
           "Cuantiles lineales; std muestral ddof=1; sin imputacion; faltantes por variable excluidos."]
save_json("eda_dev_relationships.json", {"scope": "known DEV only", "known_rows": len(known),
    "unknown_excluded": counts["unknown"], "pair_count": len(pairs), "pair_missing": len(known)-len(pairs),
    "paid_late_missing": len(known)-len(paid_rows), "pearson_r": corr,
    "late_rate_difference_yes_minus_no": delta, "groups": groups, "caveats": caveats, "conclusions": conclusions})
save_json("eda_dev.json", {"scope": "DEV only, descriptive post hoc, synthetic, no actual data",
    "rows": len(rows), "known_rows": len(known), "labels": dict(counts),
    "clients_known": len({r["client_id"] for r in known}),
    "missing_by_feature_known": {r["feature"]: r["missing"] for r in descriptives},
    "duplicate_loan_ids": len(rows)-len({r["loan_id"] for r in rows}),
    "caveats": caveats, "conclusions": conclusions})

figures = []
fig, ax = plt.subplots(figsize=(7, 4))
ax.bar(["Puntual (0)", "Atraso (1)"], [counts["0"], counts["1"]])
ax.set(title="DEV sintetico conocido (n=534); 7 nulos excluidos", ylabel="Fiados")
figures.append((fig, "eda_dev_labels.png"))
fig, ax = plt.subplots(figsize=(7, 4))
ax.scatter(x, y, alpha=.35, s=16)
ax.set(title=f"DEV conocido: antiguedad y ventas (n={len(pairs)}, r={corr:.3f})" if corr is not None else "DEV: asociacion no estimable",
       xlabel="tenure_days", ylabel="completed_sales")
figures.append((fig, "eda_dev_tenure_completed_sales.png"))
fig, ax = plt.subplots(figsize=(7, 4))
ax.bar([f"No (n={no['count']})", f"Si (n={yes['count']})"],
       [g["late_rate"] if g["late_rate"] is not None else 0 for g in (no, yes)])
ax.set(title="DEV conocido: atraso observado por historial previo", xlabel="paid_late > 0",
       ylabel="Tasa late_payment=1 (denominador: grupo conocido)", ylim=(0, 1))
figures.append((fig, "eda_dev_prior_paid_late.png"))
fig, ax = plt.subplots(figsize=(7, 4))
for label, title in (("0", "Puntual"), ("1", "Atraso")):
    ax.hist([float(r["requested_ratio"]) for r in known if r["late_payment"] == label and r["requested_ratio"] != ""],
            bins=np.linspace(0, max(float(r["requested_ratio"]) for r in known if r["requested_ratio"] != ""), 13),
            alpha=.55, label=title)
ax.set(title="DEV sintetico conocido: monto/cupo por etiqueta", xlabel="requested_ratio", ylabel="Fiados")
ax.legend()
figures.append((fig, "eda_dev_requested_ratio.png"))
for fig, name in figures:
    fig.text(.5, .01, "Descriptivo post hoc; sintetico; no causal; sin retune", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .035, 1, 1))
    fig.savefig(outputs / name, dpi=140)
    plt.close(fig)
annex = "# Anexo EDA DEV\n\n" + "\n\n".join(caveats + conclusions)
annex += "\n\n" + "\n\n".join(f"![{name}]({name})" for _, name in figures)
annex += "\n\n" + "\n".join(f"- [{name}]({name})" for name in (
    "eda_dev_descriptives.csv", "eda_dev_target_counts.csv", "eda_dev_relationships.csv", "eda_dev_relationships.json"))
with (outputs / "anexo_eda_dev.md").open("x", encoding="utf-8") as stream:
    stream.write(annex + "\n")
print("EDA DEV post hoc:", *conclusions, sep="\n")
'''


def eda_and_display(work, report, python, env):
    outputs = work / "outputs"
    subprocess.run([str(python), "-B", "-c", EDA_DRIVER, str(outputs)],
                   env={**env, "MPLCONFIGDIR": str(work / "matplotlib-config")}, cwd=work, check=True)
    try:
        from IPython import get_ipython
        from IPython.display import Image, Markdown, display
        if get_ipython() is not None:
            winner = report["selection"]["global_winner"]
            display(Markdown("## APF3 V6 Final\nEntrenamiento nuevo, procedimiento fijo; datos sinteticos. "
                             f"Seleccion OOF: **{winner['family']}**, umbral **{winner['threshold']}**. "
                             "No es una segunda validacion independiente."))
            for name in ("eda_dev_labels.png", "eda_dev_tenure_completed_sales.png",
                         "eda_dev_prior_paid_late.png", "eda_dev_requested_ratio.png"):
                display(Image(filename=str(outputs / name)))
            display(Markdown(f"[Anexo EDA local]({outputs / 'anexo_eda_dev.md'})"))
    except ImportError:
        pass


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="ZIP confiable local; evita descargarlo")
    parser.add_argument("--work-dir", type=Path, help="Directorio NUEVO o vacio; no sobrescribe")
    parser.add_argument("--runtime-python", type=Path, help="Python exacto existente; validado antes de fit")
    parser.add_argument("--verify-only", action="store_true", help="Solo integridad; NO entrena ni infiere")
    args = parser.parse_args(argv)
    if args.archive:
        data = args.archive.read_bytes()
    else:
        print("Descargando ZIP inmutable publicado; sin login ni credenciales...", flush=True)
        try:
            with urllib.request.urlopen(ARCHIVE_URL, timeout=120) as response:
                data = response.read(128_000_001)
            require(len(data) <= 128_000_000, "Descarga demasiado grande")
        except Exception as error:
            raise RuntimeError("No se pudo descargar el ZIP (red/GitHub privado/bloqueado). "
                               "Use --archive con el ZIP publicado exacto; no requiere files.upload. "
                               "El bootstrap tambien necesita red salvo --runtime-python preinstalado.") from error
    files = verify_archive(data)
    print(f"SHA256 externo + inventario completo + freeze + documentos verificados: {len(files)} archivos")
    if args.verify_only:
        print("VERIFY-ONLY: no entrenamiento, inferencia, generacion ni extraccion.")
        return None
    work = new_workspace(args.work_dir)
    print("Workspace nuevo:", work, flush=True)
    source = work / "source" / "APF3_Grupo2_V6_Final"
    # No se extrae experiment/, development/, datos/ ni ningun joblib publicado.
    for name, content in files.items():
        if (name.startswith(("codigo-base/", "revision/"))
                or (name.startswith("sources/") and name.endswith(".json"))):
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(content)
    outputs = work / "outputs"
    outputs.mkdir()
    python = runtime_python(work, args.runtime_python)
    driver = work / "run_frozen.py"
    with driver.open("x", encoding="utf-8") as stream:
        stream.write(DRIVER)
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", OMP_NUM_THREADS="1",
               OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    # Solo valida: nunca instala ni modifica un --runtime-python proporcionado.
    subprocess.run([str(python), "-B", "-c",
                    "import importlib.metadata as m; import importlib.util as u; "
                    "assert u.find_spec('matplotlib') is not None, "
                    "'Dependencia obligatoria ausente: matplotlib==3.11.2 en --runtime-python; runtime no modificado'; "
                    "assert m.version('matplotlib') == '3.11.2', 'Se requiere matplotlib==3.11.2'"],
                   env=env, cwd=work, check=True)
    subprocess.run([str(python), "-B", str(driver), str(source), str(outputs), PROTOCOL_SHA256],
                   env=env, cwd=work, check=True)
    report = results(work, files)
    eda_and_display(work, report, python, env)
    # Hashes finales de la nueva salida, sin auto-hash circular.
    write_json(outputs / "replay_manifest.json", {"archive_sha256": ARCHIVE_SHA256,
        "files": {p.relative_to(outputs).as_posix(): sha(p.read_bytes())
                  for p in sorted(outputs.rglob("*")) if p.is_file()}})
    return outputs


if __name__ == "__main__":
    main()
