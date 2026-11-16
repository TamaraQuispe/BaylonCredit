# Machine Learning para priorizar la revision del fiado a un dia

## Cerveceria Baylon | Credify | APF3 Grupo 2

Universidad Tecnologica del Peru. Facultad de Ingenieria de Sistemas e Informatica.

Caso 4: Scoring crediticio alternativo con IA para el fiado y microcredito MYPE.

| Integrante | Codigo |
| --- | --- |
| Omara Yamileth Baylón Vila | U23231338 |
| Tamara Alison Coveñas Quispe | U23204737 |
| César Augusto Daniel Paredes Paredes | U23259768 |
| Pablo Enrique Yman Avila | U23251279 |

Docente: Caman Sanchez, Richard Enrique. Seccion 35036. Periodo 2026-2. Lima, Peru.

**Edicion documental V6:** 2026-11-16T15:26:29.283697+00:00. Datos simulados. Revision humana grupal pendiente.

**Ejecucion experimental conservada:** 2026-11-16T00:32:09.208779+00:00. Esta fecha no es la de edicion ni una nueva validacion independiente.

Informe sustentado en evidencia congelada, sin nuevas llamadas al modelo. La demo V6 esta publicada y autenticada; los artefactos y codigo se entregan localmente. No se publican fuentes privadas ni firmas.

<!-- PAGE -->

# 1. Resumen ejecutivo y problema ML

## Continuidad APF1 y APF2

Cerveceria Baylon, negocio familiar de San Martin de Porres operado por dos propietarios, administra fiados a un dia. APF1 identifico registro manual y ausencia de evaluacion sistematica; APF2 construyo Credify con clientes, evaluacion por reglas, fiados, abonos e historial (React, FastAPI, PostgreSQL). Se conservan equipo, empresa, problema e indicadores de cobertura de registro y evaluacion. Lean Startup orienta construir-medir-aprender y Kanban organiza el trabajo (Ries, 2011; Anderson, 2010). La URL heredada es https://demo-credify.168-75-71-113.sslip.io; su laboratorio V6 esta disponible con datos sinteticos y acceso autenticado. El acceso docente corresponde al usuario `docente@example.com`; no es una cuenta de produccion ni acredita aceptacion comercial.

La brecha sigue siendo el historial real elegible: APF2 documento cero filas exportables al cierre, no ausencia de operaciones. El 5 % mensual declarado es perdida estimada/ventas del mes, no atraso ni probabilidad; no calibra el modelo. No se consulto la base real actual.

## Formulacion y criterio de exito

**Para el propietario, el modelo clasificara el atraso de un fiado a un dia con el proposito de priorizar revision humana. F2 de politica es el criterio tecnico academico; la meta de menor tiempo exige comparar la carga medida antes y despues, registrando FN y FP.** Cada fila es un fiado otorgado, no una persona independiente. `late_payment=1` significa atraso contractual, no perdida permanente; 0 significa liquidacion completa hasta vencimiento inclusive. Sin desenlace suficiente, la etiqueta queda desconocida.

Se estudia clasificacion binaria supervisada, coherente con el contrato de APF2. La accion prevista es mostrar candidato a REVIEW en evaluacion crediticia, nunca aprobar automaticamente. Cualquier saldo previo positivo impide nuevo fiado; liquidarlo solo restablece elegibilidad para evaluar.

El equipo priorizo cualitativamente evitar atrasos omitidos (FN), reconociendo el costo de falsas alertas (FP). F2 pondera recall; beta=2 es decision academica, no costo monetario medido ni preferencia aprobada por el propietario. El arbol gano por F2 OOF de politica; la superioridad final de SVM no cambia la seleccion. El resultado permite estudiar una cola de revision, no demostrar ahorro ni confianza crediticia real.

**Baseline declarado por Rildo, por memoria y no cronometrado.** En una semana normal atiende alrededor de 14 solicitudes; otorga unos 12 fiados a 9 clientes y rechaza cerca de 2, generalmente por deuda pendiente. Revisar una solicitud le toma aproximadamente entre 1 y 3 minutos segun conozca al cliente y la deuda; calcula unos 25-35 minutos semanales en total. Resumen sanitizado: [anexos/datos/rildo-baseline.json](../anexos/datos/rildo-baseline.json). Esta es una aproximacion autoinformada, no una medicion con cronometro. La meta propuesta debe comparar esta referencia con el piloto; cinco revisiones/dia y dos minutos/caso no son una referencia validada.

<!-- PAGE -->

# 2. Dataset, coherencia y preprocesamiento

## 2.1. Trazabilidad del contrato

Fuente primaria: APF2 original, Tabla 17, pagina fisica 10/impresa 9, y Anexo B.4, fisica 20/impresa 19 (Grupo 2, 2026). El flujo cliente > evaluacion > fiado > pagos genera snapshots y desenlaces. Se declara el cambio de fuente real prevista a simulacion academica, sin afirmar captura real ni autorizacion docente adicional.

| Campo/elemento APF2 | Fuente prevista | Aplicacion/cambio V6 |
| --- | --- | --- |
| 11 variables de snapshot | credit_evaluations.feature_snapshot | Mismo esquema numerico; eventos simulados |
| completed_sales | Ventas completadas del MVP | V6 solo ventas ligadas a credito; igual a paid_credits, no ventas al contado |
| paid_credits; paid_late | Creditos y pagos previos | Solo liquidaciones observadas estrictamente antes de evaluar |
| pending_overdue/current; outstanding; utilization; overdue_rate | Saldos/activos | Cinco constantes cero por elegibilidad V6; no fabricar variacion |
| requested_ratio; tenure_days; punctuality_rate | Solicitud, alta e historial | Monto/80; dias; proporcion historica. Cupo y altas ficticios |
| late_payment | Vencimiento y pagos | Mismo atraso contractual, no defaulted; desconocidos separados |
| Fuente/volumen | 30-50 fiados reales en 4-6 semanas | 0 elegibles al cierre APF2; DEV 545 estudio/541 conocidos; no sustituye piloto |
| 12 a 24 columnas | 11 variables + target APF2 | 12 metadatos agregados para origen, fechas y trazabilidad, excluidos del modelo |
| Particion | APF2 preveia temporal o por cliente | CV agrupada por cliente y FINAL disjunto; no validacion temporal prospectiva |

El diccionario completo de las 24 columnas, tipos, unidades, dominios y nulos esta en Anexo A y `anexos/datos/diccionario-v6.json`. Se conservan las once entradas del contrato; los campos de escenario, saldo al corte, fechas e identificadores nunca alimentan el aprendizaje.

<!-- PAGE -->

## 2.2. Origen, escala y simulacion congelada

Todas las filas llevan `origen=simulado`. DEV son dos historias alternativas: 545 fiados de estudio, 541 conocidos (454/87), cuatro desconocidos, 24 clientes ficticios y 91 fiados de calentamiento. FINAL es una tercera historia: 280 de estudio, 276 conocidos (243/33), cuatro desconocidos, 12 clientes y 46 de calentamiento. No se suman como volumen real ni como sucursales simultaneas.

| Historia | Clientes | Warmup | Estudio | Conocidos 0/1 | Desconocidos |
| --- | --- | --- | --- | --- | --- |
| PND6-D1 | 12 | 45 | 273 | 225/46 | 2 |
| PND6-D2 | 12 | 46 | 272 | 229/41 | 2 |
| PND6-T | 12 | 46 | 280 | 243/33 | 4 |

Despues de ver la demo, el propietario indico que Credify tiene potencial y que el ejercicio academico es razonable, pero que antes de utilizarlo necesitaria mas pruebas y comprobar que funcione correctamente. Resumen: [anexos/normativa-ia/rildo-aceptacion-parcial-v6.json](../anexos/normativa-ia/rildo-aceptacion-parcial-v6.json). Esto solo describe interes y aceptacion parcial. La respuesta posterior endurecio el alcance: es una autorizacion prospectiva, condicionada a pruebas adicionales y confiabilidad. Resumen: [autorizacion condicionada sanitizada](../anexos/normativa-ia/rildo-autorizacion-condicionada-v6.json).

