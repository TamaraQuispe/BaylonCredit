# Guion de sustentación APF3 · Grupo 2

**Plan:** 12 minutos, 13 diapositivas. Incluye 50 segundos de operación en vivo. Reparto propuesto; ensayo y revisión humana pendientes.

| Diapositiva | Expositor | Segundos |
| --- | --- | --- |
| 1 | Omara | 30 |
| 2 | Omara | 30 |
| 3 | Omara | 75 |
| 4 | César | 75 |
| 5 | César | 75 |
| 6 | Omara | 75 |
| 7 | Tamara | 40 |
| 8 | César | 40 |
| 9 | Tamara | 70 |
| 10 | Pablo | 60 |
| 11 | Tamara | 60 |
| 12 | Pablo | 45 |
| 13 | Pablo | 45 |

<!-- PAGE -->

## 1. Fiado a un día: continuidad y equipo

**Tiempo:** 30 s · **Expositor propuesto:** Omara

Presentamos la comparación CV3 para el fiado a un día en Cervecería Baylón. APF1 identificó el registro en cuaderno y el criterio personal; APF2 propuso Credify para digitalizar clientes, fiados y abonos. Ahora evaluamos una ayuda predictiva académica, no un sistema autorizado para decidir créditos. Nuestro equipo está identificado en pantalla y el reparto de exposición es propuesto.

**Apoyo:** mostrar título, empresa, Grupo 2 y los cuatro nombres completos con sus códigos de la tabla inicial. Dibujar la continuidad APF1 → APF2 → APF3. Mantener visible «CV3 · registros ficticios · apoyo a revisión humana».

## 2. Problema ML e indicador financiero

**Tiempo:** 30 s · **Expositor propuesto:** Omara

La pregunta es si un fiado tendrá atraso respecto a su vencimiento contractual, usando información anterior al otorgamiento. Cada fila representa un fiado; uno significa atraso y cero, pago puntual. El cinco por ciento mencionado en antecedentes es una estimación financiera de pérdida mensual sobre ventas, sin corroboración contable específica. No es prevalencia de atraso ni se utilizó para etiquetar.

**Apoyo:** mostrar «Clasificación binaria supervisada · target: late_payment» y, separado, «5 % referencial = pérdida mensual estimada / ventas del mes × 100». No convertir ese indicador en probabilidad, objetivo de accuracy o beneficio conseguido.

## 3. Dataset: origen, exclusiones y trazabilidad

**Tiempo:** 75 s · **Expositor propuesto:** Omara

Todos los registros son ficticios, no clientes reales anonimizados. Al cierre documentado de APF2 no había empezado el piloto real; el exportador no produjo fiados elegibles. Eso no demuestra que el negocio careciera de operaciones. La simulación es un cambio de fuente declarado, no el cumplimiento de la captura prevista.

Desarrollo reúne mil doscientas ochenta y nueve filas etiquetadas de ciento veinticinco clientes: novecientas cuarenta y tres del entrenamiento original y trescientas cuarenta y seis de validación. Se excluyeron trescientas nueve filas del test antiguo y veinticuatro sin desenlace.

La cohorte final CV3 contiene mil noventa y un fiados de ciento veinte clientes distintos. Solo mil setenta y tres tienen etiqueta: seiscientos noventa y cinco puntuales y trescientos setenta y ocho atrasados. Los dieciocho desconocidos permanecen fuera de las métricas. Hay hashes y semilla predeclarada para rastrear el experimento, pero ambas cohortes proceden del mismo generador: no son validación externa.

**Apoyo:** presentar dos bloques sin sumar cohortes: «Desarrollo: 1289 / 125 clientes» y «Final: 1091 / 120 clientes; 1073 evaluables + 18 desconocidos». Al pie: «Exclusiones fuente: 309 + 24 = 333». Referenciar procedencia y conteos del reporte congelado.

<!-- PAGE -->

## 4. EDA: balance y relaciones de desarrollo

**Tiempo:** 75 s · **Expositor propuesto:** César

El análisis exploratorio se limita al conjunto de desarrollo, que funciona como base de entrenamiento y selección. No utiliza el test antiguo ni la cohorte final. Tampoco afirmamos que este EDA documental se hubiera realizado antes de la corrida congelada.

