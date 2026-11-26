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

## Expiracion de revisiones

La API expira sola las revisiones pendientes o asignadas que superan
`CREDIT_REVIEW_TTL_HOURS` (48 por defecto). Un ciclo interno arranca con el
lifespan y se repite cada `CREDIT_REVIEW_EXPIRY_INTERVAL_MINUTES` (60 por
defecto); con `0` se desactiva el ciclo. La cola tambien cierra los items
vencidos al consultarse, asi que nunca se muestran ni se pueden resolver
revisiones caducadas.

No hace falta un cron con token: los access tokens duran 30 minutos
(`ACCESS_TOKEN_EXPIRE_MINUTES`) y un bearer fijo en cron dejaria de autenticar.
El endpoint admin sigue disponible para un cierre manual puntual:

```bash
curl -fsS -X POST -H "Authorization: Bearer $TOKEN" \
  https://TU_DOMINIO/api/v1/credits/reviews/expire
```

Con varias replicas de la API cada una ejecuta el ciclo; es idempotente y usa
bloqueo `SKIP LOCKED`, asi que no duplica trabajo sobre la misma revision.

Al desplegar, el primer ciclo cierra cualquier pendiente que ya supere el TTL.
Si se quiere conservar esa cola, subir `CREDIT_REVIEW_TTL_HOURS` antes del
despliegue y ajustarlo despues.