Rildo tambien declaro el baseline semanal anterior y reviso 23 elementos intencionales V5 (12 fiados, cuatro rechazos, cuatro semanas y tres supuestos), no todas las filas V6 ni el modelo. Su aclaracion impide nuevo fiado con **cualquier saldo positivo**, incluso vigente; abono o acuerdo no bastan y la liquidacion debe observarse antes de evaluar. La fuente revisada ya esta recibida; no se exige repetir aprobacion para describir la variacion semanal derivada. Revision de fuente no equivale a validacion grupal ni aceptacion global.

Los agregados base proceden de recuerdo y revision parcial de cuaderno: 48 anotaciones, 45 evaluables, ocho tardias y tres desconocidas; no son filas de entrenamiento. La referencia usual de 12 fiados/9 clientes admite variacion. Doce clientes forman un grupo de ejemplo con rotacion, no una poblacion real fija.

El protocolo de datos conserva lognormal truncada de montos S/5..50 (localizacion S/20, sigma 0.45), cupo S/80, heterogeneidad Beta (concentracion 3), abonos con probabilidad supuesta 10/48, fraccion 0.5 y atrasos de 1..15 dias. La mezcla 75 % redondeado a soles/.50 y 25 % precio exacto es **supuesto del equipo**, no frecuencia declarada; precios exactos estan permitidos. Pagos variados en 08:00..12:00 y 16:00..20:00; corte duro 20:00 es supuesto del equipo. Gracia de tres dias no convierte atraso en puntualidad. Los planes finitos de liquidacion no estiman perdida permanente.

Semillas y distribuciones completas estan en `experimento/data_protocol.json` y `protocol.json`; FINAL usa 2026111901 tras congelar seleccion. Este generador documental no simula datos.

<!-- PAGE -->

## 2.3. Ficha de coherencia: siete criterios de la consigna

| Criterio | Verificacion | Evidencia y resultado |
| --- | --- | --- |
| Escala del negocio | Referencia habitual aproximada: 12 fiados / 9 clientes por semana completa | Medias por cada una de las 24 semanas completas: ; PND6-D1: 11.208 fiados / 8.750 clientes; PND6-D2: 11.208 fiados / 8.917 clientes; T: 11.500 fiados / 8.833 clientes |
| Rangos y unidades | Montos 5..50 PEN; cupo 80; ratios 0..1 | Tres historias: hard_constraints_pass=true; detalle DEV en anexo |
| Consistencia logica y temporal | Saldo previo bloquea; pagos anteriores; no sobrepago | 0 otorgamientos con pendiente en D1, D2 y T; hard pass en las tres |
| Relaciones plausibles | Historia de atraso/target y antiguedad/ventas | Dos relaciones DEV conocido, Figura 2; no EDA de desenlaces FINAL |
| Señal ni nula ni perfecta | Contrastar Dummy y auditar fuga | F2 OOF arbol 0.59757943; accuracy 0.55268022, no separacion perfecta |
| Coherencia con APF2 | Campos y cambios explicitos | 11 entradas preservadas; ventas restringidas a credito; fuente simulada |
| Mezcla real + simulado | Comparacion por origen | No aplica: 100 % simulado, cero filas reales |

**Limpieza reconstruida solo en DEV conocido (n=541).** Nulos por columna: 0; duplicados por loan_id excedentes: 0; vectores repetidos excedentes: 1. Los vectores iguales no se borran automaticamente: pueden ser fiados distintos del mismo historial. Cuatro etiquetas desconocidas DEV no se imputan ni puntuan; si compiten en cola.

Se calcularon cercas IQR 1.5 por variable; los extremos se retienen al ser valores plausibles y limitados por reglas, no errores probados. No se recorta la distribucion para mejorar resultados. Anexo B incluye conteos, rangos, cuartiles y decision por columna.

Los hard pass son controles tecnicos: integridad, rangos, reglas y temporalidad. `coherence_accepted=false` no significa datos incoherentes; significa que no existe aceptacion del propietario sobre todas las filas V6 ni validacion de rendimiento real. Rildo reviso y corrigio una muestra intencional; ese aporte valida reglas y plausibilidad, no convierte las 545 observaciones en datos auditados negocio por negocio. La escala de otorgamientos puede ser menor a la solicitud tipica por bloqueo de pendientes. Se preserva la advertencia de escala heredada, sin regenerar ni ajustar semillas.

<!-- PAGE -->

## 2.4. EDA de desarrollo: balance y estadisticos

![Figura 1. Balance en DEV conocido: 454 puntuales y 87 atrasos; cuatro etiquetas inmaduras fuera de metricas.](figuras/balance-v6.png)

| Variable | Min | Q1 | Media | Q3 | Max |
| --- | --- | --- | --- | --- | --- |
| requested_amount | 5.500 | 14.610 | 21.237 | 26.750 | 50.000 |
| paid_credits | 2.000 | 9.000 | 14.645 | 20.000 | 28.000 |
| paid_late | 0.000 | 0.000 | 2.213 | 4.000 | 15.000 |
| tenure_days | 56.000 | 153.000 | 202.721 | 251.000 | 360.000 |
| punctuality_rate | 0.000 | 0.727 | 0.836 | 1.000 | 1.000 |

El atraso representa 87/541 = 16.0813 % de las observaciones DEV conocidas. El desbalance hace inadecuado usar solo accuracy: Dummy mayoritario no detecta atrasos. Se comparan precision, recall, F1 y F2; class_weight y umbrales fueron predeclarados. No se aplica sobremuestreo. Los estadisticos describen transacciones sinteticas repetidas, no una muestra independiente de personas.

La elegibilidad produce cinco entradas constantemente cero y `completed_sales == paid_credits`. Se mantienen para respetar el contrato, pero no se atribuye capacidad explicativa a la deuda ni importancia independiente a variables duplicadas.

<!-- PAGE -->

## 2.5. Dos relaciones esperadas del negocio

![Figura 2. Historia de atraso frente a atraso actual y antiguedad frente a ventas de credito; solo DEV conocido.](figuras/relaciones-v6.png)

| Historia previa | n | Atrasos actuales | Proporcion |
| --- | --- | --- | --- |
| Sin atraso previo | 253 | 10 | 0.03952569 |
| Con atraso previo | 288 | 77 | 0.26736111 |

| Banda predefinida (dias) | n | Media ventas completadas |
| --- | --- | --- |
| 30..119 | 62 | 6.67741935 |
| 120..239 | 318 | 13.36163522 |
| >=240 | 161 | 20.24844720 |

**Interpretacion.** Se espera que antecedentes tardios contengan señal de comportamiento futuro, sin determinarlo: ambos grupos pueden fallar o cumplir. El grafico cuantifica esa asociacion dentro del simulador, no causalidad ni validez externa. Una mayor antiguedad permite acumular ventas completadas, pero la rotacion y los bloqueos tambien influyen. Las bandas 30..119, 120..239 y >=240 fueron fijadas para describir DEV, no optimizadas con FINAL.

Se usan antecedentes ya observados, nunca pagos futuros del propio fiado. Estas dos relaciones complementan el balance y justifican explorar historial y antiguedad; no permiten recomendar variar deuda pendiente ni inventar ventas al contado.

<!-- PAGE -->

# 3. Modelado y comparacion

## 3.1. Preparacion y prevencion de fuga

Se conserva un Pipeline fresco por pliegue: `SimpleImputer(strategy=median)` y `StandardScaler`, tambien para Dummy y arbol; SVM lo requiere por su margen. Las once variables son numericas, por lo que no hay codificacion categorica ni one-hot. Origen, ID y fechas son metadatos. La mediana y el escalado se ajustan exclusivamente en entrenamiento conocido, nunca con FINAL o etiquetas desconocidas. Una entrada de entrenamiento completamente ausente detiene la ejecucion.

