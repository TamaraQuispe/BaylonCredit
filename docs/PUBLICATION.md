# Publicación Del Proyecto

Esta publicación reúne el código de la aplicación, pruebas, scripts operativos y
materiales académicos revisados. `develop` y `main` deben recibir el mismo contenido
mediante actualizaciones normales, sin reescribir el historial remoto.

## Separación De Entornos

- Subir código no equivale a desplegarlo. El workflow GitHub Actions ejecuta lint,
  build y pruebas; no contiene una tarea de despliegue del negocio.
- Los Compose de demo, laboratorio y resiliencia son herramientas diferentes.
  Los scripts de fallos detienen únicamente contenedores locales de pruebas.
- Los modelos académicos CV3 no autorizan créditos reales. Su informe mantiene
  el bajo recall y las limitaciones de fuente, selección y calibración.
- No ejecutar scripts que escriban en demo, consulten producción o inyecten fallos
  como parte de la publicación o de CI.

## Procedencia De Entregables

`entregables/APF3_CV3` conserva una copia de la entrega técnica congelada, incluida
su reproducción limpia. Los CSV y las operaciones de esos experimentos son
sintéticos y están rotulados. Las métricas no representan resultados del negocio.

La ficha completada recibida después del experimento declara que sus cifras se
obtuvieron de `final.csv` y que las demás respuestas son hipotéticas. Se publica
por separado en `entregables/APF3_CV3/escenarios`, con ese alcance explícito. No se
incorpora como evidencia independiente de entrevista o calibración y no cambia
los parámetros ni resultados del experimento publicado.

Los documentos APF1/APF2 bajo `docs/` son antecedentes o insumos de trabajo, no una
certificación del estado vigente. Sus referencias a firmas o documentos externos
no incorporan esas imágenes ni acreditan permiso para publicarlas. Se omiten
identificadores tributarios y domicilio exacto innecesarios en las copias públicas.
Los originales de trabajo permanecen fuera de esta publicación.

## Exclusiones

No se incluyen configuraciones `.env` completas, llaves privadas, tokens de API,
credenciales del negocio, respaldos de bases, firmas, documentos de identidad,
cuadernos ni operaciones reales identificables de clientes. Las credenciales
fijas que aparecen en fixtures y Compose de resiliencia corresponden únicamente
a datos ficticios y servicios aislados de prueba.

Los nombres y códigos de autoría académica fueron proporcionados por el grupo
para los entregables. No son predictores ni identificadores de clientes del dataset.
No se atribuyen nuevas entrevistas, firmas, revisión humana o aprobación docente
por el mero hecho de subir un documento a GitHub.