En desarrollo hay ochocientos setenta y siete casos puntuales y cuatrocientos doce atrasados: aproximadamente sesenta y ocho y treinta y dos por ciento. Predecir siempre puntual consigue una accuracy aparentemente aceptable sin detectar ningún atraso. Por eso necesitamos recall y referencias simples.

Los gráficos describen historial de pagos y exposición previa. El atraso es 27,10 por ciento cuando hay pagos completos sin atraso y 36,44 con pagos tardíos previos. Por utilización, pasa de 28,56 por ciento en la banda baja a 45,65 en la alta. Cada banda muestra su denominador. Deuda y utilización están vinculadas por el cupo simulado: asociación no significa causalidad. Carecer de historial no demuestra incumplimiento. La calibración comercial sigue pendiente.

**Apoyo:** mostrar las figuras de desarrollo con universo y denominadores. El PPT usa un gráfico preparado desde las mismas 1289 filas, no una nueva selección. Las figuras y conclusiones del informe generado ya tienen valores; cotejarlos antes de exponer. Si falta una figura durante la sustentación, declarar el fallo y usar los conteos guardados, sin inventar una imagen o tendencia.

## 5. Modelos y validación agrupada

**Tiempo:** 75 s · **Expositor propuesto:** César

Comparamos árbol de decisión y SVM lineal con dos Dummies: clase mayoritaria y siempre positivo. Ambos modelos reciben las mismas once variables previas y un Pipeline con imputación por mediana y escalado. Las transformaciones se ajustan dentro de cada entrenamiento, nunca sobre todo el conjunto antes de separar pliegues.

La selección empleó cinco pliegues agrupados por cliente. Así, el cliente de una fila validada no aparece en el entrenamiento de ese pliegue. La SVM usa además calibración sigmoide con tres pliegues internos también agrupados; su Pipeline queda dentro del estimador calibrado.

Se exploraron dieciocho configuraciones y siete umbrales, ciento veintiséis combinaciones, no ciento veintiséis algoritmos. La calibración interna no equivale a evaluación anidada independiente de hiperparámetros: las predicciones fuera de pliegue también se usaron para escoger. Su resultado ganador puede ser optimista. IDs, escenarios, etiquetas y datos posteriores al otorgamiento no entran como predictores.

**Apoyo:** mostrar diagrama «5 pliegues agrupados → OOF de selección → congelamiento → final común». Dentro de SVM: «3 pliegues agrupados para calibrar». Rotular expresamente «Calibración anidada ≠ evaluación anidada de hiperparámetros».

## 6. Criterio congelado: F2 con piso de precisión

**Tiempo:** 75 s · **Expositor propuesto:** Omara

El criterio preestablecido fue maximizar F2 entre candidatos con precisión de atraso de al menos cero coma cincuenta. F2 pondera más la cobertura de atrasos; el piso busca provisionalmente tantas alertas correctas como falsas. Es una hipótesis técnica, no una meta comercial ni un compromiso acordado con los propietarios.

Ganó el árbol balanceado, profundidad tres, hoja mínima dieciséis y umbral cero coma setenta. Fuera de pliegue obtuvo precisión cero coma quinientos ocho y F2 cero coma doscientos cincuenta y seis. La SVM seleccionada fue lineal, con C de cero coma uno y umbral cero coma cincuenta.

Después de guardar esa decisión se evaluaron los cuatro modelos congelados sobre la misma cohorte final. No se cambió umbral ni semilla para mejorar sus resultados. El Dummy siempre positivo tenía mayor F2, pero incumplía el piso de precisión. Eso limita la elección; no lo convierte en una referencia derrotada.

**Apoyo:** mostrar `F2 = 5TP / (5TP + 4FN + FP)` y «P ≥ 0,50, supuesto técnico». Destacar «Árbol: depth=3; leaf=16; balanced; τ=0,70». Añadir OOF exacto: P=0,50811, recall=0,22816, F2=0,25641; no confundirlo con final.

<!-- PAGE -->

## 7. Resultados sobre el mismo final

**Tiempo:** 40 s · **Expositor propuesto:** Tamara

