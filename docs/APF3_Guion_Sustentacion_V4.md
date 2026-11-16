# APF3 · Grupo 2 · Guion y contenido para PPT V4

**Base documental:** informe materializado `informe/APF3_TD_Grupo2_ML_Innovacion_Borrador.md`, `informe/verificacion-informe-v4.json` y evidencia estructurada de `experimento/aligned_v4_report.json` del paquete congelado `/Users/tamaraalison/Downloads/APF3_Grupo2_Alineado_V4`, versión `academic-owner-aligned-v4`, emitido el 14/11/2026 a las 20:20:53,604359 UTC. Se contrastan procedencia, selección, auditoría, EDA DEV, métricas, errores e inferencia ilustrativa. Las cifras son transcripciones: esta edición no genera datos, experimentos, entrenamiento ni inferencia; tampoco rematerializa el informe.

**Cierre técnico documentado:** `verificacion-reproduccion.json` final tiene `passed=true` y SHA-256 `86831dabd16b66499afbea6cc7f621c6dba5827367ae2526c788396900872558`: 15 archivos SHA-256, 12 evaluaciones brutas, 12 políticas y cinco estados aprendidos exactos. Los bytes de los cinco Joblib NO son iguales; `estado-artefactos.json` registra ambas huellas binarias. Se excluyen tres timestamps (`report.generated_utc`, `provenance.recorded_utc`, `selection.frozen_utc`) y dos hashes derivados (`selection.decision_sha256.provenance.json`, `artifact_manifest.frozen_selection.json`); las cadenas locales pasan. La CLI aislada, sin red, sí se comprobó técnicamente sobre artefactos originales y reproducidos. No acredita ensayo humano, integración web, validación independiente ni aceptación comercial. El plan de notas registra las huellas actuales del informe y su verificación, que pueden actualizarse por otra edición autorizada.

**Uso:** exactamente 13 diapositivas. Los párrafos bajo cada encabezado son texto hablado; las tablas, comandos y bloques **Acción:** son apoyo visual no pronunciado. Preguntas y revisión humana quedan fuera de los doce minutos. No se acredita ensayo, revisión individual ni aprobación empresarial.

**Reparto propuesto, no constancia de contribuciones pasadas:** los cuatro integrantes deben confirmar sus intervenciones y revisar el contenido. No se atribuyen trabajos realizados, consentimiento o conformidades por asignar una exposición.

| Integrante | Código | Rol propuesto para esta sustentación |
| --- | --- | --- |
| Omara Yamileth Baylón Vila | U23231338 | Continuidad, problema, procedencia y selección |
| César Augusto Daniel Paredes Paredes | U23259768 | Escala, EDA, metodología y errores |
| Tamara Alison Coveñas Quispe | U23204737 | Resultados, inferencia local e integración |
| Pablo Enrique Yman Avila | U23251279 | Interpretación de negocio, normativa y cierre |

**Cronometraje fijo:** 30 + 30 + 75 + 75 + 75 + 75 + 40 + 40 + 70 + 60 + 60 + 45 + 45 = **720 segundos, 12 minutos**. La diapositiva 9 reserva **20 segundos hablados y 50 segundos de operación en vivo**, no 70 de narración. Ventanas acumuladas: 00:00, 00:30, 01:00, 02:15, 03:30, 04:45, 06:00, 06:40, 07:20, 08:30, 09:30, 10:30, 11:15 y 12:00. Relevos incluidos.

**Extensión hablada:** 1329 palabras, medidas con `parse_notes` actual de `deploy/generate-apf3-defense.py` y registradas en `sustentacion/plan-notas-v4.json`, exclusivamente en los párrafos pronunciados de las 13 diapositivas; excluye portada, tablas, acciones, comandos, preguntas y revisión. Dentro del objetivo de 1250 a 1450 palabras; la duración requiere ensayo humano.

**Fuente comercial única:** declaración actual de Rildo, consulta declarada del 08/10/2026 sobre septiembre de 2026, SHA-256 `45bc22a10ad5dccf323708b8aeabb780d8de4629ff5087cca2582c7dd055819f`. El formulario anterior enteramente hipotético queda excluido como evidencia y calibración. El documento privado no se reproduce; solo se citan agregados y hash.

**Alcance de la instrucción:** se conserva el fragmento literal aportado para esta fase, «ya haz lo que sigue...», junto con la aclaración de usar únicamente la declaración actual y la precisión de denominadores. No es una entrevista nueva, aceptación del modelo, acreditación de autoría humana ni consentimiento nuevo. La asistencia documental no sustituye revisión personal.

