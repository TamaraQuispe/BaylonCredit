# Solución de Machine Learning para el fiado a un día en Cervecería Baylón

## Avance de Proyecto Formativo 3 · Grupo 2 · Estudio alineado V4

Facultad de Ingeniería de Sistemas e Informática · Universidad Tecnológica del Perú

Caso 4: Scoring crediticio alternativo con IA para el fiado y microcrédito MYPE

| Integrante | Código |
| --- | --- |
| Omara Yamileth Baylón Vila | U23231338 |
| Tamara Alison Coveñas Quispe | U23204737 |
| César Augusto Daniel Paredes Paredes | U23259768 |
| Pablo Enrique Yman Avila | U23251279 |

Docente: Caman Sanchez, Richard Enrique · Sección 35036 · Lima, Perú · 2026-2

**Versión documental:** V4, 14 de noviembre de 2026. Base técnica: `academic-owner-aligned-v4`; reporte congelado el 14/11/2026 a las 20:20:53,604359 UTC. Organización conforme a las siete secciones del informe: resumen y continuidad; datos; modelado; evaluación; integración; normativa y proyección; conclusiones.

**Extensión planificada:** portada y 14 páginas manuales de cuerpo, 15 antes de referencias y anexos. Los separadores no certifican páginas físicas; la exportación deberá comprobar el máximo de 15 páginas de este bloque, sin desbordes tras insertar el EDA. Referencias y anexos quedan fuera del cuerpo.

**Alcance académico.** Cero filas reales en entrenamiento o evaluación. Se documenta un estudio sintético ya congelado, alineado parcialmente con agregados declarados por Rildo, no una validación predictiva real. Esta redacción solo consulta archivos guardados: no genera experimentos, entrena ni ejecuta inferencia. No acredita ahorro, calibración de riesgo real, aprobación del propietario, revisión humana completada ni despliegue V4. La reproducción limpia permanece pendiente.

<!-- PAGE -->

# 1. Resumen ejecutivo y continuidad

## 1.1. Continuidad con APF1 y APF2

Cervecería Baylón es un negocio familiar de San Martín de Porres, Lima, operado por dos propietarios. APF1 identificó la administración del fiado a un día mediante cuaderno y criterio personal; APF2 desarrolló Credify, un MVP con clientes, reglas preliminares, fiados, abonos e historial persistente. Se mantienen empresa, equipo, problema y unidad de análisis. Lean Startup y Kanban organizan la evolución, pero no sustituyen evidencia predictiva (Grupo 2, 2026a, 2026b).

Al cierre documentado de APF2 el piloto real no había empezado y la exportación devolvió cero fiados elegibles; ello no prueba ausencia de otras operaciones del negocio. V4 tampoco cumple la captura prevista de 30 a 50 fiados reales. La declaración actual del propietario aporta agregados de calibración, no filas de clientes para aprender o evaluar.

## 1.2. Problema y resultado congelado

**Para los propietarios, se propone anticipar si un fiado otorgado tendrá atraso frente al vencimiento contractual de un día, usando exclusivamente el historial visible antes de otorgarlo, para priorizar revisión humana.** Es clasificación binaria supervisada por fiado: `late_payment=1` significa atraso, no pérdida permanente. Una alerta no rechaza automáticamente una solicitud.

Desarrollo contiene dos historias sintéticas alternativas de 12 clientes cada una: 559 fiados de estudio, 552 resueltos y siete desconocidos. No son 559 operaciones reales ni dos sucursales sumables. FINAL es otro mundo alternativo de 12 clientes: 260 fiados de estudio, 259 evaluables y uno desconocido. El calentamiento queda fuera de las filas supervisadas.

El criterio previo maximiza F2 OOF de la política de revisión con máximo cinco alertas por réplica y día. Ganó la **SVM lineal, C=1, balanced, umbral 0,10**, con F2 OOF 0,55921 frente a 0,53165 del árbol. En FINAL logra F2 0,70115, detecta 61 de 65 atrasos y genera 114 falsas alertas conocidas. Son 176 revisiones hipotéticas, incluida una sin etiqueta.

La SVM supera descriptivamente a las dos políticas Dummy en F2 final y respeta el tope de alertas. **El árbol obtiene mejor F2 final, 0,71096; no se cambia la selección después del test.** El Dummy mayoritario conserva mayor accuracy, 0,74903 frente a 0,54440 de SVM; revisar todo detecta más atrasos. No hay dominancia universal ni beneficio financiero demostrado.

<!-- PAGE -->

# 2. Datos, procedencia y alcance

## 2.1. Una fuente declarada, no un dataset real

La única fuente comercial de calibración es la declaración actual de Rildo, consulta declarada del 08/10/2026 sobre septiembre de 2026, identificada por SHA-256 `45bc22a10ad5dccf323708b8aeabb780d8de4629ff5087cca2582c7dd055819f`. Combina recuerdo y revisión parcial del cuaderno: es aproximada, no auditada independientemente. El formulario anterior enteramente hipotético está excluido como evidencia y como base de calibración. No se usan filas CV3, v2, tests anteriores ni del caso docente Doña Rosa.

De 48 anotaciones revisadas, tres no tenían desenlace: **45 evaluables, ocho atrasos, 8/45=17,78 %**. Los diez registros con abonos parciales usan otro denominador, **10/48=20,83 %**, no 10/45. La fuente estima unos 12 fiados y nueve clientes distintos por semana, retorno usual siete días, rango 3 a 14; monto típico S/ 20, rango S/ 5 a S/ 50 y exposición máxima S/ 80. S/ 20 es una estimación típica, no una media empírica.

## 2.2. Cohortes del estudio congelado

| Mundo alternativo | Clientes ficticios | Fiados de estudio | Resueltos | Clase 0 / 1 | Desconocidos | Calentamiento excluido |
| --- | --- | --- | --- | --- | --- | --- |
| DEV D1 | 12 | 278 | 274 | 233 / 41 | 4 | 43 |
| DEV D2 | 12 | 281 | 278 | 251 / 27 | 3 | 46 |
| DEV combinado para ML | 24 | 559 | 552 | 484 / 68 | 7 | 89 |
| FINAL, separado | 12 | 260 | 259 | 194 / 65 | 1 | 42 |

Las sumas DEV describen un corpus de aprendizaje de alternativas, no volumen comercial simultáneo ni información real adicional. Los 12 clientes FINAL son distintos de los 24 identificadores DEV. La separación por cliente no convierte la simulación en validación externa.

El calendario ficticio comienza con cuatro semanas de calentamiento desde el 16/03/2026; el estudio va del 13/04 al 30/09/2026, 24 semanas completas y tres días. Extrapolar una declaración de septiembre a meses anteriores supone estacionariedad, no observación real retrospectiva. Población total de 12, calentamiento, calendario y distribuciones latentes son hipótesis no medidas; el Anexo A las separa de los agregados declarados.

<!-- PAGE -->

## 2.3. Variables, desenlace y preparación

Se mantienen once predictores del MVP en el orden congelado. Cada fila corresponde a un fiado efectivamente otorgado en la simulación y a su snapshot previo. Solo se modelan ventas vinculadas a esos fiados; no se inventa un conteo de ventas al contado.

| Predictor | Unidad | Definición previa al otorgamiento |
| --- | --- | --- |
| completed_sales | Conteo | Ventas completadas vinculadas a fiados previos |
| paid_credits | Conteo | Fiados pagados completamente |
| paid_late | Conteo | Fiados completos pagados tarde |
| pending_overdue | Conteo | Fiados activos vencidos |
| pending_current | Conteo | Fiados activos no vencidos |
| outstanding | PEN | Deuda pendiente previa |
| utilization | Ratio | Deuda previa / cupo S/ 80 |
| requested_ratio | Ratio | Monto solicitado / cupo S/ 80 |
| tenure_days | Días | Antigüedad del cliente al evaluar |
| punctuality_rate | Ratio | Pagados puntuales / pagados completos |
| overdue_rate | Ratio | Activos vencidos / activos totales |

