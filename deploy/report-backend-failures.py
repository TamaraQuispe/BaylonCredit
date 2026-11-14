"""Build the APF3 handoff from successful local fault-test evidence."""

import hashlib
import json
import sys
from pathlib import Path

from docx import Document
from docx.shared import Cm, Pt


def generate(directory: Path) -> None:
    report = json.loads((directory / "fallos-backend-reales.json").read_text())
    checks = json.loads((directory / "verificaciones.json").read_text())
    results = report["results"]
    assert len(results) == 6 and all(item["passed"] for item in results), (
        "Six successful fault/recovery checks required"
    )
    failures = [item for item in results if "actual_http" in item]
    recoveries = [item for item in results if "rows_before_retry" in item]
    assert len(failures) == len(recoveries) == 3
    assert all(item["rows_before_retry"] == 0 and item["rows_after_retry"] == 1
               for item in recoveries)
    doc = Document()
    doc.core_properties.title = "APF3 - Pruebas reales aisladas de fallos del backend"
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    section = doc.sections[0]
    section.top_margin = section.bottom_margin = Cm(2)
    section.left_margin = section.right_margin = Cm(2)

    def table(headers, rows):
        item = doc.add_table(rows=1, cols=len(headers))
        item.style = "Light Shading Accent 1"
        for cell, title in zip(item.rows[0].cells, headers, strict=True):
            cell.text = title
        for values in rows:
            for cell, value in zip(item.add_row().cells, values, strict=True):
                cell.text = str(value)

    doc.add_heading("APF3: fallos del backend y recuperacion", 0)
    doc.add_paragraph("Grupo 2 - Credify - Entorno local aislado - Datos ficticios")
    doc.add_heading("1. Alcance y resultado", 1)
    doc.add_paragraph(report["scope"])
    doc.add_paragraph(f"Inicio UTC: {report['started']}. Fin UTC: {report['finished']}.")
    doc.add_paragraph(
        "Se aprobaron tres escenarios de fallo y tres recuperaciones. Se uso navegador "
        "real contra Nginx, FastAPI y PostgreSQL 17, sin interceptar la red del navegador. "
        "No se apagaron ni desplegaron servicios de produccion o demo publica."
    )
    table(["Fallo real", "HTTP", "Tiempo observado (ms)"], [
        [item["name"], item["actual_http"], item["elapsed_ms"]] for item in failures
    ])
    doc.add_paragraph(
        "Se conservaron nombres, apellidos, documento, telefono, negocio, consentimiento "
        "y token. Un solo POST observado por intento fallido; sin reenvio automatico. "
        "El mensaje visible fue: Sistema no disponible temporalmente. "
        "Int\u00e9ntalo m\u00e1s tarde."
    )
    table(["Recuperacion explicita", "Filas antes", "Filas despues"], [
        [item["name"], item["rows_before_retry"], item["rows_after_retry"]]
        for item in recoveries
    ])
    doc.add_paragraph(
        "En las dos fallas de BD, live devolvio 200 y ready 503. Los errores de la API "
        "incluyeron JSON seguro, Retry-After: 5 y X-Request-ID. El error del proxy no "
        "tiene ese request ID de FastAPI porque la API estaba detenida."
    )
    doc.add_heading("2. Hallazgos y correcciones", 1)
    doc.add_paragraph(
        "La primera prueba con PostgreSQL pausado supero 25 segundos: el timeout del "
        "comando no bastaba. asyncpg esperaba la cancelacion del servidor durante el "
        "cierre ordenado de SQLAlchemy. Se termina directamente la conexion al detectar "
        "timeout/cancelacion antes de invalidarla. Quitar solo pool_pre_ping y luego "
        "invalidar la sesion no habia resuelto el bloqueo."
    )
    doc.add_paragraph(
        "Tambien se detecto espera prolongada al apagar API por el timeout de conexion "
        "predeterminado del proxy. Nginx ahora usa 3 segundos para conectar y no cambia "
        "de upstream. En esta ejecucion devolvio 504; un rechazo inmediato puede ser "
        "502. Ambos, junto con 503, reciben el mismo mensaje en el frontend."
    )
    doc.add_paragraph(
        "Versiones observadas: SQLAlchemy 2.0.54, asyncpg 0.31.0, Python 3.12.14. "
        "Conexion/comando/pool usan 2 segundos cada uno en la prueba. En configuracion "
        "general los valores por defecto son 5/10/5 segundos, no un plazo absoluto "
        "para toda peticion. Los cambios no estan desplegados en servicios publicos."
    )
    doc.add_heading("3. Verificacion automatizada", 1)
    table(["Verificacion", "Resultado observado"], [
        [item["name"], item["result"]] for item in checks["checks"]
    ])
    doc.add_paragraph(checks["notes"])
    doc.add_heading("4. Metodo y limites", 1)
    doc.add_paragraph(
        "El harness verifica la etiqueta Compose credify-resilience antes de actuar; "
        "usa stop/pause reales de Docker y reactiva servicios en finally. El puerto "
        "solo escucha en 127.0.0.1:8093. El envio se realiza mediante requestSubmit "
        "sobre el formulario y su handler React real; no acredita el clic fisico del "
        "boton. Los tiempos son observaciones de esta ejecucion, no SLA ni benchmark."
    )
    doc.add_paragraph(report["limits"])
    doc.add_paragraph(
        "El rollback tras flush se verifica en una prueba SQLite; la prueba real "
        "PostgreSQL comprueba conteos del cliente. No se probo perder la respuesta "
        "despues de confirmar COMMIT, failover, concurrencia ni particiones parciales. "
        "Consultar el historial antes de reenviar una operacion de resultado incierto. "
        "No se agregaron claves de idempotencia ni se afirma exactamente una vez."
    )
    doc.add_heading("5. Instrucciones para el documento academico", 1)
    doc.add_paragraph(
        "Usar el JSON y capturas de esta ejecucion como evidencia tecnica local de "
        "APF3. Distinguir las 6 comprobaciones reales de las 126 pruebas de la suite "
        "(que ya incluyen 30 de fallos). No sumarlas como aceptacion humana ni "
        "atribuirlas a produccion, al propietario o a la entrega historica APF2. "
        "Mantener los hallazgos iniciales y limites. El grupo debe revisar la evidencia "
        "y registrar su validacion humana y asistencia IA sin fabricar firmas."
    )
    evidence = ["fallos-backend-reales.json", "verificaciones.json"]
    for item, recovery in zip(failures, (
        "postgresql-detenido", "postgresql-timeout", "api-detenida"
    ), strict=True):
        doc.add_page_break()
        doc.add_heading(item["name"], 1)
        doc.add_paragraph(
            f"HTTP {item['actual_http']}; {item['elapsed_ms']} ms; formulario conservado. "
            f"Request ID: {item['request_id'] or 'No disponible: error de proxy'}."
        )
        for filename, caption in (
            (item["name"] + ".png", "Error controlado"),
            (recovery + "-recuperado.png", "Recuperacion con reenvio explicito"),
        ):
            doc.add_paragraph(caption)
            doc.add_picture(str(directory / filename), width=Cm(14))
            evidence.append(filename)
    manifest = {
        name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
        for name in evidence
    }
    (directory / "evidencias-sha256.json").write_text(json.dumps(manifest, indent=2) + "\n")
    output = directory / "APF3_Grupo2_Pruebas_Fallos_Backend.docx"
    doc.save(output)
    verified = Document(output)
    assert len(verified.tables) == 3 and len(verified.inline_shapes) == 6
    print(f"Word verificado: {output}; 3 tablas, 6 capturas; hashes en evidencias-sha256.json")


if __name__ == "__main__":
    generate(Path(sys.argv[1]))
