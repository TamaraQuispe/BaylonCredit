# APF2 - Guía de redacción e insumos verificables para Claude

Proyecto: Credify para Cervecería Baylón. Grupo 2. Documento de trabajo, NO informe final ni certificado de cumplimiento.

Documento consolidado: reúne requisitos, línea base, implementación, backlog, viabilidad, normativa, contrato de datos, riesgos, metodología, plantilla de validación, resultados de pruebas y capturas. Claude puede trabajar con este Word como insumo principal; las fuentes oficiales y el APF1 deben conservarse para cotejar citas. No trasladar toda esta guía al informe: el informe final tiene un límite de doce páginas, excluyendo portada, referencias y anexos.

## 1. Instrucción principal para Claude

Redacta APF2_TD_Grupo2_MVP_Innovacion siguiendo la consigna adjunta y el APF1 corregido en Word. Mantén empresa, problema, integrantes, Lean Startup y Kanban. Usa únicamente hechos identificados como implementados o verificados. Todo resultado no medido, captura ausente, entrevista no realizada, costo sin comprobante y responsable no asignado debe marcarse [PENDIENTE DE EVIDENCIA], no inventarse. Diferencia entorno de demostración, producción y piloto real. No confundas registros ficticios de pruebas con dataset real de APF3. No prometas exactitud predictiva, reducción de morosidad ni cumplimiento legal integral sin evidencia. Usa APA 7 y verifica referencias en fuentes oficiales. Este documento es un insumo; no sustituye la consigna ni la validación humana.

## 2. Fuentes que deben adjuntarse

- Innovacion_TD_Consigna_APF2 (1).pdf: cinco páginas, requisitos y rúbrica oficial.
- APF1_TD_Grupo2_DiagnosticoMiPYME.docx: versión corregida que delimita fiado a un día y entrenamiento con datos reales.
- APF1_B_G2_Rev_TKGMDK.docx: feedback del docente; nota 14/20 y énfasis en digitalizar antes de predecir.
- Capturas, pruebas, tablero Kanban y validación del propietario que el grupo recoja para APF2.
- El PDF de APF1 con el mismo nombre no coincide con el Word: contiene una versión anterior con referencia a datos simulados/reales. Usar el Word corregido como fuente principal.
- No utilizar el anterior APF1_Paso4_borrador.md ni su Word como evidencia: tienen afirmaciones que no representan íntegramente el estado del sistema.

## 3. Datos heredados del APF1

| Elemento | Información disponible |
|---|---|
| Institución y curso | Universidad Tecnológica del Perú; Innovación y Transformación Digital |
| Grupo | 2; sección 35036 |
| Docente | Caman Sanchez, Richard Enrique, transcripción de la carátula del APF1; variante ortográfica Camán Sánchez, Richard Enrique. Es la misma persona; conservar la escritura de la carátula hasta confirmación institucional |
| Integrantes | Omara Yamileth Baylón Vila; Tamara Alison Coveñas Quispe; César Augusto Daniel Paredes Paredes; Pablo Enrique Yman Avila |
| MiPYME | Cervecería Baylón, persona natural con negocio; identificador tributario omitido en esta copia pública |
| Ubicación declarada | San Martín de Porres, Lima; domicilio exacto omitido en esta copia pública |
| Operación | Dos años de antigüedad y dos colaboradores según APF1 |
| Acceso primario | Entrevista al propietario Rildo Baylón Espíritu, 28 de agosto de 2026; minuta, foto y tarjeta declaradas en anexos |
| Problema | Ausencia de scoring para clientes fijos que solicitan fiado a un día; registro manual e instinto del dueño |
| Línea base | 15 % de ventas al fiado y 5 % mensual referencial de mora/pérdida, estimados por el dueño; el denominador del 5 % está pendiente de precisar |
| Cobertura inicial | 0 % de clientes evaluados con scoring automatizado |
| Tecnología | IA de clasificación, con cloud como infraestructura complementaria |
| Metodología | Lean Startup: construir-medir-aprender |
| Gestión | Kanban |
| Usuario principal | Propietario y co-propietaria; el sistema apoya y no reemplaza su decisión |
| Barreras | Falta de tiempo y resistencia a delegar el criterio personal |
| Champion | Propietario; validación de adopción aún debe documentarse |

## 4. Entregables y límites exactos

