# Solución de Machine Learning para el fiado a un día en Cervecería Baylón

## Avance de Proyecto Formativo 3 · Grupo 2

Facultad de Ingeniería de Sistemas e Informática · Universidad Tecnológica del Perú

Caso 4: Scoring crediticio alternativo con IA para el fiado y microcrédito MYPE

Integrantes: Baylón Vila, Omara Yamileth; Coveñas Quispe, Tamara Alison; Paredes Paredes, César Augusto Daniel; Yman Avila, Pablo Enrique.

| Integrante | Código |
| --- | --- |
| Omara Yamileth Baylón Vila | U23231338 |
| Tamara Alison Coveñas Quispe | U23204737 |
| César Augusto Daniel Paredes Paredes | U23259768 |
| Pablo Enrique Yman Avila | U23251279 |

Docente: Caman Sanchez, Richard Enrique · Sección 35036 · Lima, Perú · 2026-2

**BORRADOR DE TRABAJO.** Registros ficticios confirmados por la usuaria. Resultados experimentales sintéticos; no validación del negocio ni autorización automática de créditos. Este documento no está listo para entrega: conserva brechas metodológicas y verificaciones humanas pendientes, detalladas en el Anexo C.

<!-- PAGE -->

# 1. Resumen ejecutivo y problema ML

## 1.1. Continuidad de APF1 y APF2

Cervecería Baylón es un negocio familiar de San Martín de Porres, Lima, operado por dos propietarios. APF1 identificó una gestión del fiado a un día basada en cuaderno y criterio personal, sin historial digital analizable. APF2 desarrolló Credify, un MVP con clientes, evaluación preliminar por reglas, fiados, abonos e historial persistente. Conservamos empresa, equipo y problema; Lean Startup y Kanban siguen como marco de evolución, no como sustitutos de la evaluación ML (Grupo 2, 2026a, 2026b).

La demo pública es https://demo-credify.168-75-71-113.sslip.io. Al cierre de APF2 no había comenzado el piloto real y el exportador devolvió cero fiados elegibles; ello no demostraba ausencia de otras operaciones en la base. La usuaria confirmó para este borrador que los registros siguen siendo ficticios. APF3 documenta un experimento sintético separado: no transforma las operaciones de demostración en evidencia del negocio.

## 1.2. Definición del problema y decisión

**Para los propietarios de Cervecería Baylón, el modelo clasificará si un fiado evaluado se pagará con atraso respecto al vencimiento contractual, para apoyar su revisión antes de otorgarlo, medido mediante precision, recall y F1 de atraso frente a una línea base, manteniendo como finalidad futura reducir el dinero no recuperado y ampliar la cobertura de evaluación. La meta numérica de negocio está pendiente de acuerdo y justificación con el propietario.**

Es clasificación binaria supervisada. Cada fila representa un fiado evaluado; el target es `late_payment`. No se predice una pérdida definitiva ni una mora a 30 días. La salida informa revisión humana, no aprobación o rechazo automático.

## 1.3. Indicadores y costo de errores

APF1 declaró evaluación automatizada inicial de 0 %. APF2 precisó el 5 % referencial como pérdida mensual estimada / ventas del mes × 100, sin corroboración contable de un mes específico. Ese porcentaje no equivale a prevalencia de atraso, accuracy ni probabilidad de impago. No se usa para generar etiquetas ni se afirma que haya disminuido.

Un falso negativo omite un atraso y puede dejar exposición sin revisar; un falso positivo genera revisión innecesaria y podría limitar una venta. Es una hipótesis de consecuencias, no un costo monetario medido. El protocolo v2 ponderó ambos errores por igual mediante accuracy y exigió recall ≥ 0,30; ese piso es experimental, no una meta acordada con el propietario. Falta definir el costo relativo y una meta observable antes de otro experimento confirmatorio.

<!-- PAGE -->

# 2. Dataset, coherencia y preprocesamiento

## 2.1. Origen y trazabilidad

El dataset no procede de operaciones reales: se generaron clientes, fiados y abonos ficticios mediante un simulador reproducible. Se conserva `data_source=synthetic` y este paquete agrega `origen=simulado` como metadato de procedencia, sin modificar las once variables, el target ni el modelo ya entrenado. No se añaden nombres, DNI, teléfonos o direcciones de clientes reales.

| Elemento de APF2 | Implementación del experimento | Cambio o límite |
| --- | --- | --- |
| Un fiado evaluado | Una fila por fiado con snapshot previo | Se conserva la unidad |
| Target `late_payment` | Etiqueta derivada de pagos y vencimiento | Se conserva la definición |
| Once variables históricas | Mismo orden de `FEATURE_NAMES` | No se usa el score como etiqueta |
| Fuente real consentida prevista | Libro de transacciones sintéticas separado | Cambio de fuente que debe justificarse |
| 30–50 fiados reales en 4–6 semanas | 1622 fiados simulados; 1598 etiquetados | No son registros capturados ni escala validada |
| CSV sin fechas de exportación | IDs ficticios, evaluación, vencimiento y corte | Metadatos para auditoría, no predictores |
| Partición 80/20 preliminar | 60/20/20 por cliente en ejecución-02 | Se evita que un cliente cruce particiones |

APF1 contempló complementar un historial insuficiente con simulación. APF2 propuso extender la captura real sin sustituir datos. La consigna APF3 admite simulación justificada y exige declarar cambios de fuente. Por ello, el experimento actual se presenta como desarrollo académico, no como cumplimiento del piloto real prometido en APF2. La usuaria reportó autorización del docente para datos ficticios; no se incorpora una constancia independiente ni se atribuye un alcance adicional a esa comunicación.

