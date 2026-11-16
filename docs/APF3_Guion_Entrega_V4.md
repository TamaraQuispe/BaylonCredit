# APF3 · Grupo 2 · Guion de entrega V4

**Edición independiente:** deriva del guion `docs/APF3_Guion_Sustentacion_V4.md`, sin sustituirlo. Fuente materializada: `informe/APF3_TD_Grupo2_ML_Innovacion.md` y `informe/verificacion-informe-entrega.json` de `/Users/tamaraalison/Downloads/APF3_Grupo2_Entrega_V4`: 15 páginas de cuerpo, 48 totales. SHA-256 de la verificación final: `0906cae7f2449413e87a39f2f212575a635d9b05603ef2caddd70522e66defb5`. Métricas, selección, errores e ilustración se leen de `experimento/aligned_v4_report.json` y sus cachés, sin cargar modelos, entrenar, predecir ni reproducir FINAL. Calidad DEV conserva los siete criterios de coherencia originales corregidos; la figura EDA no cambió.

**Uso:** exactamente 13 diapositivas. Solo los párrafos bajo cada intervención se pronuncian; tablas, comandos y bloques **Acción:** no son narración. Cronometraje: 30 + 30 + 75 + 75 + 75 + 75 + 40 + 40 + 70 + 60 + 60 + 45 + 45 = 720 segundos. Diapositiva 9: 20 hablados y 50 de operación. Preguntas fuera del cronómetro. Objetivo editorial de 1250 a 1450 palabras, no requisito de la consigna; conteo real en `plan-sustentacion-entrega.json`. Duración real pendiente de ensayo.

**Reparto propuesto, no contribuciones acreditadas:**

| Integrante | Código | Rol de exposición propuesto |
| --- | --- | --- |
| Omara Yamileth Baylón Vila | U23231338 | Continuidad, problema, datos y selección |
| César Augusto Daniel Paredes Paredes | U23259768 | EDA, metodología, errores e interpretación |
| Tamara Alison Coveñas Quispe | U23204737 | Resultados, demo CLI e integración local |
| Pablo Enrique Yman Avila | U23251279 | Negocio, normativa y cierre |

**Procedencia:** única fuente comercial permitida, declaración actual de Rildo sobre septiembre de 2026, consulta declarada del 08/10/2026, SHA-256 `45bc22a10ad5dccf323708b8aeabb780d8de4629ff5087cca2582c7dd055819f`. Agregados aproximados, cuaderno parcial y recuerdo incierto; no dataset supervisado, consentimiento de clientes ni aprobación del modelo. Formulario enteramente hipotético anterior excluido; no publicar la ficha privada.

**Preparación técnica, no acta humana:** reproducción guardada con `passed=true`, 15 archivos exactos, 12 evaluaciones brutas, 12 políticas y cinco estados aprendidos exactos; bytes Joblib distintos, con exclusiones documentadas de tres timestamps y dos hashes derivados. Web/API V4 probadas solo en stack local Docker/Postgres/JWT/navegador, según `anexos/integracion/evidence-stack-v4.json`. No acredita URL pública V4, producción, aceptación comercial ni ensayo. Esta exportación verifica documentos y cachés; no ejecuta inferencia.

**Evidencias técnicas finales guardadas:** `anexos/integracion/prueba-cli-v4.json` tiene `status=passed`, wrapper raíz y score 0,11922453881690649 en un único ejemplo ilustrativo sin etiqueta; 0,824 s incluye arranque Docker, imports, carga e inferencia. `anexos/integracion/latencia-v4.json` registra 30 llamadas calientes del servicio sobre el mismo vector, mediana 1,90 ms y p95 2,23 ms. No mide HTTP, autenticación, red, navegador o concurrencia sostenida ni acredita SLA. Son preparación técnica, no demo ni ensayo humanos. Se citan resultados guardados, no se repiten aquí.

## 1. Fiado a un día: continuidad y equipo
**Tiempo:** 30 s | **Expositor propuesto:** Omara