`punctuality_rate=(paid_credits-paid_late)/paid_credits` es una variable derivada interpretable; sin denominador vale cero por convencion, no por puntualidad demostrada. `requested_ratio=monto/80` normaliza la solicitud. Los snapshots preceden al otorgamiento; se excluyen target, pagos futuros, escenario, saldo al corte, propension latente y scores previos. La lista congelada no se cambia despues de OOF/FINAL.

## 3.2. Particion y comparabilidad

StratifiedGroupKFold agrupa por client_id, con tres pliegues externos e internos guardados; semillas externas 2026111801 e internas 2026111802. Las validaciones externas tienen 182, 179 y 180 filas conocidas (minoritarias 29, 30 y 28); cada cliente queda en un solo lado. No es una division 80/20: entrenamiento externo contiene 359, 362 y 361 filas. Se reutiliza el plan exacto, sin buscar semillas por resultados.

Los desconocidos se asignan al pliegue del cliente, compiten por capacidad y no calibran ni entran a metricas. FINAL mantiene IDs disjuntos y se genero solo despues de congelar modelo y umbral. Hubo un lote por familia sobre 280 filas; el analisis documental solo reutiliza sus resultados guardados.

## 3.3. Modelos de Unidad 3

Arbol de decision: reglas explicables y limites de profundidad/hoja para un conjunto pequeño. SVM lineal: margen regularizado, con calibracion sigmoid interna por grupos (`ensemble=false`); no usa `probability=true`. Dos Dummy comparables: mayoritario y constante 1. Todos comparten filas, pliegues, transformacion y politica de capacidad. El escalado tambien se conserva en el arbol para igualdad del procedimiento, no por necesidad matematica.

El estudio evalua nuevos clientes sinteticos del mismo simulador; no certifica generalizacion temporal ni real. Filas repetidas no son 541 personas independientes.

<!-- PAGE -->

## 3.4. Busqueda congelada y sobreajuste

Grilla arbol: profundidad {2,3,4}, hoja minima {8,16}, peso {None,balanced}: 12 configuraciones. SVM: C={0.1,1,10}, peso {None,balanced}, kernel lineal: seis. Siete umbrales {0.1,...,0.7} producen 126 pares configuracion-umbral. Dummy usa 0.5. Se maximiza F2 OOF de politica; desempates: recall, precision, F1, menos revisiones, orden declarado de grilla, cercania a 0.5 y menor umbral. No se exigio precision minima.

**Gano arbol, candidato indice 9, profundidad 4, hoja 8, balanced, random_state=42, umbral 0.2.** F2 OOF de politica 0.59757943 frente a SVM 0.59654631 (C=1, balanced, umbral 0.1). La diferencia es pequeña; no implica superioridad estadistica.

| Modelo RAW | Particion | Precision | Recall | F1 | F2 | Accuracy |
| --- | --- | --- | --- | --- | --- | --- |
| Arbol seleccionado | train | 0.24576271 | 1.00000000 | 0.39455782 | 0.61965812 | 0.50646950 |
| Arbol seleccionado | oof | 0.25239617 | 0.90804598 | 0.39500000 | 0.59757943 | 0.55268022 |
| SVM | train | 0.31250000 | 0.86206897 | 0.45871560 | 0.63775510 | 0.67282810 |
| SVM | oof | 0.26297578 | 0.87356322 | 0.40425532 | 0.59654631 | 0.58595194 |
| Dummy mayoritario | train | 0.00000000 | 0.00000000 | 0.00000000 | 0.00000000 | 0.83918669 |
| Dummy mayoritario | oof | 0.00000000 | 0.00000000 | 0.00000000 | 0.00000000 | 0.83918669 |
| Dummy constante 1 | train | 0.16081331 | 1.00000000 | 0.27707006 | 0.48931384 | 0.16081331 |
| Dummy constante 1 | oof | 0.16081331 | 1.00000000 | 0.27707006 | 0.48931384 | 0.16081331 |

Caida F2 RAW train-OOF del arbol: 0.02207869; OOF-FINAL: 0.14866302. Profundidad y hoja limitadas reducen complejidad; no eliminan optimismo. En SVM, C regulariza y la calibracion usa particiones internas del entrenamiento.

OOF se reutilizo para elegir configuracion y umbral: su ganador es optimista; calibracion interna no equivale a evaluacion anidada independiente de hiperparametros. El deterioro FINAL se reporta sin reseleccion ni nuevos ajustes.

<!-- PAGE -->

# 4. Evaluacion e interpretacion de negocio

## 4.1. Resultados RAW en FINAL intacto

| Modelo RAW | Particion | Precision | Recall | F1 | F2 | Accuracy |
| --- | --- | --- | --- | --- | --- | --- |
| Arbol seleccionado | final | 0.15183246 | 0.87878788 | 0.25892857 | 0.44891641 | 0.39855072 |
| SVM | final | 0.23214286 | 0.78787879 | 0.35862069 | 0.53278689 | 0.66304348 |
| Dummy mayoritario | final | 0.00000000 | 0.00000000 | 0.00000000 | 0.00000000 | 0.88043478 |
| Dummy constante 1 | final | 0.11956522 | 1.00000000 | 0.21359223 | 0.40441176 | 0.11956522 |

Metricas en 276 etiquetas conocidas; clase positiva=atraso. Precision indefinida usa zero_division=0. Cuatro desconocidos no se convierten en puntuales.

![Figura 3. Matriz FINAL del arbol: real por filas y predicho por columnas, orden 0/1.](figuras/matriz-v6.png)

El arbol detecta 29/33 atrasos (recall 0.87878788), omite cuatro y produce 162 FP, con 81 TN. Precision 0.15183246 y accuracy 0.39855072 reflejan carga alta de falsas alertas. La SVM obtiene mejor F2 FINAL (0.53278689), pero **no se selecciona con el test**. Dummy mayoritario logra accuracy 0.88043478 con F2=0: demuestra por que accuracy no basta. Los 33 atrasos satisfacen el minimo orientativo de 30, no suficiencia para validar personas reales ni intervalos independientes.

<!-- PAGE -->

## 4.2. Politica operativa y comparacion con revisar todo

Primero umbral, luego score descendente e ID ficticio como desempate, maximo cinco por replica y fecha civil Lima. Dos minutos por caso y capacidad cinco/dia son estimaciones, no tiempos observados. La cola cubre fiados otorgados simulados, no toda solicitud, cobranza o trabajo obligatorio.

| Modelo POLICY | Particion | Precision | Recall | F1 | F2 | Accuracy |
| --- | --- | --- | --- | --- | --- | --- |
| Arbol seleccionado | final | 0.15183246 | 0.87878788 | 0.25892857 | 0.44891641 | 0.39855072 |
| SVM | final | 0.23214286 | 0.78787879 | 0.35862069 | 0.53278689 | 0.66304348 |
| Dummy mayoritario | final | 0.00000000 | 0.00000000 | 0.00000000 | 0.00000000 | 0.88043478 |
| Dummy constante 1 | final | 0.12087912 | 1.00000000 | 0.21568627 | 0.40740741 | 0.13043478 |

| Modelo COLA | Particion | Total | Conocidas | Sin etiqueta | Max/dia | Dias sobre antes | Min supuestos | TN/FP/FN/TP |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Arbol seleccionado | final | 193 | 191 | 2 | 5 | 0 | 386 | 81 / 162 / 4 / 29 |
| SVM | final | 115 | 112 | 3 | 4 | 0 | 230 | 157 / 86 / 7 / 26 |
| Dummy mayoritario | final | 0 | 0 | 0 | 0 | 0 | 0 | 243 / 0 / 33 / 0 |
| Dummy constante 1 | final | 277 | 273 | 4 | 5 | 3 | 554 | 3 / 240 / 0 / 33 |