Sin pagos completos, `punctuality_rate=0`, interpretado junto con `paid_credits`, no como atraso probado; sin activos, `overdue_rate=0`. Se excluyen IDs, réplica, fechas, propensión latente, plan futuro, desenlace, score previo y saldos al corte del vector predictor. `client_id` solo agrupa particiones; réplica y fecha civil solo delimitan capacidad.

La etiqueta se **deriva de eventos de pago y vencimiento**, no de copiar un score o la propensión latente. El contrato vence al siguiente día calendario; los pagos puntuales generados ocurren a más tardar a las 20:00. El cierre aproximado no incorpora un nuevo campo temporal al MVP. Los tres días de gracia declarados no convierten un pago tardío en clase 0. Un desenlace no observable conserva etiqueta desconocida: no se imputa ni entra en Pipeline, búsqueda o métricas supervisadas.

Árbol y SVM usan `SimpleImputer(strategy="median")` y `StandardScaler` en Pipeline, ajustados solo dentro de cada entrenamiento. En SVM el Pipeline queda dentro del estimador calibrado también en las particiones internas. Escalar el árbol da procesamiento común, no una necesidad del algoritmo. Imputar predictores es una salvaguarda de contrato, no imputar outcomes. Los controles comprueban esquema, finitud, IDs y snapshots sin eventos futuros; snapshots iguales no se borran por sí solos.

<!-- PAGE -->

## 2.4. EDA DEV: balance, escala y suficiencia

El EDA utiliza exclusivamente las **552 filas resueltas de desarrollo**, guardadas en `development_rows.json`: no calentamiento, desconocidos ni FINAL. Las figuras y la tabla se preparan durante el empaquetado desde ese caché, sin generar operaciones ni ajustar modelos. Se documenta el estudio ya terminado, no se presenta el EDA como una exploración prospectiva anterior a la corrida.

![Figura 1. Balance de late_payment en las 552 filas DEV resueltas, dos historias alternativas.](figuras/eda_balance.png)

**Balance.** Hay 484 puntuales, 87,68 %, y 68 atrasos, 12,32 %. Predecir siempre clase 0 obtiene accuracy 0,87681 en DEV sin detectar atrasos. Por ello se comparan precisión, recall, F1 y F2 positivos, además de accuracy. No se fuerza la prevalencia a reproducir 17,78 % de la declaración.

{{eda_table}}

Los estadísticos descriptivos de la tabla deben conservar unidades y denominadores de DEV; no se usa FINAL para completar vacíos. `requested_ratio` representa el monto relativo, no añade un duodécimo predictor. Los extremos acotados son parte del escenario, no evidencia para eliminar clientes futuros.

**Suficiencia con reservas.** D1 tiene 41 atrasos; D2 solo 27, por debajo de la referencia orientativa de 30 minoritarios, y su auditoría marca `adequate=false`. El combinado tiene 68 minoritarios y 552 etiquetas, pero esa suma no elimina la insuficiencia por réplica ni crea 552 personas independientes. FINAL tiene 65 atrasos y 259 etiquetas en solo 12 clientes.

Los umbrales orientativos de 200 filas y 30 minoritarios son banderas descriptivas, no demostración estadística de suficiencia, ni razón para regenerar o alterar etiquetas. Las tres historias pasan los controles duros y de escala del protocolo; pasar esas auditorías comprueba coherencia con restricciones elegidas, no representatividad de toda la empresa ni validez de cada distribución.

<!-- PAGE -->

## 2.5. EDA DEV: historial y exposición

Se examinan dos relaciones pertinentes: historial de pagos tardíos frente al atraso del fiado nuevo y exposición previa frente a ese atraso. Los gráficos deben conservar denominadores por banda; las bandas son descriptivas, no reglas crediticias ni umbrales adicionales.

![Figura 2. Relaciones de historial y exposición con late_payment en DEV resuelto, sin filas FINAL.](figuras/eda_relaciones.png)

**Conclusión sobre historial.** {{history_conclusion}}

La persistencia puede surgir porque el generador asigna una propensión estable por cliente. Esa estabilidad es una hipótesis sintética no medida, nunca un predictor. Por tanto, una asociación favorable a `paid_late` o puntualidad no confirma su magnitud en personas reales. Carecer de historial no equivale a ser moroso.

**Conclusión sobre exposición.** {{exposure_conclusion}}

La deuda y la utilización son previas al nuevo fiado; con cupo constante, `utilization=outstanding/80`, por lo que no son señales independientes. La relación atraso-exposición también está condicionada por la política que deja fuera solicitudes no otorgadas. No permite atribuir causalidad al cupo ni estimar desenlaces de solicitudes rechazadas.

Las operaciones repetidas de un cliente son dependientes. La CV agrupa clientes, pero no es una evaluación temporal prospectiva ni una prueba dejando fuera mundos completos. Una separación por cliente no corrige por sí sola la hipótesis de estacionariedad entre marzo y septiembre. Si las bandas son pequeñas o no monotónicas, se conserva ese resultado sin corregir el generador.

Los tres únicos gráficos del informe son los dos EDA y la matriz final. La matriz se construirá desde la métrica congelada de SVM, no mediante nuevas predicciones. La construcción e inserción de figuras queda fuera de esta edición documental.

<!-- PAGE -->

# 3. Modelado y comparación V4

## 3.1. Búsqueda y validación agrupada

Se comparan árbol de decisión, inspeccionable mediante reglas y capaz de cortes no lineales, y SVM lineal, frontera regularizada sobre variables estandarizadas. Dos Dummy permiten detectar la utilidad aparente de acertar la clase frecuente o alertar siempre. Ningún ganador se importa de otro estudio.

| Componente | Protocolo congelado V4 |
| --- | --- |
| Árbol | max_depth: 2, 3, 4; min_samples_leaf: 8, 16; class_weight: None, balanced |
| SVM lineal | C: 0,1; 1; 10; class_weight: None, balanced; probability=False |
| Estimadores | random_state=42 |
| Umbrales | 0,10; 0,20; 0,30; 0,40; 0,50; 0,60; 0,70 |
| CV externa | StratifiedGroupKFold, shuffle=True, grupo client_id, semilla 20261122 |
| Cantidad de pliegues | Preferir 3; fallback 2 solo por adecuación de clases; detener si ninguno sirve |
| Calibración SVM | Sigmoide agrupada, ensemble=False; preferir 3, fallback 2; semilla 20261123 |
| Referencias | Dummy most_frequent y constant=1; umbral 0,50 |

Son **18 configuraciones**, 12 de árbol y seis SVM, por siete umbrales: 126 combinaciones, no 126 algoritmos. La alternativa de dos pliegues depende de que cada entrenamiento/validación tenga ambas clases, nunca de scores o FINAL.

## 3.2. Pliegues realmente utilizados

`fold_audit.json` registra **tres pliegues externos**: cada uno entrena con 368 filas y 16 clientes, valida con 184 filas y ocho clientes; los clientes son disjuntos. Las tres calibraciones internas de entrenamientos externos usan **tres pliegues cada una**, y el reajuste SVM con DEV completo usa también tres internos. No fue necesario el fallback. El Anexo B conserva los tamaños internos reales.

Cada fila recibe un score OOF de un ajuste que no vio a su cliente. La sigmoide se calibra únicamente dentro del entrenamiento externo y el preprocesamiento permanece dentro de los estimadores internos. Esto es calibración anidada, **no evaluación anidada independiente de la búsqueda de hiperparámetros**. Reutilizar OOF para elegir configuración y umbral produce optimismo en el ganador. La calibración sintética no certifica probabilidades de riesgo para clientes reales.

<!-- PAGE -->

## 3.3. Política primaria y selección congelada

Primero se aplica `probability >= threshold`. Después, para cada clave **réplica + fecha civil de evaluación**, se ordenan alertas por score descendente y, en empate, por `loan_id` ficticio; se revisan como máximo cinco. D1 y D2 nunca compiten por una misma cola: son alternativas, no sucursales. El resultado de política es `review=1`, distinto conceptualmente de `predicted=1`.

El objetivo primario es maximizar **F2 OOF de la política ya limitada**, `F2=5TP/(5TP+4FN+FP)`. No existe piso de precisión 0,50 en V4. Los desempates son recall de revisión, precisión, F1, menos revisiones, candidato anterior en la grilla y umbral más cercano a 0,50, en ese orden.