Presentamos V4 para el fiado a un día en Cervecería Baylón. APF1 identificó cuaderno y criterio personal; APF2 desarrolló Credify. APF3 compara modelos para apoyar revisión humana, nunca aprobar automáticamente. Esta entrega incorpora evidencia web local y una demo principal por CLI offline. Los datos siguen siendo ficticios, parcialmente alineados con Rildo. El reparto de exposición es propuesto, no constancia de contribuciones ni aprobación empresarial.

**Acción:** portada con los cuatro nombres y códigos, APF1 → APF2 → APF3, datos ficticios y revisión pendiente. No abrir ficha privada.

## 2. Problema ML e indicador financiero
**Tiempo:** 30 s | **Expositor propuesto:** Omara

Buscamos anticipar atraso frente al vencimiento contractual del día siguiente, usando solo información previa al otorgamiento. Cada fila es un fiado: uno significa atraso y cero, puntualidad. Los tres días de gracia no cambian la etiqueta. El cinco por ciento referencial es pérdida mensual estimada sobre ventas: no prevalencia, probabilidad ni meta conseguida. Un atraso no equivale a pérdida definitiva, y una alerta exige criterio humano.

**Acción:** clasificación binaria supervisada, target `late_payment`; separar el 5 % financiero de la tasa de etiquetas.

## 3. Dataset: historias alternativas, no volumen real
**Tiempo:** 75 s | **Expositor propuesto:** Omara

No hay filas reales de clientes en entrenamiento ni evaluación. Al cierre de APF2 el piloto no había empezado y el exportador produjo cero fiados elegibles; eso no significa que el negocio no operara. La declaración actual aporta agregados aproximados, no registros supervisados.

Desarrollo reúne dos mundos alternativos de doce clientes ficticios: quinientos cincuenta y nueve fiados de estudio y quinientas cincuenta y dos etiquetas conocidas. Hay cuatrocientos ochenta y cuatro puntuales, sesenta y ocho atrasados y siete desconocidos. Ochenta y nueve fiados de calentamiento construyen historia, pero no entrenan.

FINAL es otro mundo con doce clientes nuevos: doscientos sesenta fiados, doscientos cincuenta y nueve conocidos, ciento noventa y cuatro puntuales, sesenta y cinco atrasados y uno desconocido. Excluye cuarenta y dos de calentamiento. Sumar alternativas permite aprender, no afirmar volumen empresarial, personas independientes ni validación externa. Nunca convertimos un desconocido en puntual.

**Acción:** mostrar tabla por mundo; DEV combinado 559/552/7, FINAL 260/259/1. Calentamiento excluido de supervisión.

| Universo | Clientes | Estudio | Clases 0 / 1 | Desconocidos | Calentamiento |
| --- | --- | --- | --- | --- | --- |
| DEV D1 | 12 | 278 | 233 / 41 | 4 | 43 |
| DEV D2 | 12 | 281 | 251 / 27 | 3 | 46 |
| DEV combinado | 24 | 559 | 484 / 68 | 7 | 89 |
| FINAL separado | 12 | 260 | 194 / 65 | 1 | 42 |

## 4. Fuente y dos relaciones EDA DEV
**Tiempo:** 75 s | **Expositor propuesto:** César

Rildo declara ocho atrasos entre cuarenta y cinco anotaciones evaluables: diecisiete coma setenta y ocho por ciento. Son agregados aproximados de una fuente parcial, no registros del modelo. Los abonos usan diez entre cuarenta y ocho; tres desenlaces son desconocidos. Simulamos montos de cinco a cincuenta soles y cupo ochenta; veinte es monto típico declarado, no media observada.

El EDA describe exclusivamente las quinientas cincuenta y dos etiquetas DEV. Sin atraso previo, ocho de doscientos dieciocho se atrasan; con él, sesenta de trescientos treinta y cuatro. No hay casos sin historial, por tanto esa tasa no es estimable.

La segunda relación es antigüedad frente a ventas vinculadas a crédito. En bandas fijas de treinta a ciento diecinueve, ciento veinte a doscientos treinta y nueve y desde doscientos cuarenta días, las medianas son ocho, trece y veintiuna ventas. Describe acumulación sintética, no causalidad ni señal validada de atraso. Exposición tiene quinientos cincuenta y uno, uno y cero casos: no sostiene tendencia general.

