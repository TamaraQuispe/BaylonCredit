# APF2 - Correcciones y aclaraciones para Claude

Proyecto: Credify para Cervecería Baylón. Grupo 2. Documento complementario: no sustituye la consigna ni el informe final.

## 1. Instrucciones de uso

Aplicar estas correcciones al borrador de APF2 y cotejarlas con APF2_Grupo2_Guia_e_Insumos_Para_Claude.docx actualizado. Diferenciar observación histórica, corrección implementada, prueba técnica y pendiente. No modificar retroactivamente la ficha de Rildo para hacer desaparecer hallazgos. No convertir datos ficticios en evidencia real de negocio.

## 2. Correcciones realizadas y texto recomendado

| Punto | Corrección o aclaración | Cómo reflejarlo en el informe |
|---|---|---|
| Contador 245 | Se eliminó la constante y se muestra el número de clientes cargados. Publicado y probado en demo. | Durante la prueba del propietario se detectó un contador fijo inconsistente. Se corrigió y se verificó técnicamente; queda pendiente repetir la tarea con él. |
| Banner DEMO | El aviso fue retirado. Se eliminó la instrucción de mostrarlo en el guion. | Antes de demostrar, declarar verbalmente que la demo usa datos ficticios y evaluación preliminar por reglas. |
| Nombre del docente | La guía conserva la escritura de la carátula del APF1: Caman Sanchez, Richard Enrique; explica la variante Camán Sánchez. | Usar una sola escritura, consistente con carátula o registro institucional confirmado. No tratarlos como dos docentes distintos. |
| Formulario vacío | Se obtuvo una captura y una comprobación de validación del navegador. | El formulario impide enviar los campos obligatorios vacíos; adjuntar evidencia técnica nueva. |
| Error de red | Se interceptó y abortó la solicitud en el navegador para probar el mensaje y la conservación del formulario. | Describirlo como fallo de red simulado de forma controlada, no una caída real del servidor. |
| Costos | Se incorporó una tabla preliminar en soles con importes por concepto y pendientes. | No declarar un costo mensual total mientras falten factura de hosting, horas y tarifas. |
| Anexo C | Se identificó OpenCode y el modelo declarado por el entorno, OpenAI gpt-6.1-sol, y se recuperaron varios prompts exactos. | Registrar Claude por separado y confirmar allí su modelo. No asignar a los prompts las fechas de las pruebas automatizadas. |

## 3. Evidencias técnicas actualizadas

La carpeta APF2_Grupo2_Evidencias de Descargas contiene nueve capturas y un reporte de diecisiete comprobaciones aprobadas. Son pruebas automatizadas del equipo, no resultados de la sesión del propietario.

| Archivo | Contenido |
|---|---|
| 01-login-desktop.png | Login y logo local |
| 02-clientes-desktop.png | Listado y contador de clientes actualizado |
| 03-evaluacion-desktop.png | Resultado preliminar y factores |
| 04-fiado-antes-del-pago.png | Crédito antes de registrar abono |
| 05-fiado-despues-del-pago.png | Crédito después del abono |
| 06-historial-desktop.png | Historial de evaluaciones |
| 07-evaluacion-mobile.png | Pantalla en ancho móvil |
| 08-formulario-vacio-validacion.png | Validación de formulario vacío |
| 09-error-red-simulado.png | Mensaje ante fallo de red controlado |
| reporte-pruebas.json | Resultados y fecha real de ejecución |
| README.md | Resumen de la ejecución |

No renombrar estas imágenes como T1-T6 para atribuirlas a la sesión de Rildo. El contador actual puede superar cinco clientes porque las pruebas agregan registros ficticios: el criterio es coherencia con la lista cargada, no mantener artificialmente cinco filas.

## 4. Contradicción de la etiqueta APF3

| Aspecto | Estado actual |
|---|---|
| Objetivo APF1 | Estimar atraso desde el vencimiento del fiado a un día |
| Código de preparación de datos | Actualizado: atraso al vencimiento, etiqueta late_payment, sin gracia |
| Motivo de la diferencia | Se acordó previamente ese umbral de treinta días durante la implementación |
| Corrección implementada | CSV/metadatos/pruebas alineados; 58 tests aprobados; tooling separado en la VM |
| Decisión confirmada | Atraso al vencimiento, por elección explícita del usuario |