- Informe APF2_TD_Grupo2_MVP_Innovacion.pdf: máximo 12 páginas sin portada, referencias y anexos.
- Presentación APF2_TD_Grupo2_MVP_Innovacion.pptx: máximo 12 diapositivas.
- URL pública funcional del MVP; si requiere login, incluir cuenta de prueba limitada. Nunca credenciales de administración del negocio.
- Anexos sin límite: arquitectura, pruebas, diccionario de datos y prompts con validación humana.
- Sustentación: 10 minutos de exposición y demo más 5 minutos de preguntas; todos deben participar.
- Rúbrica: coherencia 3 puntos, metodología aplicada 4, MVP 6, gestión ágil 3, viabilidad/normativa/APF3 2, sustentación 2.
- IA no declarada o contenido fabricado: penalización de cinco puntos; enlace roto compromete los seis puntos del MVP.

## 5. Estructura obligatoria y contenido a redactar

### 5.1 Resumen ejecutivo y línea base (0.5-1 página)

Presentar continuidad con APF1, problema, usuario, tecnología, indicador y brecha. No cambiar la empresa ni afirmar que Credify es una nueva empresa beneficiaria: es el nombre de la aplicación.

Objetivo sugerido: Para los propietarios de Cervecería Baylón, el MVP permitirá registrar clientes, fiados a un día y pagos, consultar saldos y una evaluación preliminar explicable, con el propósito de sistematizar el registro del crédito informal, medido mediante cobertura de registro digital y porcentaje de clientes evaluados.

La disminución de morosidad es una finalidad futura, no un resultado demostrado. Precisar con el dueño fórmula, periodo y denominador de la línea base antes de comparar.

### 5.2 Aplicación de Lean Startup (2-3 páginas)

Hipótesis heredadas: el dueño adoptará una herramienta simple; el uso podrá acumular historial suficiente para APF3. Convertirlas en hipótesis medibles, identificando los umbrales como propuestas del grupo.

- Construir: MVP real con cliente, fiado, evaluación, pago e historial.
- Medir: tareas completadas por el dueño, errores, duración, porcentaje de fiados registrados y cantidad de desenlaces utilizables.
- Aprender: incorporar la ficha de Rildo recibida, fechada 06/10/2026. Registra seis tareas completadas, cero ayudas y aceptación con condiciones. La decisión declarada es iterar y volver a probar. Las correcciones y su nueva validación siguen pendientes; Omara Baylon y Pablo Yman están confirmados como facilitadora y observador. Faltan las capturas citadas en la ficha.
- No presentar nuestra conversación de diseño o un test automatizado como entrevista o validación del propietario.

### 5.3 Desarrollo del MVP y gestión ágil (3-4 páginas)

Incluir URL, credenciales de prueba, arquitectura resumida, Kanban aplicado, backlog con mínimo ocho US, MoSCoW, criterios de aceptación y estado; pruebas por flujo crítico y roadmap.

Kanban de cierre operativo: docs/APF2_Kanban.json, con Por hacer / En curso / Revisión / Hecho / Bloqueado y WIP dos en curso y dos en revisión. Se registraron movimientos reales desde el inicio de esta sesión de cierre; el anexo incluye tabla, eventos y captura. No es evidencia de semanas anteriores de trabajo ni de responsables individuales aceptados por el grupo. El grupo debe continuar el tablero y validar sus asignaciones.

DoD propuesta: criterios satisfechos, revisión de código, pruebas pertinentes, lint/build correcto, despliegue, verificación y evidencia. El estado implementado en código no sustituye aceptación por el dueño.

### 5.4 Viabilidad, normativa y preparación APF3 (3-4 páginas)

Incluir viabilidad técnica/económica/organizacional, matriz de tres columnas requisito-función-evidencia, contrato de datos y al menos tres riesgos con probabilidad, impacto, responsable y mitigación.

### 5.5 Conclusiones

Sintetizar capacidad funcional demostrada, limitaciones y proyección APF3. Evitar concluir que el negocio ya redujo sus pérdidas. Ajustar extensión total a 12 páginas; las extensiones sugeridas por sección no deben sumarse por encima del límite.

## 6. MVP separado que se preparó