## 2.2. Volumen y versiones

| Conjunto | Clientes ficticios | Fiados | Etiquetados | Sin desenlace |
| --- | --- | --- | --- | --- |
| Ejecución-02, desarrollo de v1/v2 | 180 | 1622 | 1598 | 24 |
| Cohorte final nueva de v2 | 120 | 1088 | 1070 | 18 |

Entrenamiento original: 943 filas (627 puntuales, 316 atrasadas); validación: 346 (250/96); test original: 309 (195/114), ya consultado en v1. V2 no utilizó ese test para su búsqueda. La cohorte final de v2 tiene 721 puntuales y 349 atrasadas. No se suman estas cohortes para describir un único test ni una muestra de clientes reales.

Los tamaños superan las referencias orientativas de 200 filas y 30 ejemplos minoritarios de APF3, pero el volumen por sí solo no demuestra representatividad.

<!-- PAGE -->

## 2.3. Simulación y ficha de coherencia

Semilla de desarrollo: 20261028; corte simulado: 31/10/2026. Se asignan seis perfiles ficticios, con igual número de clientes por perfil, y se generan de 8 a 13 oportunidades de fiado por cliente no nuevo; los nuevos tienen una. Las fechas avanzan entre 1 y 5 días. El plazo contractual es un día. El monto base sigue una lognormal con parámetros 3,85 y 0,55, acotada inicialmente entre S/ 10 y S/ 200 y por el cupo disponible; sin pagos completos previos, se limita a S/ 50.

Las propensiones y pesos de escenarios fueron fijados por el equipo: por ejemplo, rangos de 0,02–0,12 para perfil puntual y 0,55–0,80 para atrasos frecuentes, con ajustes por dificultad temporal y exposición. Se simulan pago anticipado, puntual, abonos puntuales/tardíos, atrasos cortos/largos, pago incompleto y ausencia de pago. La etiqueta se calcula desde los eventos observados, no desde el score del MVP.

**Estos parámetros no son estimaciones de Cervecería Baylón.** El fiado a un día y la existencia de clientes fijos/abonos se vinculan con APF1/APF2; faltan fuentes verificables para cantidades de clientes, frecuencias, montos y probabilidades. S/ 200 es un supuesto de configuración y demostración, no un límite validado del negocio. Las compras semanales mencionadas en APF1 no se convierten en ventas.

| Criterio APF3 | Evidencia disponible | Evaluación honesta |
| --- | --- | --- |
| Escala del negocio | Volumen sintético y ficha APF1 | Calibración cuantitativa pendiente |
| Rangos y unidades | Soles, conteos, ratios; validaciones de montos | Controles técnicos ejecutados |
| Lógica y tiempo | Vencimiento +1 día; pagos no exceden deuda; snapshot anterior | Verificaciones del simulador |
| Relaciones plausibles | EDA de entrenamiento, sección 2.6 | Asociaciones simuladas, no causales |
| Señal no nula ni perfecta | AUC v2 final 0,6584, F1 0,4791 | Señal limitada, no validación externa |
| Coherencia con APF2 | Mismos predictores/target; fuente modificada | Trazabilidad explícita, fuente pendiente de calibración |
| Mezcla real + simulado | No hay registros reales en este paquete | No aplica comparar distribuciones por origen |

Las fechas de transacciones y el corte son parte del escenario ficticio, no constancias de actividad histórica. La generación y evaluación registrada el 29/10/2026 no significa que ya se hubieran observado pagos reales del 31/10. El código conserva las verificaciones automáticas en `validate_academic_dataset`; su resultado no certifica los siete criterios completos de la rúbrica.

<!-- PAGE -->

## 2.4. Limpieza y variables derivadas

Los 24 fiados originales sin desenlace se mantienen en el CSV documental con target vacío, pero se excluyeron del aprendizaje supervisado. No se imputa un resultado a créditos todavía dentro de plazo. Los controles de esta preparación verifican IDs únicos, procedencia sintética, finitud y rangos de predictores; el manifiesto indica los conteos realmente observados. No se eliminan dos fiados por compartir un snapshot: un mismo cliente puede tener operaciones legítimas parecidas.

No se ejecutó imputación porque el generador produce predictores completos. Para datos reales habría que definir el tratamiento de faltantes dentro de un Pipeline, usando solo entrenamiento. Tampoco se descartan outliers por ser grandes: los límites del simulador son supuestos documentados y no una estimación de los extremos del negocio.

Variables derivadas: `utilization = outstanding / max_credit_amount`, `requested_ratio = requested_amount / max_credit_amount`, `punctuality_rate = (paid_credits - paid_late) / paid_credits` y `overdue_rate = pending_overdue / (pending_current + pending_overdue)`. Cuando no hay historial, la puntualidad se representa como cero y se interpreta junto con el conteo de pagos: no significa que el cliente haya incumplido.

## 2.5. Partición y prevención de fuga

La ejecución-02 asignó 108/36/36 clientes a entrenamiento, validación y test antes de simular; proporción 60/20/20 por cliente, no por número de filas. Un cliente no cruza conjuntos. Los snapshots se reconstruyen con operaciones disponibles antes de cada evaluación, sin pagos posteriores. La selección usa únicamente las once variables previstas en APF2.

Se excluyen del vector `client_id`, `loan_id`, `profile`, `scenario`, `split`, `pending_at_cutoff`, fechas posteriores y `late_payment`. `origen` también es metadato. Los perfiles y escenarios se utilizan para auditar errores, nunca para predecir. Todas las variables de aprendizaje son numéricas: no se requiere codificar estas categorías excluidas.