**Acción:** reutilizar `anexos/datos/eda_relaciones_entrega.png`: historial y scatter antigüedad-ventas, sin sustituirlo por tendencia de exposición. Bandas n=80/302/169; una fila de 28 días queda fuera de bandas pero dentro del scatter n=552. Clientes compartidos entre bandas, filas no independientes. Análisis post hoc de DEV congelado, no selección de variables.

## 5. Modelos y validación agrupada
**Tiempo:** 75 s | **Expositor propuesto:** César

Comparamos árbol y SVM lineal con dos referencias: clase mayoritaria y siempre positivo. Ambos modelos reciben once predictores previos y un Pipeline con imputación por mediana y escalado, ajustados dentro de cada entrenamiento. En SVM el Pipeline también está dentro de la calibración sigmoide. Identificadores y desenlaces no son predictores.

Se usaron tres pliegues externos agrupados por cliente: trescientas sesenta y ocho filas entrenan y ciento ochenta y cuatro validan en cada uno. SVM calibra con tres internos también agrupados. El protocolo permite bajar a dos solo por adecuación de clases, nunca por resultados favorables; aquí no hizo falta.

Se exploraron dieciocho configuraciones y siete umbrales, ciento veintiséis combinaciones. OOF excluye al cliente evaluado de su ajuste, pero reutilizarlo para seleccionar introduce optimismo. La calibración interna no convierte esto en evaluación anidada independiente. D2 conserva veintisiete atrasos, bajo la referencia orientativa de treinta; combinar mundos no elimina esa reserva ni prueba generalización temporal.

**Acción:** 12 configuraciones árbol + 6 SVM, 3 externos por cliente, 3 internos SVM. Desconocidos fuera de CV, Pipeline y métricas; en FINAL sí compiten por capacidad.

## 6. Selección congelada: F2 de política limitada
**Tiempo:** 75 s | **Expositor propuesto:** Omara

Primero aplicamos umbral; después ordenamos alertas por score y conservamos hasta cinco por réplica y fecha civil. Las historias alternativas no compiten en una cola conjunta. El identificador ficticio resuelve empates. Predicción positiva y revisión efectiva no son lo mismo.

V4 maximiza F2 OOF de esa política limitada, sin el antiguo piso de precisión. Favorecer cobertura es propuesta investigativa del equipo, no costo medido ni objetivo aprobado por Rildo. La fórmula pondera más los falsos negativos, pero no expresa soles de pérdida.

Ganó SVM lineal, C uno, pesos balanceados y umbral cero coma diez: F2 OOF cero coma quinientos cincuenta y nueve frente a cero coma quinientos treinta y dos del árbol. Protocolo y semilla FINAL estaban predeclarados. Aunque el árbol consiga mayor F2 final, conservamos SVM: no hay nueva selección. Los siete desconocidos DEV no compitieron en la cola OOF; esa limitación permanece. Esta entrega transcribe la decisión congelada, no la recalcula.

**Acción:** `F2 = 5TP / (5TP + 4FN + FP)`; caché SVM OOF 0,55921 y árbol 0,53165; `C=1`, `class_weight=balanced`, umbral 0,10. Selección 14/11/2026 20:20:53,285017 UTC anterior a FINAL; no aplicar la nueva meta de negocio retrospectivamente a esta selección.

## 7. Resultados: bruto y política separados
**Tiempo:** 40 s | **Expositor propuesto:** Tamara

Comparamos las mismas doscientas cincuenta y nueve etiquetas finales antes del tope. SVM obtiene F2 cero coma setecientos uno y árbol cero coma setecientos once; ambos detectan noventa y tres coma ochenta y cinco por ciento de atrasos. El mayoritario tiene mayor accuracy, pero recall cero. Siempre positivo bruto detecta todos; limitarlo cambia las métricas. Las cuatro familias tienen tarjetas separadas de política. No mezclamos denominadores ni afirmamos superioridad universal o significancia estadística.

**Acción:** tabla RAW FINAL; tarjetas de política FINAL de las cuatro familias tomadas del reporte. Para SVM/árbol el tope no retira alertas; positivo bruto F2=0,62620 frente a limitado F2=0,62257, recall=0,98462. Precisión sin alertas usa `zero_division=0`.

