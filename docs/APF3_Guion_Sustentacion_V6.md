# APF3 · Grupo 2 · Guion de sustentación V6

**Uso:** 13 diapositivas, 720 segundos: 30+30+75+75+75+75+40+40+70+60+60+45+45. Diapositiva 9: 20 segundos hablados y 50 de operación en vivo. Solo se pronuncian los párrafos de intervención; acciones, tablas, comandos y preguntas quedan fuera. Objetivo editorial 1250..1450 palabras, no requisito de la consigna. Duración real pendiente de ensayo.

**Fuentes actuales:** `experimento/pending_v6_report.json`, `resumen-v6.json`, `verificacion-reproduccion.json` y cachés JSON del paquete V6. El generador registra hashes reales antes y después; no ejecuta entrenamiento, inferencia, generación de cohortes ni lectura de documentos privados. No modifica el informe de otro agente. Revisión humana pendiente, sin acta de aprobación.

| Integrante | Código | Rol propuesto |
| --- | --- | --- |
| Omara Yamileth Baylón Vila | U23231338 | Continuidad, problema, datos y selección |
| César Augusto Daniel Paredes Paredes | U23259768 | EDA, método e interpretación |
| Tamara Alison Coveñas Quispe | U23204737 | Resultados, demo e integración |
| Pablo Enrique Yman Avila | U23251279 | Negocio, normativa y cierre |

## 1. Del cuaderno a evidencia reproducible
**Tiempo:** 30 s | **Expositor propuesto:** Omara

Presentamos el avance APF3 de Credify para Cervecería Baylón. APF1 identificó el problema del cuaderno y el criterio personal; APF2 construyó el MVP. V6 compara modelos para apoyar revisión humana del fiado a un día. No aprueba créditos automáticamente. Usamos datos ficticios y una demo local por consola. Los roles son propuestos y la revisión humana continúa pendiente.

**Acción:** mostrar título original APF3_TD_Grupo2_ML_Innovacion, nombres y códigos completos. No abrir documentos privados.

## 2. Problema supervisado y regla previa
**Tiempo:** 30 s | **Expositor propuesto:** Omara

Cada fila representa un fiado otorgado. La etiqueta uno indica atraso frente al vencimiento del día siguiente; cero, puntualidad. La gracia no transforma un atraso en puntual. Antes de evaluar, cualquier saldo positivo bloquea otro fiado, incluso no vencido o parcialmente abonado. El cinco por ciento financiero referencial no es prevalencia ni probabilidad del modelo. Cancelar la deuda permite evaluar, nunca garantiza aprobación.

**Acción:** target late_payment; separar regla comercial determinista de clasificación ML y de pérdida definitiva.

## 3. Fuente y universos sintéticos
**Tiempo:** 75 s | **Expositor propuesto:** Omara

Rildo revisó veintitrés elementos de una muestra intencional V5: doce fiados, cuatro rechazos, cuatro semanas y tres supuestos. No revisó nuevamente todas las filas V6 ni aprobó el modelo. Sus correcciones permiten soles completos o terminados en cincuenta céntimos, conservando importes exactos cuando corresponden a productos. Los pagos varían entre ocho y doce, o dieciséis y veinte horas.

La mezcla setenta y cinco sobre veinticinco, la distribución horaria y el corte estricto de las veinte horas son supuestos del equipo. Doce clientes son un grupo de ejemplo, no población real fija.

DEV contiene dos historias alternativas: quinientos cuarenta y cinco fiados, quinientos cuarenta y uno conocidos, cuatrocientos cincuenta y cuatro puntuales y ochenta y siete atrasados. Cuatro son desconocidos. FINAL tiene doce clientes nuevos, doscientos ochenta fiados, doscientos setenta y seis conocidos y cuatro desconocidos. El calentamiento excluido suma noventa y uno en DEV y cuarenta y seis en FINAL. No sumamos alternativas como volumen comercial real.

**Acción:** mostrar tabla por mundo desde resumen-v6.json: D1 273/271/2, D2 272/270/2; FINAL clases 243/33. Fuente comercial aproximada: 8/45 atrasos, 10/48 anotaciones de abonos, no dataset supervisado.

