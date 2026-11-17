# V6 Final: Ejecucion Y Reproduccion

## Entrada Actual

`APF3_TD_Grupo2_ML_Innovacion.py` y el notebook equivalente ejecutan el protocolo
congelado en un directorio nuevo. Descargan el ZIP inmutable y comprueban su SHA-256,
preparan el entorno aislado Python 3.12.14, entrenan/comparan los modelos, congelan
la seleccion antes de generar FINAL y realizan una inferencia con el modelo nuevo.
Matplotlib 3.11.2 es obligatorio en ese entorno para cuatro graficos DEV.

```sh
python APF3_TD_Grupo2_ML_Innovacion.py
```

La instalacion inicial requiere Internet. `--archive` permite aportar el ZIP
publicado exacto; `--runtime-python` permite aportar un entorno previamente
instalado y comprobado. Si falta una dependencia obligatoria, se detiene antes
del entrenamiento. El notebook usa `main([])` para no recibir argumentos del kernel.

Se comprobo una reproduccion local completa en Python 3.12.14 con las dependencias
ML fijadas y Matplotlib 3.11.2. La evidencia resumida se incluye en
`anexos/ejecucion-codigo/`; no equivale a una ejecucion dentro de una cuenta de Colab.
Se preservan las discrepancias numericas observadas, sin forzar igualdad de resultados.
El comparador historico contrasta el registro OOF completo, incluido Brier: su
`selection_matches` puede ser falso por redondeo, aunque familia, parametros y umbral
sean iguales. `anexos/ejecucion-codigo/registro-ejecucion.json` verifica por separado
esa decision y las matrices/metricas de clasificacion de las cuatro familias.

La revision humana del proyecto fue realizada por el grupo. Los complementos nuevos
requieren cotejo final; ensayo, acceso a Colab y entrega en Aula no estan acreditados.

## Receta Docker Original

The original finalization used Python stdlib and cached JSON only. That historical
verification did not itself train, infer or generate cohorts. The current entrypoint
and its separate local replay evidence are described above.
The frozen runner and original 21-file codepack are byte-for-byte preserved.
The pure policy enforces debt before history. Illustrative probability alone has
authorized abs_tol=1e-12, rel_tol=0; no exact numeric inference claim is made.

From this delivery root, with Docker and an EXISTING empty external output directory:

```sh
docker build -t apf3-v6-final .
docker run --rm --network none --read-only --tmpfs /tmp -v "$PWD/sources:/sources:ro" -v "/absolute/new-output:/results" apf3-v6-final replay
docker run --rm --network none --read-only --tmpfs /tmp -v "$PWD/experiment:/evidence:ro" -v "$PWD/ejemplos:/examples:ro" -v "/absolute/new-output:/results" apf3-v6-final predict3
```

Replay creates NEW /results/reproduccion/development and experiment. Predict3 creates
NEW /results/predict3. Both refuse existing targets. Never mount original evidence
writable. Keep /app and /revision paths: future predict verifies those absolute
provenance paths. /sources is read only; /results is the only output mount.
Fixed-seed replay checks reproducibility only, not a second independent validation.
These commands are a recipe, not evidence that an independent replay was performed.
Dependency resolver transitive packages are not claimed fully locked; six direct
requirements and the Python image version are pinned, not an image digest.

Historical record verificacion-v6-final.json: release_required_checks are separate from optional
coverage. TRAIN fitted per-row scores/actions were not persisted: per-score metrics
and queue reconstruction are not_available, not release blockers. TRAIN aggregate
bindings and confusion-derived metrics were checked. ROC AUC and Brier are source
values only, not recomputed. No permission to infer or alter frozen evidence follows.
The historical document record does not certify the current PDF/PPT. Their content
is preserved and checked by tools/verificar_entrega_actual.py, with the new inventory
manifiesto-entrega-actual.json and verificacion-entrega-actual.json.
