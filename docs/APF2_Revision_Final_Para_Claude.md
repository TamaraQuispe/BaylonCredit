# APF2 - Instrucciones de corrección final del informe

Informe a corregir: APF2_TD_Grupo2_MVP_Innovacion.docx. Grupo 2, Cervecería Baylón, aplicación Credify. Objetivo: obtener una versión completa y coherente para revisión humana y entrega. Esta guía no garantiza una nota ni permite inventar información.

## 1. Fuentes y prioridad

1. Consigna y rúbrica oficial Innovacion_TD_Consigna_APF2 (1).pdf: requisitos y límites.
2. APF1_TD_Grupo2_DiagnosticoMiPYME.docx corregido: continuidad, fiado a un día, Lean Startup y Kanban.
3. APF2_Grupo2_Ficha_Validacion_Rildo (1).docx: NUEVA versión con 12 capturas y una imagen de firma. Sustituye la versión anterior como fuente de validación, no altera la fecha ni los resultados declarados.
4. APF2_Grupo2_Guia_e_Insumos_Para_Claude.docx y registros técnicos actualizados: implementación y pruebas.
5. Carpeta APF2_Grupo2_Evidencias: reporte-pruebas.json, capturas 08 y 09, captura móvil, tablero y registro de prompts.
6. Cost details by date2026-10-07T22_46_51Z.pdf: reporte Oracle recibido.

Corregir el informe existente, no elaborar otra propuesta ni otra aplicación. Cuando una afirmación histórica se haya actualizado, corregir cuerpo, tablas, conclusiones y anexos. Mantener separados resultados de Rildo y pruebas automatizadas.

## 2. Checklist de correcciones obligatorias

| ID | Ubicación | Corrección requerida | Evidencia o criterio de cierre |
|---|---|---|---|
| C01 | 2.3, Anexo B.1 y cualquier mención equivalente | Eliminar que las capturas de la ficha no están disponibles | La nueva ficha incluye 12 capturas identificadas por tarea |
| C02 | 2.3, Anexo B y cualquier mención equivalente | Eliminar que la firma está vacía; indicar que contiene imagen de firma | No afirmar firma digital certificada ni autenticarla criptográficamente |
| C03 | Ficha incorporada y 2.3 | Consignar facilitadora Omara Baylon y observador Pablo Yman | Roles confirmados por el grupo; nueva ficha aún los deja vacíos |
| C04 | Tabla 10 P3 y Anexo B | Incrustar capturas de formulario vacío y fallo de red controlado | Archivos 08 y 09 disponibles; no dejar instrucción incrustar |
| C05 | Tabla 6 y Anexo B | Añadir captura móvil si se afirma esa evidencia | 07-evaluacion-mobile.png; aclarar alcance de prueba, no certificación completa de responsive |
| C06 | Tabla 10 P9 y Anexo B.2 | Adjuntar respaldo técnico de la suite backend y resultados de navegador | No usar el JSON de navegador para probar los 58 tests backend |
| C07 | Tabla 17 | Completar responsables de riesgos con nombres o roles confirmados | No asignar personas sin confirmación del grupo |
| C08 | 3.2 y tablero | Incorporar mejoras R01-R07 al backlog/tablero | R02 corregido técnicamente; repetir con propietario. Resto pendiente salvo prueba específica |
| C09 | Tabla 8 US09 y roadmap | Resolver contradicción consentimiento pendiente APF3 versus piloto real APF2 | Debe completarse ANTES de cualquier captura con clientes reales, independientemente de la fase |
| C10 | Tabla 16 Fuente y conclusiones | No concluir que cero casos elegibles significa cero datos reales en la BD | Exporte cero filas elegibles con vínculo, snapshot y desenlace; no prueba ausencia de créditos/pagos |
| C11 | Tabla 16 Unidad de observación | No afirmar que fecha de corte se incluye/persiste en CSV | Timestamp de evaluación en BD; exportador usa fecha de observación, pero CSV no la contiene |
| C12 | Tabla 16 Campos/volumen | Quitar confirmar donde el código ya verifica el contrato | 11 features + late_payment = 12 columnas; mínimo 30 filas y cinco por clase antes de dividir |
| C13 | Tabla 16 Partición/métricas | Separar implementación actual de plan APF3 | Actual: split estratificado 80/20 semilla 42; StandardScaler y regresión logística; accuracy y ROC-AUC |
| C14 | Tablas 12 y 13 | Cambiar horas mensuales de hosting por costo mensual de hosting | No confundir horas de personal, importe de alojamiento ni periodo observado |
| C15 | Tabla 12 | Ampliar criterio de beneficio | Incluir tiempo, trazabilidad y futura reducción de atrasos, sin beneficios monetarios inventados |
| C16 | Numeración | Corregir salto Tabla 13 -> Tabla 15 | Numerar consecutivamente y actualizar referencias cruzadas |
| C17 | Todo el documento | Quitar instrucciones de edición, barras y marcadores resueltos | Incrustar, adjuntar, confirmar y //Script// no deben quedar como borrador |
| C18 | Referencias y citas | Citar las fuentes efectivamente usadas en Kanban/MoSCoW y verificar edición | No mantener libros sin uso ni presentar verificaciones no realizadas |
| C19 | Anexo C | Completar registro Claude y revisión humana | Prompts/fechas/modelo reales, no metadatos de OpenCode reutilizados |
| C20 | PDF final | Comprobar límite de 12 páginas de cuerpo | Exportar PDF y contar desde sección 1 hasta conclusiones; no inferir paginación del DOCX |