La prioridad cualitativa de no omitir atrasos y la estimación de cinco revisiones/día informan el diseño. F2, sus pesos y la meta de superar referencias son decisiones de investigación del equipo, no una razón de costos medida ni una meta de recall aprobada por Rildo. Dos minutos por revisión y cinco casos/día son estimaciones, no capacidad cronometrada ni aprobación de diez minutos totales de trabajo.

| Candidato fijado | Configuración | Umbral | Precisión política OOF | Recall | F2 | Revisiones OOF |
| --- | --- | --- | --- | --- | --- | --- |
| Árbol, índice 0 | Profundidad 2, hoja 8, sin pesos | 0,10 | 0,34146 | 0,61765 | 0,53165 | 123 |
| SVM, índice 15 | Lineal, C=1, balanced | 0,10 | 0,27717 | 0,75000 | 0,55921 | 184 |
| Dummy mayoritario | most_frequent | 0,50 | 0,00000 | 0,00000 | 0,00000 | 0 |
| Dummy positivo | constant=1, con tope | 0,50 | 0,12454 | 1,00000 | 0,41565 | 546 |

En OOF la cola contiene solo los 552 resueltos: **omite competencia por capacidad de los siete desconocidos**, limitación expresa. El tope no retira alertas de los dos candidatos ML en esta corrida; sí retira seis del Dummy positivo. Las 184 revisiones SVM suman 95 D1 y 89 D2 solo como conteo del corpus alternativo, no como carga conjunta de un negocio.

`frozen_selection.json` registra la decisión del **14/11/2026, 20:20:53,285017 UTC**, junto con hashes y contrato. Antes de generar FINAL se fijaron protocolo, calibración, datos DEV, búsqueda, modelos y umbrales. La semilla FINAL 2026112103 ya estaba declarada. Se conserva SVM aunque el árbol resulte mejor en FINAL; no se retocan semillas, umbrales o criterio al ver el test.

<!-- PAGE -->

## 3.4. Entrenamiento, OOF y FINAL: clasificador bruto

Train corresponde al modelo reajustado con las 552 etiquetas DEV; OOF agrega scores de los ajustes externos; FINAL usa las mismas 259 etiquetas conocidas para los cuatro modelos. **Esta tabla es del clasificador bruto al umbral, antes del tope diario**, no de revisar todo con capacidad. Valores redondeados a cinco decimales; clase positiva: atraso.

| Modelo | Evaluación | Accuracy | Precisión | Recall | F1 | F2 |
| --- | --- | --- | --- | --- | --- | --- |
| Árbol, 0,10 | Train, n=552 | 0,79348 | 0,34028 | 0,72059 | 0,46226 | 0,58894 |
| Árbol, 0,10 | OOF, n=552 | 0,80616 | 0,34146 | 0,61765 | 0,43979 | 0,53165 |
| Árbol, 0,10 | FINAL, n=259 | 0,56757 | 0,36095 | 0,93846 | 0,52137 | 0,71096 |
| SVM, 0,10 | Train, n=552 | 0,76087 | 0,30247 | 0,72059 | 0,42609 | 0,56452 |
| SVM, 0,10 | OOF, n=552 | 0,72826 | 0,27717 | 0,75000 | 0,40476 | 0,55921 |
| SVM, 0,10 | FINAL, n=259 | 0,54440 | 0,34857 | 0,93846 | 0,50833 | 0,70115 |
| Dummy mayoritario | Train, n=552 | 0,87681 | 0,00000 | 0,00000 | 0,00000 | 0,00000 |
| Dummy mayoritario | OOF, n=552 | 0,87681 | 0,00000 | 0,00000 | 0,00000 | 0,00000 |
| Dummy mayoritario | FINAL, n=259 | 0,74903 | 0,00000 | 0,00000 | 0,00000 | 0,00000 |
| Dummy positivo bruto | Train, n=552 | 0,12319 | 0,12319 | 1,00000 | 0,21935 | 0,41262 |
| Dummy positivo bruto | OOF, n=552 | 0,12319 | 0,12319 | 1,00000 | 0,21935 | 0,41262 |
| Dummy positivo bruto | FINAL, n=259 | 0,25097 | 0,25097 | 1,00000 | 0,40123 | 0,62620 |

El árbol pierde F2 de train a OOF, 0,58894 a 0,53165; SVM pasa de 0,56452 a 0,55921, con recall OOF algo mayor. No basta esa cercanía para declarar ausencia de sobreajuste: el ganador reutiliza OOF para selección. Tampoco se deben diagnosticar causas solo con tres métricas agregadas.

En FINAL aumenta F2 y recall de ambos ML, pero baja accuracy; esto no prueba mejora temporal. La prevalencia cambia de 68/552=12,32 % en DEV a **65/259=25,10 % en FINAL**, frente a 8/45=17,78 % de la fuente declarada. El muestreo de solo 12 propensiones por mundo y la heterogeneidad latente permiten cambios de composición y prevalencia. No se fuerza el porcentaje de etiquetas ni se escoge otra semilla para acercarlo a la declaración. El aumento de F2 convive con peor Brier y AUC respecto de OOF.

<!-- PAGE -->

# 4. Evaluación e interpretación de negocio

## 4.1. Prueba final común: todas las métricas brutas

Los cuatro modelos congelados recibieron **un único lote por modelo con los 260 fiados de estudio FINAL**, incluido el desconocido para competir por capacidad. Las métricas utilizan solo los 259 conocidos: 194 clase 0 y 65 clase 1. El calentamiento de 42 fiados no integra este lote. Se reutilizan reporte y caché, sin inferencia adicional.

| Modelo bruto | Accuracy | Precisión | Recall | F1 | F2 |
| --- | --- | --- | --- | --- | --- |
| Árbol, umbral 0,10 | 0,56757 | 0,36095 | 0,93846 | 0,52137 | 0,71096 |
| SVM seleccionada, 0,10 | 0,54440 | 0,34857 | 0,93846 | 0,50833 | 0,70115 |
| Dummy mayoritario | 0,74903 | 0,00000 | 0,00000 | 0,00000 | 0,00000 |
| Dummy siempre positivo | 0,25097 | 0,25097 | 1,00000 | 0,40123 | 0,62620 |

| Modelo bruto | Balanced accuracy | ROC AUC | Brier | TN / FP / FN / TP | Alertas conocidas |
| --- | --- | --- | --- | --- | --- |
| Árbol | 0,69088 | 0,74492 | 0,16830 | 86 / 108 / 4 / 61 | 169 |
| SVM | 0,67542 | 0,75496 | 0,16296 | 80 / 114 / 4 / 61 | 175 |
| Dummy mayoritario | 0,50000 | 0,50000 | 0,25097 | 194 / 0 / 65 / 0 | 0 |
| Dummy positivo | 0,50000 | 0,50000 | 0,74903 | 0 / 194 / 0 / 65 | 259 |

**Resultado desfavorable conservado.** El árbol tiene mayor F2 final que SVM, seis falsas alertas menos y el mismo recall. Eso no autoriza reemplazar a SVM después de observar FINAL: el ganador se decidió con OOF de política, no con el test. SVM mantiene AUC algo mayor y Brier algo menor que el árbol, pero esas ventajas descriptivas no implican dominancia.

El Dummy mayoritario supera accuracy de ambos ML sin detectar un solo atraso; accuracy sola favorece la clase abundante. El Dummy positivo logra recall 1 antes del tope. La precisión cero sin alertas usa la convención `zero_division=0`. AUC describe ordenamiento; Brier, error cuadrático del score. Ninguna métrica valida calibración real ni ausencia de sesgo. No se calcularon intervalos ni significancia; 259 fiados no son 259 clientes independientes.

<!-- PAGE -->

## 4.2. Matriz SVM y política de capacidad

![Figura 3. Matriz final SVM V4, umbral 0,10, 259 etiquetas conocidas; métricas congeladas.](figuras/matriz_v4.png)

Filas: desenlace; columnas: predicción, orden 0 y 1. La matriz SVM es **[[80,114],[4,61]]**: 61 atrasos detectados, cuatro omitidos y 114 falsas alertas. En esta cohorte el tope no retira alertas SVM, por lo que su matriz de revisión coincide con la bruta. Hay 175 alertas conocidas y una desconocida: **176 revisiones**, no 175.