La regresión logística usa `StandardScaler` dentro de un Pipeline ajustado con entrenamiento. Random Forest no se escala, por su estructura de particiones. Comparten variables y particiones, pero no idéntica transformación. El procedimiento no incluye validación cruzada: es una brecha frente a la sección 5 de APF3, no una característica que deba describirse como cumplida.

V2 congeló modelo/umbral antes de generar la cohorte final con semilla 20261030. Esta nueva cohorte usa el mismo simulador y clientes distintos: no constituye validación externa. Una vez publicados sus resultados, no debe reutilizarse para ajustar modelos o umbrales. El CSV de desarrollo también conserva el test antiguo como ya consultado, no como prueba futura intacta.

<!-- PAGE -->

## 2.6. EDA: distribución y estadísticos

El EDA que se incorpora a este borrador se calculó sobre las 943 filas de entrenamiento ya existentes. Es descriptivo y posterior al experimento: no se presenta como análisis prospectivo realizado antes de seleccionar v2. No se ejecutó un nuevo entrenamiento ni se volvió a seleccionar con el test.

![Figura 1. Distribución de `late_payment` en entrenamiento sintético.](figuras/eda_balance.png)

**Conclusión.** Hay {{train_negative_pct}} % de fiados puntuales y {{train_positive_pct}} % con atraso. El desbalance hace insuficiente interpretar accuracy de forma aislada. Esto justifica informar precision, recall, F1 y matriz de confusión, sin cambiar retrospectivamente el criterio de selección de v2.

{{descriptives_table}}

Los estadísticos describen el escenario generado, no ventas, cartera ni frecuencia real del negocio. La información de montos se encuentra en metadatos de transacciones; el modelo usa el ratio solicitado y no el monto bruto como predictor independiente. Las observaciones de un mismo cliente están relacionadas, por lo que no deben tratarse como 943 clientes independientes.

<!-- PAGE -->

## 2.7. EDA: relaciones esperadas y sus límites

Se examinan dos relaciones que pueden ser relevantes para el fiado: historial de pagos tardíos frente a un nuevo atraso, y exposición previa frente al atraso del nuevo fiado. Las bandas se usan solo para describir datos; no son umbrales nuevos del modelo.

![Figura 2. Tasa de atraso por historial y exposición en entrenamiento sintético.](figuras/eda_relaciones.png)

{{relationships_table}}

**Conclusión sobre historial.** {{history_conclusion}} La asociación se refiere a un simulador que introduce persistencia de perfiles; no prueba que esta magnitud se observe en clientes del negocio ni permite calificar como incumplidor a quien no tiene historial.

**Conclusión sobre exposición.** {{exposure_conclusion}} El gráfico presenta denominadores por banda; una banda pequeña puede ser inestable. Si la relación no es monotónica, se informa tal como aparece, sin modificar datos para forzarla. Tampoco equivale a un efecto causal de aumentar o disminuir el cupo.

La combinación de comportamientos cambiantes, historial limitado y ruido simulado explica que exista señal sin separación perfecta. La plausibilidad estadística no resuelve la calibración de escala: todavía deben contrastarse los parámetros con una fuente verificable del negocio o sector.

<!-- PAGE -->

# 3. Modelado, comparación y reproducibilidad

## 3.1. Candidatos y línea base

En v1 se compararon regresión logística regularizada y Random Forest con entrenamiento y validación compartidos; se eligió por F1 de validación. La referencia fue `DummyClassifier(strategy="prior")`, ajustado con entrenamiento. V2 conserva el dataset de desarrollo y explora diez configuraciones de dos familias, no diez algoritmos diferentes.

| Familia v2 | Espacio explorado | Control de complejidad |
| --- | --- | --- |
| Regresión logística + StandardScaler | C = 0,1; 1; 10; class_weight = None/balanced | Regularización L2; max_iter = 2000 |
| Random Forest | max_depth = 3/6; class_weight = None/balanced | 150 árboles; min_samples_leaf = 12; n_jobs = 1 |
| Umbral de clasificación | 0,20 a 0,80 en pasos de 0,05 | 13 valores por configuración |
| Línea base mayoritaria | Prevalencia calculada solo en entrenamiento | Predice clase 0 al usar umbral 0,5 |

La logística facilita inspeccionar coeficientes y requiere escalado; el bosque representa relaciones no lineales y limita profundidad. Random Forest fue contemplado en APF1, pero la guía U3 de la consigna no lo nombra expresamente: falta confirmar su aceptación o incorporar un segundo algoritmo explícitamente permitido. No se presenta esa verificación como realizada.

## 3.2. Selección y evaluación

V2 ajustó cada candidato con 943 filas y calculó 130 combinaciones modelo/umbral sobre las mismas 346 filas de validación. Eligió mayor accuracy con recall ≥ 0,30; desempató por balanced accuracy, F1 y cercanía del umbral a 0,5. Se seleccionó `logistic_C0.1_unweighted`, umbral 0,40; accuracy de validación 0,6994 y recall 0,3542.

Se guardó `frozen_selection.json` antes de generar la cohorte final nueva. El modelo exportado mantiene el ajuste de entrenamiento; no se reentrenó con train + validación. `academic_model_v2.joblib` incluye el escalador; el umbral y orden de características se conservan en el reporte y se aplican en el endpoint.

**Brechas.** La búsqueda fue holdout, no validación cruzada. Faltan métricas de entrenamiento para cuantificar sobreajuste y una evaluación final común de todos los candidatos fijados por protocolo. No se calculan ahora esos resultados sobre el test para corregir retrospectivamente la selección.

## 3.3. Reproducción y viabilidad

