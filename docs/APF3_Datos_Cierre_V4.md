# Datos: cierre descriptivo V4 SOLO DEV

Analisis post hoc congelado. No fit, predict, carga joblib, nuevos datos, nuevas features, cambios de runner/protocolo ni seleccion. No se abre DOCX privado. Auditorias guardadas son evidencia historica, no una nueva validacion independiente.

## Ficha En Seis Pasos

1. Delimitar: prestamos concedidos study; warmup solo contexto para snapshots. CSV DEV completo 559; supervision 552; 7 desconocidos conservados y auditados.

2. Identificar fuente: calibration.json y source_vs_assumptions de development_audits.json; anclas agregadas parciales del propietario, no filas reales ni verdad auditada. Hash del DOCX, sin abrirlo.

3. Operacionalizar: diccionario de las 24 columnas originales y once predictores; tipos, unidades, rangos MVP/V4, null policy y metadatos posteriores al desenlace excluidos.

4. Comprobar calidad: nulos, IDs repetidos, vectores coincidentes, no finitos, rangos y estadisticos IQR por feature; conservar coincidencias legitimas y valores extremos, sin exclusion ni imputacion.

5. Contrastar coherencia: ficha principal con los siete criterios exactos de la consigna 4.2; restricciones de calibracion separadas como detalle. Distinguir anclas, aproximaciones y supuestos; no regenerar para mejorar ajuste.

6. Describir dos relaciones declaradas en el script: reportar magnitud, denominadores y resultado adverso si aparece; sin busqueda de alternativas, causalidad ni independencia ficticia.

## Ficha Principal: Consigna 4.2

Siete criterios originales de la consigna, solo evidencia DEV y cierre APF2 documentado. Tabla principal compacta; las restricciones de calibracion siguientes son detalle de negocio, no sustituyen estos criterios.

| Criterio original | Evidencia trazable | Lectura y limite |
| --- | --- | --- |
| Escala del negocio | DEV: 2 historias alternativas, 12 clientes/replica; medias semanales AL4-D1: 11.2917 fiados/8.7917 clientes; AL4-D2: 11.5000 fiados/8.8333 clientes | Alineacion aproximada con 12 fiados/9 clientes por semana; no sumar replicas como volumen real. |
| Rangos/unidades | 559 DEV: 0 violaciones de rango por predictor, 0 de tipo y 0 no finitos; PEN, dias, conteos y proporciones en diccionario. | Importes 5..50 PEN, exposicion <=80; contrato MVP puede admitir ratios >1, V4 acotado; cercas IQR no son exclusiones. |
| Consistencia lógica/temporal | 559 DEV: 0 discrepancias en once snapshots reconstruidos; plazo 1 dia y pagos auditados; 7 unknown verificados y excluidos de supervision. | Eventos observados, sin planes futuros; tolerancia <1e-9 del validador; auditorias guardadas no son validacion independiente. |
| Relaciones plausibles | DEV resuelto: nuevo atraso 8/218 frente a 60/334; medianas ventas/antiguedad 8/13/21; 1 fila fuera de bandas, conservada. | Las medianas apoyan la direccion esperada en estas filas sinteticas. Dependencia intracliente; no causalidad ni segunda fuente independiente. |
| Señal ni nula ni perfecta | DEV OOF guardado svm, n=552: F2=0.559210526; Dummy constante 1=0.415647922, mayoritario=0.000000000; TN/FP/FN/TP=351/133/17/51. | Se observa discriminacion parcial con errores, no senal nula ni separacion perfecta; OOF reutilizado para seleccionar es optimista, no prueba utilidad real. |
| Coherencia con APF2 | APF2: captura real consentida prevista de 30-50 fiados en 4-6 semanas; cierre documentado: 0 elegibles exportados. V4: 552 etiquetas DEV sinteticas; completed_sales restringido a ventas ligadas a credito, MVP contaba ventas registradas sin ese filtro. | Cambio de fuente, volumen y cobertura declarado: no cumple captura real prevista. Cero elegibles es evidencia del cierre original, no consulta de DB actual ni ausencia de operaciones. |
| Mezcla real+simulado | DEV: 559/559 filas origen=simulado; 0 filas reales. Declaracion del propietario aporta agregados, no snapshots reales. | No aplica: 100% sintetico; no existe mezcla ni contraste real/simulado. No inferir equivalencia con datos reales. |

