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

**Extensión planificada:** portada y 15 páginas de cuerpo de cuerpo, 16 antes de referencias y anexos. Los separadores se contrastan con la exportación PDF y su registro de paginación; el límite es 15 páginas de este bloque, sin desbordes tras insertar el EDA. Referencias y anexos quedan fuera del cuerpo.

**Alcance académico.** Cero filas reales en entrenamiento o evaluación. Se documenta un estudio sintético ya congelado, alineado parcialmente con agregados declarados por Rildo, no una validación predictiva real. Esta redacción solo consulta archivos guardados: no genera experimentos, entrena ni ejecuta inferencia. No acredita ahorro, calibración de riesgo real, aprobación del propietario, revisión humana completada ni despliegue público V4. La reproducción técnica está comprobada con salvedad binaria Joblib, no como validación independiente (Anexo C).



**Estado editorial:** Datos simulados | Edición de entrega; revisión humana pendiente.

<!-- PAGE -->

# 1. Resumen ejecutivo y continuidad

## 1.1. Continuidad con APF1 y APF2

Cervecería Baylón es un negocio familiar de San Martín de Porres, Lima, operado por dos propietarios. APF1 identificó la administración del fiado a un día mediante cuaderno y criterio personal; APF2 desarrolló Credify, un MVP con clientes, reglas preliminares, fiados, abonos e historial persistente. Se mantienen empresa, equipo, problema y unidad de análisis. Lean Startup y Kanban organizan la evolución (Grupo 2, 2026a, 2026b). URL pública heredada del MVP/demo: https://demo-credify.168-75-71-113.sslip.io. Demo y producción son entornos distintos; no se verificó disponibilidad actual ni se afirma V4 público.

Al cierre documentado de APF2 el piloto real no había empezado y la exportación devolvió cero fiados elegibles; ello no prueba ausencia de otras operaciones del negocio. V4 tampoco cumple la captura prevista de 30 a 50 fiados reales. La declaración actual del propietario aporta agregados de calibración, no filas de clientes para aprender o evaluar.

## 1.2. Problema y resultado congelado

**Para el usuario propietario, se propone priorizar la revisión del fiado a un día con historial previo, medido por F2 de política y la meta propuesta de reducir minutos de revisión frente a revisar todo, sin superar cinco alertas/día y reportando el costo de los atrasos omitidos.** Es clasificación binaria supervisada por fiado: `late_payment=1` significa atraso, no pérdida permanente. Una alerta no rechaza automáticamente una solicitud.

Desarrollo contiene dos historias sintéticas alternativas de 12 clientes cada una: 559 fiados de estudio, 552 resueltos y siete desconocidos. No son 559 operaciones reales ni dos sucursales sumables. FINAL es otro mundo alternativo de 12 clientes: 260 fiados de estudio, 259 evaluables y uno desconocido. El calentamiento queda fuera de las filas supervisadas.

El criterio previo maximiza F2 OOF de la política de revisión con máximo cinco alertas por réplica y día. Ganó la **SVM lineal, C=1, balanced, umbral 0,10**, con F2 OOF 0,55921 frente a 0,53165 del árbol. En FINAL logra F2 0,70115, detecta 61 de 65 atrasos y genera 114 falsas alertas conocidas. Son 176 revisiones hipotéticas, incluida una sin etiqueta.

La SVM supera descriptivamente a las dos políticas Dummy en F2 final y respeta el tope de alertas. **El árbol obtiene mejor F2 final, 0,71096; no se cambia la selección después del test.** El Dummy mayoritario conserva mayor accuracy, 0,74903 frente a 0,54440 de SVM; revisar todo detecta más atrasos. No hay dominancia universal ni beneficio financiero demostrado.

<!-- PAGE -->

## 1.3. Trazabilidad APF2 y meta propuesta

Fuente primaria: APF2 original, Tabla 17, página física 10 / impresa 9, y B.4, física 20 / impresa 19. El diccionario de apoyo está en `APF2_Insumos_Para_Claude.md`, líneas 155-182. No se consultó la base real actual para esta edición.

| Campo / contrato APF2 | Fuente prevista | Fórmula / alcance APF3 | Cambio declarado |
| --- | --- | --- | --- |
| completed_sales | Ventas registradas al evaluar | Conteo de ventas completadas vinculadas a fiados previos | Restricción V4: solo ventas de crédito; MVP incluía todas las ventas |
| paid_credits; paid_late | Créditos y pagos anteriores | Pagados completos; de ellos, pagados tarde | Semántica conservada; eventos simulados |
| pending_overdue; pending_current | Créditos activos | Conteos con saldo vencidos / no vencidos al evaluar | Conservados; snapshot anterior al otorgamiento |
| outstanding; utilization | Saldos y máximo configurado | Saldo previo; saldo / 80 PEN | Cupo fijo sintético, no cupo real estimado |
| requested_ratio; tenure_days | Solicitud; registro del cliente | Monto / 80; días desde registro | Cupo fijo y registro simulado |
| punctuality_rate; overdue_rate | Pagos; créditos activos | (pagados - tardíos) / pagados; vencidos / activos | Sin denominador: 0 por convención, no evidencia |
| late_payment | Vencimiento y pagos | 0 puntual; 1 tardío o saldo vencido; desconocido excluido | Target de atraso sin cambio; no impago a 30 días |
| Fuente, volumen y evaluación | 30-50 fiados reales consentidos en 4-6 semanas | 552 etiquetas sintéticas DEV; CV por cliente | Cero elegibles al cierre APF2; simulación no reemplaza piloto real |

**Meta empresarial PROPUESTA, no aprobada.** Para un piloto futuro autorizado: registrar ANTES minutos de revisar todo en un periodo de referencia y DESPUÉS minutos de la política en un periodo comparable, volumen elegible, revisiones, atrasos omitidos y falsas alertas con desenlace maduro. Criterio observable propuesto: minutos DESPUÉS < minutos de referencia, máximo cinco alertas/día y reporte explícito de FN/FP y sus consecuencias. No hay baseline cronometrado, costo FN acordado ni meta financiera numérica; no basta reducir tiempo para aceptar un daño no acordado.

Esta propuesta retrospectiva de piloto no fue predeclarada para seleccionar modelos y no retoca FINAL. El criterio técnico ex ante permanece F2 de política superior a ambas referencias Dummy y capacidad limitada. El resultado actual son 79 revisiones menos y tres FN más, no éxito empresarial incondicional.

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



**Ficha de coherencia, consigna §4.2:** Escala del negocio; Rangos y unidades; Consistencia lógica y temporal; Relaciones plausibles; Señal ni nula ni perfecta; Coherencia con APF2; Mezcla real + simulado: N/A. La tabla completa del Anexo F distingue evidencia guardada, reservas y anclas aproximadas; conserva además los controles comerciales de calibración. No son observaciones nuevas.

**Calidad DEV:** 552 supervisadas, 24 clientes, cero nulos, IDs duplicados y vectores repetidos; once snapshots contrastados sin diferencias. Los siete targets desconocidos se conservan fuera de supervisión. IQR es descriptivo, no motivo para borrar extremos. Diccionario de las 24 columnas con tipo, unidad, rango y política de nulos: Anexo G y [CSV](../anexos/datos/diccionario-datos.csv).

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

El EDA utiliza exclusivamente las **552 filas resueltas de desarrollo**, guardadas en `development_rows.json`: no calentamiento, desconocidos ni FINAL. Las figuras y la tabla se han preparado durante el empaquetado desde ese caché, sin generar operaciones ni ajustar modelos. Se documenta el estudio ya terminado, no se presenta el EDA como una exploración prospectiva anterior a la corrida.

![Figura 1. Balance de late_payment en las 552 filas DEV resueltas, dos historias alternativas.](figuras/eda_balance.png)

**Balance.** Hay 484 puntuales, 87,68 %, y 68 atrasos, 12,32 %. Predecir siempre clase 0 obtiene accuracy 0,87681 en DEV sin detectar atrasos. Por ello se comparan precisión, recall, F1 y F2 positivos, además de accuracy. No se fuerza la prevalencia a reproducir 17,78 % de la declaración.

**Descriptivos DEV resuelto, n=552 por variable; origen 100 % simulado.**

| Variable (unidad) | Mín. | Media | Mediana | Máx. |
| --- | --- | --- | --- | --- |
| requested_amount (PEN) | 6,39 | 21,80 | 19,51 | 49,42 |
| paid_credits (conteo) | 2,00 | 14,81 | 15,00 | 28,00 |
| paid_late (conteo) | 0,00 | 1,64 | 1,00 | 15,00 |
| outstanding (PEN) | 0,00 | 0,08 | 0,00 | 21,64 |
| utilization (ratio) | 0,0000 | 0,0011 | 0,0000 | 0,2705 |
| punctuality_rate (ratio) | 0,0000 | 0,8686 | 0,9444 | 1,0000 |
| tenure_days (días) | 28,00 | 198,54 | 200,00 | 359,00 |