## 8. Error guardado e interpretación del margen
**Tiempo:** 40 s | **Expositor propuesto:** César

SVM registra ochenta verdaderos negativos, ciento catorce falsas alertas, cuatro atrasos omitidos y sesenta y uno detectados. El caso guardado AL4-T-L00045, con cuatro pagos sin atraso, tuvo score cero coma cero setenta y tres y terminó atrasado. Además, paid_late tiene coeficiente positivo cero coma siete siete seis nueve nueve; punctuality_rate, negativo cero coma dos ocho siete cinco ocho. Son pesos del margen estandarizado, no cambios directos de probabilidad ni causas. Historial puntual no garantiza el siguiente pago; no reajustamos con este error.

**Acción:** matriz `[[80,114],[4,61]]`, caso del caché score=0.07274632365606258, real=1/predicho=0. Coeficientes guardados: `paid_late +0,77699`, `punctuality_rate -0,28758`; describir signos manteniendo los demás predictores, no atribución causal o explicación completa del caso. No volver a inferir FINAL.

## 9. Demo principal: CLI local offline
**Tiempo:** 70 s | **Expositor propuesto:** Tamara

La demo principal propuesta es CLI offline: once campos ficticios, sin etiqueta. El respaldo guardado da cero coma ciento diecinueve, mayor que cero coma diez: candidata a revisión. No prueba acierto ni aprueba crédito. Si falla, declararemos el fallo y mostraremos el respaldo como guardado.

**Acción:** 20 segundos hablados + 50 de operación: entrada 10, comando 10, salida 20, límites 10. Ensayo y demo humana pendientes. Desde la raíz del paquete, usar el wrapper relativo `APF3_TD_Grupo2_ML_Innovacion.py`. CLI técnica guardada: [prueba CLI](../anexos/integracion/prueba-cli-v4.json), passed, score 0,11922453881690649; Docker + CLI 0,824 s para un ejemplo ilustrativo, no ensayo humano. Requiere Python 3.12.14 y dependencias ML versionadas o Docker existente compatible. El venv documental no es entorno ML. No instalar ni descargar durante la demo; no requiere preparar ni abrir la aplicación web.

```bash
python APF3_TD_Grupo2_ML_Innovacion.py --predict-artifact-dir experimento --input-json experimento/illustrative_input.json --output-json demo_salida_NUEVA.json
```

**Acción:** comprobar antes el wrapper raíz y manifiesto, artefactos confiables y salida libre. Si el wrapper aún no está preparado, resolverlo con empaquetado antes del ensayo; no afirmar preparación completa. Si el nombre existe, elegir otro nuevo sin sobrescribir evidencia. Alternativa Docker compatible existente, desde la raíz, con el paquete montado y sin red; comprobar previamente arquitectura, ruta del intérprete y soporte del wrapper:

```bash
docker run --rm --network none --entrypoint python -v "$PWD:/entrega" -w /entrega credify-demo-academic-api:v4 APF3_TD_Grupo2_ML_Innovacion.py --predict-artifact-dir experimento --input-json experimento/illustrative_input.json --output-json demo_salida_NUEVA.json
```

**Acción:** la imagen de referencia es local arm64, no promesa de compatibilidad universal; validar entorno antes, no improvisarlo dentro de los 50 segundos. Entrada guardada exacta:

```json
{"features":{"completed_sales":6,"paid_credits":4,"paid_late":1,"pending_overdue":0,"pending_current":0,"outstanding":0,"utilization":0,"requested_ratio":0.25,"tenure_days":60,"punctuality_rate":0.75,"overdue_rate":0}}
```

**Acción:** mostrar `experimento/illustrative_output.json` solo como respaldo previamente guardado. `known_label` debe conservarse `null`. Seis ventas de crédito, cuatro pagos y uno tardío; ratio 0,25 × cupo S/ 80 = S/ 20. La consulta individual solo aplica umbral; la revisión efectiva requiere la cola completa.

