# APF3 - Pruebas de fallos del backend

Ejecucion final UTC: 2026-11-03 17:07:08.820 a 17:07:25.999.
Proyecto Docker local exclusivo: `credify-resilience`.
No se detuvieron ni desplegaron produccion o demo publica.

## Resultados

| Escenario real | HTTP | Tiempo observado |
| --- | --- | --- |
| PostgreSQL detenido | 503 | 20 ms |
| PostgreSQL pausado, timeout | 503 | 2029 ms |
| API detenida, error del proxy | 504 | 3026 ms |

Las tres recuperaciones tambien pasaron: cero filas del cliente antes del
reenvio explicito y una fila despues, con HTTP 201. Se comprobaron los cinco
campos rellenados, consentimiento y token conservados, un solo POST por intento
fallido y ausencia de reintentos automaticos de indisponibilidad. Las dos fallas
de BD mantuvieron liveness 200 y readiness 503.

## Archivos

- `APF3_Grupo2_Pruebas_Fallos_Backend.docx`: informe con 3 tablas y 6 capturas.
- `fallos-backend-reales.json`: resultados medidos de los 6 casos aprobados.
- `verificaciones.json`: suite backend y verificaciones de build/lint.
- `evidencias-sha256.json`: hashes de los 2 JSON y las 6 capturas usados en Word.
- `01-*`, `02-*`, `03-*`: mensajes de fallo en el formulario.
- `*-recuperado.png`: recuperaciones de los tres escenarios.
- `diagnostico-ejecucion.png`: intento anterior fallido, no incluido en Word
  ni en los resultados aprobados finales; se conserva como diagnostico.

Backend: 126 pruebas aprobadas, incluidas 30 de fallos. Frontend: build y lint
correctos. Ruff de los archivos de resiliencia y scripts de prueba/informe:
correcto. Ruff global conserva un E501 previo en `app/scripts/seed_demo.py:33`.
La suite tuvo 13 warnings de serializacion/deprecacion, documentados en el JSON.

## Limites

Los datos y el operador son ficticios. Es evidencia tecnica local, no validacion
del propietario ni de produccion. El formulario se envia con `requestSubmit()`
y el handler React real, sin interceptar la red; no prueba el clic fisico en
Guardar. Los tiempos no constituyen SLA o benchmark. No se probo perder la
respuesta despues de un COMMIT confirmado: consultar el historial antes de
reenviar una operacion incierta. No hay garantia universal de exactamente una
vez ni claves de idempotencia nuevas.

Reproduccion y decisiones tecnicas: `docs/BACKEND_FAILURE_TESTS.md` en el
repositorio. Generador del Word: `deploy/report-backend-failures.py`.
Los cambios de resiliencia permanecen locales, sin commit ni despliegue publico.
