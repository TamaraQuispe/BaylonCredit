# Segundo experimento académico y laboratorio

Se usa el dataset coherente de ejecución-02 sin cambiar el generador. Se revisan errores en la partición de validación del primer modelo, sin afinar con su test publicado. Diez modelos (regresión logística y Random Forest con pesos/regularización/profundidad distintos) y trece umbrales se comparan por exactitud de validación, con recall >= 0.30. El criterio supone errores igualmente costosos, no costos estimados del negocio.

Se congeló `logistic_C0.1_unweighted`, umbral 0.4, antes de generar 120 clientes sintéticos finales con semilla 20261030. Hay 1088 fiados, 1413 abonos y 1070 filas etiquetadas; 18 sin desenlace se excluyen. Los IDs FINAL no cruzan las particiones originales. Los escenarios/perfiles, IDs, saldo posterior y etiqueta no entran en predictores.

## Resultado en la misma cohorte final nueva

| Medida | V2 | V1 | Referencia mayoritaria |
|---|---|---|---|
| Exactitud | 0.6626 | 0.6075 | 0.6738 |
| Precisión | 0.4826 | 0.4291 | 0 |
| Recall | 0.4756 | 0.6160 | 0 |
| F1 | 0.4791 | 0.5059 | 0 |
| ROC-AUC | 0.6584 | 0.6564 | 0.5 |

Falsas alertas bajan 286 -> 178, pero atrasos no detectados suben 134 -> 183. No existe mejora universal ni prueba de utilidad de crédito real. No afinar más con esta cohorte final después de verla. Archivos: Descargas/APF3_Grupo2_Piloto_Sintetico/experimento-v2, con protocolo, búsqueda, elección congelada, transacciones, predicciones, errores, artefacto y reporte.

## Laboratorio integrado únicamente en demo

URL `/laboratorio-academico` bajo el dominio demo. Link en Evaluación crediticia, solo build `VITE_ACADEMIC_ML_LAB=true`. Backend `ACADEMIC_ML_LAB_ENABLED=true` restringido a staging y autenticación; artefactos confiables montados de solo lectura en `/app/academic`. No crea clientes, créditos ni evaluaciones operativas. Modelo productivo y regla de revisión de primer fiado permanecen intactos.

Servicios de demo usan la imagen pequeña de `deploy/Dockerfile.academic-lab` y el override `docker-compose.academic-lab.yml`, después de `docker-compose.demo.yml`. Directorio servidor `/home/ubuntu/credify-demo/academic`. Mantener ambos archivos al recrear para conservar flags y volumen. Imágenes de rollback: `credify-demo-api:before-academic-lab` y `credify-demo-frontend:before-academic-lab`. No entrenar en la VM de 1 GB ni ejecutar este override contra producción.

Pruebas locales: selección, exclusión de metadata, métricas, autenticación y guardas del laboratorio; suite 96 tests aprobados. Verificación demo `deploy/verify-academic-lab.mjs`: autenticación, comparación, inferencia de casos, desktop/móvil y ausencia de nuevos créditos/evaluaciones. Capturas y JSON en `experimento-v2/evidencias-demo`. Los resultados siguen siendo sintéticos, no aceptación del propietario.