- Reutiliza React/FastAPI/PostgreSQL del sistema actual; conserva colores, header y navegación.
- Proyecto Docker independiente: credify-demo; volumen credify-demo_demo_data y red propia.
- Base credify_demo, sin copia ni conexión a la base de producción.
- Inicio: bash deploy/start-demo.sh. Dirección LOCAL: http://localhost:8081.
- Usuario de demostración: docente@example.com. Contraseña solo para ensayo local: DemoAPF2-2026! En la demo pública se generó una contraseña distinta; consultar el apartado de acceso del Word. Rol: operator, sin administración de usuarios.
- Tres clientes ficticios identificados con DEMO, sin información del negocio. El seed no inventa operaciones comerciales ni desenlaces.
- Plazo configurado de un día. ML deshabilitado mediante CREDIT_ML_ENABLED=false; evaluación preliminar por reglas, versión rules-v1. OpenRouter y WhatsApp deshabilitados.
- El aviso visual de demo se retiró a solicitud del grupo; los registros siguen siendo ficticios y este hecho debe declararse en informe y sustentación. La demo ejecuta lógica real y guarda operaciones de prueba en PostgreSQL; no es una maqueta.
- Demo pública habilitada: https://demo-credify.168-75-71-113.sslip.io/evaluacion-crediticia. Certificado público válido y respuesta externa HTTP/2 200 verificados. Localhost sigue siendo el ensayo local, no el enlace de entrega.
- Despliegue público en /home/ubuntu/credify-demo, con secretos propios y cuenta de operador. BD/API sin puertos públicos; frontend publicado solo en la puerta de enlace privada Docker y accesible por Caddy. API limitada a 256 MB, BD 128 MB y frontend 32 MB. Comparte VM y proxy con producción, pero no sus datos, red interna ni volumen de BD.
- La URL SSLIP del sistema de producción NO es la URL de esta demo. No confundirlas ni compartir credenciales de producción.
- Estos datos son solo pruebas funcionales, nunca insumo ni evidencia de modelo entrenado con datos reales.

## 7. Estado funcional y backlog base

| ID | Historia de usuario | MoSCoW propuesto | Estado | Criterio de aceptación |
|---|---|---|---|---|
| US01 | Como propietario, quiero ingresar con una cuenta autorizada para proteger los registros. | Must | Implementado | Login válido y rechazo de acceso inválido |
| US02 | Como operador, quiero registrar clientes para asociar correctamente los fiados. | Must | Implementado | Cliente guardado y consultable |
| US03 | Como propietario, quiero evaluar un monto para recibir una recomendación explicable. | Must | Implementado como evaluación preliminar | Score, riesgo, límite y factores devueltos y persistidos |
| US04 | Como operador, quiero registrar un fiado con vencimiento para controlar su cobro. | Must | Implementado | Crédito consultable y fecha de compromiso correcta |
| US05 | Como operador, quiero registrar abonos para actualizar la deuda del cliente. | Must | Implementado | Saldo disminuye sin permitir pago excesivo |
| US06 | Como propietario, quiero consultar cartera e historial para dar seguimiento. | Must | Implementado | Crédito, pagos y evaluaciones recuperables |
| US07 | Como equipo técnico, quiero guardar variables al evaluar para preparar APF3 sin fuga temporal. | Must | Implementado | Snapshot y vínculo evaluación-crédito en esquema |
| US08 | Como equipo técnico, quiero exportar desenlaces observados para construir el dataset. | Should | Implementado por script, no botón web | CSV con variables y etiqueta; casos no resueltos excluidos |
| US09 | Como cliente, quiero que quede constancia del consentimiento para conocer el uso de mis datos. | Must antes del piloto real | Parcial/pendiente | Constancia persistida con fecha, alcance y versión |
| US10 | Como propietario, quiero recordatorios WhatsApp para apoyar la cobranza. | Could | Código preparado; inactivo en demo | Envío real probado cuando se habilite |
| US11 | Como equipo, quiero entrenar y validar un modelo con datos reales para estimar riesgo. | Should | Pendiente APF3 | Dataset trazable y evaluación contra resultados observados |

Los estados describen código disponible. Adjuntar capturas y pruebas actuales; no afirmar validación humana de todas las US.

## 8. Arquitectura y capacidades técnicas

Flujo: navegador -> Nginx -> FastAPI -> PostgreSQL. En producción existe Caddy para TLS; la demo local no utiliza HTTPS público. Docker separa API, frontend, migración, seed y BD.

Frontend: React 18, TypeScript, Vite, Tailwind. Backend: Python 3.12, FastAPI, SQLAlchemy asíncrono, asyncpg. Persistencia: PostgreSQL 17 y Alembic. Autenticación: hash Argon2, JWT, refresh tokens y roles. WebAuthn existe, pero no es requisito de la demo; login por contraseña simplifica sustentación.

Endpoints: POST /api/v1/auth/login; GET/POST /api/v1/clients; POST /api/v1/credits/evaluate; GET /api/v1/credits/evaluations; GET/POST /api/v1/credits; GET/POST /api/v1/payments; GET /health/ready.

Tablas relevantes: clients, credits, payments, payment_allocations, credit_evaluations, users y business_settings.

El artefacto ML existente en el repositorio se originó con 4,000 filas sintéticas. No es un modelo validado con clientes reales; permanece deshabilitado en esta demo. OpenRouter explica decisiones pero no las determina. No afirmar que el MVP aprendió del negocio ni que sus porcentajes son probabilidades calibradas. Los factores visibles son contribuciones de reglas, no SHAP del ensemble.

