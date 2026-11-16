"""Standalone delivery deck/notes export from saved evidence, with offline layout QA.

Uses only parse_notes, documents and export_slides from shared helpers; never calls
an earlier generator, imports the ML runtime, loads Joblib or executes inference.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from pptx import Presentation
from pypdf import PdfReader

REPO = Path(__file__).resolve().parents[1]
ROOT = Path("/Users/tamaraalison/Downloads/APF3_Grupo2_Entrega_V4")
ORIGINAL = ROOT.with_name("APF3_Grupo2_Alineado_V4")
SOURCE = REPO / "docs/APF3_Guion_Entrega_V4.md"
NAME = "APF3_TD_Grupo2_ML_Innovacion"
GUIDE = "APF3_Grupo2_Guion_12min"
TEAL, COPPER, MUTED = "236F69", "A85632", "526572"
STATUS = "Datos simulados / Roles propuestos / Revision humana pendiente"
PLAYWRIGHT = "/var/folders/sx/_6ljw37n2_j9hk2f_vtqplj40000gn/T/opencode/apf3-render/node_modules/playwright/index.mjs"


def module(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).with_name(filename)
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(folder):
    return {str(p): digest(p) for p in sorted(folder.rglob("*")) if p.is_file()}


def normalize(value):
    return re.sub(r"\W+", "", value).lower()


# Both HTML variants are rendered without network access. DOM bounds include text
# ranges, not just element boxes, so clipped lines and overflowing table cells fail.
BROWSER = r"""
import {readFile} from 'node:fs/promises';
const {chromium} = await import(process.env.PLAYWRIGHT_MODULE_PATH);
const browser = await chromium.launch();
try {
  const [input, output, kind, views] = process.argv.slice(1);
  const page = await browser.newPage({viewport:{width:1280,height:1000},serviceWorkers:'block'});
  const requests = [];
  await page.route('**/*', r => {requests.push(r.request().url());return r.abort();});
  let markup = await readFile(input,'utf8');
  if (kind !== 'deck') {
    const {pathToFileURL} = await import('node:url');
    markup = markup.replace('<head>', `<head><base href="${pathToFileURL(input).href}">`);
  }
  await page.setContent(markup);
  await page.emulateMedia({media:'print'});
  await page.evaluate(() => document.fonts.ready);
  await page.locator('img').evaluateAll(imgs => Promise.all(imgs.map(i => i.decode())));
  const sections = await page.locator(kind === 'deck' ? '.slide' : '.page').evaluateAll((sections, kind) => sections.map(s => {
    const box = s.getBoundingClientRect();
    const errors = [];
    const candidates = kind === 'deck' ? s.querySelectorAll('.txt,.tbl .tr>div') : s.querySelectorAll('p,h1,h2,table,pre,li');
    for (const e of candidates) {
      const r = e.getBoundingClientRect();
      if(r.left < box.left-1 || r.right > box.right+1 || e.scrollWidth > e.clientWidth+1 ||
         (kind === 'deck' && (r.top < box.top-1 || r.bottom > box.bottom+1 || e.scrollHeight > e.clientHeight+1)))
        errors.push({type:'box',text:e.textContent.slice(0,100)});
      const walker = document.createTreeWalker(e,NodeFilter.SHOW_TEXT);
      let node;
      while ((node=walker.nextNode())) {
        if(!node.textContent.trim()) continue;
        const range=document.createRange(); range.selectNodeContents(node);
        for(const t of range.getClientRects()) {
          // Font ascent can extend above its line box without clipping (overflow is visible).
          if(t.left < r.left-1 || t.right > r.right+1 || (kind === 'deck' && (t.top < box.top-1 || t.bottom > r.bottom+1)))
            errors.push({type:'text',text:node.textContent.slice(0,100),box:{x:r.x,y:r.y,w:r.width,h:r.height},range:{x:t.x,y:t.y,w:t.width,h:t.height}});
        }
      }
    }
    return {title:s.querySelector('h1,h2')?.textContent, height_px:Math.ceil(box.height),overflow:errors};
  }),kind);
  const maxHeight = kind === 'deck' ? 720 : 259*96/25.4;
  if(requests.length || sections.some(s=>s.overflow.length || s.height_px>maxHeight+1))
    throw Error(JSON.stringify({requests,maxHeight,sections}));
  if(kind === 'deck') {
    for(let i=0;i<sections.length;i++)
      await page.locator('.slide').nth(i).screenshot({path:`${views}/${String(i+1).padStart(2,'0')}.png`});
  }
  await page.pdf({path:output,preferCSSPageSize:true,printBackground:true,
    displayHeaderFooter:kind !== 'deck',headerTemplate:'<div></div>',
    footerTemplate:'<div style="font:8px Arial;width:100%;text-align:center">Guion V4 entrega | Revision humana pendiente | <span class="pageNumber"></span> / <span class="totalPages"></span></div>'});
  console.log(JSON.stringify({offline:true,external_requests:requests,sections,overflow:false}));
} finally {await browser.close();}
"""


def generate(root, source, playwright_module):
    notes_helper = module("delivery_parse", "generate-apf3-defense.py")
    documents = module("delivery_documents", "generate-apf3-report.py")
    renderer = module("delivery_renderer", "slide-renderer.py")
    protected = [ORIGINAL, root / "experimento", root / "informe", root / "anexos"]
    before = {str(p): snapshot(p) for p in protected}
    sources = {}

    def read(path):
        sources[str(path.resolve())] = digest(path)
        return path.read_text(encoding="utf-8")

    def load(relative):
        return json.loads(read(root / relative))

    for path in (
        Path(__file__),
        Path(notes_helper.__file__),
        Path(documents.__file__),
        Path(renderer.__file__),
        REPO / "docs/APF3_Guion_Sustentacion_V4.md",
        Path(__file__).with_name("generate-aligned-v4-defense.py"),
    ):
        read(path)
    text = read(source)
    notes = notes_helper.parse_notes(text)
    report = load("experimento/aligned_v4_report.json")
    selection = load("experimento/frozen_selection.json")
    verification = load("informe/verificacion-informe-entrega.json")
    report_manifest = load("informe/manifest-informe-entrega.json")
    assert sources[
        str((root / "informe/verificacion-informe-entrega.json").resolve())
    ] == report_manifest["files"]["verificacion-informe-entrega.json"]
    report_text = read(root / "informe" / (NAME + ".md"))
    quality = load("anexos/datos/calidad-dev-v4.json")
    stack = load("anexos/integracion/evidence-stack-v4.json")
    cli = load("anexos/integracion/prueba-cli-v4.json")
    latency = load("anexos/integracion/latencia-v4.json")
    wrapper = root / (NAME + ".py")
    read(wrapper)
    reproduction = load("verificacion-reproduccion.json")
    read(root / "estado-artefactos.json")
    entry = load("experimento/illustrative_input.json")
    illustration = load("experimento/illustrative_output.json")
    assert report["selection"] == selection
    assert selection["global_winner"]["family"] == "svm"
    assert reproduction["passed"] and stack["status"] == "passed"
    assert verification["physical_render"]["body_pages"] == 15
    assert verification["physical_render"]["pdf_total_pages"] == 48
    assert not verification["physical_render"]["overflow"]
    assert illustration["known_label"] is None and not illustration["business_approval"]
    assert cli["status"] == latency["status"] == "passed"
    assert cli["entrypoint_sha256"] == digest(wrapper)
    assert cli["expected_output_sha256"] == digest(
        root / "experimento/illustrative_output.json"
    )
    for evidence in (cli["result"], latency):
        assert evidence["probability"] == illustration["probability"]
        assert evidence["known_label"] is None and not evidence["business_approval"]
    assert not cli["new_training"] and not cli["final_inference"]
    assert not latency["new_training"] and not latency["final_inference"]
    assert latency["warm_service_calls"] == 30
    assert round(latency["warm_service_ms"]["median"], 2) == 1.90
    assert round(latency["warm_service_ms"]["p95_nearest_rank"], 2) == 2.23
    assert len(quality["coherence_criteria"]) == 7
    assert len(entry["features"]) == 11
    for filename, counts in [
        ("desarrollo.csv", [559, 552, 7]),
        ("final.csv", [260, 259, 1]),
    ]:
        assert [
            quality["csv"][filename][k] for k in ("study", "known", "unknown")
        ] == counts
    assert "8/13/21" in report_text
    models = report["models"]
    coef = models["svm"]["interpretation"]["standardized_coefficients"]
    assert round(coef["paid_late"], 5) == 0.77699
    assert round(coef["punctuality_rate"], 5) == -0.28758
    questions = text.split("# Preguntas difíciles y respuestas breves", 1)[1].split(
        "# Lista de revisión humana pendiente", 1
    )[0]
    qa = re.findall(
        r"(?m)^\*\*¿.*?(?=\n\n\*\*¿|\Z)", questions.strip(), flags=re.DOTALL
    )
    assert len(qa) == 18
    words = sum(len(n["spoken"].split()) for n in notes)
    assert words == 1384
    output = root / "sustentacion"
    output.mkdir(exist_ok=True)
    (output / "vistas").mkdir(exist_ok=True)
    deck = []

    def slide(dark=False):
        item = {**notes[len(deck)], "dark": dark, "elements": []}
        deck.append(item)
        return item

    def txt(item, value, x=0.7, y=1.85, w=11.9, h=0.65, size=23, **style):
        item["elements"].append(
            dict(kind="text", text=value, x=x, y=y, w=w, h=h, size=size, **style)
        )

    def table(item, headers, rows, y, widths, size=18, rh=0.63):
        item["elements"].append(
            {
                "kind": "table",
                "headers": headers,
                "rows": rows,
                "x": 0.65,
                "y": y,
                "w": sum(widths),
                "h": rh * (len(rows) + 1),
                "widths": widths,
                "row_height": rh,
                "size": size,
            }
        )

    def image(item, path, x, y, w, h):
        sources[str(path.resolve())] = digest(path)
        item["elements"].append(
            {"kind": "image", "path": str(path), "x": x, "y": y, "w": w, "h": h}
        )

    def num(value):
        return f"{value:.5f}".replace(".", ",")

    item = slide(True)
    txt(
        item,
        "Fiado a un dia\nDel registro a la revision",
        y=1.15,
        h=1.6,
        size=38,
        bold=True,
    )
    txt(item, "Cerveceria Baylon / Credify / V4 entrega", y=3, size=25)
    txt(item, "APF1: problema  >  APF2: MVP  >  APF3: evidencia ML", y=3.8, size=21)
    team = text.split("| Integrante |", 1)[1].split("\n\n", 1)[0].splitlines()[2:]
    txt(
        item,
        "\n".join(" / ".join(line.strip("|").split("|")[:2]).strip() for line in team),
        y=4.85,
        w=9,
        h=1.5,
        size=16,
    )
    txt(
        item,
        "Ficticio\nRevision humana\nNo produccion",
        x=9.5,
        y=4.85,
        w=3.1,
        h=1.5,
        size=21,
        color="E3AA7A",
    )

    item = slide()
    txt(item, "1 fiado = 1 fila", size=34, bold=True, color=TEAL)
    txt(
        item,
        "late_payment: 1 atraso / 0 puntual\nVence al dia siguiente; gracia no cambia etiqueta.",
        y=2.9,
        h=1.2,
        size=26,
    )
    txt(
        item,
        "5 % referencial = perdida mensual / ventas",
        y=4.65,
        size=27,
        bold=True,
        color=COPPER,
    )
    txt(
        item,
        "No es prevalencia, probabilidad ni meta conseguida.\nSolo informacion previa al otorgamiento; alerta no aprueba.",
        y=5.7,
        h=1.05,
        size=22,
    )

    item = slide()
    rows = []
    for label, audit in [
        *[(f"DEV D{i + 1}", a) for i, a in enumerate(report["development"]["audits"])],
        ("FINAL", report["final"]["audit"]),
    ]:
        labels = audit["study_label_counts"]
        rows.append(
            [
                label,
                audit["clients"],
                audit["study_loans"],
                f"{labels['0']} / {labels['1']}",
                labels["None"],
                audit["warmup_loans"],
            ]
        )
    table(
        item,
        ["Mundo", "Clientes", "Estudio", "Clases 0 / 1", "Sin label", "Warmup"],
        rows,
        1.9,
        [1.8, 1.6, 1.6, 2.5, 1.8, 2.7],
    )
    txt(
        item,
        "DEV 559 / 552 conocidos / 7 desconocidos\nFINAL 260 / 259 conocidos / 1 desconocido",
        y=4.85,
        h=1.15,
        size=28,
        bold=True,
        color=TEAL,
    )
    txt(
        item,
        "Cero filas reales. Historias alternativas, no volumen empresarial sumado.\nWarmup excluido; desconocidos nunca se convierten en puntuales.",
        y=6.2,
        h=0.7,
        size=18,
    )

    item = slide()
    txt(
        item,
        "Fuente aproximada: atraso 8/45; abonos 10/48. DEV: 484 puntuales + 68 atrasos.",
        y=1.7,
        h=0.5,
        size=20,
        color=TEAL,
        bold=True,
    )
    image(item, root / "anexos/datos/eda_relaciones_entrega.png", 0.7, 2.35, 11.9, 3.8)
    txt(
        item,
        "Bandas fijas de antiguedad: medianas 8 / 13 / 21 ventas de credito.\nExposicion 551/1/0: sin tendencia general. Asociaciones sinteticas, no causalidad.",
        y=6.3,
        h=0.65,
        size=17,
    )

    item = slide()
    table(
        item,
        ["Modelos", "Pipeline dentro de cada ajuste", "Referencias"],
        [
            ["Arbol + SVM lineal", "Mediana + StandardScaler", "2 Dummy"],
            ["12 + 6 configuraciones", "11 predictores previos", "Mayoria / positivo"],
        ],
        1.9,
        [3.5, 5, 3.5],
        size=18,
        rh=0.7,
    )
    txt(
        item,
        "3 folds externos por cliente; SVM: 3 internos agrupados",
        y=4.4,
        size=26,
        bold=True,
        color=TEAL,
    )
    txt(
        item,
        "Por externo: 368 filas / 16 clientes entrenan; 184 / 8 validan.\n18 configuraciones x 7 umbrales. Fallback por clases, no por score.",
        y=5.3,
        h=1,
        size=21,
    )
    txt(
        item,
        "OOF reutilizado para seleccionar: optimismo. No evaluacion anidada independiente. D2: 27 atrasos.",
        y=6.6,
        h=0.35,
        size=16,
        color=COPPER,
    )

    item = slide(True)
    txt(
        item,
        "Umbral > ordenar score > hasta 5 / replica / fecha",
        y=1.9,
        size=27,
        color="E3AA7A",
        bold=True,
    )
    txt(item, "F2 = 5TP / (5TP + 4FN + FP)", y=2.9, size=32, bold=True)
    for x, family, label in [(0.7, "svm", "SVM seleccionada"), (7, "tree", "Arbol")]:
        txt(
            item,
            num(models[family]["review_policy"]["oof"]["metrics"]["f2"]),
            x=x,
            y=4.15,
            w=5.2,
            h=0.8,
            size=44,
            color="E3AA7A",
            bold=True,
        )
        txt(item, label + " / F2 OOF politica", x=x, y=5.2, w=5.5, size=22)
    txt(
        item,
        "C=1 / balanced / umbral 0,10. Sin piso de precision.\nDecision congelada antes de FINAL; no cambiar por el mejor arbol final.",
        y=6.25,
        h=0.65,
        size=18,
    )

    item = slide()
    families = [
        ("svm", "SVM elegida"),
        ("tree", "Arbol"),
        ("most_frequent", "Mayoria"),
        ("constant_1", "Positivo"),
    ]
    table(
        item,
        ["RAW FINAL", "Precision", "Recall", "F1", "F2", "Accuracy"],
        [
            [
                label,
                *[
                    num(models[f]["final"][k])
                    for k in ("precision", "recall", "f1", "f2", "accuracy")
                ],
            ]
            for f, label in families
        ],
        1.8,
        [2.7, 1.9, 1.85, 1.85, 1.85, 1.85],
        size=17,
        rh=0.58,
    )
    txt(
        item,
        "POLITICA FINAL, despues del tope / 259 etiquetas conocidas",
        y=4.95,
        size=20,
        bold=True,
        color=TEAL,
    )
    for index, (family, label) in enumerate(families):
        policy = models[family]["review_policy"]["final"]
        x = 0.7 + index * 3.03
        txt(
            item,
            label
            + f"\nF2 {num(policy['metrics']['f2'])}\nR {num(policy['metrics']['recall'])}",
            x=x,
            y=5.65,
            w=2.9,
            h=1.1,
            size=18,
            bold=True,
        )
    txt(
        item,
        "Positivo bruto no es positivo limitado; SVM y arbol no pierden alertas por el tope.",
        y=6.85,
        h=0.25,
        size=13,
    )

    item = slide()
    image(item, root / "informe/figuras/matriz_v4.png", 0.65, 1.95, 7.05, 3.14)
    error = next(
        e for e in models["svm"]["error_cases"] if e["loan_id"] == "AL4-T-L00045"
    )
    assert error["actual"] == 1 and error["predicted"] == 0
    txt(
        item,
        f"Caso guardado\n{error['loan_id']}\nScore {error['probability']:.5f} < 0,10\nReal 1 / predicho 0",
        x=8,
        y=2.05,
        w=4.6,
        h=2,
        size=21,
    )
    txt(
        item,
        f"paid_late {coef['paid_late']:+.5f}    /    punctuality_rate {coef['punctuality_rate']:+.5f}",
        y=5.45,
        h=0.6,
        size=23,
        bold=True,
        color=TEAL,
    )
    txt(
        item,
        "Pesos del margen estandarizado, no efectos causales ni cambios de probabilidad.\nHistorial puntual no garantiza el siguiente pago. No reinferir ni reajustar FINAL.",
        y=6.25,
        h=0.65,
        size=18,
    )

    item = slide()
    fields = list(entry["features"].items())
    for start, x in [(0, 0.7), (6, 7)]:
        txt(
            item,
            "\n".join(f"{k}: {v}" for k, v in fields[start : start + 6]),
            x=x,
            y=1.85,
            w=5.65,
            h=2.55,
            size=18,
            mono=True,
        )
    txt(
        item,
        f"Respaldo: score {illustration['probability']:.10f} > 0,10 / clase 1",
        y=4.7,
        size=27,
        bold=True,
        color=TEAL,
    )
    txt(
        item,
        "known_label: null / Ficticio, sin prueba de acierto ni aprobacion.",
        y=5.5,
        size=22,
    )
    txt(
        item,
        "20 s hablados + 50 s CLI offline. Comando completo en el guion.\nFallo: declararlo; mostrar illustrative_output.json como guardado.",
        y=6.3,
        h=0.65,
        size=19,
    )

    item = slide()
    policies = [models[f]["review_policy"]["final"] for f in ("svm", "constant_1")]
    table(
        item,
        ["Politica FINAL", "Revisiones", "Conocidas + ?", "FN"],
        [
            [
                label,
                p["reviews"],
                f"{p['reviews_known']} + {p['reviews_unknown']}",
                p["metrics"]["confusion_matrix"][1][0],
            ]
            for label, p in zip(("SVM", "Todo limitado"), policies, strict=True)
        ],
        1.9,
        [4.1, 2.5, 3.5, 1.9],
        size=21,
        rh=0.7,
    )
    delta = policies[1]["reviews"] - policies[0]["reviews"]
    txt(
        item,
        f"{delta} x 2 = {delta * 2} minutos hipoteticos / tres FN adicionales",
        y=4.35,
        size=27,
        bold=True,
        color=TEAL,
    )
    txt(
        item,
        "Meta PROPUESTA ahora, no aprobada ni criterio previo de seleccion:\nminutos DESPUES < ANTES; maximo 5/dia; reportar costos FN/FP.",
        y=5.25,
        h=1,
        size=22,
    )
    txt(
        item,
        "Piloto futuro autorizado y periodos comparables. Baseline, costos y utilidad pendientes.",
        y=6.65,
        h=0.35,
        size=17,
        color=COPPER,
    )

    item = slide()
    txt(
        item,
        "Web local V4 + API autenticada + CLI",
        y=1.9,
        size=31,
        bold=True,
        color=TEAL,
    )
    txt(
        item,
        "/laboratorio-academico/v4\n/api/v1/academic-ml/v4\nBundle confiable solo lectura; flag staging apagado por defecto.",
        y=2.9,
        h=1.6,
        size=22,
    )
    txt(
        item,
        "Stack Docker / Postgres / JWT / navegador: probado LOCALMENTE.\nNo produccion, no URL publica V4, no creacion de creditos.",
        y=4.85,
        h=1.05,
        size=23,
        bold=True,
    )
    txt(
        item,
        "Reproduccion guardada: 15 SHA / 12 brutas / 12 politicas / 5 estados exactos.\nBytes Joblib distintos. Hash no hace seguro un artefacto ajeno. Ensayo humano pendiente.",
        y=6.25,
        h=0.65,
        size=17,
    )

    item = slide()
    txt(
        item,
        "Ley N. 29733 / D.S. N. 016-2024-JUS",
        y=1.9,
        size=29,
        bold=True,
        color=TEAL,
    )
    txt(
        item,
        "Finalidad y base juridica; informacion; accesos y conservacion; ARCO.\nNo publicar ficha privada ni inventar consentimiento.",
        y=2.9,
        h=1.1,
        size=23,
    )
    txt(
        item,
        "Supuestos no medidos: poblacion, warmup, Beta, sigmas, estabilidad.\nVentas al contado no modeladas. Datos ficticios no certifican cumplimiento.",
        y=4.45,
        h=1.05,
        size=22,
    )
    txt(
        item,
        "Anexo IA: prompts disponibles; brecha del historial anterior.\nRevision individual y ensayo pendientes, sin actas o firmas inventadas.",
        y=6,
        h=0.85,
        size=22,
        color=COPPER,
    )

    item = slide(True)
    txt(
        item,
        "Alineacion parcial no es validacion real",
        y=1.95,
        h=0.8,
        size=35,
        bold=True,
        color="E3AA7A",
    )
    txt(
        item,
        "F2 supera referencias solo en simulacion.\n61 detectados / 114 falsas alertas / 4 omisiones.",
        y=3.15,
        h=1.2,
        size=28,
    )
    txt(
        item,
        "Fuente aproximada 8/45 = 17,78 % / FINAL 65/259 = 25,10 %.\nSin forzar tasas ni cambiar la seleccion SVM.",
        y=4.75,
        h=0.9,
        size=23,
    )
    txt(
        item,
        "Web local comprobada, no produccion. Revision, ensayo y costos pendientes.\nCaptura real solo autorizada. Preguntas fuera del cronometro.",
        y=6.1,
        h=0.85,
        size=21,
    )

    elapsed = 0
    for item in deck:
        start = elapsed
        elapsed += item["seconds"]
        color = "C8D6DF" if item["dark"] else MUTED
        txt(
            item,
            "UTP / GRUPO 2 / V4 ENTREGA",
            x=0.65,
            y=0.25,
            w=5,
            h=0.25,
            size=10,
            color=color,
            bold=True,
        )
        stamp = (
            f"{start // 60:02}:{start % 60:02} - {elapsed // 60:02}:{elapsed % 60:02}"
        )
        txt(
            item,
            f"{item['owner']} / {stamp} / {item['number']:02}/13",
            x=7.2,
            y=0.25,
            w=5.4,
            h=0.25,
            size=10,
            color=color,
            align="right",
        )
        if item["number"] != 1:
            txt(item, item["title"], x=0.65, y=0.8, w=12.05, h=0.8, size=28, bold=True)
        txt(item, STATUS, x=0.65, y=7.16, w=12, h=0.2, size=9, color=color)
    assert len(deck) == 13 and elapsed == 720
    renderer.export_slides(deck, output, name=NAME, version="V4 entrega")
    native = Presentation(output / (NAME + ".pptx"))
    assert len(native.slides) == 13
    native_checks = 0
    for item, slide in zip(deck, native.slides, strict=True):
        assert slide.notes_slide.notes_text_frame.text == item["notes"]
        assert len(slide.shapes) == len(item["elements"])
        for element, shape in zip(item["elements"], slide.shapes, strict=True):
            for key, actual in [
                ("x", shape.left),
                ("y", shape.top),
                ("w", shape.width),
                ("h", shape.height),
            ]:
                assert abs(actual / 914400 - element[key]) < 0.00001
            if element["kind"] == "text":
                assert shape.text == element["text"]
            elif element["kind"] == "table":
                assert [[c.text for c in row.cells] for row in shape.table.rows] == [
                    [str(v) for v in row]
                    for row in [element["headers"], *element["rows"]]
                ]
            elif element["kind"] == "image":
                assert hashlib.sha256(shape.image.blob).hexdigest() == digest(
                    Path(element["path"])
                )
            native_checks += 1

    # Eleven authentic sections; no fabricated pagination titles or extra slide.
    timeline, elapsed = [], 0
    for n in notes:
        end = elapsed + n["seconds"]
        timeline.append(
            [
                n["number"],
                n["owner"],
                f"{elapsed // 60:02}:{elapsed % 60:02} - {end // 60:02}:{end % 60:02}",
                n["seconds"],
            ]
        )
        elapsed = end
    pages = [
        "# Guion de entrega V4\n\n**Roles propuestos; revision humana y ensayo pendientes.**\n\n"
        + "| Integrante |"
        + text.split("| Integrante |", 1)[1].split("\n\n", 1)[0]
        + "\n\n"
        + documents.table(["Diap.", "Expositor", "Ventana", "Segundos"], timeline)
        + f"\n\n**Texto hablado:** {words} palabras. 720 segundos: 670 hablados y 50 de operacion; diapositiva 9, 20+50. Preguntas fuera.\n\n"
        + "**Preparacion tecnica, no acta:** informe final 15 paginas de cuerpo/48 totales; web/API V4 solo local. Demo principal CLI offline con wrapper raiz; prueba tecnica guardada passed, no demo humana. No requiere preparar web. Sin ML en esta exportacion. Fuentes y SHA-256 en plan-sustentacion-entrega.json."
    ]
    for start, end in [(0, 3), (3, 6), (6, 9), (9, 13)]:
        pages.append(
            f"# Intervenciones {start + 1} a {end}\n\n"
            + "\n\n".join(
                f"## {n['number']}. {n['title']}\n\n**Tiempo:** {n['seconds']} s / **Expositor propuesto:** {n['owner']}\n\n{n['spoken']}\n\n**Apoyo no hablado:** {n['first_action']}"
                for n in notes[start:end]
            )
        )
    for index in range(3):
        pages.append(
            f"# Preguntas dificiles {index + 1}/3\n\n**Fuera de los 720 segundos.**\n\n"
            + "\n\n".join(qa[index * 6 : (index + 1) * 6])
        )
    # Keep the full demo instructions, including exact input and null-labelled backup.
    demo_support = notes[8]["notes"].split("**Acción:**", 1)[1]
    pages.append(
        "# Demo CLI: preparacion y comando\n\n**Instrucciones, no acta humana.**\n\n**Acción:**"
        + demo_support.split(
            "**Acción:** mostrar `experimento/illustrative_output.json`", 1
        )[0]
    )
    pages.append(
        "# Demo CLI: respaldo y limites\n\n**Resultado previamente guardado, no recien ejecutado.**\n\n**Acción:** mostrar `experimento/illustrative_output.json`"
        + demo_support.split(
            "**Acción:** mostrar `experimento/illustrative_output.json`", 1
        )[1]
        + "\n\n**IA y trazabilidad:** Anexo H del informe conserva prompts disponibles. Historial anterior incompleto; no reconstruirlo. Reproduccion guardada: 15 SHA, 12 brutas, 12 politicas, cinco estados exactos; bytes Joblib distintos, tres timestamps y dos hashes derivados excluidos. No validacion independiente ni aprobacion."
    )
    review = text.split("# Lista de revisión humana pendiente", 1)[1].strip()
    pages.append(
        "# Revision humana pendiente\n\n" + re.sub(r"\n(?=- \[ \])", "\n\n", review)
    )
    compact = "\n\n<!-- PAGE -->\n\n".join(pages)
    (output / (GUIDE + ".md")).write_text(compact, encoding="utf-8")
    (output / "Guion_completo_con_indicaciones.md").write_text(text, encoding="utf-8")
    document_result = documents.documents(
        compact, output, name=GUIDE, expected_figures=0
    )
    html_path = output / (GUIDE + ".html")
    markup = html_path.read_text().replace(
        "APF3 - Credify - Borrador",
        "APF3 - Guion V4 entrega - Revision humana pendiente",
    )
    markup = markup.replace(
        "</style>",
        """
