"""Incorpora la aclaracion del taller en la guia, sin editar la evidencia APF3."""

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
PREVIOUS_SHA = '0468b09fc75a52634274a151f31a89afcc01b33367150f8eae5d2e442c139c68'
MODELS = ['SVM', 'KNN', 'Arbol de decision', 'AdaBoost']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def add_before(anchor, text, style=None):
    return anchor.insert_paragraph_before(text, style=style)


def insert_table(doc, anchor, headers, rows):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = 'Light Shading Accent 1'
    for cell, value in zip(table.rows[0].cells, headers):
        cell.text = value
    for row in rows:
        for cell, value in zip(table.add_row().cells, row):
            cell.text = value
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(8.5)
    anchor._p.addprevious(table._tbl)


def amend(original):
    document = Document(io.BytesIO(original))
    heads = {p.text.split('. ', 1)[0]: p for p in document.paragraphs if p.style.name == 'Heading 1'}
    require(len(heads) == 24, 'Guia de origen inesperada')
    anchor = heads['1']
    add_before(anchor, 'ACLARACION PRIORITARIA: APLICAR TODO EL TALLER DE DONA ROSA', 'Heading 2')
    add_before(anchor, 'Segun la aclaracion del equipo sobre la instruccion del profesor, PROY debe aplicar '
               'SVM, KNN, Arbol de decision y AdaBoost, incluidos los retos de numero de vecinos y rondas. '
               'No basta con reutilizar la metodologia ni comparar solo dos modelos. Esta indicacion '
               'complementa el minimo general de la consigna; no afirma que esos modelos ya se hayan ejecutado.')
    add_before(anchor, 'APF3 V6 Final comparo SVM y arbol con dos Dummy: KNN y AdaBoost no se incluyeron. '
               'Conservar ese resultado enviado y completar los cuatro algoritmos en una nueva revision de PROY. '
               'Los Dummy se mantienen como referencias, pero no sustituyen los modelos del taller.')

    replacements = {
        'Comparar al menos modelos pertinentes y las mismas filas frente a referencias simples. Mantener claro RAW frente a acciones con cupo.':
            'Entrenar obligatoriamente los cuatro modelos del taller: SVM, KNN, Arbol de decision y AdaBoost, '
            'sobre las mismas particiones y contrato de datos de Baylon, junto con ambos Dummy. '
            'Comparar todos con las mismas metricas y distinguir RAW de politica con cupo.',
        'El tiempo de cada hito depende de la fecha real de entrega y disponibilidad del equipo. No se asignan fechas inventadas ni una duracion garantizada del piloto. Si el plazo no permite datos maduros, priorizar seguridad e integracion demostrable y declarar la validacion real pendiente.':
            'El tiempo de cada hito depende de la fecha real de PROY. Si no hay datos reales maduros '
            'adecuados, completar la comparacion academica de los cuatro modelos con datos simulados '
            'justificados y un protocolo nuevo, sin afirmar validacion real. La falta de datos reales '
            'no convierte KNN ni AdaBoost en extensiones opcionales de esta instruccion.',
    }
    seen = set()
    for paragraph in document.paragraphs:
        if paragraph.text in replacements:
            seen.add(paragraph.text)
            paragraph.text = replacements[paragraph.text]
    require(seen == set(replacements), 'Parrafos de actualizacion no encontrados')

    anchor = heads['13']
    add_before(anchor, '12.1. Transferencia completa del taller a Baylon', 'Heading 2')
    add_before(anchor, 'Reutilizar todos los procedimientos no significa copiar el CSV de 160 clientes, '
               'la definicion de mas de siete dias de mora, los resultados AdaBoost ni el costo de S/150 '
               'por FN como si fueran datos de Baylon. Conservar la continuidad del fiado a un dia '
               'y las reglas del propietario; documentar cada adaptacion.')
    insert_table(document, anchor, ['Modelo obligatorio', 'Trabajo para el companero', 'Evidencia de cierre'], [
        ('SVM', 'Comparar SVM lineal; justificar C, pesos, escalado y calibracion agrupada. '
         'La calibracion moderna puede sustituir probability=True del ejemplo sin cambiar la familia.',
         'OOF, hiperparametros, umbral, TRAIN/validacion y test nuevo; no heredar ganador.'),
        ('KNN', 'Aplicar el reto de vecinos k=1,3,5,7,9, sujeto a factibilidad declarada antes de resultados. '
         'Imputacion y escalado dentro del Pipeline de cada fold; discutir distancias y redundancia de variables.',
         'Tabla/grafico k frente a metricas y seleccion solo sobre DEV; documentar casos inviables.'),
        ('Arbol de decision', 'Partir de la referencia depth=3 del taller y declarar control de profundidad/hojas. '
         'Mostrar reglas o un camino real y comparar ajuste aparente con validacion.',
         'Arbol/reglas interpretables, parametros y errores; no causas o garantias de pago.'),
        ('AdaBoost', 'Aplicar la referencia de 50 estimadores y el reto de 50 frente a 400 rondas. '
         'Declarar estimador debil, semilla y parametros compatibles con la version fijada.',
         'Tabla/grafico de rondas, metricas, brecha TRAIN/validacion y justificacion del ganador.'),
    ])
    add_before(anchor, 'Declarar las grillas antes del ajuste. Si el docente confirma valores exactos '
               'adicionales, reflejarlos en el protocolo nuevo. No probar k o rondas en FINAL ni '
               'cambiar el generador para que un algoritmo gane. AdaBoost no debe ganar por haber '
               'ganado en Dona Rosa, ni SVM por haber ganado en el APF3.')
    add_before(anchor, '12.2. Correspondencia de todos los pasos del taller', 'Heading 2')
    insert_table(document, anchor, ['Paso del taller', 'Aplicacion requerida en el proyecto'], [
        ('0. Entorno', 'Notebook o script ejecutable, versiones fijadas, semillas y salida de ejecucion limpia.'),
        ('1. Carga y exploracion', 'Datos Baylon trazables y rotulados; validaciones, estadisticos y dos relaciones explicadas.'),
        ('2. Separacion y escalado', 'Particiones por cliente/tiempo adecuadas; fit de transformaciones solo en entrenamiento.'),
        ('3. SVM', 'Entrenamiento y evaluacion del SVM bajo el protocolo nuevo.'),
        ('4. KNN', 'Entrenamiento y reto de vecinos con seleccion solo en desarrollo.'),
        ('5. Arbol', 'Entrenamiento, control de complejidad y lectura de reglas.'),
        ('6. AdaBoost', 'Entrenamiento y reto de cantidad de estimadores, sin consultar test para elegir.'),
        ('7. Comparacion y costo', 'Una tabla con las cuatro familias y Dummy, mismas filas/metricas; FN/FP y costos medidos o supuestos identificados.'),
        ('8. Umbral y prioridad', 'Retomar curva/tabla de umbrales y top-k o cola. Diez llamadas era el taller; no imponer diez fiados o contactos en Baylon. Acordar capacidad y finalidad.'),
        ('9. Conclusiones', 'Elegir por evidencia DEV, reportar prueba cerrada e interpretar utilidad, errores, privacidad e integracion en el MVP.'),
    ])
    add_before(anchor, 'No copiar la exploracion repetida del test del taller: PROY debe mantener una '
               'prueba nueva sin consultar hasta congelar modelo y umbral. Las etiquetas pueden '
               'evaluar un top-k, pero no ordenan las acciones reales. No usar costos didacticos '
               'como costos monetarios del propietario ni equiparar atraso con perdida definitiva.')
    add_before(anchor, '12.3. Paquete minimo de evidencia de la comparacion completa', 'Heading 2')
    for text in (
        'Notebook ejecutado con los diez pasos adaptados y una tabla de correspondencia con el taller.',
        'Resultados reales de SVM, KNN, arbol, AdaBoost y dos Dummy, sin casillas rellenadas con numeros del taller o de otra particion.',
        'Retos de k y de rondas, parametros, semillas y folds guardados, matrices y al menos tres errores explicados como hipotesis.',
        'Ganador seleccionado solo con DEV, artefacto con preprocesamiento exportado y una prediccion en vivo desde el modelo cargado.',
        'Registro de lo que mejora y lo que no: presupuesto de revision, FN/FP, limitaciones sinteticas y tareas humanas pendientes.',
    ):
        add_before(anchor, text, 'List Bullet')

    backlog = next(t for t in document.tables if t.cell(0, 0).text == 'ID / prioridad')
    cells = backlog.add_row().cells
    cells[0].text = 'P0-05 / requisito docente'
    cells[1].text = 'Incluir todos los modelos y retos del taller: SVM, KNN, arbol y AdaBoost, mas Dummy.'
    cells[2].text = 'Planificar desde el inicio; completar los pasos 0-9 adaptados con comparacion y seleccion sin fuga.'
    for table in document.tables:
        for row in table.rows:
            if row.cells[0].text == 'P2-01':
                row.cells[1].text = 'Ejecutar la nueva revision PROY con los cuatro modelos del taller; datos reales adecuados o simulacion justificada.'
                row.cells[2].text = 'Protocolo nuevo, retos KNN/AdaBoost, baselines y test no consultado. No alterar APF3.'
    tests = next(t for t in document.tables if t.cell(0, 0).text == 'ID' and t.cell(0, 1).text == 'Caso')
    cells = tests.add_row().cells
    cells[0].text = 'T26'
    cells[1].text = 'Cobertura del taller completo: SVM, KNN, arbol y AdaBoost; retos de k y rondas.'
    cells[2].text = 'Los cuatro entrenados en mismas particiones; tablas/retos completos, ganador DEV y test nuevo sin reutilizar FINAL APF3.'
    add_before(heads['22'], '[ ] Cuatro modelos del taller ejecutados: SVM, KNN, arbol y AdaBoost; retos de vecinos y rondas, costos/umbrales y pasos 0-9 documentados.', 'List Bullet')
    document.core_properties.comments = 'Guia actualizada: aplicar integralmente el taller Dona Rosa en PROY; APF3 se conserva.'
    stream = io.BytesIO()
    document.save(stream)
    result = stream.getvalue()
    with ZipFile(io.BytesIO(result)) as archive:
        require(archive.testzip() is None, 'Word no valido')
    reopened = Document(io.BytesIO(result))
    full = '\n'.join(p.text for p in reopened.paragraphs) + '\n'.join(
        cell.text for table in reopened.tables for row in table.rows for cell in row.cells)
    for text in ('P0-05', 'T26', 'k=1,3,5,7,9', '50 frente a 400', 'KNN', 'AdaBoost',
                 'No basta con reutilizar la metodologia', 'No copiar la exploracion repetida del test'):
        require(text in full, f'Contenido faltante: {text}')
    require(len([p for p in reopened.paragraphs if p.style.name == 'Heading 1']) == 24,
            'Secciones principales perdidas')
    return result


