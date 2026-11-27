# PROY SVM: cargador experimental y compatibilidad comprobada

## Estado

Se comprobo inferencia REAL del mismo artefacto, sin reentrenarlo ni tocar FINAL,
en el runtime registrado, en el candidato Linux/aarch64 y en un runner Linux/x86_64
real (GitHub Actions, sin emulacion). El `pyproject` admite `>=3.12,<3.15` para
que la tupla de referencia sea instalable; el CI sigue en 3.12.
El cargador acepta SOLO las tres combinaciones comprobadas:

| Entorno | Python | NumPy | Sistema / arquitectura |
| --- | --- | --- | --- |
| Referencia de entrenamiento | 3.14.6 | 2.5.5 | CPython / Darwin / arm64 |
| Candidato local de API | 3.12.14 | 2.5.3 | CPython / Linux / aarch64 |
| Servidor de staging | 3.12.14 | 2.5.3 | CPython / Linux / x86_64 |

Los tres: scikit-learn 1.9.1, joblib 1.6.0, SciPy 1.18.1 y threadpoolctl 3.7.0.
No se presume compatibilidad con otras versiones de Python, librerias,
arquitecturas o sistemas. La metadata conserva el runtime original; la comprobacion
se agrega separadamente, sin reescribir la procedencia. El probe x86_64 queda en
`docs/PROY_SVM_EVIDENCIAS/probe-x86_64.json` y su comparacion en
`docs/PROY_SVM_COMPATIBILIDAD_X86_64.json` (delta maximo 2.58e-14).

Esto permite avanzar en pruebas locales de integracion, NO habilita produccion
ni valida el modelo comercialmente. Ya existe una ruta experimental apagada por
defecto (ver abajo); el score antiguo y los laboratorios academicos siguen sin
conectarse al flujo transaccional.

## Identidad y procedencia

Fuente confiable: `academic/proy-p05`, materializada en
`entregables/PROY_Grupo2/materiales/experiment/p0-05`.
Version fuente: `proy-credit-experiment-v1`; version publicada: `credit-proy-svm-v1`.
`selected_model.joblib` y `svm.joblib` tienen SHA256
`f89db794fc657c3c0f858b1392e26474bc15577facd38ac49355b19a6834db45`.
El manifiesto fija `frozen_selection.json` en
`90548dcfc7562cf01a8175df99bd4884eee042c473b11818e7210afdec3d046c`.
La metadata publica conserva hashes del protocolo, procedencia y freeze,
runtime, orden de las 11 features, umbral 0.1 y autorizacion dev-only.
`research_only=true`, `business_approval=false`, `final_contacted=false`,
`final_test_evaluated=false`. No hay evaluacion final ni aprobacion comercial.

## Preparacion reproducible

Desde la raiz, con el directorio de destino ya existente:

```sh
python3 deploy/prepare-proy-svm-artifact.py
```

Opciones: `--source DIR --artifact-dir DIR`. Script stdlib, sin entrenamiento,
imports de la API, joblib ni deserializacion. Verifica hashes fijados en codigo,
manifiesto y freeze; copia los bytes y genera metadata determinista. Rechaza
destinos existentes y symlinks. No modifica la evidencia fuente. Para repetir,
usar otro directorio vacio existente, no sobrescribir el artefacto publicado.
La confianza depende de revisar el origen y los pins, no de que pickle sea seguro.

## Contrato de uso futuro

No hay carga ni inferencia PROY al importar este modulo. Solo una llamada explicita
a `predict_proy(snapshot, artifact_dir=None)` puede ejecutar el modelo. No se
modificaron rutas, configuracion, modelos historicos, features, outcomes ni main.
No existe fallback a modelos anteriores ni imports del laboratorio academico.

Advertencia: importar `app.ml` ejecuta su `__init__.py` historico, que carga el
modelo legado. Esa conducta preexistente queda intacta; no equivale a inferencia
PROY. Las pruebas verifican que la prediccion PROY no llama al predictor legado.

Cualquier saldo o conteo pendiente conocido bloquea antes del loader, incluso
con otros campos desconocidos. Sin historial pagado, campos nulos, tipos no
numericos, bools, negativos, no finitos, conteos fraccionarios o inconsistencias,
se devuelve revision sin probabilidad. Se valida ademas el contrato existente,
paid_late <= paid_credits y puntualidad consistente. requested_ratio debe ser
mayor que cero y como maximo uno.

Este modelo simulado solo admite completed_sales == paid_credits y
requested_ratio entre 5/80 y 50/80. Fuera de ese dominio devuelve
`unsupported_training_domain`, sin proyectar ni alterar features. Un fiado directo
real puede romper la igualdad legitimamente: esto no invalida el negocio,
solo impide inferir con este artefacto. S/80 no es un limite comercial.

