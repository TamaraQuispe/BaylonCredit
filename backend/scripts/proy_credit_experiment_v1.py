"""Experimento PROY P0-05: SVM, KNN, arbol y AdaBoost sobre DEV, con FINAL cerrado.

Entrena 25 modelos y los dos Dummy sobre las 534 filas DEV ya etiquetadas, usando
los folds guardados (3 externos disjuntos por cliente y los internos de calibracion
del SVM). La seleccion es por F2 OOF y se congela con hashes antes de cualquier
contacto con FINAL.

Este runner **no** puede generar ni puntuar la cohorte FINAL: la puerta exige un
paso separado de autorizacion que no forma parte de esta entrega. Asi el test no
se consulta hasta congelar el ganador, que es exactamente lo que se hace aqui.

Uso:
    python scripts/proy_credit_experiment_v1.py \
        --development-dir entregables/PROY_Grupo2/materiales/development \
        --protocol docs/PROY_P0-05_MODEL_PROTOCOL.json \
        --output-dir academic/proy-p05
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import AdaBoostClassifier
from sklearn.impute import SimpleImputer
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.ml import proy_contract  # noqa: E402
from app.ml.features import FEATURE_NAMES  # noqa: E402
from scripts.academic_credit_grouped_cv import metrics, positive_scores  # noqa: E402

VERSION = "proy-credit-experiment-v1"
PROTOCOL_VERSION = "proy-credit-model-protocol-1"
MODEL_FAMILIES = ("svm", "knn", "tree", "adaboost")
BASELINES = ("dummy_most_frequent", "dummy_constant_1")
RANDOM_STATE = 42
FINAL_AUTHORIZATION = "PROY_FINAL_AUTHORIZATION.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def load_json(path: Path):
    return json.loads(path.read_bytes())


def actual_runtime() -> dict:
    return {
        "python": platform.python_version(),
        "sklearn": version("scikit-learn"),
        "numpy": np.__version__,
        "joblib": version("joblib"),
    }


def validate_protocol(protocol: dict) -> None:
    """Rechaza cualquier protocolo que no sea el declarado, sin sustituir defaults."""
    if protocol["version"] != PROTOCOL_VERSION:
        raise ValueError(f"Protocolo no soportado: {protocol['version']}")
    if protocol["feature_names"] != FEATURE_NAMES:
        raise ValueError("El orden de features del protocolo no coincide con app.ml.features")
    if list(FEATURE_NAMES) != list(proy_contract.FEATURE_NAMES_PROY):
        raise ValueError("app.ml.features y proy_contract declaran ordenes distintos")
    for key in ("frozen_inputs", "development", "cv", "candidate_grid", "selection"):
        if key not in protocol:
            raise ValueError(f"Falta la seccion obligatoria '{key}'")
    if set(protocol["candidate_grid"]) != set(MODEL_FAMILIES):
        raise ValueError("La grilla debe declarar exactamente svm, knn, tree y adaboost")
    if tuple(protocol["baselines"]) != BASELINES:
        raise ValueError("El protocolo debe declarar los dos Dummy")
    if protocol["candidate_grid"]["knn"]["n_neighbors"] != [1, 3, 5, 7, 9]:
        raise ValueError("KNN debe declarar k = 1, 3, 5, 7, 9")
    if protocol["candidate_grid"]["adaboost"]["n_estimators"] != [50, 400]:
        raise ValueError("AdaBoost debe declarar 50 y 400 rondas")
    thresholds = protocol["thresholds"]
    if thresholds != sorted(thresholds) or not all(0 < t < 1 for t in thresholds):
        raise ValueError("Los umbrales deben ser crecientes y estar en (0, 1)")
    if protocol["selection"]["minimum_precision"] is not None:
        raise ValueError("Este protocolo no fija piso de precision; es decision de negocio")
    if protocol["final_cohort"]["current_status"].startswith("CERRADA") is False:
        raise ValueError("El protocolo debe declarar FINAL cerrado")
    if protocol["development"]["rows"] != 534 or protocol["development"]["clients"] != 24:
        raise ValueError("El protocolo declara un DEV distinto al disponible")


def validate_runtime(protocol: dict) -> dict:
    actual = actual_runtime()
    expected = protocol["runtime"]
    for key in ("sklearn", "numpy", "joblib"):
        if actual[key] != expected[key]:
            raise ValueError(f"Runtime distinto en {key}: {actual[key]} != {expected[key]}")
    if tuple(actual["python"].split(".")[:2]) != tuple(expected["python"].split(".")[:2]):
        raise ValueError(f"Python incompatible: {actual['python']} vs {expected['python']}")
    return actual


def verify_inputs(development: Path, protocol: dict) -> dict:
    files = {
        "development_known_csv_sha256": development / "development_known.csv",
        "planned_folds_sha256": development / "planned_folds.json",
        "development_manifest_sha256": development / "development_manifest.json",
        "effective_protocol_sha256": development / "effective_protocol.json",
    }
    found = {}
    for key, path in files.items():
        digest = sha256(path)
        if digest != protocol["frozen_inputs"][key]:
            raise ValueError(f"{path.name} no coincide con el SHA del protocolo")
        found[key] = digest
    return found


def read_development(development: Path, folds: dict) -> tuple[list[dict], np.ndarray, np.ndarray]:
    rows = []
    with (development / "development_known.csv").open(newline="", encoding="utf-8") as stream:
        for raw in csv.DictReader(stream):
            row = {"loan_id": raw["loan_id"], "client_id": raw["client_id"]}
            for name in FEATURE_NAMES:
                value = raw[name].strip()
                row[name] = None if value in ("", "NA", "null", "None") else float(value)
            row["late_payment"] = int(raw["late_payment"])
            rows.append(row)
    if [row["loan_id"] for row in rows] != folds["known_row_ids"]:
        raise ValueError("El CSV DEV no conserva el orden de known_row_ids")
    x = np.asarray(
        [[np.nan if row[name] is None else row[name] for name in FEATURE_NAMES] for row in rows],
        dtype=float,
    )
    y = np.asarray([row["late_payment"] for row in rows], dtype=int)
    if x.shape != (len(rows), len(FEATURE_NAMES)) or np.isinf(x).any():
        raise ValueError("Matriz DEV invalida")
    if not set(y.tolist()) <= {0, 1}:
        raise ValueError("Etiquetas DEV fuera de {0, 1}")
    groups = np.asarray([row["client_id"] for row in rows])
    if len(groups) != 534 or len(set(groups)) != 24:
        raise ValueError("El DEV disponible no coincide con el protocolo")
    return rows, x, y


def fold_pairs(plan: dict) -> list[tuple[np.ndarray, np.ndarray]]:
    pairs = [
        (np.asarray(fold["train_indices"]), np.asarray(fold["validation_indices"]))
        for fold in plan["folds"]
    ]
    coverage = np.zeros(max(int(i.max()) for _, i in pairs) + 1, dtype=int)
    for _train, valid in pairs:
        coverage[valid] += 1
    if not np.all(coverage == 1):
        raise ValueError("Los folds guardados no cubren cada fila exactamente una vez")
    return pairs


def local_inner(inner: dict, parent: np.ndarray) -> list[tuple[np.ndarray, np.ndarray]]:
    """Los indices guardados son globales; sklearn los espera locales al entrenamiento."""
    positions = {int(global_index): local for local, global_index in enumerate(parent)}
    pairs = []
    for fold in inner["folds"]:
        train = np.asarray([positions[i] for i in fold["train_indices"]])
        valid = np.asarray([positions[i] for i in fold["validation_indices"]])
        if set(train.tolist()) & set(valid.tolist()):
            raise ValueError("Los folds internos se solapan")
        pairs.append((train, valid))
    if len(pairs) != inner["n_splits"]:
        raise ValueError("Cantidad de folds internos distinta a la declarada")
    return pairs


def build_candidates(protocol: dict) -> list[dict]:
    grid = protocol["candidate_grid"]
    candidates = [
        {
            "family": "svm",
            "C": c,
            "class_weight": weight,
            "kernel": grid["svm"]["kernel"],
            "probability": grid["svm"]["probability"],
            "random_state": RANDOM_STATE,
        }
        for c in grid["svm"]["C"]
        for weight in grid["svm"]["class_weight"]
    ]
    candidates.extend(
        {
            "family": "knn",
            "n_neighbors": k,
            "weights": grid["knn"]["weights"],
            "metric": grid["knn"]["metric"],
            "p": grid["knn"]["p"],
        }
        for k in grid["knn"]["n_neighbors"]
    )
    candidates.extend(
        {
            "family": "tree",
            "max_depth": depth,
            "min_samples_leaf": leaf,
            "class_weight": weight,
            "random_state": RANDOM_STATE,
        }
        for depth in grid["tree"]["max_depth"]
        for leaf in grid["tree"]["min_samples_leaf"]
        for weight in grid["tree"]["class_weight"]
    )
    candidates.extend(
        {
            "family": "adaboost",
            "n_estimators": rounds,
            "learning_rate": grid["adaboost"]["learning_rate"],
            "random_state": RANDOM_STATE,
        }
        for rounds in grid["adaboost"]["n_estimators"]
    )
    return candidates


def fit_model(params: dict, x, y, groups, inner) -> object:
    family = params["family"]
    options = {key: value for key, value in params.items() if key != "family"}
    if family == "svm":
        classifier = SVC(**options)
    elif family == "knn":
        classifier = KNeighborsClassifier(**options)
    elif family == "tree":
        classifier = DecisionTreeClassifier(**options)
    elif family == "adaboost":
        classifier = AdaBoostClassifier(**options)
    elif family == "dummy_most_frequent":
        classifier = DummyClassifier(strategy="most_frequent")
    elif family == "dummy_constant_1":
        classifier = DummyClassifier(strategy="constant", constant=1)
    else:
        raise ValueError(f"Familia desconocida: {family}")
    if np.isnan(np.asarray(x)).all(axis=0).any():
        raise ValueError("Feature completamente vacia en entrenamiento")
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("classifier", classifier),
        ]
    )
    if family == "svm":
        if options.get("probability") is not False or inner is None or len(inner) != 3:
            raise ValueError("El SVM exige margen lineal y calibracion sigmoide guardada")
        model = CalibratedClassifierCV(estimator=model, cv=inner, method="sigmoid", ensemble=False)
    model.fit(x, y)
    return model


def oof_scores(params: dict, x, y, groups, folds, inner_folds) -> np.ndarray:
    scores = np.full(len(y), np.nan)
    coverage = np.zeros(len(y), dtype=int)
    for number, (train, valid) in enumerate(folds):
        if set(groups[train]) & set(groups[valid]):
            raise ValueError("Fuga de cliente en los folds externos")
        if len(np.unique(y[train])) != 2 or len(np.unique(y[valid])) != 2:
            raise ValueError("Cada fold requiere ambas clases")
        inner = inner_folds[number] if params["family"] == "svm" else None
        model = fit_model(params, x[train], y[train], groups[train], inner)
        scores[valid] = positive_scores(model, x[valid])
        coverage[valid] += 1
    if not np.all(coverage == 1) or not np.isfinite(scores).all():
        raise ValueError("El OOF debe cubrir cada fila exactamente una vez")
    return scores


def rank(entry: dict) -> tuple:
    value = entry["metrics"]
    return (
        value["f2"],
        value["recall"],
        value["precision"],
        value["f1"],
        -entry["candidate_index"],
        -round(abs(entry["threshold"] - 0.5), 12),
        -entry["threshold"],
    )


def describe(model, family: str) -> dict:
    if family in ("svm", "tree"):
        from scripts.academic_credit_grouped_cv import interpretation

        return interpretation(model, family)
    if family == "adaboost":
        classifier = model.named_steps["classifier"]
        return {
            "feature_importances_scaled": dict(
                zip(FEATURE_NAMES, classifier.feature_importances_.tolist(), strict=True)
            ),
            "base_estimator": "DecisionTreeClassifier(max_depth=1)",
            "caveat": (
                "Importancias sobre features estandarizadas; describen el ensamble, "
                "no causalidad."
            ),
        }
    if family == "knn":
        return {
            "reference_rows": len(model.named_steps["classifier"]._fit_X),
            "caveat": (
                "KNN no ofrece coeficientes; el vecindario depende de la escala "
                "estandarizada."
            ),
        }
    return {"caveat": "Referencia Dummy, no un modelo de riesgo entrenado"}


def final_test_status(output: Path) -> dict:
    """FINAL solo puede abrirse con un paso de autorizacion que esta entrega no incluye."""
    freeze = output / "freeze_before_final.json"
    if not freeze.exists():
        return {
            "status": "closed",
            "reason": "No existe freeze_before_final.json: la seleccion aun no esta congelada.",
        }
    frozen = load_json(freeze)
    if frozen["final_generation_calls"] or frozen["final_prediction_calls"]:
        raise ValueError("El freeze declara contacto previo con FINAL; se rechaza la evidencia")
    manifest = load_json(output / "artifact_manifest.json")
    for name, digest in manifest.items():
        if sha256(output / name) != digest:
            raise ValueError(f"{name} cambio despues del freeze")
    return {
        "status": "closed",
        "reason": (
            "Seleccion congelada con hashes. FINAL exige la cohorte nueva del protocolo y el "
            f"archivo {FINAL_AUTHORIZATION}, que no forma parte de esta entrega."
        ),
        "reserved_cohort": {"seed": "declarado en el protocolo", "generated": False},
    }


def run(development: Path, protocol_path: Path, output: Path) -> dict:
    if not __debug__:
        raise RuntimeError("La validacion exige assertions activas")
    development, protocol_path, output = (
        path.resolve() for path in (development, protocol_path, output)
    )
    if output.exists():
        raise ValueError("El directorio de salida debe ser nuevo; no se reutiliza evidencia")
    protocol = load_json(protocol_path)
    validate_protocol(protocol)
    runtime = validate_runtime(protocol)
    inputs = verify_inputs(development, protocol)
    folds_plan = load_json(development / "planned_folds.json")
    rows, x, y = read_development(development, folds_plan)
    groups = np.asarray([row["client_id"] for row in rows])
    outer = fold_pairs(folds_plan["outer"])
    inner_folds = [local_inner(inner, train) for inner, (train, _) in
                   zip(folds_plan["inner_sigmoid_by_outer_train"], outer, strict=True)]
    inner_full = local_inner(folds_plan["inner_sigmoid_full_train"], np.arange(len(y)))

    output.mkdir()
    write_json(output / "provenance.json", {
        "recorded_utc": datetime.now(UTC).isoformat(),
        "version": VERSION,
        "protocol_sha256": sha256(protocol_path),
        "input_sha256": inputs,
        "runtime": runtime,
        "code_sha256": {
            str(path.relative_to(BACKEND)): sha256(path)
            for path in (Path(__file__), BACKEND / "app/ml/features.py",
                         BACKEND / "app/ml/proy_contract.py")
        },
        "development": {"rows": len(rows), "clients": len(set(groups)),
                        "class_counts": {"0": int((y == 0).sum()), "1": int((y == 1).sum())}},
        "authorization": {"stage": "dev_only_selection", "final_contacted": False},
    })

    candidates = build_candidates(protocol)
    expected = protocol["candidate_count"]
    if len(candidates) != expected["trained_models"]:
        raise ValueError(
            f"La grilla produjo {len(candidates)} modelos, no {expected['trained_models']}"
        )

    search, entries = [], []
    for index, params in enumerate(candidates):
        scores = oof_scores(params, x, y, groups, outer, inner_folds)
        results = [
            {
                "family": params["family"],
                "candidate_index": index,
                "params": params,
                "threshold": threshold,
                "metrics": metrics(y, scores, threshold),
            }
            for threshold in protocol["thresholds"]
        ]
        entries.extend(results)
        search.append({
            "candidate_index": index,
            "params": params,
            "threshold_results": results,
            "oof_probabilities": scores.tolist(),
        })
    baselines = {}
    for name in BASELINES:
        scores = oof_scores({"family": name}, x, y, groups, outer, inner_folds)
        baselines[name] = {
            "params": {"family": name},
            "threshold": protocol["baseline_threshold"],
            "metrics": metrics(y, scores, protocol["baseline_threshold"]),
            "oof_probabilities": scores.tolist(),
        }
    write_json(output / "cv_search.json", {
        "candidates": search,
        "baselines": baselines,
        "study_loan_ids": [row["loan_id"] for row in rows],
        "selection_optimism": protocol["reporting"]["oof_limit"],
    })

    families = {
        name: max([entry for entry in entries if entry["family"] == name], key=rank)
        for name in MODEL_FAMILIES
    }
    winner = max(families.values(), key=rank)
    write_json(output / "family_winners.json", {"families": families, "global_winner": winner})

    choices = {**families, **baselines}
    reports, artifacts = {}, {}
    for name, choice in choices.items():
        model = fit_model(choice["params"], x, y, groups, inner_full)
        path = output / f"{name}.joblib"
        joblib.dump(model, path)
        artifacts[name] = path.name
        reports[name] = {
            "params": choice["params"],
            "threshold": choice["threshold"],
            "oof": choice["metrics"],
            "train_descriptive": metrics(y, positive_scores(model, x), choice["threshold"]),
            "artifact": path.name,
            "interpretation": describe(model, name),
        }
    (output / "selected_model.joblib").write_bytes(
        (output / artifacts[winner["family"]]).read_bytes()
    )

    selection = {
        "version": VERSION,
        "feature_names": FEATURE_NAMES,
        "frozen_utc": datetime.now(UTC).isoformat(),
        "families": families,
        "global_winner": winner,
        "baselines": {
            name: {
                "params": item["params"],
                "threshold": item["threshold"],
                "metrics": item["metrics"],
            }
            for name, item in baselines.items()
        },
        "beat_baselines": {
            name: {
                "f2_strictly_higher": winner["metrics"]["f2"] > baselines[name]["metrics"]["f2"],
                "recall_strictly_higher": (
                    winner["metrics"]["recall"] > baselines[name]["metrics"]["recall"]
                ),
                "baseline_f2": baselines[name]["metrics"]["f2"],
            }
            for name in BASELINES
        },
        "research_only": True,
    }
    write_json(output / "frozen_selection.json", selection)
    manifest = {
        name: sha256(output / name)
        for name in (*artifacts.values(), "selected_model.joblib", "frozen_selection.json")
    }
    write_json(output / "artifact_manifest.json", manifest)
    write_json(output / "freeze_before_final.json", {
        "version": VERSION,
        "frozen_utc": selection["frozen_utc"],
        "files": {path.name: sha256(path) for path in sorted(output.iterdir()) if path.is_file()},
        "final_generation_calls": 0,
        "final_prediction_calls": 0,
    })
    status = final_test_status(output)

    report = {
        "version": VERSION,
        "origen": "simulado",
        "research_only": True,
        "business_approval": False,
        "feature_names": FEATURE_NAMES,
        "provenance": load_json(output / "provenance.json"),
        "development": {
            "rows": len(rows),
            "clients": len(set(groups)),
            "class_counts": {"0": int((y == 0).sum()), "1": int((y == 1).sum())},
            "outer_folds": folds_plan["outer"]["n_splits"],
            "fold_seed": folds_plan["outer"]["seed"],
        },
        "candidates": {
            "families": {name: sum(1 for c in candidates if c["family"] == name)
                         for name in MODEL_FAMILIES},
            "total": len(candidates),
            "baselines": list(BASELINES),
        },
        "selection": selection,
        "models": reports,
        "final_test": status,
        "artifact_sha256": manifest,
        "limits": protocol["limits"],
    }
    write_json(output / "proy_p0_05_report.json", report)
    return report


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development-dir", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--status-only", type=Path,
                        help="Muestra el estado de la puerta FINAL para un directorio ya congelado")
    args = parser.parse_args(argv)
    if args.status_only is not None:
        print(json.dumps(final_test_status(args.status_only), indent=2, allow_nan=False))
        return
    report = run(args.development_dir, args.protocol, args.output_dir)
    winner = report["selection"]["global_winner"]
    print(json.dumps({
        "version": VERSION,
        "global_winner": {"family": winner["family"], "params": winner["params"],
                          "threshold": winner["threshold"], "oof_f2": winner["metrics"]["f2"]},
        "families": {name: {
            "params": entry["params"], "threshold": entry["threshold"],
            "oof_f2": entry["metrics"]["f2"], "oof_recall": entry["metrics"]["recall"],
            "oof_precision": entry["metrics"]["precision"],
        } for name, entry in report["selection"]["families"].items()},
        "baselines": {name: {"oof_f2": item["metrics"]["f2"],
                             "oof_recall": item["metrics"]["recall"]}
                      for name, item in report["selection"]["baselines"].items()},
        "final_test": report["final_test"]["status"],
    }, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