El arbol genera 193 revisiones: 191 conocidas y dos desconocidas. Dummy constante produce 277: 273 conocidas y cuatro desconocidas. Son **84 revisiones menos y 168 minutos hipoteticos**, no ahorro demostrado. Los FN pasan de cero con Dummy limitado a cuatro con arbol; los FP bajan de 240 a 162. Dummy RAW tiene F2 0.40441176, mientras su politica limitada tiene 0.40740741: no se confunden denominadores ni decisiones.

La politica del arbol supera descriptivamente ambas referencias en F2 y respeta capacidad, pero revisar tanto con precision baja puede ser inviable para el usuario. La utilidad no esta validada ni el costo de omitir cuatro atrasos acordado. Las colas OOF se separan por pliegue, replica y dia; no representan competencia conjunta de todos los casos bajo un solo modelo desplegado.

<!-- PAGE -->

## 4.3. Tres errores del cache, sin segunda prediccion

Se muestran los primeros tres errores ordenados por loan_id del reporte congelado, no casos elegidos por conveniencia. Son FP RAW y de politica.

| Caso | Real/predicho/review | Score | Hipotesis, no causalidad |
| --- | --- | --- | --- |
| PND6-T-L00047 | 0/1/1 | 0.86707410 | Tres pagos previos tardios no impiden un pago puntual nuevo |
| PND6-T-L00048 | 0/1/1 | 0.61021505 | Poco historial pese a puntualidad: hoja amplia y umbral bajo |
| PND6-T-L00049 | 0/1/1 | 0.71719780 | Historia mixta no determina desenlace; alerta sin atraso |

| Entrada | PND6-T-L00047 | PND6-T-L00048 | PND6-T-L00049 |
| --- | --- | --- | --- |
| completed_sales | 3 | 4 | 4 |
| paid_credits | 3 | 4 | 4 |
| paid_late | 3 | 0 | 2 |
| pending_overdue | 0 | 0 | 0 |
| pending_current | 0 | 0 | 0 |
| outstanding | 0 | 0 | 0 |
| utilization | 0 | 0 | 0 |
| requested_ratio | 0.18125 | 0.35 | 0.2 |
| tenure_days | 42 | 93 | 199 |
| punctuality_rate | 0 | 1 | 0.5 |
| overdue_rate | 0 | 0 | 0 |

Todos los valores son ficticios. Las hipotesis explican limitaciones plausibles, no causas demostradas. El score del tercer error coincide con el ejemplo CLI, pero sus once entradas son distintas: igualdad de score de hoja no implica duplicacion del vector. Los cuatro FN totales se conservan en la matriz y no se ocultan por mostrar estos tres FP deterministas.

<!-- PAGE -->

## 4.4. Interpretacion y accion concreta

El arbol utiliza `punctuality_rate <= 0.911067` en la raiz. Entre antecedentes menos puntuales separa `tenure_days <= 317.5` y `punctuality_rate <= 0.305556`; para antecedentes puntuales considera antiguedad 196.5 dias, solicitud/80 y pagos previos 4.5. Son cortes aprendidos, no reglas aprobadas del negocio. Anexo C conserva el texto real de las reglas en unidades originales. La clase de hoja por defecto no sustituye el umbral 0.2 aplicado al score.

| Hallazgo | Lectura prudente | Accion propuesta |
| --- | --- | --- |
| Puntualidad e historial | Asociacion dentro del simulador | Revisar pagos anteriores y corregir registros antes de mostrar alerta |
| Antiguedad y pocos pagos | Historial limitado no es solvencia ni causalidad | Mostrar cantidad de evidencia y reservar decision al propietario |
| Solicitud/80 | Cupo 80 es supuesto | Confirmar monto/cupo real antes de integrar, sin recomendar modificarlo por este estudio |
| Cinco constantes y dos duplicadas | Sin evidencia de variacion de deuda | Bloquear pendientes fuera del modelo; no interpretar su importancia |

Coeficientes reales de SVM (margen estandarizado, no probabilidades):

| Variable | Coeficiente |
| --- | --- |
| punctuality_rate | -0.95604184 |
| paid_late | 0.15071652 |
| tenure_days | -0.04082182 |
| completed_sales | -0.02945010 |
| paid_credits | -0.02945010 |
| requested_ratio | -0.02203495 |

Puntualidad tiene coeficiente negativo y paid_late positivo; los duplicados reparten contribucion y las cinco constantes tienen coeficiente cero. No son efectos causales. Para una persona no tecnica: el modelo señala que historial merece mirar primero, pero muchas alertas seran puntuales y algunas tardias se omitiran. No estima perdida definitiva ni autoriza fiar.

<!-- PAGE -->

# 5. Integracion con el MVP

## Contrato y reglas previas al modelo V6

Flujo: once campos ficticios > validacion > reglas del propietario > Pipeline exportado, solo si es elegible > score/umbral > candidato a REVIEW. CLI y laboratorio web V6 autenticado aplican las mismas reglas, sin modificar el experimento congelado.

**Saldo pendiente:** cualquier saldo positivo, vigente o vencido, bloquea con `decision=blocked_pending_balance`. Abono o acuerdo no bastan. **Sin fiados pagados:** `decision=requires_owner_review`; exige revision del propietario. Si falta confirmar deuda cero o historial, tambien se deriva a revision. En ambos estados `model_called=false`, probabilidad, umbral y prediccion son nulos. La deuda tiene prioridad.

Solo deuda cero confirmada e historial pagado permiten consultar el arbol. Ninguna salida aprueba creditos, asigna cupo ni garantiza pago. La web ofrece tres ejemplos cerrados: `illustrative-v6`, `pending-balance-v6` y `no-history-v6`, sin entradas libres.

Ejemplo elegible S/20 sobre cupo S/80, sin PII ni etiqueta conocida:

```json
{"features":{"completed_sales":6,"paid_credits":6,"paid_late":1,"pending_overdue":0,"pending_current":0,"outstanding":0,"utilization":0,"requested_ratio":0.25,"tenure_days":60,"punctuality_rate":0.8333333333333334,"overdue_rate":0}}
```

Comando desde la raiz con dependencias preparadas; no entrena:

```bash
python APF3_TD_Grupo2_ML_Innovacion.py \
  --predict-artifact-dir experimento \
  --input-json experimento/illustrative_input.json \
  --output-json inferencia-demo-v6-nueva.json
```

Salida elegible sin cambios: tree, score `0.7171978005286032`, umbral `0.2`, predicted=1, research_only=true, business_approval=false. Es candidato a REVIEW, no aprobacion ni DEFAULT real. La cola diaria no se aplica a una solicitud aislada.

La prueba CLI acredita ambos bloqueos sin directorio de artefactos: no puede cargar modelo. El ejemplo elegible conserva su salida exacta. La reproduccion historica mantiene 47 archivos deterministas, 12 RAW y 12 politicas exactas y cinco Joblib binariamente iguales. Estas reglas son una capa previa, no un nuevo entrenamiento ni una reevaluacion de FINAL; las metricas publicadas pertenecen al experimento original.

La demo en `/laboratorio-academico/v6` no crea creditos. El primer fiado transaccional requiere excepcion administrativa justificada y auditada; el laboratorio solo muestra la derivacion humana. Para PROY faltan adaptador transaccional V6, cola compartida y validacion con datos reales. Esta exportacion no modifica produccion.

**Viabilidad medida V6 (Anexo G).** Docker + CLI: 1.758941 s. Prediccion local con verificacion de hashes y deserializacion: primera 151.729 ms; 30 llamadas calientes, mediana 142.585 ms, p95 148.923 ms y maximo 149.624 ms. RSS pico 240144 KiB (234.52 MiB) en contenedor limitado a 256 MiB: diferencia nominal 21.48 MiB, margen estrecho que no equivale a memoria libre del contenedor. Solo este caso en venv limpio; no se midieron HTTP, concurrencia ni SLA, ni se certifica produccion.

<!-- PAGE -->

# 6. Normativa y proyeccion a PROY

Se mantiene el marco de APF1/APF2: Ley N.° 29733 y D.S. N.° 016-2024-JUS. Es herencia documental, no nueva consulta de vigencia legal ni certificacion integral. La autorizacion del propietario para revisar ejemplos no equivale a consentimiento de clientes reales.

