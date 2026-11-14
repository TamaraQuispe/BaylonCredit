"""Create an explanatory Word and scenario examples from the academic run."""

import csv
import hashlib
import json
import sys
from pathlib import Path

from docx import Document
from docx.shared import Cm, Pt


def report(directory: Path, output: Path) -> None:
    result = json.loads((directory / "academic_synthetic_report.json").read_text())
    dataset = json.loads((directory / "synthetic_transactions.json").read_text())
    for name, checksum in result["sha256"].items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == checksum
    seen = set()
    examples = []
    for row in dataset["rows"]:
        if row["scenario"] not in seen:
            seen.add(row["scenario"])
            examples.append(row)
    with (directory / "synthetic_scenario_examples.csv").open("w", newline="", encoding="utf-8") as file:
        fields = ["data_source", "client_id", "loan_id", "scenario", "evaluated_at", "due_date", "requested_amount", "pending_at_cutoff", "late_payment"]
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(examples)

    doc = Document()
    doc.core_properties.title = "APF3 - Piloto académico sintético - Grupo 2"
    section = doc.sections[0]
    section.top_margin = section.bottom_margin = Cm(2)
    section.left_margin = section.right_margin = Cm(2)
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = "Calibri", Pt(11)
    doc.add_heading("Piloto académico con datos sintéticos", 0)
    doc.add_paragraph("Credify · Cervecería Baylón · Grupo 2 · APF3")
    doc.add_paragraph("DATOS FICTICIOS. No son operaciones ni resultados predictivos verificados del negocio. No se cargaron en producción ni se activó este modelo en la aplicación.")

    def table(headers, rows):
        t = doc.add_table(rows=1, cols=len(headers))
        t.style = "Light Shading Accent 1"
        for cell, value in zip(t.rows[0].cells, headers, strict=True):
            cell.text = str(value)
        for row in rows:
            for cell, value in zip(t.add_row().cells, row, strict=True):
                cell.text = str(value)

    doc.add_heading("1. Alcance y autorización", level=1)
    doc.add_paragraph("El usuario comunicó que el docente autorizó datos ficticios para el trabajo, siempre que fueran variados y coherentes. No se adjuntó una comunicación independiente del docente. Conservar ese respaldo si el grupo dispone de él. El feedback anterior pedía datos reales: presentar el cambio de alcance explícitamente, sin alterar la entrega histórica de APF2.")
    doc.add_paragraph("Esta simulación permite probar generación, entrenamiento y evaluación académica. No acredita adopción diaria, consentimiento de clientes reales, reducción de pérdidas ni fiabilidad predictiva en producción. Ninguna persona real aparece en el dataset.")
    doc.add_heading("2. Qué se generó", level=1)
    c = result["consistency"]
    table(["Elemento", "Cantidad"], [
        ["Clientes ficticios", c["clients"]], ["Fiados ficticios", c["loans"]],
        ["Eventos de abono ficticios", c["payments"]],
        ["Pagados a tiempo (0)", c["labels"]["0"]],
        ["Atrasados (1)", c["labels"]["1"]],
        ["Sin desenlace, excluidos de entrenamiento", c["labels"]["None"]],
    ])
    table(["Caso simulado", "Fiados"], sorted(c["scenarios"].items()))
    doc.add_paragraph("Se simularon clientes puntuales, mixtos, con atrasos frecuentes, que abonan en partes, con dificultad temporal y nuevos. Los perfiles no son calificaciones de personas reales ni variables predictoras.")
    doc.add_heading("3. Supuestos y coherencia", level=1)
    for text in [
        "Plazo contractual de un día. Montos entre S/ 10 y S/ 200; primera exposición sin pagos previos hasta S/ 50 como supuesto académico, no cambio de política productiva.",
        "Saldo pendiente previo más nuevo fiado no supera el máximo simulado de S/ 200 por cliente. Se identifican autorizaciones simuladas del propietario cuando no hay pagos previos o hay atrasos; no son autorizaciones reales.",
        "Los abonos tienen fechas posteriores al otorgamiento, no superan la deuda y se conservan solo hasta el corte de observación.",
        "Las once variables se recomputan con eventos anteriores a cada evaluación. El crédito actual y pagos futuros no entran en su snapshot.",
        "La etiqueta se deriva del pago completo y el vencimiento, no del score ni de copiar la aprobación del sistema.",
        "El periodo septiembre-octubre de 2026 y el corte del 31/10/2026 son fechas de escenario ficticio, no fechas de operación real ni evidencia histórica del negocio.",
        "Las tasas de atraso son supuestos de variedad de escenarios. No se deducen del 5 % de pérdida sobre ventas declarado por Rildo; atraso y pérdida financiera no son equivalentes.",
    ]:
        doc.add_paragraph(text, style="List Bullet")
    doc.add_paragraph("Se conservaron dos ejecuciones. Ejecución-01 quedó como versión inicial. Usar ejecución-02 para este reporte: se corrigió la falta de casos con crédito previo todavía vigente y se limitó la primera exposición. La revisión se hizo por variedad/coherencia, no para aumentar las métricas; los resultados de prueba fueron menores y se conservaron.")
    doc.add_heading("4. Contrato y partición", level=1)
    doc.add_paragraph("late_payment=0 si pagó completamente hasta el vencimiento inclusive; 1 si pagó después o aún debe al observar desde el día siguiente. Casos no resueltos no se usan para entrenar.")
    doc.add_paragraph("Predictores: " + ", ".join(result["features"]) + ".")
    doc.add_paragraph("El CSV académico incluye además metadatos para auditoría. IDs, partición, perfil, escenario, fecha de observación, saldo futuro y etiqueta NO se usan como predictores. Es distinto del CSV mínimo de doce columnas para exportación real.")
    table(["Partición", "Clientes", "Etiqueta 0", "Etiqueta 1", "Filas etiquetadas"], [
        [name, result["clients_per_split"][name], counts["0"], counts["1"], sum(counts.values())]
        for name, counts in result["class_counts"].items()
    ])
    doc.add_paragraph("60/20/20 por cliente, no necesariamente por número de filas. Ningún cliente cruza particiones. El escalado y ajuste se hacen solo con train. Se selecciona por F1 de validation y se usa test para evaluación final, sin elegir por sus métricas ni cambiar el umbral de 0.5.")
    doc.add_heading("5. Resultados de esta ejecución sintética", level=1)
    table(["Modelo", "F1 validación", "ROC-AUC validación"], [
        [name, f"{values['f1']:.3f}", f"{values['roc_auc']:.3f}"] for name, values in result["validation_metrics"].items()
    ])
    doc.add_paragraph("Modelo seleccionado: " + result["selected_model"] + ". Se compararon regresión logística con escalado y Random Forest, ambos con pesos de clase equilibrados. No se modificó el modelo que sirve producción.")
    metrics, baseline = result["held_out_synthetic_test_metrics"], result["baseline_synthetic_test_metrics"]
    table(["Métrica de test sintético", "Modelo", "Referencia mayoritaria"], [
        [name, f"{metrics[name]:.4f}", f"{baseline[name]:.4f}"]
        for name in ["accuracy", "precision", "recall", "f1", "roc_auc", "brier_score"]
    ])
    matrix = metrics["confusion_matrix_labels_0_1"]
    table(["Real / predicción", "Predice puntual", "Predice atraso"], [
        ["Puntual (0)", *matrix[0]], ["Atraso (1)", *matrix[1]],
    ])
    doc.add_paragraph("Interpretación: de " + str(sum(matrix[1])) + " atrasos sintéticos de test, identificó " + str(matrix[1][1]) + ". De " + str(matrix[0][1] + matrix[1][1]) + " alertas, " + str(matrix[1][1]) + " correspondieron a atrasos. Exactitud y precisión no son lo mismo.")
    doc.add_paragraph("Limitación importante: la exactitud del modelo es inferior a la referencia que predice siempre pago puntual. Aunque detecta atrasos que la referencia no detecta, no se puede concluir superioridad general ni aptitud para aprobar créditos. Las probabilidades no están calibradas con comportamiento real; el Brier tampoco supera la referencia en esta ejecución.")
    doc.add_heading("6. Archivos y reproducibilidad", level=1)
    doc.add_paragraph("Semilla: " + str(result["seed"]) + ". Fecha de generación UTC: " + result["generated_utc"] + ".")
    for name in ["synthetic_credit_dataset.csv", "synthetic_transactions.json", "synthetic_scenario_examples.csv", "synthetic_test_predictions.csv", "academic_synthetic_report.json", "academic_synthetic_late_payment.joblib"]:
        doc.add_paragraph(name, style="List Bullet")
    doc.add_paragraph("Código: backend/app/ml/synthetic.py y backend/scripts/academic_credit_pilot.py. Ejecución desde backend: python scripts/academic_credit_pilot.py --output-dir RUTA_NUEVA --clients 180 --seed 20261028, con PYTHONPATH del backend y sus dependencias. No sobrescribe una carpeta con evidencias previas. El artefacto tiene nombre académico y no se instala en app/ml/artifacts.")
    doc.add_heading("7. Texto para el informe", level=1)
    doc.add_paragraph("Según autorización comunicada por el grupo, se preparó un piloto académico con datos sintéticos y trazabilidad de transacciones. Se simularon compras, fiados a un día y distintos desenlaces de pago. Las etiquetas y variables históricas se derivaron de los eventos, y se separaron clientes entre entrenamiento, validación y prueba. Los resultados evalúan el pipeline bajo supuestos simulados; no demuestran desempeño en clientes reales ni reducción de pérdidas. El modelo no fue activado en producción y sus limitaciones frente a la referencia mayoritaria se reportan explícitamente.")
    doc.add_paragraph("Pendiente: validación humana del grupo sobre supuestos y ejemplos, respaldo de autorización docente si está disponible y plan de próximos experimentos. No fabricar aprobación de Rildo o del profesor.")
    doc.save(output)
    verified = Document(output)
    assert len(verified.tables) >= 6
    print(f"Resumen Word verificado: {output}")


if __name__ == "__main__":
    report(Path(sys.argv[1]), Path(sys.argv[2]))