## 9. Pruebas y guion de demo

Comando reproducible: python3 deploy/verify-demo.py. Crea operaciones únicamente en localhost:8081 y con clientes DEMO. Verifica salud, login, consulta de clientes, rechazo de monto cero, evaluación rules-v1, fiado de S/ 50 a un día, abono de S/ 20, saldo S/ 30 y consulta del historial.

Resultado ejecutado durante esta preparación: PASS en todos esos controles mediante HTTP contra la demo local. Es una prueba funcional automatizada de API y persistencia; no acredita revisión visual, prueba del propietario ni disponibilidad pública. El guion queda en deploy/verify-demo.py como evidencia reproducible.

Después de publicar, el mismo guion también pasó contra la URL HTTPS de la demo desde la VM. La ruta pública fue comprobada desde este equipo y producción respondió ready al finalizar. No se reiniciaron sus contenedores, pero durante el build hubo timeouts transitorios del healthcheck por carga en la VM; la disponibilidad compartida es una limitación que debe monitorearse. No atribuir estos controles a una prueba humana del propietario.

| Prueba | Esperado | Evidencia a conservar |
|---|---|---|
| Servicio | /health/ready devuelve ready | Salida del script |
| Acceso | Cuenta demo puede entrar | Captura, sin tokens |
| Validación | Monto cero devuelve 422 | Salida/script o captura |
| Evaluación | Score y factores, model_version rules-v1 | Captura y respuesta sin identificadores personales |
| Fiado | S/ 50 y vencimiento mañana | Pantalla de detalle |
| Abono | S/ 20 reduce saldo a S/ 30 | Pantalla antes/después |
| Persistencia | Consulta posterior conserva el saldo | Captura tras recargar |
| Historia | Evaluaciones guardadas | Pantalla de historial |

No marcar como prueba humana aprobada únicamente porque el script pasó. Durante esta preparación se ejecutó la suite backend en contenedor de pruebas con el código actualizado: 55 pruebas aprobadas, incluyendo protección del seed contra producción y desactivación del ML en demo. Ruff y ESLint pasaron; el build frontend de la demo terminó correctamente. Hay warnings preexistentes. Esto no sustituye aceptación del propietario ni una prueba visual del navegador. La construcción también reportó vulnerabilidades de dependencias npm pendientes de revisión antes de publicar la demo.

Demo de cuatro minutos propuesta: declarar verbalmente que se usan datos ficticios y evaluación preliminar por reglas; entrar; seleccionar cliente; evaluar S/ 50; registrar fiado a un día; consultar detalle; registrar abono S/ 20; volver a consultar saldo e historial. No pedir mostrar banner DEMO: fue retirado. Un dato ficticio de interfaz no es un dato inventado para validar ML.

## 10. Contrato de datos preliminar APF3

Fuente futura: operaciones consentidas del negocio. Snapshot al momento de evaluación en credit_evaluations.feature_snapshot, enlazado mediante credits.evaluation_id; desenlace de credits y pagos/asignaciones. Exportador: backend/scripts/export_real_credit_outcomes.py.

| Campo | Tipo | Significado |
|---|---|---|
| completed_sales | Numérico | Ventas registradas hasta evaluar |
| paid_credits | Numérico | Créditos completamente pagados |
| paid_late | Numérico | Créditos pagados con pagos posteriores al vencimiento |
| pending_overdue | Numérico | Créditos pendientes vencidos |
| pending_current | Numérico | Créditos pendientes no vencidos |
| outstanding | Decimal | Deuda pendiente |
| utilization | Decimal | Deuda / máximo configurado |
| requested_ratio | Decimal | Monto solicitado / máximo configurado |
| tenure_days | Numérico | Días desde registro del cliente |
| punctuality_rate | Decimal | Proporción histórica de pago sin atraso |
| overdue_rate | Decimal | Proporción de créditos activos vencidos |
| late_payment | Binario | 1 si no pagó completamente al vencimiento; 0 si pagó a tiempo |

El usuario confirmó Atraso al vencimiento. El código de preparación usa late_payment: 0 si el crédito se pagó totalmente hasta la fecha de vencimiento inclusive; 1 si se pagó después o mantiene saldo al observarlo desde el día siguiente. Mientras siga dentro del plazo y no esté pagado, no tiene etiqueta. Se eliminó la gracia de treinta días. Los CSV antiguos con defaulted se rechazan para evitar mezclar semánticas. Metadatos del futuro modelo: ml-real-late-v1, objetivo late_payment y grace_days 0. No se entrenó ni activó un modelo real.

