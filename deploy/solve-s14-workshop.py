"""Prepare and execute a self-contained Colab workshop, preserving the input notebook."""

import argparse
import ast
import csv
import hashlib
import io
import json
from datetime import UTC, datetime
from pathlib import Path

import nbformat
from nbclient import NotebookClient


def build(source: Path, output: Path) -> None:
    original_bytes = source.read_bytes()
    notebook = nbformat.reads(original_bytes.decode(), as_version=4)
    cells = {cell.id: cell for cell in notebook.cells}
    data_cell = cells["73fbe212"]
    assignment = ast.parse(data_cell.source).body[0]
    assert isinstance(assignment, ast.Assign) and assignment.targets[0].id == "datos"
    data = ast.literal_eval(assignment.value)
    rows = list(csv.DictReader(io.StringIO(data)))
    assert len(rows) == 160 and len(rows[0]) == 10
    assert [row["cliente"] for row in rows] == [f"C{i:03}" for i in range(1, 161)]
    assert sum(int(row["moroso"]) for row in rows) == 48
    assert all(int(row["pagos_puntuales"]) <= int(row["fiados_previos"]) for row in rows)

    cells["8b49c988"].source = """# Caso: Bodega Doña Rosa
## Taller práctico · Semana 14, sesión B · Grupo 2
**Curso:** Innovación y Transformación Digital · UTP · Sección 35036

**Grupo del proyecto:**

| Integrante | Código estudiantil |
|---|---|
| Coveñas Quispe, Tamara Alison | U23204737 |
| Baylón Vila, Omara Yamileth | U23231338 |
| Paredes Paredes, César Augusto Daniel | U23259768 |
| Yman Avila, Pablo Enrique | U23251279 |

**El taller pide parejas:** confirmar qué dos integrantes presentan este enlace, o la
autorización del docente si participa el grupo completo. Códigos proporcionados por la usuaria.
La fecha/hora técnica real de ejecución se muestra en el Paso 0; no acredita una sesión humana.

**Objetivo:** ejecutar SVM, KNN, árbol y AdaBoost sobre la misma base y priorizar hasta
diez llamadas. El CSV exacto de 160 clientes está incrustado: no requiere Drive,
archivos externos, credenciales ni datos del proyecto.

**Etiqueta del taller:** `moroso=1` significa más de siete días de retraso, no pérdida
definitiva. Los 40 clientes de prueba representan la semana ficticia del ejercicio;
no son una cartera nueva ni clientes de Cervecería Baylón.

**Límite metodológico:** el taller consulta repetidamente prueba para comparar k,
rondas y umbrales. Se conserva ese procedimiento para resolver la consigna, pero sus
resultados son exploratorios, no una evaluación final independiente tras seleccionar.
En APF3 ajustaremos dentro de entrenamiento y reservaremos un test final sin consultar.

**Uso de IA:** preparación asistida por OpenCode; ejecución técnica comprobada.
Cada participante debe revisar, explicar y validar las respuestas antes de entregarlas.
No se afirma que esa revisión humana ya haya ocurrido.
"""

    install = nbformat.v4.new_code_cell(
        """# Dependencias fijadas para reproducir las tablas y respuestas de esta entrega.
# Ejecutar en un entorno nuevo de Colab (Python 3.11–3.13; verificado en 3.12).
import sys
import subprocess
from importlib.metadata import version, PackageNotFoundError

requisitos = {
    "scikit-learn": "1.8.0", "pandas": "2.2.3",
    "numpy": "2.3.5", "matplotlib": "3.10.8",
}
assert (3, 11) <= sys.version_info[:2] < (3, 14), "Usar Python 3.11–3.13, preferiblemente 3.12."
instalar = []
for paquete, requerido in requisitos.items():
    try:
        actual = version(paquete)
    except PackageNotFoundError:
        actual = None
    if actual != requerido:
        instalar.append(f"{paquete}=={requerido}")
if instalar:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", *instalar])
print("Dependencias listas:", requisitos)
"""
    )
    notebook.cells.insert(2, install)
    cells["38b073ec"].source += """
from datetime import datetime, timezone
print("Ejecución técnica UTC:", datetime.now(timezone.utc).isoformat())
for paquete, requerido in requisitos.items():
    assert version(paquete) == requerido
assert sklearn.__version__ == requisitos["scikit-learn"]
assert np.__version__ == requisitos["numpy"] and pd.__version__ == requisitos["pandas"]
"""
    cells["e817affd"].source = """### Registra
Se fijan scikit-learn 1.8.0, pandas 2.2.3, NumPy 2.3.5 y Matplotlib 3.10.8.
La salida anterior registra Python y la fecha técnica de ejecución. La primera celda
instala solo lo que falta antes de importar las bibliotecas. Si ya se habían importado
versiones distintas, reiniciar la sesión de Colab y ejecutar desde el principio.
Las respuestas numéricas corresponden a este entorno; no se copian las referencias
del PDF para sustituir una ejecución distinta.
"""
    data_cell.source += """
assert not df.isna().any().any()
assert df["moroso"].value_counts().to_dict() == {0: 112, 1: 48}
limites = {
    "monto_fiado": (20, 300), "compras_mes": (0, 20),
    "dias_sin_comprar": (0, 45), "fiados_previos": (0, 30),
    "pagos_puntuales": (0, 30), "dias_prom_pago": (2, 30),
    "deuda_vencida": (0, 150), "antiguedad_meses": (1, 60),
}
for columna, (minimo, maximo) in limites.items():
    assert df[columna].between(minimo, maximo).all(), columna
print("Validaciones: 160 IDs únicos, sin nulos, clases 112/48 y rangos correctos.")
"""

    cells["9256efd2"].source += """

No incluimos `cliente` como predictor. Se mantienen exactamente las ocho variables
del taller. No se introduce `punctuality_rate` aquí: ese campo corresponde al contrato
de Baylón y se explica en la transferencia del Paso 9.
"""
    cells["a4670eef"].source += """

La matriz se calcula para AdaBoost de 50 rondas, el modelo elegido al final; no para
el árbol usado como recurso didáctico de explicabilidad.
"""
    cells["2a37476f"].source = cells["2a37476f"].source.replace(
        'morosos reales:', 'morosos según la etiqueta simulada:'
    )
    cells["f7b431ce"].source = cells["f7b431ce"].source.replace(
        "morosos reales", "morosos según la etiqueta simulada"
    )

    cells["aa234a50"].source = """## Paso 9 · Conclusiones del taller — Caso Bodega Doña Rosa

1. **Modelo elegido:** AdaBoost con 50 rondas. Accuracy 0.950, precision 0.917,
recall 0.917 y F1 0.917. Detecta 11 de 12 morosos con una falsa alerta. SVM empata
en las cuatro métricas: no afirmamos superioridad estadística de AdaBoost. Lo usamos
para la priorización reproducible del ejercicio. El árbol es más fácil de explicar,
pero con igual recall genera siete falsos positivos y precision 0.611; no se elige
solo por ser interpretable. Los resultados de esta bodega no eligen el modelo de Baylón.

2. **Métrica priorizada:** recall de atraso, acompañado de precision y F1. Una omisión
deja sin advertencia un fiado potencialmente atrasado; no prueba que se perderá todo
el monto. Bajo el supuesto didáctico de S/ 150 por falso negativo, uno equivale a
S/ 150 de exposición hipotética. No es pérdida observada ni ahorro demostrado.
Una referencia que siempre dice puntual alcanza 70 % de accuracy y recall cero.

3. **Umbral y capacidad:** 0.5 como filtro y top 10 por puntaje sin redondear como
límite de atención. Hay 12 alertas, se atienden 10 y dos quedan pendientes.
Los diez contactos incluyen nueve morosos: precision@10 = 90 % y recall@10 = 75 %.
No confundirlos con el recall 91.67 % del clasificador. Ninguno de los umbrales
0.3/0.5/0.7 produce exactamente diez alertas por sí solo. Con 0.7 no hay alertas.
El puntaje del décimo puesto no se convierte en umbral universal para otras semanas.

4. **Explicabilidad:** para explicar un árbol mostramos una ruta completa de reglas
en soles y días. AdaBoost combina reglas débiles y no es ese mismo árbol: las reglas
del Paso 5 no explican exactamente sus decisiones. Para una llamada, revisaríamos
el historial concreto, el motivo del contacto y la evidencia disponible. Los puntajes
de `predict_proba` no son probabilidades de riesgo real cuya calibración se haya demostrado.

5. **Ética y límites:** recordatorios respetuosos, revisión humana, privacidad,
corrección de datos y límites de contactos repetidos. Ser nuevo no debe convertirse
en una sanción automática. Registraríamos versión, variables, posición, última llamada
y decisión humana; auditaríamos errores por historial/antigüedad antes de usarlo.
Esto es un plan de control, no una demostración de ausencia de sesgo. La prueba tiene
40 registros sintéticos y fue consultada en varios retos; no acredita desempeño futuro.

6. **Transferencia a Cervecería Baylón (Credify):** replicaremos preparación sin fuga,
comparación y selección informada; no copiaremos la base ni el modelo de Doña Rosa.
La usuaria confirmó que Baylón tiene registros ficticios, no 30–50 fiados reales.
Esa cantidad era una meta de captura de APF2. Mantendremos una fila por fiado
evaluado, las once variables del snapshot y `origen=simulado` mientras corresponda.
El target del proyecto es `late_payment`: atraso desde el vencimiento del fiado a
un día, no la regla de más de siete días de este taller. No se puede trasladar la
etiqueta renombrando `moroso` ni usar el score por reglas como verdad de pago.

### Qué replicaremos y qué no en APF3

| Aspecto | Doña Rosa, taller | Baylón, proyecto |
|---|---|---|
| Unidad/target | Cliente: atraso > 7 días | Fiado: late_payment al vencimiento |
| Fuente | 160 clientes simulados | Ficticios; origen=simulado; justificar generador |
| Variables | Ocho atributos del PDF | Once campos de APF2; no copiar esquema del taller |
| Modelos | SVM, KNN, árbol, AdaBoost | Árbol y SVM son candidatos, no ganadores anticipados |
| Ajuste | Retos sobre prueba | CV en entrenamiento; Pipeline y agrupación por cliente |
| Test final | Consultado varias veces | Reservado hasta congelar; no reajustar con el final v2 |
| Acción | Hasta 10 recordatorios | Revisión del fiado; capacidad por acordar con propietarios |
| Umbral | 0.3, 0.5, 0.7 y top 10 | Elegir en validación; no copiar diez llamadas sin evidencia |
| Integración | Ejercicio aislado | Exportar Pipeline/umbral/contrato; inferencia de caso nuevo |

Para Baylón, recall es una prioridad candidata si se justifica el costo de omitir
atrasos; también se controlarán precision y volumen de revisiones. El objetivo
financiero del 5 % de APF2 no es prevalencia ni precisión del modelo. Los coeficientes
o reglas deben provenir del modelo realmente entrenado en Baylón, no de este taller.

La caída de accuracy de AdaBoost de 50 a 400 rondas en este ejercicio ilustra
sobreajuste en esta partición, no una ley de que Boosting siempre sobreajusta con
pocos datos. Ni el árbol ni SVM tienen garantía automática de generalización.
Un cliente nuevo requerirá tratamiento y auditoría explícitos: no afirmamos que el
modelo no use antigüedad o no tenga sesgos por haber redactado esa intención.

**Estado del proyecto:** esta transferencia es un plan concreto, no una implementación
operativa nueva. No se cambió el modelo de producción ni el laboratorio v2, ni se
mezclaron datasets. El notebook no se conecta al servidor del negocio.

## Preparación de la entrega en Colab

1. Confirmar la pareja participante; los cuatro códigos ya están en la celda inicial.
2. En Google Colab: Archivo → Subir notebook, seleccionar este `.ipynb`.
3. En una sesión nueva: Entorno de ejecución → Ejecutar todo; revisar tablas y respuestas.
4. Guardar la copia en Drive. Compartir → Cualquier usuario que tenga el vínculo → Lector.
5. Abrir el enlace en incógnito y comprobar que no solicita acceso. Pegar ese enlace
en UTPCLASS y verificar el estado Enviado; no entregar solo el archivo adjunto.

**Datos para el comentario de entrega:** Coveñas U23204737; Baylón U23231338;
Paredes U23259768; Yman U23251279. Conservar los participantes autorizados.
Modelo elegido: AdaBoost, 50 rondas; recall en prueba: 91.67 % (11/12), datos simulados.

La preparación asistida y los controles automáticos no sustituyen las observaciones
y revisión de los estudiantes. Antes de enviar, cada participante debe poder explicar
cualquier celda. La publicación y el envío requieren la cuenta de Google del grupo.
"""

    verify = nbformat.v4.new_code_cell(
        """# Comprobación final: los textos y tablas deben coincidir con la ejecución real.
import json
from sklearn.dummy import DummyClassifier

base = DummyClassifier(strategy="most_frequent").fit(X_train, y_train)
print("Línea base adicional (no quinto modelo del reto): accuracy =",
      accuracy_score(y_test, base.predict(X_test)), "; recall =",
      recall_score(y_test, base.predict(X_test), zero_division=0))
esperados = {
    "SVM": [0.95, 11/12, 11/12, 11/12],
    "KNN (k=3)": [0.9, 0.9, 0.75, 9/11],
    "Árbol": [0.8, 11/18, 11/12, 11/15],
    "Boosting": [0.95, 11/12, 11/12, 11/12],
}
for nombre, esperado in esperados.items():
    assert np.allclose(comparacion.loc[nombre].to_numpy(), esperado), nombre
assert matriz.tolist() == [[27, 1], [1, 11]]
assert np.allclose(tabla_k["Accuracy"], [0.875, 0.9, 0.9, 0.9, 0.925])
assert np.allclose(tabla_k["Recall"], [0.75, 0.75, 0.75, 8/12, 0.75])
assert np.allclose(tabla_b["Accuracy entrenamiento"], [0.95, 1.0])
assert np.allclose(tabla_b["Accuracy prueba"], [0.95, 0.875])
assert tabla_u["N.º de alertas"].tolist() == [35, 12, 0]
assert np.allclose(tabla_u["Recall"], [1.0, 11/12, 0.0])
assert np.allclose(tabla_u["Precisión"], [12/35, 11/12, 0.0])
assert top10["cliente"].tolist() == [
    "C036", "C135", "C119", "C075", "C014",
    "C016", "C021", "C131", "C158", "C117",
]
assert len(llamadas) == 10 and int(llamadas["real"].sum()) == 9
resumen_verificado = {
    "versiones": requisitos,
    "filas": len(df), "entrenamiento": len(X_train), "prueba": len(X_test),
    "comparacion": comparacion.to_dict(orient="index"),
    "matriz_adaboost": matriz.tolist(),
    "llamadas": len(llamadas), "atrasados_en_llamadas": int(llamadas["real"].sum()),
    "precision_top10": float(llamadas["real"].mean()),
    "recall_top10": float(llamadas["real"].sum()/y_test.sum()),
    "passed": True,
}
print("Registros, métricas, retos y top 10 verificados; sin conectar con el proyecto.")
print("RESUMEN_VERIFICADO=" + json.dumps(resumen_verificado, ensure_ascii=False))
"""
    )
    notebook.cells.append(verify)
    notebook.metadata.colab = {"provenance": [], "name": "S14A_TallerML_Grupo2_Colab.ipynb"}
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.execution_count = None
            cell.outputs = []
    nbformat.validate(notebook)
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "S14A_TallerML_Grupo2_Colab.ipynb"
    assert source.resolve() != destination.resolve()
    started = datetime.now(UTC).isoformat()
    NotebookClient(notebook, timeout=300, kernel_name="python3").execute(cwd=str(output))
    nbformat.validate(notebook)
    code = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert len(code) == 12 and all(cell.execution_count for cell in code)
    assert not any(item.output_type == "error" for cell in code for item in cell.outputs)
    images = sum("image/png" in item.get("data", {}) for cell in code for item in cell.outputs)
    assert images == 3, "EDA, tree and confusion-matrix figures must be embedded"
    stdout = "".join(item.text for item in verify.outputs if item.output_type == "stream")
    summary = json.loads(stdout.split("RESUMEN_VERIFICADO=", 1)[1].strip())
    assert summary["passed"]
    nbformat.write(notebook, destination)
    (output / "verificacion-ejecucion.json").write_text(json.dumps({
        "started_utc": started,
        "finished_utc": datetime.now(UTC).isoformat(),
        "source_sha256": hashlib.sha256(original_bytes).hexdigest(),
        "dataset_sha256": hashlib.sha256(data.encode()).hexdigest(),
        "notebook_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "executed_code_cells": len(code),
        "embedded_figures": images,
        "errors": 0,
        "results": summary,
        "human_review": "Pending; technical execution is not student acceptance",
    }, ensure_ascii=False, indent=2) + "\n")
    assert source.read_bytes() == original_bytes, "Original notebook must remain unchanged"
    print(f"Notebook verificado: {destination}; {len(code)} celdas ejecutadas sin errores")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    build(args.source, args.output_dir)