El loader verifica archivos regulares sin symlinks, metadata e identidad fijadas,
SHA256 de bytes y runtime/arquitectura admitidos antes de joblib. La cache usa bytes verificados;
cada llamada vuelve a verificar archivos y runtime. Valida clases [0,1], 11
features y predict_proba; rechaza salidas distintas de 1x2, no finitas, fuera de
[0,1] o sin suma uno. Falla con `ProyModelUnavailable`, nunca con una probabilidad
inventada. La probabilidad cruda >=0.1 indica `MODEL_REVIEW_CANDIDATE`; por debajo
indica `BELOW_REVIEW_THRESHOLD`. Ambos requieren decision humana, nunca aprobacion.

## Verificacion

Los tests unitarios usan un estimador falso para gates, corrupcion, runtime,
metadata, interfaz, salida, cache y ausencia de fallback. Una prueba opt-in
`PROY_REAL_MODEL_TEST=1` usa ademas el SVM real a traves del cargador, verifica
el ejemplo, las compuertas, el hash y que no se use el predictor legado.
La prueba CLI del preparador necesita montar tambien `deploy`, `docs` y
`entregables` en solo lectura.

## Evidencia de compatibilidad

`deploy/verify-proy-svm-runtime.py` separa probes de inferencia y comparacion
stdlib. `docs/PROY_SVM_COMPATIBILIDAD.json` registra 534 vectores DEV conocidos
y un ejemplo adicional, con 535 clases exactamente iguales. La mayor diferencia
absoluta de probabilidad fue 2.19824158875781e-14, dentro de abs_tol=1e-12,
rel_tol=0. No se toleran cambios de clase, umbral, vector, orden o identidad.
No se calculan nuevas metricas de calidad ni se usa FINAL. Reutilizar DEV aqui
comprueba compatibilidad, no generalizacion ni otra validacion independiente.

Ejemplo: seis pagados, uno tardio, ratio solicitado 0.25 y antiguedad 180 dias.
Probabilidad referencia 0.13741099608146004; candidato 0.1374109960814624;
umbral 0.1, clase 1. No confundir este ejemplo con el anterior de 60 dias.

No hubo warnings; el hash del archivo y del CSV no cambio. La serializacion del
estado del modelo antes/despues fue identica dentro de cada entorno. Python y
NumPy variaron juntos, por lo que no se atribuye la diferencia a una sola causa.
Solo se permitio el `LabelEncoder.fit` interno de predict_proba calibrado sobre
las clases congeladas [0,1]; no ajusta SVM, preprocesamiento o calibracion.
El primer intento se detuvo por el guard generico de fit; se conserva su huella
y la causa instrumental en el registro. No fue un fallo predictivo del SVM.

SHA256 del registro de compatibilidad:
`3daed68193f3cd328949e3b2412646394f1a82b6580bc094665107422924aa30`.
El preparador y la metadata vinculan esta evidencia. Los probes completos estan en
`docs/PROY_SVM_EVIDENCIAS/`, con hashes fijados en el registro: la comparacion puede
reconstruirse sin inferencia. No se incluye entrenamiento ni acceso a BD.

## Endpoint experimental (solo demo de staging)

`POST /api/v1/proy-experimental/evaluations` con `client_id` y `amount`.

- Requiere autenticacion con rol ADMIN, OPERATOR o CREDIT; un VIEWER recibe 403.
- Doble candado: apagado por defecto (`PROY_EXPERIMENTAL_ENABLED=false`) y el
  validador de configuracion impide habilitarlo fuera de `staging`. Apagado o
  fuera de staging responde 404. En `docker-compose.staging.yml` la demo lo deja
  activado por defecto (`${PROY_EXPERIMENTAL_ENABLED:-true}`), siempre con
  autenticacion y solo en staging.
- Lee el historial real con `app/ml/features.py` (congelado). La compuerta de
  saldo pendiente vive en el cargador: con cualquier deuda pendiente responde sin
  cargar el artefacto ni calcular probabilidad. Si el snapshot cae en el dominio
  de entrenamiento, infiere con el SVM.
- Guarda la traza en `proy_experimental_evaluations` (decision, razon,
  probabilidad, umbral, snapshot, versiones). Es una tabla aparte: no escribe en
  `credit_evaluations`, no entra a la cola de revisiones y no crea ni aprueba
  fiados. La respuesta declara `research_only=true`, `business_approval=false` y
  `requires_human_decision=true`.
- Si el artefacto, el hash o el runtime no cuadran, responde 503 sin guardar una
  evaluacion inventada; no hay fallback al score antiguo.
