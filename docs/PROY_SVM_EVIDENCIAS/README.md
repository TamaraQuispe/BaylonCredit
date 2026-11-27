# Probes Reales De Compatibilidad

Estos JSON son las salidas originales de `deploy/verify-proy-svm-runtime.py probe`,
no fixtures de los tests. Solo se ejecuto inferencia sobre 534 vectores sinteticos
DEV y un ejemplo manual de 180 dias de antiguedad. No hubo ajuste ni acceso a FINAL.

- `ref-probe-v2.json`: CPython 3.14.6, Darwin arm64, NumPy 2.5.5.
- `candidate-probe-v2.json`: CPython 3.12.14, Linux aarch64, NumPy 2.5.3.

Sus SHA-256 estan fijados en `../PROY_SVM_COMPATIBILIDAD.json`. Ambos conservan los
vectores, scores, runtime y hashes de estado antes/despues. La comparacion es pura
y puede repetirse sin cargar un modelo. El comando exige un destino nuevo:

```sh
python3 deploy/verify-proy-svm-runtime.py compare --reference docs/PROY_SVM_EVIDENCIAS/ref-probe-v2.json --candidate docs/PROY_SVM_EVIDENCIAS/candidate-probe-v2.json --output-json /ruta/nueva/comparacion.json
```

La comprobacion de llamadas Python es instrumentacion, no un sandbox contra
pickle malicioso. Solo se cargo un artefacto local de confianza con hash fijado.
La excepcion de LabelEncoder codifica [0,1] durante predict_proba; los hashes de
estado confirman que no se modifico el modelo. `fit_calls=0` se refiere a ajuste
del modelo, preprocesamiento y calibracion, no a esa codificacion interna.

No acredita servidores x86_64, otras combinaciones, peticiones de la API, seguridad
comercial ni una nueva validacion predictiva. La autorizacion de produccion sigue
siendo falsa. Estas pruebas no sustituyen una nueva evaluacion final de PROY.
