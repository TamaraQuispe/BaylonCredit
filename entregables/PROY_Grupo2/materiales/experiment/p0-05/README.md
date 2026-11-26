# PROY P0-05 — Evidencia congelada (selección en DEV)

Copia versionada de la salida del runner `backend/scripts/proy_credit_experiment_v1.py`,
cuya carpeta de trabajo (`academic/`) está fuera de Git. La prueba FINAL sigue cerrada:
no hay cohorte generada ni puntuada.

## Contenido

| Archivo | Qué es |
| --- | --- |
| `PROY_P0-05_MODEL_PROTOCOL.json` | Protocolo preinscrito (grilla, folds, umbrales, cohorte FINAL reservada). |
| `provenance.json` | SHA-256 de entradas, runtime y código; hash del protocolo. |
| `cv_search.json` | 25 candidatos × 7 umbrales sobre OOF, más ambos Dummy. |
| `family_winners.json` | Ganador por familia y ganador global. |
| `frozen_selection.json` | Selección congelada con parámetros, umbral y métricas. |
| `artifact_manifest.json` | SHA-256 de los artefactos congelados. |
| `freeze_before_final.json` | Cierre: inventario de archivos y 0 llamadas a FINAL. |
| `proy_p0_05_report.json` | Reporte completo de la corrida (incluye estado de FINAL). |
| `svm.joblib`, `knn.joblib`, `tree.joblib`, `adaboost.joblib` | Modelos refit de cada ganador de familia. |
| `dummy_most_frequent.joblib`, `dummy_constant_1.joblib` | Referencias Dummy. |
| `selected_model.joblib` | Copia del ganador global (SVM lineal, `C=1.0`, `balanced`). |

## Verificación

Desde la raíz del repositorio, los hashes del cierre deben coincidir con los archivos:

```bash
cd entregables/PROY_Grupo2/materiales/experiment/p0-05
python - <<'PY'
import hashlib, json
from pathlib import Path
freeze = json.loads(Path("freeze_before_final.json").read_text())["files"]
for name, expected in freeze.items():
    found = hashlib.sha256(Path(name).read_bytes()).hexdigest()
    assert found == expected, name
print(f"{len(freeze)} archivos coinciden con freeze_before_final.json")
PY
```

La puerta FINAL se puede consultar sin abrirla:

```bash
cd backend && ../.venv/bin/python scripts/proy_credit_experiment_v1.py \
  --development-dir ../entregables/PROY_Grupo2/materiales/development \
  --protocol ../docs/PROY_P0-05_MODEL_PROTOCOL.json \
  --output-dir ../entregables/PROY_Grupo2/materiales/experiment/p0-05 \
  --status-only ../entregables/PROY_Grupo2/materiales/experiment/p0-05
```

## Nota de selección

El ganador quedó en el umbral 0.1, el borde inferior de la grilla. Está registrado en
`docs/PROY_P0-05_ADENDUM_UMBRAL.md`: no se exploraron umbrales menores y no se hizo
tuning post-hoc. Este directorio no se modifica después del cierre.
