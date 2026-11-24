"""Integra feedback en la guia y sus copias; no cambia el experimento enviado."""

import hashlib
import io
import json
from pathlib import Path
import tempfile
from zipfile import ZipFile

from docx import Document
from docx.shared import Pt

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / 'entregables/PROY_Grupo2'
NAME = 'Guia_Traspaso_PROY_Grupo2_Credify.docx'
PREVIOUS_SHA = 'b62b64a3d4b2238b5e8efbf119ff875a43170e6c50b1de343d38305877e6cc14'
FEEDBACK_SHA = '3868059e689b5ece2fc1a912eac73f5da1df39d8f3d1f30ff6c49d68b9572606'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def paragraph(doc, text, style=None):
    return doc.add_paragraph(text, style=style)


def table(doc, headers, rows):
    value = doc.add_table(rows=1, cols=len(headers))
    value.style = 'Light Shading Accent 1'
    for cell, text in zip(value.rows[0].cells, headers):
        cell.text = text
    for row in rows:
        for cell, text in zip(value.add_row().cells, row):
            cell.text = text
    for row in value.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(8.5)
    return value


def amend(original):
    doc = Document(io.BytesIO(original))
    headings = [p for p in doc.paragraphs if p.style.name == 'Heading 1']
    require(len(headings) == 24, 'Guia de origen inesperada')
    first = next(p for p in doc.paragraphs if p.style.name == 'Heading 2'
                 and p.text.startswith('ACLARACION PRIORITARIA:'))
    first.insert_paragraph_before('FEEDBACK DOCENTE: PRIORIDAD CRITICA DE CIERRE', 'Heading 2')
    first.insert_paragraph_before(
        'El grupo confirma que realizo la revision humana, pero el docente encuentra estados '
        'PENDIENTE y ausencia de cuatro revisiones individuales firmadas. Aportar evidencia real '
        'y aclarar la version oficial por el canal docente; no fabricar firmas, fechas ni '
        'cambiar hashes historicos. Ver seccion 25 y FEEDBACK_DOCENTE_APF3.md.')
    first.insert_paragraph_before(
        'El feedback corrobora las metricas y la reproduccion tecnica. Lo urgente es coherencia '
        'de evidencias y cierre del flujo operativo; no repetir entrenamientos para buscar una '
        'mejor nota. Se mantienen obligatorios SVM, KNN, arbol y AdaBoost para PROY.')

    doc.add_page_break()
    doc.add_heading('25. Plan de cierre del feedback docente APF3', level=1)
    paragraph(doc, 'Fuente: Reporte_APF3_GB2_SARYON.pdf, cinco paginas, proporcionado por el equipo. '
              'SHA-256: ' + FEEDBACK_SHA + '. Este apartado registra observaciones y acciones; '
              'no altera el reporte, el APF3 presentado ni su calificacion. La aceptacion del '
              'cierre de observaciones corresponde al docente.')
    table(doc, ['ID / prioridad', 'Accion del companero y del equipo', 'Evidencia de cierre'], [
        ('F01 / critica', 'Acreditar revision humana y conciliar estados realizados/pendientes.',
         'Cuatro revisiones reales con alcance, version/hash, fecha real y firma o confirmacion aceptada por el docente; entrega privada.'),
        ('F02 / alta', 'Fijar documento oficial y una nueva entrega PROY canonica y legible.',
         'Comprobante del Aula, PDF/ZIP identificado por hash, mapa de versiones y verificacion visual de tablas/paginas.'),
        ('F03 / alta', 'Separar igualdad exacta de equivalencia numerica en el nuevo verifier.',
         'Allowlist por campo, abs_tol/rel_tol, deltas y pruebas positivas/negativas; sin ocultar cambios de clase o hashes.'),
        ('F04 / alta', 'Ampliar clientes y cuantificar incertidumbre por cliente.',
         'Protocolo nuevo, factibilidad de folds, roster justificado e intervalos bootstrap agrupados reproducibles.'),
        ('F05 / alta', 'Demostrar endpoint operativo e interfaz con modelo realmente invocado.',
         'Solicitud autenticada, snapshot servidor, version/hash del artefacto, resultado mostrado y auditoria; pruebas E2E y rollback.'),
        ('F06 / alta', 'Medir capacidad y costos con Rildo antes de fijar nueva familia/umbral.',
         'Registro de tiempos, FN/FP y consecuencias; tolerancias y objetivo acordados antes del test nuevo.'),
        ('F07 / alta', 'Asignar responsables concretos y fechas aceptadas.',
         'Nombre real por tarea, aceptacion, fecha objetivo, prueba de cierre y persona que valida.'),
        ('F08 / media', 'Preparar la defensa y preservar las fortalezas del avance.',
         'Replay, Brier explicado, seleccion OOF, limites de precision, demo elegible y respaldo preparados.'),
        ('F09 / aclaracion', 'Confirmar diferencias de nota y cifras/versiones citadas.',
         'Consulta al docente; no anunciar 17.9 o 16.9 como nota definitiva ni corregir su reporte por cuenta propia.'),
    ])

    doc.add_heading('25.1. Revision humana: que se debe entregar realmente', level=2)
    paragraph(doc, 'La confirmacion del grupo de que reviso no sustituye el archivo que solicita '
              'el profesor. Documentar que reviso cada integrante, hallazgos/correcciones, '
              'version y hash y fecha real. Si la revision ocurre ahora, usar la fecha actual; '
              'no antedatarla para aparentar una constancia contemporanea al envio. Si ya '
              'ocurrio pero no existe registro, explicarlo con honestidad.')
    paragraph(doc, 'Los estados historicos de PENDIENTE se preservan. Crear un registro actual '
              'separado y una nota que enlace las versiones y sus momentos. No cambiar el JSON '
              'congelado a realizada ni recalcular su hash como si asi se hubiera entregado. '
              'Si se requiere aclarar APF3 antes de cerrar nota, coordinar con todo el grupo y '
              'solicitar el procedimiento al docente; no reemplazar el envio sin autorizacion.')
    paragraph(doc, 'Plantilla de constancia, NO firmada y NO acreditada por esta guia:', 'Heading 3')
    table(doc, ['Integrante', 'Version/hash y alcance revisado', 'Fecha real', 'Firma/confirmacion'], [
        ('O. Baylon', 'Completar personalmente', 'Completar', 'Completar por el integrante'),
        ('T. Covenas', 'Completar personalmente', 'Completar', 'Completar por el integrante'),
        ('C. Paredes', 'Completar personalmente', 'Completar', 'Completar por el integrante'),
        ('P. Yman', 'Completar personalmente', 'Completar', 'Completar por el integrante'),
    ])
    paragraph(doc, 'Recoger las firmas o confirmaciones autenticas por el medio que acepte el '
              'docente. No publicar firmas manuscritas, DNI o constancias privadas en GitHub: '
              'entregar la evidencia sensible al profesor y mantener publico solo un resumen '
              'de estado adecuado. La guia no resuelve por si sola la observacion ni elimina '
              'la posible penalizacion de la seccion 11.')

    doc.add_heading('25.2. Una version oficial y formato realmente legible', level=2)
    paragraph(doc, 'El docente reviso un ZIP publico de 149 archivos y un informe entregado '
              'con otro nombre/extension. Registrar cual PDF/ZIP se presento con el comprobante '
              'del Aula, no por fecha o sufijo. Conservar esa evidencia sin cambios. Publicar '
              'una version nueva de PROY con un indice de archivos oficiales y otra carpeta '
              'de antecedentes, evitando varios PDF candidatos al mismo nivel.')
    paragraph(doc, 'Conciliar la referencia a pruebas-reglas-previas.json: identificar el archivo '
              'que reviso el docente, el registro complementario posterior y su ruta/hash. No '
              'afirmar que esta o falta sin cotejar la version exacta. Una ejecucion nueva no '
              'restaura un registro historico ni prueba cuando se hizo la anterior.')
    paragraph(doc, 'Para el nuevo informe, verificar el PDF exportado, no solo Word: contar '
              'cuerpo sin portada/referencias/anexos segun la consigna aplicable, examinar '
              'visualmente tablas de las paginas observadas 13-15 y revisar en otro visor. '
              'Usar anchos de columna razonables, encabezados repetidos, fuente legible y '
              'anexos para detalle. No asegurar que el problema esta cerrado solo porque una '
              'version local anterior contaba 15 paginas. Confirmar los limites de PROY.')

    doc.add_heading('25.3. Tolerancia flotante: Brier no es una metrica fabricada', level=2)
    paragraph(doc, 'El profesor reprodujo las cifras y observo tres cambios de Brier en torno '
              'al digito 16, mas la probabilidad ilustrativa 0.15310676521820044 frente a '
              '0.15310676521820216. Mantener ambos valores; no cambiar la salida publicada '
              'ni redondear entradas para forzar coincidencia.')
    paragraph(doc, 'PROPUESTA para una nueva version del comparador: abs_tol=1e-12 y rel_tol=0 '
              'solo para Brier y probabilidad ilustrativa, con justificacion, deltas y entorno. '
              'La guia no implementa esa politica: hay que escribirla, probarla y versionarla. '
              'R2 no aplica a esta clasificacion binaria y no debe agregarse para seguir una '
              'recomendacion generica pensada tambien para regresion.')
    paragraph(doc, 'Separar exact_raw_and_policy_reports de numerically_equivalent y '
              'classification_behavior_match. Si los bytes/numeros no son identicos, conservar '
              'exact=false aunque se cumpla la tolerancia. Matrices, etiquetas, conteos, '
              'acciones de cola, decisiones, familia/parametros, umbral y hashes se comparan '
              'exactamente. No tolerar NaN/inf ni un cambio de clase porque un score cercano '
              'al umbral caiga dentro de abs_tol. Comparar la decision de seleccion por sus '
              'campos, no todo el registro OOF que contiene Brier.')
    paragraph(doc, 'Tests minimos: delta dentro/fuera de tolerancia, NaN/inf, clase distinta con '
              'score cercano, un conteo cambiado, hash alterado y campo no autorizado. El '
              'verifier debe fallar ante cambios reales y mostrar la ruta concreta de cada '
              'diferencia aceptada. No sustituir todas las comparaciones por allclose.')

    doc.add_heading('25.4. Mas clientes y bootstrap por cliente', level=2)
    paragraph(doc, 'Los 12 clientes por historia son pocos clusters para valorar generalizacion. '
              'Definir antes del nuevo entrenamiento una ampliacion justificada de clientes, '
              'periodos y casos por clase, y comprobar viabilidad de todos los folds externos '
              'e internos con grupos disjuntos. No aumentar solo filas repetidas, renombrar '
              'copias o forzar resultados. Un roster sintetico ampliado sigue siendo simulado '
              'y no representa una poblacion real medida sin fuente.')
    paragraph(doc, 'Predeclarar intervalos bootstrap por cliente: remuestrear IDs de cliente '
              'con reemplazo y llevar todas sus observaciones con su multiplicidad, no '
              'remuestrear fiados como independientes. Propuesta metodologica a justificar: '
              'IC 95%, 2000 remuestreos y semilla fija; definir estimando, n de clientes, '
              'metodo del intervalo y tratamiento de muestras sin ambas clases. Reportar '
              'indefinidos/exclusiones y la inestabilidad con pocos clientes, sin buscar otra '
              'semilla para estrechar el intervalo.')
    paragraph(doc, 'Comenzar por metricas RAW desde scores guardados del modelo fijo. Para '
              'POLICY, la competencia y capacidad diaria requieren un procedimiento separado '
              'explicito; no promediar intervalos por fila ni fingir que una cola remuestreada '
              'es una operacion real. No usar intervalos del test para cambiar el ganador. '
              'Un anexo bootstrap post hoc de APF3 debe identificarse como tal; la nueva '
              'evaluacion de PROY requiere protocolo y prueba no consultada.')

    doc.add_heading('25.5. Endpoint operativo y prueba de circuito completo', level=2)
    paragraph(doc, 'El feedback deja pendiente POST /api/v1/scoring y no acredita la integracion '
              'operativa a partir de la pantalla de laboratorio. El laboratorio academico '
              'existente no equivale al flujo transaccional. Para cerrar: implementar y '
              'documentar un endpoint autenticado de PROY, primero en staging, que construya '
              'el snapshot del servidor, aplique gates y cargue el artefacto confiable exportado.')
    paragraph(doc, 'Proponer entrada operativa client_id/monto y obtener el historial desde '
              'PostgreSQL; documentar su transformacion al contrato interno de once campos. '
              'No confiar en deuda o historial financieros aportados libremente por el navegador. '
              'Salida: ID de evaluacion, estado, razon, modelo/esquema/politica, score/umbral '
              'solo si elegible y decision humana separada. Resolver primero las brechas '
              'de deuda, override y concurrencia de las secciones 6-10.')
    paragraph(doc, 'Evidencia E2E: solicitud JSON autenticada y respuesta, snapshot calculado, '
              'hash/version del artefacto realmente cargado, traza sanitizada de predict y '
              'pantalla del MVP mostrando ese resultado. No basta HTTP 200 de la portada '
              'ni mostrar un JSON almacenado. Cachear el modelo cargado en memoria es '
              'distinto de responder una prediccion prefabricada; demostrar la nueva llamada.')
    paragraph(doc, 'Pruebas: sin login/rol, entrada invalida, cliente inaccesible, modelo '
              'incompatible, bloqueo por deuda, ausencia de historial y elegible; fallos '
              'seguros con nulls y sin aprobacion automatica. Acreditar snapshot, auditoria, '
              'rollback y limites de proveedores/consentimiento. Probar con datos ficticios '
              'antes de un piloto real; este documento no autoriza despliegues productivos.')

    doc.add_heading('25.6. Capacidad, costos y nuevo umbral con el propietario', level=2)
    paragraph(doc, 'Llevar a Rildo la consecuencia concreta: 100 alertas, 32 atrasos detectados, '
              '68 falsas alertas y nueve omisiones. El valor F2 no decide por si solo utilidad. '
              'Tres alertas por dia fue un maximo observado en la simulacion; cinco por dia '
              'y dos minutos por caso no son capacidad ni tiempos reales medidos.')
    paragraph(doc, 'Cronometrar tareas y carga total, incluyendo primera revision obligatoria, '
              'falsas alertas, correcciones, rezagos y uso del sistema. Definir que perjuicio '
              'produce un atraso, cuanto cuesta revisar y que tolerancias/pausas acepta el '
              'propietario. No usar S/150 del taller ni igualar atraso con perdida definitiva. '
              'Registrar aceptacion real, fecha y alcance; la meta futura de reduccion de '
              'tiempo >=10% sigue siendo una propuesta no aceptada ni demostrada.')
    paragraph(doc, 'Fijar criterio comercial, candidatos y procedimiento antes de comparar '
              'familias/umbrales en DEV de PROY. Congelar decision antes del nuevo test. '
              'No promover el arbol por ganar FINAL APF3 ni conservar SVM/umbral 0.1 por '
              'inercia. Mantener SVM, KNN, arbol y AdaBoost mas Dummy: los cuatro modelos '
              'contados en el reporte son dos algoritmos mas dos Dummy, no los cuatro '
              'algoritmos del taller requeridos por la aclaracion del equipo.')

    doc.add_heading('25.7. Responsables con nombres, no solo cargos', level=2)
    paragraph(doc, 'El equipo debe completar y aceptar el reparto. No se asignan nombres ni '
              'fechas inventadas por esta guia. Una sola persona puede asumir varios frentes '
              'si lo acepta y la carga es viable; cada tarea necesita evidencia y revisor.')
    table(doc, ['Frente', 'Responsable con nombre', 'Fecha acordada', 'Cierre / revisor'], [
        ('Revision humana / aclaracion docente', 'Por acordar por el grupo', 'Por acordar', 'Constancias y respuesta docente'),
        ('Version oficial y legibilidad', 'Por acordar por el grupo', 'Por acordar', 'Archivo/hash y revision visual'),
        ('Comparador, roster y bootstrap', 'Por acordar por el grupo', 'Por acordar', 'Tests y protocolo nuevo'),
        ('API, UI, auditoria y rollback', 'Por acordar por el grupo', 'Por acordar', 'Prueba E2E y QA'),
        ('Medicion / validacion con Rildo', 'Por acordar por el grupo', 'Por acordar', 'Registro y criterios aceptados'),
        ('Demo y entrega PROY', 'Por acordar por el grupo', 'Por acordar', 'Ensayo y comprobante del Aula'),
    ])

    doc.add_heading('25.8. Defensa y fortalezas que deben conservarse', level=2)
    paragraph(doc, 'El docente informa que ejecuto el replay en limpio y recargo el joblib. '
              'Conservar seeds, freeze, ledger, gates y limites honestos; no hay observacion '
              'de metricas inventadas o seleccion por FINAL. Su ejecucion propia corrobora '
              'reproducibilidad, pero no es un nuevo test de otra poblacion ni validacion comercial.')
    paragraph(doc, 'Preparar respuestas breves: revision y version oficial; significado de '
              'las tres diferencias Brier; por que SVM se eligio en OOF aunque arbol gane '
              'FINAL; costo de 68 FP/9 FN; capacidad real aun no medida; diferencia entre '
              'laboratorio y endpoint operativo. El feedback pide ejecutar el replay '
              'frente al docente: dejar el entorno instalado y coordinar ese espacio, '
              'sin sustituirlo por verify-only. Ensayar tambien la inferencia elegible '
              'en vivo y acordar como encajan ambas pruebas en el tiempo disponible.')

    doc.add_heading('25.9. Aclaraciones que requieren consulta, no una correccion unilateral', level=2)
    paragraph(doc, 'El encabezado del reporte propone 17.9/20, mientras la tabla totaliza '
              '16.9/20 y sus siete filas suman 16.9. El indicador de sustentacion dice '
              'maximo asignado pero muestra 1.00 de 2.00. Confirmar la nota definitiva '
              'con el docente; no interpretar ni aplicar penalizaciones por cuenta propia.')
    paragraph(doc, 'Cotejar tambien version y conteo de paginas que evaluo, cifras de '
              'solicitudes por semana y terminologia de preprocesamiento con artefactos '
              'reales. No copiar la cifra 421 intentos/semana como volumen del negocio '
              'ni confundir totals de dos historias con una tienda. Si se usa Pipeline '
              'sin ColumnTransformer, documentar el objeto real. Estas aclaraciones '
              'no invalidan el feedback ni autorizan alterar su texto.')

    backlog = next(t for t in doc.tables if t.cell(0, 0).text == 'ID / prioridad')
    cells = backlog.add_row().cells
    cells[0].text = 'P0-F / feedback docente'
    cells[1].text = 'Resolver F01-F09 de la seccion 25, antes de declarar cerradas las observaciones.'
    cells[2].text = 'Evidencias reales y responsables aceptados; conformidad docente donde corresponda, no solo guia actualizada.'
    acceptance = next(t for t in doc.tables if t.cell(0, 0).text == 'ID' and t.cell(0, 1).text == 'Caso')
    for row in [
        ('T27', 'Comparador con tolerancias por campo y negativos.', 'Tol explicita; deltas registrados; cambios de clase/hash/conteo rechazan; exact=false no se maquilla.'),
        ('T28', 'Bootstrap agrupado y roster del protocolo PROY.', 'Remuestreo por cliente, semilla/metodo declarados, intervalos e indefinidos; sin tuning de FINAL.'),
        ('T29', 'POST /api/v1/scoring y recorrido MVP real.', 'Artefacto cargado, snapshot servidor, gates y respuesta mostrada con auditoria; no solo cache o HTTP 200.'),
    ]:
        for cell, text in zip(acceptance.add_row().cells, row):
            cell.text = text
    doc.core_properties.comments = 'Guia con feedback docente F01-F09 y cuatro algoritmos del taller; tareas aun pendientes.'
    output = io.BytesIO()
    doc.save(output)
    result = output.getvalue()
    with ZipFile(io.BytesIO(result)) as archive:
        require(archive.testzip() is None, 'Word invalido')
    reopened = Document(io.BytesIO(result))
    require(len([p for p in reopened.paragraphs if p.style.name == 'Heading 1']) == 25, 'Secciones perdidas')
    require(len(reopened.tables) == 22, 'Tablas esperadas ausentes')
    return result


