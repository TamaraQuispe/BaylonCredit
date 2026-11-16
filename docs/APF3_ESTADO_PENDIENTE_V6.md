# Estado Pendiente V6

Estado: **revision local de datos DEV sinteticos, sin aprobacion global y sin produccion**. La importacion auditable de las 23 respuestas V5 se encuentra en `APF3_Revision_Rildo_V5_Resultados.md` y en `/Users/tamaraalison/Downloads/APF3_Revision_Rildo_V5_Procesada/audit.json`.

## Evidencia Existente

Fuente actual: `docs/APF3_OWNER_REVIEW_V5.json`, con 12 fiados, 4 rechazos, 4 semanas y 3 supuestos, mas correcciones y tres respuestas adicionales verbatim. La revision es parcial e intencional, no probabilistica ni aprobacion de toda una cohorte.

Protocolo de datos ya escrito: `docs/APF3_PENDING_V6_DATA_PROTOCOL.json`. Salida DEV ya generada: `/Users/tamaraalison/Downloads/APF3_Grupo2_Pendiente_V6`. La importacion no altera ese protocolo, fuentes, modulo ni datos congelados.

Segun `data_revision_report.json` existente:

| Dato | Conteo/estado |
| --- | --- |
| Filas de estudio | 545 |
| Resultados conocidos | 541 |
| Puntuales, clase 0 | 454 |
| Con atraso, clase 1 | 87 |
| Desconocidos | 4 |
| Otorgamientos con saldo pendiente | 0 |
| coherence_accepted | false |
| models_trained | false |
| final_generated | false |

Estos son resultados descriptivos del DEV generado, no validacion de Rildo de las nuevas 545 filas. Las marcas de escala heredadas permanecen visibles y no constituyen rechazo o aceptacion global por si mismas. El informe conserva `legacy_grant_scale_flag=true` en ambas replicas.

## Impacto de la Revision

- La regla relevante pasa de deuda vencida a **cualquier saldo pendiente**, incluido el aun no vencido. Abonos y acuerdos no restauran elegibilidad. Solo cancelacion observada estrictamente antes permite volver a evaluar; no hay aprobacion automatica.
- Montos enteros o .50 y precios exactos de productos son admisibles. La mezcla 75% redondeados / 25% exactos es **SUPUESTO DEL EQUIPO**, no frecuencia declarada por Rildo. Los conteos observados de enteros/.50 incluyen coincidencias del escenario de precios exactos.
- Horarios normalmente 08:00-12:00 y 16:00-20:00, variables. El corte contractual duro a las **20:00 es SUPUESTO DEL EQUIPO**, no hora fija real confirmada. La hora exacta real de vencimiento queda sin confirmar; no se cambia retroactivamente el protocolo congelado.
- Pagar despues del vencimiento es atraso, independientemente de los tres dias de gracia. Los casos V5 9 y 10 siguen desconocidos respecto al corte 30/09/2026, no respecto a noviembre.
- Doce clientes es un grupo de ejemplo aceptable, no una poblacion real fija. La rotacion semanal concreta y distribuciones sinteticas son supuestos. Unos 12 fiados a 9 clientes es una referencia variable; 8/7 puede ocurrir y es menos habitual que 11 o 12 fiados. Frecuencias y tolerancias numericas reales siguen sin medirse.

## Puerta Pendiente

La revision tecnica DEV y la predeclaracion separada ya se completaron, sin entrenar: ver `APF3_PROTOCOLO_MODELADO_V6.md` y `APF3_PENDING_V6_MODEL_PROTOCOL.json`, SHA-256 `eb7fcd39f69be0115895cbb43b6d84e4488535646108bd6f21381d0fb1607923`. El snapshot esta en `/Users/tamaraalison/Downloads/APF3_Protocolo_Modelado_V6/`.

Los campos `selection_protocol`, `final_seed` y `final_dataset` del **protocolo de datos historico** siguen nulos; no se reescriben. La nueva especificacion separada fija CV, grilla, seleccion y futura semilla de test, pero en este cierre `models_authorized=false`, no hay modelos ni FINAL y el runner V6 todavia debe implementarse y probarse. La puerta tecnica no constituye aceptacion empresarial ni permiso de despliegue.

No elegir semillas, forzar etiquetas/otorgamientos ni ajustar distribuciones para mejorar metricas. Reportar todos los candidatos, desviaciones, desconocidos y limitaciones, aunque sean desfavorables. Los futuros resultados V6 requieren su propia evidencia, sin reutilizar metricas V4 como si fueran de V6.

Los modelos publicos y la aplicacion local siguen usando V4 anterior. No se reemplazan esos modelos ni se presenta la revision parcial como validacion predictiva o autorizacion de produccion.

## Comprobacion de esta Importacion

23 respuestas exactas contra la fuente actual; cinco tablas cotejadas con la plantilla original, CSV muestrales cotejados, correcciones con ordinales verificables, cero marcas de comentarios/cambios en el ZIP/XML. Word completado SHA-256 `82d4c748b3403e8a3e45b4361b95e9da4ffaf0b0ca21e3a9ac4baedc6040f29b` intacto antes/despues. La discrepancia con el hash de plantilla en blanco es esperada e intencional. Las otras salidas originales mantienen sus hashes.

Resumen de negocio en PDF de 2 paginas y DOCX nuevo, sin duplicar Word fuente/contactos; seis pruebas propias y Ruff selectivo correctos. No hubo cambios de generador, fuentes, protocolos, datasets o modelos congelados; no hubo ZIP, produccion ni commit.
