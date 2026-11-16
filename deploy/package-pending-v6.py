"""Package frozen V6 evidence and replay its fixed procedure offline, without tuning."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

IMAGE = "bayloncredit-api-training-test:latest"
TEMP = Path("/private/var/folders/sx/_6ljw37n2_j9hk2f_vtqplj40000gn/T/opencode")
DOWNLOADS = Path.home() / "Downloads"
MODELS = ("tree", "svm", "most_frequent", "constant_1")
SPLITS = ("train", "oof", "final")
VERSION = "academic-owner-pending-v6"
PROTOCOL_SHA = "eb7fcd39f69be0115895cbb43b6d84e4488535646108bd6f21381d0fb1607923"
RUNNER_SHA = "60f0ed75e2dec6175232776e8820369e53baf1944819d272f3bcef484e0aae6d"
DEV_NAMES = frozenset([
    "APF3_OWNER_ANCHORS_V4.json", "APF3_OWNER_REVIEW_V5.json",
    "APF3_PENDING_V6_DATA_PROTOCOL.json", "PND6-D1_transactions.json",
    "PND6-D2_transactions.json", "README.md", "data_revision_report.json",
    "desarrollo.csv", "desarrollo_etiquetado.csv", "development_audits.json",
    "manifest.json", "preparation_plan.json",
])
PROTO_NAMES = frozenset([
    "APF3_OWNER_ANCHORS_V4.json", "APF3_OWNER_REVIEW_V5.json",
    "APF3_PENDING_V6_DATA_PROTOCOL.json", "APF3_PENDING_V6_MODEL_PROTOCOL.json",
    "README.md", "calidad-dev-v6.csv", "manifest.json", "pliegues-planificados.json",
    "preparation_plan.json", "summaryauditoria-dev-v6.json",
])
ARTIFACTS = frozenset([*(f"{m}.joblib" for m in (*MODELS, "selected_model")),
                       "frozen_selection.json", "protocol.json"])
DECISIONS = frozenset([
    *[f"inputdev_{n}" for n in DEV_NAMES], *[f"snapshot_{n}" for n in PROTO_NAMES],
    "protocol.json", "data_protocol.json", "calibration.json", "owner_review.json",
    "fold_audit.json", "development_gate.json", "inputdevmanifest.json",
    "historical_snapshot.json", "development_audits.json", "inputdev_inventory.json",
    "snapshot_inventory.json", "development_rows.json", "development_study_rows.json",
    "development_transactions.json", "development_rows.csv", "provenance.json",
    "cv_search.json", "training_reports.json",
    *[f"{m}.joblib" for m in (*MODELS, "selected_model")],
])
FREEZE_FILES = DECISIONS | {"frozen_selection.json", "artifact_manifest.json"}
VOLATILE = {"provenance.json", "frozen_selection.json", "freeze_before_final.json",
            "artifact_manifest.json", "pending_v6_report.json"}
PROBE = """
import importlib.metadata as m, json, platform, sys
from pathlib import Path
print(json.dumps({'python': platform.python_version(), 'prefix': sys.prefix,
 'base_prefix': sys.base_prefix, 'sys_path': sys.path,
 'venv_config': Path(sys.prefix, 'pyvenv.cfg').read_text(),
 'packages': {d.metadata['Name']: {'version': d.version,
 'location': str(d.locate_file(''))} for d in m.distributions()}}))
"""
STATE_PROBE = """
import hashlib, json, joblib
import numpy as np
from pathlib import Path
def state(v):
    if v is None or isinstance(v, (str, bool, int)): return v
    if isinstance(v, float): return {'float_hex': v.hex()}
    if isinstance(v, np.ndarray):
        return {'dtype': str(v.dtype), 'shape': list(v.shape), 'values': state(v.tolist())}
    if isinstance(v, np.generic): return state(v.item())
    if isinstance(v, np.dtype): return {'numpy_dtype': str(v)}
    if isinstance(v, type): return {'type': v.__module__ + '.' + v.__qualname__}
    if isinstance(v, dict): return {str(k): state(x) for k,x in sorted(v.items())}
    if isinstance(v, (list, tuple)): return {type(v).__name__: [state(x) for x in v]}
    if isinstance(v, bytes): return {'bytes_hex': v.hex()}
    name = type(v).__module__ + '.' + type(v).__qualname__
    if hasattr(v, '__dict__'): return {'class': name, 'state': state(vars(v))}
    if hasattr(v, '__getstate__'): return {'class': name, 'state': state(v.__getstate__())}
    raise TypeError('Unsupported learned state: ' + name)
