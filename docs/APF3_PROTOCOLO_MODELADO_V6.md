# V6: Revision DEV Y Protocolo De Modelado

## Estado De Este Paso

Se completo una auditoria de los DEV existentes y se congelo una especificacion prospectiva de modelado. No se entrenaron modelos V6, no se calculo desempeno predictivo y no se genero FINAL. La preparacion no modifica los protocolos ni datos anteriores y no autoriza produccion.

Protocolo: `docs/APF3_PENDING_V6_MODEL_PROTOCOL.json`.

SHA-256: `eb7fcd39f69be0115895cbb43b6d84e4488535646108bd6f21381d0fb1607923`.

Snapshot local: `/Users/tamaraalison/Downloads/APF3_Protocolo_Modelado_V6/`.

## Revision DEV

| Comprobacion | Resultado |
| --- | --- |
| Fiados sinteticos de estudio | 545 |
| Con etiqueta / desconocidos | 541 / 4 |
| Puntuales / atrasados conocidos | 454 / 87 |
| Clientes ficticios DEV | 24, en dos historias alternativas |
| Concesiones con saldo previo pendiente | 0 |
| CSV y transacciones | Coinciden, sin modificar fuentes |
| Pliegues externos | Tres; clientes disjuntos y ambas clases en cada particion |
| Calibracion interna propuesta | Tres pliegues viables dentro de cada entrenamiento externo y DEV completo |
| Ajustes / predicciones / generacion en la auditoria | Cero |

Los conjuntos de validacion externos tienen 182, 179 y 180 etiquetas conocidas, con 29, 30 y 28 atrasos respectivamente. No son 541 personas independientes: hay varias operaciones de cada cliente.

Los cuatro casos sin etiqueta pertenecen a clientes presentes en DEV; se asignaron al mismo pliegue retenido de su cliente. No se etiquetan como puntuales, no entrenan y no calibran. Sus futuras alertas se contaran para capacidad, sin incluirlos en las metricas supervisadas.

**Hallazgo esperado por la regla del negocio:** `pending_overdue`, `pending_current`, `outstanding`, `utilization` y `overdue_rate` son constantes cero en fiados otorgados. `completed_sales` coincide con `paid_credits` porque se simulan ventas vinculadas a credito y no volumen de contado. Se conserva el contrato de once entradas, pero estas columnas no acreditan senales independientes ni deben recibir ruido para aparentar utilidad.

La auditoria pasa la puerta tecnica de investigacion con limites declarados. No sustituye una auditoria del negocio, la revision humana del equipo ni validacion real. Rildo reviso una muestra intencional V5 y proporciono aclaraciones posteriores, no las 545 filas V6.

Auditoria: `/Users/tamaraalison/Downloads/APF3_Revision_DEV_V6_No_Modelos/summaryauditoria-dev-v6.json`.

## Decisiones Fijadas Antes De Entrenar

- Comparar arbol de decision y SVM lineal, mas Dummy mayoritario y Dummy siempre positivo.
- Mantener Pipeline con imputacion por mediana y StandardScaler ajustados solo dentro de cada entrenamiento.
- Usar exactamente el plan de pliegues guardado: externos con semilla 2026111801 e internos con 2026111802. No buscar una particion de mejores resultados.
- Explorar 12 configuraciones de arbol y seis de SVM; siete umbrales por configuracion, 126 combinaciones. Ningun ganador ni umbral se hereda de V4.
- Elegir mediante F2 OOF de acciones de revision limitadas; los desempates y baselines estan escritos en el JSON. F2 es una decision de investigacion, no un costo medido ni una meta empresarial aprobada.
- Umbral primero y luego hasta cinco alertas por replica y fecha civil de Lima, con score descendente e ID ficticio para empates. Esta cola solo representa fiados sinteticos otorgados.
- En OOF las colas se calculan dentro de cada pliegue retenido, sin mezclar scores de modelos distintos como si constituyeran una cola completa desplegada. Se declara que no captura competencia de capacidad entre pliegues.
- Reajustar y guardar todos los modelos y su seleccion antes de generar el futuro test `PND6-T`, semilla 2026111901. FINAL no existe en este cierre.
- Evaluar cada modelo congelado en un unico lote FINAL, guardar scores y reutilizarlos. Cualquier fallo o resultado inferior al Dummy se informa, no se corrige cambiando datos, semillas o ganador.
- La propuesta tecnica es superar ambas referencias en F2 de politica final y respetar capacidad. Su incumplimiento sera un resultado valido a reportar, no razon para volver a ajustar con FINAL.

## Limites Que Se Mantienen

El reparto 75/25 de montos redondeados/exactos, corte estricto a las 20:00, distribuciones latentes, calentamiento, poblacion de ejemplo y estacionariedad son supuestos del equipo. La revision muestral de Rildo no los convierte en frecuencias medidas ni en aprobacion global.

No se elimina la advertencia de optimismo: OOF se reutiliza para elegir configuracion y umbral; la calibracion interna no es una evaluacion anidada independiente de la busqueda. Tampoco se valida el desempeno real, el ahorro, los rechazados sin contrafactual ni la perdida permanente.

## Siguiente Ejecucion Separada

Falta implementar y probar el runner V6 contra esta especificacion; despues se podra ejecutar el experimento con salidas nuevas. Este snapshot no incluye OOF, ganador, modelos exportados ni metricas finales. Los flags historicos `models_authorized=false` del protocolo de datos y del cierre actual significan que en este paso solo se auditaron y congelaron decisiones; no deben reescribirse como si ya se hubieran ejecutado modelos.

No presentar informe, capturas o metricas V4 como resultados V6. Los documentos de entrega se actualizaran solo con los resultados reales de la futura ejecucion.
