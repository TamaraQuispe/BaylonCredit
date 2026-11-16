# Reglas Previas A La Prediccion V6

Las aclaraciones del propietario se aplican en la entrada CLI entregada y en el
laboratorio web V6, antes de deserializar o ejecutar el modelo. No se modifican
el runner academico congelado, los datos, los modelos ni las metricas FINAL.

| Condicion | Resultado | Ejecuta el modelo |
| --- | --- | --- |
| Cualquier indicador de saldo pendiente positivo | `blocked_pending_balance` | No |
| Deuda cero no confirmada o sin fiados pagados confirmados | `requires_owner_review` | No |
| Deuda cero confirmada e historial pagado | Comparacion experimental con el umbral | Si |

La deuda tiene prioridad, incluso con abonos, acuerdos o ausencia de historial.
En los casos sin modelo, probabilidad, umbral y prediccion son `null`; no son cero
ni una garantia de pago. El propietario debe revisar el primer fiado. El laboratorio
no concede excepciones, no asigna monto inicial y no crea creditos.

La politica comun esta en `backend/app/services/academic_v6_policy.py` y se entrega
como `v6_policy.py`. La CLI se conserva como fuente en
`deploy/templates/pending-v6-entrypoint.py`; el paquete incorpora ambos archivos
fuera de `codigo/` para preservar la cadena de evidencia congelada.

El laboratorio autenticado ofrece solo tres casos ficticios cerrados:
`illustrative-v6`, `pending-balance-v6` y `no-history-v6`. No acepta datos libres ni
consulta expedientes reales. La politica diaria con capacidad limitada sigue sin
aplicarse a una inferencia individual: `review_policy_applied=false` no significa
que se omitan estos controles previos.

## Verificacion

- 32 pruebas CLI, incluyendo Python aislado `-I`, deuda parcial/vigente/vencida,
  historial ausente o desconocido, prioridad, entradas invalidas y no sobrescritura.
- 165 pruebas del laboratorio backend, incluyendo ausencia de deserializacion
  en los casos bloqueados o derivados al propietario.
- Pruebas de interfaz con API simulada, roles y tamanos de escritorio/movil.
- Verificacion publica de los tres casos y navegador escritorio/movil.
- La CLI conserva la salida elegible exacta: `0.7171978005286032`, umbral `0.2`.
- Verificador CLI prueba ambos controles sin directorio de artefactos y conserva
  los hashes del experimento. No se ejecuta prediccion de la cohorte FINAL.

El despliegue de demo y su incidencia operativa estan registrados en
`deploy/review-pending-v6-policy-deployment.json`. No se cambiaron contenedores de
produccion. Durante recuperacion de un timeout se relanzaron accidentalmente las
tareas migrate/seed de demo; no se observaron cambios posteriores en registros de
negocio ni migraciones aplicadas, pero no hubo snapshot completo previo.

Estas reglas no validan la capacidad predictiva del arbol ni sustituyen un piloto
autorizado. Las metricas publicadas corresponden al experimento original, no a una
nueva evaluacion de esta capa. Revision grupal, ensayo y entrega humana pendientes.