Los scripts existentes son `academic_credit_pilot.py` y `academic_credit_experiment_v2.py`; el Anexo B identifica fuentes, semillas y artefactos. Python registrado: 3.12.14; scikit-learn: 1.9.1; semilla de estimadores v2: 42. Falta empaquetar y verificar el entregable ML completo en un entorno limpio con dependencias fijadas. Las dependencias del generador de este informe no sustituyen las de entrenamiento.

La inferencia se ejecuta en FastAPI sobre un vector de once números. El entrenamiento se realizó fuera del servicio público; no debe ejecutarse en la VM compartida de recursos limitados. Una inspección local del artefacto midió 100 inferencias de un registro: mediana {{latency_median}} ms y p95 {{latency_p95}} ms. Se excluyen carga, preparación, red y BD: no es latencia del endpoint ni un SLA de la VM. No hay medición de memoria del servicio.

El taller de Doña Rosa permitió ejecutar SVM, KNN, árbol y AdaBoost, pero no añade esos algoritmos a la comparación de Baylón. Su transferencia se documenta en el Anexo D: replicar el método con el contrato del proyecto, no copiar resultados ni elegir anticipadamente el árbol.

<!-- PAGE -->

# 4. Evaluación e interpretación de negocio

## 4.1. Comparación en la misma cohorte final de v2

{{metrics_table}}

Fuente: `experiment_v2_report.json`, 1070 fiados etiquetados de 120 clientes ficticios nuevos. La columna v1 se calculó sobre esta misma cohorte; no es el resultado del test original de 309 filas. El test antiguo y el nuevo no se mezclan. La tabla no representa todos los candidatos de la búsqueda: esa comparación final requerida sigue pendiente para un protocolo corregido.

**Resultado principal.** V2 mejora accuracy respecto a v1, de 60,75 % a 66,26 %, y reduce falsas alertas de 286 a 178. Sin embargo, queda por debajo de la línea base mayoritaria en accuracy (67,38 %). También baja el recall respecto a v1 (61,60 % a 47,56 %) y el F1 (50,59 % a 47,91 %). No existe una mejora universal.

## 4.2. Matriz de confusión de v2

| Desenlace simulado | Predice puntual (0) | Predice atraso (1) |
| --- | --- | --- |
| Puntual (0) | 543 verdaderos negativos | 178 falsos positivos |
| Atraso (1) | 183 falsos negativos | 166 verdaderos positivos |

Se detectaron 166 de 349 atrasos. De 344 alertas, 166 correspondieron a atraso. La referencia mayoritaria acertó 721 pagos puntuales y omitió los 349 atrasos. Un F1 superior al cero de esa referencia muestra capacidad de detección dentro de la simulación, pero no permite afirmar superioridad general ni cumplimiento del criterio principal de accuracy usado en v2.

El AUC de 0,6584 señala discriminación limitada en este escenario. El Brier score no certifica calibración para clientes reales. No se deben presentar las probabilidades como riesgo real validado ni prometer que una alerta evita una pérdida.

<!-- PAGE -->

## 4.3. Tres errores concretos y sus hipótesis

{{errors_table}}

Los casos proceden de `final_errors_not_for_tuning.json`; su cliente ficticio se contrasta con `fresh_synthetic_transactions.json`. El umbral es 0,40. Las hipótesis son interpretaciones, no causas comprobadas ni motivos para modificar el umbral con el test ya visto. Los dos primeros casos pertenecen a un mismo historial, por lo que tampoco son errores independientes de dos clientes.

## 4.4. Interpretación para los propietarios

El modelo puede mostrar una señal experimental para revisar un fiado a partir del historial disponible; no conoce la voluntad futura del cliente ni garantiza el cobro. La ausencia de pagos previos limita sus conclusiones. Debe complementarse con la decisión humana y no usarse para negar automáticamente crédito.

Los resultados permiten cuantificar decisiones de revisión dentro de la simulación: v2 emitió 344 alertas, con 178 falsas alertas y 183 atrasos omitidos. No se afirma ahorro de soles, reducción de morosidad ni adopción diaria. Para medir impacto se necesitaría comparar un periodo y una política de revisión definidos, registrar la acción del propietario y observar recuperación y ventas sin atribuir causalidad solo al score.

El costo ilustrativo puede expresarse como `C_FP × 178 + C_FN × 183`, siempre que los costos sean obtenidos y justificados. Esta fórmula cuenta errores del escenario, no pérdida financiera real; un atraso no equivale necesariamente a dinero definitivamente no recuperado. No se asignan valores a C_FP/C_FN en este borrador.

<!-- PAGE -->

## 4.5. Interpretabilidad del artefacto exportado

Se verificó el hash del artefacto y se extrajeron sus coeficientes, sin reentrenarlo. La tabla resume cinco; los once y el intercepto están en el JSON anexo. Son cambios en log-odds por una unidad del escalador ajustado; exp(coeficiente) multiplica odds, no probabilidades ni pérdidas. No son efectos causales ni explicaciones de `rules-v1`.

{{coefficients_table}}

Los predictores derivados están correlacionados; en esta simulación, `utilization` equivale a `outstanding / 200`. Eso limita atribuir efectos separados. La antigüedad tiene coeficiente positivo en v2: no se interpreta como razón para penalizar antigüedad ni se afirma ausencia de sesgo. Debe auditarse antes de uso real.

La meta numérica del Paso 1 sigue pendiente: por tanto, no se declara alcanzada. La conclusión disponible es más limitada: existe un pipeline e inferencia funcional sobre datos sintéticos, con capacidad parcial para identificar atrasos y un intercambio explícito entre falsas alertas y omisiones.

<!-- PAGE -->

# 5. Integración con el MVP