Pruebas de este cambio: 58 tests backend aprobados y Ruff limpio. En la VM se desplegó una imagen independiente credify-training-tools, sin sustituir la API viva, y se ejecutó el exportador de solo lectura: cero casos elegibles con snapshot y enlace. Esta ausencia no se sustituye con datos ficticios. El flujo crediticio de la demo sigue por reglas.

APF1 exige 30-50 fiados reales y piloto de 4-6 semanas; si faltan, extender captura. El entrenador exige mínimo 30 desenlaces y cinco de cada clase. No todos los créditos ni evaluaciones serán entrenables. Registros antiguos sin snapshot no se reconstruyen con valores actuales. La demo no se mezcla con dataset del negocio.

Calidad: comprobar procedencia, faltantes, duplicados, etiquetas, rangos, fechas y consistencia de pagos. CSV actual omite identificadores directos pero no garantiza anonimización irreversible. El validador estructural tampoco distingue automáticamente datos reales de sintéticos.

Partición actual: aleatoria estratificada 80/20, semilla 42. Propuesta para APF3: partición temporal o por cliente, para evitar fuga y comparar con una línea base. Métricas previstas: precisión, recall, F1, matriz de confusión y ROC-AUC cuando ambas clases lo permitan. No reportar resultados reales aún inexistentes.

## 11. Viabilidad tripartita

Técnica: tecnologías abiertas, flujo persistente, despliegue Docker; límite API configurado en producción de 512 MB, no capacidad máxima de Oracle. Demo local usa Docker Desktop y no representa alta disponibilidad. Verificar recursos concretos y cuotas con proveedor antes de publicar.

Económica: licencias principales y certificado pueden no tener costo de licencia; SSLIP no requiere compra de dominio. Hosting gratuito condicionado a elegibilidad/facturación real. OpenRouter, WhatsApp, mantenimiento y capacitación tienen costos o restricciones a comprobar. No reutilizar S/ 48 de Render como costo comprobado de Oracle. Se incluye abajo una tabla preliminar en soles; facturación, horas y tarifas restantes siguen pendientes.

Tabla preliminar de costos en soles, no comprobante de facturación. No se presenta un total mensual mientras falten infraestructura y horas. Los importes cero se refieren exclusivamente al concepto indicado.

| Concepto | Importe en soles | Base y limitación |
|---|---|---|
| Licencias React, FastAPI y PostgreSQL | S/ 0 por licencia de uso del stack abierto | No incluye implementación, mantenimiento ni soporte |
| Compra de dominio SSLIP | S/ 0 de compra | Se utilizó subdominio sin registrar un dominio propio; depende del servicio externo |
| Emisión de certificado Let's Encrypt | S/ 0 por emisión | Caddy obtuvo certificado; no incluye administración del servidor |
| Consumo OpenRouter/WhatsApp en demo | S/ 0 de consumo de estos servicios en el flujo descrito | Ambos deshabilitados en la demo; no es cotización para producción |
| Infraestructura Oracle compartida | PEN 0.00 mostrado, 1-7 octubre 2026 | Reporte Cost Analysis recibido; no factura, ni mes completo, ni filtros de VM identificados |
| Internet/electricidad | [PENDIENTE: estimación] | El equipo debe estimar costo incremental, no todo el recibo del negocio |
| Capacitación/mantenimiento | [PENDIENTE: horas y tarifa] | No valorar trabajo como gratuito por ausencia de factura |

Si se citan tarifas en dólares, documentar fecha, fuente y tipo de cambio de la estimación. Los precios anteriores de Render no son el costo de este despliegue.

Organizacional: dos dueños, falta de tiempo y necesidad de conservar criterio humano. Capacitación estimada en APF1 de hasta dos horas es una hipótesis, no una sesión ejecutada. [PENDIENTE: plan y registro de capacitación, observaciones y aceptación].

## 12. Matriz normativa honesta

| Requisito | Función/proceso | Evidencia/estado |
|---|---|---|
| Protección de acceso | Autenticación, roles y contraseñas con hash | Implementado; pruebas y captura |
| Seguridad del transporte | Caddy HTTPS en producción | Configurado; demo local no acredita despliegue público seguro |
| Consentimiento informado | Casilla de registro de cliente | Parcial: no persiste constancia; completar antes del piloto real |
| Finalidad y minimización | Variables transaccionales y payload explicativo sin identificadores directos | Revisar flujo y redactar aviso de privacidad |
| Derechos del titular | Procedimiento de atención y eliminación/retención | Pendiente; archivar cliente no equivale a borrar datos |
| Proveedores externos | Cloud y servicios de IA | Pendiente documentar condiciones y transferencias aplicables |

