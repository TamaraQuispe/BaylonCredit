# PROY P0-05 — Adendo: el umbral ganador está en el borde de la grilla

Fecha: 2026-11-25, después del congelamiento y sin reentrenar.
Estado del experimento: selección DEV congelada con hashes; prueba FINAL cerrada.

## Observación

El ganador global — SVM lineal, `C=1.0`, `class_weight="balanced"` — quedó con umbral
**0.1**, que es el mínimo de la grilla declarada en
`docs/PROY_P0-05_MODEL_PROTOCOL.json` (`0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7`).
Los ganadores de familia `svm`, `knn` y `tree` también quedaron en 0.1; solo
`adaboost` quedó en 0.3. Además, KNN eligió `k=9`, el máximo de su propia grilla.

Métricas OOF del ganador en 0.1: F2 0.552, recall 0.895, precisión 0.218,
sobre 534 filas de 24 clientes sintéticos.

## Qué significa

- El óptimo observado por F2 está en el borde inferior: el protocolo no evaluó
  umbrales menores que 0.1, así que **0.1 es el mejor de la grilla, no
  necesariamente el mejor umbral posible**.
- No se añadieron umbrales por debajo de 0.1 después de ver los resultados: eso
  sería tuning post-hoc sobre DEV y rompería el congelamiento.
- 0.1 no es un umbral operativo. Fijarlo exige capacidad y costos acordados con el
  propietario, que el protocolo declara ausentes (`minimum_precision: null`).

## Qué no cambia

- No se reentrena, no se reordena el ranking y no se consulta FINAL.
- Los hashes de `frozen_selection.json`, `artifact_manifest.json` y
  `freeze_before_final.json` siguen siendo los del cierre; este adendo es un
  archivo nuevo y no forma parte de los manifiestos.
- Explorar el borde inferior requiere un protocolo nuevo y un test no consultado.
