# PROY - Despliegue, operacion y rollback

## Antes de desplegar
- Inventariar imagenes, contenedores, mounts y versiones activas.
- Revisar diferencias de codigo/configuracion del servidor antes de cualquier pull.
- Construir fuera del servidor para la arquitectura correcta.
- Comprobar checksums de imagenes y bundles.

## Rollback
- Conservar imagenes y bundle anteriores con tags unicos.
- Probar rollback de codigo. Un rollback de imagen no revierte migracion ni mutacion de datos.
- Respaldar la base y probar restauracion en entorno separado antes de migraciones autorizadas.

## Verificacion
- Verificar /health/live, /health/ready, autenticacion, reglas, inferencia elegible, cola y version visible.
- Medir latencia fria y caliente, RSS y concurrencia del flujo completo.
- Si falla el modelo, mantener regla dura y revision humana.
- Si falla infraestructura, mostrar indisponibilidad, no credito aprobado.

## Incidente a evitar
- No relanzar migrate/seed accidentalmente en recuperacion de timeout.
- Usar --no-deps y --no-build solo cuando corresponda.