```json
{"origen":"simulado","illustrative_only":true,"known_label":null,"family":"svm","probability":0.11922453881690649,"threshold":0.1,"predicted":1,"research_only":true,"business_approval":false}
```

**Acción:** prohibidos fit, generación, reproducción y cualquier nueva predicción FINAL. No inventar terminal, grabación, duración ni éxito. Ante fallo declarar «ejecución en vivo fallida/no realizada» y usar respaldo rotulado dentro de los mismos 50 segundos; si no es verificable, reconocerlo. Grabaciones auténticas se rotulan grabadas.

## 10. Negocio: meta observable propuesta ahora
**Tiempo:** 60 s | **Expositor propuesto:** Pablo

SVM propone ciento setenta y seis revisiones frente a doscientas cincuenta y cinco de revisar todo limitado: setenta y nueve menos, pero cuatro atrasos omitidos frente a uno. Multiplicar por dos minutos produce ciento cincuenta y ocho minutos hipotéticos, no ahorro observado.

Para un futuro piloto autorizado proponemos medir minutos antes revisando todo y después con la política, en periodos comparables. El criterio observable sería minutos después menores que antes, máximo cinco alertas diarias y reporte de falsos negativos, falsas alertas y sus costos. No basta ahorrar tiempo si el daño no está acordado.

Esta meta se formula retrospectivamente ahora: no fue predeclarada para elegir SVM ni aprobada por el negocio. Faltan baseline cronometrado, costos y revisión humana. El cálculo solo cubre fiados elegibles otorgados en veinticuatro semanas ficticias y tres días; no solicitudes rechazadas ni todo el trabajo del negocio.

**Acción:** SVM conocidas/desconocidas 175+1; todo limitado 254+1. No comparar contra 260 alertas brutas para calcular 79. Meta PROPUESTA, no éxito ni aprobación: minutos DESPUÉS < ANTES, ≤5/día, reportar consecuencias FN/FP sin retocar FINAL.

## 11. Integración web local, no producción
**Tiempo:** 60 s | **Expositor propuesto:** Tamara

V4 tiene CLI y web local en laboratorio académico v cuatro, con API autenticada. La evidencia guardada acredita stack local con Docker, Postgres, JWT y navegador, usando el ejemplo ilustrativo, no nuevas cohortes FINAL. No crea créditos ni aplica una cola operativa. La demo principal sigue siendo CLI offline por control del entorno y del tiempo.

No afirmamos publicación V4, producción ni disponibilidad de la URL pública heredada. Esa demo y el laboratorio local son entornos distintos. Un hash detecta cambios, pero no vuelve seguro un Joblib ajeno.

La reproducción guardada pasó: quince archivos, doce evaluaciones brutas, doce políticas y cinco estados aprendidos exactos, aunque los bytes Joblib difieren. Repetir el protocolo no es validación independiente. Las verificaciones técnicas y esta exportación no sustituyen preparación del equipo expositor, revisión individual ni ensayo humano. No prometemos SLA ni aceptación comercial.

**Acción:** web/API V4 local, bundle confiable solo lectura; flag staging deshabilitado por defecto. Evidencia: [stack local](../anexos/integracion/evidence-stack-v4.json). [Latencia guardada](../anexos/integracion/latencia-v4.json): 30 llamadas calientes del servicio, mediana 1,90 ms, p95 2,23 ms; no HTTP/red/navegador, concurrencia ni SLA. Demo principal CLI offline; no preparar web ni desplegar laboratorio. Conservar salvedades de reproducción y bytes Joblib distintos. No acredita producción ni ensayo humano.

## 12. Normativa, supuestos y asistencia IA
**Tiempo:** 45 s | **Expositor propuesto:** Pablo

Aplican Ley veintinueve mil setecientos treinta y tres y Decreto Supremo cero dieciséis de dos mil veinticuatro, JUS. Datos ficticios y hashes no certifican cumplimiento ni consentimiento. Faltan finalidad, base jurídica, accesos, conservación y derechos ARCO para datos reales. Población, calentamiento, Beta, dispersiones y estabilidad temporal son supuestos; efectivo no modelado. El anexo IA conserva prompts disponibles, pero hay una brecha del historial anterior. La asistencia y la comprobación técnica no acreditan autoría revisada, aprobación ni conformidad humana.

