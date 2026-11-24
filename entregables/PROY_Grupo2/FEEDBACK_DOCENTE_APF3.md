# Acciones Del Feedback Docente Para PROY

Fuente: `Reporte_APF3_GB2_SARYON.pdf`, cinco paginas, facilitado por el equipo.
SHA-256: `3868059e689b5ece2fc1a912eac73f5da1df39d8f3d1f30ff6c49d68b9572606`.
Este archivo resume acciones; no modifica el feedback, el APF3 enviado ni sus hashes.
El detalle y una plantilla NO firmada estan en la guia Word actualizada.

| ID | Prioridad | Accion requerida | Evidencia para cerrar |
| --- | --- | --- | --- |
| F01 | Critica | Resolver revision humana y estados contradictorios | Cuatro revisiones reales, version/hash revisado, alcance, fecha real y firma/confirmacion aceptada por el docente; entrega privada, sin firmas inventadas |
| F02 | Alta | Fijar version oficial y formato legible | Comprobante del Aula, identificador/hash, una version PROY canonica; conteo de cuerpo y revision visual de tablas al exportar |
| F03 | Alta | Distinguir igualdad exacta y equivalencia numerica | Nueva politica de tolerancias por campo, deltas y tests; no maquillar el flag exacto ni permitir cambios de clase/hash |
| F04 | Alta | Ampliar clientes y reportar bootstrap agrupado | Nuevo protocolo, factibilidad por cliente/clase y folds, mas clientes justificados e intervalos por cliente sin tuning de FINAL |
| F05 | Alta | Cerrar integracion operativa | Endpoint autenticado real, artefacto cargado, snapshot del servidor, gates, UI, auditoria, pruebas E2E y rollback; no solo HTTP 200 o cache |
| F06 | Alta | Medir capacidad y costos con Rildo | Tiempos reales, carga total, costos FN/FP y tolerancias acordadas antes de elegir umbral/familia en la nueva revision |
| F07 | Alta | Asignar responsables concretos | Nombre real, aceptacion, fecha objetivo y prueba de cierre por tarea, no solo roles genericos |
| F08 | Media | Preparar defensa y preservar fortalezas | Replay y discrepancias explicados, seleccion OOF justificada, demo elegible en vivo y respaldo; no nueva validacion por repetir semillas |
| F09 | Aclaracion | Cotejar inconsistencias del reporte | Consultar al docente 17.9 del encabezado frente a 16.9 de la tabla; cotejar archivo/paginado y cifras sin modificar su evaluacion |

## Revision Humana

El grupo ha confirmado que reviso el proyecto. El docente observa que no se adjuntaron
cuatro revisiones individuales firmadas y que otros archivos conservan PENDIENTE.
La accion es aportar evidencia autentica y explicar fechas/versiones; no afirmar que
una declaracion en un script sustituye firmas o conformidad docente. Si la revision
se realiza ahora, registrar la fecha de ahora, no antedatarla. Los originales del
APF3 y sus estados historicos se conservan. Una aclaracion o fe de erratas requiere
el canal y la autorizacion que indique el profesor.

## Comparacion Numerica Propuesta Para La Nueva Revision

Proponer `abs_tol=1e-12, rel_tol=0` solo para Brier y probabilidad ilustrativa, con
justificacion y registro por campo. Esta tolerancia no se implementa por actualizar
la guia y no modifica salidas antiguas. Matrices, etiquetas, conteos, decisiones,
umbrales, familia/parametros y hashes siguen con comparacion exacta. Rechazar
NaN/inf y cambios de clase aunque una probabilidad quede cerca del umbral.

Mantener `exact_raw_and_policy_reports=false` cuando no hay igualdad exacta, y
anadir un estado separado de equivalencia numerica con deltas, tolerancias y
violaciones. Separar la igualdad de la decision de seleccion de la igualdad del
registro OOF completo, que contiene Brier. R2 no es una metrica de este clasificador.

## Validacion Y Negocio

Un roster mayor se fija con fuentes/objetivo antes de entrenar. No convierte los
datos sinteticos en observaciones reales. Para intervalos, remuestrear clientes
con todas sus observaciones, no filas independientes; declarar semilla, numero
de remuestreos, nivel, estimando y tratamiento de replicas sin ambas clases.
Con pocos clientes, declarar la inestabilidad. El bootstrap no selecciona con FINAL.

Hablar con el propietario de 100 alertas, 32 atrasos detectados, 68 falsas alertas
y nueve omisiones. Tres alertas/dia fue un maximo observado en simulacion, no la
capacidad real; cinco/dia y dos minutos siguen siendo hipotesis. Elegir umbral y
familia nuevos con evidencia de desarrollo y costos acordados antes del test.

## Instruccion Del Taller Que Sigue Vigente

La guia mantiene SVM, KNN, Arbol de decision y AdaBoost, con retos de vecinos y
rondas, mas ambos Dummy. Los cuatro modelos citados en el feedback son arbol,
SVM y dos Dummy: no confundirlos con los cuatro algoritmos del taller.

## Alcance

El docente informa haber reproducido el protocolo y recargado el modelo. Es
corroboracion de reproducibilidad tecnica, no validacion comercial con otra poblacion.
La guia distingue lo implementado de lo pendiente: no se ha desplegado un nuevo
endpoint, recalculado intervalos, obtenido firmas ni realizado un piloto por escribirla.
La nota definitiva y el cierre de observaciones corresponden al docente.