## 1. Fiado a un día: continuidad y equipo
**Tiempo:** 30 s | **Expositor propuesto:** Omara

Presentamos V4 para el fiado a un día en Cervecería Baylón. APF1 identificó cuaderno y criterio personal; APF2 desarrolló Credify. APF3 compara modelos como apoyo a revisión humana, no para aprobar automáticamente. La novedad es alinear parcialmente la simulación con la declaración actual de Rildo; el formulario hipotético anterior queda excluido. Nuestro reparto de exposición es propuesto, no una constancia de contribuciones.

**Acción:** mostrar los cuatro nombres completos y códigos de la portada, continuidad APF1 → APF2 → APF3 y rótulo «V4 · registros ficticios · revisión humana». Identificar la fuente por el hash `45bc…819f`, sin abrir el formulario privado ni atribuir aprobación del modelo al propietario.

## 2. Problema ML e indicador financiero
**Tiempo:** 30 s | **Expositor propuesto:** Omara

Buscamos anticipar atraso frente al vencimiento contractual del día siguiente, usando solo información previa al otorgamiento. Cada fila es un fiado: uno significa atraso y cero, puntualidad. Los tres días de gracia no cambian esa etiqueta. El cinco por ciento de antecedentes es pérdida mensual estimada sobre ventas, no prevalencia, probabilidad ni objetivo conseguido. Un atraso tampoco equivale a pérdida definitiva.

**Acción:** mostrar «Clasificación binaria supervisada · target: late_payment» y, separado, «5 % referencial = pérdida mensual estimada / ventas del mes × 100; sin corroboración contable específica». No convertirlo en tasa de etiquetas.

## 3. Dataset: historias alternativas, no volumen real
**Tiempo:** 75 s | **Expositor propuesto:** Omara

No hay filas reales de clientes en entrenamiento ni evaluación. Al cierre de APF2 el piloto no había empezado y el exportador produjo cero fiados elegibles; eso no significa que el negocio no operara. La declaración actual aporta agregados, no registros supervisados.

Desarrollo reúne dos mundos alternativos de doce clientes ficticios cada uno: quinientos cincuenta y nueve fiados de estudio, con quinientas cincuenta y dos etiquetas conocidas. Son cuatrocientos ochenta y cuatro puntuales y sesenta y ocho atrasados; siete quedan desconocidos. Ochenta y nueve fiados de calentamiento no son filas de entrenamiento.

FINAL es otro mundo de doce clientes distintos: doscientos sesenta fiados de estudio, doscientos cincuenta y nueve conocidos, con ciento noventa y cuatro puntuales, sesenta y cinco atrasados y uno desconocido. Excluye cuarenta y dos de calentamiento. Sumar alternativas sirve para aprender, nunca para afirmar volumen real ni validación externa.

**Acción:** mostrar los bloques separados, sin sumar DEV y FINAL como actividad de una empresa. El calentamiento construye historia previa, pero no aporta filas supervisadas.

| Universo ficticio | Clientes | Estudio | Conocidos: 0 / 1 | Desconocidos | Calentamiento excluido |
| --- | --- | --- | --- | --- | --- |
| DEV D1 | 12 | 278 | 274: 233 / 41 | 4 | 43 |
| DEV D2 | 12 | 281 | 278: 251 / 27 | 3 | 46 |
| DEV combinado para ML | 24 | 559 | 552: 484 / 68 | 7 | 89 |
| FINAL separado | 12 | 260 | 259: 194 / 65 | 1 | 42 |

## 4. Fuente, escala y EDA de desarrollo
**Tiempo:** 75 s | **Expositor propuesto:** César

La fuente declara cuarenta y cinco anotaciones evaluables y ocho atrasos: diecisiete coma setenta y ocho por ciento. No son registros del modelo. Los límites simulados son cinco a cincuenta soles y exposición máxima ochenta. Veinte soles es monto típico declarado, no media empírica.

La agenda fija doce oportunidades y nueve clientes distintos por semana completa. Eso no garantiza doce otorgamientos: FINAL registra medias de diez coma sesenta y siete fiados y ocho coma setenta y cinco clientes con otorgamiento. Las visitas agendadas conservan intervalos de tres a catorce días, media seis coma noventa y cinco.

