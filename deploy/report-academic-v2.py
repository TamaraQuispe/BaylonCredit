"""Generate the experiment-v2 report for the academic handoff, from frozen evidence."""

import json
import sys
from pathlib import Path

from docx import Document
from docx.shared import Cm, Pt


def generate(directory: Path, output: Path) -> None:
    report = json.loads((directory / "experiment_v2_report.json").read_text())
    frozen = json.loads((directory / "frozen_selection.json").read_text())
    original_errors = json.loads((directory / "first_model_validation_errors.json").read_text())
    assert frozen["model"] == report["chosen"]["model"]
    assert frozen["threshold"] == report["chosen"]["threshold"]
    doc = Document()
    doc.core_properties.title = "APF3 - Segundo experimento sintético y laboratorio de demo"
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    section = doc.sections[0]
    section.top_margin = section.bottom_margin = Cm(2)
    section.left_margin = section.right_margin = Cm(2)
    doc.add_heading("APF3: segundo experimento académico", 0)
    doc.add_paragraph("Grupo 2 · Credify · Datos sintéticos · No es validación de crédito real")

    def table(headers, rows):
        item = doc.add_table(rows=1, cols=len(headers))
        item.style = "Light Shading Accent 1"
        for cell, title in zip(item.rows[0].cells, headers, strict=True):
            cell.text = title
        for values in rows:
            for cell, value in zip(item.add_row().cells, values, strict=True):
                cell.text = str(value)

    doc.add_heading("1. Qué se corrigió y qué no", 1)
    doc.add_paragraph("El primer modelo tenía muchas falsas alertas y no superaba a la referencia mayoritaria en exactitud. Este experimento compara pesos de clase, regularización, árboles y umbral sin modificar el generador ni las etiquetas para favorecer resultados. Se mantiene como experimento limitado y no se activa para decidir fiados.")
    doc.add_paragraph("El grupo comunicó autorización del profesor para datos ficticios coherentes y variados. La procedencia sigue declarada como sintética. La política de revisión manual de producción permanece intacta; el laboratorio no sustituye la evaluación operativa por reglas de la demo.")
    doc.add_heading("2. Análisis del primer modelo en validación", 1)
    table(["Segmento de validación", "TP", "FP", "FN", "TN"], [
        [name, values["TP"], values["FP"], values["FN"], values["TN"]]
        for name, values in original_errors["counts"].items()
    ])
    doc.add_paragraph("TP: atraso identificado; FP: pago puntual marcado como atraso; FN: atraso no detectado; TN: pago puntual identificado. Los escenarios se usan solo para analizar errores, nunca como predictores. Las filas por escenario y por historial son agrupaciones distintas que se solapan y no deben sumarse.")
    doc.add_heading("3. Protocolo y selección", 1)
    table(["Aspecto", "Valor"], [
        ["Entrenamiento original usado", report["training_rows"]],
        ["Validación original usada", report["validation_rows"]],
        ["Modelos candidatos", len(report["protocol"]["models"])],
        ["Umbrales por candidato", len(report["protocol"]["thresholds"])],
        ["Criterio", "Mayor exactitud de validación con recall mínimo 0.30"],
        ["Modelo elegido", report["chosen"]["model"]],
        ["Umbral elegido", report["chosen"]["threshold"]],
        ["Selección congelada UTC", frozen["frozen_utc"]],
        ["Semilla de nueva cohorte final", report["protocol"]["final_cohort_seed"]],
    ])
    doc.add_paragraph("El test anterior ya se había consultado y se excluyó de selección. Se guardaron protocol.json y frozen_selection.json antes de generar la nueva cohorte final. Se usó el mismo simulador coherente, otra semilla e IDs FINAL separados. No se cambiaron resultados después de consultar esa cohorte ni se afinó el umbral sobre test.")
    doc.add_paragraph("El criterio pondera igual falsos positivos y falsos negativos para exactitud, con un piso de recall para evitar seleccionar una solución que nunca alerta. No es una función de costos económicos estimada con Rildo. La búsqueda de 130 combinaciones puede sobreajustar validación; la cohorte final reduce pero no elimina las limitaciones del estudio.")
    c = report["fresh_final_checks"]
    table(["Cohorte sintética final", "Cantidad"], [
        ["Clientes nuevos", c["clients"]], ["Fiados", c["loans"]],
        ["Abonos", c["payments"]], ["Pagos puntuales etiquetados", c["labels"]["0"]],
        ["Atrasos etiquetados", c["labels"]["1"]],
        ["Sin desenlace, excluidos", c["labels"]["None"]],
    ])
    doc.add_heading("4. Comparación en la MISMA cohorte final nueva", 1)
    comparison = report["comparison_on_same_fresh_cohort"]
    table(["Métrica", "Modelo v2", "Modelo v1", "Referencia mayoritaria"], [
        [key, *[f"{comparison[name][key]:.4f}" for name in ("second_model", "first_model_same_fresh_cohort", "majority_baseline")]]
        for key in ("accuracy", "balanced_accuracy", "precision", "recall", "f1", "roc_auc", "brier_score")
    ])
    table(["Modelo", "TN", "FP", "FN", "TP"], [
        [name, values["confusion_matrix"][0][0], values["confusion_matrix"][0][1], values["confusion_matrix"][1][0], values["confusion_matrix"][1][1]]
        for name, values in comparison.items()
    ])
    doc.add_paragraph("Interpretación: v2 reduce falsas alertas de 286 a 178 y eleva la exactitud de 60.7 % a 66.3 % frente a v1. Sin embargo, los atrasos detectados bajan de 215 a 166 (recall de 61.6 % a 47.6 %) y F1 también baja. La referencia que siempre predice pago puntual obtiene 67.4 % de exactitud y no detecta ningún atraso. No afirmar que v2 es superior en todas las métricas ni que debe aprobar créditos reales.")
    doc.add_paragraph("No comparar el 66.3 % directamente con el 61.8 % publicado en ejecución-02 como si fuera la misma muestra. La comparación justa está en esta tabla: ambos modelos evaluados sobre 1070 fiados etiquetados de la cohorte final nueva.")
    doc.add_heading("5. Integración segura en la demo", 1)
    doc.add_paragraph("URL: https://demo-credify.168-75-71-113.sslip.io/laboratorio-academico")
    doc.add_paragraph("Ingresar con la cuenta de prueba habitual. Desde Evaluación crediticia, abrir Laboratorio ML, elegir un caso sintético y pulsar Evaluar caso sintético. Se ejecuta predict_proba del artefacto, se aplica umbral 0.4 y se compara con el desenlace simulado. El resultado no crea crédito ni cambia el score operativo.")
    doc.add_paragraph("Backend limitado a staging con flag explícito. Requiere autenticación, verifica hash del artefacto y acepta solo casos predefinidos. No hay carga de modelos por usuarios, entrenamiento dentro del servidor ni consultas de historial externo. Producción no tiene habilitado este laboratorio.")
    evidence = directory / "evidencias-demo/verificacion-laboratorio.json"
    if evidence.exists():
        verification = json.loads(evidence.read_text())
        doc.add_paragraph("Prueba de demo: " + verification["started"] + " a " + verification["finished"] + ". " + verification["scope"])
        for result in verification["results"]:
            doc.add_paragraph(("PASÓ: " if result["passed"] else "NO PASÓ: ") + result["case"])
        for name in ("laboratorio-desktop.png", "laboratorio-mobile.png"):
            doc.add_paragraph("Captura técnica: " + name)
            picture = doc.add_picture(str(evidence.parent / name), width=Cm(16))
            if picture.height > Cm(22):
                picture.width = int(picture.width * Cm(22) / picture.height)
                picture.height = Cm(22)
    doc.add_heading("6. Archivos y limitaciones", 1)
    for name in ("protocol.json", "first_model_validation_errors.json", "validation_search.json", "frozen_selection.json", "experiment_v2_report.json", "fresh_synthetic_transactions.json", "fresh_synthetic_predictions.csv", "final_errors_not_for_tuning.json", "academic_model_v2.joblib", "academic_lab_cases.json"):
        doc.add_paragraph(name, style="List Bullet")
    doc.add_paragraph("Las fechas de transacciones son ficticias. Los perfiles, escenarios, IDs y saldos posteriores no entran como predictores. El dataset conserva trazabilidad, no operaciones reales. La nueva cohorte procede del mismo simulador, no de un generador externo ni de clientes reales. No prueba calibración ni reducción de pérdidas. Después de inspeccionar este final, cualquier nueva selección requiere otra evaluación final independiente y debe documentarse, no perseguir una cifra de precisión.")
    doc.add_paragraph("85 pruebas anteriores y 96 actuales corresponden a versiones distintas de la suite; las cinco comprobaciones de la demo y las pruebas frontend con fixtures no se suman a la suite como aceptación humana. El grupo debe revisar supuestos, errores y referencias y registrar su validación humana.")
    doc.add_heading("7. Texto e instrucciones para Claude", 1)
    doc.add_paragraph("Se realizó un segundo experimento con datos sintéticos, selección de modelos y umbral exclusivamente por entrenamiento/validación y una cohorte final nueva después de congelar la elección. Se redujeron falsas alertas y mejoró exactitud respecto al primer modelo en la misma cohorte, a costa de menor recall/F1. No superó a la referencia mayoritaria en exactitud. Por esas limitaciones se integró solo un laboratorio académico de consulta en la demo; no se activó en producción ni se utiliza para autorizar créditos.")
    doc.add_paragraph("Claude: usar estas cifras de archivos, conservar resultados desfavorables y distinguir demostración funcional, validez sintética y desempeño real no demostrado. No reescribir APF2 como si este experimento existiera durante su entrega. No fabricar autorización del docente ni aceptación de Rildo sobre este modelo. Añadir protocolo, partición, métricas, matriz y limitaciones en APF3, junto con los anexos de asistencia IA y revisión humana real.")
    doc.save(output)
    verified = Document(output)
    assert len(verified.tables) == 5
    assert len(verified.inline_shapes) == 2
    print(f"Word experimento v2 verificado: {output}")


if __name__ == "__main__":
    generate(Path(sys.argv[1]), Path(sys.argv[2]))