## 5.1. Flujo implementado

Flujo académico: selección de caso ficticio → recuperación de sus once variables → StandardScaler del artefacto → `predict_proba` → comparación con umbral 0,40 → resultado en pantalla. Disponible en https://demo-credify.168-75-71-113.sslip.io/laboratorio-academico, con enlace desde Evaluación crediticia y autenticación. No se afirma que el modelo v2 determine la aprobación operativa.

El backend verifica procedencia sintética, orden de campos y SHA-256 del artefacto antes de cargarlo. Solo admite artefactos confiables del despliegue, no archivos de usuarios. Está restringido a staging mediante flag y no crea créditos ni evaluaciones operativas.

## 5.2. Contrato actual y contrato pendiente

| Parte | Esquema actual verificado en código |
| --- | --- |
| Entrada HTTP | POST `/api/v1/academic-ml/evaluate/{case_id}`; token de acceso; sin cuerpo JSON |
| Datos internos | Caso predefinido con objeto `features` de once campos del MVP |
| Salida | case_id, scenario, data_source, version, estimated_late_probability, threshold, predicted_late_payment, actual_late_payment, features, disclaimer |
| Acción de interfaz | Mostrar predicción experimental y desenlace simulado para comparación |

Además del endpoint por ID, el script `inspect_academic_artifact.py` acepta un archivo JSON con las once variables, valida el esquema y carga el pipeline exportado. Se ejecutó con un vector ilustrativo de APF2 distinto de los 16 casos predefinidos. No es una operación real y su desenlace es desconocido.

Entrada JSON ejecutada por el script, no por el endpoint HTTP:

```json
{"completed_sales":3,"paid_credits":2,"paid_late":1,"pending_overdue":0,"pending_current":0,"outstanding":0,"utilization":0,"requested_ratio":0.25,"tenure_days":45,"punctuality_rate":0.5,"overdue_rate":0}
```

Salida ejecutada: `probability_class_1={{new_probability}}`, `threshold=0.4`, `prediction=0`, `origin=simulado`; etiqueta real desconocida. Es una demostración de inferencia, no prueba de que la predicción sea correcta ni una aprobación de crédito. `academic_artifact_inspection.json` registra entrada, salida, hash y versiones. El HTTP todavía acepta solo un ID; conectar captura libre a la interfaz queda para PROY. El desenlace conocido de casos de test solo se usa para comparación académica, nunca como predictor.

## 5.3. Evidencia y estado

El reporte técnico del 29/10/2026 registra cinco comprobaciones aprobadas, incluida inferencia de 16 casos predefinidos, autenticación, pantalla escritorio/móvil y ausencia de nuevos créditos/evaluaciones. Las capturas se incluyen en el Anexo B. Son evidencia de funcionamiento en esa fecha, no disponibilidad continua ni aceptación del propietario. La demo completa de operación con predicciones validadas queda para PROY.

<!-- PAGE -->

# 6. Normativa y proyección a PROY

## 6.1. Tratamiento de datos y normativa

Se mantiene el marco de APF2: Ley N.° 29733 y Reglamento aprobado por D.S. N.° 016-2024-JUS (ANPD, 2011, 2024). Las fuentes oficiales se incluyen en Referencias. La matriz es un autodiagnóstico académico, no un dictamen de cumplimiento legal integral. No se atribuyen artículos o plazos específicos que no hayan sido contrastados.

| Requisito o aspecto | Decisión/control del dataset o modelo | Evidencia y estado |
| --- | --- | --- |
| Finalidad y minimización | Once variables transaccionales para experimentar con atraso; excluir score, nombres y documentos del vector | `FEATURE_NAMES`, CSV y diccionario; finalidad real futura por formalizar |
| Procedencia y datos personales | Dataset generado, IDs ficticios y columna origen=simulado | Generador y manifiesto; no presentar como anonimización de clientes reales |
| Acceso y seguridad | Autenticación del laboratorio, artefacto de solo lectura e integridad SHA-256 | Dependencia get_current_user, load_lab y guardas de staging |
| Consentimiento para piloto real | No inferir consentimiento de clientes desde la firma del propietario o una casilla visual | APF2 US09: constancia persistida y aviso pendientes de verificación actual |
| Conservación y derechos ARCO | Separar datos académicos de operativos; definir retención y procedimiento antes de tratar datos reales | Procedimiento, plazos y eliminación comprobada pendientes |
| Proveedores y transferencias | No remitir el dataset a OpenRouter; laboratorio no requiere WhatsApp | Revisar condiciones de nube y terceros antes del piloto real |

La afirmación de registros ficticios se aplica al dataset de este informe, no implica que las cuentas del sistema o los documentos de entrevistas carezcan de datos personales. Los nombres de integrantes y del propietario aparecen como atribución académica; no son predictores. No se incorporan contraseñas, tokens, firmas, DNI o contactos personales en los anexos de datos del modelo.

La configuración HTTPS de la demo pública descrita en APF2 y los tests de acceso son controles técnicos acotados. Las pruebas locales de resiliencia no acreditan HTTPS ni cumplimiento de producción. Omitir identificadores directos de un dataset real futuro tampoco garantiza anonimización irreversible; deberá evaluarse riesgo de reidentificación y la base jurídica aplicable.

Antes de cualquier piloto real, el equipo debe revisar el aviso, finalidades, mecanismos de consentimiento cuando correspondan, conservación, derechos del titular, accesos y proveedores. Este borrador no afirma que esas brechas se hayan cerrado desde APF2.

<!-- PAGE -->

## 6.2. Proyección a PROY y riesgos

