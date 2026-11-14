"""Convert the APF2 evidence handoff to a Word document (python-docx)."""

import re
import os
import json
import sys
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.table import Table
from docx.text.paragraph import Paragraph


def generate(source: Path, output: Path, extra_source: Path | None = None) -> None:
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin = section.bottom_margin = Cm(2.54)
    section.left_margin = section.right_margin = Cm(2.54)
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    style.paragraph_format.line_spacing = 1.15
    style.paragraph_format.space_after = Pt(6)
    doc.core_properties.title = source.stem.replace("_", " ") + " - Grupo 2"
    doc.core_properties.subject = "Guia de trabajo: no es el informe final"
    footer = section.footer.paragraphs[0]
    footer.add_run("Credify | Guia APF2 | ")
    page = OxmlElement("w:fldSimple")
    page.set(qn("w:instr"), "PAGE")
    footer._p.append(page)
    table = None
    text = source.read_text(encoding="utf-8")
    if extra_source:
        text += "\n\n" + extra_source.read_text(encoding="utf-8")
    if os.environ.get("APF2_CLOSURE_SOURCE"):
        text += "\n\n" + Path(os.environ["APF2_CLOSURE_SOURCE"]).read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if all(re.fullmatch(r":?-+:?", cell) for cell in cells):
                continue
            if table is None:
                table = doc.add_table(rows=0, cols=len(cells))
                table.style = "Light Shading Accent 1"
            row = table.add_row()
            for cell, text in zip(row.cells, cells, strict=True):
                cell.text = text
            if len(table.rows) == 1:
                repeat = OxmlElement("w:tblHeader")
                row._tr.get_or_add_trPr().append(repeat)
            continue
        table = None
        if not line.strip():
            continue
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            doc.add_heading(line.lstrip("# "), level=min(level, 3))
        elif line.startswith("- "):
            doc.add_paragraph(line[2:], style="List Bullet")
        else:
            doc.add_paragraph(line)
    if os.environ.get("APF2_AI_LOG"):
        log = json.loads(Path(os.environ["APF2_AI_LOG"]).read_text())
        doc.add_heading("Anexo C: solicitudes recuperadas del historial", level=1)
        doc.add_paragraph(log["source"] + ". Fechas originales de los mensajes, no fechas de pruebas. Revisión humana del grupo por documentar.")
        table = doc.add_table(rows=1, cols=3)
        table.style = "Table Grid"
        for cell, label in zip(table.rows[0].cells, ["Fecha y referencia", "Prompt exacto", "Herramienta y modelo"], strict=True):
            cell.text = label
        for entry in log["records"]:
            cells = table.add_row().cells
            cells[0].text = "UTC: " + entry["date_utc"] + "\nLima: " + entry["date_lima"] + "\n" + entry["message_id"]
            cells[1].text = entry["prompt"]
            cells[2].text = entry["tool"] + "\n" + ", ".join(item["provider"] + "/" + item["model"] for item in entry["models"])
    if os.environ.get("APF2_KANBAN"):
        board = json.loads(Path(os.environ["APF2_KANBAN"]).read_text())
        doc.add_heading("Kanban: registro operativo del cierre", level=1)
        doc.add_paragraph(board["scope"])
        table = doc.add_table(rows=1, cols=3)
        table.style = "Table Grid"
        for cell, label in zip(table.rows[0].cells, ["Tarjeta", "Estado", "Evidencia"], strict=True):
            cell.text = label
        for entry in board["cards"]:
            cells = table.add_row().cells
            cells[0].text = entry["id"] + ": " + entry["title"]
            cells[1].text = entry["state"]
            cells[2].text = entry["evidence"]
        for event in board["events"]:
            doc.add_paragraph(event["date_utc"] + " - " + event["card"] + ": " + event["from"] + " -> " + event["to"] + ". " + event["evidence"])
        if os.environ.get("APF2_KANBAN_IMAGE"):
            doc.add_picture(os.environ["APF2_KANBAN_IMAGE"], width=Cm(16))
    if os.environ.get("APF2_OWNER_FORM"):
        form = Document(os.environ["APF2_OWNER_FORM"])
        doc.add_heading("Anexo: contenido de la ficha completada entregada por el grupo", level=1)
        doc.add_paragraph("Transcripción del Word recibido; se conserva separado el original. No acredita por sí sola las capturas citadas ni una firma inexistente.")
        for block in form.iter_inner_content():
            if isinstance(block, Paragraph):
                doc.add_paragraph(block.text)
            elif isinstance(block, Table):
                table_copy = doc.add_table(rows=0, cols=len(block.columns))
                table_copy.style = "Table Grid"
                for source_row in block.rows:
                    for target, source_cell in zip(table_copy.add_row().cells, source_row.cells, strict=True):
                        target.text = source_cell.text
    if os.environ.get("APF2_EVIDENCE_DIR"):
        directory = Path(os.environ["APF2_EVIDENCE_DIR"])
        report = json.loads((directory / "reporte-pruebas.json").read_text())
        doc.add_heading("Anexo de evidencias técnicas obtenidas", level=1)
        doc.add_paragraph("Fecha UTC: " + report["finished"] + ". Prueba automatizada del equipo, no aceptación del propietario.")
        for result in report["results"]:
            doc.add_paragraph(("PASÓ: " if result["passed"] else "NO PASÓ: ") + result["name"])
        for warning in report["warnings"]:
            doc.add_paragraph("Observación: " + warning)
        for name in report["screenshots"]:
            if (directory / name).exists():
                doc.add_paragraph("Captura real de la demo: " + name)
                picture = doc.add_picture(str(directory / name), width=Cm(16))
                if picture.height > Cm(22):
                    picture.width = int(picture.width * Cm(22) / picture.height)
                    picture.height = Cm(22)
    if os.environ.get("APF2_TASK_CAPTURE_DIR"):
        directory = Path(os.environ["APF2_TASK_CAPTURE_DIR"])
        provenance = json.loads((directory / "procedencia.json").read_text())
        doc.add_heading("Capturas técnicas posteriores por tarea (T1-T6)", level=1)
        doc.add_paragraph("Origen: " + provenance["source"] + ". Fecha UTC: " + provenance["finished"] + ". Tomadas por OpenCode, no durante la sesión de Rildo.")
        for name in provenance["mapping"]:
            doc.add_paragraph(name)
            picture = doc.add_picture(str(directory / name), width=Cm(16))
            if picture.height > Cm(22):
                picture.width = int(picture.width * Cm(22) / picture.height)
                picture.height = Cm(22)
    if os.environ.get("APF2_ORACLE_EVIDENCE_DIR"):
        directory = Path(os.environ["APF2_ORACLE_EVIDENCE_DIR"])
        doc.add_heading("Anexo: reporte Oracle Cost Analysis recibido", level=1)
        doc.add_paragraph("Fuente: Cost details by date2026-10-07T22_46_51Z.pdf. Periodo UTC: 1 al 7 de octubre de 2026. Moneda PEN; total mostrado 0.00. No es factura ni prueba de gratuidad permanente; no muestra filtros/identificación de recursos y el gráfico indica No data to display. La tabla contiene filas por día y servicio con importe 0.00.")
        for image in sorted(directory.glob("oracle-costos-pagina-*.png")):
            doc.add_paragraph(image.name + ": reproducción del reporte suministrado, sin editar sus importes.")
            picture = doc.add_picture(str(image), width=Cm(16))
            if picture.height > Cm(22):
                picture.width = int(picture.width * Cm(22) / picture.height)
                picture.height = Cm(22)
    if os.environ.get("APF2_REVIEW_EVIDENCE_DIR"):
        directory = Path(os.environ["APF2_REVIEW_EVIDENCE_DIR"])
        doc.add_heading("Evidencias disponibles para completar el informe", level=1)
        doc.add_paragraph("Capturas técnicas de la demo: no son de la sesión de Rildo. Incorporar en Anexo B según el caso probado.")
        for name in ["08-formulario-vacio-validacion.png", "09-error-red-simulado.png", "07-evaluacion-mobile.png"]:
            doc.add_paragraph(name)
            picture = doc.add_picture(str(directory / name), width=Cm(16))
            if picture.height > Cm(22):
                picture.width = int(picture.width * Cm(22) / picture.height)
                picture.height = Cm(22)
        report = json.loads((directory / "reporte-pruebas.json").read_text())
        doc.add_paragraph("Navegador: " + report["started"] + " a " + report["finished"] + ". " + str(len(report["results"])) + " comprobaciones; ejecución distinta de la suite backend.")
        doc.add_heading("Respaldo de ejecución backend", level=2)
        doc.add_paragraph("Transcripción del log backend-pruebas.log. Contenedor de pruebas, no aceptación del propietario ni garantía de paridad con producción.")
        for line in (directory / "backend-pruebas.log").read_text().splitlines():
            paragraph = doc.add_paragraph()
            run = paragraph.add_run(line)
            run.font.name = "Consolas"
            run.font.size = Pt(8)
    if os.environ.get("APF2_IMPROVEMENTS_DIR"):
        directory = Path(os.environ["APF2_IMPROVEMENTS_DIR"])
        report = json.loads((directory / "reporte-mejoras.json").read_text())
        doc.add_heading("Anexo: prueba posterior de mejoras", level=1)
        doc.add_paragraph("Inicio UTC: " + report["started"] + "; fin UTC: " + report["finished"] + ". " + report["type"])
        for result in report["results"]:
            doc.add_paragraph(("PASÓ: " if result["passed"] else "NO PASÓ: ") + result["card"] + ". " + result["detail"])
        for image in sorted(directory.glob("*.png")):
            doc.add_paragraph("Captura técnica posterior: " + image.name)
            picture = doc.add_picture(str(image), width=Cm(16))
            if picture.height > Cm(22):
                picture.width = int(picture.width * Cm(22) / picture.height)
                picture.height = Cm(22)
    if os.environ.get("APF2_FINAL_PROOF_DIR"):
        directory = Path(os.environ["APF2_FINAL_PROOF_DIR"])
        board = json.loads((directory / "kanban-r01-r07.json").read_text())
        doc.add_heading("Evidencia 1: captura actual del Kanban R01-R07", level=1)
        doc.add_paragraph("Fecha UTC de captura: " + board["captured_utc"] + ". Vista filtrada de siete tarjetas, no todo el tablero.")
        doc.add_picture(str(directory / "kanban-r01-r07.png"), width=Cm(16))
        report_path = directory.parent / "Mejoras_R/reporte-mejoras.json"
        report = json.loads(report_path.read_text())
        doc.add_heading("Evidencia 2: B.5 - reporte-mejoras.json", level=1)
        table = doc.add_table(rows=1, cols=3)
        table.style = "Table Grid"
        for cell, title in zip(table.rows[0].cells, ["Caso", "Resultado", "Detalle"], strict=True):
            cell.text = title
        for result in report["results"]:
            cells = table.add_row().cells
            cells[0].text = result["card"]
            cells[1].text = "Pasó" if result["passed"] else "No pasó"
            cells[2].text = result["detail"]
        doc.add_paragraph("Contenido literal del archivo original, sin reescribir fechas o resultados:")
        for line in report_path.read_text().splitlines():
            run = doc.add_paragraph().add_run(line)
            run.font.name, run.font.size = "Consolas", Pt(8)
        login_path = directory / "login-credenciales-invalidas.json"
        login = json.loads(login_path.read_text())
        doc.add_heading("Evidencia 3: contraseña incorrecta", level=1)
        doc.add_paragraph("Inicio UTC: " + login["started"] + "; fin UTC: " + login["finished"] + ". " + login["type"])
        picture = doc.add_picture(str(directory / "login-credenciales-invalidas.png"), width=Cm(16))
        if picture.height > Cm(22):
            picture.width = int(picture.width * Cm(22) / picture.height)
            picture.height = Cm(22)
        for line in login_path.read_text().splitlines():
            run = doc.add_paragraph().add_run(line)
            run.font.name, run.font.size = "Consolas", Pt(8)
    if os.environ.get("DEMO_PUBLIC_PASSWORD"):
        doc.add_heading("Acceso a la demostración pública para el docente", level=1)
        doc.add_paragraph("URL: https://demo-credify.168-75-71-113.sslip.io/evaluacion-crediticia")
        doc.add_paragraph("Usuario: docente@example.com")
        doc.add_paragraph("Contraseña: " + os.environ["DEMO_PUBLIC_PASSWORD"])
        doc.add_paragraph("Cuenta de operador exclusiva de la demo, sin datos reales. Compartir solo para la evaluación académica; no es la cuenta de producción.")
    doc.save(output)
    checked = Document(output)
    assert len(checked.tables) >= 1
    assert len(checked.paragraphs) >= 20
    print(f"Word verificado: {output}; {len(checked.paragraphs)} parrafos, {len(checked.tables)} tablas")


if __name__ == "__main__":
    generate(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]) if len(sys.argv) > 3 else None)