Fuentes: development_audits.json, calidad por predictor y relaciones DEV de este anexo; aligned_v4_report.json solo models/svm/review_policy/oof/metrics (552 resueltos, no 559); APF2_Cierre_de_Pendientes.md tabla 1 y APF2_Validacion_y_Artefactos.md H2/contrato. Todas hasheadas antes/despues. Sin metricas FINAL ni consulta a la DB actual.

## Restricciones de calibración

Controles de negocio detallados; no son los siete criterios de la consigna. Los resumenes transaccionales guardados pueden incluir warmup como contexto, no como filas de estudio.

### 1. Escala semanal

Aproximados declarados: 12 fiados/9 clientes; tolerancias de equipo 25%/2, no forzar aprobaciones. Evidencia guardada: `[{"replica": "AL4-D1", "mean_grants": 11.291666666666666, "mean_clients": 8.791666666666666, "saved_pass": true}, {"replica": "AL4-D2", "mean_grants": 11.5, "mean_clients": 8.833333333333334, "saved_pass": true}]`.

### 2. Importes y exposicion

Anclas 5..50 PEN, tope 80; distribucion lognormal es supuesto. Evidencia guardada: `[{"requested": {"count": 343, "min": 6.76, "max": 49.42, "mean": 21.935947521865888}, "granted": {"count": 321, "min": 7.55, "max": 49.42, "mean": 22.01538940809969}}, {"requested": {"count": 342, "min": 6.39, "max": 49.4, "mean": 21.745233918128655}, "granted": {"count": 327, "min": 6.39, "max": 49.4, "mean": 21.790825688073394}}]`.

### 3. Plazo y pagos

Plazo 1 dia; pagos positivos sin sobrepago; gracia no convierte atraso en puntual. Evidencia guardada: `[true, true]`.

### 4. Visitas y calendario

Ancla visitas 3..14 dias, usual 7; rotacion, 12 clientes y warmup son supuestos. Evidencia guardada: `[{"count": 331, "min_days": 3, "max_days": 14, "mean_days": 6.945619335347432, "within_3_14": true}, {"count": 330, "min_days": 3, "max_days": 14, "mean_days": 6.930303030303031, "within_3_14": true}]`.

### 5. Atrasos y heterogeneidad

8/45 evaluables es ancla parcial no auditada, no frecuencia forzada; Beta concentracion 3 y estabilidad por cliente son supuestos. Evidencia guardada: `[{"0": 233, "1": 41, "None": 4}, {"0": 251, "1": 27, "None": 3}]`.

### 6. Abonos y politica

10/48 anotaciones; independencia, fraccion 0.5 y pagos completos futuros son supuestos; sin inventar perdida permanente ni excepciones cuantificadas. Evidencia guardada: `"Reject a request with overdue debt unless every overdue loan already has a positive post-due abono visible before evaluation; then record simulated owner review. No unquantified payment-agreement exceptions are sampled."`.

### 7. Temporalidad y procedencia

Snapshots solo eventos anteriores; unknown excluido supervision; historias alternativas sinteticas no volumen real; fuente hipotetica anterior excluida. Evidencia guardada: `{"saved_hard_constraints": [true, true], "source_docx_sha256": "45bc22a10ad5dccf323708b8aeabb780d8de4629ff5087cca2582c7dd055819f"}`.

## Calidad DEV

Supervisadas n=552; clientes=24; nulos totales=0; IDs duplicados excedentes=0; grupos de vectores repetidos=0, filas implicadas=0, excedentes=0. No se borra ninguna fila.

| Feature | Min | Max | Mediana | Q1 | Q3 | IQR | Bajo/alto IQR | Nulos | No finitos | Tipo/rango invalido | Snapshot distinto |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| completed_sales | 2 | 28 | 15 | 9 | 20.25 | 11.25 | 0/0 | 0 | 0 | 0/0 | 0 |
| paid_credits | 2 | 28 | 15 | 9 | 20.25 | 11.25 | 0/0 | 0 | 0 | 0/0 | 0 |
| paid_late | 0 | 15 | 1 | 0 | 2 | 2 | 0/45 | 0 | 0 | 0/0 | 0 |
| pending_overdue | 0 | 1 | 0 | 0 | 0 | 0 | 0/5 | 0 | 0 | 0/0 | 0 |
| pending_current | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 | 0 | 0 | 0/0 | 0 |
| outstanding | 0 | 21.64 | 0 | 0 | 0 | 0 | 0/5 | 0 | 0 | 0/0 | 0 |
| utilization | 0 | 0.2705 | 0 | 0 | 0 | 0 | 0/5 | 0 | 0 | 0/0 | 0 |
| requested_ratio | 0.079875 | 0.61775 | 0.243875 | 0.184375 | 0.3385 | 0.154125 | 0/7 | 0 | 0 | 0/0 | 0 |
| tenure_days | 28 | 359 | 200 | 147 | 252.25 | 105.25 | 0/0 | 0 | 0 | 0/0 | 0 |
| punctuality_rate | 0 | 1 | 0.944444 | 0.838333 | 1 | 0.161667 | 41/0 | 0 | 0 | 0/0 | 0 |
| overdue_rate | 0 | 1 | 0 | 0 | 0 | 0 | 0/5 | 0 | 0 | 0/0 | 0 |

