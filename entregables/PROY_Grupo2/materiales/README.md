# V6 Final

Revision prospectiva `v6-final-r1`. Datos 100 % simulados; no uso comercial.

La ejecucion V6 anterior permanece sin cambios. Esta revision aplica ambas reglas
del propietario antes del modelo: bloqueo por saldo pendiente y revision humana
sin fiados pagados. Bloqueos y revisiones no se cuentan como aciertos del modelo.

El protocolo y los hashes se fijan antes de generar nuevos datos DEV. La prueba
FINAL nueva solo se genera tras congelar seleccion y modelos. No hay ajuste de
semillas, datos o modelo en funcion de los resultados finales.

La ejecucion autorizada esta concluida y congelada en `experiment/`. La seleccion
OOF eligio SVM con umbral `0.1`. FINAL tiene 277 elegibles, 275 etiquetas conocidas
y 2 desconocidas. La matriz RAW SVM es `[[166, 68], [9, 32]]`, precision `0.32`,
recall `0.7804878048780488`, F1 `0.45390070921985815`, F2 `0.6060606060606061`
y accuracy `0.72`. No se selecciono ni ajusto el modelo usando FINAL.

## Estado De Entrega

El informe y la presentacion conservan su contenido, con los nombres formales
solicitados por la consigna. La evidencia faltante se completa separadamente en
[anexos/complemento-consigna.pdf](anexos/complemento-consigna.pdf): estadisticas DEV,
dos relaciones descriptivas, criterio tecnico predeclarado, meta futura propuesta,
hipotesis de errores y siete comprobaciones nuevas de las reglas previas.

La verificacion de esta carpeta es `verificacion-entrega-actual.json`, con el
inventario `manifiesto-entrega-actual.json`. El archivo `verificacion-v6-final.json`
y `support/manifest-support.json` se conservan como registros HISTORICOS del paquete
anterior: sus estados de revision y sus hashes documentales no certifican los
documentos actuales ni deben confundirse con su estado presente.

El manifiesto congelado no contiene scores TRAIN por fila: `training_reports.json`
guarda agregados. Se comprobaron sus vinculos, matrices, precision, recall, F1, F2,
accuracy derivadas de confusion y consistencia agregada de colas. La reconstruccion
TRAIN por score y de su cola queda `not_available`: es una limitacion de cobertura,
no un bloqueo de publicacion de los resultados OOF/FINAL reconstruidos.
ROC AUC y Brier, incluidos los de TRAIN, son valores de fuente verificada por hash,
no recalculados. No se infiere, modifica evidencia ni inventa un cache TRAIN.

La verificacion bloqueada anterior se conserva bajo `support/history/` como historia;
no representa un bloqueo actual. No se ha generado un ZIP nuevo de esta carpeta.

El experimento publicado permanece congelado. El script/notebook de entrada si
realiza una nueva ejecucion del MISMO procedimiento para comprobar reproducibilidad,
con salida separada y sin modificar `experiment/` ni `development/`. Repetir las
semillas no constituye una nueva validacion independiente. Los complementos EDA
son descriptivos y posteriores al congelamiento; no se retoco la seleccion del modelo.

## Contenido

- `datos/`: CSV de desarrollo, desarrollo etiquetado y FINAL; historiales completos,
  diccionario de 24 columnas, conteos y hashes. Son copias verificadas, no datos nuevos.
- `informe/APF3_TD_Grupo2_ML_Innovacion.pdf`: 22 paginas totales, 15 de cuerpo.
- `sustentacion/APF3_TD_Grupo2_ML_Innovacion.pptx`: 13 diapositivas con notas.
- `APF3_TD_Grupo2_ML_Innovacion.py` y `.ipynb`: entrada ejecutable, entrenamiento,
  comparacion, exportacion, inferencia y cuatro graficos DEV obligatorios.
- `APF3_V6_Final_requirements.txt`: dependencias de esa entrada; runtime ML y
  matplotlib aislados, sin reemplazar paquetes del kernel.
- `anexos/`: complemento PDF/Markdown, estadisticas, graficos, hipotesis, reglas
  y trazabilidad de sus calculos; `anexos/ejecucion-codigo/` contiene evidencia local.
- `codigo-base/`: copia exacta de los 21 archivos del codepack inmutable anterior.
- `revision/`: runner final y politica congelados, sin cambios.
- `sources/`: protocolo final, cuatro fuentes heredadas y resultados documentados.
- `tools/`: verificador stdlib, pruebas, generadores y harness de reproduccion futura.
- `ejemplos/`: tres entradas manuales ilustrativas y expectativas, no nuevas inferencias.
- `support/`: manifiesto de soporte y copia sanitizada del registro de despliegue.
- `REPRODUCCION.md`: ejecucion y limites. `Dockerfile` y `requirements.txt`
  conservan la receta original de entrenamiento/inferencia; no son las dependencias
  del generador de anexos ni del verificador documental.
- `tools/completar_anexos.py`: recalcula solo anexos, sin entrenamiento.
- `tools/verificar_entrega_actual.py`: verifica hashes, CSV, documentos y notebook.

## Despliegue Y Limites

El registro publico existente declara despliegue y verificacion satisfactorios de
la demo academica sintetica. No se despliega ni se modifica nada durante esta
finalizacion. Solo la probabilidad ilustrativa admite `abs_tol=1e-12, rel_tol=0`:
valor congelado `0.15310676521820216`, API `0.15310676521820044`, diferencia
`1.7208456881689926e-15`. No es igualdad numerica exacta. Modelos, clase, umbral,
metricas y hashes siguen siendo exactos; esa tolerancia no se extiende a ellos.

La revision humana del proyecto fue realizada por los cuatro integrantes, segun
confirmacion del grupo. Los anexos recien incorporados requieren su cotejo final.
El ensayo cronometrado, la ejecucion en una cuenta real de Colab y la subida al Aula
Virtual no se acreditan mediante esta preparacion tecnica. No hay autorizacion
comercial ni validacion predictiva con clientes reales.