Norma base: Ley 29733. Verificar reglamento vigente aprobado por D.S. 016-2024-JUS en fuentes oficiales; no reutilizar automáticamente D.S. 003-2013-JUS como reglamento actual. No inventar artículos ni calificar cualquier deuda como dato sensible legalmente sin sustento. La autorización académica del dueño no equivale al consentimiento de todos sus clientes. Reemplazar nombre por ID es seudonimización, no anonimización garantizada.

## 13. Riesgos y roadmap

| Riesgo | Probabilidad propuesta | Impacto | Responsable | Mitigación |
|---|---|---|---|---|
| URL inaccesible durante demo | Media | Alto | [ASIGNAR] | Publicar demo aislada, probar desde otra red y ensayar |
| Pocos desenlaces o una clase | Alta | Alto | [ASIGNAR] | Extender captura real; bloquear entrenamiento insuficiente |
| Mezclar pruebas y datos reales | Media | Alto | [ASIGNAR] | BD/red/volumen separados y aviso DEMO |
| Consentimiento no trazable | Alta mientras exista brecha | Alto | [ASIGNAR] | Persistir constancia y validar política antes del piloto |
| Caída de proveedor externo | Media | Medio | [ASIGNAR] | Demo sin OpenRouter/WhatsApp; fallback por reglas |
| Pérdida de datos | Baja/media | Alto | [ASIGNAR] | Backup externo y ensayo de restauración; no afirmarlo probado sin registro |

APF2 semanas 10-14: demo funcional, URL pública, prueba con dueño, Kanban, pruebas y captura real consentida. APF3 semana 15: dataset trazable, etiqueta/horizonte definidos, entrenamiento experimental y métricas. PROY semana 17: integración validada, impacto y transferencia. Las semanas son hitos académicos, no fechas de calendario inventadas.

## 14. Anexos y presentación

Anexo A: arquitectura y flujo. Anexo B: diccionario, evidencia de pruebas y esquema no sensible. Anexo C obligatorio: prompts de IA y validación humana, incluyendo asistencia de programación y redacción realmente utilizada. Capturas del Kanban y prueba con usuario también deben adjuntarse.

Exposición: continuidad 1 min; metodología 2 min; MVP/demo 4 min; ágil 1.5 min; viabilidad/normativa 1 min; APF3 0.5 min. Total diez minutos más preguntas. Máximo doce slides.

## 15. Lista de pendientes antes de afirmar que APF2 está listo

- URL de demo HTTPS independiente publicada y comprobada; volver a verificar acceso y credenciales antes de sustentar. No exponer puertos BD/API ni usar la contraseña fija del ensayo local.
- Capturar pantallas desktop/móvil y ejecutar prueba humana del flujo completo.
- Incorporar ficha entregada de Rildo; completar facilitador/observador y anexos, corregir hallazgos y repetir prueba. No hay ficha de la co-propietaria.
- Tablero de cierre creado con movimientos reales; el grupo confirma responsables y continúa su uso. No atribuirle historia previa.
- Precisar denominador y fórmula de morosidad referencial del 5 %.
- Etiqueta resuelta como atraso contractual; mantener definición y no reutilizar CSV de treinta días. La validación predictiva real sigue pendiente.
- Completar consentimiento persistido antes de operar con datos reales.
- Verificar recursos/costos y referencias legales oficiales.
- No entrenar modelo con datos de la demo ni presentar métricas sintéticas como evidencia de negocio.
- Revisión humana final de citas, afirmaciones, anexos y límite de páginas.

## 16. Prompt listo para Claude

Actúa como asistente de redacción académica. Con la consigna APF2, el APF1 corregido en Word y esta guía, redacta un borrador del informe APF2_TD_Grupo2_MVP_Innovacion de máximo doce páginas, excluyendo portada, referencias y anexos. Conserva Cervecería Baylón, Grupo 2, Lean Startup, Kanban y el problema del fiado a un día. Distingue evidencia implementada, prueba técnica, demo con datos ficticios, piloto real y funcionalidades pendientes. Incluye las cinco secciones obligatorias, backlog de al menos ocho historias con MoSCoW y criterios, matriz de pruebas, roadmap, viabilidad tripartita, matriz normativa de tres columnas, contrato de datos y riesgos. No inventes entrevistas, métricas, costos, enlaces públicos, resultados de ML, citas ni cumplimiento legal. Marca faltantes [PENDIENTE DE EVIDENCIA] y entrega una lista de preguntas para completar la información. Indica que la demo usa reglas, no un modelo validado con clientes reales. Mantén un estilo académico claro, referencias APA 7 verificables y anexo de IA con validación humana. No incluyas credenciales de producción.

## 17. ¿Claude puede crear el MVP?