**Acción:** Ley N.° 29733 y D.S. N.° 016-2024-JUS; no publicar ficha privada. Anexo H del informe: prompts disponibles, historial incompleto y registro humano pendiente. No reconstruir prompts ausentes, firmas o actas. Beta(8/45×3,37/45×3), sigmas log 0,45/0,55 y estacionariedad marzo-septiembre ficticios no son mediciones del propietario.

## 13. Conclusión defendible y pendientes
**Tiempo:** 45 s | **Expositor propuesto:** Pablo

V4 alinea parcialmente rangos y escala, y supera F2 de ambas referencias solo en simulación. Conserva ciento catorce falsas alertas y cuatro omisiones. FINAL tiene veinticinco coma diez por ciento de atraso frente a diecisiete coma setenta y ocho de la fuente aproximada; no forzamos tasas ni cambiamos selección. La integración web está probada localmente, no en producción. Entregamos documentos verificables y demo CLI propuesta; siguen pendientes revisión individual, ensayo, costos y captura real autorizada. Alineación parcial no es validación real ni utilidad comercial probada.

**Acción:** cierre técnico documental, no humano; no activar producción, reentrenar ni inventar acuerdos. Preguntas: cinco minutos fuera de los doce.

# Preguntas difíciles y respuestas breves

**Uso:** 18 preguntas fuera de las 13 diapositivas y de los 720 segundos.

**¿Qué cambia en esta entrega?** Nueva edición documental independiente con web/API local probada, EDA historial y antigüedad-ventas, interpretación oral del margen, meta propuesta y demo CLI offline. No cambia experimento, runtime ni selección.

**¿Rildo aprobó el modelo o aportó filas?** No. Solo fuente agregada aproximada y parcial, hash `45bc22a10ad5dccf323708b8aeabb780d8de4629ff5087cca2582c7dd055819f`; no aprobación de F2 ni consentimiento de clientes. Formulario hipotético excluido.

**¿Por qué 8/45 y 10/48?** Hay 48 anotaciones, tres sin desenlace; atraso 8/45=17,78 %, abonos 10/48=20,83 %. Son universos distintos, ninguno es dataset supervisado real.

**¿Son 819 operaciones reales?** No: DEV 559/552/7 y FINAL 260/259/1 son historias ficticias alternativas. No sumarlas como volumen real; calentamiento 89 y 42 excluido de entrenamiento.

**¿Doce oportunidades garantizan doce otorgamientos?** No. Agenda 12/9 oportunidades/clientes; FINAL registra medias 10,6667/8,75 en 24 semanas completas. Visitas 3-14 días, media 6,9512; no intervalos entre otorgamientos.

**¿Qué muestran las dos relaciones EDA?** Historial 8/218 y 60/334, sin historial n=0. Antigüedad-ventas: medianas 8/13/21 en bandas fijas 30-119/120-239/≥240, n=80/302/169; una fila de 28 días fuera de bandas. Scatter n=552, no causalidad. Exposición 551/1/0 no sostiene tendencia.

**¿Tres pliegues bastan?** Tres externos por cliente y tres internos SVM, fallback solo por clases no usado. D2 tiene 27 atrasos; 24 clientes DEV no son 552 individuos independientes.

**¿Cómo controlan fuga y optimismo?** Pipeline dentro de cada ajuste, clientes separados, sin desenlaces futuros. Reutilizar OOF para seleccionar introduce optimismo; calibración interna no es evaluación anidada independiente ni validación temporal.

**¿Quién aprobó F2, cinco casos o dos minutos?** Nadie ha acreditado aprobación comercial. F2 es propuesta investigativa; capacidad y tiempo son estimaciones sin cronómetro. La nueva meta antes/después se propone ahora, no antes de seleccionar.

**¿Por qué mantener SVM si árbol gana en FINAL?** Selección congelada OOF F2 SVM 0,55921 frente a árbol 0,53165. FINAL F2 0,70115/0,71096 no se reutiliza para elegir. Nueva selección exigiría protocolo y test no consultado.