El siguiente hito no es activar automáticamente v2: primero se requiere corregir el protocolo y completar la evidencia. La integración académica demuestra carga e inferencia, mientras el proceso operativo conserva sus reglas y revisión humana. Los responsables de la tabla son propuestas de seguimiento basadas en roles previos; deben ser confirmados por el grupo y no acreditan trabajo pasado.

| Riesgo | Probabilidad / impacto | Responsable propuesto | Mitigación y criterio de cierre |
| --- | --- | --- | --- |
| Simulación no representativa | Alta / Alto | César y Omara | Calibrar parámetros con fuente verificable; distinguir supuestos de observaciones |
| Selección sobreajustada a validación | Media-alta / Alto | César y Tamara | CV agrupada en entrenamiento; congelar protocolo y reservar test nuevo |
| Confundir atraso con pérdida | Alta / Alto | Omara y Pablo | Mantener target contractual y fórmula financiera separados; revisión del propietario |
| Uso indebido del score sintético | Media / Alto | Tamara | Laboratorio separado, advertencias y prohibición de aprobación automática con v2 |
| Consentimiento no trazable en piloto | Alta mientras siga la brecha / Alto | Omara y Tamara | Constancia persistida, información y revisión de tratamiento antes de datos reales |
| Demo o proveedor no disponible | Media / Alto | Tamara y Pablo | Ensayo previo, artefacto local y evidencia de última ejecución; no prometer disponibilidad |

## 6.3. Plan de evolución

1. Validar supuestos de simulación y tabla de trazabilidad con APF1/APF2; registrar fuente, fecha y parámetro respaldado.
2. Declarar costo de errores y meta antes de otro experimento; comparar baseline y al menos dos algoritmos aceptados mediante CV sin fuga.
3. Guardar pipeline, umbral y esquema; ejecutar un ejemplo nuevo y medir memoria/latencia en el entorno previsto.
4. Completar controles de tratamiento de datos antes de captura real; definir qué operaciones son elegibles y no reconstruir snapshots con información posterior.
5. Recoger nuevos desenlaces consentidos y revisar distribuciones y desempeño antes de autorizar uso operativo del modelo.

**Reentrenamiento propuesto.** Revisar al cierre de cada periodo de captura acordado, no entrenar automáticamente por calendario. Condicionar un candidato a datos trazables, ambas clases, volumen suficiente para la partición, métricas y revisión humana. Versionar código/datos/artefacto, contrastarlo con la línea base y conservar rollback. La frecuencia y los criterios numéricos quedan por acordar; no se afirma que haya un ciclo productivo activo.

<!-- PAGE -->

# 7. Conclusiones

El trabajo conserva el problema de Cervecería Baylón y el contrato de once variables de APF2, con una etiqueta de atraso al vencimiento. La contribución actual es un experimento reproducible por diseño y un laboratorio conectado a la demo que carga un artefacto e informa predicciones sobre casos ficticios. La reproducción limpia completa del paquete ML todavía debe verificarse como entregable, no presumirse a partir de las pruebas de la aplicación.

V2 redujo falsas alertas respecto a v1 en la misma cohorte final, pero omitió más atrasos y no superó a la referencia mayoritaria en accuracy. Su recall y F1 son distintos de cero, pero eso no demuestra utilidad financiera, calibración para clientes reales ni reducción del 5 % referencial de pérdidas. No se declara alcanzada una meta de negocio que aún no ha sido acordada y medida.

La simulación preserva reglas temporales y contables del escenario y evita usar el desenlace futuro como predictor. Sin embargo, la coherencia verificable de montos y pagos no demuestra que el volumen y las probabilidades representen al negocio. Faltan fuentes para calibrar esos supuestos. El EDA añadido es descriptivo de entrenamiento y no se utiliza para volver a ajustar sobre la cohorte final ya consultada.

Las brechas prioritarias para la entrega son: calibración verificable de la simulación, CV agrupada, comparación de sobreajuste y candidatos, meta y costos de negocio, empaquetado reproducible del entrenamiento y validación humana del informe. La inspección añadió coeficientes e inferencia de un vector ilustrativo nuevo, sin corregir retrospectivamente el protocolo v2. Los pendientes impiden presentar el borrador como cumplimiento total de la rúbrica.

La proyección a PROY consiste en completar esa evaluación y la integración operativa de forma controlada, mejorar los datos con captura real consentida cuando sea viable y medir resultados observados. El sistema apoya al propietario; no sustituye su decisión ni permite tratar un cliente sin historial como un riesgo demostrado.

## Control de versión y alcance

Este borrador utiliza los reportes congelados de ejecución-02 y experimento-v2; sus métricas no se han reentrenado ni reemplazado para favorecer conclusiones. Las 126 pruebas backend y las pruebas de caída del servidor son evidencias de software separadas, no precisión del modelo ni aceptación humana. Se citan como anexo complementario, sin trasladarlas retrospectivamente a APF2.

El Anexo C lista los bloqueos antes de entregar. No se asignan firmas, conformidades, tareas ejecutadas o revisiones a integrantes sin su confirmación. El grupo debe completar el Anexo de IA con los prompts realmente utilizados y verificar datos, gráficos, métricas, código y redacción.

<!-- PAGE -->

# Referencias

Autoridad Nacional de Protección de Datos Personales. (2011, 3 de julio). Ley N.° 29733 - 2011: Ley de protección de datos personales. Gob.pe. https://www.gob.pe/institucion/anpd/normas-legales/2018427-29733-2011

Autoridad Nacional de Protección de Datos Personales. (2024, 30 de noviembre). Decreto Supremo N.° 16-2024-JUS: Reglamento de la Ley N.° 29733, Ley de Protección de Datos Personales. Gob.pe. https://www.gob.pe/institucion/anpd/normas-legales/6554453-16-2024-jus