Sí: Claude puede asistir en implementación, pruebas, documentación y mejoras si recibe el código y acceso al entorno autorizado. Sin embargo, el MVP ya existe: la demo pública cumple el flujo de cliente, evaluación preliminar por reglas, fiado, abono, saldo e historial. No pedir otra aplicación desde cero ni sustituir la demo por una maqueta o capturas generadas.

Instrucción adicional para Claude: Reutiliza el código de Credify y la configuración docker-compose.demo.yml. Antes de programar, distingue lo ya implementado de lo pendiente. Si se requiere completar el MVP, trabaja solo en el entorno separado de demostración, preserva los colores y el diseño y no modifiques producción ni uses sus datos o secretos. Comprueba el flujo principal y documenta resultados reales. Las mejoras al modelo con datos reales pertenecen a APF3. No declarar una función terminada solo porque se escribió el código: debe probarse y desplegarse.

## 18. Paquete para completar APF2

Consultar APF2_Validacion_y_Artefactos.md y APF2_Cierre_de_Pendientes.md: ficha recibida, guion de repetición, hipótesis, contrato alineado y pendientes. El tablero de cierre tiene eventos reales de esta sesión; no se atribuye uso de Kanban a semanas anteriores. Se mantiene separada la validación declarada en la ficha de Rildo de las pruebas automatizadas.

Las capturas y el reporte de pruebas se entregan en la carpeta APF2_Grupo2_Evidencias de Descargas. Diferenciar pruebas automatizadas del equipo y aceptación real por el propietario. Los valores de marketing del login (por ejemplo, 99.4 % de precisión y montos gestionados) no constituyen métricas verificadas y no deben citarse como resultados del piloto.

## 19. Estado de cierre y ficha de validación recibida

Pruebas técnicas disponibles: el reporte actualizado contiene diecisiete comprobaciones automatizadas aprobadas y diez capturas reales de la demo, con fecha de ejecución registrada. Incluye comprobación del contador corregido, formulario vacío bloqueado y fallo de red simulado mediante intercepción del navegador. La falla de red es un caso controlado, no una caída real del servidor. No son una sesión con Rildo ni demuestran adopción del negocio. Los anexos incluyen los resultados y todas las capturas disponibles.

Las capturas se renovaron después de corregir Créditos en navegación y el contador de clientes. También muestran el logo local compartido y el ajuste de ancho del contenido en escritorio. El contador se calcula ahora con clientes cargados, no con la constante 245. La ficha original conserva esa observación histórica, que ahora puede vincularse a una corrección y nueva prueba. La fecha del anexo técnico no reemplaza la fecha de Rildo. Los demás hallazgos siguen pendientes salvo prueba específica.

El grupo entregó APF2_Grupo2_Ficha_Validacion_Rildo.docx completada. Según esa ficha, la sesión remota ocurrió el 06/10/2026 de 23:56 a 23:59, en PC con Chrome. Las seis tareas suman 48.9 segundos de ejecución, dentro de una sesión de aproximadamente tres minutos; no confundir ambas duraciones. Se registran seis tareas completadas y cero ayudas. La ficha marca autorizaciones de notas, capturas y grabación, pero la autorización de grabación no prueba que exista un video.

La aceptación registrada es CON CONDICIONES y la decisión es ITERAR Y VOLVER A PROBAR, no una aprobación definitiva del uso diario. Rildo pide acciones de fila visibles, contadores consistentes, revisión de clientes con el mismo nombre, estado de vencimiento correcto, aclarar el modo de pago y formatos de fecha consistentes. También solicita historial real antes de fiar; score 92 e impago estimado 8 % son salidas preliminares de reglas en esa prueba, no precisión del modelo ni resultados del negocio.

Roles confirmados por el grupo y añadidos a la ficha: facilitadora Omara Baylon; observador Pablo Yman. Se consignó el nombre del observador, no una firma. La firma del propietario era opcional y está vacía: no describir la ficha como firmada. Las capturas citadas T1_01_login.png a T6_04_historiales.png no se localizaron con esos nombres en Descargas; las siete capturas automatizadas existentes son evidencia distinta y no deben atribuirse a esa sesión.

Propuesta abreviada de validación: una sesión real de diez minutos para registrar un fiado ficticio de S/ 50, abonar S/ 20 y consultar el saldo; preguntar si lo usaría, qué fue difícil y qué cambiaría. Registrar las respuestas reales con su autorización. La ficha completa y el experimento están incluidos a continuación.

Roles del Kanban: la ficha identifica como responsable de dos mejoras a Grupo 2 - Credify, sin asignación individual. El grupo debe confirmar nombres. El tablero documenta los hallazgos recibidos y las actividades pendientes desde ahora, no movimientos históricos inventados.