## 3. Nueva ficha: cómo usarla

La versión APF2_Grupo2_Ficha_Validacion_Rildo (1).docx tiene 13 imágenes: una de firma y doce capturas. La inspección visual mostró pantallas de la versión de la demo de esa ficha, distintas de las capturas técnicas posteriores suministradas por OpenCode. Incorporarlas como capturas adjuntas a la ficha remitida por el grupo. No afirmar una fecha de toma o autor que no conste en la evidencia: distinguir la fecha declarada de sesión de una fecha técnica de archivo.

Capturas rotuladas en la nueva ficha:

- T1_01_login.png y T1_02_inicio.png: acceso e inicio.
- T2_01_lista_clientes.png y T2_02_detalle_cliente.png: listado y ficha del cliente.
- T3_01_resultado.png: resultado de evaluación.
- T4_01_evaluacion_previa.png, T4_02_tras_confirmar.png y T4_03_lista_creditos.png: registro de fiado.
- T5_01_monto.png y T5_02_tras_confirmar.png: abono de S/ 20 y confirmación.
- T6_01_detalle_credito.png y T6_02_lista_pagos.png: saldo e historial de pagos.

Conservar estos resultados declarados: seis tareas completadas, cero ayudas, suma de 48.9 s, sesión 06/10/2026 de 23:56 a 23:59, aceptación con condiciones y decisión iterar y volver a probar. No interpretar que el flujo completado careció de hallazgos de usabilidad. No modificar comentarios originales para mostrar que ya fueron corregidos.

La firma incorporada es una imagen; describirla así si hace falta. No inventar una firma del observador ni afirmar certificación digital. La nueva ficha aún presenta facilitador/observador vacíos: añadir los nombres confirmados, o indicar en el informe que fueron confirmados posteriormente por el grupo. La existencia de autorización de video no significa que haya video entregado.

## 4. Redacciones de sustitución

### 4.1 Evidencia de validación

Se recibió una versión ampliada de la ficha de validación del propietario, con doce capturas por tarea y una imagen de firma en la constancia. Estos anexos se incorporan como evidencia aportada por el grupo. Se mantienen separados de las capturas automatizadas posteriores del asistente, que demuestran funcionamiento técnico pero no constituyen otra validación del propietario.

### 4.2 Cero casos elegibles

La ejecución del exportador produjo cero casos elegibles con evaluación vinculada, snapshot de variables y desenlace observado. Esto no demuestra que la base carezca de créditos o pagos registrados. No se entrenó un modelo real ni se sustituyó el modelo de producción.

### 4.3 Fecha de corte y CSV

La evaluación conserva fecha de creación en la base de datos. El exportador utiliza la fecha de observación para determinar el desenlace, pero actualmente el CSV contiene solo las once variables y late_payment, sin timestamp de evaluación ni fecha de corte. La incorporación de estos metadatos a un manifiesto de exportación queda pendiente.

### 4.4 Consentimiento

La constancia persistida de consentimiento debe completarse antes del piloto con datos personales reales. Su prioridad es previa a la captura real, aunque el entrenamiento ocurra en APF3. La demostración con registros ficticios no acredita consentimiento de clientes reales.

### 4.5 Métricas

El entrenador preparado implementa regresión logística con escalado y partición aleatoria estratificada 80/20, semilla 42. Calcula accuracy y ROC-AUC. Precision, recall, F1, matriz de confusión y partición temporal/por cliente se proponen para la validación de APF3 y no se presentan como mediciones existentes. Se exigen treinta filas y cinco de cada clase antes del split, no cinco en cada partición.

### 4.6 Economía

La viabilidad económica se evaluará contrastando costos con beneficios medidos, incluyendo tiempo de registro/consulta, trazabilidad y eventual disminución de atrasos. El reporte Oracle aportado muestra PEN 0.00 del 1 al 7 de octubre de 2026; no es una factura, no muestra filtros/VM, no equivale al mes completo y no garantiza gratuidad futura. Las estimaciones de capacitación y mantenimiento son supuestos de planificación, no gastos realizados.

## 5. Evidencias técnicas que deben adjuntarse