## 4. Balance y relaciones EDA DEV
**Tiempo:** 75 s | **Expositor propuesto:** César

El EDA utiliza exclusivamente las quinientas cuarenta y una etiquetas DEV conocidas, sin entrenar modelos nuevos. La clase puntual domina: cuatrocientos cincuenta y cuatro frente a ochenta y siete atrasos. Por eso una accuracy alta puede esconder ausencia total de detección. Los desconocidos no se recodifican como puntuales.

La primera relación compara la tasa de atraso entre historial sin atraso previo y con atraso previo. Los grupos se definieron antes de calcular sus conteos, sin escoger cortes favorables. La segunda relaciona antigüedad con ventas vinculadas a crédito; muestra dispersión y medianas en bandas fijas de treinta a ciento diecinueve, ciento veinte a doscientos treinta y nueve, y desde doscientos cuarenta días.

Son asociaciones sintéticas descriptivas, no causalidad. Cinco variables de pendientes y exposición valen siempre cero por la regla de elegibilidad. Además, ventas completadas y créditos pagados son duplicados: no representan dos señales independientes. Las filas repetidas por cliente tampoco son observaciones independientes.

**Acción:** mostrar figuras/eda-v6.png, calculada desde development_rows.json. Sin atraso previo: 10/253; con atraso previo: 77/288. Bandas fijas: n=62/318/161, medianas de ventas 6/13/21; cero filas fuera de bandas. No inferir tendencia de exposición constante ni generalización comercial.

## 5. Comparación y validación agrupada
**Tiempo:** 75 s | **Expositor propuesto:** César

Comparamos árbol y SVM lineal contra dos Dummy: mayoría y siempre positivo. Los modelos reciben once predictores previos; identificadores, etiqueta y desenlaces futuros quedan fuera. La imputación y el escalado se ajustan dentro de cada entrenamiento. La SVM usa calibración sigmoide interna agrupada, no convierte su margen directamente en probabilidad.

Tres pliegues externos separan clientes para evitar que una misma persona aparezca simultáneamente en entrenamiento y validación. Los resultados OOF permiten escoger configuración y umbral antes de FINAL. Reutilizar OOF para seleccionar produce optimismo; no es evaluación anidada independiente de hiperparámetros.

Las filas desconocidas del holdout compiten por la cola aunque no entren en métricas supervisadas. Sin embargo, la capacidad OOF se calcula por pliegue, réplica y fecha: modelos distintos no reproducen una cola desplegada con toda la población. FINAL es una prueba congelada con clientes separados, no autorización para volver a ajustar ni prueba de desempeño real.

**Acción:** mostrar Pipeline, agrupación y limitación de capacidad entre folds; no afirmar que se midió una cola operativa completa.

## 6. Selección congelada y sobreajuste
**Tiempo:** 75 s | **Expositor propuesto:** Omara

Seleccionamos por F dos de la política OOF, que pondera más las omisiones que las falsas alertas. El árbol obtiene cero coma cinco nueve siete cinco ocho; SVM, cero coma cinco nueve seis cinco cinco. La diferencia es pequeña y no acredita superioridad estadística. Se congeló árbol de profundidad cuatro, hoja mínima ocho, pesos balanceados y umbral cero coma dos.

La política filtra por umbral, ordena score y limita a cinco revisiones por réplica y fecha. La alerta no equivale a aprobación y un caso individual no permite aplicar el límite diario.

El árbol cae de F dos de entrenamiento aproximadamente cero coma seis dos, a OOF cero coma seis cero, y FINAL cero coma cuatro cinco. Reportamos la caída como riesgo de sobreajuste y cambio de escenario, sin retocar FINAL. SVM termina mejor en FINAL, pero sustituir al ganador después de verlo contaminaría la evaluación. Conservamos la decisión previa y declaramos sus límites.

**Acción:** mostrar valores exactos train/OOF/FINAL desde caché, tanto RAW como política; F2=5TP/(5TP+4FN+FP).

## 7. RAW y política no son lo mismo
**Tiempo:** 40 s | **Expositor propuesto:** Tamara

