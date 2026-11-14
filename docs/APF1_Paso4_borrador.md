# APF1 — Paso 4: Entregables APF2 y APF3 + Vínculo normativo (Borrador)

**Proyecto:** Sistema de Scoring Crediticio Alternativo con IA para el fiado — Cervecería Baylón
**Grupo 2 / APF1:** Baylón Vila O., Coveñas Quispe T., Paredes Paredes C., Yman Avila P.
**Docente:** Camán Sánchez, Richard Enrique
**Base de esta sección:** código real desplegado en producción (no datos simulados).
Clave del proyecto: **capturar datos reales desde el día 1 y entrenar el modelo sobre esa captura** — nunca al revés.

---

## A. Delimitación de APF2 — MVP de captura de datos reales de fiado

### Objetivo
Tener operando, desde el primer día del bodega/BaylonCredit, el flujo por el que cada nuevo fiado **queda registrado de forma estructurada** (con score y explicación IA), reemplazando el cuaderno físico. Ningún valor se inventa: se captura lo real.

### Alcance funcional (ya implementado y desplegado)
Se toma como entregable la tabla `credit_evaluations` que ya corre en producción:

| Componente | Campo real en la tabla | Qué captura |
|---|---|---|
| Perfil del fiado | `client_id` → `clients` | quién es el cliente (datos reales, no simulados) |
| Monto del fiado | `requested_amount` | cuánto quiere fiarse |
| Scoring alternativo | `score`, `risk`, `default_probability`, `recommended_limit` | salida del modelo de reglas+IA |
| Decisión y límite | `approved`, `recommended_limit` | cuánto sí se le fía |
| Explicación IA | `ai_explanation`, `ai_risk_factors`, `ai_recommendations` | **por qué** ese score (3 factores + 2 recomendaciones) |
| Trazabilidad IA | `ai_status`, `ai_model`, `ai_generated_at` | cuándo/modelo con que se generó (marca de tiempo con Z) |
| Medición de performance | `response_time_ms` | cuánto tardó la decisión |

### No va en APF2 (queda fuera, explícito)
- Modelo de ML entrenado (eso es APF3).
- Integración con el sistema financiero formal regulado por la SBS (plataforma alternativa, no bancaria).
- Reemplazo del criterio del dueño: el sistema **potencia** el instinto del dueño (score + explicación), no lo sustituye.

### Regla de oro (responde a la observación del docente)
No existe el "plan B de datos simulados". Un modelo entrenado con datos inventados predice los sesgos de quien los inventó, no el comportamiento real de los fiadores. Por eso APF2 **primero** digitaliza la captura; el entrenamiento (APF3) usa exclusivamente esas evaluaciones reales.

### Captura desde el día 1 (evidencia en producción)
El API ya persiste, en cada evaluación, un score con `recommended_limit`, 3 `ai_risk_factors` y 2 `ai_recommendations`. Cada repetición de "Evaluación de crédito" en la UI agrega **un registro real** a la base de datos (la última: explicación IA visible, 290 caracteres, estado `completed`).

### ¿Cómo se enlaza WhatsApp? (canal de captura + consentimiento)
El canal WhatsApp del sistema sirve para **recolectar el consentimiento y las notificaciones** de los fiados en formato digital (eliminando el papel). Es un habilitador de APF2: facilita capturar el "sí/no fiado" real del dueño y los recordatorios de pago — vía que el propio profe señaló como necesaria para respetar la práctica cultural.

## B. Delimitación de APF3 — Modelo de scoring entrenado con datos reales

### Objetivo
Entrenar el modelo de probabilidad de impago usando **30–50 evaluaciones reales** capturadas por la aplicación (APF2), no simuladas, y **comparar la predicción contra lo que realmente pasó** con el fiado.

### Alcance
1. **Dataset:** mínimo 30–50 registros `credit_evaluations` reales (los que la app capture en semanas de uso en el local).
2. **Label/desenlace:** el `pending_amount` de cada fiado y su `status` (al corriente / atrasado / impago) — se observa en la vida real, no se inventa.
3. **Features (las mismas que la IA ya usa, del schema):** `requested_amount`, `score`, `risk`, `default_probability` y los `ai_risk_factors` textuales.
4. **Modelo:** clasificador (scikit-learn, ya elegido en el stack) entrenado sobre esas features.
5. **Validadón real (métrica de ingeniería — la única válida):** comparar la predicción del modelo contra el desenlace real observado del fiado. Presentar el CSV predicción vs. resultado real.

