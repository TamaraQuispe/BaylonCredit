# APF3 · Comparación agrupada v3

Experimento académico nuevo sobre registros ficticios de Cervecería Baylón.
El protocolo se conserva en `experimento/protocol.json`, la selección previa al
test en `experimento/frozen_selection.json` y los resultados en
`experimento/grouped_cv_report.json`. No se usan los tests ya consultados para
seleccionar. No es una validación del negocio ni autoriza créditos reales.

Los parámetros de simulación aún necesitan calibración con una fuente verificable.
F2 y el piso de precisión de 0,50 son supuestos técnicos de investigación, no costos,
capacidad o metas aprobadas por el propietario. Conservar resultados desfavorables.

## Resultado

Se eligió mediante CV un árbol balanceado de profundidad 3, hoja mínima 16 y
umbral 0,70. En el final obtuvo precisión 0,56250, recall 0,11905, F1 0,19651,
F2 0,14133 y accuracy 0,65704. Detectó 45 de 378 atrasos y omitió 333.
La SVM no emitió alertas en ese final. No es un modelo listo para uso operativo.

El Dummy siempre positivo tiene F2 0,73114, mayor que el árbol, pero precisión
0,35228, por debajo del piso técnico. La elección no demuestra superioridad
universal ni reducción de pérdidas. El 95 % de Doña Rosa no corresponde a Baylón.

## Archivos

- `informe/`: Word, PDF y Markdown actualizados, figuras y revisión de páginas.
- `codigo/`: runner de comparación e inferencia y módulos compartidos necesarios.
- `datos/`: CSV con origen simulado y libro original requerido por su hash.
- `experimento/`: evidencia inmutable de la corrida analítica, modelos y predicciones.
- `reproduccion/`: repetición del protocolo fijo en un entorno sin bibliotecas
  heredadas y sin red al ejecutarlo; todas las métricas coincidieron exactamente.
- `sustentacion/`: PPT de 13 diapositivas, PDF, guion de 12 minutos, preguntas
  de preparación y ficha editable de calibración/meta con campos pendientes.

El paquete académico incluye una inicialización `app.ml` mínima para evitar
cargar el modelo legado de la aplicación. Los archivos de cálculo de features,
simulador, etiquetas y runner conservan los hashes de la corrida analítica.
Se importan esquemas SQLAlchemy para compartir el contrato; no se abre ninguna
sesión ni conexión a base de datos. No se incluye configuración de producción.

## Reproducción

Desde esta carpeta, con Python 3.12 y un entorno virtual nuevo:

```bash
python -m pip install -r requirements.txt
python codigo/scripts/academic_credit_grouped_cv.py --source datos/ledger_desarrollo_original.json --protocol experimento/protocol.json --output-dir salida_repro_nueva
```

La salida debe ser una carpeta nueva o vacía. No sobrescribir `experimento`.
Repetir este protocolo cerrado verifica reproducibilidad; no constituye otra
validación independiente ni autoriza ajustar parámetros con el test publicado.

Solo inferencia, sin entrenar ni generar clientes:

```bash
python codigo/scripts/academic_credit_grouped_cv.py --predict-artifact-dir experimento --input-json experimento/illustrative_input.json --output-json prediccion_nueva.json
```

La predicción ilustrativa es 0 con puntuación 0,45599584 y umbral 0,70. No tiene
etiqueta conocida ni significa aprobación de crédito. Solo cargar artefactos
Joblib de procedencia confiable; el hash verifica integridad, no autenticidad.

La demo web sigue en v2. No hubo despliegue ni sustitución del modelo operativo.
Siguen pendientes calibración cuantitativa, meta y costos de negocio, controles
normativos, revisión humana y ensayo de la presentación. El ZIP y el informe son evidencia
técnica, no aceptación del propietario ni de los integrantes.