Texto recomendado: El contrato preliminar se alineó a atraso desde el vencimiento. late_payment toma 0 para pago completo hasta el vencimiento inclusive y 1 para pago posterior o saldo pendiente observado desde el día siguiente. Los registros todavía sin desenlace se excluyen. Se rechazaron CSV con etiquetas antiguas para no mezclar objetivos. El MVP demuestra registro y persistencia, no desempeño predictivo validado.

La preparación y exportación se desplegaron como tooling independiente, no como sustitución del modelo de producción. No afirmar que un modelo real ya predice atraso. La demo utiliza reglas preliminares y no entrena con los registros ficticios.

## 5. Ficha de Rildo: qué conservar

- Facilitadora: Omara Baylon. Observador: Pablo Yman, confirmados por el grupo.
- Fecha declarada: 06/10/2026; intervalo 23:56-23:59.
- Seis tareas completadas y cero ayudas, según la ficha entregada.
- Suma de tareas: 48.9 segundos; duración de sesión aproximada: tres minutos. No son la misma medición.
- Aceptación con condiciones y decisión de iterar y volver a probar.
- La observación 245 frente a cinco filas es histórica y debe conservarse como hallazgo, enlazándola con la corrección posterior.
- La firma de Rildo era opcional y no consta. No describir la ficha como firmada.
- La autorización para grabar no demuestra que exista video. No se ha entregado una grabación.
- La consigna APF2 revisada no exige expresamente firma o video; sí requiere evidencia propia de aplicación metodológica y prueba con usuario.

## 6. Pendientes que no se deben ocultar

| Pendiente | Información o acción requerida |
|---|---|
| Capturas originales de Rildo | No disponibles; usar seis capturas técnicas posteriores identificadas sin atribuirlas a esa sesión |
| Kanban | Aportar evidencia de tablero utilizado, responsables y movimientos reales; la plantilla no acredita gestión histórica |
| Denominador del 5 % | Preguntar a Rildo si se refiere a ventas totales, ventas fiadas, saldo o fiados; confirmar periodo y fórmula |
| Costos completos | Cost Analysis recibido: PEN 0.00 mostrado del 1 al 7 de octubre; confirmar filtros/alcance y estimar horas/costos restantes |
| Anexo C | Completar fechas y prompts exactos faltantes; describir revisión humana realmente realizada |
| Nueva validación de correcciones | Repetir con el propietario los flujos afectados; un test técnico no reemplaza esa aceptación |
| Otros hallazgos de Rildo | Acciones ocultas, vencimiento, modo de pago y fechas siguen pendientes salvo evidencia específica posterior |

## 7. Tabla de costos preliminar en soles

| Concepto | Importe | Alcance y pendiente |
|---|---|---|
| Licencias del stack abierto | S/ 0 por licencia | No incluye desarrollo, mantenimiento ni soporte |
| Compra de dominio SSLIP | S/ 0 de compra | No se registró dominio propio; disponibilidad depende del proveedor |
| Emisión Let's Encrypt | S/ 0 por emisión | No incluye administración del servidor |
| Consumo OpenRouter/WhatsApp del flujo demo | S/ 0 de consumo | Servicios deshabilitados en la demo; no es precio de producción |
| Hosting Oracle compartido | PEN 0.00 mostrado, 1-7 octubre 2026 | Cost Analysis recibido; no identifica VM/filtros, no factura ni mes completo |
| Internet y electricidad | Pendiente de estimar | Estimar costo incremental |
| Capacitación y mantenimiento | Pendiente de estimar | Horas reales o previstas por tarifa justificada |

No sumar los ceros y concluir que el proyecto completo no cuesta nada. No usar S/ 48 estimados para Render como factura del despliegue en Oracle. Si se convierten dólares, documentar fecha, fuente y tipo de cambio.

## 8. Anexo C: datos recuperados y límites

Herramienta usada en esta asistencia: OpenCode. Modelo declarado por su entorno: OpenAI gpt-6.1-sol. Claude es otra herramienta usada por el grupo para el informe; registrar su versión y revisión de forma independiente.

Prompts exactos recuperados de esta conversación:

- me puedes dar una ficha para llenar para rildo en un word a parte para que sea mas facil
- facilitador: Omara Baylon y observador: Pablo Yman
- ya mira ahora en el demo la palabra creditos en el NAV sale asi CrÃ©ditos y no se entiende corrigelo
- ya puedes tomar nuevamente las capturas de pantalla y corregir el word

