"""Create an unfilled follow-up validation form, separate from the first session."""

import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


def generate(output: Path) -> None:
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin = section.bottom_margin = Cm(1.8)
    section.left_margin = section.right_margin = Cm(1.8)
    normal = doc.styles['Normal']
    normal.font.name, normal.font.size = 'Calibri', Pt(10)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.05
    doc.core_properties.title = 'APF2 - Revalidación con Rildo después de las mejoras'
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run('Grupo 2 | Segunda prueba del MVP | Página ')
    field = OxmlElement('w:fldSimple')
    field.set(qn('w:instr'), 'PAGE')
    footer._p.append(field)

    doc.add_heading('Revalidación del MVP después de las mejoras', 0)
    doc.add_paragraph('Credify · Cervecería Baylón · APF2 · Grupo 2')
    doc.add_paragraph('Participante: Rildo Baylón Espíritu')
    doc.add_paragraph('Facilitadora: Omara Baylon    Observador: Pablo Yman')
    doc.add_paragraph('Fecha real: ____ / ____ / ______    Lugar/modalidad: _______________________')
    doc.add_paragraph('Hora de inicio: __________    Hora de fin: __________    Zona horaria: _________')
    doc.add_paragraph('Dispositivo y navegador: _______________________________________________')
    doc.add_paragraph('Demo: https://demo-credify.168-75-71-113.sslip.io')
    doc.add_paragraph('Esta ficha documenta una segunda sesión. No reemplaza ni cambia los resultados de la primera prueba del 06/10/2026. No completar fecha, tiempos o aceptación antes de realizarla.')

    doc.add_heading('1. Autorización y preparación', 1)
    doc.add_paragraph('Prueba académica voluntaria con clientes y operaciones ficticios. La evaluación es orientativa por reglas y no garantiza el pago. No usar datos reales ni modificar producción; Rildo puede detener la sesión.')
    doc.add_paragraph('Autoriza notas: [ ] Sí  [ ] No    Capturas: [ ] Sí  [ ] No')
    doc.add_paragraph('Grabación: [ ] Autoriza  [ ] No autoriza  [ ] No se realizará')
    doc.add_paragraph('Cliente(s) DEMO utilizado(s), sin datos reales: ______________________________')
    doc.add_paragraph('Código del fiado de esta segunda prueba, cuando se cree: ____________________')

    doc.add_heading('2. Tareas y resultados', 1)
    doc.add_paragraph('Omara lee la tarea sin indicar cada clic. Pablo anota duración, ayudas y dificultades. Si se indica dónde hacer clic, cuenta como ayuda. Registrar también las tareas no probadas.')
    table = doc.add_table(rows=1, cols=4)
    table.style = 'Table Grid'
    for cell, title in zip(table.rows[0].cells, ['Tarea / mejora', 'Resultado', 'Tiempo / ayudas', 'Problema o comentario'], strict=True):
        cell.text = title
    tasks = [
        '1. Buscar cliente DEMO y abrir detalle sin hover. R01: la edición no implementada debe verse deshabilitada.',
        '2. Comparar contador y listado de clientes sin filtros. R02: número de registros cargados coherente.',
        '3. Distinguir nombres iguales por DNI/RUC ficticio. R03: si no existen nombres iguales, marcar No probó.',
        '4. Evaluar S/ 50 en cliente sin historial y explicar el aviso. R07: no confundir indicador con garantía de pago.',
        '5. Registrar fiado S/ 50 a un día y consultar listado/detalle. R04: vencimiento y singular/plural correctos.',
        '6. Abonar S/ 20 en ese fiado. R05: monto inicialmente vacío; pago total solo por acción expresa.',
        '7. Consultar saldo e historial. R06: S/ 30 pendiente y fechas comprensibles.',
    ]
    for task in tasks:
        row = table.add_row().cells
        row[0].text = task
        row[1].text = '[ ] Logró\n[ ] No logró\n[ ] No probó'
        row[2].text = 'Tiempo: ______\nAyudas: ______'
        row[3].text = '________________\n________________'
    doc.add_paragraph('Completadas: ____ de 7    Ayudas totales: ____    Suma de tiempos de tareas: ______')
    doc.add_paragraph('No confundir suma de tareas con duración completa de sesión. No registrar contraseñas ni tokens.')

    doc.add_page_break()
    doc.add_heading('3. Feedback y decisión del propietario', 1)
    for question in [
        '¿Ahora encuentras más fácil abrir el detalle y registrar un abono?',
        '¿Qué significa el aviso de historial limitado? ¿El resultado garantiza que pagarán?',
        '¿Qué falta antes de empezar a usarlo en el negocio?',
    ]:
        doc.add_paragraph(question).runs[0].bold = True
        doc.add_paragraph('________________________________________________________________________')
        doc.add_paragraph('________________________________________________________________________')
    doc.add_paragraph('Decisión de Rildo: [ ] Continuar  [ ] Continuar con condiciones  [ ] Mejorar y repetir  [ ] No continuar')
    doc.add_paragraph('Condiciones o motivo: ___________________________________________________')
    doc.add_paragraph('________________________________________________________________________')
    doc.add_paragraph('La decisión no equivale a consentimiento de todos los clientes ni a validación de un modelo predictivo.')

    doc.add_heading('4. Aclaración de la línea base del 5 %', 1)
    doc.add_paragraph('Preguntar: Ese 5 % mensual mencionado en APF1, ¿es sobre todas las ventas, solo lo vendido al fiado, el saldo pendiente o la cantidad de clientes? ¿Es atraso que luego recuperas o dinero que finalmente no recuperas? ¿De qué periodo y qué registro sale?')
    baseline = doc.add_table(rows=1, cols=2)
    baseline.style = 'Table Grid'
    baseline.rows[0].cells[0].text = 'Dato'
    baseline.rows[0].cells[1].text = 'Respuesta de Rildo'
    for label in ['Base/denominador (5 % de qué)', 'Numerador (atraso o pérdida definitiva)', 'Mes o periodo', 'Fuente (cuaderno, cálculo o estimación)', 'Fórmula o explicación con sus palabras']:
        row = baseline.add_row().cells
        row[0].text = label
        row[1].text = '________________________________________'
    doc.add_paragraph('Si no puede precisarlo: [ ] Se conserva como estimación referencial pendiente; no se inventa fórmula.')

    doc.add_heading('5. Evidencia y acciones siguientes', 1)
    action = doc.add_table(rows=1, cols=3)
    action.style = 'Table Grid'
    for cell, label in zip(action.rows[0].cells, ['Hallazgo restante / acción', 'Responsable confirmado', 'Fecha y forma de verificar'], strict=True):
        cell.text = label
    for _ in range(2):
        for cell in action.add_row().cells:
            cell.text = '_____________________\n_____________________'
    doc.add_paragraph('Archivos adjuntos de ESTA sesión, si se autorizaron: __________________________')
    doc.add_paragraph('No citar capturas técnicas anteriores como si se hubieran tomado durante esta sesión.')
    doc.add_paragraph('Firma de Rildo (opcional): ____________________    Fecha: ___________________')
    doc.add_paragraph('Nombre/firma del observador: ____________________________________________')
    doc.add_paragraph('La firma deja constancia de participación; no se añade automáticamente ni acredita pago garantizado.')
    doc.save(output)
    check = Document(output)
    assert len(check.tables) == 3
    assert len(check.tables[0].rows) == 8
    assert any('Omara Baylon' in paragraph.text and 'Pablo Yman' in paragraph.text for paragraph in check.paragraphs)
    print(f'Ficha de revalidación verificada: {output}')


if __name__ == '__main__':
    generate(Path(sys.argv[1]))