El EDA usa solo las quinientas cincuenta y dos etiquetas DEV: ochenta y siete coma sesenta y ocho por ciento puntuales. Hay al menos dos pagos previos; no hay casos sin historial. Las tasas son tres coma sesenta y siete por ciento sin atraso previo y diecisiete coma noventa y seis con él. La exposición reúne quinientos cincuenta y uno, uno y cero casos por banda: no sustenta una tendencia general ni causalidad. Son asociaciones sintéticas, no validación real.

**Acción:** separar «fuente», «reglas del generador» y «resultado auditado». Las medias semanales FINAL usan 24 semanas completas; no dividir totales con días adicionales o calentamiento. No confundir intervalos de visitas agendadas con intervalos entre fiados otorgados.

**Acción:** consultar el EDA ya materializado del informe y `relationships` en `informe/verificacion-informe-v4.json`, sin generar figuras en esta edición. Historial: sin pagos previos n=0, tasa no estimable (no 0 %); pagados sin atraso 8/218=3,67 %; con pagos tardíos 60/334=17,96 %. `paid_credits` mínimo DEV=2. Utilización: 0-25 %: 68/551=12,34 %; >25-50 %: 0/1=0 %; >50 %: n=0, no estimable. No hay soporte para tendencia general por exposición ni para comportamiento sin historial. De 48 anotaciones fuente, tres son desconocidas; parcialidad es 10/48, no 10/45.

## 5. Modelos y validación agrupada
**Tiempo:** 75 s | **Expositor propuesto:** César

Comparamos árbol y SVM lineal con dos referencias: clase mayoritaria y siempre positivo. Ambos modelos reciben once predictores previos y un Pipeline con imputación por mediana y escalado, ajustado dentro de cada entrenamiento. En SVM ese Pipeline también queda dentro de la calibración sigmoide.

Se utilizaron tres pliegues externos agrupados por cliente, sin compartir clientes entre entrenamiento y validación. La calibración SVM usó tres internos, también agrupados. El protocolo permite bajar a dos solo por adecuación de clases, nunca por resultados favorables; aquí no hizo falta.

Se exploraron dieciocho configuraciones y siete umbrales: ciento veintiséis combinaciones. OOF significa predicciones de ajustes que no vieron al cliente evaluado. Reutilizar OOF para seleccionar introduce optimismo: calibración interna no equivale a evaluación anidada independiente. D2 tiene solo veintisiete atrasos, bajo la referencia orientativa de treinta; combinar mundos no elimina esa reserva.

**Acción:** mostrar «3 externos → OOF de selección → congelamiento → FINAL común» y «SVM: 3 internos». Cada externo: 368 filas/16 clientes para entrenar y 184/8 para validar. Mostrar «12 configuraciones árbol + 6 SVM; 7 umbrales». Los desconocidos se excluyen de CV, Pipeline y métricas; en FINAL sí compiten por capacidad. IDs y desenlaces no son predictores. Los umbrales de suficiencia, 200 filas y 30 minoritarios, son banderas, no garantía estadística.

## 6. Selección congelada: F2 de revisión limitada
**Tiempo:** 75 s | **Expositor propuesto:** Omara

Primero aplicamos el umbral; después ordenamos alertas por score y conservamos hasta cinco por réplica y fecha civil. Las alternativas no compiten en una cola conjunta. En empate se usa el identificador ficticio del fiado. Predicción positiva y revisión efectiva son conceptos distintos.

V4 maximiza F2 OOF de esa política limitada, sin el antiguo piso de precisión. Favorecer cobertura de atrasos es una propuesta investigativa del equipo, no un costo medido ni una meta aprobada por Rildo.

Ganó SVM lineal, C uno, pesos balanceados y umbral cero coma diez: F2 OOF cero coma quinientos cincuenta y nueve frente a cero coma quinientos treinta y dos del árbol. Protocolo y semilla final estaban predeclarados. Aunque el árbol consiga mejor F2 final, conservamos SVM. Los siete desconocidos DEV no compitieron en la cola OOF: esa limitación permanece.

**Acción:** mostrar `F2 = 5TP / (5TP + 4FN + FP)`, «sin piso P ≥ 0,50» y «tope: 5 por réplica/fecha, después del umbral». Valores exactos: SVM OOF F2=0,55921; árbol=0,53165. SVM: `C=1`, `class_weight=balanced`, `threshold=0.10`. Semillas DEV: 2026112101 y 2026112102; FINAL: 2026112103, prefijada. Selección congelada el 14/11/2026 a las 20:20:53,285017 UTC, antes de generar FINAL. No reajustar con el test.

