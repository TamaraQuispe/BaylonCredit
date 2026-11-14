# APF2 - Avances técnicos del cierre de pendientes

Proyecto Credify, Grupo 2. Documento complementario al informe v3 y su checklist. No sustituye la ficha del propietario ni constituye nueva aceptación humana. Las fechas y resultados del anexo técnico son de esta ejecución posterior.

## 1. Estado de R01-R07

| Tarjeta | Cambio o diagnóstico realizado | Evidencia | Límite |
|---|---|---|---|
| R01 | Ver detalle siempre visible, sin depender de hover | Clic en escritorio y móvil verificado | Editar no tenía implementación; se muestra deshabilitado y explícito, no se creó editor |
| R02 | Contador por clientes cargados, no 245 fijo | Comparación de listado/API aprobada | No cambia observación histórica del propietario |
| R03 | Nombres compartidos identificados por documento; diagnóstico por ID y documento | Dos nombres iguales con IDs/documentos distintos; registros cargados sin repetición de esos identificadores | No se borraron clientes ni se declaró auditoría completa del negocio |
| R04 | Días calculados de fecha real, eliminadas constantes 4/15; singular correcto | Listado Vence en 1 día y detalle Falta 1 día | La política de riesgo no cambió; nueva prueba con Rildo pendiente |
| R05 | Monto inicial vacío; abono explícito; deuda total solo al pulsar botón | Abono UI S/20 y saldo persistido S/30 | No es una nueva validación del propietario |
| R06 | DD/MM/YYYY; timestamps DD/MM/YYYY, HH:mm en Lima | Utilidades comprobadas en UTC, Lima y Tokio y pantalla de pagos | Fechas del negocio no se alteraron; solo formato y cálculo de presentación |
| R07 | Aviso de historial limitado y resultado por reglas orientativo | Captura y prueba automatizada | No se entrenó ML ni cambió aprobación del backend; indicador por reglas no es probabilidad calibrada |

Los estados Hecho del tablero significan cierre técnico: implementación/diagnóstico, build/lint, publicación y prueba. La aceptación de Rildo después de estos cambios sigue pendiente. No modificar su ficha anterior ni reemplazar sus comentarios por resultados nuevos.

## 2. Incidencia adicional corregida

Al abrir un crédito por enlace directo, la pantalla podía redirigir antes de cargar la cartera. Se corrigió para esperar carga inicial y mostrar error si falla, antes de decidir si el crédito existe. La prueba de vencimiento detectó el fallo y pasó después de corregirlo. No presentar la primera ejecución fallida como aprobada; el reporte final registra la nueva ejecución exitosa.

El login dejó de mostrar 99.4 % de precisión, S/ 48,500+, 100 % cero papel y cifrado bancario de punto a punto: no eran cifras verificadas ni una descripción precisa del transporte. Se sustituyeron por descripción funcional y acceso HTTPS, sin cambiar colores ni diseño. Las imágenes históricas de la ficha mantienen lo que se vio entonces; las capturas nuevas muestran el contenido actual.

## 3. Evidencia y despliegue

Se actualizó solo el frontend de demo, compilado localmente. API, base de datos y producción no se recrearon. La prueba posterior utilizó clientes ficticios separados, sin borrar registros. URL: https://demo-credify.168-75-71-113.sslip.io.

Resultados en Descargas/APF2_Grupo2_Evidencias/Mejoras_R: reporte-mejoras.json y capturas de acciones, indicador, vencimientos, abono y fechas. Ocho comprobaciones posteriores aprobadas. No se suman a las diecisiete de la ejecución anterior ni a las 58 de backend. Leer las fechas del reporte nuevo.

Kanban actualizado con R01-R07, criterios, evidencia de movimientos reales y WIP máximo dos En curso y dos Revisión. El usuario confirmó distribución para seguimiento FUTURO: Tamara infraestructura/aplicación; César dataset y separación de datos; Omara coordinación con Rildo y consentimiento; Pablo pruebas, Kanban y evidencias. OpenCode ejecutó los cambios técnicos; esta asignación no acredita revisiones o actividades humanas ya realizadas.

## 3.1 Responsables confirmados para riesgos

| Riesgo | Responsable de seguimiento confirmado |
|---|---|
| URL/infraestructura no disponible | Tamara Alison Coveñas Quispe |
| Pocos desenlaces o una clase | César Augusto Daniel Paredes Paredes |
| Mezclar datos ficticios y reales | César Augusto Daniel Paredes Paredes |
| Consentimiento no trazable | Omara Yamileth Baylón Vila |
| Caída de proveedor externo | Tamara Alison Coveñas Quispe |
| Pérdida de datos | Tamara Alison Coveñas Quispe; César apoya verificación de datos |
| Pruebas de mitigación, tablero y evidencias | Pablo Enrique Yman Avila |

