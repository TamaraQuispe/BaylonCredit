# APF3 Grupo 2: Revision Y Presentacion V4

**Estado:** preparacion tecnica comprobada; revision individual, ensayo y entrega en Aula Virtual pendientes. Este documento no es un acta de aprobacion ni atribuye contribuciones pasadas.

## Localizar La Entrega

La edicion actual es `APF3_Grupo2_Entrega_V4`. El paquete anterior `APF3_Grupo2_Alineado_V4` se conserva como evidencia congelada, no se sustituye ni se presenta como si incluyera la integracion posterior.

- Informe: `informe/APF3_TD_Grupo2_ML_Innovacion.pdf` y `.docx`.
- Presentacion: `sustentacion/APF3_TD_Grupo2_ML_Innovacion.pptx` y `.pdf`.
- Guion: `sustentacion/APF3_Grupo2_Guion_12min.pdf`.
- Codigo academico: `APF3_TD_Grupo2_ML_Innovacion.py`, `codigo/` y `requirements.txt`.
- Datos simulados: `datos/desarrollo.csv`, `datos/final.csv`; diccionario y calidad en `anexos/datos/`.
- Integracion real local: `anexos/integracion/`; fuentes completas del MVP en `laboratorio/codigo_fuente_MVP_V4.zip`.
- Instrucciones de demo: `laboratorio/README.md`. Las imagenes Docker, el interprete y los wheels no se incluyen; deben prepararse antes de clase.

## Controles Tecnicos Ya Comprobados

Estas marcas describen verificaciones automaticas, no revisiones realizadas por integrantes.

- [x] Informe con 15 paginas de cuerpo; portada, referencias y anexos fuera del limite. Render A4 y enlaces locales comprobados.
- [x] Trece diapositivas, 720 segundos planificados y 18 preguntas de apoyo; no equivalen a duracion ensayada.
- [x] Trazabilidad APF2, diccionario de 24 columnas y ficha de los siete criterios originales de la consigna.
- [x] Dos relaciones DEV documentadas sin entrenar ni consultar FINAL para ajustar el modelo. Se conserva la falta de tendencia por exposicion.
- [x] Modelo SVM seleccionado antes de FINAL; metricas congeladas, errores y resultados desfavorables conservados.
- [x] Reproduccion tecnica: 15 archivos iguales, 12 metricas brutas y 12 politicas exactas, cinco estados aprendidos iguales. Bytes Joblib distintos, con salvedad explicita.
- [x] Web V4 probada solo localmente con login y DB efimera; sin crear creditos ni evaluaciones comerciales. Demo publica y produccion sin actualizar.
- [x] Wrapper de entrega ejecutado sobre el ejemplo ilustrativo: score 0.11922453881690649, umbral 0.1, clase 1, sin etiqueta conocida ni aprobacion.
- [x] Medicion separada del servicio: 30 llamadas calientes, mediana 1.90 ms y p95 2.23 ms. No mide HTTP, navegador, concurrencia ni SLA.

## Revision Individual Autentica

Cada integrante debe contrastar fuentes, codigo, datos y conclusiones asistidos por IA, no solo leer su parte. Completar exclusivamente lo realmente revisado; no copiar fechas, firmas o conformidades de otra persona.

| Integrante | Codigo | Alcance revisado | Hallazgo/correccion y evidencia | Fecha real |
| --- | --- | --- | --- | --- |
| Omara Yamileth Baylon Vila | U23231338 | PENDIENTE | PENDIENTE | PENDIENTE |
| Tamara Alison Covenas Quispe | U23204737 | PENDIENTE | PENDIENTE | PENDIENTE |
| Cesar Augusto Daniel Paredes Paredes | U23259768 | PENDIENTE | PENDIENTE | PENDIENTE |
| Pablo Enrique Yman Avila | U23251279 | PENDIENTE | PENDIENTE | PENDIENTE |