result = {}
for name in ('tree', 'svm', 'most_frequent', 'constant_1', 'selected_model'):
    paths = [Path('/output', f, name + '.joblib') for f in ('experimento', 'reproduccion')]
    data = [p.read_bytes() for p in paths]
    equal = data[0] == data[1]
    item = {'binary_equal': equal, 'binary_sha256': [hashlib.sha256(x).hexdigest() for x in data],
            'sizes': [len(x) for x in data]}
    if not equal:
        states = [state(joblib.load(p)) for p in paths]
        item['learned_state_equal'] = states[0] == states[1]
        item['state_sha256'] = [hashlib.sha256(json.dumps(x, sort_keys=True,
            allow_nan=False).encode()).hexdigest() for x in states]
        offset = next((i for i,(a,b) in enumerate(zip(*data)) if a != b), min(map(len,data)))
        item['first_binary_mismatch'] = offset
        item['mismatch_context_hex'] = [x[max(0,offset-16):offset+32].hex() for x in data]
    result[name] = item
print(json.dumps(result, allow_nan=False))
"""
WRAPPER = (Path(__file__).with_name("templates") / "pending-v6-entrypoint.py").read_text()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(folder):
    paths = sorted(folder.rglob("*"))
    require(not any(p.is_symlink() for p in paths), f"Symlink in {folder}")
    return {str(p.relative_to(folder)): sha(p) for p in paths if p.is_file()}


def check_hashes(folder, values, names):
    require(set(values) == set(names), f"Manifest keys mismatch: {folder}")
    for name, digest in values.items():
        require(Path(name).name == name and not (folder / name).is_symlink(), "Unsafe path")
        require(sha(folder / name) == digest, f"SHA256 mismatch: {folder / name}")


def validate_artifacts(folder):
    report = load(folder / "pending_v6_report.json")
    selection = load(folder / "frozen_selection.json")
    provenance = load(folder / "provenance.json")
    manifest = load(folder / "artifact_manifest.json")
    frozen = load(folder / "freeze_before_final.json")
    require(set(selection) == {"version", "feature_names", "families", "global_winner",
                              "baselines", "decision_sha256", "research_only"}, "Selection keys")
    require(set(frozen) == {"version", "frozen_utc", "files", "final_generation_calls",
                            "final_prediction_calls"}, "Freeze keys")
    require(frozen["final_generation_calls"] == frozen["final_prediction_calls"] == 0,
            "Invalid pre-final freeze")
    require(report["selection"] == selection and report["provenance"] == provenance,
            "Report selection/provenance mismatch")
    require(report["artifact_sha256"] == manifest, "Report manifest mismatch")
    check_hashes(folder, manifest, ARTIFACTS)
    check_hashes(folder, selection["decision_sha256"], DECISIONS)
    check_hashes(folder, frozen["files"], FREEZE_FILES)
    check_hashes(folder, provenance["input_sha256"], {
        *[f"inputdev_{n}" for n in DEV_NAMES], *[f"snapshot_{n}" for n in PROTO_NAMES],
        "protocol.json", "data_protocol.json", "calibration.json", "owner_review.json",
        "fold_audit.json", "development_gate.json", "inputdevmanifest.json",
        "historical_snapshot.json", "development_audits.json"})
    require(sha(folder / "protocol.json") == PROTOCOL_SHA, "Protocol drift")
    require(selection["version"] == report["version"] == frozen["version"] == VERSION,
            "Version mismatch")
    require(selection["feature_names"] == report["feature_names"]
            == load(folder / "protocol.json")["feature_names"], "Feature mismatch")
    require(set(selection["families"]) == {"tree", "svm"}
            and set(selection["baselines"]) == {"most_frequent", "constant_1"}
            and set(report["models"]) == set(MODELS), "Family keys")
    winner = selection["global_winner"]
    require(winner == selection["families"][winner["family"]], "Winner mismatch")
    require(manifest["selected_model.joblib"] == manifest[winner["family"] + ".joblib"],
            "Selected artifact mismatch")
    return True


def validate_environment(env, expected):
    require(env["python"] == expected["python"], "Python runtime drift")
    for name, version in expected.items():
        if name != "python":
            distribution = "scikit-learn" if name == "sklearn" else name
            require(env["packages"][distribution]["version"] == version,
                    f"Runtime drift: {distribution}")
    require(env["prefix"] == "/repro-env/venv" and env["prefix"] != env["base_prefix"]
            and "include-system-site-packages = false" in env["venv_config"].lower()
            and all(p["location"].startswith("/repro-env/venv/")
                    for p in env["packages"].values())
            and all(p.startswith("/repro-env/venv/") for p in env["sys_path"]
                    if "site-packages" in p or "dist-packages" in p), "Unclean venv")
    require(not any("pydantic" in n.lower() for n in env["packages"]), "Unexpected Pydantic")
    return True


def probe(venv, image, expected):
    command = ["docker", "run", "--rm", "--network", "none", "--read-only", "--mount",
               f"type=bind,src={venv},dst=/repro-env,readonly", "--entrypoint",
               "/repro-env/venv/bin/python", image, "-I", "-B", "-c", PROBE]
    env = json.loads(subprocess.run(command, check=True, text=True, capture_output=True).stdout)
    validate_environment(env, expected)
    env["image"] = json.loads(subprocess.run(["docker", "image", "inspect", image],
                             check=True, text=True, capture_output=True).stdout)[0]["Id"]
    env["clean_venv"] = True
    return env


def docker_base(root, venv, image):
    command = ["docker", "run", "--rm", "--network", "none", "--read-only",
               "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
               "--tmpfs", "/tmp:rw,noexec,nosuid", "--workdir", "/app", "--env", "HOME=/tmp"]
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                 "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        command += ["--env", name + "=1"]
    for src, dst, readonly in (
        (root, "/output", False), (root / "codigo", "/app", True),
        (root / "fuentes-dev", "/development", True),
        (root / "protocolo-modelado", "/protocol", True),
        (root / "experimento", "/output/experimento", True),
        (root / "datos", "/output/datos", True), (venv, "/repro-env", True),
    ):
        command += ["--mount", f"type=bind,src={src},dst={dst}" + (",readonly" if readonly else "")]
    return command + ["--entrypoint", "/repro-env/venv/bin/python", image, "-I", "-B"]


def normalized_selection(value):
    result = copy.deepcopy(value)
    result["decision_sha256"].pop("provenance.json")
    # Model serialization hashes are validated locally, with full state compared separately.
    for name in result["decision_sha256"]:
        if name.endswith(".joblib"):
            result["decision_sha256"][name] = "validated-separately"
    return result


def normalized_report(value):
    result = copy.deepcopy(value)
    result["provenance"].pop("recorded_utc")
    result["selection"] = normalized_selection(result["selection"])
    require(set(result["artifact_sha256"]) == ARTIFACTS, "Report artifact keys")
    result["artifact_sha256"] = sorted(result["artifact_sha256"])
    return result


def compare_reports(expected, actual):
    return {
        "full_report_except_time_and_serialization": normalized_report(expected) == normalized_report(actual),
        "selection": normalized_selection(expected["selection"]) == normalized_selection(actual["selection"]),
        "raw": {f"{m}/{s}": expected["models"][m][s] == actual["models"][m][s]
                for m in MODELS for s in SPLITS},
        "policy": {f"{m}/{s}": expected["models"][m]["review_policy"][s]
                   == actual["models"][m]["review_policy"][s] for m in MODELS for s in SPLITS},
        "illustrative": expected["illustrative_inference"] == actual["illustrative_inference"],
    }


def all_equal(value):
    return all(all_equal(v) if isinstance(v, dict) else v is True for v in value.values())


def study_rows(experiment):
    return {
        "desarrollo.csv": load(experiment / "development_study_rows.json"),
        "final.csv": [r for r in load(experiment / "final_transactions.json")["rows"]
                      if r["phase"] == "study"],
    }


def summary(report, experiment):
    return {
        "version": VERSION, "research_only": True, "business_approval": False,
        "feature_names": report["feature_names"],
        "constant_features": load(experiment / "protocol.json")["feature_policy"]["constant_features"],
        "duplicate_features": "completed_sales == paid_credits",
        "development": {k: v for k, v in report["development"].items() if k != "audits"},
        "final": {k: v for k, v in report["final"].items() if k != "audit"},
        "audit_summary": [{k: audit[k] for k in (
            "replica_id", "clients", "requests", "all_loans", "warmup_loans", "study_loans",
            "study_label_counts", "pending_grants", "pending_policy_pass", "hard_constraints_pass",
            "coherence_accepted", "coherence_status", "legacy_grant_scale_flag",
            "mean_weekly_study_requests", "mean_weekly_study_request_clients",
            "mean_weekly_study_grants", "mean_weekly_study_grant_clients",
        ) if k in audit} for audit in [
            *report["development"]["audits"], report["final"]["audit"]]],
        "study_counts": {n: {"study": len(rows), "known": sum(r["late_payment"] is not None for r in rows),
                             "unknown": sum(r["late_payment"] is None for r in rows),
                             "columns": len(rows[0]),
                             "class_0": sum(r["late_payment"] == 0 for r in rows),
                             "class_1": sum(r["late_payment"] == 1 for r in rows)}
                         for n, rows in study_rows(experiment).items()},
        "global_winner": {k: report["selection"]["global_winner"][k] for k in
                          ("family", "candidate_index", "params", "threshold", "metrics")},
        "models": {m: {"params": report["models"][m]["params"],
                        "threshold": report["models"][m]["threshold"],
                        "raw": {s: report["models"][m][s] for s in SPLITS},
                        "policy": {s: {k: v for k, v in report["models"][m]["review_policy"][s].items()
                                       if k != "daily"} for s in SPLITS}}
                   for m in MODELS},
        "baseline_comparison": report["baseline_comparison"],
        "illustrative_inference": report["illustrative_inference"],
        "source": {k: report["provenance"]["source_anchors"][k] for k in
                   ("source_quality", "reviewed_annotations", "evaluable", "late", "unknown_included")},
        "limits": report["limits"],
        "reproduction_interpretation": "Fixed-procedure replay, not a new independent test; no tuning",
        "web": "Current repository web laboratory is V4, not V6; no web bundle included",
    }


def package(args):
    root = args.root
    require(root.is_dir(), "Root parent must already exist")
    targets = ("codigo", "datos", "experimento", "fuentes-dev", "protocolo-modelado",
               "manifest-codepack.json", "manifest-paquete.json", "requirements.txt",
               "reproducir-v6.py", "README.md", "APF3_TD_Grupo2_ML_Innovacion.py", "resumen-v6.json",
               "v6_policy.py")
    for name in (*targets, "reproduccion"):
        require(not (root / name).exists(), f"Refusing overwrite: {root / name}")
    before = inventory(args.experiment)
    require(len(before) == 57, "Expected 57 original experiment files")
    validate_artifacts(args.experiment)
    code_manifest = load(args.code.with_name(args.code.name + "-manifest.json"))
    require(inventory(args.code) == code_manifest["files"] and len(code_manifest["files"]) == 21,
            "Code package drift")
    provenance = load(args.experiment / "provenance.json")
    for name, digest in provenance["code_sha256"].items():
        require(sha(args.code / name) == digest, f"Frozen code drift: {name}")
    require(sha(args.code / "scripts/academic_credit_pending_v6.py") == RUNNER_SHA, "Runner drift")
    for source, names, prefix in ((args.development, DEV_NAMES, "inputdev_"),
                                  (args.protocol, PROTO_NAMES, "snapshot_")):
        check_hashes(source, inventory(source), names)
        for name in names:
            require(sha(source / name) == before[prefix + name], f"Frozen source drift: {name}")
        saved = load(source / "manifest.json")["files"]
        check_hashes(source, saved, names - {"manifest.json"})
    env = probe(args.venv_parent, args.image, provenance["runtime"])
    for source, target in ((args.experiment, "experimento"), (args.code, "codigo"),
                            (args.development, "fuentes-dev"), (args.protocol, "protocolo-modelado")):
        shutil.copytree(source, root / target)
        require(inventory(source) == inventory(root / target), f"Copy mismatch: {target}")
    shutil.copyfile(args.code.with_name(args.code.name + "-manifest.json"), root / "manifest-codepack.json")
    (root / "datos").mkdir()
    for name, source in (("desarrollo.csv", "development_rows.csv"),
                         ("desarrollo_etiquetado.csv", "inputdev_desarrollo_etiquetado.csv"),
                         ("final.csv", "final_rows.csv")):
        shutil.copyfile(root / "experimento" / source, root / "datos" / name)
    (root / "requirements.txt").write_text("# Python==" + env["python"] + "; Linux; actual clean venv inventory\n"
        + "".join(f"{n}=={p['version']}\n" for n, p in sorted(env["packages"].items())), encoding="utf-8")
    (root / "APF3_TD_Grupo2_ML_Innovacion.py").write_text(WRAPPER, encoding="utf-8")
    shutil.copyfile(Path(__file__).resolve().parents[1] / "backend/app/services/academic_v6_policy.py",
                    root / "v6_policy.py")
    shutil.copyfile(Path(__file__), root / "reproducir-v6.py")
    write(root / "entorno-empaquetado.json", env)
    report = load(root / "experimento/pending_v6_report.json")
    write(root / "resumen-v6.json", summary(report, root / "experimento"))
    manifest = {
        "version": "pending-v6-delivery-1", "original_experiment_path": str(args.experiment),
        "original_experiment_sha256": before,
        "folders": {n: inventory(root / n) for n in
                    ("experimento", "codigo", "datos", "fuentes-dev", "protocolo-modelado")},
        "support_sha256": {n: sha(root / n) for n in targets if (root / n).is_file()},
        "code_source_exception": code_manifest["initializer_exception"],
    }
    require(inventory(args.experiment) == before, "Original changed during packaging")
    write(root / "manifest-paquete.json", manifest)
    write_readme(root)
    print(json.dumps({"packaged": str(root), "study_counts": load(root / "resumen-v6.json")["study_counts"]}, indent=2))


def integrity(root):
    manifest = load(root / "manifest-paquete.json")
    checks = {n: inventory(root / n) == values for n, values in manifest["folders"].items()}
    checks.update({n: sha(root / n) == digest for n, digest in manifest["support_sha256"].items()})
    original = Path(manifest["original_experiment_path"])
    if original.is_dir():
        checks["external_original_unchanged"] = inventory(original) == manifest["original_experiment_sha256"]
    require(all_equal(checks), "Package/source integrity failure")
    return checks


def refresh_support(args):
    """Refresh only owned tooling/summary, never frozen inputs or replay output."""
    root = args.root
    integrity(root)
    manifest = load(root / "manifest-paquete.json")
    shutil.copyfile(Path(__file__), root / "reproducir-v6.py")
    write(root / "resumen-v6.json", summary(
        load(root / "experimento/pending_v6_report.json"), root / "experimento"))
    for name in ("reproducir-v6.py", "resumen-v6.json"):
        manifest["support_sha256"][name] = sha(root / name)
    write(root / "manifest-paquete.json", manifest)
    return verify(args)


def verify(args):
    root = args.root
    checks = {"integrity": integrity(root)}
    for name in ("experimento", "reproduccion"):
        checks[name + "_artifact_chain"] = validate_artifacts(root / name)
    expected, actual = [load(root / n / "pending_v6_report.json") for n in ("experimento", "reproduccion")]
    checks.update(compare_reports(expected, actual))
    expected_files = inventory(root / "experimento")
    checks["output_keys"] = set(expected_files) == set(inventory(root / "reproduccion"))
    checks["exact_file_sha256"] = {n: sha(root / "experimento" / n) == sha(root / "reproduccion" / n)
        for n in expected_files if n not in VOLATILE and not n.endswith(".joblib")}
    env = probe(args.venv_parent, args.image, expected["provenance"]["runtime"])
    write(root / "entorno-verificacion.json", env)
    checks["environment"] = env == load(root / "entorno-empaquetado.json") == load(root / "entorno-reproduccion.json")
    command = docker_base(root, args.venv_parent, env["image"]) + ["-c", STATE_PROBE]
    artifacts = json.loads(subprocess.run(command, check=True, capture_output=True, text=True).stdout)
    require(set(artifacts) == {*MODELS, "selected_model"}, "Artifact probe keys mismatch")
    binary_equal = all(v["binary_equal"] for v in artifacts.values())
    checks["learned_state"] = {m: v["binary_equal"] or v["learned_state_equal"] for m, v in artifacts.items()}
    original_cli, repro_cli = [load(root / f"inferencia-{n}.json") for n in ("original", "reproduccion")]
    checks["inference_cli"] = {
        "original_equals_reproduction": original_cli == repro_cli,
        "equals_frozen_illustration": original_cli == {k: expected["illustrative_inference"][k] for k in original_cli},
        "no_known_label": original_cli["known_label"] is None,
    }
    checks["csv_scope"] = {}
    for name, rows in study_rows(root / "experimento").items():
        with (root / "datos" / name).open(newline="", encoding="utf-8") as stream:
            exported = list(csv.DictReader(stream))
        checks["csv_scope"][name] = exported == [
            {k: "" if v is None else str(v) for k, v in r.items()} for r in rows]
    negative = copy.deepcopy(actual)
    negative["models"]["tree"]["final"]["recall"] += 0.001
    checks["negative_metric_control"] = not all_equal(compare_reports(expected, negative))
    result = {
        "passed": all_equal(checks), "checks": checks, "joblib_binary_equal": binary_equal,
        "binary_serialization_caveat": not binary_equal, "artifact_serialization": artifacts,
        "environment": env, "commands": load(root / "comandos-reproduccion.json"),
        "state_probe_command": command,
        "methods": {
            "metrics": "Exact JSON values, 12 raw and 12 full policy comparisons; no tolerance",
            "selection": "Full selection except provenance timestamp-derived hash and separately checked binary hashes",
            "report": "No generated_utc in V6; exclude only provenance.recorded_utc and derived artifact hashes",
            "state": "Binary equality first; otherwise recursive full class/vars/native state, dtype/shape/values, float.hex; no tolerance",
            "integrity": "Strict complete artifact/decision/freeze/input keys and every local SHA before deserialization",
            "replay": "One fixed-procedure replay; not a new independent test; no tuning or new seed",
        },
        "results": summary(actual, root / "reproduccion"),
    }
    write(root / "estado-artefactos.json", artifacts)
    write(root / "verificacion-reproduccion.json", result)
    require(result["passed"], "Reproduction mismatch; see verificacion-reproduccion.json")
    write_readme(root)
    print(json.dumps({"passed": True, "raw": 12, "policy": 12,
                      "exact_file_hashes": len(checks["exact_file_sha256"]),
                      "joblib_binary_equal": binary_equal, "inference": original_cli}, indent=2))
    return result


def reproduce(args):
    root = args.root
    require(not (root / "reproduccion").exists(), "Reproduction output must be nonexisting")
    integrity(root)
    validate_artifacts(root / "experimento")
    env = probe(args.venv_parent, args.image, load(root / "experimento/provenance.json")["runtime"])
    require(env == load(root / "entorno-empaquetado.json"), "Runtime changed after packaging")
    write(root / "entorno-reproduccion.json", env)
    base = docker_base(root, args.venv_parent, env["image"])
    runner = "/app/scripts/academic_credit_pending_v6.py"
    commands = [base + [runner, "--development-dir", "/development", "--protocol-dir", "/protocol",
                        "--output-dir", "/output/reproduccion"]]
    for label, folder in (("original", "experimento"), ("reproduccion", "reproduccion")):
        require(not (root / f"inferencia-{label}.json").exists(), "Inference output must be fresh")
        commands.append(base + [runner, "--predict-artifact-dir", f"/output/{folder}",
            "--input-json", "/output/experimento/illustrative_input.json", "--output-json",
            f"/output/inferencia-{label}.json"])
    write(root / "comandos-reproduccion.json", commands)
    for index, command in enumerate(commands):
        # Validate every artifact hash immediately before each inference deserialization.
        if index:
            validate_artifacts(root / ("experimento" if index == 1 else "reproduccion"))
        with (root / f"reproduccion-comando-{index + 1}.log").open("x", encoding="utf-8") as log:
            subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
    return verify(args)


def write_readme(root):
    data = load(root / "resumen-v6.json")
    verification = root / "verificacion-reproduccion.json"
    status = load(verification)["passed"] if verification.exists() else "PENDIENTE"
    binary = load(verification)["joblib_binary_equal"] if verification.exists() else "PENDIENTE"
    text = f'''# APF3 Grupo 2 V6

100% simulado. Solo investigacion academica, no aprobacion crediticia ni produccion.
Verificacion: **{status}**. Igualdad binaria joblib: **{binary}**.
Una reproduccion del procedimiento fijo no es una segunda validacion independiente.

## Contenido

- `experimento/`: 57 archivos originales, copia byte exacta; nunca sobrescribir.
- `codigo/`: 21 archivos; 20 copias exactas y solo el inicializador ML minimo aislado.
- `manifest-codepack.json`: procedencia y excepcion del inicializador. Sin imports del servicio legacy.
- `fuentes-dev/`: los 12 archivos DEV congelados; `protocolo-modelado/`: los 10 del snapshot.
- `datos/desarrollo.csv`: estudio completo 545 filas, 24 columnas, 541 conocidas y 4 desconocidas.
- `datos/desarrollo_etiquetado.csv`: 541 filas conocidas originales.
- `datos/final.csv`: estudio final con TODOS los campos, no CSV de predicciones; origen=simulado.
- `requirements.txt`: inventario pip real del venv Linux limpio, Python 3.12.14.
- `APF3_TD_Grupo2_ML_Innovacion.py`: wrapper del runner congelado en codigo/scripts.
- `manifest-paquete.json`: hashes de evidencia, codigo, datos, snapshots y soporte.
- `resumen-v6.json`: resultados originales para autores del informe y sustentacion.
- `reproduccion/`: salida separada de la unica repeticion fija, sin ajustes.
- `verificacion-reproduccion.json`: comparaciones, comandos, entorno, estado y caveat binario.

## Reproduccion

Con Docker local y el venv Linux preparado, desde esta raiz:

```sh
python3 reproducir-v6.py --root "$PWD" --action reproduce --venv-parent "{TEMP / 'cv3-repro'}"
python3 reproducir-v6.py --root "$PWD" --action verify --venv-parent "{TEMP / 'cv3-repro'}"
```

`reproduce` exige reproduccion/ e inferencias inexistentes. NO borrar salidas para repetir.
`verify` no entrena ni genera FINAL. Imagen {IMAGE}; ID registrado en entorno y comandos.
Docker sin red, -I -B, threads=1, raiz readonly, codigo en /app, DEV en /development,
snapshot en /protocol, originales readonly. No cambia prefijos de procedencia.
Solo las salidas del paquete y /tmp son escribibles. No se descarga nada al reproducir.
Preparar otro entorno requiere Python 3.12.14 Linux, `python -m venv venv` y
`venv/bin/python -m pip install -r requirements.txt` (offline: --no-index --find-links).
La imagen y wheels no se distribuyen. No se incluye Pydantic ni backend completo.
Se validan hashes estrictos antes de cargar joblib local confiable; hashes no son firmas.

## Resultados

Ganador seleccionado SOLO por OOF: tree, umbral {data['models']['tree']['threshold']}.
Parametros: `{json.dumps(data['models']['tree']['params'], sort_keys=True)}`.
Se conserva el ganador aunque no supere Dummy en FINAL; nunca se ajusta consultando FINAL.

| Modelo | Split | Precision raw | Recall raw | F2 raw | F2 policy | Revisiones | Desconocidos |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
'''
    for m in MODELS:
        for s in SPLITS:
            raw, policy = data["models"][m]["raw"][s], data["models"][m]["policy"][s]
            text += (f"| {m} | {s} | {raw['precision']:.9f} | {raw['recall']:.9f} | {raw['f2']:.9f} | "
                     f"{policy['metrics']['f2']:.9f} | {policy['reviews']} | {policy['reviews_unknown']} |\n")
    text += f'''
Conteos: `{json.dumps(data['study_counts'], sort_keys=True)}`.
Comparacion con Dummy: `{json.dumps(data['baseline_comparison'], sort_keys=True)}`.
Inferencia ilustrativa p={data['illustrative_inference']['probability']}, sin etiqueta,
no cola diaria ni aprobacion. Dos CLI frescos se comparan exactamente con el ejemplo original.

## Limites

Once features conservadas, cinco constantes cero: {', '.join(data['constant_features'])}.
completed_sales == paid_credits, no afirmar importancia independiente ni ventas al contado.
Anclas: 48 apuntes, 45 evaluables, 8 atrasos, 3 desconocidos; recuerdo y cuaderno parcial,
sin auditoria independiente. Revision Rildo de 23 items intencionales V5, NO todas las filas V6.
Historias alternativas por replica, no sucursales sumables ni volumen real agregado.
Todo saldo positivo bloquea; pago parcial no habilita. Cancelacion observada antes de evaluar
solo devuelve elegibilidad, nunca aprobacion. Se mantienen fallos finales de escala/coherencia.
OOF optimista por seleccion de configuracion y umbral; calibracion interna no es evaluacion
anidada independiente. Colas OOF separadas por fold/replica/fecha Lima, incluyen desconocidos
para capacidad sin inventar etiquetas. Tope 5/dia y 2 minutos son hipotesis, no ahorro medido.
Comparacion exacta de datos, folds, busqueda, scores, 12 raw + 12 policy completos.
Solo timestamps de ejecucion y hashes derivados/serializacion se exceptuan, validando
cada cadena local. Si joblib difiere, comparar TODOS los estados aprendidos, clases,
vars/native, dtype/shape/valores y float.hex sin tolerancia; caveat binario separado.
La web actual del repositorio es V4, NO V6. No se empaqueta ni despliega web.
Sin ZIP final mientras otros autores preparan informe y sustentacion; sus rutas no se tocan.
'''
    (root / "README.md").write_text(text, encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--action", choices=("package", "reproduce", "verify", "refresh-support"), default="package")
    parser.add_argument("--experiment", type=Path, default=DOWNLOADS / "APF3_Grupo2_Experimento_V6")
    parser.add_argument("--development", type=Path, default=DOWNLOADS / "APF3_Grupo2_Pendiente_V6")
    parser.add_argument("--protocol", type=Path, default=DOWNLOADS / "APF3_Protocolo_Modelado_V6")
    parser.add_argument("--code", type=Path, default=TEMP / "v6-academic-code")
    parser.add_argument("--venv-parent", type=Path, default=TEMP / "cv3-repro")
    parser.add_argument("--image", default=IMAGE)
    args = parser.parse_args(argv)
    args.root = args.root.resolve(strict=True)
    try:
        {"package": package, "reproduce": reproduce, "verify": verify,
         "refresh-support": refresh_support}[args.action](args)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        if args.action != "package":
            write(args.root / "verificacion-reproduccion.json", {"passed": False, "error": str(error)})
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