| Política FINAL, después del tope | Precisión | Recall | F1 | F2 | Accuracy |
| --- | --- | --- | --- | --- | --- |
| Árbol | 0,36095 | 0,93846 | 0,52137 | 0,71096 | 0,56757 |
| SVM seleccionada | 0,34857 | 0,93846 | 0,50833 | 0,70115 | 0,54440 |
| Dummy mayoritario | 0,00000 | 0,00000 | 0,00000 | 0,00000 | 0,74903 |
| Revisar todo, limitado | 0,25197 | 0,98462 | 0,40125 | 0,62257 | 0,26255 |

| Política | Revisiones total / conocidas / desconocidas | Máximo diario | Días con exceso antes del tope | TN / FP / FN / TP conocidos |
| --- | --- | --- | --- | --- |
| Árbol | 170 / 169 / 1 | 5 | 0 | 86 / 108 / 4 / 61 |
| SVM | 176 / 175 / 1 | 5 | 0 | 80 / 114 / 4 / 61 |
| Dummy mayoritario | 0 / 0 / 0 | 0 | 0 | 194 / 0 / 65 / 0 |
| Revisar todo, limitado | 255 / 254 / 1 | 5 | 5 | 4 / 190 / 1 / 64 |

Todas respetan cinco revisiones/día después del tope. Revisar todo bruto alerta los 260 casos; limitarlo deja 255 y cambia su F2 de **0,626204 a 0,622568**, su recall de 1 a 0,984615 y su precisión de 0,250965 a 0,251969. No deben mezclarse ambas evaluaciones.

La propuesta investigativa de superar ambas políticas Dummy en F2 final y respetar el tope se cumple descriptivamente para SVM. Frente a revisar todo limitado hay **79 revisiones menos**, `255-176`, equivalentes hipotéticamente a **158 minutos**, `79×2`, pero **tres falsos negativos adicionales**, cuatro frente a uno. No es ahorro demostrado. El alcance cubre solo alertas de fiados elegibles otorgados; no toda solicitud real, revisión obligatoria, cobranza, registro o trabajo humano. Tampoco mide el contrafactual de solicitudes rechazadas.

<!-- PAGE -->

## 4.3. Tres errores SVM del caché existente

Se transcriben los **primeros tres casos ya guardados** en `models.svm.error_cases` de `aligned_v4_report.json`, en su orden: FP, FP y FN. No se ejecutó inferencia ni se buscaron ejemplos para retocar el umbral. Son clientes y préstamos ficticios de FINAL, no evidencia de revisión humana.

| Cliente | Préstamo | Evaluación ficticia | Score guardado | Real / predicho / revisión | Error |
| --- | --- | --- | --- | --- | --- |
| AL4-T-C007 | AL4-T-L00043 | 14/04/2026, 09:00 | 0.1329226109003587 | 0 / 1 / 1 | FP |
| AL4-T-C010 | AL4-T-L00044 | 14/04/2026, 09:00 | 0.22751476849249946 | 0 / 1 / 1 | FP |
| AL4-T-C004 | AL4-T-L00045 | 15/04/2026, 09:00 | 0.07274632365606258 | 1 / 0 / 0 | FN |

**FP L00043.** Tenía tres ventas vinculadas, tres fiados pagados, uno tardío, puntualidad 2/3, antigüedad 178 días y ratio solicitado 0,169125. No tenía pendientes ni deuda. El score supera 0,10 pero el nuevo fiado resulta puntual. El historial tardío no determina el próximo desenlace.

**FP L00044.** Tenía tres ventas, tres fiados pagados, dos tardíos, puntualidad 1/3, antigüedad 154 días y ratio solicitado 0,1525. Tampoco tenía pendientes ni deuda. Produce una alerta mayor que el primer caso, pero paga puntualmente. La señal latente y la calibración no hacen determinista una operación individual.

**FN L00045.** Tenía cuatro ventas, cuatro fiados pagados, ninguno tardío, puntualidad 1, antigüedad 142 días y ratio solicitado 0,2365; pendientes y deuda cero. El score 0,07275 queda por debajo de 0,10, aunque el fiado termina atrasado. Una historia favorable no garantiza puntualidad.

En los tres casos `pending_overdue`, `pending_current`, `outstanding`, `utilization` y `overdue_rate` son cero. Las descripciones anteriores conservan las once entradas sin añadir escenarios no exportados. Son hipótesis interpretativas, no explicaciones causales. Dos FP muestran carga innecesaria y posible trato restrictivo si se usa mal la alerta; el FN muestra atraso sin priorización. Ninguno permite cambiar retrospectivamente el umbral. El caché registra 118 errores SVM conocidos en total, no solo estos tres.

El atraso puede recuperarse: no equivale a pérdida del principal. El 5 % financiero referencial de APF2, `pérdida mensual estimada / ventas del mes`, carecía de corroboración contable para un mes y no es prevalencia de atraso ni meta del modelo. No se usa para generar etiquetas ni se afirma haberlo reducido.

<!-- PAGE -->

## 4.4. Interpretación de los ajustes congelados

### Árbol alternativo: reglas en unidades originales

El árbol candidato fijado tiene profundidad 2, hoja mínima 8, sin pesos y umbral 0,10. El reporte devuelve cortes a unidades originales después de imputación. Su texto completo guardado es:

```text
|--- punctuality_rate <= 0.641711
|   |--- tenure_days <= 295.500002
|   |   |--- class: 1
|   |--- tenure_days >  295.500002
|   |   |--- class: 1
|--- punctuality_rate >  0.641711
|   |--- punctuality_rate <= 0.853571
|   |   |--- class: 0
|   |--- punctuality_rate >  0.853571
|   |   |--- class: 0
```

Una ruta completa combina puntualidad ≤ 64,1711 % y antigüedad ≤ 295,500002 días; imprime clase 1. Las hojas hermanas pueden compartir clase y aun así tener scores distintos. **La clase impresa no sustituye `probability >= 0.10` ni la cola posterior**; copiar clases de hoja no implementa la política V4. Son cortes aprendidos de ficción, no reglas comerciales validadas.

### SVM seleccionada: margen estandarizado

| Variable | Coeficiente exacto guardado |
| --- | --- |
| paid_late | 0.7769868642357229 |
| punctuality_rate | -0.28757567817416807 |
| pending_overdue | -0.15476913015262392 |
| outstanding | -0.10494144484861799 |

El margen es `m=b+Σ(w_j×z_j)`, con `b=-0.575638261272002` y `z_j` imputado y estandarizado con parámetros de entrenamiento. Los once coeficientes figuran en el Anexo B. La probabilidad sale después de la sigmoide calibrada; no de aplicar directamente estos pesos a datos crudos ni de interpretar `m` como porcentaje.

El signo negativo de vencidos se conserva aunque resulte contraintuitivo. Correlaciones, selección de fiados otorgados, escasez de estados y regularización impiden traducirlo a «más deuda reduce el riesgo». Los coeficientes no son causalidad ni importancia comercial independiente. `pending_current` tiene coeficiente cero en este ajuste, no prueba irrelevancia real. Las reglas y pesos no certifican equidad; no deben penalizar automáticamente falta de historial.

<!-- PAGE -->

# 5. Integración mínima con el MVP

## 5.1. Frontera real de la implementación

La demo heredada es https://demo-credify.168-75-71-113.sslip.io y el laboratorio `/laboratorio-academico` **sigue en v2, no en V4**. Las capturas previas no prueban disponibilidad actual, integración o aceptación V4. No se fabrican capturas, aprobaciones ni pruebas de interfaz nuevas.

La integración V4 es local y separada de la web: `predict(artifact_dir, input_data)` y CLI del runner `academic_credit_aligned_v4.py`. Carga el Pipeline confiable, verifica manifiesto/hashes y contrato de once campos, y aplica el umbral congelado. No es un endpoint de producción ni otorga créditos; conectar este contrato al MVP requiere pruebas y controles propios. No se midieron latencia, memoria o SLA V4.

## 5.2. Ejemplo nuevo, sin etiqueta conocida

