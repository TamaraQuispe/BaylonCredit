# Pruebas aisladas de fallos del backend

## Alcance

Prueba real local de navegador, Nginx, FastAPI y PostgreSQL 17. No usa
intercepcion de red del navegador. Detiene o pausa exclusivamente contenedores
con etiqueta Compose `credify-resilience`, nunca servicios publicos.
Los clientes y la cuenta del operador son ficticios. No desplegar este Compose.

## Cambios y decisiones

- La dependencia de BD transforma fallos de conexion y timeout en HTTP 503,
  mensaje seguro, `code=database_unavailable`, `Retry-After: 5` y `X-Request-ID`.
- Hay presupuestos configurables para conexion, comando y espera del pool.
  Valores por defecto: 5, 10 y 5 segundos; el entorno de prueba usa 2 para todos.
  No son un plazo absoluto para toda la peticion: varias consultas pueden
  consumir presupuestos independientes.
- En SQLAlchemy 2.0.54 / asyncpg 0.31.0, el cierre ordenado tras un timeout
  puede quedar esperando la cancelacion de PostgreSQL si este esta pausado.
  El listener `handle_error` termina la conexion asyncpg sin esperar al servidor
  antes de la invalidacion de SQLAlchemy. La sesion tambien se invalida.
- No se usa `pool_pre_ping`: la primera consulta detecta una conexion obsoleta
  y puede devolver 503; la siguiente peticion puede recuperar una conexion nueva.
  No se reejecuta automaticamente una escritura para ocultar ese fallo.
- Nginx limita la conexion al upstream a 3 segundos y no prueba otro upstream.
  API detenida puede producir 502 (rechazo) o 504 (timeout de conexion), segun
  el comportamiento de red. No se cambian los timeouts de lectura/escritura.
- El frontend muestra el mismo mensaje para 502/503/504 y conserva el borrador
  y la sesion. El reintento de autenticacion existente tras 401 no se modifica;
  las respuestas de indisponibilidad no reintentan la escritura.

## Reproduccion

Desde la raiz del repositorio, con Docker, Node y Playwright/Chromium disponibles:

```bash
docker build --target test -t bayloncredit-api-training-test:latest backend
docker compose -p credify-resilience -f docker-compose.resilience.yml build frontend
docker compose -p credify-resilience -f docker-compose.resilience.yml up -d
node deploy/test-real-backend-failures.mjs /ruta/a/evidencias
```

El nombre de imagen backend es una dependencia local heredada; construirla con
`--target test` instala tambien pytest/Ruff. No entrena modelos. El Compose monta
el codigo backend y `nginx.conf` actuales; reiniciar API despues de editar Python.
Puerto unico publicado: `127.0.0.1:8093`.

Si Playwright esta instalado fuera del proyecto, definir `PLAYWRIGHT_MODULE_PATH`
con la ruta absoluta a su `index.mjs`. Instalar Chromium con ese Playwright.
El harness autentica una cuenta exclusiva del seed local, prepara el formulario
y usa `HTMLFormElement.requestSubmit()` con el handler React real. No demuestra
el recorrido fisico del clic en el boton Guardar.

Escenarios: BD detenida, BD pausada y API detenida. Para cada uno se comprueba
el error visible, los cinco campos rellenados, consentimiento, token conservado,
un solo POST observado y recuperacion explicita con HTTP 201. Una consulta SQL
real comprueba cero filas del intento fallido antes del reenvio y una despues.
Con BD no disponible tambien se comprueba live=200 y ready=503.
El `finally` reactiva los servicios alterados si la prueba falla.

El reporte `fallos-backend-reales.json` debe tener seis resultados aprobados.
Los tiempos medidos incluyen la respuesta y las comprobaciones del formulario;
no son un benchmark ni un SLA. Una ejecucion sobreescribe sus archivos; usar
otro directorio para conservar ejecuciones independientes.

Generacion opcional del Word, con `python-docx` instalado:

```bash
python deploy/report-backend-failures.py /ruta/a/evidencias
```

Se requiere ademas `verificaciones.json` con los resultados observados de la
suite y validadores. El generador se niega a publicar como completo un reporte
de fallos incompleto o fallido. Incluye hashes de las evidencias usadas.

Para detener solo este entorno sin borrar los datos/evidencias:

```bash
docker compose -p credify-resilience -f docker-compose.resilience.yml stop
```

## Limites

No demuestra disponibilidad de produccion, failover, carga concurrente,
particiones de red parciales ni aceptacion de usuarios. La prueba de rollback
tras flush es una integracion SQLite de la suite; los escenarios reales usan
PostgreSQL y verifican filas de clientes antes/despues. No se simula perdida de
respuesta despues de un commit confirmado. En ese caso el resultado puede ser
incierto: consultar el historial antes de reenviar. No hay garantia universal
de exactamente una vez, ni claves de idempotencia nuevas.

Estos cambios permanecen locales hasta un despliegue autorizado. Produccion
y demo publica no se detienen ni reciben los datos o cuentas de estas pruebas.