Los estadísticos descriptivos de la tabla conservan unidades y denominadores de DEV; no se usa FINAL para completar vacíos. `requested_ratio` representa el monto relativo, no añade un duodécimo predictor. Los extremos acotados son parte del escenario, no evidencia para eliminar clientes futuros.

**Suficiencia con reservas.** D1 tiene 41 atrasos; D2 solo 27, por debajo de la referencia orientativa de 30 minoritarios, y su auditoría marca `adequate=false`. El combinado tiene 68 minoritarios y 552 etiquetas, pero esa suma no elimina la insuficiencia por réplica ni crea 552 personas independientes. FINAL tiene 65 atrasos y 259 etiquetas en solo 12 clientes.

Los umbrales orientativos de 200 filas y 30 minoritarios son banderas descriptivas, no demostración estadística de suficiencia, ni razón para regenerar o alterar etiquetas. Las tres historias pasan los controles duros y de escala del protocolo; pasar esas auditorías comprueba coherencia con restricciones elegidas, no representatividad de toda la empresa ni validez de cada distribución.

<!-- PAGE -->

## 2.5. EDA DEV: historial y antigüedad-ventas

Análisis post hoc del DEV congelado, no exploración prospectiva previa al experimento. Las dos relaciones se fijaron antes del cálculo descriptivo de esta auditoría, no antes de la corrida ML. No se seleccionan nuevas variables ni modelos.

![Figura 2. DEV resuelto: historial frente a atraso y antigüedad frente a ventas de crédito; scatter con las 552 filas.](figuras/eda_relaciones_entrega.png)

**Historial:** sin atraso previo, 8/218 (3,67 %); con atraso previo, 60/334 (17,96 %). No hay casos sin pagos previos (0/0, no estimable). La asociación puede reflejar la propensión latente estable supuesta por cliente, no causalidad ni riesgo medido en personas reales.

| Antigüedad, bandas fijas | Fiados | Clientes distintos | Mediana ventas |
| --- | --- | --- | --- |
| 30-119 días | 80 | 10 | 8 |
| 120-239 días | 302 | 24 | 13 |
| >=240 días | 169 | 17 | 21 |

Una fila de 28 días queda fuera de bandas, pero está en el scatter de las 552 filas. Las medianas 8/13/21 apoyan acumulación de operaciones en este escenario; no una señal causal de atraso. Registro inicial aleatorio y calentamiento común limitan la exposición observada; completed_sales solo cuenta ventas vinculadas a crédito.

Hay clientes compartidos entre bandas y fiados repetidos por cliente: no son observaciones independientes ni una segunda fuente comercial. Sin p-valores, causalidad ni validación predictiva. La CV por cliente no prueba generalización temporal ni corrige estacionariedad supuesta. La relación adversa de exposición se conserva íntegra en el Anexo F: 551 casos en la primera banda, uno en la segunda y cero en la tercera no permiten afirmar tendencia de riesgo.

Solo tres figuras: balance, estas relaciones y matriz SVM leída de métricas congeladas; sin nuevas predicciones.

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



**Acción:** usar señales para revisión, nunca rechazo automático. Contrastar deuda, vencimientos y capacidad de pago; investigar los signos contraintuitivos con futuros datos autorizados, sin inferir que endeudarse beneficia ni cambiar ahora el umbral.

<!-- PAGE -->

# 5. Integración mínima con el MVP

## 5.1. Frontera real de la implementación

Recapitulación APF2: MVP persistente de clientes, fiados y abonos por reglas. Producción y demo pública son entornos distintos; la URL pública heredada del MVP/demo es https://demo-credify.168-75-71-113.sslip.io. No se verificó su disponibilidad actual ni se afirma que exponga V4. La demo pública/v2 no acredita el laboratorio V4 local.

La integración actual V4 incluye web local `/laboratorio-academico/v4`, API autenticada `/api/v1/academic-ml/v4` y CLI, separadas de producción. El stack local con imagen y DB ficticia fue probado; aplica solo el ejemplo ilustrativo guardado, no cohortes FINAL. Verifica contrato/hashes y usa bundle de confianza solo lectura, flag staging deshabilitado por defecto. No crea créditos ni aplica cola diaria operativa. La muestra API de memoria fue 160,9 MiB frente al límite 256 MiB: observación puntual, no garantía bajo carga. Evidencia: [stack V4](../anexos/integracion/evidence-stack-v4.json).

## 5.2. Ejemplo nuevo, sin etiqueta conocida

Entrada y salida ya almacenadas en `illustrative_input.json` e `illustrative_output.json`; no se vuelven a inferir en esta redacción:

```json
{"features":{"completed_sales":6,"paid_credits":4,"paid_late":1,"pending_overdue":0,"pending_current":0,"outstanding":0,"utilization":0,"requested_ratio":0.25,"tenure_days":60,"punctuality_rate":0.75,"overdue_rate":0}}
```

```json
{"origen":"simulado","illustrative_only":true,"known_label":null,"family":"svm","probability":0.11922453881690649,"threshold":0.1,"predicted":1,"research_only":true,"business_approval":false}
```

Seis ventas vinculadas, cuatro fiados pagados y uno tardío dan puntualidad 0,75. Con cupo S/ 80, `requested_ratio=0.25` representa **S/ 20 solicitados**, no el cupo ni una media. La comprobación guardada de distinción respecto de las cohortes pasa. El score supera 0,10: es candidato a revisión, **no rechazo ni aprobación**. La asignación efectiva de revisión requiere todos los casos de ese día y su réplica; la salida individual solo aplica umbral. `known_label=null` no entra al predictor ni demuestra acierto.

El contrato admite números finitos no negativos y `null` para imputación de predictores, con conteos enteros, ratios válidos y `paid_late <= paid_credits`; no acepta el target como feature. La CLI de inferencia y el comando de reproducción se documentan, no se ejecutan, en el Anexo C. **La reproducción técnica V4 está comprobada con salvedad binaria Joblib**; no se hereda la verificación de versiones previas ni se atribuyen ahorros o calibración real al ejemplo.



**Medición local de servicio:** validación de bundle 6,13 ms; carga del modelo + primera predicción 38,55 ms; 30 llamadas warm: mediana 1,90 ms, p95 (nearest-rank) 2,23 ms. Pico RSS del proceso: 125240 KiB, independiente de los 160,9 MiB del stack. Solo load_bundle + evaluate del ejemplo fijo confiable; no FINAL, HTTP, DB, navegador, concurrencia sostenida ni SLA. [Evidencia](../anexos/integracion/latencia-v4.json); este generador no ejecuta inferencia.


Entrega por archivos para Aula Virtual: [código](../codigo/scripts/academic_credit_aligned_v4.py) y dependencias versionadas del paquete; enlace local, no publicación pública ni prueba de acceso docente. GitHub/CV3 es solo antecedente.

<!-- PAGE -->

# 6. Normativa y proyección a PROY

Se mantienen la Ley N.° 29733 y su Reglamento aprobado por D.S. N.° 016-2024-JUS (ANPD, 2011, 2024). Este autodiagnóstico no acredita cumplimiento integral ni constituye dictamen jurídico. Las URLs oficiales son las heredadas; no se afirma una nueva verificación jurídica en esta redacción.

| Requisito normativo | Control en dataset/modelo | Evidencia concreta y límite |
| --- | --- | --- |
| Finalidad y minimización | Investigación sintética, once predictores; alerta no rechaza | Contrato V4, research_only; finalidad/base real pendientes |
| Seguridad y custodia | JWT, flag staging, bundle solo lectura y hashes | Servicio/rutas V4; hashes no autentican al publicador ni vuelven seguro un Joblib ajeno |
| Información y derechos | No hay consentimiento nuevo de clientes ni circuito ARCO acreditado | US09 APF2 pendiente; aviso, retención, borrado y responsables abiertos |
| Terceros y exposición | Sin IA externa para inferencia V4; solo ejemplo guardado | Servicio local; nube/transferencias y privacidad global no auditadas |


Nombres académicos, formularios y firmas pueden ser datos personales aunque las cohortes sean ficticias. El permiso del propietario no sustituye consentimiento u otra base jurídica aplicable a cada cliente. HTTPS, quitar IDs y verificar hashes no certifican anonimización ni cumplimiento.

Para PROY se propone acordar finalidad, meta y costos reales antes del piloto; capturar de forma autorizada snapshots, desenlaces y acciones humanas; evaluar políticas con un test no consultado; y versionar datos, código y rollback. El reentrenamiento no está activo: frecuencia y promoción deben acordarse, con calidad, ambas clases, comparación contra baselines y revisión humana, no por calendario automático. Riesgos y responsables del Anexo D son propuestas. El Anexo H integra normativa y prompts disponibles: historial anterior incompleto declarado, no puede reconstruirse; validación humana pendiente. Meta/costos y cierre jurídico del piloto son trabajo operativo futuro, no requisitos previos de esta entrega académica.