Entrada y salida ya almacenadas en `illustrative_input.json` e `illustrative_output.json`; no se vuelven a inferir en esta redacción:

```json
{"features":{"completed_sales":6,"paid_credits":4,"paid_late":1,"pending_overdue":0,"pending_current":0,"outstanding":0,"utilization":0,"requested_ratio":0.25,"tenure_days":60,"punctuality_rate":0.75,"overdue_rate":0}}
```

```json
{"origen":"simulado","illustrative_only":true,"known_label":null,"family":"svm","probability":0.11922453881690649,"threshold":0.1,"predicted":1,"research_only":true,"business_approval":false}
```

Seis ventas vinculadas, cuatro fiados pagados y uno tardío dan puntualidad 0,75. Con cupo S/ 80, `requested_ratio=0.25` representa **S/ 20 solicitados**, no el cupo ni una media. La comprobación guardada de distinción respecto de las cohortes pasa. El score supera 0,10: es candidato a revisión, **no rechazo ni aprobación**. La asignación efectiva de revisión requiere todos los casos de ese día y su réplica; la salida individual solo aplica umbral. `known_label=null` no entra al predictor ni demuestra acierto.

El contrato admite números finitos no negativos y `null` para imputación de predictores, con conteos enteros, ratios válidos y `paid_late <= paid_credits`; no acepta el target como feature. La CLI de inferencia y el comando de reproducción se documentan, no se ejecutan, en el Anexo C. **La reproducción limpia V4 está pendiente**; no se hereda la verificación de versiones previas ni se atribuyen ahorros o calibración real al ejemplo.

<!-- PAGE -->

# 6. Normativa y proyección a PROY

Se mantienen la Ley N.° 29733 y su Reglamento aprobado por D.S. N.° 016-2024-JUS (ANPD, 2011, 2024). Este autodiagnóstico no acredita cumplimiento integral ni constituye dictamen jurídico. Las URLs oficiales son las heredadas; no se afirma una nueva verificación jurídica en esta redacción.

| Área | Control acotado actual | Pendiente antes de datos reales |
| --- | --- | --- |
| Finalidad y minimización | Once variables; sin identidades reales en las filas | Finalidad formal, información y base jurídica aplicable |
| Fuente y privacidad | Publicación solo de calibración agregada | Custodia restringida del formulario bruto, firmas y contactos; no publicarlo |
| Información y consentimiento | Declaración del propietario, no consentimiento de clientes | Evidencia de cada cliente cuando corresponda; verificar US09 de APF2 |
| Seguridad | Artefactos locales y hashes de integridad | Accesos, conservación, eliminación, ARCO y pruebas operativas |
| Terceros | Sin enviar este dataset a OpenRouter para inferencia | Revisar nube, proveedores, transferencias y responsabilidades |

Nombres académicos, formularios y firmas pueden ser datos personales aunque las cohortes sean ficticias. El permiso del propietario no sustituye consentimiento u otra base jurídica aplicable a cada cliente. HTTPS, quitar IDs y verificar hashes no certifican anonimización ni cumplimiento.

Para PROY se propone acordar finalidad, meta y costos reales antes del piloto; capturar de forma autorizada snapshots, desenlaces y acciones humanas; evaluar políticas con un test no consultado; y versionar datos, código y rollback. El reentrenamiento no está activo: frecuencia y promoción deben acordarse, con calidad, ambas clases, comparación contra baselines y revisión humana, no por calendario automático. Riesgos y responsables del Anexo D son propuestas.

# 7. Conclusiones

V4 completa una comparación propia árbol/SVM con dos Dummy, fuente agregada actual trazable, historias alternativas a escala declarada, Pipeline, CV por cliente, calibración interna agrupada y congelamiento antes de FINAL. La SVM seleccionada logra F2 de política final 0,70115 frente a 0 y 0,62257 de las referencias; respeta cinco alertas diarias y detecta 61/65 atrasos, pero produce 114 falsas alertas y omite cuatro. El árbol alcanza mejor F2 final, sin reemplazar al ganador OOF.

La meta investigativa propuesta se cumple en esta simulación, no una meta empresarial aprobada. La fuente es aproximada; distribuciones, estacionariedad y población siguen supuestas; D2 no llega a 30 minoritarios; FINAL tiene solo 12 clientes y prevalencia distinta. No hay validación externa, ahorro, consentimiento de clientes ni aceptación humana acreditados. La web sigue v2 y la reproducción limpia está pendiente. Los tres placeholders DEV y la maquetación deben cerrarse desde cachés, sin reabrir selección ni ocultar resultados desfavorables.

<!-- PAGE -->

# Referencias

Autoridad Nacional de Protección de Datos Personales. (2011, 3 de julio). Ley N.° 29733 - 2011: Ley de protección de datos personales. Gob.pe. https://www.gob.pe/institucion/anpd/normas-legales/2018427-29733-2011

Autoridad Nacional de Protección de Datos Personales. (2024, 30 de noviembre). Decreto Supremo N.° 16-2024-JUS: Reglamento de la Ley N.° 29733, Ley de Protección de Datos Personales. Gob.pe. https://www.gob.pe/institucion/anpd/normas-legales/6554453-16-2024-jus

Grupo 2. (2026a). Diagnóstico de Innovación y Transformación Digital de una MiPYME Peruana Real: Cervecería Baylón [Avance de Proyecto Formativo 1, Universidad Tecnológica del Perú]. Documento aportado por el grupo; continuidad, no dataset V4.

Grupo 2. (2026b). Propuesta Metodológica de Innovación y Hoja de Ruta Ágil para la MiPYME: MVP de la aplicación Credify para el fiado a un día en Cervecería Baylón [Avance de Proyecto Formativo 2, Universidad Tecnológica del Perú]. Documento aportado por el grupo; continuidad, no dataset V4.

Rildo. (2026, 8 de octubre; fecha de consulta declarada). Declaración del propietario sobre el fiado de Cervecería Baylón, periodo septiembre de 2026 [Formulario privado, recuerdo y revisión parcial del cuaderno]. Versión actual de `APF3_Ficha_Propietario_Baylon.docx`, SHA-256 `45bc22a10ad5dccf323708b8aeabb780d8de4629ff5087cca2582c7dd055819f`. Se divulgan solo agregados de `calibration.json`, no el formulario bruto ni datos de clientes.

Scikit-learn developers. (s. f.-a). Cross-validation: evaluating estimator performance. Scikit-learn documentation. https://scikit-learn.org/stable/modules/cross_validation.html

Scikit-learn developers. (s. f.-b). Pipelines and composite estimators. Scikit-learn documentation. https://scikit-learn.org/stable/modules/compose.html

Scikit-learn developers. (s. f.-c). Probability calibration. Scikit-learn documentation. https://scikit-learn.org/stable/modules/calibration.html

Universidad Tecnológica del Perú. (2026). Consigna APF3 - 2026-2: Solución de Machine Learning para la MiPYME [Consigna de evaluación aportada por el grupo].

**Fuentes técnicas internas V4.** Paquete local `APF3_Grupo2_Alineado_V4`, versión `academic-owner-aligned-v4`: `experimento/aligned_v4_report.json`, `protocol.json`, `calibration.json`, `frozen_selection.json`, `fold_audit.json`, `development_audits.json`, `final_audits.json`, `illustrative_input.json` e `illustrative_output.json`. Reporte emitido el 14/11/2026 a las 20:20:53,604359 UTC. Son registros técnicos internos, no publicaciones externas ni observaciones reales.

**Límite de las fuentes.** El documento CV3 se consultó solo para portada, cuatro códigos, continuidad APF1/APF2 y normativa, no como fuente de filas, parámetros, evidencia comercial o métricas V4. El formulario hipotético anterior queda excluido incluso como base. No se traslada ninguna cifra de evaluación de CV3, v2 o Doña Rosa. Las fuentes metodológicas explican técnicas, no calibran distribuciones del negocio.

<!-- PAGE -->

# Anexo A. Calibración y supuestos

## A.1. Matriz de procedencia comercial

