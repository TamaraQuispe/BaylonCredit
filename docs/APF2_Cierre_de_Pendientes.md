# APF2 - Cierre verificable y datos que requiere el grupo

## 1. Estado del trabajo

| Punto | Estado | Evidencia y límite |
|---|---|---|
| Etiqueta APF3 | Resuelto en preparación | Elección atraso al vencimiento; late_payment; 58 tests; tooling separado; cero casos elegibles exportados, sin entrenamiento |
| T1-T6 | Originales no disponibles; técnicas posteriores generadas | Carpeta APF2_Grupo2_Capturas_Tareas con seis capturas fechadas; no se atribuyen a Rildo |
| Kanban | Tablero operativo iniciado | JSON con movimientos reales de esta sesión, WIP 2; no historial de semanas previas |
| Morosidad 5 % | Bloqueado por confirmación | Se requiere definición y periodo de Rildo |
| Costos | Reporte Oracle recibido; estimación restante | Cost Analysis muestra PEN 0.00 del 1 al 7 de octubre; filtros y factura no constan |
| Anexo C OpenCode | Seis solicitudes recuperadas | Texto exacto, UTC/Lima, proveedor/modelo; revisión humana y registros Claude deben aportarse |

## 2. Declaración de capturas de la ficha

Texto para el informe: No se dispone de capturas de la sesión del propietario. Se conserva su ficha y se adjuntan seis capturas técnicas posteriores por tarea, tomadas por OpenCode y fechadas en procedencia.json. No se atribuyen a la sesión con Rildo. La referencia de anexos de la ficha se aclaró para evitar esa confusión, sin cambiar sus resultados.

## 3. Preguntas concretas para Rildo

Enviar: En el APF1 anotamos aproximadamente 5 % mensual de morosidad o pérdida. ¿Cinco por ciento de qué: todas las ventas, solo las ventas al fiado, el saldo pendiente o la cantidad de clientes? ¿De qué mes o periodo sale esa estimación? ¿Es dinero atrasado que luego se cobra o dinero que finalmente no se recupera?

| Campo a confirmar | Respuesta del propietario |
|---|---|
| Denominador del 5 % | [PENDIENTE] |
| Numerador: atraso o pérdida definitiva | [PENDIENTE] |
| Mes o periodo | [PENDIENTE] |
| Fuente: cuaderno/recuerdo/cálculo | [PENDIENTE] |
| Fórmula y si es estimación | [PENDIENTE] |

Hasta recibir respuesta, escribir línea base referencial estimada por el propietario, sin compararla numéricamente con otra métrica. No convertir atraso en pérdida financiera automáticamente.

## 4. Estimación económica de planificación

Los siguientes valores son supuestos propuestos para presupuesto, no horas realizadas ni cotizaciones recibidas. Tarifa propuesta para valorar trabajo: S/ 20 por hora, a confirmar por el grupo. No representa una tarifa de Oracle ni un salario documentado.

| Concepto | Supuesto | Estimación | Frecuencia y confirmación |
|---|---|---|---|
| Capacitación inicial | 2 h a S/ 20/h | S/ 40 | Una vez; hipótesis de dos horas del APF1, no capacitación ejecutada |
| Mantenimiento básico | 2 h a S/ 20/h | S/ 40 | Mensual; planificación propuesta |
| Licencias y emisión de certificado | Stack abierto y Let's Encrypt | S/ 0 por esos conceptos | No incluye soporte |
| Dominio SSLIP | Sin compra de dominio propio | S/ 0 de compra | Servicio externo |
| OpenRouter/WhatsApp de demo | Deshabilitados | S/ 0 de consumo del flujo | No extrapolar a producción |
| Hosting compartido Oracle | Reporte Cost Analysis recibido | PEN 0.00 mostrado del 1 al 7 de octubre de 2026 | No extrapolar a mes completo ni atribuir a VM sin confirmar filtros; H mensual por confirmar |
| Internet/electricidad incremental | Importe E por estimar | E soles/mes | No usar total del recibo sin atribución |

Presupuesto mensual propuesto: S/ 40 + H + E, más cualquier servicio externo que se active. Capacitación inicial: S/ 40 adicionales una sola vez. No presentar un total cerrado mientras H y E estén desconocidos ni sumar capacitación como gasto mensual permanente.

Evidencia requerida de Oracle: captura/exportación de Cost Analysis o Billing con periodo, importe y moneda, identificando qué recursos corresponden a esta VM. Ocultar número de tarjeta, direcciones, secretos e identificadores innecesarios. Si el importe es cero, adjuntar esa evidencia; tener una VM no acredita free tier.

Reporte entregado: Cost details by date2026-10-07T22_46_51Z.pdf, dos páginas. Página 1: periodo 1-7 octubre UTC, Cost To Date PEN 0.00 y gráfico No data to display. Página 2: siete días con Block Storage, Compute, Telemetry y Virtual Cloud Network, todos 0.00; total PEN 0.00. El PDF no contiene número de factura ni filtros/identificación de cuenta, compartimento o VM. Registrar el resultado mostrado con esa limitación. No se necesita conversión de dólares porque ya está en PEN.

## 5. Uso del tablero

docs/APF2_Kanban.json mantiene las seis tarjetas y sus eventos. deploy/apf2-kanban.py controla WIP y registra la hora real al mover cada tarjeta. El tablero puede continuar desde ahora; no registrar fechas retroactivas. Asistencia técnica OpenCode es el ejecutor de las tareas técnicas; el grupo confirma responsables humanos y revisa entregables. Bloqueados por respuesta de propietario/facturación permanecen visibles.

## 6. Uso del Anexo C

anexo-c-prompts.json proviene de una consulta acotada y de solo lectura del historial OpenCode. No se exportaron secretos, autenticación ni conversaciones de otros proyectos. Cada fila conserva mensaje, texto y fecha. El registro documenta asistencia real, pero no prueba revisión humana: esa columna debe completarse con lo que cada integrante realmente cotejó. Para Claude, aportar su historial de solicitudes, fechas y modelo; no reutilizar metadatos de OpenCode.