La tabla compara precisión, recall, F uno, F dos y accuracy brutos de los cuatro modelos. Debajo se presentan cuatro tarjetas de política, con revisiones conocidas y desconocidas separadas. El árbol tiene F dos FINAL cero coma cuatro cuatro ocho nueve; SVM alcanza cero coma cinco tres dos ocho. El Dummy positivo bruto obtiene cero coma cuatro cero cuatro cuatro, y limitado cero coma cuatro cero siete cuatro. Mayoría alcanza accuracy cero coma ocho ocho, pero F dos cero: no detecta ningún atraso. Superar referencias sintéticas satisface un criterio técnico descriptivo, no valida utilidad empresarial.

**Acción:** leer las veinte celdas desde JSON. No mezclar RAW positivo con política positiva limitada.

## 8. Errores e interpretación guardada
**Tiempo:** 40 s | **Expositor propuesto:** César

La matriz del árbol contiene ochenta y un verdaderos negativos, ciento sesenta y dos falsas alertas, cuatro omisiones y veintinueve atrasos detectados. Recall es veintinueve de treinta y tres, pero precisión apenas quince coma dieciocho por ciento: revisar muchos puntuales genera carga. El árbol guardado usa proporción de puntualidad y antigüedad en días, entre otras reglas. Sus hojas y cortes no son causas ni garantías. La clase de una hoja tampoco sustituye la comparación del score con nuestro umbral cero coma dos. Los coeficientes SVM describen margen estandarizado, no efectos sobre probabilidad.

**Acción:** mostrar un camino real guardado en unidades originales y coeficientes reales del JSON; no cargar Joblib ni inventar explicación individual del ejemplo.

## 9. Demo principal CLI offline
**Tiempo:** 70 s | **Expositor propuesto:** Tamara

Ejecutaremos el wrapper local con once campos ficticios, seis créditos pagados y un atraso previo. El respaldo guardado muestra score cero coma siete uno siete dos, umbral cero coma dos y clase uno. La etiqueta es desconocida: no demuestra acierto ni aprobación. Ahora verificamos una salida nueva.

**Acción:** 20 s hablados + 50 s de operación. CLI raíz probado técnicamente antes de clase: prueba-cli-v6.json passed=true; demo y ensayo humanos pendientes. Preparar ANTES Python 3.12.14 y requirements.txt con versiones ML exactas, o Docker compatible bayloncredit-api-training-test ya construido, alternativa técnicamente probada. Alternativa local: entorno virtual limpio y preinstalado. La imagen no viene incluida para el estudiante. Abrir terminal en la raíz V6; no entrenar en clase. Comprobar que /tmp/demo-v6-NUEVA.json no existe antes, o elegir otro nombre nuevo. Ejecutar y comprobar creación, fecha y contenido de la salida distinta del respaldo.

```bash
python APF3_TD_Grupo2_ML_Innovacion.py --predict-artifact-dir experimento --input-json experimento/illustrative_input.json --output-json /tmp/demo-v6-NUEVA.json
```

**Acción:** mostrar los once campos exactos de illustrative_input.json en la diapositiva. illustrative_output.json es respaldo previamente guardado, NO ejecución nueva. source/input etiqueta no es predictor. known_label=null, business_approval=false, review_policy_applied=false; el límite diario requiere lote completo. Si falla, declararlo y mostrar JSON/captura guardados; no fingir éxito y asumir la penalización que corresponda a la rúbrica. La exportación documental no ejecuta este comando.

**Acción:** evidencia técnica guardada en anexos/integracion/prueba-cli-v6.json y latency-v6.json, ambos passed=true. Score 0.7171978005286032, umbral 0.2, predicho 1, known_label=null, sin aprobación. Docker con arranque y CLI: 1.759 s; primera predicción: 151.73 ms; 30 llamadas calientes: mediana 142.59 ms y p95 148.92 ms. Incluyen integridad y deserialización; no HTTP, autenticación, DB, navegador ni carga sostenida. Pico 240144 KiB, aproximadamente 234.52 MiB, bajo límite 256m: no garantiza capacidad. Ambos controles previos pasan sin directorio de artefactos y sin predicción. Es preparación técnica, no ensayo humano; la exportación solo lee JSON.