| Requisito de la norma | Decision/control | Evidencia y limite |
| --- | --- | --- |
| Ley 29733: finalidad y proporcionalidad | Solo once variables transaccionales; IDs fuera del modelo | codigo/scripts/academic_credit_pending_v6.py; experimento/protocol.json feature_policy |
| Ley 29733: minimizacion y proteccion | CSV 100 % simulado; fuente de revision sanitizada; no Word ni firmas | datos/desarrollo.csv origen; anexos/normativa-ia/revision-propietario-sanitizada-v6.json |
| Seguridad y trazabilidad | Hashes, protocolo y reproduccion; cargar solo Joblib confiable | experimento/artifact_manifest.json; verificacion-reproduccion.json |
| Consentimiento/finalidad antes de clientes reales | Persistir fecha, alcance y version; pendiente del piloto real | APF2 Tabla 16/US09; no exigible como nueva autorizacion para filas ficticias |
| Conservacion, ARCO y proveedores | Definir plazos, borrado y contratos antes de produccion | Brecha futura; archivar no equivale a borrar; no certificacion legal |

## Riesgos y plan propuesto

| Riesgo | Prob./impacto | Responsable propuesto | Mitigacion |
| --- | --- | --- | --- |
| Poca generalizacion; repeticion sintetica | Alta/Alto | Cesar Paredes | Piloto real consentido con desenlaces maduros; nuevo test prospectivo |
| Carga de FP y FN omitidos | Alta/Alto | Omara Baylon | Medir minutos y consecuencias; acordar tolerancia antes de uso real |
| Fallo de integracion o version | Media/Alto | Tamara Coveñas | Versionar adaptador y contrato; conservar fallback y logs |
| Privacidad y revisiones incompletas | Media/Alto | Pablo Yman | Revisar normativa, prompts y trazabilidad; completar revision grupal |

Probabilidades y responsables son propuesta de seguimiento, no tareas ya aceptadas. PROY: integrar snapshot y cola REVIEW, ensayar con usuario, completar controles legales antes de clientes reales y medir un piloto autorizado. Reentrenar solo con nuevo protocolo, desenlaces suficientes y test no consultado; nunca retocar este FINAL.

<!-- PAGE -->

# 7. Conclusiones

V6 aporta una cadena ejecutable y reproducida desde el contrato de datos hasta un modelo exportado y una llamada CLI real. Se compararon dos modelos de Unidad 3 y dos referencias triviales bajo un procedimiento congelado. El arbol seleccionado por desarrollo supera ambas referencias en F2 de politica FINAL y respeta la capacidad supuesta. SVM obtiene mejor F2 en FINAL, sin alterar la seleccion previa.

El beneficio tecnico es disponer de evidencia y priorizacion reproducible, no de un sistema crediticio validado. Detectar 29 de 33 atrasos cuesta 162 falsas alertas conocidas y cuatro omisiones. Frente a Dummy limitado se reducen 84 revisiones, pero los 168 minutos asociados son hipoteticos. El alto burden de alertas y su precision baja impiden concluir utilidad empresarial aprobada.

La regla de no fiar con cualquier saldo pendiente esta reflejada en los datos; las cinco variables de pendiente constantes y la duplicacion ventas/pagos limitan el aprendizaje. No se inventaron variaciones ni se imputaron targets inmaduros. Los 33 casos minoritarios finales cumplen el minimo orientativo, sin convertir transacciones repetidas en personas independientes. Los hard pass no cambian `coherence_accepted=false`.

**Meta de negocio propuesta para piloto, no aprobada:** medir ANTES minutos de revisar todos los casos elegibles y DESPUES minutos de la politica en periodos comparables; exigir menos tiempo, maximo cinco alertas/dia y registrar FN/FP con desenlaces maduros y sus consecuencias. No hay costos acordados ni referencia cronometrada; el exito tecnico no demuestra mejora de cobertura real ni reduccion de la perdida mensual del APF1.

Rildo se muestra dispuesto a autorizar Credify solo como herramienta de apoyo, bajo su revision y conservando la decision final. La autorizacion es prospectiva y condicionada a mas pruebas y confiabilidad comprobada. No autoriza produccion inmediata, decisiones automaticas ni sustituye la revision grupal, la revision de PROY ni un piloto autorizado.

El siguiente paso para PROY es conectar V6 al flujo transaccional, completar la gobernanza para datos reales y medir utilidad prospectiva. CLI y laboratorio web sintetico aplican los controles previos de saldo pendiente e historial pagado; esto no valida el modelo ni autoriza produccion. La revision final de los cuatro integrantes permanece pendiente.

<!-- PAGE -->

# Referencias

Anderson, D. J. (2010). *Kanban: Successful evolutionary change for your technology business*. Blue Hole Press.

Congreso de la Republica del Peru. (2011). *Ley N.° 29733, Ley de Proteccion de Datos Personales*. Diario Oficial El Peruano.

Grupo 2. (2026). *Propuesta metodologica de innovacion y hoja de ruta agil para la MiPYME: MVP de la aplicacion Credify para el fiado a un dia en Cerveceria Baylon* [Informe APF2, Universidad Tecnologica del Peru]. Tabla 17 y Anexo B.4.

Ministerio de Justicia y Derechos Humanos. (2024). *Decreto Supremo N.° 016-2024-JUS, que aprueba el Reglamento de la Ley N.° 29733*. https://www.gob.pe/institucion/anpd/normas-legales/6554453-16-2024-jus

Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D., Brucher, M., Perrot, M., & Duchesnay, E. (2011). Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research, 12*, 2825-2830. https://jmlr.org/papers/v12/pedregosa11a.html

Ries, E. (2011). *The lean startup: How today's entrepreneurs use continuous innovation to create radically successful businesses*. Crown Business.

Universidad Tecnologica del Peru. (2026). *Consigna APF3: Solucion de Machine Learning para la MiPYME, 2026-2* [Consigna del curso Innovacion y Transformacion Digital].

Documentacion tecnica: scikit-learn, Pipeline y validacion agrupada, https://scikit-learn.org/stable/modules/cross_validation.html; Joblib, persistencia de objetos confiables, https://joblib.readthedocs.io/en/stable/persistence.html. Fuentes documentales; no se declara consulta web fresca ni evidencia sectorial no aportada.

<!-- PAGE -->

# Anexo A. Diccionario completo (1-6/24)

Unidad de observacion: fiado otorgado con snapshot anterior. Rango observado: solo DEV conocido (541). Nulos de features: mediana ajustada solo en entrenamiento; target desconocido nunca se imputa.

| Variable / tipo / unidad | Descripcion y rango valido | Observado DEV |
| --- | --- | --- |
| loan_id / texto / ID ficticio | Identificador unico del fiado. PND6-* | Ver CSV; identificador/fecha no predictora |
| client_id / texto / ID ficticio | Cliente; solo agrupacion CV. PND6-*-C* | Ver CSV; identificador/fecha no predictora |
| replica_id / categoria / historia | Mundo alternativo; no sucursal. PND6-D1/D2/T | PND6-D1 / PND6-D2 |
| origen / categoria / origen | Procedencia rotulada. simulado | simulado |
| phase / categoria / fase | CSV supervisado de estudio. study | study |
| evaluated_at / datetime ISO / America/Lima | Instante del snapshot previo. Anterior a vencimiento y corte | Ver CSV; identificador/fecha no predictora |

Dominio de inferencia V6: elegible sin saldo previo, cinco variables pendientes cero y ventas de credito iguales a paid_credits. Un pendiente positivo debe bloquearse por regla antes del modelo, no extrapolar su score. El CSV guarda numeros integrales como float; el tipo semantico es conteo entero. Campos no predictores se usan solo para trazabilidad.

<!-- PAGE -->

# Anexo A. Diccionario completo (7-12/24)

