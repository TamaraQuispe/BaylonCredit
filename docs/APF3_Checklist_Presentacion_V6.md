# APF3 Grupo 2: Revision Y Presentacion V6

**Estado:** preparacion tecnica comprobada; revision individual, ensayo y entrega al Aula Virtual pendientes. No atribuye contribuciones pasadas ni conformidad del grupo.

## Localizar La Entrega

- Informe: `informe/APF3_TD_Grupo2_ML_Innovacion.pdf` y `.docx`; 15 paginas de cuerpo, 33 totales.
- Presentacion: `sustentacion/APF3_TD_Grupo2_ML_Innovacion.pptx`; PDF y guion incluido.
- Codigo academico: `APF3_TD_Grupo2_ML_Innovacion.py`, `codigo/` y `requirements.txt`.
- Datos simulados: `datos/*.csv`; diccionario y auditoria en `anexos/datos/`.
- Integracion: CLI raiz en `codigo/` y laboratorio V6 en la demo autenticada [Laboratorio V6](https://demo-credify.168-75-71-113.sslip.io/laboratorio-academico/v6). Es sintetico y no produccion.
- Entregar por Aula Virtual; hacer referencia a la demo, no publicar datos ni credenciales privadas en el paquete.

## Controles Tecnicos Ya Comprobados

- [x] 545 filas de estudio DEV, 541 conocidas, 454 puntuales y 87 atrasadas; cuatro desconocidas. 280 filas FINAL, 276 conocidas, 243 puntuales, 33 atrasadas y cuatro desconocidas.
- [x] Ningun fiado otorgado con saldo previo pendiente. Regla confirmada: cualquier deuda vigente impide nuevo fiado hasta cancelar todo.
- [x] Arbol, SVM y dos referencias evaluados bajo protocolo congelado; SVM gana final pero se conserva el arbol seleccionado por OOF.
- [x] Reproduccion: 12 metricas brutas/policy exactas, 5 Joblib identicos y ejemplo ilustrativo reproducido.
- [x] Wrapper CLI raiz probado: score 0.7171978005286032, umbral 0.2, clase 1, etiqueta desconocida, sin aprobacion.
- [x] Latencia local declarada: 30 llamadas, mediana 154.03 ms y p95 177.40 ms. No incluye HTTP, base, autenticacion ni concurrencia.

Estas marcas son verificaciones automaticas, no revisiones individuales.

## Revision Individual Autentica

| Integrante | Codigo | Alcance revisado | Hallazgo / correccion y evidencia | Fecha real |
| --- | --- | --- | --- | --- |
| Omara Yamileth Baylon Vila | U23231338 | PENDIENTE | PENDIENTE | PENDIENTE |
| Tamara Alison Coveñas Quispe | U23204737 | PENDIENTE | PENDIENTE | PENDIENTE |
| César Augusto Daniel Paredes Paredes | U23259768 | PENDIENTE | PENDIENTE | PENDIENTE |
| Pablo Enrique Yman Avila | U23251279 | PENDIENTE | PENDIENTE | PENDIENTE |

- [ ] Contrastar fuente, datos, metricas, limitaciones y conclusiones asistidos por IA.
- [ ] Explicar diferencia entre pagos puntuales/tardios, abonos observados y etiqueta desconocida.
- [ ] Defender por que no se cambio a SVM despues de ver FINAL.
- [ ] Explicar la baja precision del arbol: 162 falsos positivos y cuatro omisiones.
- [ ] Verificar normativa para uso real; el documento privado no debe incluirse.
- [ ] Confirmar que todos entienden que esto no aprueba ni rechaza creditos.

## Preparar La Maquina De Exposicion

- [ ] Elegir responsable principal y suplente para ejecutar la demostracion.
- [ ] Probar `python APF3_TD_Grupo2_ML_Innovacion.py --predict-artifact-dir experimento --input-json experimento/illustrative_input.json --output-json /tmp/demo-v6-NUEVA.json`.
- [ ] Usar una salida nueva y verificar que el archivo aparece y no contiene etiqueta conocida ni aprobacion.
- [ ] Tener preparado el respaldo guardado y rotularlo como ejecucion anterior si falla la demo.
- [ ] Preparar diapositivas y abrir PPTX en la aplicacion que se usara en clase.

## Ensayo Real

- [ ] Ejecutar los 13 bloques con los cuatro expositores y cronometrar 12 minutos.
- [ ] Reservar 50 segundos de operacion en la demo.
- [ ] Ensayar preguntas fuera del bloque de cada integrante.

| Intento | Fecha real | Duracion | Demo | Correcciones / responsable |
| --- | --- | --- | --- | --- |
| 1 | PENDIENTE | PENDIENTE | PENDIENTE | PENDIENTE |
| 2 | PENDIENTE | PENDIENTE | PENDIENTE | PENDIENTE |

## Entrega Y Acceso

- [ ] Subir informe, codigo, presentacion y anexos antes de la sesion de semana 15.
- [ ] Comprobar descarga del ZIP y acceso del docente.
- [ ] Guardar constancia real de entrega.
- [ ] No publicar ficha privada, contactos, bases ni credenciales.
- [ ] Declarar la ausencia o limitacion del historial completo de IA si no puede recuperarse.

No se afirma cumplimiento integral hasta cerrar la revision humana y el acceso docente. La activacion de V6 en produccion, el consenso legal del negocio y la aprobacion de clientes no son requisitos documentales de esta entrega academica, pero si condiciones antes de operar con datos reales.