def main():
    tracked, local = ROOT / NAME, Path.home() / 'Downloads' / NAME
    original = tracked.read_bytes()
    require(sha(original) == PREVIOUS_SHA and local.read_bytes() == original,
            'Guia modificada desde la revision; no sobrescribir')
    source = Path.home() / 'Downloads/Reporte_APF3_GB2_SARYON.pdf'
    require(sha(source.read_bytes()) == FEEDBACK_SHA, 'Feedback distinto de la fuente revisada')
    path = ROOT / 'inventario-traspaso.json'
    manifest = json.loads(path.read_bytes())
    protected = {n: value for n, value in manifest['files'].items() if n not in (NAME, 'README.md')}
    require(all(sha((ROOT / n).read_bytes()) == value for n, value in protected.items()), 'Cambio ajeno en APF3')
    result = amend(original)
    require(tracked.read_bytes() == local.read_bytes() == original, 'Cambio concurrente')
    for target in (tracked, local):
        with tempfile.NamedTemporaryFile(dir=target.parent, suffix='.docx', delete=False) as tmp:
            temporary = Path(tmp.name)
            tmp.write(result)
        temporary.replace(target)
    manifest['files'][NAME] = sha(result)
    manifest['files']['README.md'] = sha((ROOT / 'README.md').read_bytes())
    manifest['files']['FEEDBACK_DOCENTE_APF3.md'] = sha((ROOT / 'FEEDBACK_DOCENTE_APF3.md').read_bytes())
    manifest['guide_amendment']['current_sha256'] = sha(result)
    manifest['teacher_feedback_amendment'] = {
        'previous_guide_sha256': PREVIOUS_SHA, 'current_guide_sha256': sha(result),
        'feedback_source_sha256': FEEDBACK_SHA, 'action_ids': ['F%02d' % n for n in range(1, 10)],
        'implementation_status': 'Plan pendiente; sin firmas, endpoint, piloto ni intervalos nuevos acreditados',
        'apf3_evidence_changed': False, 'raw_feedback_published': False,
    }
    path.write_text(json.dumps(manifest, indent=2) + '\n')
    require(local.read_bytes() == tracked.read_bytes(), 'Copias distintas')
    require(all(sha((ROOT / n).read_bytes()) == value for n, value in manifest['files'].items()), 'Inventario inconsistente')
    print(json.dumps({'word': str(local), 'sha256': sha(result), 'sections': 25, 'tables': 22,
                      'feedback_actions': 9, 'protected_apf3_files_unchanged': len(protected)}, indent=2))


if __name__ == '__main__':
    main()