Unidad de observacion: fiado otorgado con snapshot anterior. Rango observado: solo DEV conocido (541). Nulos de features: mediana ajustada solo en entrenamiento; target desconocido nunca se imputa.

| Variable / tipo / unidad | Descripcion y rango valido | Observado DEV |
| --- | --- | --- |
| due_date / fecha ISO / dia civil Lima | Vencimiento contractual. Dia siguiente a evaluacion | Ver CSV; identificador/fecha no predictora |
| observed_on / fecha ISO / dia civil Lima | Corte de observacion. 2026-09-30 | 2026-09-30 |
| requested_amount / decimal(2) / PEN | Monto solicitado. [5,50] | 5.5..50 |
| credit_cap / decimal(2) / PEN | Cupo supuesto. 80 | 80..80 |
| pending_at_cutoff / decimal(2) / PEN | Saldo al corte; excluido del modelo. [0,50] | 0..0 |
| scenario / categoria / escenario | Plan simulado; excluido del modelo. on_time/late/partial_* | late / on_time / partial_late_after_due / partial_late_before_due / partial_on_time_before_due |

Dominio de inferencia V6: elegible sin saldo previo, cinco variables pendientes cero y ventas de credito iguales a paid_credits. Un pendiente positivo debe bloquearse por regla antes del modelo, no extrapolar su score. El CSV guarda numeros integrales como float; el tipo semantico es conteo entero. Campos no predictores se usan solo para trazabilidad.

<!-- PAGE -->

# Anexo A. Diccionario completo (13-18/24)

Unidad de observacion: fiado otorgado con snapshot anterior. Rango observado: solo DEV conocido (541). Nulos de features: mediana ajustada solo en entrenamiento; target desconocido nunca se imputa.

| Variable / tipo / unidad | Descripcion y rango valido | Observado DEV |
| --- | --- | --- |
| completed_sales / numero entero / ventas | Ventas de credito completadas previas; no todas las ventas MVP. >=0; igual a paid_credits | 2..28 |
| paid_credits / numero entero / fiados | Fiados liquidados antes de evaluar. >=0 | 2..28 |
| paid_late / numero entero / fiados | Liquidados tarde antes de evaluar. [0,paid_credits] | 0..15 |
| pending_overdue / numero entero / fiados | Saldo previo vencido. 0 en dominio V6 elegible | 0..0 |
| pending_current / numero entero / fiados | Saldo previo vigente. 0 en dominio V6 elegible | 0..0 |
| outstanding / decimal / PEN | Deuda previa total. 0 en dominio V6 elegible | 0..0 |

Dominio de inferencia V6: elegible sin saldo previo, cinco variables pendientes cero y ventas de credito iguales a paid_credits. Un pendiente positivo debe bloquearse por regla antes del modelo, no extrapolar su score. El CSV guarda numeros integrales como float; el tipo semantico es conteo entero. Campos no predictores se usan solo para trazabilidad.

<!-- PAGE -->

# Anexo A. Diccionario completo (19-24/24)

Unidad de observacion: fiado otorgado con snapshot anterior. Rango observado: solo DEV conocido (541). Nulos de features: mediana ajustada solo en entrenamiento; target desconocido nunca se imputa.

| Variable / tipo / unidad | Descripcion y rango valido | Observado DEV |
| --- | --- | --- |
| utilization / decimal / proporcion | outstanding / 80. 0 en dominio V6 elegible | 0..0 |
| requested_ratio / decimal / proporcion | requested_amount / 80. [0.0625,0.625] | 0.06875..0.625 |
| tenure_days / numero entero / dias | Antiguedad desde registro ficticio. >=0 | 56..360 |
| punctuality_rate / decimal / proporcion | (paid_credits-paid_late)/paid_credits; sin historial=0. [0,1] | 0..1 |
| overdue_rate / decimal / proporcion | Vencidos/activos; sin activos=0. 0 en dominio V6 elegible | 0..0 |
| late_payment / binario nullable / clase | 0 puntual; 1 atraso desde vencimiento; no perdida definitiva. 0/1/vacio si inmaduro | 0 / 1 |

Dominio de inferencia V6: elegible sin saldo previo, cinco variables pendientes cero y ventas de credito iguales a paid_credits. Un pendiente positivo debe bloquearse por regla antes del modelo, no extrapolar su score. El CSV guarda numeros integrales como float; el tipo semantico es conteo entero. Campos no predictores se usan solo para trazabilidad.

<!-- PAGE -->

# Anexo B. Auditoria DEV y precision de montos

| Variable | Cerca inferior | Cerca superior | Fuera IQR | Decision |
| --- | --- | --- | --- | --- |
| completed_sales | -7.5000 | 36.5000 | 0 | Retener |
| paid_credits | -7.5000 | 36.5000 | 0 | Retener |
| paid_late | -6.0000 | 10.0000 | 9 | Retener |
| pending_overdue | 0.0000 | 0.0000 | 0 | Retener |
| pending_current | 0.0000 | 0.0000 | 0 | Retener |
| outstanding | 0.0000 | 0.0000 | 0 | Retener |
| utilization | 0.0000 | 0.0000 | 0 | Retener |
| requested_ratio | -0.0450 | 0.5620 | 5 | Retener |
| tenure_days | 6.0000 | 398.0000 | 0 | Retener |
| punctuality_rate | 0.3182 | 1.4091 | 30 | Retener |
| overdue_rate | 0.0000 | 0.0000 | 0 | Retener |
| requested_amount | -3.6000 | 44.9600 | 5 | Retener |
| credit_cap | 80.0000 | 80.0000 | 0 | Retener |
| pending_at_cutoff | 0.0000 | 0.0000 | 0 | Retener |

Conteos de precision sobre **todas las filas de estudio DEV**, incluidos desconocidos, excluido calentamiento:

| Historia | Estudio | Entero/.50 | Otros centimos exactos |
| --- | --- | --- | --- |
| PND6-D1 | 273 | 222 | 51 |
| PND6-D2 | 272 | 208 | 64 |

No confundir con amount_precision_counts de la auditoria transaccional, que incluye warmup. El JSON propio `anexos/datos/auditoria-calidad-dev-v6.json` conserva nulos por cada columna, duplicados por ID/vector y cercas IQR. Los extremos no se eliminan por ser estadisticamente raros. La validez de reglas no demuestra representatividad global.

<!-- PAGE -->

# Anexo C. Reglas reales exportadas

Unidades originales despues de imputacion mediana de entrenamiento; no causalidad. Estas clases de hoja no sustituyen clasificacion por score >=0.2.

```text
|--- punctuality_rate <= 0.911067
|   |--- tenure_days <= 317.500000
|   |   |--- punctuality_rate <= 0.305556
|   |   |   |--- requested_ratio <= 0.178125
|   |   |   |   |--- class: 1
|   |   |   |--- requested_ratio >  0.178125
|   |   |   |   |--- class: 1
|   |   |--- punctuality_rate >  0.305556
|   |   |   |--- tenure_days <= 266.500001
|   |   |   |   |--- class: 1
|   |   |   |--- tenure_days >  266.500001
|   |   |   |   |--- class: 1
|   |--- tenure_days >  317.500000
|   |   |--- class: 0
|--- punctuality_rate >  0.911067
|   |--- tenure_days <= 196.500000
|   |   |--- requested_ratio <= 0.362500
|   |   |   |--- paid_credits <= 4.500000
|   |   |   |   |--- class: 1
|   |   |   |--- paid_credits >  4.500000
|   |   |   |   |--- class: 0
|   |   |--- requested_ratio >  0.362500
|   |   |   |--- class: 0
|   |--- tenure_days >  196.500000
|   |   |--- requested_ratio <= 0.484375
|   |   |   |--- class: 0
|   |   |--- requested_ratio >  0.484375
|   |   |   |--- class: 0
```

Fuente: experimento/pending_v6_report.json, models.tree.interpretation. No se cargo Joblib para extraerlas ni se ejecuto segunda inferencia. SVM describe margen estandarizado; intercepto -0.28282011.

<!-- PAGE -->

