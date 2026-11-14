# APF3: piloto académico con datos sintéticos

Según declaración del usuario, el docente autorizó datos ficticios para todo el trabajo con variedad y coherencia. No se recibió un mensaje independiente del profesor. Conservar ese respaldo si se dispone de él; no reescribir el feedback de APF2 como si siempre hubiera permitido esta modalidad.

Se implementó un simulador separado (`backend/app/ml/synthetic.py`) que produce eventos ficticios de clientes, compras, créditos y abonos. Calcula los mismos once predictores a partir del historial anterior al fiado y deriva `late_payment` de los pagos y vencimiento. No usa datos personales, score como etiqueta ni operaciones de producción. Los perfiles son parámetros ocultos de generación, no predictores.

Hay pagos anticipados, puntuales, abonos puntuales y tardíos, atrasos cortos y largos, ausencia de pago observada, abonos incompletos y casos sin desenlace. Plazo de un día, máximo simulado S/200 de exposición y primer monto sin historial hasta S/50, como supuestos académicos que no cambian la política productiva.

El script `backend/scripts/academic_credit_pilot.py` separa 60/20/20 de clientes antes de simular. Ajusta solo en entrenamiento, compara regresión logística y Random Forest por F1 de validación y mide el modelo seleccionado una vez en test. Exporta baseline mayoritario, precisión, recall, F1, matriz de confusión, ROC-AUC y Brier, además de predicciones y hashes del dataset/ledger. Metadatos de desenlace, cliente, escenario y partición no entran en los once predictores.

## Ejecución entregada

Carpeta: Descargas/APF3_Grupo2_Piloto_Sintetico/ejecucion-02. 180 clientes, 1622 fiados, 2078 eventos de abono; 1598 filas etiquetadas y 24 sin desenlace. Modelo seleccionado: regresión logística. Métricas de test SINTÉTICO: accuracy 0.6181, precision 0.4859, recall 0.6053, F1 0.5391 y ROC-AUC 0.6305. Baseline accuracy 0.6311: NO se afirma superioridad general ni idoneidad de decisiones reales. No se activó ningún artefacto en producción.

Ejecución-01 se conserva como versión previa. Se revisó porque no incluía créditos anteriores aún vigentes en el snapshot; en ejecución-02 también se acotó la exposición inicial. No se escogió por mejor resultado: las métricas de test fueron menores y se reportaron. Cualquier experimento adicional debe declararse y, si se reutiliza test para decisiones, se necesita un nuevo conjunto final no usado para seleccionar.

## Comandos

Desde backend y con sus dependencias:

```bash
PYTHONPATH=. python scripts/academic_credit_pilot.py --output-dir /ruta/nueva --clients 180 --seed 20261028
pytest tests/test_synthetic_academic.py
```

No escribir salidas académicas en `app/`, no sustituir artefactos productivos y no importar este dataset a la BD del negocio. La aprobación inicial manual de producción sigue activa. La tasa de pérdida del 5 % sobre ventas no se usó como tasa de atraso; no son equivalentes.

El documento Word y el JSON de resultados declaran procedencia, supuestos, límites y cifras. El grupo debe cotejar ejemplos y registrar su validación humana; una prueba automatizada no es aprobación del dueño.