### Entregable
- Artefacto del modelo (`model.pt` / `.joblib`) más el script `backend/scripts/train_credit_model.py` (ya existe en el repo).
- Reporte de métricas: exactitud y separación del scoring (accuracy / AUC) sobre los 30–50 casos reales.
- Comparación de **lo que la IA recomendó y lo que pasó en la realidad**, mostrando la viabilidad económica al dueño con números propios del negocio.

### Qué queda explícitamente fuera de APF3
- Entrenar con datos comprados o inventados (prohibido por diseño).
- Prometer "predicción" sin haber digitalizado antes la captura (eso sería el error señalado: un juguete que predice sus propios sesgos).

---

## C. Vínculo normativo (leyes peruanas aplicables)

### C.1 Ley 29733 — Protección de Datos Personales (y su Reglamento D.S. 003-2013-JUS)
La app trata datos personales de los clientes (quiénes deben y cuánto). Obligaciones que el sistema ya contempla o debe contemplar:
- **Consentimiento previo, informado, expreso e inequívoco** del titular antes de registrar y tratar sus datos (Ley 29733, art. 5; art. 14). Capture: bitácora/consentimiento digital (por UI y, en el flujo, por WhatsApp).
- **Finalidad determinada**: el uso exclusivo es el scoring del fiado, no la venta ni otros usos (art. 6).
- **Seguridad y confidencialidad**: almacenamiento cifrado y acceso restringido (art. 9-11; D.S. 003-2013-JUS, título III).
- **Derechos del titular**: acceso, rectificación, cancelación y oposición (art. 18 — ARCO), facilitables desde la UI.

### C.2 Ley MYPE — Ley 28015 (+ mod. Ley 30056)
Define a la **micro y pequeña empresa** (identificador tributario omitido en esta copia pública) y su promoción. El sistema es una **plataforma alternativa de financiamiento al fiado**, complementaria (no regulada por la SBS), que se alinea con la Ley MYPE al formalizar y dar soporte a MYPE peruanas. También se alinea con la **Ley 30056** (simplificación y promoción de MYPE).

### C.3 Reglas de riesgo crediticio de la SBS (aplicables si el sistema se integra a la formalidad)
- **Reglamento para la Evaluación y Clasificación del Deudor y la Exigencia de Provisiones** (Res. SBS 11356-2008 y modificatorias): la metodología de scoring alternativo debe ser **homologable y auditable** (se documenta score, factores y explicación — el schema ya persiste los tres).
- Si se incorpora el sistema a una entidad supervisada: **Reglamento de Crédito Directo y/o Indirecto** con exposición máxima al cliente y límites de concentración.

> Discreción con el RUC/nombre completo de los clientes fuera del contexto del proyecto: los datos personales citados en este documento se refieren solo a las tablas y modelos del sistema, no a datos de personas naturales en texto libre.

## D. Plan de trabajo APF2/APF3 (vínculo con el cronograma)

| Entregable | Responsable | Semáforo en notas | Qué mide |
|---|---|---|---|
| APF2 captura real de fiado funcionando en el local | Grupo 2 | Verificado en producción | Registros reales por semana |
| APF2 canal WhatsApp (consentimiento + recordatorios) | Grupo 2 | Por habilitar (necesita credencial Meta) | Fiados digitalizados |
| APF3 modelo entrenado sobre ≥30–50 evaluaciones reales | Grupo 2 | No iniciado | accuracy/AUC vs desenlace real |
| APF3 comparación predicción vs. resultado real | Grupo 2 | No iniciado | % acierto sobre la realidad |
| Vinculación normativa 29733 / 28015 / SBS | Grupo 2 | Este documento | Cobertura de requisitos |

**Cierre (toma de nota del docente):**
- "Primero digitaliza, después predice" — requisito ya adoptado: el sistema no entrena sobre datos simulados; entrena sobre las evaluaciones reales que el propio local genera.
- Con esto, en APF3 podrán presentar un modelo comparado contra la realidad (métrica de ingeniería), y el dueño verá viabilidad económica con números reales de su bodega, no con un "sistema bancario frío" que reemplace su instinto.