# 7. Conclusiones

V4 completa una comparación propia árbol/SVM con dos Dummy, fuente agregada actual trazable, historias alternativas a escala declarada, Pipeline, CV por cliente, calibración interna agrupada y congelamiento antes de FINAL. La SVM seleccionada logra F2 de política final 0,70115 frente a 0 y 0,62257 de las referencias; respeta cinco alertas diarias y detecta 61/65 atrasos, pero produce 114 falsas alertas y omite cuatro. El árbol alcanza mejor F2 final, sin reemplazar al ganador OOF.

La meta investigativa propuesta se cumple en esta simulación, no una meta empresarial aprobada. La fuente es aproximada; distribuciones, estacionariedad y población siguen supuestas; D2 no llega a 30 minoritarios; FINAL tiene solo 12 clientes y prevalencia distinta. No hay validación externa, ahorro, consentimiento de clientes ni aceptación humana acreditados. La web V4 está probada solo localmente; la reproducción técnica está comprobada, sin identidad binaria Joblib ni validación independiente. Los tres campos EDA DEV se materializaron desde cachés y la paginación se controla en la exportación, sin reabrir selección ni ocultar resultados desfavorables.

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

<!-- PAGE -->

# Anexo A. Supuestos cuantitativos

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

## C.1. Reproducción técnica comprobada y comandos

El reporte registra Python 3.12.14, scikit-learn 1.9.1, NumPy 2.5.3, SciPy 1.18.1 y Joblib 1.6.0. La verificación posterior registra esas versiones en un entorno limpio, sin red durante la ejecución, y `passed=true`. El código y los datos están empaquetados; sus controles de integridad pasan en `verificacion-reproduccion.json`. Los comandos se indican desde la raíz del paquete, no desde `informe/`.

**Reproducción técnica comprobada:** 12 evaluaciones brutas y 12 de política exactas; 15 archivos con SHA-256 iguales y cinco estados aprendidos iguales, según `verificacion-reproduccion.json` y `estado-artefactos.json`. **Los bytes de los cinco Joblib NO son iguales.** Se excluyen tres timestamps y dos hashes derivados; las cadenas locales de integridad pasan. No es validación independiente. Comando desde la raíz del paquete, con destino nuevo:

```bash
python codigo/scripts/academic_credit_aligned_v4.py --calibration experimento/calibration.json --protocol experimento/protocol.json --output-dir salida_repro_nueva
```

La ejecución técnica separada repitió el protocolo fijo; selección, auditorías e inferencia ilustrativa coinciden. Este generador solo lee su evidencia: no reentrena ni reabre selección. Repetir FINAL no agrega otro test independiente.

Modo de inferencia local confiable, ya contrastado en la verificación separada; se documenta sin reejecutarlo aquí:

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

Consultar FINAL lo vuelve un conjunto observado para cualquier selección futura. No se debe promocionar ahora el árbol por ganar en ese conjunto ni ajustar umbrales con sus errores; una nueva comparación requerirá otra prueba no consultada y protocolo previo. La reproducción técnica documentada solo verifica el diseño fijo, no agrega evidencia externa ni elimina el optimismo de búsqueda OOF. Se excluyen `report.generated_utc`, `provenance.recorded_utc`, `selection.frozen_utc` y los hashes derivados `selection.decision_sha256.provenance.json` y `artifact_manifest.frozen_selection.json`; no se afirma identidad binaria de los Joblib.

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
| Reproducción técnica | Comprobada, con salvedad binaria Joblib | 12 brutas + 12 políticas, 15 SHA y cinco estados iguales; no validación independiente |
| EDA y tres figuras | Materializados desde cachés congelados | Solo DEV para EDA y matriz SVM desde métricas, sin re-inferir |
| Paginación PDF | Edición de entrega, 15 páginas de cuerpo | Conteo físico y total en verificacion-informe-entrega.json |
| Revisión humana | Sin constancias nuevas | Registrar revisiones realmente realizadas, fechas y correcciones |
| Meta y costo empresarial | No aprobados ni medidos | Acordar finalidad y medidas observables con propietario |
| Integración | Web/API V4 probadas solo localmente; demo pública heredada/v2 | No acredita producción, URL pública V4 ni aceptación humana |

No se atribuye ahorro a la diferencia hipotética de 158 minutos ni se atribuye al propietario aprobación de F2, costo por FN/FP o beneficio. La capacidad cinco/día solo afecta alertas de otorgados; el resto del trabajo queda fuera. El siguiente paso propuesto es completar revisión humana y archivo de entrega, y cerrar normativa y diseño de captura real, no activar producción ni reentrenar con FINAL.

<!-- PAGE -->

# Anexo E. Uso de IA y revisión humana

## E.1. Alcance de la asistencia documental

Esta redacción utiliza OpenCode, modelo `openai/gpt-6.1-sol`, para consultar estructuradamente los JSON congelados y crear el Markdown V4 de base y materializar su exportación Word/HTML/PDF. No ejecuta experimentos, entrenamiento o inferencia, no modifica artefactos del experimento; las tres figuras se generan exclusivamente desde cachés congelados. El alcance de esta sesión no acredita quién ejecutó o revisó humanamente las fases anteriores.

La instrucción de esta actualización exige usar solo la declaración actual de Rildo, preservar resultados desfavorables, separar métricas brutas/de política y cerrar la reproducción técnica solo con evidencia final, declarando su salvedad binaria. Se conserva como evidencia de alcance, no como respuesta de entrevista, firma o aceptación empresarial. No se reconstruyen prompts históricos ni se inventan modelos, fechas, personas o aprobaciones de otras sesiones.

Los controles documentales automáticos contrastan estructura, referencias de figuras, placeholders y números transcritos con los archivos guardados. No equivalen a revisión humana, auditoría contable ni verificación jurídica. El formulario privado del propietario no debe incorporarse a una publicación de evidencias; los agregados y el hash bastan para esta trazabilidad acotada.

## E.2. Registro humano sin constancias inventadas

Las celdas siguientes permanecen vacías intencionalmente: no consta en esta actualización una revisión individual completada. Cada integrante deberá consignar solo la revisión que efectivamente realice.

| Integrante | Alcance efectivamente revisado | Resultado o corrección | Fecha |
| --- | --- | --- | --- |
| Omara Yamileth Baylón Vila | | | |
| Tamara Alison Coveñas Quispe | | | |
| César Augusto Daniel Paredes Paredes | | | |
| Pablo Enrique Yman Avila | | | |

Aspectos prioritarios para esa revisión: denominadores 8/45 y 10/48; alternativas no sumables como volumen real; bandera de 27 minoritarios en D2; cuatro FN y 114 FP SVM; mayor F2 final del árbol sin cambiar ganador; diferencia entre revisar todo bruto y limitado; desconocidos en capacidad FINAL; fuentes privadas y límites jurídicos; reproducción técnica con salvedad binaria y paginación PDF comprobadas.

No se acredita nueva entrevista, conformidad del propietario con el modelo, consentimiento de clientes, aceptación de interfaz V4, ensayo de exposición o aprobación del grupo. Los registros APF1/APF2 aportan continuidad, no validan este modelo posterior. Toda eventual constancia se añadirá únicamente cuando exista evidencia auténtica.

<!-- PAGE -->

# Anexo F. Auditoría DEV y coherencia completa

# Datos: cierre descriptivo V4 SOLO DEV

Analisis post hoc congelado. No fit, predict, carga joblib, nuevos datos, nuevas features, cambios de runner/protocolo ni seleccion. No se abre DOCX privado. Auditorias guardadas son evidencia historica, no una nueva validacion independiente.

## Ficha En Seis Pasos

1. Delimitar: prestamos concedidos study; warmup solo contexto para snapshots. CSV DEV completo 559; supervision 552; 7 desconocidos conservados y auditados.

2. Identificar fuente: calibration.json y source_vs_assumptions de development_audits.json; anclas agregadas parciales del propietario, no filas reales ni verdad auditada. Hash del DOCX, sin abrirlo.

3. Operacionalizar: diccionario de las 24 columnas originales y once predictores; tipos, unidades, rangos MVP/V4, null policy y metadatos posteriores al desenlace excluidos.

4. Comprobar calidad: nulos, IDs repetidos, vectores coincidentes, no finitos, rangos y estadisticos IQR por feature; conservar coincidencias legitimas y valores extremos, sin exclusion ni imputacion.

5. Contrastar coherencia: ficha principal con los siete criterios exactos de la consigna 4.2; restricciones de calibracion separadas como detalle. Distinguir anclas, aproximaciones y supuestos; no regenerar para mejorar ajuste.

