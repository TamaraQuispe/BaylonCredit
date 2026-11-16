# Resultados de la revision parcial V5

**Revision parcial completada con correcciones; no aprobacion global.**

Fecha declarada en los dos parrafos de fecha del Word: 15/11/2026. Importacion ejecutada con `deploy/review-rildo/import_completed_review.py`. Es revision intencional de ejemplos sinteticos, no acta firmada, consentimiento de clientes, validacion predictiva ni autorizacion de produccion.

## Respuestas importadas

| Grupo | Total | Habitual | Posible | no | posible |
| --- | --- | --- | --- | --- | --- |
| Fiados, tablas 1 y 2, seis por tabla | 12 | 3 | 9 | 0 | 0 |
| Rechazos, tabla 3 | 4 | 4 | 0 | 0 | 0 |
| Semanas, tabla 4 | 4 | 2 | 2 | 0 | 0 |
| Supuestos y correcciones, tabla 5 | 3 | 0 | 0 | 1 | 2 |
| Total | 23 | 9 | 11 | 1 | 2 |

Las 23 respuestas coinciden exactamente, por ID o historia/semana, con `docs/APF3_OWNER_REVIEW_V5.json` actual. Se conserva el texto raw, incluidas las minusculas; `classification_canonical` es un campo separado (9 habitual, 13 posible, 1 no). Las tres correcciones de la tabla 5 se conservan literalmente, sin sustituirlas por las glosas inglesas del JSON.

## Correcciones Clave

- Todo saldo pendiente impide otro fiado, incluso si aun no vence. Abonar o acordar no habilita: de S/30, pagar S/20 deja S/10 pendientes.
- Cancelar completamente permite evaluar otra solicitud, no aprobarla automaticamente. La liquidacion debe observarse estrictamente antes de la evaluacion.
- Los casos 9 y 10 siguen desconocidos al corte simulado 30/09/2026; vencian 01/10/2026. La frase del propietario sobre el momento de revision se interpreta respecto al corte del ejemplo, no como afirmacion de que el vencimiento seguia futuro el 15/11/2026.
- Pagar despues del vencimiento es atraso. Tres dias de gracia no convierten el pago en puntual.
- Soles completos o terminados en .50 son ejemplos normales; precios exactos de productos pueden mantenerse. No se midieron sus frecuencias.
- Los pagos varian, normalmente 08:00-12:00 o 16:00-20:00. No se confirmo una hora fija real de pago o vencimiento.
- Doce clientes se acepta como grupo de ejemplo, no poblacion real estatica. Los clientes pueden variar semanalmente. Unos 12 fiados a 9 clientes es habitual, no constante; 8/7 es posible y menos habitual que 11 o 12 fiados.

## Trazabilidad

Salida nueva: `/Users/tamaraalison/Downloads/APF3_Revision_Rildo_V5_Procesada`.

- `responses.json`: 23 clasificaciones, correcciones, coordenadas y tres respuestas adicionales verbatim de la fuente JSON. Estas adicionales se identifican como fuente JSON, no como contenido del Word.
- `rawentries.csv`: texto exacto de respuestas y correcciones del Word, con coordenadas de tabla/celda o parrafo.
- `corrections.md`: parrafos reales P18, P19, P24, P25, P26, P33-P37 y P46-P55; ordinales desde 1 y tambien indices Python desde 0. Se conserva el prompt de origen, sin copiar contactos ni el Word completo.
- `resumen.md`, `resumen.docx`, `resumen.pdf`: resumen de negocio; PDF de 2 paginas, tipografia de 11 puntos, sin desbordamientos, render local con red bloqueada. DOCX reabierto correctamente.
- `audit.json`: hashes antes/despues, cotejos, conteos XML, controles de maquetacion y hashes de archivos congelados.
- `manifest.json`: hashes de los nuevos productos, excluyendo el propio manifiesto.

SHA-256 del Word completado antes y despues: `82d4c748b3403e8a3e45b4361b95e9da4ffaf0b0ca21e3a9ac4baedc6040f29b`.

SHA-256 del Word en blanco registrado en el manifiesto original: `f4d6eb34a69ecd4bcc5b3aacb243b7d840b8358a16f2a8b80b11defb378a95c3`. La diferencia es intencional por haber completado el formulario; se registra como excepcion esperada, no como corrupcion. No se edito el manifiesto en blanco.

El paquete original tiene **12 archivos totales**, no 12 archivos adicionales al DOCX: 11 salidas declaradas (DOCX y otras 10) mas el manifiesto. Las otras 10 salidas coinciden con sus hashes originales; el manifiesto tambien mantiene su hash antes/despues. No se inventan archivos para satisfacer un conteo distinto. El MD, HTML y PDF originales siguen en blanco y son historicos, no la revision completada actual.

Todas las celdas no destinadas a respuesta de las cinco tablas coinciden con el MD original generado; se cotejaron ademas los IDs, montos/fechas de fiados y conteos semanales de los CSV. Las 11 correcciones verbatim del JSON se localizaron en el Word. La inspeccion de todas las partes ZIP/XML arrojo cero comentarios, referencias de comentarios, inserciones, eliminaciones, movimientos, cambios de propiedades, activacion de control de cambios, relaciones externas, objetos incrustados y altChunk. Ausencia de marcas XML no equivale a firma ni prueba de autoria.

Los hashes antes/despues de las fuentes JSON, modulos sinteticos protegidos y archivos de los directorios V4/V5/V6 comprobados son iguales. No se duplico el Word original ni informacion personal/contactos.

## Limites y Verificacion

No se validaron globalmente las 540 filas V5 ni las 545 filas V6. El propietario no reviso las nuevas filas V6. Los modelos publicos y la aplicacion local siguen siendo V4 anterior; sus metricas no se trasladan a V6.

Pruebas ejecutadas: `python3 -m unittest discover -s deploy/review-rildo -p 'test_*.py' -v`: **6 pruebas correctas**, con fixtures XML sinteticas sin PII. Cubren blancos/invalidos, capitalizacion, conteos, IDs, alteracion de celdas, correccion faltante, tablas, saltos de linea y marcas ocultas. Ruff por Docker sobre los dos archivos propios, `--select E4,E7,E9,F,I,UP,B`: **sin incidencias**.

No se genero otro dataset, generador, modelo, prediccion o ZIP; no hubo despliegue ni commit. Ningun modelo adicional debe comenzar antes de revisar DEV y predeclarar por separado la seleccion y evaluacion.