En Tabla 16 del informe reemplazar Por confirmar con estas asignaciones futuras, sin atribuir medidas que aún no se ejecutaron. Pablo coordina verificación; Omara coordina la nueva prueba con Rildo. La revisión humana del Anexo C aún debe documentar qué cotejó cada integrante.

## 4. Correcciones concretas para el informe v3

- Actualizar Tabla 5, 3.2, Tabla 10 y conclusiones: ya no afirmar que solo R02 fue atendido. Describir el cierre técnico según tabla de este documento, con sus límites.
- Incorporar R01-R07 al tablero y citar movimientos actuales; no darles fechas del pasado.
- Mantener la aceptación con condiciones de la ficha y la nueva prueba pendiente.
- Tabla 6 Datos APF3: sustituir aún sin datos reales por aún sin dataset real elegible para entrenamiento.
- Tabla 15 calidad: sustituir eso es seudonimización por el CSV omite identificadores directos, lo cual no garantiza anonimización irreversible.
- US07: sustituir preparar APF3 sin fuga temporal por conservar variables disponibles al evaluar para reducir el riesgo de fuga temporal. No garantizar que el split aleatorio ya evita toda fuga.
- R07: documentar advertencia y presentación de indicador por reglas, no resultado ML validado ni aprobación garantizada.
- Añadir nueva ejecución técnica y capturas en anexo separado; no reemplazar fechas de Rildo ni mezclar conteos.
- En la nueva ficha (1) se completaron los nombres de facilitadora Omara Baylon y observador Pablo Yman, ya confirmados por el grupo. Se conservaron las doce capturas y la firma en imagen del propietario; no se añadió firma del observador ni se alteraron tiempos/resultados. El informe puede quitar que esos nombres siguen vacíos en la versión actualizada.

## 5. Confirmaciones humanas que permanecen pendientes

| Pendiente | Qué confirmar |
|---|---|
| Responsables de riesgos y revalidación | Distribución futura confirmada; registrar resultados cuando realicen las actividades |
| Revisión humana Anexo C | Qué cotejó realmente cada integrante, fuente y cambios realizados |
| Historial Claude | Fecha y modelo de solicitudes, o resumen fiel declarado como resumen |
| 5 % de morosidad | Denominador, periodo, atraso versus pérdida definitiva; respuesta de Rildo |
| Oracle y presupuesto | Alcance de filtros del reporte y aprobación de supuestos de horas/tarifa |
| Consentimiento real | Constancia persistida y procesos necesarios ANTES del piloto con clientes reales |
| Nueva prueba con propietario | Repetir tareas afectadas y registrar comentarios auténticos |
| Paginación | Compartir/exportar PDF del informe; no se confirmó su paginación desde el DOCX |

No afirmar que todos los pendientes académicos están resueltos. Estas mejoras completan parte técnica y evidencia, no revisión humana, facturación ni adopción real.

## 6. Ficha breve de revisión humana por completar

Los siguientes son encargos propuestos según la distribución confirmada, no revisiones ejecutadas. Cada integrante debe registrar fecha, fuente, resultado del cotejo y cambio real; no marcar aprobado sin revisarlo.

| Integrante | Fuente a cotejar | Resultado / cambio / fecha |
|---|---|---|
| Omara | Ficha del propietario y correspondencia de capturas; consulta sobre el 5 % | [COMPLETAR después de revisar] |
| Tamara | Implementación desplegada, costos Oracle y límites de infraestructura | [COMPLETAR después de revisar] |
| César | Campos del dataset, etiqueta y exclusión de datos ficticios | [COMPLETAR después de revisar] |
| Pablo | Capturas/pruebas, tablero, referencias y checklist de entrega | [COMPLETAR después de revisar] |

Para el 5 %, enviar a Rildo: ¿Ese 5 % mensual se calcula sobre todas las ventas, solo las ventas fiadas, la deuda pendiente o los clientes? ¿Es atraso que luego cobras o pérdida definitiva? ¿Qué mes o periodo y qué registro respaldan la estimación?

## 7. Actualización del checklist de Claude

- C03: aplicada en la ficha ampliada; roles consignados y capturas/firma original preservadas. No se añadió firma del observador.
- C07: asignación futura de responsables confirmada por el usuario; completar tabla de riesgos del informe con sección 3.1.
- C08: R01-R07 ya están en el tablero real y tienen verificación técnica publicada; la nueva prueba del propietario sigue pendiente.
- C19: continúa pendiente la declaración concreta de revisión humana y completar historial de Claude; no cambiarla a aplicada solo por tener responsables.
- C20: verificar el PDF renderizado aportado por el grupo; no se comprobó su paginación con el DOCX ni se recibió el PDF en esta sesión.

No alterar la ficha histórica para afirmar que Rildo vio estos cambios antes de que existieran. Adjuntar reporte técnico nuevo y mantener el hito de revalidación como futuro.