| Parámetro | Declaración actual | Uso V4 y límite |
| --- | --- | --- |
| Atraso | 8 de 45 evaluables; tres desconocidos dentro de 48 | Ancla p=8/45, no porcentaje forzado de etiquetas |
| Abonos parciales | 10 de 48 anotaciones | Bernoulli 10/48; relación conjunta con atraso desconocida |
| Escala semanal | Aproximadamente 12 fiados y nueve clientes distintos | Agenda de 12 oportunidades, nueve asistentes por semana completa; otorgamientos pueden ser menores |
| Visitas | Usual siete días; rango 3 a 14 | Agenda con intervalos acotados; distribución de días supuesta |
| Monto típico | Estimación S/ 20 | Ancla log-localización ln(20), no media observada |
| Rango y exposición | S/ 5 a S/ 50; cupo S/ 80 | Solicitud/otorgamiento dentro de rango y exposición previa+nuevo ≤80 |
| Primer monto sin historial | Desconocido, null | No se inventa cupo inicial separado; S/ 50 es solo máximo general |
| Plazo y cierre | Un día calendario; cierre aproximado 20:00 | Pagos puntuales generados hasta las 20:00; no nuevo campo MVP |
| Gracia | Tres días | No cambia la etiqueta de atraso contractual |
| Demora tardía | Usual cuatro días, rango 1 a 15 | Lognormal truncada y redondeada; sigma no medida |
| Otorgar con vencidos | Abono previo o acuerdo, con revisión del propietario; excepciones no cuantificadas | Solo se simula la rama verificable de abono posterior al vencimiento; no frecuencia de acuerdos inventada |
| Capacidad | Estimación cinco revisiones/día, dos minutos/caso | Política hipotética de alertas, no medición ni costos aprobados |
| Objetivo comercial | Sin meta numérica de recall declarada | F2 y superar referencias son propuesta del equipo |

La fuente no es un conjunto de entrenamiento y no incluye snapshots individuales. No hay auditoría independiente del recuerdo ni cobertura completa del cuaderno. El hash identifica versión, no certifica veracidad. Ninguna distribución completa se atribuye al propietario.

## A.2. Hipótesis cuantitativas no medidas

| Elemento | Distribución o supuesto fijado |
| --- | --- |
| Población y calendario | 12 clientes/mundo, cuatro semanas de calentamiento, estacionariedad de marzo a septiembre |
| Antigüedad inicial | Rango de registro de 0 a 180 días; no antigüedades reales observadas |
| Agenda | Rotación de tres ausentes entre 12; nueve asisten; el grupo ausente la semana siguiente repite a los tres días; asignación de día aleatoria acotada |
| Montos | Lognormal por rechazo truncada a [5,50], log-localización ln(20), sigma logarítmica 0,45; luego limitada por exposición disponible |
| Heterogeneidad | Una propensión estable por cliente: Beta(p×3,(1-p)×3), p=8/45, concentración 3 |
| Parcialidad | Bernoulli 10/48 independiente del comportamiento tardío; independencia conjunta no observada |
| Plan parcial | Dos pagos del 50 %; si es tardío, probabilidad 0,5 de primer abono antes del vencimiento |
| Demora | Lognormal por rechazo, log-localización ln(4), sigma 0,55; redondeo a enteros de 1 a 15 días |

La heterogeneidad estable crea señal histórica potencial, no evidencia empírica de estabilidad. La propensión latente no se exporta como predictor ni se copia a la etiqueta. Esas decisiones estructurales influyen en qué modelos funcionan; alinear límites y un promedio probabilístico no valida su realismo.

<!-- PAGE -->

# Anexo A. Lógica de eventos y escala auditada

## A.3. Reglas del mundo sintético

Cada préstamo generado tiene un plan de pago completo eventual, incluso después del corte. Los parciales son dos pagos positivos que suman el monto. Solo son visibles los eventos ocurridos hasta el corte del 30/09/2026 y, para cada snapshot, estrictamente los previos a evaluar. No se inventa frecuencia de pérdida permanente, abandono o deuda incobrable; la recuperación eventual planificada limita cualquier análisis de pérdidas reales.

Si existe deuda vencida, se rechaza la solicitud salvo que **todos los préstamos vencidos** tengan ya un abono positivo **posterior a su vencimiento** y visible antes de la nueva evaluación; en ese caso se registra revisión simulada del propietario. Un abono anterior al vencimiento no basta. La declaración también menciona acuerdos, pero al no cuantificarse sus excepciones no se muestrean. Una revisión simulada no es una conformidad humana real.

Sin historial se registran identidad/referencia ficticias y revisión simulada, sin inventar un monto inicial distinto. Las ventas modeladas son solo las vinculadas a fiados otorgados; el historial de efectivo no está cuantificado. Las solicitudes no otorgadas no tienen desenlace crediticio observado para evaluar un modelo contrafactual.

## A.4. Auditorías de escala por mundo

| Medida guardada | D1 | D2 | FINAL |
| --- | --- | --- | --- |
| Oportunidades por semana completa | 12 | 12 | 12 |
| Clientes distintos agendados/semana completa | 9 | 9 | 9 |
| Media de otorgamientos/semana completa de estudio | 11,2917 | 11,5000 | 10,6667 |
| Media de clientes con otorgamiento/semana completa | 8,7917 | 8,8333 | 8,7500 |
| Intervalo entre visitas agendadas, mínimo/máximo, días | 3 / 14 | 3 / 14 | 3 / 14 |
| Media de intervalo agendado, días | 6,9456 | 6,9303 | 6,9512 |
| Solicitudes, incluido calentamiento | 343 | 342 | 340 |
| Otorgamientos, incluido calentamiento | 321 | 327 | 302 |
| Media de monto otorgado, incluido calentamiento, PEN | 22,0154 | 21,7908 | 20,5556 |
| Rango de monto otorgado observado, PEN | 7,55 a 49,42 | 6,39 a 49,40 | 5,73 a 48,69 |
| Restricciones duras / escala aproximada | Pasa / pasa | Pasa / pasa | Pasa / pasa |
| Minoritarios <30 / adecuación descriptiva | No / pasa | Sí, 27 / no pasa | No / pasa |

Las medias semanales usan solo 24 semanas completas, no dividen los totales que incluyen los tres días finales. Las medias monetarias usan **todos los otorgados, con calentamiento**, no solo el periodo de estudio; no se las denomina media del estudio. En FINAL, S/ 20,5556 no es la estimación típica declarada S/ 20 ni una media empírica comercial. Los límites fijados siguen siendo S/ 5 a S/ 50, no los mínimos/máximos casualmente observados.

Las negativas de política explican que 12 oportunidades no sean 12 otorgamientos; pueden alargar los intervalos entre fiados otorgados respecto de las visitas. El control de escala admite desviación relativa de 25 % en media de fiados respecto de 12 y absoluta de dos clientes respecto de nueve. DEV debía pasar antes de ajustar; FINAL se audita sin regenerarlo aunque falle. Aquí pasa, pero D2 conserva su bandera de minoritarios. No se fuerzan aprobaciones o etiquetas para corregir cifras.

<!-- PAGE -->

# Anexo B. Particiones e interpretación exacta

## B.1. Auditoría de pliegues realmente usados

Índices referidos al orden de las 552 filas resueltas de `development_rows.json`. Las siguientes cantidades son de `fold_audit.json`, no una inferencia desde el protocolo preferido.

| Partición | Pliegue | Entrenamiento | Validación | Clientes train / validación | Clientes disjuntos |
| --- | --- | --- | --- | --- | --- |
| Externa | 0 | 368 | 184 | 16 / 8 | Sí |
| Externa | 1 | 368 | 184 | 16 / 8 | Sí |
| Externa | 2 | 368 | 184 | 16 / 8 | Sí |

| Calibración SVM interna | Cantidad | Tamaños train/validación por pliegue 0; 1; 2 |
| --- | --- | --- |
| Entrenamiento externo 0 | 3 | 231/137; 254/114; 251/117 |
| Entrenamiento externo 1 | 3 | 249/119; 254/114; 233/135 |
| Entrenamiento externo 2 | 3 | 253/115; 251/117; 232/136 |
| Reajuste con DEV completo | 3 | 368/184; 368/184; 368/184 |