## 10. Carga de revisión y utilidad pendiente
**Tiempo:** 60 s | **Expositor propuesto:** Pablo

El árbol propone ciento noventa y tres revisiones: ciento noventa y una conocidas y dos desconocidas. El Dummy positivo limitado propone doscientas setenta y siete: doscientas setenta y tres conocidas y cuatro desconocidas. Son ochenta y cuatro revisiones menos. A dos minutos supuestos cada una, resultan ciento sesenta y ocho minutos hipotéticos, no ahorro observado. Rildo calcula unas catorce solicitudes, doce fiados a nueve clientes y entre veinticinco y treinta y cinco minutos semanales: una referencia inicial aproximada, no cronometrada.

El costo importa: el árbol omite cuatro atrasos; la referencia positiva limitada no omite ninguno en FINAL. Las ciento sesenta y dos falsas alertas del árbol siguen siendo una carga considerable. No conocemos costos reales ni utilidad neta. El criterio descriptivo de superar ambos Dummy en F dos se cumple en esta simulación, pero no demuestra rentabilidad ni aceptación. Para validarlo hacen falta periodos comparables, tiempos medidos, costos de errores y un piloto autorizado con supervisión humana.

**Acción:** comparar FN 4 frente a 0 desde matrices de política; no llamar ahorro a 84×2 ni inventar una meta empresarial aprobada.

## 11. Integración mínima y reproducción
**Tiempo:** 60 s | **Expositor propuesto:** Tamara

La integración V6 existe por dos vías: la CLI con runner backend y artefactos guardados, y la demo heredada en `https://demo-credify.168-75-71-113.sslip.io/laboratorio-academico/v6`. Esta última es un laboratorio sintético autenticado, no un endpoint comercial ni producción. El ejemplo usa S/20 y no crea créditos ni evalúa finales.

La reproducción actual pasó: cuarenta y siete archivos deterministas, doce evaluaciones brutas y doce políticas coinciden; cinco Joblib son idénticos byte a byte. Esto demuestra repetición del procedimiento fijo, no validación independiente. Los hashes comprueban integridad, no vuelven seguro un archivo ajeno. Las pruebas CLI y latencia V6 se incorporan solo si existen y pasan sus verificaciones; no sustituyen demo ni ensayo humanos. Preparar el entorno antes evita instalar o entrenar durante la exposición.

**Acción:** mostrar los tres casos web: deuda bloqueada, sin historial a revisión, elegible con señal; nunca aprobación. Cotejar verificacion-reproduccion.json y prueba-cli-v6.json / latency-v6.json; tiempos locales sin SLA ni ensayo humano.

## 12. Privacidad, IA y revisión humana
**Tiempo:** 45 s | **Expositor propuesto:** Pablo

Un piloto real requiere finalidad, base jurídica, información, accesos, conservación y derechos ARCO, conforme a la Ley veintinueve mil setecientos treinta y tres y su reglamento. Datos ficticios no certifican cumplimiento. No publicamos fichas privadas ni inventamos consentimiento. El anexo de asistencia conserva prompts disponibles; la frase del usuario «ya hazlo todo correctamente» documenta una instrucción, no consentimiento de clientes ni aprobación de resultados. Reconocemos vacíos del historial. Cada integrante debe revisar cifras, límites y su intervención; no declaramos que todos revisaron sin evidencia.

**Acción:** mantener los cuatro casilleros humanos vacíos; distinguir preparación técnica de revisión individual, ensayo y validación empresarial.

## 13. Conclusión acotada
**Tiempo:** 45 s | **Expositor propuesto:** Pablo

