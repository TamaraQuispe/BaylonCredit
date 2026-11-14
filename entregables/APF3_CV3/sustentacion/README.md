# Material de sustentación APF3 · Grupo 2

## Archivos principales

- `APF3_TD_Grupo2_ML_Innovacion.pptx`: 13 diapositivas editables, con notas por diapositiva.
- `APF3_TD_Grupo2_ML_Innovacion.pdf`: 13 páginas desde el mismo contenido/diseño.
- `APF3_Grupo2_Guion_12min.docx` y PDF: narración, acciones, demo y 12 preguntas difíciles.
- `APF3_Grupo2_Ficha_Calibracion_Meta.docx` y PDF: cinco bloques de consulta y validación,
  sin respuestas nuevas ni acuerdos atribuidos al propietario.
- `APF3_Ficha_Propietario_Baylon.docx` y PDF: versión solo para el propietario,
  con nueve preguntas y campos en blanco, sin apartados técnicos del equipo.
- `Guion_completo_con_indicaciones.md`: instrucciones ampliadas, contingencias y checklist.
- `vistas/` y `vista-general.png`: revisión visual de las 13 diapositivas.
- `evidencias/demo_inferencia_preparacion.json`: salida real de la prueba técnica de
  inferencia durante la preparación, no una ejecución ante el docente.

## Reparto propuesto

| Integrante | Tiempo planificado |
| --- | --- |
| Omara | 3 min 30 s |
| César | 3 min 10 s |
| Tamara | 2 min 50 s, incluidos 50 s de operación de inferencia |
| Pablo | 2 min 30 s |
| Total | 12 min, más 5 min de preguntas |

Los tiempos son una planificación, no un ensayo cronometrado. Los cuatro deben
poder explicar cualquier parte y confirmar o modificar el reparto. El texto
hablado tiene aproximadamente 1324 palabras; preguntas y acciones no se leen
dentro de los doce minutos.

## Demo

Desde la raíz del paquete, en el entorno compatible y con una salida nueva:

```bash
python codigo/scripts/academic_credit_grouped_cv.py --predict-artifact-dir experimento --input-json experimento/illustrative_input.json --output-json demo_inferencia_nueva.json
```

Se probó solo inferencia, sin entrenar ni consultar las filas finales. El resultado
es puntuación 0,4559958404, umbral 0,70 y predicción 0, con etiqueta desconocida.
No es garantía de cobro ni aprobación del fiado. La aplicación web sigue en v2.

Si falla la ejecución en vivo, declararlo y mostrar el JSON de respaldo como
resultado guardado. No pegar una salida anterior fingiendo una ejecución actual.

## Revisión necesaria

El PPTX es nativo y editable; su estructura y notas se verifican automáticamente.
El PDF y las vistas se renderizan offline desde el mismo contenido/diseño, no con
un motor nativo de PowerPoint. Abrir el PPTX en el editor que se usará para ensayar
y comprobar tipografías, saltos y legibilidad antes de exponer.

No se inventaron cifras de calibración, capacidad K, costos, meta numérica,
respuestas de entrevista ni revisiones individuales. Completar la ficha con fuente,
periodo, unidades y evidencia mínima, sin datos identificables de clientes.
Una meta nueva no cambia retrospectivamente el criterio de CV3.

El material mantiene visibles el bajo recall, el F2 superior de la referencia
siempre positiva y los límites de datos simulados. La preparación con IA no
equivale a revisión humana, aceptación del propietario o conformidad docente.
