# Laboratorio Academico V4: tooling de demo

Esta revision prepara un bundle local de investigacion sintetica para la demo,
no autoriza un despliegue ni acredita validacion predictiva con clientes reales.
Las imagenes API/frontend se construyeron y se probaron en una pila local
efimera independiente. No se ha actualizado la demo publica ni produccion.
No modificar el paquete de evidencia extraido ni su ZIP.

## Preparacion local

Desde la raiz del repositorio, con Python 3.12 o posterior y solo stdlib:

```sh
python3 deploy/test-prepare-aligned-v4-lab.py -v
ruff check --config backend/pyproject.toml deploy/prepare-aligned-v4-lab.py deploy/test-prepare-aligned-v4-lab.py
python3 deploy/prepare-aligned-v4-lab.py --source /Users/tamaraalison/Downloads/APF3_Grupo2_Alineado_V4 --destination ./academic/v4
git check-ignore academic/v4/web_manifest.json
```

`academic/` ya esta ignorado por Git y por el contexto Docker. El preparador
valida todo antes de crear el destino, exige un directorio nuevo y nunca
sobrescribe, ni siquiera un directorio vacio. Rechaza symlinks en archivos,
directorios y ancestros de origen/destino. Usar rutas locales de confianza,
sin procesos concurrentes que sustituyan directorios durante la preparacion.
Para repetir la preparacion, elegir otro destino nuevo; no borrar evidencia.

Comprueba los 24 SHA256 de `manifest-paquete.json:experiment_sha256`, los hashes
congelados de `artifact_manifest.json` y `frozen_selection.json`, y su coherencia
con reporte, seleccion, procedencia, runtime y protocolo. Exige SVM con umbral
0.1, `research_only=true`, `business_approval=false` en el reporte y el ejemplo
exacto del protocolo: solicitud PEN 20, cap PEN 80. La seleccion no contiene un
campo `business_approval`; el reporte es el contrato de esa prohibicion.

Copia byte por byte solo estos cinco archivos de `experimento/`:

- `aligned_v4_report.json`
- `frozen_selection.json`
- `selected_model.joblib`
- `illustrative_input.json`
- `provenance.json`

Agrega unicamente `web_manifest.json` con `version=academic-owner-aligned-v4`
y `files` con los cinco nombres exactos y sus SHA256. El resumen de controles
sale por stdout, no se escriben logs, checks ni otros archivos dentro del bundle.
No importa joblib, no deserializa modelos y no ejecuta inferencia o entrenamiento.
Los hashes detectan corrupcion, no autentican a un publicador hostil. Joblib
puede ejecutar codigo al cargarse en runtime: solo se admite el paquete de
confianza revisado, nunca artefactos enviados por usuarios.

## Configuracion De Demo

Solo combinar con `docker-compose.demo.yml`, nunca con compose de produccion.
Para validar sin leer archivos de entorno ni imprimir configuracion o secretos,
usar un valor ficticio exclusivamente para interpolacion:

```sh
JWT_SECRET_KEY=configuration-check-only docker compose --env-file /dev/null -f docker-compose.demo.yml -f docker-compose.academic-v4.yml config --quiet
```

Para validar posteriormente con el entorno privado de demo ya provisionado, sin mostrarlo:

```sh
docker compose --env-file .env.demo -f docker-compose.demo.yml -f docker-compose.academic-v4.yml config --quiet
```

No ejecutar `config` sin `--quiet`, ni publicar archivos de entorno. El preparador
no crea, lee ni modifica secretos. No aplicar cambios al servidor sin autorizacion.
El override conserva los limites, dependencias, autenticacion y roles existentes.
No concede permisos nuevos: los endpoints V4 usan el usuario autenticado
existente y solo estan habilitados en staging.

El bind `./academic/v4:/app/academic-v4` es de solo lectura y usa
`create_host_path: false`: un bundle ausente no se transforma silenciosamente en
un directorio vacio. Solo la API recibe ese bind. V4 habilita su flag de backend
y el build arg `VITE_ACADEMIC_ML_V4=true`; el Dockerfile de frontend mantiene
`false` por defecto. V2 se preserva sin cambios y no se habilita por este override.
Solo si se desea expresamente combinar ambos laboratorios se agrega primero
`docker-compose.academic-lab.yml`, y al final el override V4; se conservan entonces
el flag y el mount de V2, con las imagenes V4 como resultado final.

## Imagenes Y Arranque

Construir en una maquina con recursos, **no en la VM de 1 GB**. Las imagenes
se construyeron localmente mediante `docker build`; estos comandos Compose y
de exportacion son referencias para una publicacion posterior, no ejecutada:

```sh
docker compose --env-file .env.demo -f docker-compose.demo.yml -f docker-compose.academic-v4.yml build api frontend
docker image save -o /tmp/credify-academic-v4-images.tar credify-demo-academic-api:v4 credify-demo-academic-frontend:v4
```

