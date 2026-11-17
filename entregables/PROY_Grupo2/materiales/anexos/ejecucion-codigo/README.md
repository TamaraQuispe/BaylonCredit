# Evidencia De Ejecucion Local

Resumen de una ejecucion completa del procedimiento fijo V6 Final con Python
3.12.14 y dependencias aisladas. No se uso el FINAL publicado para entrenar.
Las tablas y modelos de experiment/ originales se conservan sin modificar.

registro-ejecucion.json verifica la cadena del run y los archivos aqui copiados.
Familia, parametros, umbral y metricas de clasificacion TRAIN/OOF/FINAL coinciden.
published_comparison.json conserva diferencias numericas de scores agregados,
incluido Brier; no se afirma igualdad binaria entre plataformas.
El campo selection_matches del comparador historico compara todo el registro OOF,
incluidos valores Brier sensibles a redondeo. El registro-ejecucion.json distingue
la igualdad de familia, parametros y umbral de la igualdad numerica completa.

No se adjunta el arbol completo del replay ni se presenta como nueva validacion
independiente. El codigo principal permite repetir el procedimiento en salida nueva.
No acredita acceso a una cuenta Colab, ensayo ni entrega en Aula Virtual.
