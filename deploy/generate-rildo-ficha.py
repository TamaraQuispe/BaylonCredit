"""Generate a separate, printable owner-validation form for APF2."""

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
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.05
    doc.core_properties.title = "Ficha de validación del MVP con Rildo - APF2 Grupo 2"
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run("APF2 | Grupo 2 | Ficha de prueba con usuario | Página ")
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    footer._p.append(field)

    doc.add_heading("Ficha de validación del MVP", 0)
    doc.add_paragraph("Cervecería Baylón · Credify · APF2 · Grupo 2")
    doc.add_paragraph("Participante: Rildo Baylón Espíritu (propietario)")
    doc.add_paragraph("Fecha: ____ / ____ / ______    Lugar o modalidad: __________________________")
    doc.add_paragraph("Facilitador: ____________________    Observador: __________________________")
    doc.add_paragraph("Inicio: __________    Fin: __________    Dispositivo: ______________________")
    doc.add_paragraph("Demo: https://demo-credify.168-75-71-113.sslip.io")

    doc.add_heading("1. Autorización y explicación inicial", 1)
    doc.add_paragraph(
        "Esta prueba es académica y voluntaria. Se utilizarán clientes y operaciones ficticias, "
        "sin modificar registros del negocio. La evaluación es preliminar por reglas, no un "
        "modelo validado con clientes reales, y no garantiza el pago. Puede detener la sesión cuando desee."
    )
    doc.add_paragraph("Autoriza registrar notas: [ ] Sí  [ ] No    Capturas de pantalla: [ ] Sí  [ ] No")
    doc.add_paragraph("Autoriza grabar audio o video: [ ] Sí  [ ] No  [ ] No se realizará grabación")
    doc.add_paragraph("Si no autoriza notas, detener esta ficha. No grabar sin autorización específica.")

    doc.add_heading("2. Tareas de prueba", 1)
    doc.add_paragraph(
        "El facilitador lee cada tarea sin indicar cada clic. El observador mide tiempo y anota "
        "errores y ayudas. Registrar lo que ocurrió, incluso si una tarea no se completa."
    )
    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    for cell, title in zip(table.rows[0].cells, ["Tarea", "Resultado", "Tiempo y ayudas", "Error / observación"], strict=True):
        cell.text = title
    tasks = [
        "1. Entrar con la cuenta de prueba entregada por el grupo.",
        "2. Identificar y seleccionar un cliente ficticio DEMO.",
        "3. Evaluar S/ 50 y explicar con sus palabras la recomendación.",
        "4. Registrar fiado de S/ 50 con vencimiento al día siguiente.",
        "5. Registrar un abono de S/ 20 en ese crédito.",
        "6. Consultar saldo (esperado: S/ 30) e historial.",
    ]
    for task in tasks:
        cells = table.add_row().cells
        cells[0].text = task
        cells[1].text = "[ ] Logró\n[ ] No logró\n[ ] No probó"
        cells[2].text = "Tiempo: ______\nAyudas: ______"
        cells[3].text = "________________\n________________"
    doc.add_paragraph("Tareas completadas: ____ de 6    Total de ayudas: ____    Tiempo total: __________")
    doc.add_paragraph("No registrar contraseñas, tokens ni datos personales de clientes en esta ficha.")

    doc.add_page_break()
    doc.add_heading("3. Opinión de Rildo", 1)
    doc.add_paragraph("Anotar sus palabras. No completar por anticipado ni atribuirle opiniones del grupo.")
    questions = [
        "¿Qué fue lo más difícil al usar el sistema?",
        "¿Qué entiende de la recomendación y qué dato le falta para decidir si fiar?",
        "¿El plazo de un día coincide con cómo cobra sus fiados?",
        "¿Usaría esta herramienta? ¿En qué momento de su jornada?",
        "¿Qué cambiaría antes de utilizarla diariamente?",
    ]
    for question in questions:
        paragraph = doc.add_paragraph()
        paragraph.add_run(question).bold = True
        doc.add_paragraph("________________________________________________________________________")
        doc.add_paragraph("________________________________________________________________________")

    doc.add_heading("4. Decisión y aprendizaje del grupo", 1)
    doc.add_paragraph("¿Acepta continuar probando el MVP? [ ] Sí  [ ] Con condiciones  [ ] No  [ ] Sin respuesta")
    doc.add_paragraph("Condiciones o motivo: ___________________________________________________")
    doc.add_paragraph("Este acuerdo no autoriza por sí solo el tratamiento de datos de todos los clientes.")
    action = doc.add_table(rows=1, cols=3)
    action.style = "Table Grid"
    for cell, title in zip(action.rows[0].cells, ["Feedback observado / cambio decidido", "Responsable", "Fecha y verificación"], strict=True):
        cell.text = title
    for _ in range(2):
        for cell in action.add_row().cells:
            cell.text = "_____________________\n_____________________"
    doc.add_paragraph("Decisión Lean Startup: [ ] Continuar  [ ] Iterar y volver a probar  [ ] Revisar alcance")
    doc.add_paragraph("Evidencia adjunta (nombre de archivo, si fue autorizada): ______________________")

    doc.add_heading("5. Constancia de participación", 1)
    doc.add_paragraph("Firma de Rildo (opcional): ____________________    Fecha: ___________________")
    doc.add_paragraph("Firma / nombre del observador: __________________________________________")
    doc.add_paragraph("La firma deja constancia de participación; no acredita que el sistema garantiza pagos ni un cumplimiento normativo integral.")
    doc.save(output)
    checked = Document(output)
    assert len(checked.tables) == 2
    assert len(checked.tables[0].rows) == 7
    print(f"Ficha verificada: {output}")


if __name__ == "__main__":
    generate(Path(sys.argv[1]))