### Registro de asistencia de IA para revisar y completar

| Solicitud realmente utilizada | Uso | Verificación disponible / revisión pendiente |
|---|---|---|
| Analizar consigna APF2 y APF1 corregido | Identificar estructura y continuidad | Lectura de archivos; cotejo final del grupo pendiente |
| Preparar demo separada y guía para Claude | Configuración Docker y documento de trabajo | Demo HTTPS y flujo verificados; aceptación del dueño pendiente |
| Corregir aviso, imágenes y logo | Cambios de interfaz solicitados por el grupo | Build, lint y carga de logos comprobados |
| Obtener pruebas y capturas | Evidencia de flujo técnico | Trece controles aprobados; capturas de navegador; no validación humana del propietario |
| Consolidar materiales en un Word | Insumo para redactar APF2 | Estructura e imágenes del Word comprobadas; citas y redacción final requieren revisión humana |

Esta tabla ayuda a preparar el anexo obligatorio de IA. El grupo debe añadir herramienta/modelo si puede confirmarlos, fecha, prompt exacto cuando esté disponible y qué revisión humana realizó. No atribuir pruebas automatizadas a revisión humana ni inventar la firma o aprobación de un integrante.

Herramienta de asistencia de esta sesión: OpenCode; modelo declarado por el entorno: OpenAI gpt-6.1-sol. Claude participa en la redacción del informe por separado; el grupo debe registrar el modelo/versión que utilizó allí. La fecha de ejecución de pruebas está en el JSON, pero no es la fecha original de emisión de cada prompt.

Se recuperaron del historial local seis prompts académicos con texto exacto, fecha UTC y Lima, identificador de mensaje, proveedor y modelo de las respuestas. Archivo anexo-c-prompts.json en Descargas/APF2_Grupo2_Evidencias. Estas fechas son de mensajes, no de capturas. Se incorporan al anexo del Word. No es el historial de Claude ni del APF1 previo: el grupo debe adjuntar esos registros y declarar cualquier resumen sin original. La revisión humana debe describirse por quien realmente la realizó.

## 20. Contradicción de la etiqueta y límites de la evidencia

La diferencia de objetivo se resolvió con confirmación explícita del usuario: preparación APF3 para atraso desde el vencimiento, sin gracia. Cambiaron etiqueta, CSV, metadatos y pruebas; no se entrenó un modelo ni se cambió el scoring de producción. El informe puede declarar el contrato alineado, pero no desempeño predictivo validado.

La firma de Rildo era opcional en la ficha; no inventarla. El video no fue entregado: la autorización no acredita que se grabó. El denominador del 5 % requiere confirmación del propietario. Las capturas nuevas 08-formulario-vacio-validacion.png y 09-error-red-simulado.png son evidencia técnica de esta ejecución, no los archivos T1-T6 citados en su ficha.

Mantener credenciales solo de demo en la entrega dirigida al docente. Rotar contraseña después de la evaluación y actualizar el documento si aún circula; no publicar claves de producción ni tokens.

### Reporte de costos Oracle entregado

El grupo entregó Cost details by date2026-10-07T22_46_51Z.pdf. Periodo UTC: 1 al 7 de octubre de 2026. Total mostrado: PEN 0.00. La tabla detalla Block Storage, Compute, Telemetry y Virtual Cloud Network con 0.00 en cada día. Es un reporte de análisis de costos, NO factura. No muestra filtros o recursos concretos y el gráfico indica No data to display, aunque la tabla incluye siete filas en cero. Usar el importe reportado sin afirmar que confirma un mes completo, gratuidad permanente o costo exclusivo de Credify. Conservar ese límite de alcance en la viabilidad y adjuntar el PDF original o las reproducciones del anexo.

## 21. Capturas por tarea generadas posteriormente

A solicitud del usuario se generó la carpeta APF2_Grupo2_Capturas_Tareas en Descargas con seis imágenes: T1_01_login.png, T2_01_clientes.png, T3_01_evaluacion.png, T4_01_fiado.png, T5_01_pago.png y T6_04_historiales.png. Son capturas técnicas posteriores de otra ejecución del asistente con datos ficticios, no las capturas de la sesión original del propietario. README.md y procedencia.json registran origen, fecha y correspondencia con las imágenes técnicas.

La referencia de anexos en la ficha de Rildo se aclaró para indicar esta procedencia. No se modificaron resultados, tiempos, comentarios, roles ni firmas. Para el informe, distinguir aceptación declarada en la ficha y funcionamiento demostrado en estas capturas posteriores; no atribuir estas imágenes a Rildo.
