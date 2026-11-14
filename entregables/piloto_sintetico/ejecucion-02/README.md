# Piloto académico con datos SINTÉTICOS

No son operaciones reales de Cervecería Baylón. No cargar en producción ni usar para afirmar reducción de pérdidas.

Semilla: 20261028. Clientes ficticios: 180. Fiados: 1622. Modelo seleccionado con validación: logistic_regression.

Se simulan eventos de compra, fiado a un día y pagos. Snapshots recomputados antes del crédito; etiquetas derivadas de pagos y vencimiento, no copiadas del score. Hay pago temprano, puntual, abonos puntuales/tardíos, atraso corto/largo, impago observado, abono incompleto y casos sin desenlace.

Cada cliente pertenece a una sola partición 60/20/20. Entrenamiento y escalado solo en train, selección por F1 en validation, evaluación final en test. Ninguna métrica demuestra precisión con clientes reales. Dataset, ledger, predicciones, reporte y artefacto tienen nombres académicos/sintéticos separados del loader productivo.