## 7. Resultados finales: clasificador bruto
**Tiempo:** 40 s | **Expositor propuesto:** Tamara

La tabla compara las mismas doscientas cincuenta y nueve etiquetas finales antes del tope. SVM obtiene F2 cero coma setecientos uno; el árbol, cero coma setecientos once. Ambos detectan noventa y tres coma ochenta y cinco por ciento de atrasos. El mayoritario tiene mayor accuracy, pero recall cero. Siempre positivo bruto detecta todos; limitarlo cambia sus métricas. No mezclamos esa referencia bruta con la política de revisión ni afirmamos superioridad universal.

**Acción:** mostrar la tabla RAW FINAL, no OOF. Clase positiva: atraso. La precisión cero sin alertas es la convención `zero_division=0`.

| Modelo bruto congelado | Precisión | Recall | F1 | F2 | Accuracy |
| --- | --- | --- | --- | --- | --- |
| SVM seleccionada, umbral 0,10 | 0,34857 | 0,93846 | 0,50833 | 0,70115 | 0,54440 |
| Árbol, umbral 0,10 | 0,36095 | 0,93846 | 0,52137 | 0,71096 | 0,56757 |
| Dummy mayoritario | 0,00000 | 0,00000 | 0,00000 | 0,00000 | 0,74903 |
| Dummy siempre positivo bruto | 0,25097 | 1,00000 | 0,40123 | 0,62620 | 0,25097 |

**Acción:** tarjeta aparte, claramente «POLÍTICA después del tope»: revisar todo limitado tiene P=0,25196850, recall=0,98461538 y F2=0,62256809. No sustituir solo una celda de la fila bruta. En SVM y árbol el tope no retira alertas en FINAL; sus métricas coinciden con las brutas. No hay intervalos ni significancia calculados.

## 8. Errores y un caso del caché
**Tiempo:** 40 s | **Expositor propuesto:** César

La matriz SVM contiene ochenta verdaderos negativos, ciento catorce falsas alertas, cuatro atrasos omitidos y sesenta y uno detectados de sesenta y cinco. La cobertura alta convive con mucha revisión innecesaria. El caso ficticio AL4-T-L00045 tenía cuatro fiados pagados sin atraso. Su score guardado, cero coma cero setenta y tres, quedó bajo cero coma diez, pero terminó atrasado. Es un falso negativo ya registrado, no una nueva inferencia ni una explicación causal. No reajustamos con él.

**Acción:** mostrar `[[80,114],[4,61]]`, filas reales y columnas predichas, orden 0/1. Tarjeta del caché `models.svm.error_cases`: cliente `AL4-T-C004`, préstamo `AL4-T-L00045`, score=0.07274632365606258, threshold=0.1, actual=1, predicted=0, review=0. No volver a evaluar ese caso FINAL.

## 9. Inferencia local ilustrativa, no validación
**Tiempo:** 70 s | **Expositor propuesto:** Tamara

Intentaremos inferencia local con once campos de un ejemplo ficticio sin etiqueta conocida. Su resultado guardado es cero coma ciento diecinueve, superior a cero coma diez: predicción uno, candidata a revisión. No prueba acierto, no entrena y no aprueba ni rechaza el fiado.

**Acción:** 20 segundos para el párrafo y 50 completos de operación: entrada (10 s), comando (10 s), salida (20 s), límites (10 s). Demo humana aún no realizada: estas son instrucciones para el ensayo y la sustentación, no un acta de ejecución. La CLI técnica aislada sí fue comprobada en `verificacion-reproduccion.json`, sin acreditar ensayo. No se reejecuta durante esta edición. Desde la raíz del paquete, únicamente en modo inferencia y con código/dependencias compatibles:

```bash
python codigo/scripts/academic_credit_aligned_v4.py --predict-artifact-dir experimento --input-json experimento/illustrative_input.json --output-json demo_inferencia_nueva.json
```

**Acción:** mostrar exactamente las once entradas. Seis ventas vinculadas, cuatro fiados pagados y uno tardío; puntualidad 0,75. El ratio 0,25 con cupo S/ 80 representa S/ 20 solicitados. No añadir `late_payment` ni `known_label` a los predictores.

