# Traspaso A PROY - Grupo 2

## Empezar Aqui

1. Leer [Guia_Traspaso_PROY_Grupo2_Credify.docx](Guia_Traspaso_PROY_Grupo2_Credify.docx).
2. Revisar [materiales/APF3_TD_Grupo2_ML_Innovacion.ipynb](materiales/APF3_TD_Grupo2_ML_Innovacion.ipynb),
   el [script Python](materiales/APF3_TD_Grupo2_ML_Innovacion.py) y
   [sus requisitos](materiales/APF3_V6_Final_requirements.txt).
3. Leer el [complemento de la consigna](materiales/anexos/complemento-consigna.pdf)
   y el [indice del material APF3](materiales/README.md).
4. Confirmar en el Aula Virtual la consigna de PROY y el archivo efectivamente enviado.

La guia es un plan de trabajo, no una implementacion terminada. APF3 ya se envio:
sus resultados y fuentes se conservan; las mejoras corresponden a PROY.

## Materiales Disponibles

- `materiales/`: copia de los 166 archivos de contenido de `APF3_Grupo2.zip`,
  excluyendo exclusivamente metadatos Finder. Conserva bytes y rutas relativas.
- `paquetes/APF3_Grupo2.zip`: instantanea local original, sin cambios.
- `paquetes/APF3_Grupo2 (1).zip`: segunda variante local original, sin cambios.
- `Guia_Traspaso_PROY_Grupo2_Credify.docx`: guia detallada con prioridades,
  archivos, criterios de aceptacion, piloto, privacidad, pruebas y despliegue.
- `inventario-traspaso.json`: hashes de archivos publicados, procedencia y comparacion.

Los ZIP originales se conservan byte a byte y pueden contener metadatos de macOS.
No se extraen esos metadatos a `materiales/`. Esta copia facilita navegar en GitHub;
no es una afirmacion de que todos los pasos humanos de entrega esten certificados.

## Advertencia Sobre Las Dos Variantes

Los 166 archivos de contenido tienen las mismas rutas normalizadas: 164 son
identicos y solo cambian el informe PDF y la presentacion PPTX.

`APF3_Grupo2.zip` coincide con sus 165 entradas del manifiesto actual. En
`APF3_Grupo2 (1).zip`, los hashes del PDF y PPT no coinciden con ese manifiesto,
porque conserva el registro de los documentos anteriores. Esto no cambia sus
modelos ni datos, pero impide usar ese registro para certificar los documentos
modificados. No se alteraron los documentos ni se reescribieron hashes historicos.

La segunda variante tambien tiene una carpeta raiz doble. No inferir cual fue
enviada por su sufijo `(1)` o su fecha: confirmar el comprobante del Aula. Ambas
quedan publicadas como antecedentes identificados, no como entregas oficiales
certificadas. El inventario distingue esta advertencia de la integridad de copia.

## Limites Y Prioridades

Los datos de V6 Final son simulados. La SVM es apoyo experimental de revision,
no aprobacion automatica ni un modelo validado con clientes reales. El laboratorio
V6 no sustituye el motor transaccional: la guia explica las brechas de saldo
pendiente, excepciones, bloqueos concurrentes, contrato de features y cola real.

No ejecutar entrenamiento, migraciones, seed o despliegues contra produccion
por seguir este traspaso. Los controles pendientes de PROY se implementan y
prueban por separado. Nunca publicar `.env`, llaves, backups ni datos reales.

La reproduccion se probo localmente, no en una cuenta real de Colab. Las diferencias
de coma flotante quedan registradas. La revision humana del proyecto fue confirmada
por el grupo; el ensayo, la subida al Aula y la autorizacion de piloto no se infieren.