6. Describir dos relaciones declaradas en el script: reportar magnitud, denominadores y resultado adverso si aparece; sin busqueda de alternativas, causalidad ni independencia ficticia.

<!-- PAGE -->

# Anexo F. Auditoría DEV y coherencia completa

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

<!-- PAGE -->

# Anexo F. Auditoría DEV y coherencia completa

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

<!-- PAGE -->

# Anexo F. Auditoría DEV y coherencia completa

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

<!-- PAGE -->

# Anexo F. Auditoría DEV y coherencia completa

## Desconocidos

- `AL4-D1-L00318`: vence 2026-10-01, corte 2026-09-30, saldo 18.42; sin resolucion al corte; excluido supervision.
- `AL4-D1-L00319`: vence 2026-10-01, corte 2026-09-30, saldo 24.82; sin resolucion al corte; excluido supervision.
- `AL4-D1-L00320`: vence 2026-10-01, corte 2026-09-30, saldo 19.49; sin resolucion al corte; excluido supervision.
- `AL4-D1-L00321`: vence 2026-10-01, corte 2026-09-30, saldo 27.83; sin resolucion al corte; excluido supervision.
- `AL4-D2-L00325`: vence 2026-10-01, corte 2026-09-30, saldo 20.10; sin resolucion al corte; excluido supervision.
- `AL4-D2-L00326`: vence 2026-10-01, corte 2026-09-30, saldo 31.07; sin resolucion al corte; excluido supervision.
- `AL4-D2-L00327`: vence 2026-10-01, corte 2026-09-30, saldo 33.68; sin resolucion al corte; excluido supervision.

<!-- PAGE -->

# Anexo F. Auditoría DEV y coherencia completa

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

<!-- PAGE -->

# Anexo F. Exposición sin tendencia acreditada

**Conclusión sobre exposición.** DEV resuelto (n=552): 0-25 %: 12,34 % (68/551); >25-50 %: 0,00 % (0/1); >50 %: no estimable (0/0). Con 551 casos en la primera banda, uno en la segunda y ninguno en la tercera, no hay soporte para afirmar una tendencia general de riesgo por exposición.

La deuda y la utilización son previas al nuevo fiado; con cupo constante, `utilization=outstanding/80`, por lo que no son señales independientes. La relación atraso-exposición también está condicionada por la política que deja fuera solicitudes no otorgadas. No permite atribuir causalidad al cupo ni estimar desenlaces de solicitudes rechazadas.

Las operaciones repetidas de un cliente son dependientes. La CV agrupa clientes, pero no es una evaluación temporal prospectiva ni una prueba dejando fuera mundos completos. Una separación por cliente no corrige por sí sola la hipótesis de estacionariedad entre marzo y septiembre. Si las bandas son pequeñas o no monotónicas, se conserva ese resultado sin corregir el generador.

<!-- PAGE -->

# Anexo G. Diccionario completo, columnas 1-6

# Diccionario completo V4

24 columnas originales, mismo orden en ambos CSV. DEV: 559 filas (552 conocidas, 7 desconocidas). FINAL: 260 filas; 1 desconocidas. FINAL solo esquema y conteos, no EDA.

Metadatos no entran al vector de once predictores. Rangos de contrato no son rangos observados; estos se guardan por separado en calidad-dev-v4.json. Convenciones de ratios no son observaciones. Tipos CSV son representaciones textuales, tipos indicados son logicos/JSON.



| columna | rol | tipo | unidad | rango_contrato | politica_nulos | definicion | alcance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| origen | metadata | string | categoria | simulado | No permitido V4; no imputar en esta auditoria | Procedencia sintetica, nunca cliente real | datos/desarrollo.csv y datos/final.csv |
| loan_id | metadata | string | identificador | unico por prestamo; prefijo replica | No permitido V4; no imputar en esta auditoria | Identificador ficticio del prestamo evaluado | datos/desarrollo.csv y datos/final.csv |
| client_id | metadata | string | identificador | 12 clientes por replica; se repite en prestamos | No permitido V4; no imputar en esta auditoria | Grupo de dependencia; no predictor | datos/desarrollo.csv y datos/final.csv |
| replica_id | metadata | string | identificador | DEV AL4-D1/AL4-D2; FINAL AL4-T | No permitido V4; no imputar en esta auditoria | Historia alternativa, no sucursal simultanea | datos/desarrollo.csv y datos/final.csv |
| phase | metadata | string | categoria | study en ambos CSV; warmup solo transacciones | No permitido V4; no imputar en esta auditoria | Fase de calendario | datos/desarrollo.csv y datos/final.csv |
| evaluated_at | metadata | ISO datetime | hora civil America/Lima | 2026-04-13..2026-09-30 | No permitido V4; no imputar en esta auditoria | Instante anterior al nuevo credito; snapshot sin futuro | datos/desarrollo.csv y datos/final.csv |

<!-- PAGE -->

# Anexo G. Diccionario completo, columnas 7-12

# Diccionario completo V4

24 columnas originales, mismo orden en ambos CSV. DEV: 559 filas (552 conocidas, 7 desconocidas). FINAL: 260 filas; 1 desconocidas. FINAL solo esquema y conteos, no EDA.

Metadatos no entran al vector de once predictores. Rangos de contrato no son rangos observados; estos se guardan por separado en calidad-dev-v4.json. Convenciones de ratios no son observaciones. Tipos CSV son representaciones textuales, tipos indicados son logicos/JSON.



| columna | rol | tipo | unidad | rango_contrato | politica_nulos | definicion | alcance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| due_date | metadata | ISO date | dia civil | evaluated_at.date + 1 dia | No permitido V4; no imputar en esta auditoria | Vencimiento contractual; gracia no cambia etiqueta | datos/desarrollo.csv y datos/final.csv |
| observed_on | metadata | ISO date | dia civil | 2026-09-30 | No permitido V4; no imputar en esta auditoria | Corte de observacion | datos/desarrollo.csv y datos/final.csv |
| requested_amount | metadata | decimal string JSON / decimal CSV | PEN | 5..50; <=80-outstanding; dos decimales | No permitido V4; no imputar en esta auditoria | Importe concedido; metadato, representado en predictor requested_ratio | datos/desarrollo.csv y datos/final.csv |
| credit_cap | metadata | decimal string JSON / decimal CSV | PEN | 80.00 | No permitido V4; no imputar en esta auditoria | Tope por cliente; denominador de ratios | datos/desarrollo.csv y datos/final.csv |
| pending_at_cutoff | metadata | decimal string JSON / decimal CSV | PEN | 0..requested_amount | No permitido V4; no imputar en esta auditoria | Saldo al corte, posterior a evaluar; PROHIBIDO como predictor | datos/desarrollo.csv y datos/final.csv |
| scenario | metadata | string | categoria | on_time, late, unresolved y variantes partial_ | No permitido V4; no imputar en esta auditoria | Desenlace observado al corte, no plan; PROHIBIDO como predictor | datos/desarrollo.csv y datos/final.csv |

<!-- PAGE -->

# Anexo G. Diccionario completo, columnas 13-18

# Diccionario completo V4

24 columnas originales, mismo orden en ambos CSV. DEV: 559 filas (552 conocidas, 7 desconocidas). FINAL: 260 filas; 1 desconocidas. FINAL solo esquema y conteos, no EDA.

Metadatos no entran al vector de once predictores. Rangos de contrato no son rangos observados; estos se guardan por separado en calidad-dev-v4.json. Convenciones de ratios no son observaciones. Tipos CSV son representaciones textuales, tipos indicados son logicos/JSON.



| columna | rol | tipo | unidad | rango_contrato | politica_nulos | definicion | alcance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| completed_sales | predictor | float64 integral | operaciones | MVP >=0; V4 >=0; limite por eventos previos; paid_late <= paid_credits | No permitido V4; no imputar en esta auditoria | Ventas de credito previas observadas; V4 no inventa ventas al contado | datos/desarrollo.csv y datos/final.csv |
| paid_credits | predictor | float64 integral | operaciones | MVP >=0; V4 >=0; limite por eventos previos; paid_late <= paid_credits | No permitido V4; no imputar en esta auditoria | Creditos previos totalmente pagados al evaluar | datos/desarrollo.csv y datos/final.csv |
| paid_late | predictor | float64 integral | operaciones | MVP >=0; V4 >=0; limite por eventos previos; paid_late <= paid_credits | No permitido V4; no imputar en esta auditoria | Creditos previos pagados con algun pago posterior al vencimiento | datos/desarrollo.csv y datos/final.csv |
| pending_overdue | predictor | float64 integral | operaciones | MVP >=0; V4 >=0; limite por eventos previos; paid_late <= paid_credits | No permitido V4; no imputar en esta auditoria | Creditos previos con saldo y vencimiento anterior al dia evaluado | datos/desarrollo.csv y datos/final.csv |
| pending_current | predictor | float64 integral | operaciones | MVP >=0; V4 >=0; limite por eventos previos; paid_late <= paid_credits | No permitido V4; no imputar en esta auditoria | Creditos previos con saldo y vencimiento no anterior al dia evaluado | datos/desarrollo.csv y datos/final.csv |
| outstanding | predictor | float64 | PEN | MVP >=0; V4 0..75 y outstanding + requested_amount <=80 | No permitido V4; no imputar en esta auditoria | Saldo de creditos previos al evaluar | datos/desarrollo.csv y datos/final.csv |