def main():
    local = Path.home() / 'Downloads' / NAME
    tracked = ROOT / NAME
    original = tracked.read_bytes()
    require(sha(original) == PREVIOUS_SHA and local.read_bytes() == original,
            'La guia cambio desde la revision; no sobrescribir')
    manifest_path = ROOT / 'inventario-traspaso.json'
    manifest = json.loads(manifest_path.read_bytes())
    for name, expected in manifest['files'].items():
        if name != 'README.md':
            require(sha((ROOT / name).read_bytes()) == expected, f'Cambio ajeno: {name}')
    result = amend(original)
    for path in (local, tracked):
        require(path.read_bytes() == original, 'Cambio concurrente en Word')
    # Los mismos bytes se guardan en ambas ubicaciones; sin tocar archivos APF3.
    for path in (local, tracked):
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.docx', delete=False) as tmp:
            temp = Path(tmp.name)
            tmp.write(result)
        temp.replace(path)
    manifest['files'][NAME] = sha(result)
    manifest['files']['README.md'] = sha((ROOT / 'README.md').read_bytes())
    manifest['guide_amendment'] = {
        'previous_sha256': PREVIOUS_SHA, 'current_sha256': sha(result),
        'scope': 'Aclaracion del equipo: todos los modelos y procedimientos del taller para PROY',
        'required_models': MODELS, 'implementation_status': 'Pendiente de ejecutar en PROY',
        'apf3_evidence_changed': False,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    require(local.read_bytes() == tracked.read_bytes(), 'Copias Word distintas')
    require(all(sha((ROOT / name).read_bytes()) == expected
                for name, expected in manifest['files'].items()), 'Inventario incorrecto')
    print(json.dumps({'guide': str(local), 'sha256': sha(result), 'required_models': MODELS,
                      'apf3_unchanged': True, 'both_copies_equal': True}, indent=2))


if __name__ == '__main__':
    main()