La imagen API independiente usa Python `3.12.14-slim`, usuario no root y
`pip install -c /tmp/requirements-academic-v4.txt .`. Las restricciones ML de
demo estan separadas de produccion: sklearn 1.9.1, numpy 2.5.3, scipy 1.18.1,
joblib 1.6.0 y threadpoolctl 3.7.0. Si el registro no ofrece estas versiones,
el build debe fallar, no sustituir versiones. El runtime valida las versiones
contra provenance; la construccion local y el smoke de la imagen final pasaron.
Conserva app, pyproject, alembic y los dos scripts operativos que ya copia
`backend/Dockerfile`; no copia runners de experimentos academicos, tests ni
datasets. OMP y OpenBLAS quedan limitados a un hilo.

Transferir las imagenes y los seis archivos del bundle por un canal privado,
preservando hashes y permisos de lectura del usuario no root. Revisar memoria,
salud y autorizacion antes de cualquier arranque posterior en el servidor. Las
migraciones y el seed se probaron solo en la base efimera del test local.

## Alcance Y Rollback

Las metricas FINAL provienen del reporte congelado/cacheado. No se vuelven a
inferir cohortes FINAL ni a ajustar modelos o umbrales. La unica evaluacion web
es un ejemplo sintetico nuevo sin etiqueta conocida, no un cliente real ni una
aprobacion de credito. Su umbral individual no aplica la politica de cola top-5.
No actualiza scores, creditos ni notificaciones y no admite datos reales de entrada.

Ante bundle corrupto, runtime incompatible o fallo de carga/inferencia, los
endpoints existentes devuelven 503 sin exponer detalles. Deshabilitado o fuera
de staging devuelve 404. El preparador no carga el modelo, por lo que no prueba
su deserializacion ni el funcionamiento de los endpoints.

Rollback: establecer `ACADEMIC_ML_V4_ENABLED=false` en la configuracion efectiva
y reconstruir el frontend con `VITE_ACADEMIC_ML_V4=false` en la maquina de build.
No basta cambiar una variable en un contenedor frontend ya construido. Retirar
este override tambien restaura la configuracion base de demo; si V2 estaba
habilitado, conservar su override e imagen previamente verificada. Comprobar
siempre con `config --quiet` antes de aplicar cambios. No eliminar el paquete
de evidencia ni alterar la configuracion productiva para hacer rollback.

## Verificacion Local Realizada

Se ejecuto `deploy/smoke-aligned-v4-api.py` contra `./academic/v4` preparado,
con la imagen existente `bayloncredit-api-training-test:latest`, sin construir
imagenes ni desplegar servicios. Esta verificacion posterior no cambia las
restricciones de despliegue descritas arriba.

Comando ejecutado desde la raiz (las variables solo abrevian rutas locales):

```sh
SMOKE_DIR=/var/folders/sx/_6ljw37n2_j9hk2f_vtqplj40000gn/T/opencode/v4-api-smoke
docker run --name bayloncredit-v4-api-smoke-local \
  --network none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=128m \
  --cap-drop ALL --security-opt no-new-privileges --user app \
  --mount "type=bind,src=$PWD/backend,dst=/app,readonly" \
  --mount "type=bind,src=$PWD/academic/v4,dst=/bundle,readonly" \
  --mount "type=bind,src=$HOME/Downloads/APF3_Grupo2_Alineado_V4/experimento,dst=/evidence,readonly" \
  --mount "type=bind,src=$PWD/deploy,dst=/tools,readonly" \
  --env OMP_NUM_THREADS=1 --env OPENBLAS_NUM_THREADS=1 \
  bayloncredit-api-training-test:latest \
  python /tools/smoke-aligned-v4-api.py --bundle /bundle \
  --evidence-dir /evidence --output /tmp/v4-api-smoke.json > "$SMOKE_DIR/result.json"
docker wait bayloncredit-v4-api-smoke-local
```

El directorio temporal se creo tras verificar su padre. `result.json` conserva
las respuestas, contadores y snapshots SHA256; `container.json` conserva la
inspeccion de aislamiento, mounts, imagen, exit code y OOM. No se escribio en el
bundle ni en el paquete original. El JSON interno en `/tmp` es efimero; stdout
se capturo en el host sin agregar mounts escribibles.

Resultados observados:

- `status=passed`, exit code Docker **0**, `OOMKilled=false`, usuario `app` (UID 999).
- Runtime real: Python **3.12.14**, sklearn **1.9.1**, numpy **2.5.3**, scipy
  **1.18.1**, joblib **1.6.0**; no se sustituyo la comprobacion de versiones.
- **22 peticiones** mediante `httpx.ASGITransport` a la app y rutas registradas
  del backend montado, no a una app de prueba ni al paquete antiguo de la imagen.
- JWT real creado por `create_access_token`, secreto efimero generado en memoria
  y nunca impreso. Sin override de `get_current_user`: anonimo y token invalido
  devuelven 401 en las tres rutas; usuario inactivo tambien devuelve 401.
- Unico override: `get_db` con fixture de identidad solo lectura, usuario ficticio
  `UserRole.OPERATOR`; **16** llamadas `get(User, id)`, **0** acciones prohibidas.
  Se bloquearon metodos de sesion, SQL mediante eventos de `Engine`, funciones
  de negocio y entrenamiento. **No se uso una DB real**, externa ni local.