<!-- PAGE -->

# Anexo G. Diccionario completo, columnas 19-24

# Diccionario completo V4

24 columnas originales, mismo orden en ambos CSV. DEV: 559 filas (552 conocidas, 7 desconocidas). FINAL: 260 filas; 1 desconocidas. FINAL solo esquema y conteos, no EDA.

Metadatos no entran al vector de once predictores. Rangos de contrato no son rangos observados; estos se guardan por separado en calidad-dev-v4.json. Convenciones de ratios no son observaciones. Tipos CSV son representaciones textuales, tipos indicados son logicos/JSON.



| columna | rol | tipo | unidad | rango_contrato | politica_nulos | definicion | alcance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| utilization | predictor | float64 | proporcion | MVP >=0, puede >1; V4 0..0.9375 | No permitido V4; no imputar en esta auditoria | outstanding / credit_cap; MVP cap=0 devuelve 0, no observado V4 | datos/desarrollo.csv y datos/final.csv |
| requested_ratio | predictor | float64 | proporcion | MVP >=0, puede >1; V4 0.0625..0.625 | No permitido V4; no imputar en esta auditoria | requested_amount / credit_cap; MVP cap=0 devuelve 1, no observado V4 | datos/desarrollo.csv y datos/final.csv |
| tenure_days | predictor | float64 integral | dias civiles | MVP >=0; V4 fecha evaluacion - registro; edad inicial 0..180, mas calendario transcurrido | No permitido V4; no imputar en esta auditoria | Dias desde registro; no equivale a dias de historia observada | datos/desarrollo.csv y datos/final.csv |
| punctuality_rate | predictor | float64 | proporcion | 0..1 | No permitido V4; no imputar en esta auditoria | (paid_credits - paid_late) / paid_credits; sin pagados =0 por convencion, no puntualidad observada | datos/desarrollo.csv y datos/final.csv |
| overdue_rate | predictor | float64 | proporcion | 0..1 | No permitido V4; no imputar en esta auditoria | pending_overdue / (pending_current + pending_overdue); sin activos =0 por convencion | datos/desarrollo.csv y datos/final.csv |
| late_payment | target | int nullable | clase | 0, 1 o vacio | JSON null / CSV vacio: conservar en CSV; excluir de supervision; no imputar target | 0 pagado a tiempo; 1 pago tardio o saldo vencido al corte; desconocido sin resolucion al corte | datos/desarrollo.csv y datos/final.csv |

<!-- PAGE -->

# Anexo H. Bloque A. Normativa y controles verificables V4

**APF3, Grupo 2, Cerveceria Baylon / Credify. Anexos de cierre integrados en la edicion documental de entrega.** Cinco bloques de origen integrados en esta edicion y redistribuidos para exportacion A4; el conteo fisico consta en la verificacion de entrega. Esta integracion documental no modifica el paquete original congelado, el protocolo ni el runtime y no constituye acta de aprobacion.

**Base documental consultada:** consigna original `/Users/tamaraalison/Downloads/Innovacion_TD_Consigna_APF3.pdf`, secciones 2.7, 6.4, 6.5, 8 y 9; informe materializado `/Users/tamaraalison/Downloads/APF3_Grupo2_Alineado_V4/informe/APF3_TD_Grupo2_ML_Innovacion_Borrador.md`, lineas 352-366 y 641-697. No se usa como estado final la copia V4 anterior del repositorio. Las rutas locales de ese paquete no presuponen acceso del docente.

