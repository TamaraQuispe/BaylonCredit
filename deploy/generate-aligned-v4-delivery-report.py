"""Export a separate delivery edition using frozen evidence, never ML execution."""

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import shutil
import statistics
import subprocess
from pathlib import Path
from zipfile import ZipFile

from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader

REPO = Path(__file__).resolve().parents[1]
ORIGINAL = Path("/Users/tamaraalison/Downloads/APF3_Grupo2_Alineado_V4")
ROOT = Path("/Users/tamaraalison/Downloads/APF3_Grupo2_Entrega_V4")
SOURCE = REPO / "docs/APF3_TD_Grupo2_ML_Innovacion_Entrega_V4.md"
NAME = "APF3_TD_Grupo2_ML_Innovacion"
STATUS = "Datos simulados | Edición de entrega; revisión humana pendiente"
SPEC = importlib.util.spec_from_file_location(
    "original_v4_report", Path(__file__).with_name("generate-aligned-v4-report.py")
)
V4 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V4)
HELPER = V4.HELPER
digest, write_json = HELPER.digest, HELPER.write_json


def compose(read, root):
    """Materialize editorial source from the delivered original and audit annexes."""
    text = read(ORIGINAL / "informe/APF3_TD_Grupo2_ML_Innovacion_Borrador.md")
    pages = text.split("<!-- PAGE -->")
    pages[0] = (
        pages[0]
        .replace("14 páginas manuales", "15 páginas de cuerpo")
        .replace("15 antes de referencias", "16 antes de referencias")
        .replace("ni despliegue V4", "ni despliegue público V4")
    )
    pages[0] += "\n\n**Estado editorial:** " + STATUS + ".\n"
    pages[1] = pages[1].replace(
        "**Para los propietarios, se propone anticipar si un fiado otorgado tendrá atraso frente al vencimiento contractual de un día, usando exclusivamente el historial visible antes de otorgarlo, para priorizar revisión humana.**",
        "**Para el usuario propietario, se propone priorizar la revisión del fiado a un día con historial previo, medido por F2 de política y la meta propuesta de reducir minutos de revisión frente a revisar todo, sin superar cinco alertas/día y reportando el costo de los atrasos omitidos.**",
    )
    pages[1] = pages[1].replace(
        "Lean Startup y Kanban organizan la evolución, pero no sustituyen evidencia predictiva (Grupo 2, 2026a, 2026b).",
        "Lean Startup y Kanban organizan la evolución (Grupo 2, 2026a, 2026b). URL pública heredada del MVP/demo: https://demo-credify.168-75-71-113.sslip.io. Demo y producción son entornos distintos; no se verificó disponibilidad actual ni se afirma V4 público.",
    )
    continuity = """
## 1.3. Trazabilidad APF2 y meta propuesta

Fuente primaria: APF2 original, Tabla 17, página física 10 / impresa 9, y B.4, física 20 / impresa 19. El diccionario de apoyo está en `APF2_Insumos_Para_Claude.md`, líneas 155-182. No se consultó la base real actual para esta edición.

| Campo / contrato APF2 | Fuente prevista | Fórmula / alcance APF3 | Cambio declarado |
| --- | --- | --- | --- |
| completed_sales | Ventas registradas al evaluar | Conteo de ventas completadas vinculadas a fiados previos | Restricción V4: solo ventas de crédito; MVP incluía todas las ventas |
| paid_credits; paid_late | Créditos y pagos anteriores | Pagados completos; de ellos, pagados tarde | Semántica conservada; eventos simulados |
| pending_overdue; pending_current | Créditos activos | Conteos con saldo vencidos / no vencidos al evaluar | Conservados; snapshot anterior al otorgamiento |
| outstanding; utilization | Saldos y máximo configurado | Saldo previo; saldo / 80 PEN | Cupo fijo sintético, no cupo real estimado |
| requested_ratio; tenure_days | Solicitud; registro del cliente | Monto / 80; días desde registro | Cupo fijo y registro simulado |
| punctuality_rate; overdue_rate | Pagos; créditos activos | (pagados - tardíos) / pagados; vencidos / activos | Sin denominador: 0 por convención, no evidencia |
| late_payment | Vencimiento y pagos | 0 puntual; 1 tardío o saldo vencido; desconocido excluido | Target de atraso sin cambio; no impago a 30 días |
| Fuente, volumen y evaluación | 30-50 fiados reales consentidos en 4-6 semanas | 552 etiquetas sintéticas DEV; CV por cliente | Cero elegibles al cierre APF2; simulación no reemplaza piloto real |

**Meta empresarial PROPUESTA, no aprobada.** Para un piloto futuro autorizado: registrar ANTES minutos de revisar todo en un periodo de referencia y DESPUÉS minutos de la política en un periodo comparable, volumen elegible, revisiones, atrasos omitidos y falsas alertas con desenlace maduro. Criterio observable propuesto: minutos DESPUÉS < minutos de referencia, máximo cinco alertas/día y reporte explícito de FN/FP y sus consecuencias. No hay baseline cronometrado, costo FN acordado ni meta financiera numérica; no basta reducir tiempo para aceptar un daño no acordado.

Esta propuesta retrospectiva de piloto no fue predeclarada para seleccionar modelos y no retoca FINAL. El criterio técnico ex ante permanece F2 de política superior a ambas referencias Dummy y capacidad limitada. El resultado actual son 79 revisiones menos y tres FN más, no éxito empresarial incondicional.
"""
    pages.insert(2, continuity)
    pages[3] += """

**Ficha de coherencia, consigna §4.2:** Escala del negocio; Rangos y unidades; Consistencia lógica y temporal; Relaciones plausibles; Señal ni nula ni perfecta; Coherencia con APF2; Mezcla real + simulado: N/A. La tabla completa del Anexo F distingue evidencia guardada, reservas y anclas aproximadas; conserva además los controles comerciales de calibración. No son observaciones nuevas.

**Calidad DEV:** 552 supervisadas, 24 clientes, cero nulos, IDs duplicados y vectores repetidos; once snapshots contrastados sin diferencias. Los siete targets desconocidos se conservan fuera de supervisión. IQR es descriptivo, no motivo para borrar extremos. Diccionario de las 24 columnas con tipo, unidad, rango y política de nulos: Anexo G y [CSV](../anexos/datos/diccionario-datos.csv).
"""
    relationships = """
## 2.5. EDA DEV: historial y antigüedad-ventas

Análisis post hoc del DEV congelado, no exploración prospectiva previa al experimento. Las dos relaciones se fijaron antes del cálculo descriptivo de esta auditoría, no antes de la corrida ML. No se seleccionan nuevas variables ni modelos.

![Figura 2. DEV resuelto: historial frente a atraso y antigüedad frente a ventas de crédito; scatter con las 552 filas.](figuras/eda_relaciones_entrega.png)

**Historial:** sin atraso previo, 8/218 (3,67 %); con atraso previo, 60/334 (17,96 %). No hay casos sin pagos previos (0/0, no estimable). La asociación puede reflejar la propensión latente estable supuesta por cliente, no causalidad ni riesgo medido en personas reales.

| Antigüedad, bandas fijas | Fiados | Clientes distintos | Mediana ventas |
| --- | --- | --- | --- |
| 30-119 días | 80 | 10 | 8 |
| 120-239 días | 302 | 24 | 13 |
| >=240 días | 169 | 17 | 21 |

Una fila de 28 días queda fuera de bandas, pero está en el scatter de las 552 filas. Las medianas 8/13/21 apoyan acumulación de operaciones en este escenario; no una señal causal de atraso. Registro inicial aleatorio y calentamiento común limitan la exposición observada; completed_sales solo cuenta ventas vinculadas a crédito.

Hay clientes compartidos entre bandas y fiados repetidos por cliente: no son observaciones independientes ni una segunda fuente comercial. Sin p-valores, causalidad ni validación predictiva. La CV por cliente no prueba generalización temporal ni corrige estacionariedad supuesta. La relación adversa de exposición se conserva íntegra en el Anexo F: 551 casos en la primera banda, uno en la segunda y cero en la tercera no permiten afirmar tendencia de riesgo.

Solo tres figuras: balance, estas relaciones y matriz SVM leída de métricas congeladas; sin nuevas predicciones.
"""
    idx = next(i for i, p in enumerate(pages) if "## 2.5." in p)
    exposure_page = pages[idx]
    pages[idx] = relationships
    idx = next(i for i, p in enumerate(pages) if "# 5. Integración" in p)
    pages[idx] = (
        pages[idx]
        .replace(
            "La demo heredada es https://demo-credify.168-75-71-113.sslip.io y el laboratorio `/laboratorio-academico` **sigue en v2, no en V4**. Las capturas previas no prueban disponibilidad actual, integración o aceptación V4. No se fabrican capturas, aprobaciones ni pruebas de interfaz nuevas.",
            "Recapitulación APF2: MVP persistente de clientes, fiados y abonos por reglas. Producción y demo pública son entornos distintos; la URL pública heredada del MVP/demo es https://demo-credify.168-75-71-113.sslip.io. No se verificó su disponibilidad actual ni se afirma que exponga V4. La demo pública/v2 no acredita el laboratorio V4 local.",
        )
        .replace(
            "La integración V4 es local y separada de la web: `predict(artifact_dir, input_data)` y CLI del runner `academic_credit_aligned_v4.py`. Carga el Pipeline confiable, verifica manifiesto/hashes y contrato de once campos, y aplica el umbral congelado. No es un endpoint de producción ni otorga créditos; conectar este contrato al MVP requiere pruebas y controles propios. No se midieron latencia, memoria o SLA V4.",
            "La integración actual V4 incluye web local `/laboratorio-academico/v4`, API autenticada `/api/v1/academic-ml/v4` y CLI, separadas de producción. El stack local con imagen y DB ficticia fue probado; aplica solo el ejemplo ilustrativo guardado, no cohortes FINAL. Verifica contrato/hashes y usa bundle de confianza solo lectura, flag staging deshabilitado por defecto. No crea créditos ni aplica cola diaria operativa. La muestra API de memoria fue 160,9 MiB frente al límite 256 MiB: observación puntual, no garantía bajo carga. Evidencia: [stack V4](../anexos/integracion/evidence-stack-v4.json).",
        )
    )
    latency = root / "anexos/integracion/latencia-v4.json"
    bench = json.loads(read(latency))
    assert bench["status"] == "passed" and bench["bundle_unchanged"]
    assert not bench["new_training"] and not bench["final_inference"]
    assert bench["case_id"] == "illustrative-v4" and bench["known_label"] is None
    samples = bench["samples_ms"]
    assert len(samples) == bench["warm_service_calls"] == 30
    assert statistics.median(samples) == bench["warm_service_ms"]["median"]
    assert sorted(samples)[28] == bench["warm_service_ms"]["p95_nearest_rank"]
    assert min(samples) == bench["warm_service_ms"]["min"]
    assert max(samples) == bench["warm_service_ms"]["max"]
    assert len(bench["bundle_sha256"]) == 6
    for name, sha in bench["bundle_sha256"].items():
        artifact = root / "laboratorio/artefactos" / name
        assert digest(artifact) == sha, name
        if artifact.suffix == ".json":
            read(artifact)

    def ms(value):
        return f"{value:.2f}".replace(".", ",")

    pages[idx] += (
        "\n\n**Medición local de servicio:** validación de bundle "
        + ms(bench["bundle_validation_cold_ms"])
        + " ms; carga del modelo + primera predicción "
        + ms(bench["model_load_and_first_prediction_ms"])
        + " ms; "
        + str(bench["warm_service_calls"])
        + " llamadas warm: mediana "
        + ms(bench["warm_service_ms"]["median"])
        + " ms, p95 (nearest-rank) "
        + ms(bench["warm_service_ms"]["p95_nearest_rank"])
        + " ms. Pico RSS del proceso: "
        + str(bench["peak_process_rss_kib"])
        + " KiB, independiente de los 160,9 MiB del stack. "
        "Solo load_bundle + evaluate del ejemplo fijo confiable; no FINAL, HTTP, DB, navegador, "
        "concurrencia sostenida ni SLA. [Evidencia](../anexos/integracion/latencia-v4.json); "
        "este generador no ejecuta inferencia.\n"
    )
    pages[idx] += (
        "\n\nEntrega por archivos para Aula Virtual: [código](../codigo/scripts/academic_credit_aligned_v4.py) y dependencias versionadas del paquete; enlace local, no publicación pública ni prueba de acceso docente. GitHub/CV3 es solo antecedente.\n"
    )
    idx = next(i for i, p in enumerate(pages) if "# 6. Normativa" in p)
    start = pages[idx].index("| Área |")
    end = pages[idx].index("\n\nNombres académicos", start)
    pages[idx] = (
        pages[idx][:start]
        + """| Requisito normativo | Control en dataset/modelo | Evidencia concreta y límite |
| --- | --- | --- |
| Finalidad y minimización | Investigación sintética, once predictores; alerta no rechaza | Contrato V4, research_only; finalidad/base real pendientes |
| Seguridad y custodia | JWT, flag staging, bundle solo lectura y hashes | Servicio/rutas V4; hashes no autentican al publicador ni vuelven seguro un Joblib ajeno |
| Información y derechos | No hay consentimiento nuevo de clientes ni circuito ARCO acreditado | US09 APF2 pendiente; aviso, retención, borrado y responsables abiertos |
| Terceros y exposición | Sin IA externa para inferencia V4; solo ejemplo guardado | Servicio local; nube/transferencias y privacidad global no auditadas |
"""
        + pages[idx][end:]
    )
    pages[idx] = pages[idx].replace(
        "La web sigue v2;", "La web V4 está probada solo localmente;"
    )
    pages[idx] = pages[idx].replace(
        "Riesgos y responsables del Anexo D son propuestas.",
        "Riesgos y responsables del Anexo D son propuestas. El Anexo H integra normativa y prompts disponibles: historial anterior incompleto declarado, no puede reconstruirse; validación humana pendiente. Meta/costos y cierre jurídico del piloto son trabajo operativo futuro, no requisitos previos de esta entrega académica.",
    )
    for i, p in enumerate(pages):
        if "## 4.4." in p:
            pages[i] += (
                "\n\n**Acción:** usar señales para revisión, nunca rechazo automático. Contrastar deuda, vencimientos y capacidad de pago; investigar los signos contraintuitivos con futuros datos autorizados, sin inferir que endeudarse beneficia ni cambiar ahora el umbral.\n"
            )
        pages[i] = (
            pages[i]
            .replace(
                "| Paginación PDF | Portada + 14 páginas de cuerpo; 25 en total | 15 antes de referencias/anexos; control A4 sin desbordes |",
                "| Paginación PDF | Edición de entrega, 15 páginas de cuerpo | Conteo físico y total en verificacion-informe-entrega.json |",
            )
            .replace(
                "| Integración | CLI local; web v2 heredada | Pruebas y autorización separadas antes de cualquier piloto V4 |",
                "| Integración | Web/API V4 probadas solo localmente; demo pública heredada/v2 | No acredita producción, URL pública V4 ni aceptación humana |",
            )
        )
    # Full audit text is embedded, not just linked, with explicit physical breaks.
    data = read(root / "anexos/datos/coherencia-datos.md")
    coherence = data.split("| Criterio original |", 1)[1].split("\n\n", 1)[0]
    criteria = [line.split("|")[1].strip() for line in coherence.splitlines()[2:]]
    assert criteria == [
        "Escala del negocio",
        "Rangos/unidades",
        "Consistencia lógica/temporal",
        "Relaciones plausibles",
        "Señal ni nula ni perfecta",
        "Coherencia con APF2",
        "Mezcla real+simulado",
    ], "Esperar ficha corregida de consigna §4.2"
    data_parts = re.split(
        r"(?=## Calidad DEV|## Desconocidos|## Dos Relaciones Fijas|## Ficha Principal|## Restricciones de calibración)",
        data,
    )
    for part in data_parts:
        pages.append("\n\n# Anexo F. Auditoría DEV y coherencia completa\n\n" + part)
    original_exposure = exposure_page[
        exposure_page.index("**Conclusión sobre exposición.**") :
    ]
    original_exposure = original_exposure.split("Los tres únicos gráficos")[0]
    pages.append(
        "\n\n# Anexo F. Exposición sin tendencia acreditada\n\n" + original_exposure
    )
    dictionary = read(root / "anexos/datos/diccionario-datos.md")
    intro, tab = dictionary.split("| columna |", 1)
    lines = ("| columna |" + tab).strip().splitlines()
    for offset in range(0, 24, 6):
        pages.append(
            "\n\n# Anexo G. Diccionario completo, columnas "
            + f"{offset + 1}-{min(offset + 6, 24)}\n\n"
            + intro
            + "\n\n"
            + "\n".join(lines[:2] + lines[2 + offset : 2 + offset + 6])
        )
    annex = read(REPO / "docs/APF3_Anexos_Cierre_V4.md")
    annex = (
        annex.replace(
            "Cinco bloques separados por `<!--PAGE-->`; son paginas logicas, no una paginacion PDF comprobada.",
            "Cinco bloques de origen integrados en esta edicion y redistribuidos para exportacion A4; el conteo fisico consta en la verificacion de entrega.",
        )
        .replace(
            "Este Markdown aun no esta integrado en PDF/DOCX/ZIP ni cubierto por sus manifiestos anteriores.",
            "Este contenido esta integrado en el informe de entrega PDF/DOCX/HTML; no se afirma inclusion en ZIP ni cobertura de manifiestos anteriores.",
        )
        .replace(
            "integracion/exportacion de este anexo pendiente",
            "acceso docente y cierre humano pendientes",
        )
    )
    annex = annex.replace(
        "**Conservacion pendiente:** recuperar y conservar el historial literal completo original, si existe, con herramienta/modelo, instrucciones, respuestas y alcance real. No sustituirlo por prompts plausibles escritos retrospectivamente. Protocolo, provenance, codigo, hashes y verificacion de artefactos son evidencia tecnica, **NO prueba de autoria, revision humana, consentimiento ni aprobacion**. El anexo declara lo conocido, no cierra la ausencia del historial IA anterior exigido por la consigna.",
        "**Limite del registro:** historial anterior incompleto declarado; no puede reconstruirse ni sustituirse por prompts plausibles retrospectivos. Se conservan los prompts literales disponibles; la consigna pide el anexo de prompts, no toda conversacion historica completa. Protocolo, provenance, codigo y hashes son evidencia tecnica, **NO prueba de autoria, revision humana, consentimiento ni aprobacion**. Validacion humana pendiente.",
    ).replace(
        "No marcar entrega integral ni uso de IA totalmente documentado mientras estas brechas sigan abiertas.",
        "Mantener el historial anterior incompleto declarado, sin exigir reconstruir toda conversacion como requisito de la rubrica; registrar la validacion humana efectivamente realizada antes de afirmarla.",
    )
    annex += "\n\nMeta/costos aprobados, piloto real, cierre juridico operativo y activacion publica V4 corresponden a una futura operacion autorizada; no se presentan como requisitos previos de la entrega academica APF3. La validacion humana pendiente se distingue de esas condiciones futuras.\n"
    annex = (
        annex.replace(
            "Anexos de cierre para integracion documental posterior.",
            "Anexos de cierre integrados en la edicion documental de entrega.",
        )
        .replace(
            "Este archivo no modifica el informe, el paquete congelado, el protocolo ni el runtime y no constituye acta de aprobacion.",
            "Esta integracion documental no modifica el paquete original congelado, el protocolo ni el runtime y no constituye acta de aprobacion.",
        )
        .replace(
            "El conteo de paginas del informe original no incluye este nuevo anexo.",
            "Estas cifras describen exclusivamente la exportacion anterior; el conteo de entrega consta en verificacion-informe-entrega.json.",
        )
        .replace(
            "**Verificacion de esta edicion:** solo lectura de fuentes y revision estructural/enlaces de este Markdown.",
            "**Verificacion del anexo de origen:** solo lectura de fuentes y revision estructural/enlaces del Markdown. La integracion de entrega agrega exportacion y render fisico, registrados por separado.",
        )
        .replace(
            "**PUBLICACION NO AUTORIZADA.** Esta edicion solo crea el Markdown.",
            "**PUBLICACION NO AUTORIZADA.** Esta edicion genera archivos locales MD/DOCX/HTML/PDF, no publicacion remota.",
        )
        .replace(
            "Este Markdown aun no esta integrado en PDF/DOCX/ZIP ni cubierto por sus manifiestos anteriores.",
            "El anexo esta integrado en los formatos documentales de entrega, no en ZIP ni en manifiestos anteriores.",
        )
    )
    # Rebase repository code links for the delivery, not a public repository.
    annex = re.sub(r"\]\(\.\./backend/(.*?)\)", r"](../codigo/\1)", annex)
    annex = re.sub(r"\]\(\.\./deploy/(.*?)\)", r"](../codigo/deploy/\1)", annex)
    annex = re.sub(
        r"\]\((APF[^)]+\.md|PUBLICATION\.md)\)", r"](../codigo/docs/\1)", annex
    )
    annex = annex.replace(
        "](../docker-compose.academic-v4.yml)",
        "](../codigo/docker-compose.academic-v4.yml)",
    )
    for part in annex.split("<!--PAGE-->"):
        part = re.sub(r"^# Anexo ([A-E])\.", r"# Anexo H. Bloque \1.", part.strip())
        # The prompt and normative matrices need two physical pages each.
        if "| Requisito normativo |" in part or "| Prompt literal disponible |" in part:
            blocks = part.split("\n\n")
            ti = next(
                i
                for i, b in enumerate(blocks)
                if b.startswith(("| Requisito", "| Prompt literal"))
            )
            rows = blocks[ti].splitlines()
            size = 3 if "| Requisito normativo |" in part else 4
            for offset in range(2, len(rows), size):
                heading = (
                    blocks[:ti]
                    if offset == 2
                    else ["# Anexo H. Matriz completa, continuación"]
                )
                tail = blocks[ti + 1 :] if offset + size >= len(rows) else []
                pages.append(
                    "\n\n"
                    + "\n\n".join(
                        heading
                        + ["\n".join(rows[:2] + rows[offset : offset + size])]
                        + tail
                    )
                )
        elif "# Anexo H. Bloque E." in part:
            first, second = part.split(
                "**Checklist de acceso y entrega, aun pendiente de comprobacion humana:**"
            )
            pages.append("\n\n" + first)
            pages.append(
                "\n\n# Anexo H. Acceso y entrega, continuación\n\n"
                + "**Checklist de acceso y entrega, aun pendiente de comprobacion humana:**"
                + second
            )
        else:
            pages.append("\n\n" + part)
    pages.append("""
# Anexo I. Índice de evidencia y brechas

| Criterio | Página PDF / archivo de entrega |
| --- | --- |
| Continuidad, usuario, meta y cambios APF2 | 2-3; APF2 Tabla 17 y B.4 |
| Fuente, calidad, coherencia y diccionario | 4-7; Anexos A, F y G; anexos/datos/ |
| Modelado, CV y selección | 8-10; Anexo B; experimento/frozen_selection.json |
| Métricas y errores, sin ocultar desfavorables | 11-14; 224 celdas cotejadas; Anexo B |
| Integración y ejemplo | 15; anexos/integracion/; codigo/ |
| Normativa, riesgos, proyección y conclusiones | 16; Anexos D y H |
| Reproducción y dependencias | Anexo C; verificacion-reproduccion.json del paquete original; versiones fijadas, no reinstaladas aquí |
| IA y revisión humana | Anexos E y H: prompts disponibles, historial previo incompleto; revisión y ensayo pendientes |
| Paginación e integridad documental | verificacion-informe-entrega.json; manifest-informe-entrega.json |

No se declara cumplimiento integral ni validación humana completada: revisión aplicada, ensayo real y acceso docente siguen pendientes de constancia. Historial anterior incompleto declarado, no puede reconstruirse; se anexan los prompts literales disponibles sin atribuir a la rúbrica la exigencia de toda conversación histórica. Meta/costos aprobados, consentimiento/base jurídica, ARCO y piloto real son condiciones de futura operación autorizada, no bloqueos previos de la entrega académica. Publicar V4 no es obligatorio para entregar código. No se inventan contribuciones ni aprobaciones; archivos locales no prueban acceso remoto docente.
""")
    return "\n\n<!-- PAGE -->\n\n".join(p.strip() for p in pages) + "\n"