Todos los pliegues internos registran separación de clientes. La adecuación requiere ambas clases en cada train/validación; el fallback no selecciona resultados favorables. Ni FINAL ni los desconocidos participan en estas particiones. El diseño mide generalización a otros clientes sintéticos dentro de la fuente, no a meses futuros o negocios distintos.

## B.2. Once coeficientes SVM e intercepto

Transcripción de `models.svm.interpretation.standardized_coefficients` e `intercept`, del ajuste final en DEV. Son pesos del margen antes de la sigmoide, no coeficientes logísticos ni cambios directos de probabilidad.

| Campo | Valor exacto guardado |
| --- | --- |
| completed_sales | -0.0779973414774499 |
| paid_credits | -0.07582704795821067 |
| paid_late | 0.7769868642357229 |
| pending_overdue | -0.15476913015262392 |
| pending_current | 0.0 |
| outstanding | -0.10494144484861799 |
| utilization | -0.10494144484871142 |
| requested_ratio | -0.0377511292624871 |
| tenure_days | -0.02318614719681159 |
| punctuality_rate | -0.28757567817416807 |
| overdue_rate | -0.15476913015262392 |
| Intercepto | -0.575638261272002 |

La casi igualdad de deuda/utilización refleja su relación con cupo constante; no deben sumarse como dos efectos causales independientes. Las reglas completas del árbol están transcritas en el cuerpo, no sustituyen el Pipeline ni el umbral. No se modifica ningún artefacto al exportar texto o interpretar estos valores.

<!-- PAGE -->

# Anexo B. Métricas complementarias DEV

## B.3. Clasificador bruto antes del tope

Complemento de las tablas del cuerpo: las ocho evaluaciones siguientes tienen n=552, con 484 etiquetas 0 y 68 etiquetas 1. Así se conservan también balanced accuracy, ROC AUC, Brier y matrices brutas de train/OOF, sin atribuir AUC o Brier a la decisión binaria de revisión.

| Modelo | Evaluación | Balanced accuracy | ROC AUC | Brier | TN / FP / FN / TP | Alertas |
| --- | --- | --- | --- | --- | --- | --- |
| Árbol | Train | 0,76215 | 0,79801 | 0,07581 | 389 / 95 / 19 / 49 | 144 |
| Árbol | OOF | 0,72515 | 0,76945 | 0,08414 | 403 / 81 / 26 / 42 | 123 |
| SVM | Train | 0,74356 | 0,82207 | 0,08074 | 371 / 113 / 19 / 49 | 162 |
| SVM | OOF | 0,73760 | 0,80305 | 0,08050 | 351 / 133 / 17 / 51 | 184 |
| Dummy mayoritario | Train | 0,50000 | 0,50000 | 0,12319 | 484 / 0 / 68 / 0 | 0 |
| Dummy mayoritario | OOF | 0,50000 | 0,50000 | 0,12319 | 484 / 0 / 68 / 0 | 0 |
| Dummy positivo | Train | 0,50000 | 0,50000 | 0,87681 | 0 / 484 / 0 / 68 | 552 |
| Dummy positivo | OOF | 0,50000 | 0,50000 | 0,87681 | 0 / 484 / 0 / 68 | 552 |

## B.4. Política aplicada a DEV resuelto

En árbol y SVM el tope no retira ninguna alerta en train u OOF: precisión, recall, F1, F2, accuracy y matriz de política coinciden con los valores brutos correspondientes. El Dummy mayoritario no emite alertas. En el positivo sí cambia la decisión: tanto train como OOF quedan con 546 revisiones, matriz [[6,478],[0,68]], precisión 0,124542, recall 1, F1 0,221498, F2 0,415648 y accuracy 0,134058, frente al F2 bruto 0,412621.

| Política DEV | Revisiones train / OOF | Máximo diario train / OOF | Días con exceso antes del tope train / OOF |
| --- | --- | --- | --- |
| Árbol | 144 / 123 | 3 / 3 | 0 / 0 |
| SVM | 162 / 184 | 3 / 4 | 0 / 0 |
| Dummy mayoritario | 0 / 0 | 0 / 0 | 0 / 0 |
| Revisar todo limitado | 546 / 546 | 5 / 5 | 6 / 6 |

Las colas se calculan por réplica y fecha, no agrupando D1 y D2 en un mismo día. Los conteos de la tabla son del corpus de alternativas; los máximos son de colas separadas. Los siete desconocidos no compiten en estas colas DEV, a diferencia del lote FINAL completo. No se interpreta esa diferencia como una medición exhaustiva de capacidad humana.

<!-- PAGE -->

# Anexo C. Reproducción e inferencia local

## C.1. Entorno y comandos documentados, no ejecutados aquí

El reporte registra Python 3.12.14, scikit-learn 1.9.1, NumPy 2.5.3, SciPy 1.18.1 y Joblib 1.6.0. Son versiones de la corrida congelada, no evidencia de instalación o reproducción limpia posterior. Al redactar, el paquete consultado contiene `experimento/` y `README.md`; la ruta `codigo/scripts/` siguiente es la referencia de empaquetado que debe completar y comprobar la integración principal.

**Reproducción limpia: PENDIENTE.** Comando previsto desde la raíz del paquete, con código y dependencias compatibles y destino nuevo:

```bash
python codigo/scripts/academic_credit_aligned_v4.py --calibration experimento/calibration.json --protocol experimento/protocol.json --output-dir salida_repro_nueva
```

Ese comando sí genera y ajusta al repetir el protocolo cerrado: **no fue ejecutado para este informe**. Una comprobación posterior deberá comparar selección, tablas train/OOF/FINAL, políticas, auditorías e inferencia ilustrativa, sin cambiar criterios ni presentar la repetición técnica como otro test independiente. La integración principal actualizará el estado únicamente después de contar con evidencia.

Modo exclusivamente de inferencia sobre artefacto local confiable, con flags existentes, también documentado sin ejecutarlo:

```bash
python codigo/scripts/academic_credit_aligned_v4.py \
  --predict-artifact-dir experimento \
  --input-json experimento/illustrative_input.json \
  --output-json prediccion_nueva.json
```

Los modos son separados: no mezclar flags de experimento con inferencia; utilizar salidas nuevas y no sobrescribir el estudio congelado. Joblib puede ejecutar código al cargar: el hash detecta cambios, no vuelve confiable un origen malicioso. La CLI no constituye despliegue web, aprobación de crédito ni evaluación de acierto de un ejemplo sin etiqueta.

## C.2. Inventario técnico

| Ruta dentro de experimento/ | Función en el estudio |
| --- | --- |
| protocol.json; calibration.json; provenance.json | Diseño, agregados permitidos, supuestos, código y entorno |
| development_transactions.json; development_audits.json | Historias alternativas y auditorías de desarrollo |
| development_rows.json; development_rows.csv | Filas resueltas ordenadas para ML y exportación de estudio |
| fold_audit.json; cv_search.json | Particiones externas/internas y búsqueda OOF guardada |
| frozen_selection.json | Selección persistida antes de FINAL |
| final_transactions.json; final_audits.json; final_rows.csv | Mundo FINAL, auditoría y filas de estudio |
| aligned_v4_report.json; final_predictions.json; final_predictions.csv | Métricas, scores, decisiones y errores cacheados |
| selected_model.joblib; tree.joblib; svm.joblib | Ajustes exportados; seleccionado idéntico a SVM |
| most_frequent.joblib; constant_1.joblib; artifact_manifest.json | Referencias e integridad para inferencia |
| illustrative_input.json; illustrative_output.json | Ejemplo nuevo ya calculado, sin outcome |

<!-- PAGE -->

# Anexo C. Integridad y límites experimentales

## C.3. SHA-256 transcritos del registro congelado