Grupo 2. (2026a). Diagnóstico de Innovación y Transformación Digital de una MiPYME Peruana Real: Cervecería Baylón [Avance de Proyecto Formativo 1, Universidad Tecnológica del Perú]. Documento aportado por el grupo.

Grupo 2. (2026b). Propuesta Metodológica de Innovación y Hoja de Ruta Ágil para la MiPYME: MVP de la aplicación Credify para el fiado a un día en Cervecería Baylón [Avance de Proyecto Formativo 2, Universidad Tecnológica del Perú]. Documento aportado por el grupo.

Universidad Tecnológica del Perú. (2026). Consigna APF3 - 2026-2: Solución de Machine Learning para la MiPYME [Consigna de evaluación aportada por el grupo].

Universidad Tecnológica del Perú. (2026). Taller práctico: Semana 14. Machine Learning para una MYPE: el caso Bodega Doña Rosa [Material de clase aportado por el grupo].

Scikit-learn developers. (s. f.). Pipelines and composite estimators. Scikit-learn documentation. https://scikit-learn.org/stable/modules/compose.html

Scikit-learn developers. (s. f.). Cross-validation: evaluating estimator performance. Scikit-learn documentation. https://scikit-learn.org/stable/modules/cross_validation.html

**Fuentes técnicas internas.** `academic_synthetic_report.json`, `protocol.json`, `frozen_selection.json`, `experiment_v2_report.json`, `final_errors_not_for_tuning.json` y `verificacion-laboratorio.json`. Son registros del experimento, no publicaciones externas. Sus copias y hashes se incluyen en el paquete; las fechas originales no se reescriben.

**Fuentes primarias heredadas.** Entrevista del 28/08/2026 y revalidación del 08/10/2026, según APF1/APF2 aportados. No se realizó una nueva entrevista para redactar este borrador y no se atribuyen parámetros adicionales a esas conversaciones.

<!-- PAGE -->

# Anexo A. Diccionario y procedencia del dataset

Todos los registros exportados en este paquete llevan `origen=simulado`. Los rangos son controles del escenario actual, no límites autorizados para producción. Los metadatos no entran al modelo.

| Variable | Tipo/unidad | Descripción y rango válido del escenario |
| --- | --- | --- |
| completed_sales | Entero, ventas | Ventas previas; ≥ 0 |
| paid_credits | Entero, fiados | Fiados pagados completos antes de evaluar; ≥ 0 |
| paid_late | Entero, fiados | Pagados completos con atraso; 0 a paid_credits |
| pending_overdue | Entero, fiados | Activos vencidos al evaluar; ≥ 0 |
| pending_current | Entero, fiados | Activos no vencidos al evaluar; ≥ 0 |
| outstanding | Decimal, PEN | Deuda previa; 0 a cupo simulado de S/ 200 |
| utilization | Decimal, ratio | outstanding / cupo; 0 a 1 |
| requested_ratio | Decimal, ratio | Monto solicitado / cupo; > 0 y ≤ 1 |
| tenure_days | Entero, días | Antigüedad al evaluar; ≥ 0 |
| punctuality_rate | Decimal, ratio | Pagos completos puntuales / pagados; 0 a 1; cero sin historial |
| overdue_rate | Decimal, ratio | Vencidos activos / activos; 0 a 1; cero sin activos |
| late_payment | Binario/ausente | 0 puntual, 1 atraso, vacío sin desenlace |
| origen / data_source | Categoría | simulado / synthetic; solo procedencia |
| loan_id / client_id | Texto ficticio | Auditoría y agrupación; excluidos del vector |
| evaluated_at / due_date / observed_on | Fecha/hora | Evaluación, vencimiento y corte ficticios |
| split | Categoría | Partición original; su test ya fue consultado |
| scenario / pending_at_cutoff | Categoría / PEN | Auditoría posterior; potencial fuga, excluidos |
| requested_amount / credit_cap | PEN | Componentes del ratio; no predictores adicionales |

`dataset_desarrollo_simulado.csv` conserva 1622 filas, incluidos 24 targets vacíos, para auditoría. Los modelos originales utilizaron solo las 1598 etiquetadas según su partición. El agregado de `origen` es documental y no implica haber reentrenado el artefacto. Los IDs son inventados desde la generación, no seudónimos de clientes reales.

<!-- PAGE -->

# Anexo B. Reproducibilidad e integración

## B.1. Artefactos y código existente

| Archivo o ruta | Función y alcance |
| --- | --- |
| backend/app/ml/synthetic.py | Simulación y controles lógicos/temporales |
| backend/scripts/academic_credit_pilot.py | Comparación inicial y exportación v1 |
| backend/scripts/academic_credit_experiment_v2.py | Búsqueda holdout, congelamiento y final nuevo |
| backend/app/api/routes/academic_ml.py | Carga con hash e inferencia autenticada |
| codigo/inspect_academic_artifact.py | Coeficientes e inferencia ilustrativa nueva, sin entrenamiento |
| evidencias/experiment_v2_report.json | Métricas finales, versión y hash del artefacto |
| evidencias/validation_search.json | 130 combinaciones de validación, no CV |
| artefactos/academic_model_v2.joblib | Pipeline ya entrenado; cargar solo si se confía en el origen |
| manifest.json | Hashes de fuentes y archivos de este paquete |

El generador de este informe lee resultados congelados, agrega procedencia, calcula EDA de entrenamiento y construye documentos. No entrena ni despliega servicios. El paquete incluye un script de inferencia local, su entrada JSON y dependencias separadas; no equivale al entregable completo de entrenamiento ejecutado en entorno limpio, que sigue pendiente.