def render(output, text):
    module = os.environ.get(
        "PLAYWRIGHT_MODULE_PATH",
        "/var/folders/sx/_6ljw37n2_j9hk2f_vtqplj40000gn/T/opencode/apf3-render/node_modules/playwright/index.mjs",
    )
    js = r"""
import {readFile} from 'node:fs/promises';
const {chromium} = await import(process.argv[1]);
const browser = await chromium.launch();
try {
 const page = await browser.newPage({viewport:{width:658,height:1120}});
 await page.route('**/*', r=>r.abort());
 await page.setContent(await readFile(process.argv[2], 'utf8'));
 await page.emulateMedia({media:'print'});
 await page.evaluate(()=>document.fonts.ready);
 await page.evaluate(()=>Promise.all([...document.images].map(i=>i.decode())));
  const sections = await page.locator('.page').evaluateAll(es=>es.map(e=>{
   const r=e.getBoundingClientRect();
   const recap=[...e.querySelectorAll('h2')].find(h=>h.textContent.startsWith('1.1.'));
   const problem=[...e.querySelectorAll('h2')].find(h=>h.textContent.startsWith('1.2.'));
   return {title:e.querySelector('h1,h2')?.textContent,height_px:Math.ceil(r.height),
    recap_height_px:recap&&problem?Math.ceil(problem.getBoundingClientRect().top-recap.getBoundingClientRect().top):null,
    body_font_pt:parseFloat(getComputedStyle(e).fontSize)*72/96,
    overflow:[...e.querySelectorAll('*')].filter(c=>{const t=c.getBoundingClientRect();return t.left<r.left-1||t.right>r.right+1||c.scrollWidth>c.clientWidth+1}).map(c=>c.tagName)};
 }));
 await page.pdf({path:process.argv[3],preferCSSPageSize:true,printBackground:true,displayHeaderFooter:true,
  headerTemplate:'<div style="font:8px Arial;text-align:center;width:100%">'+process.argv[4]+'</div>',
  footerTemplate:'<div style="font:8px Arial;text-align:center;width:100%"><span class="pageNumber"></span> / <span class="totalPages"></span></div>'});
 console.log(JSON.stringify(sections));
} finally {await browser.close()}
"""
    sections = json.loads(
        subprocess.run(
            [
                "node",
                "--input-type=module",
                "-e",
                js,
                module,
                str(output / (NAME + ".html")),
                str(output / (NAME + ".pdf")),
                STATUS,
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    for i, section in enumerate(sections):
        assert section["height_px"] <= 259 * 96 / 25.4, (i + 1, section)
        assert not section["overflow"], (i + 1, section)
        if section["recap_height_px"] is not None:
            assert section["recap_height_px"] <= 259 * 96 / 25.4 / 2
    pdf = PdfReader(output / (NAME + ".pdf"))
    parts = text.split("<!-- PAGE -->")
    assert len(pdf.pages) == len(parts), (len(pdf.pages), len(parts))
    def normalize(s):
        return re.sub(r"\W+", "", s).lower()
    for i, (p, part) in enumerate(zip(pdf.pages, parts, strict=True)):
        title = part.strip().splitlines()[0].lstrip("# ")
        assert normalize(title) in normalize(p.extract_text()), (i + 1, title)
        assert abs(float(p.mediabox.width) - 595.28) < 1
        assert abs(float(p.mediabox.height) - 841.89) < 1
        assert STATUS in p.extract_text()
    ref = next(
        i for i, part in enumerate(parts) if part.strip().startswith("# Referencias")
    )
    assert ref - 1 <= 15
    assert all(s["body_font_pt"] >= 10 for s in sections[1:ref])
    return {
        "body_pages": ref - 1,
        "pdf_total_pages": len(pdf.pages),
        "cover_pages": 1,
        "references_pages": 1,
        "appendix_pages": len(pdf.pages) - ref - 1,
        "references_start_page": ref + 1,
        "a4": True,
        "overflow": False,
        "pdf_section_titles_match_one_to_one": True,
        "sections": sections,
    }


def generate(root, do_render):
    output = root / "informe"
    assert not root.resolve().is_relative_to(ORIGINAL.resolve())
    sources = {}

    def read(path):
        sources[str(path.resolve())] = digest(path)
        return path.read_text()

    experiment = ORIGINAL / "experimento"
    before = {str(p): digest(p) for p in ORIGINAL.rglob("*") if p.is_file()}
    read(Path(__file__).resolve())
    read(Path(V4.__file__))
    read(Path(HELPER.__file__))
    read(REPO / "docs/APF2_Insumos_Para_Claude.md")
    consigna = Path("/Users/tamaraalison/Downloads/Innovacion_TD_Consigna_APF3.pdf")
    sources[str(consigna)] = digest(consigna)
    apf2 = Path("/Users/tamaraalison/Downloads/APF2_TD_Grupo2_MVP_Innovación.pdf")
    sources[str(apf2)] = digest(apf2)
    pdf = PdfReader(apf2)
    assert "Tabla 17" in pdf.pages[9].extract_text()
    assert "B.4" in pdf.pages[19].extract_text()
    read(REPO / "docs/APF3_LABORATORIO_V4.md")
    read(REPO / "deploy/requirements-academic-v4.txt")
    read(root / "requirements.txt")
    report = json.loads(read(experiment / "aligned_v4_report.json"))
    original_check = json.loads(read(ORIGINAL / "informe/verificacion-informe-v4.json"))
    reproduction = json.loads(read(ORIGINAL / "verificacion-reproduccion.json"))
    assert reproduction["passed"] and original_check["reproduction"]["verified"]
    assert not original_check["reproduction"]["joblib_binary_equal"]
    for path, sha in original_check["experiment_sha256_before"].items():
        assert digest(experiment / path) == sha, path
    for artifact in (root / "anexos/datos").iterdir():
        if artifact.is_file():
            sources[str(artifact.resolve())] = digest(artifact)
    quality = json.loads(read(root / "anexos/datos/calidad-dev-v4.json"))
    assert quality["quality_supervised"]["n"] == 552
    assert quality["frozen_unchanged"]
    assert quality["source_sha256_before"] == quality["source_sha256_after"]
    with (root / "anexos/datos/diccionario-datos.csv").open(newline="") as handle:
        assert len(list(csv.DictReader(handle))) == 24
    stack = root / "anexos/integracion/evidence-stack-v4.json"
    if stack.is_file():
        assert json.loads(read(stack))["status"] == "passed"
    else:
        raise FileNotFoundError(
            "Stack evidence must be supplied by integration owner: " + str(stack)
        )
    text = compose(read, root)
    bench = json.loads(read(root / "anexos/integracion/latencia-v4.json"))
    for name in bench["bundle_sha256"]:
        artifact = root / "laboratorio/artefactos" / name
        sources[str(artifact.resolve())] = digest(artifact)
    code_zip = root / "laboratorio/codigo_fuente_MVP_V4.zip"
    sources[str(code_zip.resolve())] = digest(code_zip)
    with ZipFile(code_zip) as archive:
        entries = archive.namelist()
        assert len(entries) == len(set(entries)), "Duplicate archive entries"
        assert archive.testzip() is None, "Archive CRC failed"
        zip_entries = {
            name: hashlib.sha256(archive.read(name)).hexdigest()
            for name in entries
            if not name.endswith("/")
        }
    source_refs = {}
    zipped_refs = {}

    def source_reference(match):
        label, link = match.groups()
        if (output / link).exists():
            return match[0]
        relative = link.removeprefix("../codigo/")
        if relative.startswith(("app/", "tests/")):
            relative = "backend/" + relative
        elif link.startswith("../entregables/"):
            relative = link.removeprefix("../")
        path = REPO / relative
        entry = "codigo_fuente_MVP_V4/" + relative
        if entry in zip_entries:
            zipped_refs[link] = {"entry": entry, "sha256": zip_entries[entry]}
            return (
                label
                + ": [codigo MVP entregado](../laboratorio/codigo_fuente_MVP_V4.zip), "
                + "entrada `"
                + entry
                + "`"
            )
        if path.is_file():
            read(path)
        source_refs[link] = {
            "label": label,
            "repository_path": relative,
            "file_sha256": digest(path) if path.is_file() else None,
        }
        return label

    text = re.sub(r"(?<!!)\[([^\]]+)\]\((\.\./[^)]+)\)", source_reference, text)
    refs = list(source_refs.values())
    for offset in range(0, len(refs), 8):
        text += (
            "\n\n<!-- PAGE -->\n\n# Anexo J. Referencias de fuentes del repositorio\n\n"
        )
        text += (
            "Las referencias siguientes identifican fuentes consultadas del repositorio, no archivos "
            "prometidos mediante enlaces rotos en la entrega. Sus hashes están en el manifiesto "
            "documental cuando son archivos. No acreditan acceso docente al repositorio ni identidad "
            "del checkout con la corrida congelada. El enlace de código del cuerpo sí apunta a un "
            "archivo local de entrega existente. Estas referencias adicionales no se afirman incluidas "
            "en el ZIP MVP salvo que se indique una entrada comprobada; publicación y Aula Virtual siguen pendientes.\n\n"
        )
        text += (
            HELPER.table(
                ["Referencia", "Ruta de fuente en repositorio"],
                [
                    [ref["label"], "`" + ref["repository_path"] + "`"]
                    for ref in refs[offset : offset + 8]
                ],
            )
            + "\n"
        )
    assert V4.verify_tables(text, report) == 224
    assert "| `okay avanza en el orden que has recomendado` |" in text
    for error in report["models"]["svm"]["error_cases"][:3]:
        assert error["loan_id"] in text and str(error["probability"]) in text
    for key, value in report["models"]["svm"]["interpretation"][
        "standardized_coefficients"
    ].items():
        assert f"| {key} | {value} |" in text
    SOURCE.write_text(text)
    sources[str(SOURCE)] = digest(SOURCE)
    output.mkdir(parents=True, exist_ok=True)
    figures = output / "figuras"
    figures.mkdir(exist_ok=True)
    for name in ("eda_balance.png", "matriz_v4.png"):
        path = ORIGINAL / "informe/figuras" / name
        sources[str(path)] = digest(path)
        shutil.copyfile(path, figures / name)
    shutil.copyfile(
        root / "anexos/datos/eda_relaciones_entrega.png",
        figures / "eda_relaciones_entrega.png",
    )
    (output / (NAME + ".md")).write_text(text)
    result = V4.documents(text, output, name=NAME, expected_figures=3)
    html = output / (NAME + ".html")
    markup = html.read_text().replace(
        "<title>APF3 - Credify - Borrador</title>",
        "<title>APF3 - Credify | " + STATUS + "</title>",
    )
    for i, part in enumerate(text.split("<!-- PAGE -->")):
        if part.strip().startswith("# Anexo"):
            markup = markup.replace(
                f'class="page" data-page="{i}"',
                f'class="page appendix" data-page="{i}"',
            )
    markup = markup.replace(
        "</style>",
        """
.appendix {font-size:9pt;line-height:1.16}
.appendix table {font-size:7.5pt;margin:6px 0}
.appendix td,.appendix th {padding:3px}
.appendix p {margin-bottom:6px}
.appendix h1 {font-size:15pt;margin-bottom:9px}
.appendix h2 {font-size:10pt;margin:9px 0 5px}
.appendix code {font-size:7.3pt}
.figure-caption {font-size:8pt;line-height:1.1;text-align:center;margin:3px 0 7px}
</style>""",
    )
    markup, count = re.subn(
        r'(<p><img alt="([^"]*)"[^>]*></p>)',
        lambda m: m[1] + f'<p class="figure-caption">{m[2]}</p>',
        markup,
    )
    assert count == 3
    html.write_text(markup)
    document = HELPER.Document(output / (NAME + ".docx"))
    document.core_properties.title = "APF3 - Credify | " + STATUS
    document.core_properties.subject = STATUS
    for section in document.sections:
        for p in section.footer.paragraphs:
            p.text = STATUS
    appendix = False
    for child in document.element.body:
        if child.tag.endswith("}p"):
            p = Paragraph(child, document._body)
            if p.text.startswith("Anexo A."):
                appendix = True
            if appendix:
                p.paragraph_format.space_after = HELPER.Pt(4)
                p.paragraph_format.line_spacing = 1.0
                if p.style.name == "Normal":
                    for run in p.runs:
                        run.font.size = HELPER.Pt(9)
        elif appendix and child.tag.endswith("}tbl"):
            for row in Table(child, document._body).rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        p.paragraph_format.space_after = HELPER.Pt(3)
                        p.paragraph_format.line_spacing = 1.0
                        for run in p.runs:
                            run.font.size = HELPER.Pt(7.5)
    document.save(output / (NAME + ".docx"))
    physical = render(output, text) if do_render else "not rendered; run with --render"
    after = {str(p): digest(p) for p in ORIGINAL.rglob("*") if p.is_file()}
    assert before == after, "Original package changed during generation"
    assert all(digest(Path(p)) == sha for p, sha in sources.items())
    links = re.findall(r"(?<!!)\[[^\]]+\]\((\.\./[^)]+)\)", text)
    missing = sorted({link for link in links if not (output / link).exists()})
    assert not missing, missing
    validation = {
        **result,
        "physical_render": physical,
        "metric_cells_checked_against_json": 224,
        "human_review": "pending",
        "original_word_tables": original_check["word_tables"],
        "additional_word_tables": result["word_tables"] - original_check["word_tables"],
        "new_training": False,
        "new_predictions": False,
        "new_tuning": False,
        "original_package_unchanged": True,
        "original_package_sha256": before,
        "source_sha256": sources,
        "reproduction": original_check["reproduction"],
        "word_physical_pagination": "not verified in native Word; counts apply to Playwright PDF",
        "delivery_relative_links_missing": missing,
        "repository_references_not_delivery_links": source_refs,
        "delivered_mvp_zip": {
            "path": "../laboratorio/codigo_fuente_MVP_V4.zip",
            "sha256": digest(code_zip),
            "entry_count": len(entries),
            "file_count": len(zip_entries),
            "crc_passed": True,
            "referenced_entries": zipped_refs,
        },
        "latency_evidence": {
            "status": bench["status"],
            "warm_service_calls": bench["warm_service_calls"],
            "sample_count": len(bench["samples_ms"]),
            "bundle_files_checked": len(bench["bundle_sha256"]),
            "source_sha256": digest(root / "anexos/integracion/latencia-v4.json"),
            "final_inference": False,
            "bundle_validation_cold_ms": bench["bundle_validation_cold_ms"],
            "model_load_and_first_prediction_ms": bench[
                "model_load_and_first_prediction_ms"
            ],
            "warm_service_ms": bench["warm_service_ms"],
            "peak_process_rss_kib": bench["peak_process_rss_kib"],
        },
        "unmet": [
            "applied human review and rehearsal",
            "teacher access",
        ],
        "declared_documentation_limits": [
            "prior history incomplete; available literal prompts annexed; no reconstruction or full-conversation requirement claimed",
        ],
        "future_operational_conditions_not_academic_delivery_blockers": [
            "business approval and measured baseline/costs",
            "real pilot and legal operational closure",
        ],
    }
    write_json(output / "verificacion-informe-entrega.json", validation)
    owned = [output / (NAME + ext) for ext in (".md", ".html", ".docx")]
    if do_render:
        owned.append(output / (NAME + ".pdf"))
    owned += list(figures.iterdir()) + [output / "verificacion-informe-entrega.json"]
    write_json(
        output / "manifest-informe-entrega.json",
        {
            "sources": sources,
            "files": {str(p.relative_to(output)): digest(p) for p in owned},
            "human_review": "pending",
            "original_package_modified": False,
        },
    )
    print(
        json.dumps(
            {
                **result,
                "physical_render": physical
                if not isinstance(physical, dict)
                else {k: v for k, v in physical.items() if k != "sections"},
                "missing_links": missing,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    generate(args.root, args.render)