```text
Declaración actual de Rildo, documento fuente
45bc22a10ad5dccf323708b8aeabb780d8de4629ff5087cca2582c7dd055819f
protocol.json
b9a6c49c2e2cb3b0e036fb9e5ce37f69421c31e6d98ccb096b7ba37b8760345c
calibration.json
81f858bc8827c88e41352745f65345a72d2b9d06361046bc86d3f07540806064
development_rows.json
85f3ecc6f0cd6d12ac7b52adf00fb8fb7180e3064ca616c925178438b3fd0355
fold_audit.json
bc43b7ee2ada9cf7e0616d5d042d76a0651b5e82be3ddddd4398d0b281fceff7
cv_search.json
a00df110dc36e9eeef3753cedf5851b567b1250f7234a677509cae0960551219
Runner de la corrida
517290f1ce71fd1b6ac0dad93c604e0cabede4839b9bc40373b51f67f47afffb
Generador y validador registrados
9fdb39dbcf33d507dc42876e53496841f79ec8c71a309ffbc8cc3b3224560a92
selected_model.joblib y svm.joblib
33236a0999c5f2e1d38b2a3bef66ba0d49c1aec936a63d7cbefb1e1f14b335ef
tree.joblib
42e0849063215fac1953eb9eedca5b0cd7c322785e3c29c261d6d20218353b36
most_frequent.joblib
678a10949eb102ae8288182d3dd16e9149aebf6aff9a3afbeedc81a3a2fb261a
constant_1.joblib
00258270c550bf35b3d41dc630ad382c4d9fb433beb543873d5d3d9398654858
frozen_selection.json
548710ff60dd8c574d588eb41dc9e10f15f6db06a6c14d9d98520cbc3d33e35d
```

Son valores transcritos del reporte y su procedencia, no una afirmación de recálculo de todos los hashes en esta edición. El hash del formulario bruto no implica publicarlo. No se confunden hash del protocolo y hash de la selección usado por el manifiesto.

## C.4. Fronteras del experimento

Las semillas DEV son 2026112101, prefijo AL4-D1, y 2026112102, AL4-D2; FINAL usa 2026112103, AL4-T. Se fijan antes de consultar FINAL. La auditoría registra una llamada de evaluación por modelo en FINAL y clientes fuente/final disjuntos. Las tablas y los errores se leen del caché existente.

Consultar FINAL lo vuelve un conjunto observado para cualquier selección futura. No se debe promocionar ahora el árbol por ganar en ese conjunto ni ajustar umbrales con sus errores; una nueva comparación requerirá otra prueba no consultada y protocolo previo. La reproducción técnica pendiente solo verifica el diseño fijo, no agrega evidencia externa ni elimina el optimismo de búsqueda OOF.

Algunos helpers puros del runner se reutilizan de código anterior; esto no importa filas, ajustes, calibración comercial o resultados de otros estudios. El código compartido no convierte CV3, v2 o Doña Rosa en evidencia V4. El único anclaje comercial es la declaración actual autorizada en `calibration.json`.

<!-- PAGE -->

# Anexo D. Riesgos y cierre hacia PROY

## D.1. Matriz propuesta, no acuerdos confirmados

Probabilidades e impactos son apreciaciones cualitativas de planificación, no frecuencias medidas. Los responsables son **propuestos**, no asignaciones aceptadas ni tareas ya ejecutadas.

| Riesgo | Probabilidad / impacto | Responsable propuesto | Mitigación propuesta y evidencia necesaria |
| --- | --- | --- | --- |
| Confundir simulación alineada con validación real | Alta / Alto | César y Omara | Publicar supuestos y discrepancias; contrastar con captura autorizada antes de uso real |
| Muchas falsas alertas y posible trato restrictivo | Alta / Alto | César y Tamara | Mantener revisión humana y prohibir rechazo automático; medir consecuencias y carga real |
| Omitir atrasos al limitar revisión | Media / Alto | Omara y César | Explicitar cuatro FN SVM frente a uno de revisar todo limitado; acordar objetivo/costos sin retocar FINAL |
| Capacidad total sobreestimada | Alta / Alto | Omara y Pablo | Cronometrar trabajo completo, no solo alertas; incluir solicitudes, cobranza y revisiones obligatorias |
| Tratamiento de clientes sin base o información trazable | Alta mientras siga pendiente / Alto | Omara y Tamara | Formalizar base jurídica, aviso, consentimiento cuando corresponda, ARCO y custodia antes del piloto |
| Usar versión equivocada o artefacto no confiable | Media / Alto | Tamara y Pablo | Verificar versión, manifiesto, contrato y rollback; no cargar Joblib ajeno |
| Conclusiones inestables con 12 clientes FINAL | Alta / Alto | César y Pablo | No equiparar filas con personas; futura evaluación con clientes y periodos trazables no consultados |

## D.2. Estado verificable de entrega

| Elemento | Estado documental actual | Condición real de cierre |
| --- | --- | --- |
| Estudio V4 | Corrida y selección congeladas disponibles | Conservar cachés y límites; no reabrir selección |
| Calibración comercial | Agregados actuales trazables, calidad aproximada | Contrastar supuestos no medidos sin atribuirlos al propietario |
| Reproducción limpia | PENDIENTE | Entorno nuevo y comparación registrada del protocolo fijo |
| EDA y tres figuras | Inserción/generación por empaquetado pendiente | Solo DEV para EDA y matriz SVM desde métricas, sin re-inferir |
| Paginación | Portada + 14 páginas manuales de cuerpo | Comprobar ≤15 páginas físicas antes de referencias/anexos |
| Revisión humana | Sin constancias nuevas | Registrar revisiones realmente realizadas, fechas y correcciones |
| Meta y costo empresarial | No aprobados ni medidos | Acordar finalidad y medidas observables con propietario |
| Integración | CLI local; web v2 heredada | Pruebas y autorización separadas antes de cualquier piloto V4 |

No se atribuye ahorro a la diferencia hipotética de 158 minutos ni se atribuye al propietario aprobación de F2, costo por FN/FP o beneficio. La capacidad cinco/día solo afecta alertas de otorgados; el resto del trabajo queda fuera. El siguiente paso propuesto es verificar reproducción y entrega, luego cerrar normativa y diseño de captura real, no activar producción ni reentrenar con FINAL.

<!-- PAGE -->

# Anexo E. Uso de IA y revisión humana

## E.1. Alcance de la asistencia documental

Esta redacción utiliza OpenCode, modelo `openai/gpt-6.1-sol`, para consultar estructuradamente los JSON congelados y crear únicamente el Markdown V4 solicitado. No ejecuta experimentos, entrenamiento o inferencia, no modifica artefactos antiguos y no genera figuras. El alcance de esta sesión no acredita quién ejecutó o revisó humanamente las fases anteriores.

La instrucción de esta actualización exige usar solo la declaración actual de Rildo, preservar resultados desfavorables, separar métricas brutas/de política y dejar la reproducción limpia pendiente. Se conserva como evidencia de alcance, no como respuesta de entrevista, firma o aceptación empresarial. No se reconstruyen prompts históricos ni se inventan modelos, fechas, personas o aprobaciones de otras sesiones.

Los controles documentales automáticos contrastan estructura, referencias de figuras, placeholders y números transcritos con los archivos guardados. No equivalen a revisión humana, auditoría contable ni verificación jurídica. El formulario privado del propietario no debe incorporarse a una publicación de evidencias; los agregados y el hash bastan para esta trazabilidad acotada.

## E.2. Registro humano sin constancias inventadas

Las celdas siguientes permanecen vacías intencionalmente: no consta en esta actualización una revisión individual completada. Cada integrante deberá consignar solo la revisión que efectivamente realice.

| Integrante | Alcance efectivamente revisado | Resultado o corrección | Fecha |
| --- | --- | --- | --- |
| Omara Yamileth Baylón Vila | | | |
| Tamara Alison Coveñas Quispe | | | |
| César Augusto Daniel Paredes Paredes | | | |
| Pablo Enrique Yman Avila | | | |

Aspectos prioritarios para esa revisión: denominadores 8/45 y 10/48; alternativas no sumables como volumen real; bandera de 27 minoritarios en D2; cuatro FN y 114 FP SVM; mayor F2 final del árbol sin cambiar ganador; diferencia entre revisar todo bruto y limitado; desconocidos en capacidad FINAL; fuentes privadas y límites jurídicos; reproducción y paginación pendientes.

No se acredita nueva entrevista, conformidad del propietario con el modelo, consentimiento de clientes, aceptación de interfaz V4, ensayo de exposición o aprobación del grupo. Los registros APF1/APF2 aportan continuidad, no validan este modelo posterior. Toda eventual constancia se añadirá únicamente cuando exista evidencia auténtica.