- [ ] Confirmar nombres, codigos y continuidad del grupo respecto de APF1/APF2.
- [ ] Verificar denominadores: 8/45 atrasos evaluables; 10/48 anotaciones con abonos; tres desconocidos incluidos en 48.
- [ ] Explicar por que 559/552/7 y 260/259/1 son historias ficticias alternativas, no volumen real sumado.
- [ ] Explicar Pipeline, CV por cliente, calibracion interna y optimismo de seleccion OOF.
- [ ] Defender por que se conserva SVM aunque el arbol tenga mayor F2 final; no volver a elegir con FINAL.
- [ ] Diferenciar prediccion por umbral, cola top-5, probabilidad experimental y decision humana.
- [ ] Explicar 114 FP, cuatro FN y 79 revisiones menos a cambio de tres omisiones adicionales frente a revisar todo limitado. Los 158 minutos son hipoteticos.
- [ ] Explicar signos de los coeficientes sin causalidad: mas deuda no demuestra menor riesgo; sin historial no significa morosidad.
- [ ] Revisar el anexo IA y completar validacion humana aplicada. Recuperar prompts anteriores disponibles o mantener explicitamente declarada su ausencia; no inventar historial.

## Preparar La Maquina De Exposicion

- [ ] Elegir un responsable de ejecutar y un suplente, sin confundir la propuesta con una asignacion aceptada.
- [ ] Tener la entrega completa y las dependencias exactas antes de clase. No instalar ni entrenar durante los 12 minutos.
- [ ] Probar el comando de inferencia de `laboratorio/README.md` en la maquina que se usara, con un nombre de salida nuevo.
- [ ] Mostrar entrada, ejecutar el wrapper en modo inferencia y explicar score, umbral, clase y etiqueta desconocida.
- [ ] No ejecutar reproduccion, entrenamiento, busqueda de umbrales ni evaluacion de cohortes FINAL durante la demo.
- [ ] Preparar la salida y captura previas como respaldo rotulado. Si falla, declarar el fallo; no mostrar el respaldo como si acabara de ejecutarse.
- [ ] Abrir PPTX y PDF en la aplicacion/proyector que se usara y comprobar legibilidad. El render tecnico no certifica Microsoft Office nativo.

## Ensayo Real Del Equipo

- [ ] Exponer los cuatro dentro de 12 minutos +/-30 segundos, incluyendo 50 segundos de operacion en diapositiva 9.
- [ ] Practicar cinco minutos de preguntas; todos responden sobre cualquier fase.
- [ ] Registrar duracion observada, relevos, fallo de demo si ocurre y correcciones necesarias.

| Intento | Fecha real | Duracion observada | Resultado de demo | Correcciones / responsable |
| --- | --- | --- | --- | --- |
| 1 | PENDIENTE | PENDIENTE | PENDIENTE | PENDIENTE |
| 2, si procede | PENDIENTE | PENDIENTE | PENDIENTE | PENDIENTE |

## Entrega Y Acceso Docente

- [ ] Confirmar la fecha y hora de la sesion evaluativa de semana 15; subir antes de su inicio.
- [ ] Cargar informe, codigo, presentacion y anexos por Aula Virtual. GitHub es opcional si el codigo se entrega como archivo.
- [ ] Si se usa Drive, Colab o GitHub, comprobar acceso de lectura equivalente al del docente e incluir el enlace correcto en el informe. El GitHub anterior de CV3 no acredita acceso a V4.
- [ ] Comprobar que el ZIP subido se descarga completo y que su checksum coincide; guardar constancia real de entrega.
- [ ] No subir ficha privada del propietario, firmas, contactos, cuaderno, credenciales, bases de datos o backups.

No son condiciones para esta entrega academica activar V4 en produccion, publicar una API ni acreditar un piloto real inexistente. La base juridica, consentimiento cuando corresponda, ARCO, conservacion y costos comerciales pendientes deben resolverse antes de trabajar con clientes reales. No se afirma cumplimiento integral hasta cerrar los requisitos humanos y de entrega que correspondan.