| Evidencia | Fuente disponible | Tratamiento |
|---|---|---|
| Formulario vacío | APF2_Grupo2_Evidencias/08-formulario-vacio-validacion.png | Incrustar; validación del navegador |
| Fallo de red | APF2_Grupo2_Evidencias/09-error-red-simulado.png | Incrustar; simulación por intercepción, no caída real |
| Móvil | APF2_Grupo2_Evidencias/07-evaluacion-mobile.png | Incrustar y describir pantalla/contexto probado |
| Navegador | reporte-pruebas.json | 17 comprobaciones, inicio 2026-10-07T22:34:36.425Z y fin 22:34:58.615Z |
| Backend | APF2_Grupo2_Evidencias/backend-pruebas.log | Nueva ejecución: 2026-10-08T01:58:43Z (7 octubre, 20:58:43 Lima); 58 aprobadas, 4 warnings, Ruff limpio en archivos revisados. No atribuir esa fecha al cierre anterior |
| Anexo C OpenCode | anexo-c-prompts.json | Seis solicitudes exactas, fechas UTC/Lima, proveedor/modelo |
| Kanban cierre | kanban.json/html y 10-kanban-cierre.png | Tablero iniciado en cierre, no gestión histórica del grupo |
| Oracle | Cost details by date2026-10-07T22_46_51Z.pdf | Dos páginas; PEN 0.00 mostrado con límites de alcance |
| Propietario | Nueva ficha (1).docx | Capturas adjuntas y firma en imagen; no confundir con captura automatizada |

No mezclar conteos de ejecuciones. 13 y 17 corresponden a comprobaciones de navegador en versiones diferentes; 55 y 58 a suite backend antes/después de nuevos tests. Usar 17 y 58 como cifras actuales e indicar fecha de cada respaldo. No sumarlas como un único total de aceptación humana.

Este Word incluye las capturas 08, 09 y móvil, y el respaldo de la nueva ejecución backend para que Claude los incorpore sin dejar adjuntar como instrucción. No sustituyen la prueba del propietario. El informe original de Claude no se modificó durante esta revisión.

## 6. Pendientes que no puede resolver Claude por redacción

| Pendiente real | Qué se requiere |
|---|---|
| Morosidad 5 % | Confirmar con Rildo denominador, periodo y si es atraso o pérdida definitiva |
| Responsables humanos | Grupo confirma asignaciones para riesgos, mejoras y continuidad Kanban |
| Historial Claude | Prompts exactos, fechas y versión real del modelo |
| Revisión humana | Cada integrante declara qué cotejó y qué cambió; no atribuirle revisión no realizada |
| Alcance Oracle | Confirmar filtros/recursos y costo de otros periodos si se necesita mensualidad |
| Horas/tarifas | Aprobar supuestos presupuestarios o entregar valores reales |
| Mejoras R01/R03-R07 | Implementación y prueba posterior; no afirmar corrección ni aceptación del dueño |
| Paginación | PDF renderizado para contar páginas y revisar tablas/imágenes |

Si no se obtiene un dato, presentarlo claramente como limitación y acción futura, no llenarlo con una cifra arbitraria. Para indicar informe al 100 % deben cerrarse los requisitos necesarios; una redacción prolija no sustituye la evidencia.

## 7. Lo que está correcto y debe conservarse

- Misma MiPYME, problema, grupo, Lean Startup y Kanban.
- Demo pública con clientes ficticios, lógica real y persistencia.
- rules-v1 en demo, sin ML validado con datos reales ni WhatsApp activo.
- late_payment alineado al vencimiento; CSV anteriores rechazados.
- Aceptación con condiciones, no adopción diaria demostrada.
- S/ 0 mostrado por Oracle limitado al periodo y consulta.
- Modelo de OpenCode registrado en historial como proveedor openai/modelo gpt-6.1-sol; es metadato de registro, no un resultado predictivo del negocio.
- Nota sobre porcentajes publicitarios no verificados del login.

La ficha y sus imágenes no prueban por sí solas corrección de hallazgos. El informe debe conservar su trazabilidad temporal: observación -> decisión -> cambio -> prueba técnica -> nueva prueba con el propietario cuando se realice.

## 8. Prompt listo para aplicar estas correcciones

Corrige APF2_TD_Grupo2_MVP_Innovacion.docx existente usando esta guía, la nueva ficha APF2_Grupo2_Ficha_Validacion_Rildo (1).docx, la consigna y evidencias actuales. No reescribas el proyecto desde cero. Incorpora la ficha ampliada con doce capturas y firma en imagen; elimina afirmaciones de anexos no disponibles o firma vacía en la versión previa. Mantén separados esos anexos de las capturas técnicas posteriores. Consigna Omara Baylon y Pablo Yman sin inventar firmas. Adjunta 08, 09, móvil y respaldos de pruebas, y quita las instrucciones de edición resueltas. Corrige el significado de cero casos exportados, la ausencia de timestamps en CSV, consentimiento previo al piloto real, métricas actuales versus futuras, costos y numeración de tablas. Integra las mejoras al tablero con estados reales. Completa responsables y revisión humana solo con confirmación del grupo. No inventes denominador del 5 %, fechas de prompts Claude, resultados ML, facturas ni aceptación posterior. Conserva doce páginas máximas de cuerpo excluyendo portada, referencias y anexos; exporta PDF para verificar paginación. Entrega Word corregido, checklist de rúbrica y una lista concreta de pendientes reales. No prometas nota máxima ni declares cumplimiento integral sin evidencia.
