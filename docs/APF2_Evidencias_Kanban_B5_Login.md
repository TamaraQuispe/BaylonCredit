# APF2 - Evidencias para completar Kanban, B.5 y login

Grupo 2 · Credify · Cervecería Baylón. Documento complementario dirigido a Claude para incorporar tres respaldos reales al informe. No es una nueva validación del propietario ni una prueba de acceso a Oracle.

## 1. Cómo incorporarlo al informe

- Actualizar la figura/tabla de Kanban con la vista R01-R07 y el registro completo actual.
- Crear o completar Anexo B.5 con el resumen y contenido literal de reporte-mejoras.json.
- Completar la fila de autenticación de la tabla de pruebas con el caso de contraseña incorrecta y su evidencia.
- Mantener fechas independientes: reporte de mejoras del 08/10/2026; captura actual de tablero y nueva prueba de login con fecha que aparece en sus respectivos registros.
- No sumar las ocho comprobaciones de mejoras a las diecisiete generales y las 58 backend como una aceptación humana.
- Renumerar figuras/tablas y referencias según el informe final. Este documento no cambia automáticamente el informe.

## 2. Kanban actualizado

La imagen adjunta es una vista filtrada R01-R07 del tablero real, generada de docs/APF2_Kanban.json. Las siete tarjetas aparecen en Hecho como cierre técnico de implementación/diagnóstico y pruebas; no significa adopción diaria o validación ML. La copia completa del tablero mantiene otras tarjetas y sus bloqueos/revisiones.

| Tarjeta | Contenido del cierre |
|---|---|
| R01 | Detalle visible sin hover; edición inexistente explícitamente deshabilitada |
| R02 | Contador por clientes cargados; valor 21/21 es dato de la sesión registrada, no constante actual |
| R03 | Nombres compartidos diferenciados por documentos; no se borraron clientes por nombre |
| R04 | Días de vencimiento reales y singular/plural correctos |
| R05 | Importe inicial vacío, total por acción expresa, abono parcial probado |
| R06 | Formato de fechas y timestamps Lima probado |
| R07 | Aviso de historial limitado; no garantía de pago ni modelo validado |

WIP del tablero: máximo dos En curso y dos Revisión. La vista filtrada no muestra P01-P06; el archivo kanban.json conserva todas las tarjetas y eventos. La ficha de revalidación recibida registra continuidad con condiciones; DNI/RUC en selectores y piloto real siguen pendientes. La definición del 5 % se recibió como estimación de pérdida mensual sobre ventas, no medición contable corroborada.

Pie sugerido: Vista filtrada de las tarjetas R01-R07 del Kanban operativo, con cierre técnico registrado y fecha de captura indicada. Fuente: registro del proyecto. No acredita trabajo histórico anterior al inicio del tablero.

## 3. Anexo B.5 - Reporte de mejoras

Fuente original: APF2_Grupo2_Evidencias/Mejoras_R/reporte-mejoras.json. Inicio UTC 2026-10-08T23:16:48.210Z; fin 23:17:30.182Z. Navegador configurado es-PE, zona America/Lima, URL de demo. Ocho comprobaciones aprobadas; incluye R01 en escritorio y móvil como comprobaciones distintas.

El contenido literal se adjunta en este Word. No modificar su fecha ni su tipo histórico: cuando se ejecutó el reporte, figuraba aceptación con propietario pendiente; la ficha recibida posteriormente se incorpora por separado. El resultado demuestra operación técnica con datos ficticios, no entrenamiento ML, adopción cotidiana o disminución de pérdidas.

Tabla sugerida para B.5: tarjeta, resultado y detalle. Utilizar el JSON como respaldo verificable; no sustituirlo por una afirmación sin fecha o inventar un reporte nuevo.

## 4. Prueba de credenciales inválidas

Se realizó un intento controlado en el formulario de login de la demo con el usuario docente@example.com y una contraseña deliberadamente incorrecta. La respuesta fue HTTP 401 y el mensaje visible Invalid email or password; el navegador permaneció en iniciar-sesion y no se creó sesión en almacenamiento local/de sesión. Después se ingresó con la contraseña válida y se alcanzó inicio. No se imprimen contraseñas válidas ni tokens en esta evidencia.

La captura y el JSON del caso se adjuntan con su fecha real de ejecución. Esta prueba no verifica todas las variantes de autenticación, MFA, bloqueo tras múltiples fallos o acceso a la cuenta Oracle.

Redacción sugerida: La prueba de autenticación negativa devolvió HTTP 401 ante una contraseña incorrecta y mostró un mensaje de error sin crear sesión. Posteriormente se comprobó acceso válido con la cuenta de demostración. Resultado: pasó. Evidencia: captura de login y login-credenciales-invalidas.json.

## 5. Archivos complementarios en Descargas

- APF2_Grupo2_Evidencias/Respaldo_Final/kanban-r01-r07.png: vista legible de las siete tarjetas.
- APF2_Grupo2_Evidencias/Respaldo_Final/kanban-r01-r07.json: datos de la vista y fecha de captura.
- APF2_Grupo2_Evidencias/kanban.json: tablero completo y eventos.
- APF2_Grupo2_Evidencias/Mejoras_R/reporte-mejoras.json: original literal de B.5.
- APF2_Grupo2_Evidencias/Respaldo_Final/login-credenciales-invalidas.png: error visible de login.
- APF2_Grupo2_Evidencias/Respaldo_Final/login-credenciales-invalidas.json: resultados del intento controlado y acceso válido posterior.

## 6. Instrucción para Claude

Incorpora estas tres evidencias al informe existente. Usa la captura R01-R07 para actualizar la gestión ágil y adjunta el JSON literal con su tabla resumen en B.5. En la prueba de login, sustituye pendiente de evidencia por el resultado del caso negativo con fecha de su nuevo registro. Mantén separados registros de mejoras, navegador general, backend y propietario. No atribuyas estos tests a Rildo, no cambies sus fichas ni elimines las condiciones nuevas o la revisión humana del Anexo C. Después de insertar, actualiza referencias, checklist y PDF de máximo doce páginas de cuerpo; los anexos no cuentan para ese límite.