```json
{"features":{"completed_sales":6,"paid_credits":4,"paid_late":1,"pending_overdue":0,"pending_current":0,"outstanding":0,"utilization":0,"requested_ratio":0.25,"tenure_days":60,"punctuality_rate":0.75,"overdue_rate":0}}
```

**Acción:** contrastar la salida con el respaldo congelado, sin pegarlo como si acabara de ejecutarse. La salida individual aplica solo umbral: asignar revisión requiere la cola completa por réplica/fecha.

```json
{"origen":"simulado","illustrative_only":true,"known_label":null,"family":"svm","probability":0.11922453881690649,"threshold":0.1,"predicted":1,"research_only":true,"business_approval":false}
```

**Acción:** antes del ensayo auténtico, volver a comprobar runner, entorno compatible, origen confiable, manifiesto y nombre de salida libre. El código ya está empaquetado y su integridad fue comprobada; esto no garantiza que el equipo de exposición esté preparado. Si la salida existe, elegir otro nombre nuevo, sin sobrescribir ni borrar evidencia. No ejecutar entrenamiento, generación, reproducción, reajustes ni predicciones del test durante la demo.

**Acción:** si falla o falta el entorno, declarar «ejecución en vivo fallida/no realizada» y mostrar `experimento/illustrative_output.json` como «resultado previamente guardado». No inventar terminal, capturas, duración ni éxito. Si falta respaldo verificable, reconocerlo dentro de los mismos 50 segundos. Una eventual grabación auténtica debe rotularse como grabada, no en vivo.

## 10. Negocio: carga hipotética y costo de omisión
**Tiempo:** 60 s | **Expositor propuesto:** Pablo

SVM propone ciento setenta y seis revisiones: ciento setenta y cinco conocidas y una desconocida. Revisar todo con tope propone doscientas cincuenta y cinco: doscientas cincuenta y cuatro conocidas y una desconocida. Son setenta y nueve menos, pero SVM omite cuatro atrasos frente a uno: tres omisiones adicionales.

Multiplicar setenta y nueve por dos minutos produce ciento cincuenta y ocho minutos teóricos durante veinticuatro semanas ficticias completas y tres días adicionales. No es ahorro observado, beneficio financiero ni utilidad incondicional.

Cinco revisiones diarias es capacidad estimada, no cronometrada. Solo cubre alertas de fiados elegibles otorgados; deja fuera solicitudes rechazadas, cobros, registro y otras revisiones humanas. Necesitamos medir consecuencias y acordar finalidad y costos antes de proponer uso real.

**Acción:** mostrar «176 vs. 255 revisiones; 4 vs. 1 FN» y `79 × 2 = 158 minutos hipotéticos`. El positivo bruto alerta los 260, incluidos 259 conocidos y uno desconocido: no usar ese denominador para la diferencia 79. El tope cambia la referencia a matriz `[[4,190],[1,64]]`; la SVM conserva `[[80,114],[4,61]]`. No prometer reducción del 5 % financiero.

## 11. Integración mínima y frontera con el MVP
**Tiempo:** 60 s | **Expositor propuesto:** Tamara

V4 dispone de una función local y una CLI que cargan el Pipeline guardado y validan un JSON con los once campos compartidos con el MVP. El contrato comprueba esquema, conteos y ratios; devuelve score, umbral y predicción. No crea créditos ni entrena durante la consulta.

Compartir esquema no significa integración web terminada. El laboratorio heredado sigue en v2: no demuestra despliegue V4 ni autorización comercial. La conexión al MVP necesita pruebas, seguridad y revisión humana propias.

Los hashes detectan cambios, pero no vuelven seguro un Joblib desconocido. La reproducción técnica pasó: quince archivos, doce evaluaciones brutas, doce políticas y cinco estados aprendidos exactos. Los bytes Joblib no son iguales. La CLI aislada está comprobada, no el ensayo humano. No medimos latencia ni disponibilidad; repetir el protocolo no es validación independiente.

**Acción:** diagrama «JSON MVP, 11 campos → predict(artifact_dir, input_data) / CLI V4 → JSON», flecha discontinua a «MVP: integración futura» y rótulo «WEB actual: v2». Referir `verificacion-reproduccion.json` final y `estado-artefactos.json`, con salvedad binaria y exclusiones declaradas en el cierre técnico. No abrir la web como evidencia V4, cargar artefactos ajenos ni afirmar aprobación automática.