body{width:174mm;font:10pt/1.18 Arial,sans-serif}.page{display:flow-root}
p{margin:0 0 6px}h1{font-size:16pt;margin:0 0 10px}h2{font-size:11.5pt;margin:10px 0 6px}
th,td{padding:4px}.page:first-child h1{margin-top:0;font-size:17pt}
pre{margin:6px 0;padding:6px}pre code{font-size:8pt}
.page:nth-child(5){font-size:9.5pt;line-height:1.16}
</style>""",
    )
    html_path.write_text(markup, encoding="utf-8")
    doc = Document(output / (GUIDE + ".docx"))
    doc.core_properties.title = "APF3 Guion V4 entrega - Revision humana pendiente"
    doc.styles["Normal"].font.size = Pt(10)
    doc.styles["Normal"].paragraph_format.space_after = Pt(4)
    for section in doc.sections:
        section.footer.paragraphs[0].runs[0].text = STATUS + " | "
    # The shared document helper leaves Markdown links literal. Materialize only
    # this edition's evidence links as portable, relative DOCX hyperlinks.
    evidence_links = {}
    for paragraph in doc.paragraphs:
        for run in list(paragraph.runs):
            matches = list(re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", run.text))
            if not matches:
                continue
            cursor = 0
            for match in matches:
                label, target = match.groups()
                assert (output / target).resolve().is_file(), target
                evidence_links[target] = label
                for value, link in [
                    (run.text[cursor : match.start()], None),
                    (label, target),
                ]:
                    node = OxmlElement("w:r")
                    content = OxmlElement("w:t")
                    content.set(qn("xml:space"), "preserve")
                    content.text = value
                    node.append(content)
                    if link:
                        hyperlink = OxmlElement("w:hyperlink")
                        hyperlink.set(
                            qn("r:id"),
                            doc.part.relate_to(
                                link, RELATIONSHIP_TYPE.HYPERLINK, is_external=True
                            ),
                        )
                        hyperlink.append(node)
                        node = hyperlink
                    run._r.addprevious(node)
                cursor = match.end()
            run.text = run.text[cursor:]
    doc.save(output / (GUIDE + ".docx"))

    renders = {}
    env = dict(os.environ, PLAYWRIGHT_MODULE_PATH=playwright_module)
    for name, kind in [(NAME, "deck"), (GUIDE, "guide")]:
        process = subprocess.run(
            [
                "node",
                "--input-type=module",
                "-e",
                BROWSER,
                str(output / (name + ".html")),
                str(output / (name + ".pdf")),
                kind,
                str(output / "vistas"),
            ],
            check=False,
            env=env,
            text=True,
            capture_output=True,
        )
        if process.returncode:
            raise RuntimeError(process.stderr)
        audit = json.loads(process.stdout)
        pdf = PdfReader(output / (name + ".pdf"))
        assert (
            len(pdf.pages)
            == (13 if kind == "deck" else len(pages))
            == len(audit["sections"])
        )
        for index, page in enumerate(pdf.pages):
            width, height = (960, 540) if kind == "deck" else (595.28, 841.89)
            assert abs(float(page.mediabox.width) - width) < 1
            assert abs(float(page.mediabox.height) - height) < 1
            extracted = normalize(page.extract_text())
            if kind == "deck":
                for element in deck[index]["elements"]:
                    if element["kind"] == "text":
                        assert normalize(element["text"]) in extracted, (
                            index + 1,
                            element["text"],
                        )
                    elif element["kind"] == "table":
                        assert all(
                            normalize(str(v)) in extracted
                            for row in [element["headers"], *element["rows"]]
                            for v in row
                        )
            else:
                assert normalize(audit["sections"][index]["title"]) in extracted
        if kind == "guide":
            pdf_links = {
                str(annotation.get_object().get("/A", {}).get("/URI", ""))
                for page in pdf.pages
                for annotation in page.get("/Annots", [])
            }
            assert all(
                (output / target).resolve().as_uri() in pdf_links
                for target in evidence_links
            ), pdf_links
            pdf_text = normalize("\n".join(p.extract_text() for p in pdf.pages))
            assert all(
                normalize(p) in pdf_text
                for n in notes
                for p in n["spoken"].split("\n\n")
            )
            assert all(normalize(q) in pdf_text for q in qa)
            for required in [
                "known_label",
                "null",
                "demo_salida_NUEVA.json",
                "Python 3.12.14",
                "illustrative_output.json",
            ]:
                assert normalize(required) in pdf_text
        renders[kind] = {**audit, "pdf_pages": len(pdf.pages), "pdf_text_checked": True}

    assert all(digest(Path(path)) == sha for path, sha in sources.items()), (
        "Source changed during export"
    )
    assert before == {str(p): snapshot(p) for p in protected}, (
        "Protected evidence changed during export"
    )
    readiness = {
        "root_wrapper_exists": wrapper.is_file(),
        "environment_required": "Python 3.12.14 + pinned ML dependencies, or existing compatible Docker image",
        "ml_environment_executed_by_this_export": False,
        "human_demo": "pending",
        "human_rehearsal": "pending",
        "primary_demo": "offline CLI via relative root wrapper; no web preparation or deployment required",
        "technical_cli_saved_evidence": {
            "path": "anexos/integracion/prueba-cli-v4.json",
            "status": cli["status"],
            "probability": cli["result"]["probability"],
            "container_start_and_cli_seconds": cli["container_start_and_cli_seconds"],
            "scope": cli["timing_scope"],
            "illustrative_examples": 1,
            "human_demo": cli["human_demo"],
        },
    }
    if wrapper.is_file():
        readiness["root_wrapper_sha256"] = digest(wrapper)
    owned = [output / (NAME + ext) for ext in (".pptx", ".html", ".pdf")]
    owned += [output / (GUIDE + ext) for ext in (".md", ".docx", ".html", ".pdf")]
    owned += [
        output / "Guion_completo_con_indicaciones.md",
        *sorted((output / "vistas").glob("*.png")),
    ]
    plan = {
        "edition": "delivery-v4",
        "generated_utc": datetime.now(UTC).isoformat(),
        "slides": 13,
        "planned_seconds": 720,
        "spoken_planned_seconds": 670,
        "slide_9": {"spoken_seconds": 20, "live_seconds": 50},
        "spoken_words": words,
        "word_target_editorial_not_assignment_requirement": [1250, 1450],
        "word_target_met": 1250 <= words <= 1450,
        "question_count": len(qa),
        "planned_speaker_seconds": {
            owner: sum(n["seconds"] for n in notes if n["owner"] == owner)
            for owner in dict.fromkeys(n["owner"] for n in notes)
        },
        "slides_data": [
            {
                k: n[k]
                for k in ("number", "title", "owner", "seconds", "spoken", "notes")
            }
            | {"spoken_words": len(n["spoken"].split())}
            for n in deck
        ],
        "human_review": "pending",
        "human_rehearsal": "pending",
        "roles": "proposed; no contribution record",
        "technical_preparation_only": True,
        "demo_readiness": readiness,
        "web_scope": "saved local stack evidence only; not public V4 or production",
        "integration_latency": {
            "source": "anexos/integracion/latencia-v4.json",
            "status": latency["status"],
            "scope": latency["scope"],
            "warm_service_calls": latency["warm_service_calls"],
            "warm_service_ms": latency["warm_service_ms"],
            "not_measured": latency["not_measured"],
            "sla_claimed": False,
            "new_measurement_by_this_export": False,
        },
        "selection_cache": {
            "winner": selection["global_winner"],
            "new_selection": False,
        },
        "metrics_cache": {
            f: {
                "raw_final": models[f]["final"],
                "policy_final": {
                    k: v
                    for k, v in models[f]["review_policy"]["final"].items()
                    if k != "daily"
                },
            }
            for f, _ in families
        },
        "metric_cells_checked": 20,
        "native_elements_checked": native_checks,
        "interpretation": {
            "standardized_coefficients": coef,
            "causal_or_probability_effects": False,
        },
        "eda_figure": "anexos/datos/eda_relaciones_entrega.png",
        "exposure_trend_supported": False,
        "report_pages": {"body": 15, "total": 48},
        "eda_coherence_criteria": len(quality["coherence_criteria"]),
        "report_rematerialized": False,
        "business_goal": "PROPOSED retrospectively now; minutes AFTER < BEFORE, <=5/day, FN/FP costs reported; not approved or used for selection",
        "ai_history": "available prompts only; earlier history gap; human review pending",
        "new_training": False,
        "new_predictions": False,
        "new_tuning": False,
        "original_package_unchanged": True,
        "protected_evidence_unchanged": True,
        "source_sha256": sources,
        "protected_sha256": before,
        "output_sha256": {str(p.relative_to(output)): digest(p) for p in owned},
        "documents": document_result,
        "evidence_links": {
            "relative_targets": list(evidence_links),
            "docx_hyperlinks": True,
            "pdf_links_checked": True,
        },
        "render": renders,
        "native_render_caveat": "PPTX content/geometry/notes checked; Microsoft PowerPoint and Word physical rendering not executed",
    }
    (output / "plan-sustentacion-entrega.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "slides": 13,
                "seconds": 720,
                "spoken_words": words,
                "questions": len(qa),
                "pdf_pages": {k: v["pdf_pages"] for k, v in renders.items()},
                "overflow": False,
                "demo_readiness": readiness,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, nargs="?", default=ROOT)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument(
        "--playwright-module",
        default=os.environ.get("PLAYWRIGHT_MODULE_PATH", PLAYWRIGHT),
    )
    args = parser.parse_args()
    generate(args.root.resolve(), args.source.resolve(), args.playwright_module)