Esta tabla utiliza las mismas mil setenta y tres etiquetas finales para todos. El árbol alcanza precisión de cincuenta y seis coma veinticinco por ciento, pero recall de solo once coma noventa y F2 de cero coma ciento cuarenta y uno. SVM y mayoritario no emiten alertas. Siempre positivo obtiene F2 mucho mayor, alertando todo. La diferencia de accuracy frente al mayoritario es pequeña y no tiene significancia estadística demostrada. No presentamos superioridad general ni buen desempeño comercial.

**Apoyo:** mostrar la tabla final transcrita, sin mezclar OOF ni métricas del taller de Doña Rosa.

## 8. Errores y un caso ya guardado

**Tiempo:** 40 s · **Expositor propuesto:** César

La matriz del árbol registra seiscientos sesenta verdaderos negativos, treinta y cinco falsas alertas, trescientos treinta y tres atrasos omitidos y cuarenta y cinco detectados. El problema principal es la omisión. Un ejemplo guardado es el préstamo ficticio CV3-L00015: tenía historial previo favorable, obtuvo puntaje cero coma treinta y tres y fue clasificado sin alerta, pero terminó atrasado. Es un falso negativo del caché, no una nueva ejecución ni evidencia de una causa comprobada. No lo usamos para reajustar.

**Apoyo:** mostrar matriz `[[660,35],[333,45]]`, filas reales y columnas predichas, orden 0/1. En tarjeta separada: `CV3-C0002 / CV3-L00015`, p=0,33009138676021355, τ=0,70, real=1, predicho=0. Fuente: `models.tree.error_cases`; no ejecutar ese caso final.

## 9. Inferencia local ilustrativa, no validación

**Tiempo:** 70 s · **Expositor propuesto:** Tamara

Ahora intentaremos una inferencia local con un ejemplo ilustrativo sin etiqueta conocida. El resultado previamente verificado es cero coma cuatrocientos cincuenta y seis, bajo el umbral cero coma siete: predicción cero. No prueba acierto, no modifica la matriz final y no autoriza el fiado.

**Apoyo:** dedicar 20 segundos al párrafo anterior y reservar 50 segundos completos para operar y mostrar pantalla. Desde la raíz del paquete, con entorno compatible y sin iniciar servicios, usar exclusivamente este comando de inferencia:

<!-- PAGE -->

## 10. Interpretación de negocio sin beneficio probado

**Tiempo:** 60 s · **Expositor propuesto:** Pablo

Traducido a una eventual revisión, el árbol habría señalado ochenta operaciones: cuarenta y cinco atrasadas y treinta y cinco puntuales. De los trescientos setenta y ocho atrasos, omitió trescientos treinta y tres. No está listo para confiarle decisiones de crédito.

Una alerta podría generar revisión innecesaria; una omisión podría dejar un atraso sin revisar. Son consecuencias hipotéticas, no costos medidos. Además, un atraso recuperado no equivale a pérdida definitiva. No hemos demostrado ahorro, rentabilidad ni reducción del cinco por ciento financiero referencial.

Antes de evaluar impacto necesitamos finalidad, capacidad de revisión, costos y una meta observable justificada. Puede ser propuesta del equipo; si se atribuye un acuerdo al propietario, debe confirmarse realmente. Una predicción cero no garantiza cobro y una predicción uno no justifica rechazar automáticamente.

**Apoyo:** mostrar «45 detectados / 378 atrasos» junto a «333 omitidos». Separar visualmente «métrica predictiva» de «pérdida mensual estimada / ventas». No incluir porcentajes de ahorro, retorno o aprobación comercial sin evidencia.

## 11. Integración mínima y frontera con el MVP

**Tiempo:** 60 s · **Expositor propuesto:** Tamara

La integración disponible de CV3 es local: una función y una CLI cargan el Pipeline guardado, verifican integridad y validan un JSON de once campos en el orden congelado. Devuelven puntaje, umbral y predicción, sin crear créditos ni entrenar durante la consulta.

Es un contrato que podría conectarse al MVP, no una conexión web ya terminada. El laboratorio web heredado sigue en v2; sus capturas no prueban que CV3 esté desplegado o aceptado. Tampoco consta autorización del negocio para usarlo operativamente.

Faltan autenticación y pruebas de integración propias, advertencias y revisión humana. No prometemos latencia ni disponibilidad medidas. Los hashes comprueban integridad; no hacen seguro cargar un archivo Joblib de origen desconocido. Debe conservarse la separación académica y operativa.