- Fuera del dominio de entrenamiento el resultado queda en
  `REQUIRES_OWNER_REVIEW` (por ejemplo `no_paid_history` o
  `unsupported_training_domain`); no se fuerza una probabilidad.

La migracion `20261127_0018` crea la tabla y se comprobo con upgrade, downgrade y
nuevo upgrade en Postgres 17. Esto sigue siendo demostracion, no aprobacion
comercial ni via transaccional de produccion.

### E2E verificado contra Postgres (2026-11-27)

Se ejecuto la API real (`uvicorn`) contra PostgreSQL 17 migrado, con
`ENVIRONMENT=staging`, `PROY_EXPERIMENTAL_ENABLED=true` y la tupla de referencia
(CPython 3.14.6, Darwin arm64, NumPy 2.5.5, threadpoolctl 3.7.0). Un cliente
sembrado con una venta y un fiado ya pagado (S/ 80, sin deuda) solicito S/ 40:

- Snapshot leido de la base: `completed_sales=1`, `paid_credits=1`, `paid_late=0`,
  `outstanding=0`, `utilization=0`, `requested_ratio=0.2`, `punctuality_rate=1`,
  `overdue_rate=0`.
- SVM real, sin stub: probabilidad 0.106575, `predicted=1`,
  `MODEL_REVIEW_CANDIDATE`, `model_called=true`, umbral 0.1.
- Traza guardada en `proy_experimental_evaluations` con el mismo snapshot,
  versiones y umbral.
- Creditos antes/despues: 1/1; `credit_evaluations` y `credit_reviews`: 0/0.

### Runtime exacto de la demo

El endpoint sigue fallando cerrado (503) en cualquier runtime fuera de las tres
tuplas verificadas, aunque el flag este activo. Para la demo de staging:

- Imagen `deploy/proy-demo/Dockerfile`: base `python:3.12.14-slim-bookworm` con
  NumPy 2.5.3, scikit-learn 1.9.1, SciPy 1.18.1, joblib 1.6.0 y threadpoolctl
  3.7.0. En staging (Linux/amd64) compila y corre nativa; en arm64 tambien esta
  verificada. Tras instalar, el build ejecuta
  `deploy/proy-demo/check-runtime.py`, que carga el artefacto y compara la fila
  de control (0.13741099608146 +- 1e-9). Si el runtime no es apto, la imagen no
  se construye.
- Override `docker-compose.proy-demo.yml` (API con `platform: linux/amd64`); el
  comando de staging esta en el README.
- Cualquier entorno puede comprobarse con
  `python deploy/proy-demo/check-runtime.py`. En la tupla de referencia imprime
  `RUNTIME_OK credit-proy-svm-v1 prob=0.137410996081460` y en las imagenes Linux
  `...081462` (aarch64 y x86_64).
- `backend/pyproject.toml` acepta ahora `>=3.12,<3.15`, para que la tupla de
  referencia 3.14.6 sea instalable; el CI sigue fijado en 3.12.

E2E a traves de la imagen arm64: PostgreSQL 17, S/ 40, probabilidad 0.106575,
`MODEL_REVIEW_CANDIDATE`, traza persistida y creditos 1/1.

En x86_64, el job `e2e-postgres-x86_64` del workflow `PROY SVM x86_64` construye
la imagen nativa y repite el E2E completo contra un PostgreSQL 17 efimero:
migracion, seed ficticio, S/ 40 y probabilidad 0.1065748513407444, snapshot de
once variables calculado en el servidor y guardado, fila en
`proy_experimental_evaluations` con autor, y contadores sin cambios (54 fiados
antes y despues, cero `credit_evaluations` y cero `credit_reviews`). La evidencia
queda como artifact `proy-e2e-x86_64`.

#### Cobertura de arquitectura

Linux/amd64 (staging) y Linux/aarch64 estan verificados; otras arquitecturas
exigen su propio probe y anadir la tupla a la evidencia. La emulacion no cuenta
como verificacion de la arquitectura emulada.

## Dependencias para el siguiente incremento

Un despliegue API debera fijar y comprobar el tuple candidato, no depender de los
rangos amplios del pyproject. El registro solo comprueba la pila de inferencia;
no acredita el resto de FastAPI, SQLAlchemy o una peticion transaccional completa.
El servidor amd64 ya tiene su probe en un runner Linux x86_64 real y su
tupla quedo admitida; otras arquitecturas siguen necesitando su propia prueba
aislada o una publicacion entrenada/verificada para ese entorno. No deshabilitar esta
comprobacion para que el arranque pase ni sustituir el artefacto silenciosamente.
