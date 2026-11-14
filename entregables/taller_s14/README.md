# Taller S14B resuelto: Bodega Doña Rosa

Archivo para abrir en Google Colab: **S14A_TallerML_Grupo2_Colab.ipynb**.
Se conserva el prefijo S14A solicitado en el Paso 0 del PDF, aunque la actividad
se titula sesión B. La versión original del notebook no se modifica.

## Contenido

- CSV exacto de 160 clientes incrustado; ocho predictores y etiqueta del taller.
- Pasos 0–9, cuatro modelos, gráficos, tablas de los tres retos y respuestas Registra.
- Dependencias fijadas y comprobaciones de concordancia entre salidas y respuestas.
- Conclusión basada en resultados y transferencia específica a Cervecería Baylón.
- Datos simulados, sin conexión a producción o a la demo del proyecto.

La selección del taller es AdaBoost con 50 rondas: accuracy 0.950 y precision,
recall y F1 de 0.917. SVM empata en esas métricas. El árbol es más interpretable,
pero genera siete falsos positivos frente a uno de AdaBoost en esta partición.
No debe elegirse el árbol antes de comparar ni extrapolar estos resultados a Baylón.

El umbral 0.5 produce 12 alertas; el cupo se respeta ordenando y atendiendo hasta
diez. El top 10 incluye nueve clientes con etiqueta de atraso: precision@10=90 %,
recall@10=75 %. La etiqueta conocida solo evalúa la simulación, no ordena llamadas.

## Antes de enviar

1. Confirmar la pareja participante: el taller pide dos personas; se consignó el
   grupo de cuatro del proyecto porque no se indicó la pareja autorizada.
2. Revisar nombres y códigos ya incorporados: Tamara U23204737, Omara U23231338,
   César Daniel U23259768 y Pablo U23251279. Comprender las respuestas: la asistencia
   de IA no equivale a revisión de los integrantes.
3. En Colab: Archivo → Subir notebook; abrir el .ipynb. En una sesión nueva con
   Python 3.11–3.13 (verificado en 3.12), ejecutar todas las celdas. La primera
   instala las dependencias si faltan; no es necesario subir el requirements.txt.
4. Guardar en Drive y compartir como Cualquier usuario que tenga el vínculo → Lector.
5. Probar el enlace en incógnito, enviarlo por UTPCLASS y confirmar el estado Enviado.

No se puede generar el enlace de Drive ni enviar a UTPCLASS sin la cuenta del grupo.
El PDF exige un enlace compartible, no únicamente el archivo adjunto.

## Transferencia y límites

En Doña Rosa, moroso significa más de siete días de retraso. En Baylón,
late_payment significa atraso desde el vencimiento contractual del fiado a un día.
La usuaria confirmó registros ficticios: 30–50 fiados reales era una meta del piloto,
no una muestra disponible. Se replica el método, no el dataset ni el modelo entrenado.

El taller consulta repetidamente prueba para retos y decisión; es exploratorio.
En APF3, elegir hiperparámetros y umbrales con validación dentro de entrenamiento,
separar por cliente/tiempo cuando corresponda y reservar test final independiente.
No reutilizar la cohorte final ya consultada de v2 para ajustar otro modelo.

El supuesto de S/ 150 por falso negativo es didáctico; atraso no implica pérdida
definitiva. Las puntuaciones no tienen calibración real demostrada. La ética descrita
es un plan de control, no una certificación de ausencia de sesgos o acoso en llamadas.

`verificacion-ejecucion.json` contiene versiones, conteos, métricas y hashes de la
ejecución técnica, no una aceptación humana. La preparación se realiza mediante
`deploy/solve-s14-workshop.py` en el repositorio.