## 12. Normativa y supuestos no medidos
**Tiempo:** 45 s | **Expositor propuesto:** Pablo

Aplican la Ley veintinueve mil setecientos treinta y tres y el Decreto Supremo cero dieciséis de dos mil veinticuatro, JUS. Las cohortes no contienen identidades reales; la declaración privada solo aporta agregados y hash. Eso no certifica cumplimiento ni consentimiento de clientes. Población, calentamiento, propensión Beta y dispersiones de montos y demoras son supuestos no medidos; las ventas al contado no se modelan. La fuente real refiere septiembre; extender estabilidad entre marzo y septiembre ficticios es otra hipótesis, no observación. Alinear rangos no valida todas las distribuciones.

**Acción:** mostrar «Ley N.° 29733 · D.S. N.° 016-2024-JUS». Pendientes: finalidad/base jurídica, información y consentimiento cuando corresponda, accesos, conservación, ARCO y proveedores. No publicar formulario bruto, firmas ni contactos. La declaración del propietario no sustituye base jurídica de clientes.

**Acción:** separar fuente de supuestos: 12 clientes/mundo y cuatro semanas de calentamiento; Beta(p×3,(1-p)×3), p=8/45; sigmas logarítmicas 0,45 para montos y 0,55 para demoras. No son mediciones del propietario ni parámetros plenamente validados en el negocio.

## 13. Conclusión defendible y pendientes
**Tiempo:** 45 s | **Expositor propuesto:** Pablo

V4 alinea parcialmente rangos y escala, y mejora F2 frente a ambas referencias solo en simulación. Detecta sesenta y uno de sesenta y cinco atrasos, con ciento catorce falsas alertas. La fuente, ocho de cuarenta y cinco, procede de un cuaderno parcial y recuerdo incierto. FINAL realiza veinticinco coma diez por ciento de atraso frente a diecisiete coma setenta y ocho de esa fuente: no forzamos tasas. Conservamos el árbol final superior sin cambiar selección. Reproducción técnica comprobada; faltan revisión humana, ensayo y captura autorizada. No afirmamos utilidad comercial probada.

**Acción:** cerrar con «Alineación parcial ≠ validación real». Cerrar únicamente lo editorial/técnico comprobado: código empaquetado, EDA e informe materializados y reproducción final con salvedad binaria. Mantener pendientes ensayo, demo humana y revisiones individuales. Repetir el protocolo fijo no agrega otro test independiente. No inventar firmas, acuerdos de costos, contribuciones pasadas ni aprobación de negocio. No activar producción ni reentrenamiento.

# Preguntas difíciles y respuestas breves

**Uso:** 18 preguntas, agrupables de seis en seis por el renderer; quedan fuera de las 13 diapositivas y los 720 segundos.

**¿Qué cambió respecto de CV3?** V4 tiene fuente agregada actual, datos sintéticos propios y otra política de selección: F2 OOF después del tope, sin piso de precisión. CV3 aporta únicamente formato y continuidad documental, no filas, resultados ni parámetros transferidos.

**¿La declaración de Rildo es un dataset real o una aprobación del modelo?** No. Es la única fuente comercial agregada permitida, identificada por el hash `45bc22a10ad5dccf323708b8aeabb780d8de4629ff5087cca2582c7dd055819f`. La confirmación de fuente y denominadores no autoriza producción, aprueba F2 ni acredita consentimiento de clientes. El formulario hipotético anterior queda excluido.

**¿Por qué 8/45 y no 8/48?** De 48 anotaciones, tres carecen de desenlace: 45 evaluables, ocho atrasos, 17,78 %. La parcialidad usa otro universo: 10/48=20,83 %. Ninguna de esas anotaciones es una fila supervisada V4.

**¿Son 819 operaciones del negocio entre DEV y FINAL?** No. Son mundos ficticios alternativos, no sucursales simultáneas. DEV combina 559 fiados de dos historias para aprendizaje; FINAL contiene 260 de otra. Solo 552 y 259, respectivamente, tienen etiqueta; no se suman como volumen real ni personas independientes.

**¿Alinear doce oportunidades garantiza doce fiados por semana?** No. La agenda fija 12 oportunidades y nueve clientes; negativas de política reducen otorgamientos. FINAL registra 10,6667 otorgamientos y 8,75 clientes con otorgamiento por semana completa. Las visitas agendadas, no los créditos otorgados, conservan intervalos 3 a 14 días, media 6,9512.