Las cercas IQR son descriptivas: con IQR=0, cualquier valor diferente puede quedar fuera; no equivale a error. quality_all_study incluye los 559, con exactamente 7 targets nulos. Se reconstruyen los once snapshots desde pagos/ventas observados del cache (sin usar planes futuros), con la misma tolerancia absoluta <1e-9 del validador V4; rango invalido y snapshot distinto son conteos separados, no sumar como filas distintas. Los contratos completos de cronologia y politicas constan ademas en auditorias guardadas y su fuente hasheada.

## Desconocidos

- `AL4-D1-L00318`: vence 2026-10-01, corte 2026-09-30, saldo 18.42; sin resolucion al corte; excluido supervision.
- `AL4-D1-L00319`: vence 2026-10-01, corte 2026-09-30, saldo 24.82; sin resolucion al corte; excluido supervision.
- `AL4-D1-L00320`: vence 2026-10-01, corte 2026-09-30, saldo 19.49; sin resolucion al corte; excluido supervision.
- `AL4-D1-L00321`: vence 2026-10-01, corte 2026-09-30, saldo 27.83; sin resolucion al corte; excluido supervision.
- `AL4-D2-L00325`: vence 2026-10-01, corte 2026-09-30, saldo 20.10; sin resolucion al corte; excluido supervision.
- `AL4-D2-L00326`: vence 2026-10-01, corte 2026-09-30, saldo 31.07; sin resolucion al corte; excluido supervision.
- `AL4-D2-L00327`: vence 2026-10-01, corte 2026-09-30, saldo 33.68; sin resolucion al corte; excluido supervision.

## Dos Relaciones Fijas

A. Historial paid_late y nuevo late_payment, sobre 552 resueltos: Sin atraso previo: 8/218 (3.669725%), 15 clientes; Con atraso previo: 60/334 (17.964072%), 17 clientes. Asociacion sintetica, compatible con propension latente estable supuesta; no demuestra riesgo real ni causalidad.

B. Mayor exposicion temporal al calendario puede acumular mas operaciones. Relacion de negocio de apoyo, no senal causal de riesgo ni segunda fuente independiente. Bandas fijadas antes del calculo:

| Antiguedad | n prestamos | Clientes distintos | Mediana ventas | Q1 | Q3 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 30..119 | 80 | 10 | 8.0 | 5.0 | 11.0 |
| 120..239 | 302 | 24 | 13.0 | 8.0 | 19.0 |
| >=240 | 169 | 17 | 21.0 | 16.0 | 24.0 |

Fuera de bandas (<30 dias): 1. Las medianas apoyan la direccion esperada en estas filas sinteticas.

Filas repetidas por cliente, bandas con clientes compartidos; no observaciones independientes. Sin p-valores ni causalidad ni validacion predictiva. Antiguedad de registro aleatoria y warmup comun limitan exposicion efectivamente observada; solo ventas de credito. Distribuciones y heterogeneidad latente son supuestos, no mediciones del negocio. No se presenta paid_late/paid_credits ni puntualidad derivada del mismo historial como evidencia independiente.

## Replica E Integridad

Semillas congeladas (no se usan para generar): AL4-D1=2026112101, AL4-D2=2026112102. Calculo determinista sin semilla nueva, sin Spearman/p-valores ni muestreo. El JSON guarda resumenes por replica y SHA256 antes/despues de todas las fuentes y de todo experimento congelado (artefactos opacos solo hash).

Figura exacta: `eda_relaciones_entrega.png`, dos paneles, solo DEV resuelto. FINAL se lee solo para encabezado/conteos/desconocidos; no distribuciones ni relaciones.

Integridad antes/despues: todos los hashes iguales.