## B.2. Captura de integración académica

![Figura 3. Laboratorio académico en escritorio; evidencia técnica del 29/10/2026, con casos ficticios.](figuras/laboratorio-desktop.png)

Fuente: `verificacion-laboratorio.json`, cinco comprobaciones aprobadas. La captura móvil y el JSON se adjuntan en `evidencias/`. No son una sesión del propietario ni prueban validez predictiva real. No se ejecutó una nueva comprobación pública para redactar este informe.

<!-- PAGE -->

# Anexo C. Pendientes de entrega y registro de IA

## C.1. Lista de cierre

| Requisito pendiente | Evidencia necesaria antes de declarar cumplimiento |
| --- | --- |
| Fuente y escala de simulación | Fuente verificable por parámetro y contraste con APF1 |
| Meta y costo de errores | Justificación del grupo y acuerdo real cuando se atribuya al propietario |
| Segundo algoritmo U3 | Confirmación de aceptación de Random Forest o comparación permitida |
| Validación cruzada y sobreajuste | CV agrupada en entrenamiento y métricas train/validación |
| Comparación final completa | Nuevo protocolo, candidatos fijados y test independiente reservado |
| Entorno limpio y requisitos | Paquete ML ejecutado de inicio a fin; versiones fijadas |
| Datos personales para piloto futuro | Controles pendientes de APF2 verificados, sin presumir cierre |
| Material final | PDF con cuerpo ≤ 15 páginas, código, requisitos y ≤ 13 diapositivas |
| Revisión humana | Registro individual realmente completado, sin firmas fabricadas |

## C.2. Uso de IA en esta preparación

Se utilizó OpenCode para revisar artefactos, redactar este borrador y generar documentos/EDA. La herramienta y el modelo exactos deben cotejarse con el historial de cada sesión; no se extrapolan los modelos declarados en APF2 a toda la asistencia posterior.

Prompt literal de inicio aportado por la usuaria: «resgistros ficticios empieza con la creacion del informe del avance 3». Resultado: primer borrador con resultados existentes y limitaciones. Controles automáticos: hashes de artefactos, concordancia de conteos y métricas, origen de filas y estructura documental. Estos controles no equivalen a validación humana.

**Pendiente del grupo:** completar el registro con los prompts de simulación, entrenamiento, depuración y conclusiones realmente utilizados en sesiones anteriores; indicar herramienta/modelo, fecha verificable, uso, responsable y comprobación humana aplicada. No sustituirlos por prompts retrospectivos inventados.

| Integrante | Qué revisó | Resultado/corrección | Fecha |
| --- | --- | --- | --- |
| Omara Baylón | PENDIENTE | PENDIENTE | PENDIENTE |
| Tamara Coveñas | PENDIENTE | PENDIENTE | PENDIENTE |
| César Paredes | PENDIENTE | PENDIENTE | PENDIENTE |
| Pablo Yman | PENDIENTE | PENDIENTE | PENDIENTE |

Las fichas humanas de APF2 no validan el modelo académico posterior. Las pruebas reales de fallos del backend se conservan en un paquete independiente como anexo complementario; no reemplazan entrenamiento, evaluación, integración ML o revisión humana de APF3.

<!-- PAGE -->

# Anexo D. Transferencia del taller a Cervecería Baylón

El notebook de Doña Rosa conserva las 160 filas del taller, ocho atributos y `moroso=1` cuando el retraso supera siete días. Se ejecutaron 12 celdas de código y tres figuras sin errores, según `verificacion-taller.json`. Es una actividad académica diferente del experimento de Baylón.

| Modelo del taller | Accuracy | Precision | Recall | F1 |
| --- | --- | --- | --- | --- |
| SVM lineal | 0,950 | 0,917 | 0,917 | 0,917 |
| KNN, k=3 | 0,900 | 0,900 | 0,750 | 0,818 |
| Árbol, profundidad 3 | 0,800 | 0,611 | 0,917 | 0,733 |
| AdaBoost, 50 rondas | 0,950 | 0,917 | 0,917 | 0,917 |

AdaBoost y SVM empataron en esas métricas. El árbol alcanzó igual recall, pero generó siete falsas alertas frente a una de AdaBoost. Por ello no se sostiene elegirlo solo por interpretabilidad antes de comparar. En el taller se eligió AdaBoost con 50 rondas; el top 10 tuvo precision de 90 % y cobertura de 75 %, distintas del recall del clasificador. El descenso con 400 rondas ilustra sobreajuste en esa partición, no que Boosting siempre sobreajuste.

| Aspecto | Transferencia correcta al proyecto |
| --- | --- |
| Datos y target | Mantener once variables de APF2 y atraso al vencimiento del fiado a un día; no renombrar moroso |
| Registros disponibles | Ficticios declarados; 30–50 reales era una meta, no una muestra conseguida |
| Modelos | Árbol y SVM son candidatos pertinentes, no modelos ya comparados o elegidos en Baylón |
| Ajuste y test | Pipeline y CV dentro de entrenamiento; no repetir selección sobre el test como en los retos |
| Capacidad | Acordar acción y volumen de revisiones con el propietario; no copiar diez llamadas |
| Ética | No equiparar falta de historial con incumplimiento; registrar y auditar decisiones humanas |

La copia ejecutada del taller y su hash constan en el paquete. No se traslada el 95 % de accuracy a Baylón, no se inserta el modelo de la bodega en producción y no se afirma que el plan de réplica ya haya sido implementado. La comparación metodológica corregida es el siguiente trabajo técnico, separado de la redacción de este borrador.