**¿Qué demuestra el EDA ya materializado?** Solo describe DEV: 484 puntuales y 68 atrasos entre 552 conocidos. Mínimo dos pagos previos; sin historial n=0, tasa no estimable. Sin atraso previo: 8/218=3,67 %; con él: 60/334=17,96 %. Exposición: 68/551, 0/1 y 0/0 no estimable. La distribución 551/1/0 impide afirmar tendencia general; no demuestra causalidad ni riesgo real.

**¿Tres pliegues bastan y el fallback mejora resultados?** Se usaron tres externos y tres internos SVM. El fallback a dos depende exclusivamente de ambas clases en cada partición, no del score; no se activó. D2 conserva 27 minoritarios y bandera de insuficiencia orientativa. Las operaciones repetidas de 24 clientes DEV no son 552 personas independientes.

**¿Cómo controlan fuga y optimismo OOF?** Agrupan clientes, ajustan imputación y escala dentro de cada entrenamiento y excluyen desenlaces y variables futuras. La calibración SVM también agrupa. Aun así, usar el mismo OOF para elegir configuración y umbral introduce optimismo; no es evaluación anidada independiente de hiperparámetros ni prueba temporal externa.

**¿Quién aprobó F2, cinco casos y dos minutos?** F2 y superar referencias son propuestas investigativas del equipo. Cinco revisiones/día y dos minutos/caso son estimaciones declaradas, no capacidad cronometrada, costo validado ni meta de recall aprobada. No se hereda el piso de precisión de CV3.

**¿Por qué conservar SVM si el árbol gana en FINAL?** SVM ganó por F2 OOF de política: 0,55921 frente a 0,53165. El árbol consigue F2 final 0,71096 y SVM 0,70115; seleccionar ahora el árbol reutilizaría el test. Otra selección necesita protocolo previo y prueba no consultada.

**¿Superan realmente a siempre positivo?** Descriptivamente, en F2 de política final: SVM 0,701149 frente a 0,622568 de revisar todo limitado. El positivo bruto tiene F2 0,626204 y recall 1; limitado, recall 0,984615 y precisión 64/254=0,25196850. El mayoritario tiene accuracy 0,74903 y recall 0. No hay dominancia universal ni significancia demostrada.

**¿Qué cambia con los desconocidos y el tope?** No se imputan etiquetas. Los siete desconocidos DEV no compiten en OOF, limitación declarada. En FINAL se puntúan los 260 juntos, incluido el desconocido para capacidad; las métricas usan 259 conocidos. La cola se limita por réplica/fecha, no mezclando D1 y D2. SVM suma 175 alertas conocidas y una desconocida.

**¿Cómo interpretan la matriz y el falso negativo guardado?** Recall SVM es 61/(61+4)=0,93846 y precisión 61/(61+114)=0,34857. `AL4-T-L00045` tiene score guardado 0,07274632365606258, bajo 0,10, real=1 y predicho=0. Se lee del caché, no se reevalúa ni usa para ajustar; historial puntual no garantiza el siguiente pago.

**¿La demo de 0,1192245388 demuestra acierto o aprobación?** No: el ejemplo es nuevo, ficticio y sin etiqueta. Sus once campos incluyen seis ventas, cuatro fiados pagados y uno tardío; ratio 0,25 equivale a S/ 20 sobre cupo S/ 80. Supera 0,10, por lo que es candidato a revisión; solo la cola completa determina revisión efectiva. No entrena ni modifica FINAL.

**¿Los 158 minutos son un ahorro y compensan las omisiones?** No está demostrado. Son (255−176)×2 minutos hipotéticos de un periodo ficticio de 24 semanas completas y tres días. SVM añade tres FN, cuatro frente a uno. No se midieron costos ni trabajo completo; tampoco desenlaces contrafactuales de rechazados. Comparar con los 260 del positivo bruto daría otra cantidad y no corresponde a esa política limitada.

**¿La simulación está plenamente validada y por qué FINAL tiene más atraso?** No. La fuente pequeña y parcial ancla rangos y agregados, pero población, Beta, sigmas, independencia de parcialidad y calentamiento siguen supuestos. Se presupone estacionariedad de marzo a septiembre a partir de referencia real de septiembre; no se modela efectivo. DEV realiza 12,32 % y FINAL 25,10 %, frente a 17,78 % fuente, sin forzar etiquetas ni cambiar semilla.

