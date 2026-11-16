# Anexo A. Normativa y controles verificables V4

**APF3, Grupo 2, Cerveceria Baylon / Credify. Anexos de cierre para integracion documental posterior.** Cinco bloques separados por `<!--PAGE-->`; son paginas logicas, no una paginacion PDF comprobada. Este archivo no modifica el informe, el paquete congelado, el protocolo ni el runtime y no constituye acta de aprobacion.

**Base documental consultada:** consigna original `/Users/tamaraalison/Downloads/Innovacion_TD_Consigna_APF3.pdf`, secciones 2.7, 6.4, 6.5, 8 y 9; informe materializado `/Users/tamaraalison/Downloads/APF3_Grupo2_Alineado_V4/informe/APF3_TD_Grupo2_ML_Innovacion_Borrador.md`, lineas 352-366 y 641-697. No se usa como estado final la copia V4 anterior del repositorio. Las rutas locales de ese paquete no presuponen acceso del docente.

**Marco heredado APF1 corregido / APF2:** Ley N.° 29733 y Reglamento aprobado por D.S. N.° 016-2024-JUS. No se incorporan otras normas del borrador legacy como obligaciones de este estudio. Referencias oficiales heredadas: [Ley 29733, ANPD](https://www.gob.pe/institucion/anpd/normas-legales/2018427-29733-2011) y [D.S. 016-2024-JUS, ANPD](https://www.gob.pe/institucion/anpd/normas-legales/6554453-16-2024-jus). **No se realizo consulta web ni nueva verificacion juridica de vigencia, articulos o plazos.** La matriz es un autodiagnostico tecnico, no certificacion de cumplimiento legal.

| Requisito normativo | Control en dataset/modelo | Evidencia concreta y limite |
| --- | --- | --- |
| Finalidad del tratamiento, continuidad APF1/APF2 | V4 se limita a investigacion sintetica sobre atraso del fiado a un dia. La alerta no autoriza ni rechaza credito. | [Servicio V4, L54-L59 y L261-L274](../backend/app/services/academic_lab_v4.py): advertencia, `research_only=true`, `business_approval=false`, sin cola diaria aplicada. Formalizar finalidad y base juridica para personas reales sigue pendiente. |
| Minimizacion de variables | Once predictores numericos; el contrato del ejemplo no admite nombres, documentos, contactos ni target como entrada. Esto no demuestra anonimato de un futuro dataset real. | [Servicio, L22-L34 y L114-L128](../backend/app/services/academic_lab_v4.py). [Generador, L34-L49](../backend/app/ml/owner_aligned_synthetic.py): IDs ficticios y fechas existen como metadatos, no como predictores; no se afirma ausencia universal de datos personales en documentos. |
| Datos simulados y prevencion de reidentificacion | Cero filas reales en aprendizaje/evaluacion; se conserva `origen=simulado`. La fuente comercial solo aporta agregados, no registros individuales. | [Generador, L125-L159, L328-L356](../backend/app/ml/owner_aligned_synthetic.py); [servicio, L166-L173 y L222-L228](../backend/app/services/academic_lab_v4.py). No equivale a anonimizar datos reales ni a auditar el recuerdo del propietario. |
| Seguridad y acceso limitado | JWT y usuario activo; flag deshabilitado por defecto; habilitacion solo en staging. No existe una restriccion V4 exclusiva por rol docente: usa la autenticacion existente. | [Rutas, L10-L21](../backend/app/api/routes/academic_ml_v4.py), [autenticacion, L17-L34](../backend/app/api/dependencies.py), [configuracion, L12-L18 y L70-L81](../backend/app/core/config.py), [registro de rutas, L19-L22](../backend/app/api/router.py). Controles locales, no auditoria de accesos del servidor. |
| Integridad, custodia y tratamiento acotado | Bundle de confianza montado solo lectura; hashes y runtime comprobados antes de cargar bytes Joblib. El servicio de inferencia no escribe operaciones comerciales; autenticar puede consultar la identidad en DB. | [Compose V4, L13-L19](../docker-compose.academic-v4.yml), [servicio, L147-L177 y L235-L260](../backend/app/services/academic_lab_v4.py). Hash no autentica al publicador; Joblib puede ejecutar codigo. No cargar archivos ajenos. |
| Minimizar nuevas capturas y exposicion | Solo se evalua `illustrative-v4`, desde entrada sintetica guardada; cuerpo o query se rechazan. Errores de consulta devuelven 503 generico. | [Rutas, L24-L31 y L45-L52](../backend/app/api/routes/academic_ml_v4.py). No admite PII como entrada de inferencia; ello no certifica redaccion de logs de infraestructura ni privacidad de toda la aplicacion. |
| Informacion y consentimiento cuando corresponda | No hay evidencia nueva de consentimiento de clientes. Una declaracion del propietario no sustituye la base juridica de cada titular. | [Pendiente heredado APF2](APF2_Validacion_y_Artefactos.md), L84; informe materializado, L360-L364. **ABIERTO:** aviso, finalidad, base aplicable y constancias trazables antes del piloto real. |
| Derechos ARCO, conservacion y eliminacion | No se acredita un circuito operativo completo ni plazo aprobado de retencion/borrado. El laboratorio solo lectura no resuelve estos deberes. | [Pendientes APF2, L84](APF2_Validacion_y_Artefactos.md); informe materializado, L361-L366. **ABIERTO:** responsables, canal ARCO, inventario, politica de conservacion, backups y prueba de eliminacion. |
| Custodia de fuentes y terceros | No entregar formulario privado, firmas, contactos, secretos ni cuaderno. El servicio V4 no invoca proveedores externos de IA para inferir. | [Servicio V4 completo](../backend/app/services/academic_lab_v4.py), [exclusiones documentales, L36-L47](PUBLICATION.md). Revisar proveedores, nube y transferencias antes de datos reales; esta evidencia no audita todos los canales del MVP. |

<!--PAGE-->

# Anexo B. Prompts disponibles y limites del registro IA

**Herramienta de esta edicion:** OpenCode, modelo `openai/gpt-6.1-sol`. Se declara asistencia IA en codigo, datos, modelado, documentacion, integracion y verificaciones segun los artefactos conocidos del Anexo C. No se puede atribuir automaticamente el mismo modelo a todas las sesiones anteriores.

**Literalidad y procedencia:** las cinco instrucciones siguientes son los textos exactos disponibles aportados por la usuaria para registrar la sesion. No se dispone aqui de la transcripcion completa de sus respuestas, ejecuciones intermedias o sesiones del experimento anterior. Su presencia no prueba que una persona haya revisado o aprobado los resultados. El alcance es contextual, no una atribucion causal exclusiva de cada archivo a un prompt.

| Prompt literal disponible | Alcance contextual | Resultado documentado, no aprobacion | Verificacion tecnica disponible | Validacion humana |
| --- | --- | --- | --- | --- |
| `que cambios se tendrian que hacer en produccion?` | Consulta sobre evolucion operativa y separacion de investigacion/produccion. | Tooling V4 separado y limites de despliegue documentados; no se deduce autorizacion para publicar o desplegar. | [Laboratorio V4](APF3_LABORATORIO_V4.md), L50-L126 y L246-L247. No se recupera una respuesta literal completa. | PENDIENTE |
| `ya comienza` | Continuacion de trabajo tecnico asistido. No contiene por si sola una especificacion de entrenamiento. | Codigo y controles V4 presentes; la correspondencia exacta entre este mensaje y cada cambio no esta reconstruida. | [Rutas](../backend/app/api/routes/academic_ml_v4.py), [servicio](../backend/app/services/academic_lab_v4.py), [tests](../backend/tests/test_academic_lab_v4.py). Existencia de codigo no prueba revision humana. | PENDIENTE |
| `continua` | Continuacion de implementacion y comprobaciones. | Preparacion y pruebas locales documentadas, sin convertir la instruccion en aceptacion del producto. | [Preparador](../deploy/prepare-aligned-v4-lab.py), [pruebas del preparador](../deploy/test-prepare-aligned-v4-lab.py), [smoke](../deploy/smoke-aligned-v4-api.py). | PENDIENTE |
| `que falta para que el avance 3 cumpla con toda la consigna y todo este listo para presentar?` | Identificacion de brechas tecnicas, documentales y humanas frente a la consigna. | Se distinguen entrega tecnica, normativa pendiente, revision, ensayo y acceso; no se declara cumplimiento total. | Consigna original, secciones 6.4, 8-11; [guion V4 y checklist](APF3_Guion_Sustentacion_V4.md). | PENDIENTE |
| `okay avanza en el orden que has recomendado` | Continuacion del cierre documental. | Materiales de apoyo y este anexo para integracion posterior, no acta grupal ni aprobacion del propietario. | Informe materializado, L674-L697; [guion V4](APF3_Guion_Sustentacion_V4.md); comprobacion estructural de este Markdown. | PENDIENTE |
| **Prompt literal no disponible: fases anteriores de codigo, simulacion y modelado.** | Generador, snapshots, etiquetas, Pipeline, CV agrupada, calibracion, busqueda, congelamiento y evaluacion FINAL. | Existen fuentes y artefactos tecnicos, pero no un historial literal completo que permita reconstruir instrucciones, autores o revisores. | [Generador](../backend/app/ml/owner_aligned_synthetic.py), [runner](../backend/scripts/academic_credit_aligned_v4.py); paquete local: `experimento/protocol.json`, `provenance.json`, `frozen_selection.json`, `fold_audit.json` y `aligned_v4_report.json`. | PENDIENTE |
| **Prompt literal no disponible: otras sesiones documentales y de verificacion.** | Redaccion, figuras desde caches, exportaciones, empaquetado, reproduccion y comprobaciones automatizadas. | Informe, deck y registros disponibles; no se inventa texto de instrucciones anteriores. | Paquete local: `informe/manifest.json`, `verificacion-reproduccion.json`, `verificacion-entrega.json`; [tooling documental](../deploy/generate-aligned-v4-report.py). | PENDIENTE |

**Conservacion pendiente:** recuperar y conservar el historial literal completo original, si existe, con herramienta/modelo, instrucciones, respuestas y alcance real. No sustituirlo por prompts plausibles escritos retrospectivamente. Protocolo, provenance, codigo, hashes y verificacion de artefactos son evidencia tecnica, **NO prueba de autoria, revision humana, consentimiento ni aprobacion**. El anexo declara lo conocido, no cierra la ausencia del historial IA anterior exigido por la consigna.

La solicitud actual de crear este archivo y las ordenes de continuar son instrucciones de edicion, no entrevistas, firmas, actas de aprobacion, validacion comercial o constancias de revision aplicada. Este anexo tampoco convierte una comprobacion automatica en validacion humana.

<!--PAGE-->

# Anexo C. Fases asistidas y verificacion tecnica

**Lectura de evidencia existente, sin reejecutar ML en esta edicion.** Raiz local del paquete: `/Users/tamaraalison/Downloads/APF3_Grupo2_Alineado_V4`. Los nombres relativos de paquete de esta tabla son rutas internas de esa raiz, no enlaces publicos. Los enlaces de codigo llevan al repositorio; no se garantiza que el checkout actual sea identico a cada fuente congelada sin cotejar manifiestos.

| Fase conocida con asistencia IA declarada | Evidencia y comprobacion registrada | Lo que NO demuestra |
| --- | --- | --- |
| Codigo y datos | [Generador/validador](../backend/app/ml/owner_aligned_synthetic.py), [pruebas](../backend/tests/test_owner_aligned_synthetic.py); `experimento/calibration.json`, `provenance.json`, `development_audits.json`, `final_audits.json`. Agregados de fuente, simulacion rotulada y snapshots previos. | No son filas reales, auditoria del cuaderno ni distribuciones medidas. Prompt exacto anterior no disponible. |
| Modelo y seleccion | [Runner V4](../backend/scripts/academic_credit_aligned_v4.py), [tests del experimento](../backend/tests/test_aligned_v4_experiment.py); `experimento/fold_audit.json`, `cv_search.json`, `frozen_selection.json`. Arbol/SVM y dos Dummy; seleccion SVM C=1 balanced, umbral 0.10, por F2 OOF limitado. | No generalizacion real, evaluacion anidada independiente de hiperparametros ni probabilidades reales calibradas. Reusar OOF para buscar introduce optimismo. |
| Evaluacion y reproduccion | `verificacion-reproduccion.json`, `estado-artefactos.json`, `verificacion-reproduccion-inicial.json`; informe materializado L554-L566 y L631-L637. Se registran 12 evaluaciones brutas y 12 de politica exactas, 15 archivos SHA-256 iguales y cinco estados aprendidos iguales. | Los cinco Joblib **no** son binariamente iguales. Se excluyen tres timestamps y dos hashes derivados; cada cadena local se comprueba. Se conserva el fallo inicial. No es validacion independiente ni un nuevo test estadistico. |
| Documentos y empaquetado | `verificacion-entrega.json`, L3-L17, L44-L49 y L114-L123: `passed=true`, 14 paginas de cuerpo, 25 PDF total, 13 slides, 720 segundos planificados, 18 preguntas y 10 paginas de guion. Figuras EDA desde DEV y matriz desde cache. | No render nativo Microsoft Office, revision humana, ensayo cronometrado o ejecucion humana de demo. El conteo de paginas del informe original no incluye este nuevo anexo. |
| Integracion local | [Preparador](../deploy/prepare-aligned-v4-lab.py), [smoke real](../deploy/smoke-aligned-v4-api.py), [stack con navegador](../deploy/test-aligned-v4-stack.mjs), [UI con API simulada](../deploy/test-aligned-v4-ui.mjs). [Registro V4, L128-L237](APF3_LABORATORIO_V4.md): smoke ASGI, imagen final y stack local efimero con login y DB ficticia. | Un test con mocks no prueba el modelo real. El smoke usa identidad ficticia; el stack local no acredita servidor publico, aceptacion humana ni carga sostenida. Solo se infiere el ejemplo ilustrativo, no cohortes FINAL. |
| Suites y analisis estatico | [Registro V4, L235-L244](APF3_LABORATORIO_V4.md): **359 tests backend y 14 del preparador**, Ruff y ESLint aprobados en ejecuciones documentadas anteriores. | No se reejecutaron en esta edicion ni se suman como aceptacion humana. La cifra **223 historicos** referida como antecedente no tiene respaldo primario identificado en las fuentes leidas: queda por localizar su log/version; no se certifica como corrida V4 ni se suma a 359. |

**Integridad del test: primera evaluacion frente a comprobaciones posteriores.** `frozen_selection.json` se persistio antes de generar FINAL; el informe materializado L187 y L220 registra un unico lote FINAL por modelo en la corrida original. Tras observarlo, FINAL ya no es un conjunto no consultado para decisiones futuras. Reproduccion, lectura de caches, recalculo de metricas y comprobaciones posteriores del protocolo fijo no restituyen esa condicion ni anaden evidencia independiente. No se promociona el arbol por ganar en FINAL, ni se retocan umbrales, semillas o datos a partir de sus errores.

**Resultado conservado con limites:** SVM FINAL, 259 conocidos y un desconocido: matriz `[[80,114],[4,61]]`, F2 de politica 0.70115, 176 revisiones incluyendo el desconocido. El arbol tiene mejor F2 FINAL, 0.71096, sin cambiar ganador. Revisar todo limitado tiene F2 0.62257 y 255 revisiones; no confundirlo con bruto, 0.62620. Las 79 revisiones y 158 minutos hipoteticos menos no son ahorro medido. D2 conserva 27 minoritarios; FINAL tiene solo 12 clientes ficticios.

**Verificacion de esta edicion:** solo lectura de fuentes y revision estructural/enlaces de este Markdown. No se entreno, genero datos, infirio, ejecuto suites, consulto produccion ni verifico leyes en la web. Los resultados automaticos anteriores se citan con su alcance, no como ejecuciones nuevas.

<!--PAGE-->

# Anexo D. Registro humano y ensayo pendientes

**Estado: PENDIENTE.** Nombres y codigos proceden de la portada del informe materializado, L9-L14. No se registran contribuciones, revision aplicada, firmas o fechas que no consten. Cada persona debe completar exclusivamente lo que efectivamente haya realizado; un rol propuesto no prueba participacion pasada.

| Integrante | Codigo | Revision efectivamente realizada | Resultado/correccion y evidencia | Fecha real |
| --- | --- | --- | --- | --- |
| Omara Yamileth Baylón Vila | U23231338 | pendiente | pendiente | pendiente |
| Tamara Alison Coveñas Quispe | U23204737 | pendiente | pendiente | pendiente |
| César Augusto Daniel Paredes Paredes | U23259768 | pendiente | pendiente | pendiente |
| Pablo Enrique Yman Avila | U23251279 | pendiente | pendiente | pendiente |

**Checklist de revision autentica, aun sin marcar:**

- [ ] Cada integrante abre las fuentes, contrasta codigo/datos/metricas/conclusiones asistidos por IA y registra alcance, resultado, correccion y fecha real; no basta declarar que leyo el texto.
- [ ] Todos explican con sus palabras la cadena APF1 problema/indicador -> APF2 MVP/contrato -> dataset sintetico -> target -> modelos/baselines -> seleccion -> inferencia -> limites de PROY.
- [ ] Cotejar los agregados permitidos: 48 anotaciones, tres sin desenlace, 45 evaluables, ocho atrasos: **8/45=17.78 %**; diez con parciales: **10/48=20.83 %**, no 10/45. Son agregados declarados aproximados, no filas de entrenamiento ni fuente auditada.
- [ ] Distinguir hipotesis de hechos: Beta, sigmas, poblacion de 12, calentamiento y estacionariedad no fueron medidos. Historias DEV alternativas no son sucursales sumables como volumen real.
- [ ] Explicar Pipeline solo con entrenamiento, CV por cliente y calibracion interna; reconocer optimismo OOF, D2 con 27 minoritarios y dependencia de multiples fiados por cliente.
- [ ] Cotejar seleccion previa a FINAL y reconocer que el test ya observado no sirve para elegir ahora otro modelo; separar primera corrida de reproduccion/comprobaciones posteriores.
- [ ] Explicar cuatro FN y 114 FP SVM, mejor F2 final del arbol sin cambiar ganador, politica limitada frente a clasificador bruto, desconocidos en capacidad y diferencia entre umbral individual y cola top-5.
- [ ] Cotejar ejemplo sin etiqueta: S/ 20 sobre cupo S/ 80, score guardado `0.11922453881690649`, umbral `0.1`, clase `1`, `known_label=null`; no afirmar acierto ni aprobacion comercial.
- [ ] Revisar exclusiones privadas, consentimiento/base juridica, ARCO y conservacion abiertos. No atribuir a Rildo aprobacion de F2, costo de errores o beneficio financiero.
- [ ] Realizar ensayo autentico con los cuatro integrantes: **12 minutos +/- 30 segundos de exposicion y 5 minutos de preguntas**; anotar duracion observada, turnos, preguntas y correcciones. 720 segundos planificados no prueban ensayo.
- [ ] Cada integrante responde sobre cualquier fase, no solo su bloque. Probar demo en el entorno de exposicion; si falla, declarar el fallo y mostrar salida/captura guardada rotulada, nunca simular ejecucion en vivo.
- [ ] Registrar comprension y conformidad real del grupo solo despues de revisar. No usar este pedido de edicion ni instrucciones de continuar como evidencia de aprobacion.

El [guion V4](APF3_Guion_Sustentacion_V4.md) es apoyo para practicar, no constancia de ensayo. No hay nueva entrevista, consentimiento de clientes, validacion del propietario, aceptacion comercial ni factor de contribucion acreditados por estos anexos.

<!--PAGE-->

# Anexo E. Riesgos, acceso y entrega

Se conservan los siete riesgos del informe materializado, L647-L655. Probabilidad e impacto son apreciaciones cualitativas, no frecuencias medidas. Los responsables siguientes son **propuestas para V4**, no asignaciones aceptadas ni contribuciones realizadas; se usan roles de seguimiento coherentes con [APF2, L31-L45](APF2_Avances_Cierre_Pendientes.md).

| Riesgo heredado | Probabilidad | Impacto | Responsable propuesto y rol | Mitigacion / evidencia necesaria |
| --- | --- | --- | --- | --- |
| Confundir simulacion con validacion real | Alta | Alto | Cesar, datos; Omara, enlace con negocio | Conservar etiquetas y supuestos; contrastar con captura autorizada antes de uso real. |
| Falsas alertas y trato restrictivo | Alta | Alto | Cesar, modelo/datos; Tamara, aplicacion | Mantener revision humana y prohibicion de rechazo automatico; medir carga y consecuencias. |
| Omitir atrasos al limitar revision | Media | Alto | Omara, objetivo de negocio; Cesar, evaluacion | Explicar cuatro FN frente a uno de revisar todo limitado; acordar costos sin retocar FINAL. |
| Sobreestimar capacidad total | Alta | Alto | Omara, coordinacion; Pablo, pruebas/evidencias | Cronometrar trabajo completo, incluyendo solicitudes, cobranza y revisiones obligatorias. |
| Tratar clientes sin base o informacion trazable | Alta mientras siga abierto | Alto | Omara, consentimiento; Tamara, controles de aplicacion | Formalizar finalidad/base, aviso, constancias cuando correspondan, ARCO y custodia antes del piloto. |
| Version equivocada o artefacto no confiable | Media | Alto | Tamara, infraestructura/aplicacion; Pablo, pruebas | Cotejar version/manifiestos/contrato, solo Joblib confiable y rollback; no reutilizar capturas v2 como V4. |
| Conclusiones inestables con 12 clientes FINAL | Alta | Alto | Cesar, particiones; Pablo, evidencia de pruebas | No equiparar filas con personas; nueva evaluacion con clientes/periodos trazables no consultados y protocolo previo. |

**PUBLICACION NO AUTORIZADA.** Esta edicion solo crea el Markdown. No autoriza push, publicacion en GitHub/Drive, cambios de permisos, subida al Aula Virtual ni activacion de demo o produccion. La seccion 8 de la consigna permite codigo entregado como archivo; GitHub no es requisito obligatorio. Si se elige compartir por enlace, debe ser legible para el docente e incluirse en el informe final.

**Checklist de acceso y entrega, aun pendiente de comprobacion humana:**

- [ ] Identificar la version de entrega: paquete local existente `/Users/tamaraalison/Downloads/APF3_Grupo2_Alineado_V4`, su ZIP/checksum adyacentes y `manifest-entrega.json`. El empaquetado local no es publicacion remota ni prueba de descarga por el docente.
- [ ] Entregar fuentes V4 y `requirements.txt`, no solo una URL del MVP: el paquete contiene `codigo/scripts/academic_credit_aligned_v4.py`, generador y helpers, datos simulados, modelo y ejemplo; `README.md` describe reproduccion y limites de dependencias binarias. No modificarlo en esta edicion.
- [ ] Separar la copia previa [APF3_CV3](../entregables/APF3_CV3/) y su [politica de publicacion](PUBLICATION.md) de la entrega V4 local. Un repositorio/enlace GitHub que muestra CV3 no acredita acceso a V4; no se comprobo el remoto en esta edicion.
- [ ] Elegir entrega por archivos en Aula Virtual o enlace de lectura autorizado. En caso de enlace, probar con permisos equivalentes a los del docente, sin credenciales personales del grupo; registrar URL final/version y ponerla en el informe. No publicar para resolver un permiso sin autorizacion.
- [ ] Integrar este anexo mediante el agente del informe y volver a verificar enlaces, referencias y paginacion de la exportacion final: maximo 15 paginas de cuerpo, sin portada/referencias/anexos, y 13 slides. Este Markdown aun no esta integrado en PDF/DOCX/ZIP ni cubierto por sus manifiestos anteriores.
- [ ] Si se reorganiza la entrega, resolver las rutas de codigo de este archivo contra la estructura final: hoy son enlaces relativos validos al repositorio. Las rutas locales del paquete son inventario, no enlaces finales para el docente. Adjuntar o enlazar las evidencias de verificacion autorizadas necesarias.
- [ ] Revisar ausencia de PII real, secretos, formulario bruto del propietario, firmas, contactos, cuaderno y backups. Los nombres/codigos academicos no son predictores; su inclusion no autoriza divulgar documentos privados.
- [ ] Confirmar acceso al entorno de exposicion y su version. Hay laboratorio V4 probado **localmente**, posterior al texto del informe que solo describia CLI; la demo publica heredada/v2 no acredita V4. [Estado y controles locales](APF3_LABORATORIO_V4.md), L197-L247. No es obligatorio activar publicamente V4 para entregar el codigo.
- [ ] Mantener evidencia de la primera evaluacion y comprobaciones posteriores sin sobrescribir; localizar respaldo de 223 tests historicos si se pretende citarlos como verificados. Revisar por separado vulnerabilidades de dependencias documentadas en el laboratorio, sin declarar seguridad total.
- [ ] Cerrar revision individual y ensayo con evidencia autentica; recuperar historial literal IA anterior disponible o declarar su ausencia. No marcar entrega integral ni uso de IA totalmente documentado mientras estas brechas sigan abiertas.

**Brechas abiertas concretas:** historial literal IA anterior incompleto; validacion humana aplicada y ensayo sin constancias; fuente comercial aproximada; meta/costos y beneficio no validados; consentimiento/base juridica, ARCO y conservacion no cerrados; activacion publica V4 no autorizada; acceso efectivo del docente y enlaces finales por comprobar; integracion/exportacion de este anexo pendiente. La reproduccion tecnica con salvedad Joblib y las pruebas automaticas locales no cierran esas brechas.