V6 bloquea solicitudes con saldo pendiente y deriva casos sin fiados pagados al propietario, sin ejecutar el modelo. Estas reglas previas no reentrenan V6. Rildo aceptaría autorizarlo como apoyo, siempre con revisión suya, más pruebas y confiabilidad comprobada. El árbol seleccionado supera referencias en F dos sintético, detecta veintinueve atrasos y omite cuatro, con ciento sesenta y dos falsas alertas. La baja precisión, caída FINAL y mejor resultado final de SVM quedan visibles. Entregamos artefactos reproducibles y demo V6 disponible, no producción comercial inmediata ni decisiones automáticas. El siguiente paso exige revisión humana, ensayo y piloto autorizado; no nuevas promesas sobre estos datos. Las preguntas empiezan fuera de los doce minutos planificados.

**Acción:** cierre honesto; revisión humana pendiente. No afirmar validación de las 545 filas ni aprobación del modelo.

# Preguntas difíciles y respuestas breves

**¿Rildo aprobó V6?** No. Revisó 23 elementos intencionales V5 y corrigió reglas; no todas las filas V6 ni el modelo.

**¿Qué bloquea otro fiado?** Cualquier saldo positivo, aun no vencido o parcialmente pagado. Cancelar solo restituye elegibilidad de evaluación.

**¿Los doce clientes son población real?** No. Son un grupo sintético de ejemplo; las personas reales pueden variar semanalmente.

**¿Qué es supuesto del equipo?** Mezcla 75/25, distribución de horas, corte 20:00, calentamiento y estabilidad; no son frecuencias medidas.

**¿Qué representan los desconocidos?** Desenlaces no observados al corte. Compiten por revisión, pero no entrenan ni se puntúan como clase cero.

**¿Qué evita fuga entre clientes?** Separación agrupada por cliente y transformaciones ajustadas dentro de cada entrenamiento. No elimina todos los sesgos sintéticos.

**¿OOF prueba capacidad de una cola desplegada?** No. Cada fold tiene su modelo y cola; falta competencia entre folds en una cola de población completa.

**¿Por qué árbol y no SVM?** Ganó F2 de política OOF 0.5975794251134644 frente a 0.5965463108320251; FINAL no cambia la selección.

**¿SVM resulta mejor en FINAL?** Sí, F2 0.5327868852459017 frente a 0.44891640866873067. Se informa sin retocar ni sustituir al ganador.

**¿Hay sobreajuste?** La caída train/OOF/FINAL lo señala como riesgo junto al cambio de escenario; no demuestra una única causa.

**¿Por qué no accuracy?** Mayoría alcanza 0.8804347826086957 sin detectar atrasos: F2 y recall cero.

**¿El positivo tiene un solo F2?** No. RAW FINAL 0.40441176470588236; política limitada 0.4074074074074074, con conteos distintos.

**¿Cuánto cuesta detectar 29 atrasos?** En FINAL hay 162 FP y 4 FN. Precisión 0.1518324607329843; utilidad neta no medida.

**¿Los 168 minutos son ahorro?** No. Son 84 revisiones de diferencia por dos minutos supuestos; árbol FN 4 frente a Dummy limitado FN 0.

**¿Los cortes del árbol son causas?** No. Son reglas guardadas en unidades originales; score y umbral operativo son distintos de la clase mayoritaria de hoja.

**¿La demo prueba que acertó?** No: known_label=null. Score 0.7171978005286032 y predicho 1 solo ilustran inferencia sin aprobación.

**¿Hay web V6?** Sí, en la demo autenticada heredada bajo `/laboratorio-academico/v6`. Es un laboratorio sintético y no producción comercial; la CLI acredita además la integración local mínima.

**¿Reproducción significa validación real?** No. passed=true e identidad de 47 archivos y 5 Joblib acreditan repetición técnica, no consentimiento, utilidad ni revisión humana.

# Lista de revisión humana pendiente

- [ ] Omara: cotejar fuente, universos, selección y límites; registrar revisión real y ensayar tiempos.
- [ ] César: cotejar EDA, agrupación, camino del árbol y errores; registrar revisión real y ensayar tiempos.
- [ ] Tamara: preparar entorno offline, probar salida nueva CLI y respaldo; distinguir laboratorio web V6 sintético de producción comercial.
- [ ] Pablo: cotejar FN/FP, minutos hipotéticos, privacidad y asistencia IA; realizar ensayo conjunto de 12 minutos.