- Summary y cases devuelven 200 con **0 cargas joblib y 0 inferencias**. Resumen
  congelado: FINAL conocido **259**, matriz SVM raw `[[80,114],[4,61]]`, politica
  constant-1 F2 **0.622568093385214**, **255** revisiones.
- Exactamente **1 carga joblib real** desde bytes verificados y **1 llamada real
  a predict_proba**, limitada al vector congelado de `illustrative-v4`. Score
  exacto **0.11922453881690649**, umbral **0.1**, prediccion **1**, etiqueta real
  `null`, `review_policy_applied=false`; coincide con `illustrative_output.json`
  original. No se entreno, no se importo el runner y no se infirio FINAL.
- Caso desconocido y `FINAL-L1`: 404. JSON, texto, multipart y query arbitrarios:
  422 sin lectura de bundle ni ML. Flag deshabilitado: 404 en las tres rutas sin
  lectura de bundle. Hash corrupto simulado en memoria y runtime incompatible
  simulado: 503 antes de deserializar, sin modificar archivos originales.
- Los seis hashes SHA256 del bundle son exactamente iguales antes y despues.
- Pico RSS del proceso Python: **206324 KiB** (aprox. **201.5 MiB**), medido con
  `resource.getrusage(RUSAGE_SELF).ru_maxrss` en Linux. No es memoria total del
  contenedor, ni de servicios desplegados, ni una prueba de capacidad de la VM.
- Ruff del script con `backend/pyproject.toml`, dentro de la misma imagen
  aislada: **All checks passed!**

Esto es un smoke local ASGI de autenticacion y runtime real con identidad
ficticia. **No es E2E humano**, prueba de navegador, conexion DB real, aprobacion
crediticia, validacion con clientes reales ni certificacion de un despliegue.
No se modificaron backend, frontend ni Dockerfiles durante esta verificacion.

## Verificacion De Las Imagenes Finales

Se construyeron localmente `credify-demo-academic-api:v4` y
`credify-demo-academic-frontend:v4`. La imagen final API tambien paso el smoke
ASGI anterior, sin montar el backend del checkout, con limite de 256 MiB,
sin red y con artefactos de solo lectura. El score coincidio exactamente;
el pico RSS observado fue 208724 KiB, no una garantia de capacidad.

`deploy/test-aligned-v4-stack.mjs` probo ambas imagenes en una red Docker interna
nueva con PostgreSQL 17 efimero en tmpfs, migraciones, seed y login reales.
Las contrasenas y JWT solo existieron en memoria; no se usaron credenciales
del servidor ni se modificaron los contenedores locales anteriores.

```sh
PLAYWRIGHT_MODULE_PATH=/ruta/local/playwright/index.mjs node deploy/test-aligned-v4-stack.mjs
```

El script valida las imagenes existentes y elimina exclusivamente sus propios
contenedores y red al terminar. Como Docker no asigno el puerto publicado a
la red interna, se uso un tunel TCP loopback hacia Nginx real mediante
`docker exec nc`, sin simular las APIs ni habilitar acceso externo.

- Navegador real: escritorio y movil, login como docente con rol operator.
- Las tres rutas V4 rechazaron consultas anonimas con 401.
- DEV 552 y FINAL 259 conocidos, cuatro modelos, raw/policy separados.
- Dos inferencias, exclusivamente del ejemplo sin etiqueta: score 11.9 %,
  umbral 10 %, etiqueta null, sin cola top-5 ni aprobacion comercial.
- Antes/despues: cero creditos y evaluaciones comerciales, tres clientes
  ficticios del seed y cero pagos. Ningun POST comercial.
- Bundle intacto y de solo lectura. Sin OOM; muestra de memoria API 160.9 MiB,
  frontend 8.77 MiB y PostgreSQL 80.26 MiB, bajo sus limites de 256/32/128 MiB.
- Recursos externos bloqueados: las capturas no acreditan carga de la fuente
  remota de iconos. No es un ensayo humano ni una prueba de carga sostenida.

Evidencia local de esa ejecucion:
`/var/folders/sx/_6ljw37n2_j9hk2f_vtqplj40000gn/T/opencode/v4-stack-check/credify-v4-check-1794709952020-9aaf9d76/`.
Contiene `evidence.json`, `desktop.png` y `mobile.png`.

Controles adicionales: 359 tests backend, 14 del preparador, Ruff y ESLint
aprobados. Las pruebas de navegador con API simulada tambien cubren los flags
activo/inactivo, errores, reintento manual, cancelacion y doble clic.

El build de frontend notifico vulnerabilidades preexistentes del lockfile:
`npm audit --omit=dev --audit-level=high` reporto dos moderadas asociadas a
React Router, sin altas en dependencias de runtime. La auditoria completa del
build reporto 14 (11 moderadas y tres altas, incluyendo desarrollo). No se
aplico `npm audit fix --force`: propone cambiar de version mayor de Router y
requiere una actualizacion separada con pruebas de regresion.

La activacion publica de demo sigue pendiente. Produccion, los paquetes
academicos congelados, V2 y las reglas comerciales no se sustituyeron.