**Apoyo:** diagrama «JSON de 11 campos → Pipeline local CV3 → JSON de salida», con flecha discontinua hacia «MVP: integración futura». En contraste: «WEB actual: v2, no CV3». No abrir la web como prueba de inferencia CV3 ni atribuirle autorización comercial.

## 12. Normativa y controles pendientes

**Tiempo:** 45 s · **Expositor propuesto:** Pablo

El marco es la Ley veintinueve mil setecientos treinta y tres y su Reglamento, Decreto Supremo cero dieciséis de dos mil veinticuatro, JUS. Minimizar a once predictores y excluir nombres o DNI reduce exposición, pero no certifica cumplimiento. La semilla reproduce personas inventadas; no anonimiza clientes reales. Antes de captar información real faltan finalidad y base jurídica, aviso y consentimiento cuando corresponda, accesos, conservación, ARCO y revisión de proveedores. La revisión humana sigue pendiente y no se sustituye con una firma ficticia ni con controles automáticos.

**Apoyo:** mostrar «Ley N.° 29733 · D.S. N.° 016-2024-JUS» y dos columnas: «Control acotado: datos ficticios, minimización, inferencia local, hashes» / «Pendiente real: tratamiento, seguridad operativa, derechos y revisión». No afirmar dictamen jurídico, consentimiento o aceptación completados.

## 13. Riesgos, pendientes y conclusión defendible

**Tiempo:** 45 s · **Expositor propuesto:** Pablo

El avance es una comparación metodológicamente corregida y trazable; la utilidad comercial no está demostrada. Persisten simulación no representativa, baja detección, sesgo de selección y riesgo de confundir versiones. Repetir el protocolo fijo comprueba reproducibilidad, no aporta otra validación independiente. Faltan fuentes cuantitativas para calibrar el simulador, una meta justificada, controles de datos y revisión individual. Esta presentación requiere ensayo. Cualquier selección posterior necesita otra prueba no consultada. No cerramos esos pendientes por redactar un guion ni atribuimos aprobaciones inexistentes.

**Apoyo:** cerrar con «Método corregido ≠ utilidad demostrada». Mostrar pendientes con estado «PENDIENTE», sin firmas ni responsables efectivos inventados. Los roles de la portada son propuestas de exposición. No activar reentrenamiento ni prometer promoción automática del modelo.

<!-- PAGE -->

# Preguntas difíciles · 1/2

**¿Por qué eligieron un árbol que funciona tan mal?** Ganó únicamente dentro del criterio técnico congelado, no por ser adecuado para producción. Su recall final de 11,90 % evidencia mala cobertura; se conserva el resultado desfavorable y no se recomienda automatizar decisiones.

**¿Por qué no elegir siempre positivo si tiene F2 mayor?** Su F2 final es 0,73114 frente a 0,14133 del árbol, pero su precisión es 0,35228 y no cumple el piso provisional de 0,50. Ese piso es una hipótesis de investigación, no evidencia de utilidad comercial. No afirmamos superar ambas referencias.

**¿Cómo calculan recall y por qué importa?** Es `TP/(TP+FN) = 45/378 = 0,11905`. Mide la fracción de atrasos detectados: quedaron 333 sin alertar. Una accuracy de 0,65704 no compensa esa omisión.

**¿La CV es anidada y el OOF es una estimación imparcial?** Hay cinco pliegues de selección y tres internos de calibración SVM. La búsqueda de configuración y umbral reutiliza OOF: no es evaluación anidada independiente de hiperparámetros y el OOF ganador puede ser optimista.

**¿Cómo evitan fuga de información?** El diseño separa clientes por pliegue, ajusta imputación y escala dentro del entrenamiento y excluye desenlaces, escenarios e IDs del predictor. La calibración SVM también agrupa clientes. Son controles documentados, no prueba de ausencia de todo sesgo; el generador compartido sigue limitando la evaluación.

**¿La simulación está calibrada porque sus gráficos parecen plausibles?** No. Los controles lógicos y las relaciones visuales no validan frecuencias, montos o probabilidades del negocio. Sigue pendiente una fuente cuantitativa verificable por parámetro, con fecha, unidad y alcance.

<!-- PAGE -->

# Preguntas difíciles · 2/2