Se recuperaron seis registros con fechas UTC/Lima y modelos asociados en anexo-c-prompts.json, que se incorporan al Word consolidado. El historial de Claude y cualquier prompt anterior de APF1 siguen a cargo del grupo. La fecha del reporte de pruebas no es la fecha de un prompt. Los resúmenes sin original deben identificarse como tales.

## 9. Credenciales de demostración

La cuenta de prueba de la demo puede incluirse en la entrega dirigida al docente porque la consigna requiere acceso cuando existe login. No incluir cuentas administrativas del negocio ni secretos de API/BD. Rotar la contraseña de demo después de la evaluación; aún no se ha rotado para no romper el acceso del docente.

## 10. Instrucción final para Claude

Actualiza el informe según este documento y la guía consolidada. Presenta el contador corregido, banner sustituido por declaración verbal, validaciones de formulario y fallo de red simulado. La etiqueta se resolvió como atraso al vencimiento; modelo real pendiente. Se declaran T1-T6 no entregadas. El tablero operativo se inició durante este cierre con movimientos reales, sin atribuirle uso histórico. Morosidad del 5 % y factura Oracle siguen pendientes. Usar fechas de prompts recuperadas y solicitar historial Claude. No inventar firmas, video, costos ni revisión humana. Mantener doce páginas de cuerpo y aceptación con condiciones de Rildo.

Actualización posterior: se generaron seis capturas técnicas por tarea en APF2_Grupo2_Capturas_Tareas, con README y procedencia fechada. Sirven como evidencia funcional posterior y NO como capturas originales de Rildo. La referencia de anexos de la ficha se aclaró sin modificar sus resultados. El reporte actual contiene diez capturas técnicas generales y diecisiete comprobaciones aprobadas.

## 11. Dónde consultar la factura o costo de Oracle

Entrar a https://cloud.oracle.com con la cuenta titular. Menú -> Billing & Cost Management (Facturación y gestión de costos) -> Billing -> Invoices (Facturas). Seleccionar factura y Download Invoice para descargar PDF. No pulsar Pay ni cambiar el plan: solo necesitamos consulta de evidencia.

Si no hay factura, consultar Billing & Cost Management -> Cost Management -> Cost Analysis. Seleccionar periodo de uso de la demo, Show: Cost (no Usage), filtrar por el compartimento/recursos del proyecto y Apply. Conservar una captura con periodo, moneda e importe. Desde Tab Actions se puede descargar la tabla CSV o el tab actual PDF.

Si el costo muestra cero para ese periodo y filtro, esa es evidencia del costo observado; no prueba que siempre será gratuito. Una tabla vacía o falta de permisos no significa costo cero. Los datos pueden tardar hasta 48 horas en aparecer. Para una VM con PostgreSQL en Docker, revisar Compute y Block Storage; no asumir que aparece como servicio administrado Database.

Antes de compartir: ocultar tarjeta, dirección, correo de facturación e identificadores innecesarios. Si no se tiene acceso, consultar al titular/administrador de la cuenta, sin solicitarle contraseña o códigos de acceso.

Fuentes oficiales consultadas: https://docs.oracle.com/en-us/iaas/Content/Billing/Concepts/invoices.htm y https://docs.oracle.com/en-us/iaas/Content/Billing/Concepts/costanalysisoverview.htm.

## 12. Reporte de costos Oracle recibido

Fuente: Cost details by date2026-10-07T22_46_51Z.pdf en Descargas, dos páginas. El periodo es 1-7 octubre 2026 UTC, la moneda PEN y el total mostrado PEN 0.00. Tabla diaria: Block Storage, Compute, Telemetry y Virtual Cloud Network con ceros en los siete días. El gráfico presenta No data to display. No contiene número de factura, filtros ni identificación de VM/compartimento.

Texto para Claude: El reporte Oracle Cost Analysis aportado muestra PEN 0.00 para el periodo del 1 al 7 de octubre de 2026. Se adjunta como evidencia del importe mostrado en la consulta; al no incluir filtros o identificación de recursos, no se atribuye exclusivamente a Credify ni se extrapola a una mensualidad completa. No constituye una factura ni garantiza gratuidad futura.

La fila del hosting ya no debe decir que no se recibió ningún documento. Sustituir por reporte recibido con alcance pendiente de confirmar. La capacitación y el mantenimiento siguen siendo estimaciones de planificación, no gastos realizados.