# Anexo D. Reproduccion, trazabilidad y ambiente

| Control guardado | Resultado |
| --- | --- |
| verificacion-reproduccion.json passed | True |
| Archivos deterministas SHA exactos | 47 |
| Comparaciones RAW / politica | 12/12 |
| Cinco Joblib binarios / estados | Iguales / iguales |
| Ejemplo distinto y CLI original/reproduccion | Exactos, sin etiqueta conocida |
| Control negativo de metricas en reproduccion | True |

| Fuente congelada | SHA-256 |
| --- | --- |
| protocol.json | eb7fcd39f69be0115895cbb43b6d84e4488535646108bd6f21381d0fb1607923 |
| data_protocol.json | 5f3cea3798b73d31cf8aea54dc6bc45341777871988f7ef68686d34287811431 |
| owner_review.json | a72ea574fa2997d3477b0522c0044d590638957f0b5e553c31d97764df1a89a3 |

El protocolo de modelado eb7f... es posterior al protocolo de datos 5f3c... y anterior al entrenamiento/final; no reescribe su autorizacion historica. La revision sanitizada a72e... referencia Word privado 82d4...: no se entrega el original ni firmas.

Runtime experimental: Python 3.12.14, sklearn 1.9.1, numpy 2.5.3, scipy 1.18.1, joblib 1.6.0 y threadpoolctl 3.7.0. Requirements y entorno limpio estan en la raiz; entorno de exportacion documental es separado. Reproduccion es replay fijo, no nueva prueba independiente.

<!-- PAGE -->

# Anexo E. Prompts y asistencia de IA

Herramienta: OpenCode. Modelo de esta asistencia: `openai/gpt-6.1-sol`. Apoyo declarado en codigo, preparacion/auditoria de datos simulados, modelado, depuracion, metricas, redaccion y exportacion documental. Los artefactos congelados, no el texto generado, son fuente de cifras.

Prompts literales visibles transmitidos en el contexto del usuario, sin inventar fechas ni historial completo:

| Texto literal | Procedencia y alcance |
| --- | --- |
| ya hazlo todo correctamente | Literal exigido por el usuario en el contexto actual; no acredita revision humana completada |
| ya haz el siguiente paso | Contexto previo proporcionado por el usuario; sin fecha disponible |
| que sigue? | Contexto previo proporcionado por el usuario; sin fecha disponible |
| IMPLEMENTA y EJECUTA nuevo informeV6 contra consigna ORIGINAL | Extracto literal inicial del encargo actual; restricciones completas aplicadas al generador |
| Rerenderregenerate ownreport docs+outputsconarchivo read cached no predictcalls. | Extracto literal del encargo de actualizacion: leer evidencia CLI/latencia, sin nuevas predicciones ni cambios del protocolo congelado |

Verificacion tecnica aplicada: cotejo de JSON completo y resumen, tablas RAW/politica/colas a precision impresa, control negativo con metrica alterada, integridad de fuentes y exportacion offline A4. Estas comprobaciones automatizadas **no son validacion humana**. La reproduccion preexistente acredita codigo/artefactos; este proceso no entreno ni predijo.

| Integrante | Revision propuesta | Validacion humana V6 |
| --- | --- | --- |
| Omara Baylon | Fuente propietaria, problema y utilidad | PENDIENTE |
| Tamara Coveñas | Codigo, integracion y reproduccion | PENDIENTE |
| Cesar Paredes | Datos, limpieza y metricas | PENDIENTE |
| Pablo Yman | Consigna, normativa y prompts | PENDIENTE |

Cada persona debe contrastar las fuentes y registrar correcciones reales antes de afirmar validacion final. No se reutiliza como aprobacion V6 la constancia historica APF2 ni la revision muestral V5 de Rildo.

<!-- PAGE -->

# Anexo F. Matriz normativa y continuidad de controles

| Requisito de la norma | Decision/control | Evidencia y limite |
| --- | --- | --- |
| Ley 29733: finalidad y proporcionalidad | Solo once variables transaccionales; IDs fuera del modelo | codigo/scripts/academic_credit_pending_v6.py; experimento/protocol.json feature_policy |
| Ley 29733: minimizacion y proteccion | CSV 100 % simulado; fuente de revision sanitizada; no Word ni firmas | datos/desarrollo.csv origen; anexos/normativa-ia/revision-propietario-sanitizada-v6.json |
| Seguridad y trazabilidad | Hashes, protocolo y reproduccion; cargar solo Joblib confiable | experimento/artifact_manifest.json; verificacion-reproduccion.json |
| Consentimiento/finalidad antes de clientes reales | Persistir fecha, alcance y version; pendiente del piloto real | APF2 Tabla 16/US09; no exigible como nueva autorizacion para filas ficticias |
| Conservacion, ARCO y proveedores | Definir plazos, borrado y contratos antes de produccion | Brecha futura; archivar no equivale a borrar; no certificacion legal |

La finalidad actual es investigacion academica sobre transacciones ficticias. No se solicita nuevo consentimiento de clientes para inventar ejemplos academicos ni se declara captacion real. Para un piloto personal real quedan pendientes aviso de privacidad, constancia versionada, retencion/eliminacion, atencion ARCO y condiciones de proveedores. No basta omitir DNI para garantizar anonimato de datos reales.

Controles heredados del MVP: autenticacion/roles, hash Argon2, HTTPS y separacion de demo/produccion constan en APF2. No se presentan como nuevas pruebas de este generador ni como endpoint V6. La evidencia ejecutable entregada de V6 esta en codigo/scripts y experimento; el informe no necesita GitHub ni publicacion.

El Word de revision y los PDF con firmas permanecen privados. Se entrega solo revision estructurada sanitizada con reglas y agregados; su hash permite rastrear la fuente sin divulgar firmas ni identidades de clientes.

<!-- PAGE -->

# Anexo G. Integracion y viabilidad V6 ejecutadas

Fuentes: `anexos/integracion/prueba-cli-v6.json` y `anexos/integracion/latency-v6.json`, ambas passed=true. La CLI elegible devuelve p=0.7171978005286032, umbral=0.2 y predicted=1. Ejemplo ficticio, candidato a REVIEW, no aprobacion.

| Medicion V6 | Valor | Unidad |
| --- | --- | --- |
| Docker + CLI raiz | 1.758941 | s |
| Primera prediccion local | 151.729 | ms |
| Llamadas calientes | 30 | llamadas |
| Mediana caliente | 142.585 | ms |
| p95 caliente (nearest rank) | 148.923 | ms |
| Maximo caliente | 149.624 | ms |
| RSS pico del proceso | 240144 | KiB |
| RSS convertido | 234.52 | MiB |
| Limite del contenedor | 256 | MiB |
| Diferencia nominal limite - RSS | 21.48 | MiB |

La prediccion local incluye integridad/hash chain, deserializacion y un vector ilustrativo; no es solo el recorrido del arbol. Docker + CLI incluye arranque. El registro conserva 30 muestras y p95 nearest rank, sin red, contenedor read-only de 256m y venv congelado.

El RSS pico se convierte con 1024 KiB/MiB. Su margen nominal frente a 256 MiB es estrecho y no mide memoria libre ni pico total del contenedor. Solo acredita este caso; no certifica capacidad, margen seguro ni concurrencia. El benchmark no mide HTTP, autenticacion, DB, navegador, carga sostenida ni SLA. Ensayo humano pendiente.

Ambas reglas previas pasan sin directorio de artefactos: `model_called=false`, sin probabilidad ni prediccion. Instrucciones y ejemplos: `anexos/revision/REGLAS_PREVIAS_V6.md`. El registro separado `anexos/integracion/despliegue-reglas-v6.json` conserva las pruebas publicas y la incidencia de recuperacion del despliegue; no es un benchmark ni validacion predictiva.

Hashes SHA-256 de los registros leidos:

| Registro | SHA-256 |
| --- | --- |
| anexos/integracion/prueba-cli-v6.json | 814a2df6006951a05eb360a3a7d1618a12cbd96e4d26c3033abab411f2d987e6 |
| anexos/integracion/latency-v6.json | 8e5944d618b0dc039a061b00173b3b3c0067eee71ed08fa27668398ba9605c4e |

La exportacion solo lee evidencia: no reejecuta prediccion ni benchmark, no entrena ni modifica protocolo, modelo o FINAL.

<!-- PAGE -->

# Anexo H. Metricas RAW completas

Misma precision que las tablas del cuerpo; train y OOF n=541, FINAL n=276.

| Modelo RAW | Particion | Precision | Recall | F1 | F2 | Accuracy |
| --- | --- | --- | --- | --- | --- | --- |
| Arbol seleccionado | train | 0.24576271 | 1.00000000 | 0.39455782 | 0.61965812 | 0.50646950 |
| Arbol seleccionado | oof | 0.25239617 | 0.90804598 | 0.39500000 | 0.59757943 | 0.55268022 |
| Arbol seleccionado | final | 0.15183246 | 0.87878788 | 0.25892857 | 0.44891641 | 0.39855072 |
| SVM | train | 0.31250000 | 0.86206897 | 0.45871560 | 0.63775510 | 0.67282810 |
| SVM | oof | 0.26297578 | 0.87356322 | 0.40425532 | 0.59654631 | 0.58595194 |
| SVM | final | 0.23214286 | 0.78787879 | 0.35862069 | 0.53278689 | 0.66304348 |
| Dummy mayoritario | train | 0.00000000 | 0.00000000 | 0.00000000 | 0.00000000 | 0.83918669 |
| Dummy mayoritario | oof | 0.00000000 | 0.00000000 | 0.00000000 | 0.00000000 | 0.83918669 |
| Dummy mayoritario | final | 0.00000000 | 0.00000000 | 0.00000000 | 0.00000000 | 0.88043478 |
| Dummy constante 1 | train | 0.16081331 | 1.00000000 | 0.27707006 | 0.48931384 | 0.16081331 |
| Dummy constante 1 | oof | 0.16081331 | 1.00000000 | 0.27707006 | 0.48931384 | 0.16081331 |
| Dummy constante 1 | final | 0.11956522 | 1.00000000 | 0.21359223 | 0.40441176 | 0.11956522 |

<!-- PAGE -->

# Anexo H. Metricas de politica completas

Acciones despues del tope; desconocidos compiten en cola pero no en metricas.

| Modelo POLICY | Particion | Precision | Recall | F1 | F2 | Accuracy |
| --- | --- | --- | --- | --- | --- | --- |
| Arbol seleccionado | train | 0.24715909 | 1.00000000 | 0.39635535 | 0.62142857 | 0.51016636 |
| Arbol seleccionado | oof | 0.25239617 | 0.90804598 | 0.39500000 | 0.59757943 | 0.55268022 |
| Arbol seleccionado | final | 0.15183246 | 0.87878788 | 0.25892857 | 0.44891641 | 0.39855072 |
| SVM | train | 0.31250000 | 0.86206897 | 0.45871560 | 0.63775510 | 0.67282810 |
| SVM | oof | 0.26297578 | 0.87356322 | 0.40425532 | 0.59654631 | 0.58595194 |
| SVM | final | 0.23214286 | 0.78787879 | 0.35862069 | 0.53278689 | 0.66304348 |
| Dummy mayoritario | train | 0.00000000 | 0.00000000 | 0.00000000 | 0.00000000 | 0.83918669 |
| Dummy mayoritario | oof | 0.00000000 | 0.00000000 | 0.00000000 | 0.00000000 | 0.83918669 |
| Dummy mayoritario | final | 0.00000000 | 0.00000000 | 0.00000000 | 0.00000000 | 0.88043478 |
| Dummy constante 1 | train | 0.15879017 | 0.96551724 | 0.27272727 | 0.47890536 | 0.17190388 |
| Dummy constante 1 | oof | 0.16081331 | 1.00000000 | 0.27707006 | 0.48931384 | 0.16081331 |
| Dummy constante 1 | final | 0.12087912 | 1.00000000 | 0.21568627 | 0.40740741 | 0.13043478 |

<!-- PAGE -->

# Anexo H. Conteos de cola: train

| Modelo COLA | Particion | Total | Conocidas | Sin etiqueta | Max/dia | Dias sobre antes | Min supuestos | TN/FP/FN/TP |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Arbol seleccionado | train | 355 | 352 | 3 | 5 | 2 | 710 | 189 / 265 / 0 / 87 |
| SVM | train | 243 | 240 | 3 | 4 | 0 | 486 | 289 / 165 / 12 / 75 |
| Dummy mayoritario | train | 0 | 0 | 0 | 0 | 0 | 0 | 454 / 0 / 87 / 0 |
| Dummy constante 1 | train | 533 | 529 | 4 | 5 | 10 | 1066 | 9 / 445 / 3 / 84 |

Train es desempeño de reajuste; OOF separa por pliegue, replica y dia; FINAL por replica y dia. Las historias alternativas no se suman como volumen empresarial. Dos minutos por caso y cinco por dia son supuestos, no ahorro medido.

<!-- PAGE -->

# Anexo H. Conteos de cola: oof

| Modelo COLA | Particion | Total | Conocidas | Sin etiqueta | Max/dia | Dias sobre antes | Min supuestos | TN/FP/FN/TP |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Arbol seleccionado | oof | 316 | 313 | 3 | 4 | 0 | 632 | 220 / 234 / 8 / 79 |
| SVM | oof | 292 | 289 | 3 | 4 | 0 | 584 | 241 / 213 / 11 / 76 |
| Dummy mayoritario | oof | 0 | 0 | 0 | 0 | 0 | 0 | 454 / 0 / 87 / 0 |
| Dummy constante 1 | oof | 545 | 541 | 4 | 5 | 0 | 1090 | 0 / 454 / 0 / 87 |

Train es desempeño de reajuste; OOF separa por pliegue, replica y dia; FINAL por replica y dia. Las historias alternativas no se suman como volumen empresarial. Dos minutos por caso y cinco por dia son supuestos, no ahorro medido.

<!-- PAGE -->

# Anexo H. Conteos de cola: final

| Modelo COLA | Particion | Total | Conocidas | Sin etiqueta | Max/dia | Dias sobre antes | Min supuestos | TN/FP/FN/TP |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Arbol seleccionado | final | 193 | 191 | 2 | 5 | 0 | 386 | 81 / 162 / 4 / 29 |
| SVM | final | 115 | 112 | 3 | 4 | 0 | 230 | 157 / 86 / 7 / 26 |
| Dummy mayoritario | final | 0 | 0 | 0 | 0 | 0 | 0 | 243 / 0 / 33 / 0 |
| Dummy constante 1 | final | 277 | 273 | 4 | 5 | 3 | 554 | 3 / 240 / 0 / 33 |

Train es desempeño de reajuste; OOF separa por pliegue, replica y dia; FINAL por replica y dia. Las historias alternativas no se suman como volumen empresarial. Dos minutos por caso y cinco por dia son supuestos, no ahorro medido.

<!-- PAGE -->

# Anexo I. Conteos de consistencia reconstruidos

Solo DEV conocido de estudio, n=541. No se usa FINAL para elegir reglas ni hacer EDA de desenlaces.

| Control ejecutado | Violaciones |
| --- | --- |
| origen_not_simulado | 0 |
| amount_outside_5_50_pen | 0 |
| cap_not_80_pen | 0 |
| negative_counts | 0 |
| paid_late_exceeds_paid_credits | 0 |
| positive_pending_input | 0 |
| requested_ratio_mismatch | 0 |
| punctuality_rate_mismatch | 0 |
| temporal_order | 0 |

Estos conteos complementan los hard pass transaccionales guardados y la ficha de siete criterios; no constituyen aceptacion global por el propietario. La coherencia con APF2 requiere leer los cambios de fuente y alcance de ventas, no solo aprobar reglas numericas.