**¿Supera a siempre positivo?** Solo descriptivamente en F2 de política: SVM 0,70115 frente a limitado 0,62257. Positivo bruto F2 0,62620 y recall 1; limitado recall 0,98462. Mayoritario accuracy 0,74903, recall 0. Sin dominancia universal ni significancia demostrada.

**¿Qué pasa con desconocidos y tope?** Siete desconocidos DEV fuera de OOF; FINAL puntúa 260 juntos para capacidad, métricas en 259. SVM 175 conocidas +1 desconocida; todo limitado 254+1. Tope por réplica/fecha, no entre mundos.

**¿Cómo interpretar error y coeficientes?** Matriz SVM [[80,114],[4,61]], caso AL4-T-L00045 score 0,07274632365606258 bajo 0,10, real 1/predicho 0. paid_late +0,77699 y puntualidad -0,28758 son pesos del margen estandarizado, no efectos causales ni incrementos de probabilidad; no explicación completa del caso.

**¿La demo prueba acierto?** No: `known_label:null`, score guardado 0,11922453881690649, umbral 0,1. Predicción 1 solo candidata, sin aprobación ni cola completa. No se ejecuta durante la exportación documental.

**¿Los 158 minutos compensan las omisiones?** No demostrado: (255−176)×2 hipotéticos y tres FN adicionales. Proponemos después<antes con periodos comparables, ≤5/día y costos FN/FP explícitos; sin baseline medido, costo acordado ni aceptación comercial.

**¿La simulación está validada plenamente?** No: Beta, sigmas, población, calentamiento, estabilidad temporal y efectivo no modelado son límites. DEV 12,32 %, FINAL 25,10 %, fuente aproximada 17,78 %, sin forzar etiquetas ni semilla.

**¿La web V4 está publicada?** Solo integración local probada con evidencia Docker/Postgres/JWT/navegador. No producción ni disponibilidad pública comprobada. Reproducción guardada pasa 15 SHA, 12 brutas, 12 políticas, cinco estados exactos; bytes Joblib distintos y exclusiones documentadas. No ensayo humano.

**¿Qué pasa si falla la demo y quién revisó?** Declarar fallo/no realizada, mostrar `illustrative_output.json` como guardado o reconocer falta. Python 3.12.14 y dependencias ML o Docker compatible existente, wrapper raíz y salida libre deben prepararse antes. Revisión individual, ensayo y consentimiento siguen pendientes; no inventar actas ni completar historial IA ausente.

# Lista de revisión humana pendiente

**Estado:** todas pendientes; registrar solo revisiones auténticas con fecha, alcance y corrección. Preparación técnica no equivale a ensayo ni aprobación.

- [ ] Confirmar nombres, códigos y reparto propuesto de Omara, César, Tamara y Pablo.
- [ ] Revisar fuente aproximada Rildo, hash y denominadores; custodiar ficha y excluir formulario hipotético.
- [ ] Cotejar cohortes 559/552/7 y 260/259/1, clases y calentamiento excluido.
- [ ] Revisar EDA historial y antigüedad-ventas; exposición sin tendencia, sin causalidad.
- [ ] Revisar CV agrupada, optimismo OOF, D2=27 y selección SVM congelada.
- [ ] Cotejar cuatro familias RAW y política, matrices y error guardado sin reinferir FINAL.
- [ ] Revisar pesos del margen estandarizado, no efectos causales o probabilísticos.
- [ ] Revisar meta retrospectiva propuesta, baseline/costos pendientes y minutos hipotéticos.
- [ ] Preparar wrapper raíz, Python 3.12.14/ML o Docker existente compatible, manifiesto y salida nueva.
- [ ] Ensayar 20 s hablados + 50 s operativos; comprobar respaldo con known_label null y declarar fallos.
- [ ] Revisar evidencia web local, no publicación V4/producción ni aprobación automática.
- [ ] Revisar normativa y supuestos antes de datos reales; no inventar consentimiento.
- [ ] Contrastar asistencia IA y prompts disponibles; mantener brecha histórica y registro humano pendientes.
- [ ] Ensayar las 13 intervenciones en 720 segundos y registrar revisiones individuales auténticas.