**¿El 5 % fue la tasa de etiquetas o una mejora conseguida?** Ninguna de las dos. Es pérdida mensual estimada dividida entre ventas, una referencia sin corroboración contable específica. No generó etiquetas ni se ha demostrado su reducción.

**¿0,4559958404 es la probabilidad verdadera y significa que pagará?** Es la salida del modelo para una entrada ficticia, no riesgo real garantizado. Queda bajo 0,70 y produce cero, pero `known_label=null`: no sabemos si acertó. La calibración sigmoide de SVM tampoco garantiza calibración real, y este ejemplo pertenece al árbol.

**¿De dónde salen los conteos y por qué no evalúan 1091 filas?** El reporte congelado registra 1289 filas de desarrollo en 125 clientes y 1091 finales en otros 120. En final hay 1073 etiquetas resueltas y 18 desconocidas, que no se imputan. La fuente original excluye 309 del test antiguo y 24 sin desenlace: 333, distintos de los 333 falsos negativos finales.

**¿La web o producción ya ejecutan CV3?** No consta despliegue CV3. El laboratorio web heredado sigue en v2 y no demuestra autorización de negocio ni aceptación humana. CV3 dispone de inferencia local independiente; integrar al MVP y verificar controles sigue pendiente.

**¿Reproducir otra vez las mismas métricas es una nueva validación?** No. La reproducción documentada repite el mismo protocolo, semilla y prueba fija para comprobar consistencia técnica. No añade clientes independientes ni validación externa; CV3 ya está consultado y no debe usarse para seleccionar de nuevo.

**¿Qué harán si falla la demo y quién aprobó el material?** Se declara el fallo y se muestra únicamente la última predicción verificable como resultado guardado, o una grabación auténtica identificada como tal, nunca como ejecución en vivo. No consta aprobación individual ni comercial de este guion: los cuatro integrantes deben revisarlo y registrar únicamente lo que realmente comprueben.

<!-- PAGE -->

# Demo y revisión humana

**En vivo:** 20 segundos hablados + 50 de operación. Mostrar entrada, ejecutar solo inferencia y explicar salida sin garantía de cobro.

```bash
python codigo/scripts/academic_credit_grouped_cv.py --predict-artifact-dir experimento --input-json experimento/illustrative_input.json --output-json demo_inferencia_nueva.json
```

**Contingencia:** declarar el fallo y mostrar experimento/illustrative_prediction.json como resultado guardado, no como ejecución en vivo. Usar una salida nueva; no borrar evidencia.



**Estado inicial:** ninguna casilla acredita revisión realizada. Cada integrante debe registrar su revisión real con alcance, hallazgo o corrección y fecha en el registro correspondiente; no se incluyen firmas ni conformidades simuladas.

- [ ] Confirmar los cuatro nombres y códigos, y aceptar o corregir el reparto propuesto sin atribuir trabajos previos.
- [ ] Contrastar los conteos, exclusiones y las cuatro filas de métricas con el reporte CV3 congelado.
- [ ] Verificar matriz, orientación de ejes y procedencia del caso de error guardado; no volver a predecir el test.
- [ ] Revisar las figuras de desarrollo y sus denominadores contra los valores materializados en el informe y el PPT.
- [ ] Mantener visibles el origen ficticio, calibración comercial pendiente, bajo recall y F2 superior del Dummy positivo.
- [ ] Comprobar en un ensayo auténtico entorno, entrada y artefactos confiables para inferencia, sin entrenamiento ni reajustes; usar salida nueva y conservar respaldo.
- [ ] Preparar respaldo verificable rotulado como guardado o grabado y declarar cualquier fallo; no fabricar ejecución ni capturas.
- [ ] Confirmar que la presentación no confunde CLI CV3 con web v2 ni afirma autorización, consentimiento o beneficio financiero.
- [ ] Revisar referencias normativas y pendientes de tratamiento, sin equiparar minimización o hashes con cumplimiento integral.
- [ ] Revisar contenido asistido por IA contra las fuentes; no sustituir revisión personal por verificaciones automáticas.
- [ ] Ensayar los 13 relevos dentro de 720 segundos, respetando 20 segundos hablados y 50 de operación en la diapositiva 9.
- [ ] Registrar revisión individual auténtica de Omara, César, Tamara y Pablo; dejar explícitamente pendiente lo que no se haya comprobado.
