# APF3: Aclaracion De Liquidacion Total Y Estado V5

## Regla De Negocio Confirmada

La usuaria transmitio posteriormente estas respuestas de Rildo:

> que pague en el momento y hasta que pague no se vuelve a fiar, eso ha dicho

> los 30 completos dice

El caso consultado era un fiado de S/ 40, un abono anterior de S/ 10 y S/ 30 todavia vencidos. La aclaracion exige pagar los **S/ 30 completos**, no otro abono parcial. No se otorga un nuevo fiado mientras quede saldo vencido. Un acuerdo de fecha o un pago futuro no elimina ese bloqueo. Liquidar la deuda permite volver a evaluar, no obliga a aprobar.

La aclaracion se limita a la deuda vencida del caso; no se inventa una prohibicion sobre toda deuda aun no vencida. Se registra como respuesta del propietario transmitida por la usuaria, sin fecha de entrevista inventada, consentimiento de clientes ni aprobacion de modelos.

Fuente nueva: `docs/APF3_OWNER_SETTLEMENT_CLARIFICATION.json`, SHA-256 `63e0e57052fa31a93de3710a8bba69fadef95f0cb97e9de452fe7d281082ad7f`. Se conserva la ficha original como antecedente; la nueva aclaracion prevalece sobre su alternativa anterior de abono/acuerdo para permitir otro fiado vencido.

## Cambio Tecnico

`backend/app/ml/owner_settled_synthetic.py` implementa una version de datos independiente. No se modificaron el generador V4 ni sus modelos, resultados y paquetes congelados. El nuevo generador y su validador rechazan concesiones con saldo vencido, incluso despues de abonos; solo cuentan liquidaciones ya observadas antes de evaluar. No se anticipan pagos ni se fuerzan aprobaciones para ajustar volumen.

Hay 66 pruebas nuevas de la regla y del contrato: S/ 40 menos S/ 10 deja bloqueo; abonar S/ 20 adicionales deja S/ 10 y mantiene bloqueo; liquidar los S/ 30 elimina ese bloqueo; otra deuda vencida, pagos futuros y acuerdos no permiten eludirlo. El tiempo de pago debe preceder a la reevaluacion; un timestamp simultaneo no acredita orden de eventos.

## Datos De Desarrollo Preparados

El protocolo `docs/APF3_SETTLED_V5_DATA_PROTOCOL.json` se guardo antes de generar las dos historias de desarrollo, con semillas fijas. No define modelos, seleccion ni semilla FINAL.

Salida local: `/Users/tamaraalison/Downloads/APF3_Grupo2_Liquidacion_V5/`.

| Historia ficticia | Fiados de estudio | Conocidos | Puntuales / atrasados | Desconocidos | Fiados por semana completa | Clientes con fiado por semana |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| SET5-D1 | 274 | 270 | 222 / 48 | 4 | 11.2083 | 8.8750 |
| SET5-D2 | 266 | 260 | 212 / 48 | 6 | 10.7500 | 8.6250 |

Total para aprendizaje futuro: **540 fiados sinteticos de estudio**, **530 conocidos**, **434 puntuales**, **96 atrasados** y **10 desconocidos**. Las historias no se suman como volumen real de la empresa. **Cero concesiones con deuda vencida pendiente** en estas historias. Los desconocidos se conservan en el CSV completo y se excluyen del CSV supervisado.

La agenda heredada mantiene 12 solicitudes por semana; la fuente de Rildo describe aproximadamente 12 fiados otorgados. El reporte muestra ambas magnitudes por separado y no convierte la tolerancia elegida por el equipo en una confirmacion del propietario. Las medias otorgadas son las observadas en esta preparacion, no resultados forzados. Poblacion, distribuciones y demas supuestos siguen explicitamente pendientes de la revision global de coherencia.

## Confirmacion Posterior De Variacion Semanal

La usuaria respondio `a la primera pregunta dice que si` al transmitir la consulta de si tambien hay semanas de 10 u 11 fiados a ocho o nueve clientes porque algunos mantienen deuda pendiente. Se registra la pregunta completa y la respuesta literal en `docs/APF3_OWNER_SCALE_CLARIFICATION.json`.

Esto respalda que 12 fiados/9 clientes es una referencia aproximada habitual, no una exigencia de obtener exactamente esas cifras cada semana. Los promedios V5 de 11.2083/8.8750 y 10.7500/8.6250 son compatibles descriptivamente con esa variacion. No se generaron nuevamente las historias, no se quitaron semanas y no se ajustaron pagos o aprobaciones para obtenerlos.

La respuesta no fija minimos ni maximos absolutos y no confirma todas las semanas sinteticas: D1 contiene una semana de nueve fiados; D2 contiene una de ocho y tres de nueve, ademas de dos semanas con siete receptores. Esas frecuencias se conservan en `/Users/tamaraalison/Downloads/APF3_Revision_Escala_V5/confirmacion-escala.json`, junto con el contraste de los hashes originales. No se atribuyen esos valores adicionales a Rildo ni se declaran invalidos solo por no haber sido mencionados en la pregunta.

La corroboracion cualitativa llego despues de preparar DEV y no se presenta como umbral numerico prospectivo. Se cierra la duda de si todas las semanas debian tener 12/9 exactos, no la validacion completa del simulador, ni la aprobacion de modelos, costos o despliegue.

## Estado De Presentacion

**V4 no debe presentarse como si ya aplicara esta aclaracion posterior.** El ZIP `APF3_Grupo2_Entrega_V4.zip` permanece como antecedente tecnico, pero no incorpora esta regla ni sus datos revisados.

V5 esta en etapa **solo datos de desarrollo**: la regla de liquidacion pasa, pero `coherence_accepted=false` evita promover automaticamente la revision a experimento final. No se entrenaron modelos V5, no se genero un conjunto FINAL y no existen metricas V5 para sustituir las anteriores.

La variacion de escala cuenta ahora con la confirmacion cualitativa posterior indicada arriba. El siguiente cierre es revisar los supuestos restantes y el alcance de la aceptacion academica; despues, fijar un protocolo de modelado nuevo antes de entrenar, reservar una cohorte no consultada y actualizar informe, diapositivas, demo y paquete. No trasladar metricas, seleccion o capturas V4 como resultados V5. Produccion no cambio.