**¿La web usa V4 y la reproducción ya está comprobada?** La web heredada sigue en v2; compartir once campos no acredita despliegue V4. `verificacion-reproduccion.json` final pasa: 15 archivos SHA, 12 brutas, 12 políticas y cinco estados aprendidos exactos; bytes Joblib NO iguales. Tres timestamps y dos hashes derivados se excluyen; integridad local comprobada. La CLI aislada pasó, sin acreditar ensayo humano ni validación independiente.

**¿Qué harán si falla la demo y quién revisó o consintió?** Se declara el fallo y se muestra únicamente `illustrative_output.json` identificándolo como guardado, o se reconoce que no puede mostrarse. No hay nuevas constancias de revisión individual, ensayo, consentimiento de clientes o aceptación comercial. Ley 29733 y D.S. 016-2024-JUS exigen revisar finalidad, base jurídica y controles; hashes y datos ficticios no certifican cumplimiento.

# Lista de revisión humana pendiente

**Estado inicial:** todas las casillas permanecen pendientes. Registrar únicamente revisiones auténticas, con alcance, hallazgo o corrección y fecha; no añadir firmas, conformidades ni tareas previas inventadas. Los roles de portada son propuestas.

- [ ] Confirmar nombres completos, códigos y reparto fijo de los cuatro expositores, sin atribuir contribuciones pasadas.
- [ ] Contrastar la fuente actual de Rildo y su hash; excluir completamente el formulario hipotético anterior y custodiar el bruto privado.
- [ ] Confirmar denominadores 8/45 y 10/48, incertidumbre del recuerdo y alcance parcial del cuaderno; no presentarlos como dataset de entrenamiento.
- [ ] Cotejar DEV 559/552/7, clases 484/68, 24 clientes alternativos y 89 de calentamiento excluidos; FINAL 260/259/1, clases 194/65, 12 clientes y 42 de calentamiento.
- [ ] Mantener historias alternativas separadas del volumen real y distinguir agenda de 12/9 de otorgamientos FINAL 10,6667/8,75.
- [ ] Revisar humanamente el EDA ya materializado: mínimo dos pagos previos, sin historial n=0, historial 8/218 y 60/334, exposición 551/1/0 sin tendencia general; no usar FINAL ni generar nuevas figuras.
- [ ] Verificar tres pliegues externos e internos, fallback solo por clases y bandera D2 de 27 minoritarios; conservar caveat de selección OOF.
- [ ] Revisar selección SVM C=1 balanced, umbral 0,10 y F2 OOF 0,55921; no trasladar piso de precisión ni elegir árbol por FINAL.
- [ ] Cotejar tabla RAW, matriz SVM, 114 FP, cuatro FN y caso guardado; no volver a predecir FINAL.
- [ ] Separar positivo bruto de revisar todo limitado, incluir desconocido en capacidad FINAL y comprobar 176 frente a 255 revisiones, 4 frente a 1 FN.
- [ ] Mantener 158 minutos como cálculo teórico, sin ahorro financiero, utilidad incondicional ni reducción probada del 5 %.
- [ ] Preparar el ensayo auténtico: volver a comprobar runner, entorno, artefactos confiables, entrada de once campos, salida nueva y respaldo rotulado; la CLI técnica aislada ya pasó, pero no acredita demo humana.
- [ ] Revisar humanamente la evidencia final existente: `passed=true`, 15 SHA, 12 brutas, 12 políticas y cinco estados exactos; bytes Joblib NO iguales y exclusiones declaradas. Reproducción técnica cerrada, no validación independiente.
- [ ] Mantener web v2 separada de CLI V4 y no afirmar despliegue, autorización operativa, aprobación automática o consentimiento nuevo.
- [ ] Revisar Ley 29733, D.S. 016-2024-JUS, privacidad de la fuente y controles antes de datos reales; explicitar Beta, sigmas, población, calentamiento, efectivo no modelado y estacionariedad supuesta.
- [ ] Revisar contenido asistido por IA contra fuentes; conservar el fragmento literal de instrucción como alcance, no como entrevista, autoría ni aceptación.
- [ ] Ensayar 13 intervenciones dentro de 720 segundos, con 20 hablados y 50 de operación en la diapositiva 9, y declarar cualquier fallo real.
- [ ] Registrar revisión individual auténtica de Omara, César, Tamara y Pablo, con fecha y correcciones; dejar sin cerrar todo lo no comprobado.