**Marco heredado APF1 corregido / APF2:** Ley N.° 29733 y Reglamento aprobado por D.S. N.° 016-2024-JUS. No se incorporan otras normas del borrador legacy como obligaciones de este estudio. Referencias oficiales heredadas: [Ley 29733, ANPD](https://www.gob.pe/institucion/anpd/normas-legales/2018427-29733-2011) y [D.S. 016-2024-JUS, ANPD](https://www.gob.pe/institucion/anpd/normas-legales/6554453-16-2024-jus). **No se realizo consulta web ni nueva verificacion juridica de vigencia, articulos o plazos.** La matriz es un autodiagnostico tecnico, no certificacion de cumplimiento legal.

| Requisito normativo | Control en dataset/modelo | Evidencia concreta y limite |
| --- | --- | --- |
| Finalidad del tratamiento, continuidad APF1/APF2 | V4 se limita a investigacion sintetica sobre atraso del fiado a un dia. La alerta no autoriza ni rechaza credito. | Servicio V4, L54-L59 y L261-L274: [codigo MVP entregado](../laboratorio/codigo_fuente_MVP_V4.zip), entrada `codigo_fuente_MVP_V4/backend/app/services/academic_lab_v4.py`: advertencia, `research_only=true`, `business_approval=false`, sin cola diaria aplicada. Formalizar finalidad y base juridica para personas reales sigue pendiente. |
| Minimizacion de variables | Once predictores numericos; el contrato del ejemplo no admite nombres, documentos, contactos ni target como entrada. Esto no demuestra anonimato de un futuro dataset real. | Servicio, L22-L34 y L114-L128: [codigo MVP entregado](../laboratorio/codigo_fuente_MVP_V4.zip), entrada `codigo_fuente_MVP_V4/backend/app/services/academic_lab_v4.py`. [Generador, L34-L49](../codigo/app/ml/owner_aligned_synthetic.py): IDs ficticios y fechas existen como metadatos, no como predictores; no se afirma ausencia universal de datos personales en documentos. |
| Datos simulados y prevencion de reidentificacion | Cero filas reales en aprendizaje/evaluacion; se conserva `origen=simulado`. La fuente comercial solo aporta agregados, no registros individuales. | [Generador, L125-L159, L328-L356](../codigo/app/ml/owner_aligned_synthetic.py); servicio, L166-L173 y L222-L228: [codigo MVP entregado](../laboratorio/codigo_fuente_MVP_V4.zip), entrada `codigo_fuente_MVP_V4/backend/app/services/academic_lab_v4.py`. No equivale a anonimizar datos reales ni a auditar el recuerdo del propietario. |

<!-- PAGE -->

# Anexo H. Matriz completa, continuación

| Requisito normativo | Control en dataset/modelo | Evidencia concreta y limite |
| --- | --- | --- |
| Seguridad y acceso limitado | JWT y usuario activo; flag deshabilitado por defecto; habilitacion solo en staging. No existe una restriccion V4 exclusiva por rol docente: usa la autenticacion existente. | Rutas, L10-L21: [codigo MVP entregado](../laboratorio/codigo_fuente_MVP_V4.zip), entrada `codigo_fuente_MVP_V4/backend/app/api/routes/academic_ml_v4.py`, autenticacion, L17-L34: [codigo MVP entregado](../laboratorio/codigo_fuente_MVP_V4.zip), entrada `codigo_fuente_MVP_V4/backend/app/api/dependencies.py`, configuracion, L12-L18 y L70-L81: [codigo MVP entregado](../laboratorio/codigo_fuente_MVP_V4.zip), entrada `codigo_fuente_MVP_V4/backend/app/core/config.py`, registro de rutas, L19-L22: [codigo MVP entregado](../laboratorio/codigo_fuente_MVP_V4.zip), entrada `codigo_fuente_MVP_V4/backend/app/api/router.py`. Controles locales, no auditoria de accesos del servidor. |
| Integridad, custodia y tratamiento acotado | Bundle de confianza montado solo lectura; hashes y runtime comprobados antes de cargar bytes Joblib. El servicio de inferencia no escribe operaciones comerciales; autenticar puede consultar la identidad en DB. | Compose V4, L13-L19: [codigo MVP entregado](../laboratorio/codigo_fuente_MVP_V4.zip), entrada `codigo_fuente_MVP_V4/docker-compose.academic-v4.yml`, servicio, L147-L177 y L235-L260: [codigo MVP entregado](../laboratorio/codigo_fuente_MVP_V4.zip), entrada `codigo_fuente_MVP_V4/backend/app/services/academic_lab_v4.py`. Hash no autentica al publicador; Joblib puede ejecutar codigo. No cargar archivos ajenos. |
| Minimizar nuevas capturas y exposicion | Solo se evalua `illustrative-v4`, desde entrada sintetica guardada; cuerpo o query se rechazan. Errores de consulta devuelven 503 generico. | Rutas, L24-L31 y L45-L52: [codigo MVP entregado](../laboratorio/codigo_fuente_MVP_V4.zip), entrada `codigo_fuente_MVP_V4/backend/app/api/routes/academic_ml_v4.py`. No admite PII como entrada de inferencia; ello no certifica redaccion de logs de infraestructura ni privacidad de toda la aplicacion. |

<!-- PAGE -->

# Anexo H. Matriz completa, continuación

| Requisito normativo | Control en dataset/modelo | Evidencia concreta y limite |
| --- | --- | --- |
| Informacion y consentimiento cuando corresponda | No hay evidencia nueva de consentimiento de clientes. Una declaracion del propietario no sustituye la base juridica de cada titular. | Pendiente heredado APF2, L84; informe materializado, L360-L364. **ABIERTO:** aviso, finalidad, base aplicable y constancias trazables antes del piloto real. |
| Derechos ARCO, conservacion y eliminacion | No se acredita un circuito operativo completo ni plazo aprobado de retencion/borrado. El laboratorio solo lectura no resuelve estos deberes. | Pendientes APF2, L84; informe materializado, L361-L366. **ABIERTO:** responsables, canal ARCO, inventario, politica de conservacion, backups y prueba de eliminacion. |
| Custodia de fuentes y terceros | No entregar formulario privado, firmas, contactos, secretos ni cuaderno. El servicio V4 no invoca proveedores externos de IA para inferir. | Servicio V4 completo: [codigo MVP entregado](../laboratorio/codigo_fuente_MVP_V4.zip), entrada `codigo_fuente_MVP_V4/backend/app/services/academic_lab_v4.py`, exclusiones documentales, L36-L47. Revisar proveedores, nube y transferencias antes de datos reales; esta evidencia no audita todos los canales del MVP. |

<!-- PAGE -->

# Anexo H. Bloque B. Prompts disponibles y limites del registro IA

**Herramienta de esta edicion:** OpenCode, modelo `openai/gpt-6.1-sol`. Se declara asistencia IA en codigo, datos, modelado, documentacion, integracion y verificaciones segun los artefactos conocidos del Anexo C. No se puede atribuir automaticamente el mismo modelo a todas las sesiones anteriores.

**Literalidad y procedencia:** las cinco instrucciones siguientes son los textos exactos disponibles aportados por la usuaria para registrar la sesion. No se dispone aqui de la transcripcion completa de sus respuestas, ejecuciones intermedias o sesiones del experimento anterior. Su presencia no prueba que una persona haya revisado o aprobado los resultados. El alcance es contextual, no una atribucion causal exclusiva de cada archivo a un prompt.

| Prompt literal disponible | Alcance contextual | Resultado documentado, no aprobacion | Verificacion tecnica disponible | Validacion humana |
| --- | --- | --- | --- | --- |
| `que cambios se tendrian que hacer en produccion?` | Consulta sobre evolucion operativa y separacion de investigacion/produccion. | Tooling V4 separado y limites de despliegue documentados; no se deduce autorizacion para publicar o desplegar. | Laboratorio V4, L50-L126 y L246-L247. No se recupera una respuesta literal completa. | PENDIENTE |
| `ya comienza` | Continuacion de trabajo tecnico asistido. No contiene por si sola una especificacion de entrenamiento. | Codigo y controles V4 presentes; la correspondencia exacta entre este mensaje y cada cambio no esta reconstruida. | Rutas: [codigo MVP entregado](../laboratorio/codigo_fuente_MVP_V4.zip), entrada `codigo_fuente_MVP_V4/backend/app/api/routes/academic_ml_v4.py`, servicio: [codigo MVP entregado](../laboratorio/codigo_fuente_MVP_V4.zip), entrada `codigo_fuente_MVP_V4/backend/app/services/academic_lab_v4.py`, tests: [codigo MVP entregado](../laboratorio/codigo_fuente_MVP_V4.zip), entrada `codigo_fuente_MVP_V4/backend/tests/test_academic_lab_v4.py`. Existencia de codigo no prueba revision humana. | PENDIENTE |
| `continua` | Continuacion de implementacion y comprobaciones. | Preparacion y pruebas locales documentadas, sin convertir la instruccion en aceptacion del producto. | Preparador: [codigo MVP entregado](../laboratorio/codigo_fuente_MVP_V4.zip), entrada `codigo_fuente_MVP_V4/deploy/prepare-aligned-v4-lab.py`, pruebas del preparador, smoke: [codigo MVP entregado](../laboratorio/codigo_fuente_MVP_V4.zip), entrada `codigo_fuente_MVP_V4/deploy/smoke-aligned-v4-api.py`. | PENDIENTE |
| `que falta para que el avance 3 cumpla con toda la consigna y todo este listo para presentar?` | Identificacion de brechas tecnicas, documentales y humanas frente a la consigna. | Se distinguen entrega tecnica, normativa pendiente, revision, ensayo y acceso; no se declara cumplimiento total. | Consigna original, secciones 6.4, 8-11; guion V4 y checklist. | PENDIENTE |

<!-- PAGE -->

# Anexo H. Matriz completa, continuación

| Prompt literal disponible | Alcance contextual | Resultado documentado, no aprobacion | Verificacion tecnica disponible | Validacion humana |
| --- | --- | --- | --- | --- |
| `okay avanza en el orden que has recomendado` | Continuacion del cierre documental. | Materiales de apoyo y este anexo para integracion posterior, no acta grupal ni aprobacion del propietario. | Informe materializado, L674-L697; guion V4; comprobacion estructural de este Markdown. | PENDIENTE |
| **Prompt literal no disponible: fases anteriores de codigo, simulacion y modelado.** | Generador, snapshots, etiquetas, Pipeline, CV agrupada, calibracion, busqueda, congelamiento y evaluacion FINAL. | Existen fuentes y artefactos tecnicos, pero no un historial literal completo que permita reconstruir instrucciones, autores o revisores. | [Generador](../codigo/app/ml/owner_aligned_synthetic.py), [runner](../codigo/scripts/academic_credit_aligned_v4.py); paquete local: `experimento/protocol.json`, `provenance.json`, `frozen_selection.json`, `fold_audit.json` y `aligned_v4_report.json`. | PENDIENTE |
| **Prompt literal no disponible: otras sesiones documentales y de verificacion.** | Redaccion, figuras desde caches, exportaciones, empaquetado, reproduccion y comprobaciones automatizadas. | Informe, deck y registros disponibles; no se inventa texto de instrucciones anteriores. | Paquete local: `informe/manifest.json`, `verificacion-reproduccion.json`, `verificacion-entrega.json`; tooling documental. | PENDIENTE |

**Limite del registro:** historial anterior incompleto declarado; no puede reconstruirse ni sustituirse por prompts plausibles retrospectivos. Se conservan los prompts literales disponibles; la consigna pide el anexo de prompts, no toda conversacion historica completa. Protocolo, provenance, codigo y hashes son evidencia tecnica, **NO prueba de autoria, revision humana, consentimiento ni aprobacion**. Validacion humana pendiente.

La solicitud actual de crear este archivo y las ordenes de continuar son instrucciones de edicion, no entrevistas, firmas, actas de aprobacion, validacion comercial o constancias de revision aplicada. Este anexo tampoco convierte una comprobacion automatica en validacion humana.

<!-- PAGE -->

# Anexo H. Bloque C. Fases asistidas y verificacion tecnica

**Lectura de evidencia existente, sin reejecutar ML en esta edicion.** Raiz local del paquete: `/Users/tamaraalison/Downloads/APF3_Grupo2_Alineado_V4`. Los nombres relativos de paquete de esta tabla son rutas internas de esa raiz, no enlaces publicos. Los enlaces de codigo llevan al repositorio; no se garantiza que el checkout actual sea identico a cada fuente congelada sin cotejar manifiestos.

| Fase conocida con asistencia IA declarada | Evidencia y comprobacion registrada | Lo que NO demuestra |
| --- | --- | --- |
| Codigo y datos | [Generador/validador](../codigo/app/ml/owner_aligned_synthetic.py), pruebas: [codigo MVP entregado](../laboratorio/codigo_fuente_MVP_V4.zip), entrada `codigo_fuente_MVP_V4/backend/tests/test_owner_aligned_synthetic.py`; `experimento/calibration.json`, `provenance.json`, `development_audits.json`, `final_audits.json`. Agregados de fuente, simulacion rotulada y snapshots previos. | No son filas reales, auditoria del cuaderno ni distribuciones medidas. Prompt exacto anterior no disponible. |
| Modelo y seleccion | [Runner V4](../codigo/scripts/academic_credit_aligned_v4.py), tests del experimento: [codigo MVP entregado](../laboratorio/codigo_fuente_MVP_V4.zip), entrada `codigo_fuente_MVP_V4/backend/tests/test_aligned_v4_experiment.py`; `experimento/fold_audit.json`, `cv_search.json`, `frozen_selection.json`. Arbol/SVM y dos Dummy; seleccion SVM C=1 balanced, umbral 0.10, por F2 OOF limitado. | No generalizacion real, evaluacion anidada independiente de hiperparametros ni probabilidades reales calibradas. Reusar OOF para buscar introduce optimismo. |
| Evaluacion y reproduccion | `verificacion-reproduccion.json`, `estado-artefactos.json`, `verificacion-reproduccion-inicial.json`; informe materializado L554-L566 y L631-L637. Se registran 12 evaluaciones brutas y 12 de politica exactas, 15 archivos SHA-256 iguales y cinco estados aprendidos iguales. | Los cinco Joblib **no** son binariamente iguales. Se excluyen tres timestamps y dos hashes derivados; cada cadena local se comprueba. Se conserva el fallo inicial. No es validacion independiente ni un nuevo test estadistico. |
| Documentos y empaquetado | `verificacion-entrega.json`, L3-L17, L44-L49 y L114-L123: `passed=true`, 14 paginas de cuerpo, 25 PDF total, 13 slides, 720 segundos planificados, 18 preguntas y 10 paginas de guion. Figuras EDA desde DEV y matriz desde cache. | No render nativo Microsoft Office, revision humana, ensayo cronometrado o ejecucion humana de demo. Estas cifras describen exclusivamente la exportacion anterior; el conteo de entrega consta en verificacion-informe-entrega.json. |
| Integracion local | Preparador: [codigo MVP entregado](../laboratorio/codigo_fuente_MVP_V4.zip), entrada `codigo_fuente_MVP_V4/deploy/prepare-aligned-v4-lab.py`, smoke real: [codigo MVP entregado](../laboratorio/codigo_fuente_MVP_V4.zip), entrada `codigo_fuente_MVP_V4/deploy/smoke-aligned-v4-api.py`, stack con navegador: [codigo MVP entregado](../laboratorio/codigo_fuente_MVP_V4.zip), entrada `codigo_fuente_MVP_V4/deploy/test-aligned-v4-stack.mjs`, UI con API simulada: [codigo MVP entregado](../laboratorio/codigo_fuente_MVP_V4.zip), entrada `codigo_fuente_MVP_V4/deploy/test-aligned-v4-ui.mjs`. Registro V4, L128-L237: smoke ASGI, imagen final y stack local efimero con login y DB ficticia. | Un test con mocks no prueba el modelo real. El smoke usa identidad ficticia; el stack local no acredita servidor publico, aceptacion humana ni carga sostenida. Solo se infiere el ejemplo ilustrativo, no cohortes FINAL. |
| Suites y analisis estatico | Registro V4, L235-L244: **359 tests backend y 14 del preparador**, Ruff y ESLint aprobados en ejecuciones documentadas anteriores. | No se reejecutaron en esta edicion ni se suman como aceptacion humana. La cifra **223 historicos** referida como antecedente no tiene respaldo primario identificado en las fuentes leidas: queda por localizar su log/version; no se certifica como corrida V4 ni se suma a 359. |

**Integridad del test: primera evaluacion frente a comprobaciones posteriores.** `frozen_selection.json` se persistio antes de generar FINAL; el informe materializado L187 y L220 registra un unico lote FINAL por modelo en la corrida original. Tras observarlo, FINAL ya no es un conjunto no consultado para decisiones futuras. Reproduccion, lectura de caches, recalculo de metricas y comprobaciones posteriores del protocolo fijo no restituyen esa condicion ni anaden evidencia independiente. No se promociona el arbol por ganar en FINAL, ni se retocan umbrales, semillas o datos a partir de sus errores.

**Resultado conservado con limites:** SVM FINAL, 259 conocidos y un desconocido: matriz `[[80,114],[4,61]]`, F2 de politica 0.70115, 176 revisiones incluyendo el desconocido. El arbol tiene mejor F2 FINAL, 0.71096, sin cambiar ganador. Revisar todo limitado tiene F2 0.62257 y 255 revisiones; no confundirlo con bruto, 0.62620. Las 79 revisiones y 158 minutos hipoteticos menos no son ahorro medido. D2 conserva 27 minoritarios; FINAL tiene solo 12 clientes ficticios.

**Verificacion del anexo de origen:** solo lectura de fuentes y revision estructural/enlaces del Markdown. La integracion de entrega agrega exportacion y render fisico, registrados por separado. No se entreno, genero datos, infirio, ejecuto suites, consulto produccion ni verifico leyes en la web. Los resultados automaticos anteriores se citan con su alcance, no como ejecuciones nuevas.

<!-- PAGE -->

# Anexo H. Bloque D. Registro humano y ensayo pendientes

**Estado: PENDIENTE.** Nombres y codigos proceden de la portada del informe materializado, L9-L14. No se registran contribuciones, revision aplicada, firmas o fechas que no consten. Cada persona debe completar exclusivamente lo que efectivamente haya realizado; un rol propuesto no prueba participacion pasada.

| Integrante | Codigo | Revision efectivamente realizada | Resultado/correccion y evidencia | Fecha real |
| --- | --- | --- | --- | --- |
| Omara Yamileth Baylón Vila | U23231338 | pendiente | pendiente | pendiente |
| Tamara Alison Coveñas Quispe | U23204737 | pendiente | pendiente | pendiente |
| César Augusto Daniel Paredes Paredes | U23259768 | pendiente | pendiente | pendiente |
| Pablo Enrique Yman Avila | U23251279 | pendiente | pendiente | pendiente |

**Checklist de revision autentica, aun sin marcar:**

- [ ] Cada integrante abre las fuentes, contrasta codigo/datos/metricas/conclusiones asistidos por IA y registra alcance, resultado, correccion y fecha real; no basta declarar que leyo el texto.
- [ ] Todos explican con sus palabras la cadena APF1 problema/indicador -> APF2 MVP/contrato -> dataset sintetico -> target -> modelos/baselines -> seleccion -> inferencia -> limites de PROY.
- [ ] Cotejar los agregados permitidos: 48 anotaciones, tres sin desenlace, 45 evaluables, ocho atrasos: **8/45=17.78 %**; diez con parciales: **10/48=20.83 %**, no 10/45. Son agregados declarados aproximados, no filas de entrenamiento ni fuente auditada.
- [ ] Distinguir hipotesis de hechos: Beta, sigmas, poblacion de 12, calentamiento y estacionariedad no fueron medidos. Historias DEV alternativas no son sucursales sumables como volumen real.
- [ ] Explicar Pipeline solo con entrenamiento, CV por cliente y calibracion interna; reconocer optimismo OOF, D2 con 27 minoritarios y dependencia de multiples fiados por cliente.
- [ ] Cotejar seleccion previa a FINAL y reconocer que el test ya observado no sirve para elegir ahora otro modelo; separar primera corrida de reproduccion/comprobaciones posteriores.
- [ ] Explicar cuatro FN y 114 FP SVM, mejor F2 final del arbol sin cambiar ganador, politica limitada frente a clasificador bruto, desconocidos en capacidad y diferencia entre umbral individual y cola top-5.
- [ ] Cotejar ejemplo sin etiqueta: S/ 20 sobre cupo S/ 80, score guardado `0.11922453881690649`, umbral `0.1`, clase `1`, `known_label=null`; no afirmar acierto ni aprobacion comercial.
- [ ] Revisar exclusiones privadas, consentimiento/base juridica, ARCO y conservacion abiertos. No atribuir a Rildo aprobacion de F2, costo de errores o beneficio financiero.
- [ ] Realizar ensayo autentico con los cuatro integrantes: **12 minutos +/- 30 segundos de exposicion y 5 minutos de preguntas**; anotar duracion observada, turnos, preguntas y correcciones. 720 segundos planificados no prueban ensayo.
- [ ] Cada integrante responde sobre cualquier fase, no solo su bloque. Probar demo en el entorno de exposicion; si falla, declarar el fallo y mostrar salida/captura guardada rotulada, nunca simular ejecucion en vivo.
- [ ] Registrar comprension y conformidad real del grupo solo despues de revisar. No usar este pedido de edicion ni instrucciones de continuar como evidencia de aprobacion.

El guion V4 es apoyo para practicar, no constancia de ensayo. No hay nueva entrevista, consentimiento de clientes, validacion del propietario, aceptacion comercial ni factor de contribucion acreditados por estos anexos.

<!-- PAGE -->

# Anexo H. Bloque E. Riesgos, acceso y entrega

Se conservan los siete riesgos del informe materializado, L647-L655. Probabilidad e impacto son apreciaciones cualitativas, no frecuencias medidas. Los responsables siguientes son **propuestas para V4**, no asignaciones aceptadas ni contribuciones realizadas; se usan roles de seguimiento coherentes con APF2, L31-L45.

| Riesgo heredado | Probabilidad | Impacto | Responsable propuesto y rol | Mitigacion / evidencia necesaria |
| --- | --- | --- | --- | --- |
| Confundir simulacion con validacion real | Alta | Alto | Cesar, datos; Omara, enlace con negocio | Conservar etiquetas y supuestos; contrastar con captura autorizada antes de uso real. |
| Falsas alertas y trato restrictivo | Alta | Alto | Cesar, modelo/datos; Tamara, aplicacion | Mantener revision humana y prohibicion de rechazo automatico; medir carga y consecuencias. |
| Omitir atrasos al limitar revision | Media | Alto | Omara, objetivo de negocio; Cesar, evaluacion | Explicar cuatro FN frente a uno de revisar todo limitado; acordar costos sin retocar FINAL. |
| Sobreestimar capacidad total | Alta | Alto | Omara, coordinacion; Pablo, pruebas/evidencias | Cronometrar trabajo completo, incluyendo solicitudes, cobranza y revisiones obligatorias. |
| Tratar clientes sin base o informacion trazable | Alta mientras siga abierto | Alto | Omara, consentimiento; Tamara, controles de aplicacion | Formalizar finalidad/base, aviso, constancias cuando correspondan, ARCO y custodia antes del piloto. |
| Version equivocada o artefacto no confiable | Media | Alto | Tamara, infraestructura/aplicacion; Pablo, pruebas | Cotejar version/manifiestos/contrato, solo Joblib confiable y rollback; no reutilizar capturas v2 como V4. |
| Conclusiones inestables con 12 clientes FINAL | Alta | Alto | Cesar, particiones; Pablo, evidencia de pruebas | No equiparar filas con personas; nueva evaluacion con clientes/periodos trazables no consultados y protocolo previo. |

**PUBLICACION NO AUTORIZADA.** Esta edicion genera archivos locales MD/DOCX/HTML/PDF, no publicacion remota. No autoriza push, publicacion en GitHub/Drive, cambios de permisos, subida al Aula Virtual ni activacion de demo o produccion. La seccion 8 de la consigna permite codigo entregado como archivo; GitHub no es requisito obligatorio. Si se elige compartir por enlace, debe ser legible para el docente e incluirse en el informe final.

<!-- PAGE -->

# Anexo H. Acceso y entrega, continuación

**Checklist de acceso y entrega, aun pendiente de comprobacion humana:**

- [ ] Identificar la version de entrega: paquete local existente `/Users/tamaraalison/Downloads/APF3_Grupo2_Alineado_V4`, su ZIP/checksum adyacentes y `manifest-entrega.json`. El empaquetado local no es publicacion remota ni prueba de descarga por el docente.
- [ ] Entregar fuentes V4 y `requirements.txt`, no solo una URL del MVP: el paquete contiene `codigo/scripts/academic_credit_aligned_v4.py`, generador y helpers, datos simulados, modelo y ejemplo; `README.md` describe reproduccion y limites de dependencias binarias. No modificarlo en esta edicion.
- [ ] Separar la copia previa APF3_CV3 y su politica de publicacion de la entrega V4 local. Un repositorio/enlace GitHub que muestra CV3 no acredita acceso a V4; no se comprobo el remoto en esta edicion.
- [ ] Elegir entrega por archivos en Aula Virtual o enlace de lectura autorizado. En caso de enlace, probar con permisos equivalentes a los del docente, sin credenciales personales del grupo; registrar URL final/version y ponerla en el informe. No publicar para resolver un permiso sin autorizacion.
- [ ] Integrar este anexo mediante el agente del informe y volver a verificar enlaces, referencias y paginacion de la exportacion final: maximo 15 paginas de cuerpo, sin portada/referencias/anexos, y 13 slides. Este contenido esta integrado en el informe de entrega PDF/DOCX/HTML; no se afirma inclusion en ZIP ni cobertura de manifiestos anteriores.
- [ ] Si se reorganiza la entrega, resolver las rutas de codigo de este archivo contra la estructura final: hoy son enlaces relativos validos al repositorio. Las rutas locales del paquete son inventario, no enlaces finales para el docente. Adjuntar o enlazar las evidencias de verificacion autorizadas necesarias.
- [ ] Revisar ausencia de PII real, secretos, formulario bruto del propietario, firmas, contactos, cuaderno y backups. Los nombres/codigos academicos no son predictores; su inclusion no autoriza divulgar documentos privados.
- [ ] Confirmar acceso al entorno de exposicion y su version. Hay laboratorio V4 probado **localmente**, posterior al texto del informe que solo describia CLI; la demo publica heredada/v2 no acredita V4. Estado y controles locales, L197-L247. No es obligatorio activar publicamente V4 para entregar el codigo.
- [ ] Mantener evidencia de la primera evaluacion y comprobaciones posteriores sin sobrescribir; localizar respaldo de 223 tests historicos si se pretende citarlos como verificados. Revisar por separado vulnerabilidades de dependencias documentadas en el laboratorio, sin declarar seguridad total.
- [ ] Cerrar revision individual y ensayo con evidencia autentica; recuperar historial literal IA anterior disponible o declarar su ausencia. Mantener el historial anterior incompleto declarado, sin exigir reconstruir toda conversacion como requisito de la rubrica; registrar la validacion humana efectivamente realizada antes de afirmarla.

**Brechas abiertas concretas:** historial literal IA anterior incompleto; validacion humana aplicada y ensayo sin constancias; fuente comercial aproximada; meta/costos y beneficio no validados; consentimiento/base juridica, ARCO y conservacion no cerrados; activacion publica V4 no autorizada; acceso efectivo del docente y enlaces finales por comprobar; acceso docente y cierre humano pendientes. La reproduccion tecnica con salvedad Joblib y las pruebas automaticas locales no cierran esas brechas.


Meta/costos aprobados, piloto real, cierre juridico operativo y activacion publica V4 corresponden a una futura operacion autorizada; no se presentan como requisitos previos de la entrega academica APF3. La validacion humana pendiente se distingue de esas condiciones futuras.

<!-- PAGE -->

# Anexo I. Índice de evidencia y brechas

| Criterio | Página PDF / archivo de entrega |
| --- | --- |
| Continuidad, usuario, meta y cambios APF2 | 2-3; APF2 Tabla 17 y B.4 |
| Fuente, calidad, coherencia y diccionario | 4-7; Anexos A, F y G; anexos/datos/ |
| Modelado, CV y selección | 8-10; Anexo B; experimento/frozen_selection.json |
| Métricas y errores, sin ocultar desfavorables | 11-14; 224 celdas cotejadas; Anexo B |
| Integración y ejemplo | 15; anexos/integracion/; codigo/ |
| Normativa, riesgos, proyección y conclusiones | 16; Anexos D y H |
| Reproducción y dependencias | Anexo C; verificacion-reproduccion.json del paquete original; versiones fijadas, no reinstaladas aquí |
| IA y revisión humana | Anexos E y H: prompts disponibles, historial previo incompleto; revisión y ensayo pendientes |
| Paginación e integridad documental | verificacion-informe-entrega.json; manifest-informe-entrega.json |

No se declara cumplimiento integral ni validación humana completada: revisión aplicada, ensayo real y acceso docente siguen pendientes de constancia. Historial anterior incompleto declarado, no puede reconstruirse; se anexan los prompts literales disponibles sin atribuir a la rúbrica la exigencia de toda conversación histórica. Meta/costos aprobados, consentimiento/base jurídica, ARCO y piloto real son condiciones de futura operación autorizada, no bloqueos previos de la entrega académica. Publicar V4 no es obligatorio para entregar código. No se inventan contribuciones ni aprobaciones; archivos locales no prueban acceso remoto docente.


<!-- PAGE -->

# Anexo J. Referencias de fuentes del repositorio

Las referencias siguientes identifican fuentes consultadas del repositorio, no archivos prometidos mediante enlaces rotos en la entrega. Sus hashes están en el manifiesto documental cuando son archivos. No acreditan acceso docente al repositorio ni identidad del checkout con la corrida congelada. El enlace de código del cuerpo sí apunta a un archivo local de entrega existente. Estas referencias adicionales no se afirman incluidas en el ZIP MVP salvo que se indique una entrada comprobada; publicación y Aula Virtual siguen pendientes.

| Referencia | Ruta de fuente en repositorio |
| --- | --- |
| Pendientes APF2, L84 | `docs/APF2_Validacion_y_Artefactos.md` |
| politica de publicacion | `docs/PUBLICATION.md` |
| Estado y controles locales | `docs/APF3_LABORATORIO_V4.md` |
| pruebas del preparador | `deploy/test-prepare-aligned-v4-lab.py` |
| guion V4 | `docs/APF3_Guion_Sustentacion_V4.md` |
| tooling documental | `deploy/generate-aligned-v4-report.py` |
| APF2, L31-L45 | `docs/APF2_Avances_Cierre_Pendientes.md` |
| APF3_CV3 | `entregables/APF3_CV3/` |
