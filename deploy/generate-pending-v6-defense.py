"""Export V6 defense from frozen JSON only, without importing the ML runtime."""

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
import re
import statistics
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
from docx import Document
from docx.shared import Pt
from pptx import Presentation
from pypdf import PdfReader

REPO = Path(__file__).resolve().parents[1]
ROOT = Path("/Users/tamaraalison/Downloads/APF3_Grupo2_Entrega_V6")
SOURCE = REPO / "docs/APF3_Guion_Sustentacion_V6.md"
NAME = "APF3_TD_Grupo2_ML_Innovacion"
GUIDE = "APF3_Grupo2_Guion_12min"
STATUS = "Datos simulados / Roles propuestos / Revision humana pendiente"
PLAYWRIGHT = "/var/folders/sx/_6ljw37n2_j9hk2f_vtqplj40000gn/T/opencode/apf3-render/node_modules/playwright/index.mjs"

BROWSER = r"""
import {readFile} from 'node:fs/promises';
const {chromium} = await import(process.env.PLAYWRIGHT_MODULE_PATH);
const browser = await chromium.launch();
try {
 const [input,output,kind,views] = process.argv.slice(1);
 const page = await browser.newPage({viewport:{width:1280,height:1000},serviceWorkers:'block'});
 const requests=[];
 await page.route('**/*',r=>{requests.push(r.request().url());return r.abort();});
 await page.setContent(await readFile(input,'utf8'));
 await page.emulateMedia({media:'print'});
 await page.evaluate(()=>document.fonts.ready);
 await page.locator('img').evaluateAll(xs=>Promise.all(xs.map(x=>x.decode())));
 const sections=await page.locator(kind==='deck'?'.slide':'.page').evaluateAll((ss,kind)=>ss.map(s=>{
  const b=s.getBoundingClientRect(), errors=[];
  for(const e of s.querySelectorAll(kind==='deck'?'.shape,.tbl .tr>div':'p,h1,h2,table,pre,li')) {
   const r=e.getBoundingClientRect();
   if(r.left<b.left-1 || r.right>b.right+1 || r.top<b.top-1 || r.bottom>b.bottom+1 ||
      e.scrollWidth>e.clientWidth+1 || (kind==='deck' && e.scrollHeight>e.clientHeight+1))
     errors.push({type:'element',text:e.textContent.slice(0,80)});
   if(e.classList.contains('tbl')) continue;
   const walker=document.createTreeWalker(e,NodeFilter.SHOW_TEXT); let node;
   while((node=walker.nextNode())) {
    if(!node.textContent.trim()) continue;
    const range=document.createRange();range.selectNodeContents(node);
    for(const t of range.getClientRects())
     if(t.left<r.left-1 || t.right>r.right+1 || t.top<b.top-1 || t.bottom>r.bottom+1)
      errors.push({type:'text',text:node.textContent.slice(0,80)});
   }
  }
  return {title:s.querySelector('h1,h2')?.textContent,height_px:Math.ceil(b.height),errors};
 }),kind);
 const maxHeight=kind==='deck'?720:259*96/25.4;
 if(requests.length || sections.some(s=>s.errors.length || s.height_px>maxHeight+1))
  throw Error(JSON.stringify({requests,sections,maxHeight}));
 if(kind==='deck') for(let i=0;i<sections.length;i++)
  await page.locator('.slide').nth(i).screenshot({path:`${views}/${String(i+1).padStart(2,'0')}.png`});
 await page.pdf({path:output,preferCSSPageSize:true,printBackground:true});
 console.log(JSON.stringify({offline:true,external_requests:requests,sections,text_overflow:0,element_bounds_errors:0}));
} finally {await browser.close();}
"""


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module(filename):
    spec = importlib.util.spec_from_file_location(filename, REPO / "deploy" / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def normalize(value):
    return re.sub(r"\W+", "", value).lower()


def generate(root, source, playwright_module):
    sources = {}

    def read(path):
        sources[str(path.resolve())] = digest(path)
        return path.read_text(encoding="utf-8")

    def load(relative):
        return json.loads(read(root / relative))

    read(Path(__file__))
    helpers = [
        module(p)
        for p in (
            "generate-apf3-defense.py",
            "generate-apf3-report.py",
            "slide-renderer.py",
        )
    ]
    for helper in helpers:
        read(Path(helper.__file__))
    parser, documents, renderer = helpers
    text = read(source)
    notes = parser.parse_notes(text)
    words = sum(len(n["spoken"].split()) for n in notes)
    assert 1250 <= words <= 1450, words
    questions = text.split("# Preguntas difíciles y respuestas breves", 1)[1].split(
        "# Lista de revisión humana pendiente", 1
    )[0]
    qa = re.findall(r"(?m)^\*\*¿.*?(?=\n\n\*\*¿|\Z)", questions.strip(), re.S)
    review = text.split("# Lista de revisión humana pendiente", 1)[1].strip()
    assert len(qa) == 18 and review.count("- [ ]") == 4
    report = load("experimento/pending_v6_report.json")
    summary = load("resumen-v6.json")
    reproduction = load("verificacion-reproduccion.json")
    selection = load("experimento/frozen_selection.json")
    entry = load("experimento/illustrative_input.json")
    illustration = load("experimento/illustrative_output.json")
    rows = load("experimento/development_rows.json")
    study = load("experimento/development_study_rows.json")
    final_rows = list(
        csv.DictReader(io.StringIO(read(root / "experimento/final_rows.csv")))
    )
    owner = load("experimento/owner_review.json")
    read(root / (NAME + ".py"))
    read(root / "requirements.txt")
    assert report["version"] == summary["version"] == "academic-owner-pending-v6"
    assert report["selection"] == selection
    winner = selection["global_winner"]
    assert all(winner[k] == v for k, v in summary["global_winner"].items())
    assert winner["family"] == "tree" and winner["threshold"] == 0.2
    assert winner["params"]["max_depth"] == 4
    assert winner["params"]["min_samples_leaf"] == 8
    assert winner["params"]["class_weight"] == "balanced"
    assert reproduction["passed"] is True
    assert reproduction["joblib_binary_equal"] is True
    checks = reproduction["checks"]
    for key, count in (
        ("exact_file_sha256", 47),
        ("raw", 12),
        ("policy", 12),
        ("learned_state", 5),
    ):
        assert len(checks[key]) == count and all(
            v is True for v in checks[key].values()
        )
    for filename in checks["exact_file_sha256"]:
        a, b = (root / folder / filename for folder in ("experimento", "reproduccion"))
        assert digest(a) == digest(b), filename
        sources[str(a.resolve())] = digest(a)
        sources[str(b.resolve())] = digest(b)
    for family, state in reproduction["artifact_serialization"].items():
        assert state["binary_equal"] is True
        for index, folder in enumerate(("experimento", "reproduccion")):
            path = root / folder / (family + ".joblib")
            sources[str(path.resolve())] = digest(path)
            assert digest(path) == state["binary_sha256"][index]
    models = report["models"]
    families = [
        ("tree", "Arbol elegido"),
        ("svm", "SVM"),
        ("most_frequent", "Mayoria"),
        ("constant_1", "Positivo"),
    ]
    for family, _ in families:
        model, cached = models[family], summary["models"][family]
        for split in ("train", "oof", "final"):
            assert model[split] == cached["raw"][split]
            replay = reproduction["results"]["models"][family]
            assert replay["raw"][split] == model[split]
            assert (
                replay["policy"][split]["metrics"]
                == model["review_policy"][split]["metrics"]
            )
            assert all(
                model["review_policy"][split][k] == v
                for k, v in cached["policy"][split].items()
            )
    assert models["tree"]["final"]["confusion_matrix"] == [[81, 162], [4, 29]]
    assert summary["baseline_comparison"]["final"]["proposal_pass"] is True
    assert len(rows) == 541 and len(study) == 545
    assert sum(r["late_payment"] for r in rows) == 87
    assert len({r["client_id"] for r in rows}) == 24
    assert len(final_rows) == 280
    assert len({r["client_id"] for r in final_rows}) == 12
    assert not {r["client_id"] for r in study} & {r["client_id"] for r in final_rows}
    assert len(entry["features"]) == 11
    assert illustration["features"] == entry["features"]
    assert illustration["probability"] == 0.7171978005286032
    assert illustration["known_label"] is None and illustration["predicted"] == 1
    assert not illustration["business_approval"] and illustration["distinctness_pass"]
    assert all(
        any(r[k] != entry["features"][k] for k in report["feature_names"])
        for r in study
    ), "Illustration must differ from every DEV vector"
    assert all(
        any(float(r[k]) != entry["features"][k] for k in report["feature_names"])
        for r in final_rows
    ), "Illustration must differ from every FINAL vector"
    assert (
        sum(
            owner["sample"][k]
            for k in (
                "fiados_reviewed",
                "rejections_reviewed",
                "weeks_reviewed",
                "assumptions_reviewed",
            )
        )
        == 23
    )
    for feature in summary["constant_features"]:
        assert all(r[feature] == 0 for r in rows)
    assert all(r["completed_sales"] == r["paid_credits"] for r in rows)

    output = root / "sustentacion"
    for folder in (output, output / "figuras", output / "vistas"):
        folder.mkdir(exist_ok=True)
    plt.switch_backend("Agg")
    history = []
    for label, group in (
        ("Sin atraso previo", [r for r in rows if r["paid_late"] == 0]),
        ("Con atraso previo", [r for r in rows if r["paid_late"] > 0]),
    ):
        late = sum(r["late_payment"] for r in group)
        history.append(
            dict(
                label=label,
                n=len(group),
                late=late,
                rate=late / len(group) if group else None,
            )
        )
    bands = []
    for low, high in ((30, 120), (120, 240), (240, None)):
        group = [
            r
            for r in rows
            if r["tenure_days"] >= low and (high is None or r["tenure_days"] < high)
        ]
        bands.append(
            dict(
                low=low,
                high_exclusive=high,
                n=len(group),
                median_sales=statistics.median(r["completed_sales"] for r in group)
                if group
                else None,
            )
        )
    fig, axes = plt.subplots(1, 2, figsize=(13, 3.8), layout="constrained")
    fig.patch.set_facecolor("#F6F3EB")
    axes[0].bar(
        [h["label"] for h in history],
        [100 * (h["rate"] or 0) for h in history],
        color=["#236F69", "#A85632"],
    )
    for index, h in enumerate(history):
        axes[0].text(
            index, 100 * (h["rate"] or 0) + 1, f"{h['late']}/{h['n']}", ha="center"
        )
    axes[0].set(
        title="Historial y atraso DEV",
        ylabel="Atraso observado (%)",
        ylim=(0, max(100 * (h["rate"] or 0) for h in history) + 8),
    )
    axes[1].scatter(
        [r["tenure_days"] for r in rows],
        [r["completed_sales"] for r in rows],
        s=13,
        alpha=0.35,
        color="#236F69",
    )
    for b in bands:
        right = b["high_exclusive"] or max(r["tenure_days"] for r in rows)
        if b["median_sales"] is not None:
            axes[1].hlines(
                b["median_sales"], b["low"], right, color="#A85632", linewidth=3
            )
    axes[1].set(
        title="Antiguedad y ventas de credito DEV",
        xlabel="Antiguedad (dias)",
        ylabel="Ventas completadas",
    )
    figure = output / "figuras/eda-v6.png"
    fig.savefig(figure, dpi=170)
    plt.close(fig)
    eda = {
        "known_rows": 541,
        "class_counts": {"0": 454, "1": 87},
        "history": history,
        "tenure_fixed_bands": bands,
        "bands_excluded": sum(r["tenure_days"] < 30 for r in rows),
        "causal": False,
        "new_ml": False,
    }
    (output / "figuras/eda-v6.json").write_text(json.dumps(eda, indent=2) + "\n")

    deck = []

    def slide(dark=False):
        item = {**notes[len(deck)], "dark": dark, "elements": []}
        deck.append(item)
        return item

    def txt(item, value, x=0.65, y=1.8, w=12, h=0.65, size=23, **style):
        item["elements"].append(
            dict(kind="text", text=value, x=x, y=y, w=w, h=h, size=size, **style)
        )

    def table(item, headers, data, y=1.9, widths=None, size=17, rh=0.58):
        widths = widths or [12 / len(headers)] * len(headers)
        item["elements"].append(
            dict(
                kind="table",
                headers=headers,
                rows=data,
                x=0.65,
                y=y,
                w=sum(widths),
                h=rh * (len(data) + 1),
                widths=widths,
                size=size,
                row_height=rh,
            )
        )

    def num(value):
        return f"{value:.5f}"

    item = slide(True)
    txt(
        item,
        "Fiado a un dia\nEvidencia, no aprobacion",
        y=1.1,
        h=1.5,
        size=37,
        bold=True,
    )
    txt(item, "Cerveceria Baylon / Credify / V6", y=2.9, size=27)
    txt(item, "APF1 problema  >  APF2 MVP  >  APF3 evidencia ML", y=3.8, size=22)
    team = text.split("| Integrante |", 1)[1].split("\n\n", 1)[0].splitlines()[2:]
    txt(
        item,
        "\n".join(
            " / ".join(c.strip() for c in line.strip("|").split("|")[:2])
            for line in team
        ),
        y=4.8,
        h=1.6,
        size=18,
    )

    item = slide()
    txt(
        item, "1 fiado = 1 fila / late_payment: 1 atraso, 0 puntual", size=27, bold=True
    )
    txt(
        item,
        "Cualquier saldo > 0 bloquea otro fiado\nNo vencido, abono parcial o acuerdo: tambien bloquean.",
        y=2.9,
        h=1.25,
        size=27,
        color="236F69",
        bold=True,
    )
    txt(
        item,
        "Cancelar habilita evaluacion, no aprobacion.\nVence al dia siguiente; gracia no cambia etiqueta.",
        y=4.55,
        h=1.15,
        size=25,
    )
    txt(
        item,
        "5 % financiero referencial no es prevalencia ni score.",
        y=6.2,
        size=22,
        color="A85632",
    )

    item = slide()
    audit_rows = []
    for label, audit in zip(
        ("DEV D1", "DEV D2", "FINAL"), summary["audit_summary"], strict=True
    ):
        labels = audit["study_label_counts"]
        audit_rows.append(
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
        ["Mundo", "Clientes", "Estudio", "Clases 0/1", "Sin label", "Warmup"],
        audit_rows,
        widths=[1.8, 1.8, 1.8, 2.4, 1.8, 2.4],
    )
    txt(
        item,
        "23 elementos revisados en V5, no 545 filas V6 aprobadas.",
        y=4.5,
        size=25,
        color="236F69",
        bold=True,
    )
    txt(
        item,
        "Montos enteros/.50; exactos por productos permitidos. Horas variadas.\n75/25 y corte 20:00: supuestos del equipo. 12 clientes: ejemplo.\nDEV: 541 conocidos + 4 ? / FINAL: 276 conocidos + 4 ?",
        y=5.5,
        h=1.2,
        size=20,
    )

    item = slide()
    txt(
        item,
        "DEV conocido: 454 puntuales / 87 atrasos (541)",
        y=1.65,
        size=22,
        color="236F69",
        bold=True,
    )
    item["elements"].append(
        dict(kind="image", path=str(figure), x=0.65, y=2.25, w=12, h=3.5)
    )
    band_text = " / ".join(f"n={b['n']}, med={b['median_sales']:g}" for b in bands)
    txt(item, "Bandas 30..119 / 120..239 / >=240 dias: " + band_text, y=5.95, size=17)
    txt(
        item,
        "5 pendientes/exposicion constantes 0; completed_sales = paid_credits.\nAsociacion sintetica, no causalidad ni dos senales independientes.",
        y=6.45,
        h=0.55,
        size=17,
    )

    item = slide()
    table(
        item,
        ["Modelos", "Dentro del entrenamiento", "Referencias"],
        [
            ["Arbol + SVM lineal", "Mediana + escalado", "Mayoria / positivo"],
            [
                "11 predictores previos",
                "SVM: calibracion agrupada",
                "Sin nuevas predicciones",
            ],
        ],
        widths=[3.6, 5, 3.4],
        size=19,
        rh=0.75,
    )
    txt(
        item,
        "3 folds externos agrupados por cliente",
        y=4.5,
        size=29,
        bold=True,
        color="236F69",
    )
    txt(
        item,
        "Grilla fija: arboles depth 2/3/4 leaf 8/16 weights +/-balanced; SVM C 0.1/1/10 weights.\n7 umbrales x 18 configuraciones = 126; sin busqueda posterior.",
        y=5.15,
        h=0.65,
        size=17,
        color="526572",
    )
    txt(
        item,
        "OOF reutilizado para seleccionar: optimismo, no evaluacion anidada.\nDesconocidos holdout compiten por cola, no por metrica supervisada.\nCapacidad por fold: no equivale a una cola desplegada de toda la poblacion.",
        y=5.82,
        h=1.2,
        size=17,
    )

    item = slide(True)
    txt(item, "F2 = 5TP / (5TP + 4FN + FP)", size=30, bold=True)
    txt(
        item,
        "Arbol OOF politica "
        + num(models["tree"]["review_policy"]["oof"]["metrics"]["f2"])
        + "   /   SVM "
        + num(models["svm"]["review_policy"]["oof"]["metrics"]["f2"]),
        y=2.8,
        size=25,
        color="E3AA7A",
    )
    txt(
        item,
        "depth 4 / leaf 8 / balanced / umbral 0.20\nUmbral > ordenar score > hasta 5 / replica / fecha",
        y=3.8,
        h=1.05,
        size=25,
    )
    for index, kind in enumerate(("raw", "policy")):
        metrics = summary["models"]["tree"][kind]
        values = [
            metrics[s] if kind == "raw" else metrics[s]["metrics"]
            for s in ("train", "oof", "final")
        ]
        txt(
            item,
            kind.upper()
            + " F2 train / OOF / FINAL: "
            + " / ".join(num(m["f2"]) for m in values),
            y=5.2 + index * 0.55,
            size=21,
        )
    txt(
        item,
        "Caida FINAL visible; no retocar ni sustituir por SVM despues de evaluar.",
        y=6.5,
        size=19,
        color="E3AA7A",
    )

    item = slide()
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
        y=1.75,
        widths=[2.5, 1.9, 1.9, 1.9, 1.9, 1.9],
        size=17,
    )
    txt(
        item,
        "POLITICA FINAL / 276 conocidos; desconocidos tambien consumen cola",
        y=4.85,
        size=20,
        bold=True,
        color="236F69",
    )
    for index, (family, label) in enumerate(families):
        p = models[family]["review_policy"]["final"]
        txt(
            item,
            f"{label}\nF2 {num(p['metrics']['f2'])}\nRev {p['reviews']} = {p['reviews_known']} + {p['reviews_unknown']} ?",
            x=0.65 + index * 3.04,
            y=5.5,
            w=2.9,
            h=1.2,
            size=18,
            bold=True,
        )
    txt(
        item,
        "Mayoritaria: accuracy alta, cero deteccion. Positivo RAW no es politica limitada.",
        y=6.85,
        h=0.25,
        size=13,
    )

    item = slide()
    table(
        item,
        ["Real / predicho", "0 puntual", "1 alerta"],
        [["0 puntual", 81, 162], ["1 atraso", 4, 29]],
        widths=[4, 4, 4],
        size=23,
        rh=0.65,
    )
    rules = models["tree"]["interpretation"]["raw_unit_rules"]
    path_lines = rules.splitlines()[:2] + [
        rules.splitlines()[7],
        rules.splitlines()[8],
        rules.splitlines()[9],
    ]
    assert "0.911067" in path_lines[0] and "266.500001" in path_lines[3]
    txt(
        item,
        "Camino guardado (proporcion / dias):\n" + "\n".join(path_lines),
        y=4.05,
        w=7.2,
        h=1.9,
        size=16,
        mono=True,
    )
    coef = models["svm"]["interpretation"]["standardized_coefficients"]
    txt(
        item,
        f"P {models['tree']['final']['precision']:.8f}\nR 29/33 = {models['tree']['final']['recall']:.8f}\nSVM paid_late {coef['paid_late']:+.5f}",
        x=8.2,
        y=4.1,
        w=4.4,
        h=1.5,
        size=21,
    )
    txt(
        item,
        "162 FP generan carga; utilidad no probada. Cortes no causales.\nClase de hoja != decision con umbral 0.20. Coeficiente SVM: margen, no probabilidad.",
        y=6.25,
        h=0.7,
        size=18,
    )

    item = slide()
    fields = list(entry["features"].items())
    for start, x in ((0, 0.65), (6, 7)):
        txt(
            item,
            "\n".join(f"{k}: {v}" for k, v in fields[start : start + 6]),
            x=x,
            y=1.8,
            w=5.7,
            h=2.6,
            size=18,
            mono=True,
        )
    txt(
        item,
        f"Respaldo guardado: score {illustration['probability']:.16f} > 0.20 / clase 1",
        y=4.65,
        size=25,
        bold=True,
        color="236F69",
    )
    txt(
        item,
        "known_label: null / business_approval: false\nNo prueba acierto; la politica diaria requiere lote completo.",
        y=5.45,
        h=0.9,
        size=21,
    )
    txt(
        item,
        "20 s hablados + 50 s CLI / salida NUEVA en /tmp/demo-v6-NUEVA.json\nSi falla: declararlo; mostrar respaldo guardado, no fingir exito.",
        y=6.45,
        h=0.6,
        size=17,
    )

    item = slide()
    policies = [models[f]["review_policy"]["final"] for f in ("tree", "constant_1")]
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
            for label, p in zip(("Arbol", "Positivo limitado"), policies, strict=True)
        ],
        widths=[4.1, 2.5, 3.5, 1.9],
        size=21,
        rh=0.75,
    )
    delta = policies[1]["reviews"] - policies[0]["reviews"]
    assert delta == 84
    txt(
        item,
        f"{delta} menos x 2 min = {delta * 2} minutos HIPOTETICOS",
        y=4.65,
        size=28,
        bold=True,
        color="236F69",
    )
    txt(
        item,
        "No ahorro medido. Arbol: 162 falsas alertas y 4 omisiones.\nSupera Dummy en F2: criterio tecnico descriptivo, no negocio validado.\nFaltan costos, tiempos reales y piloto autorizado comparable.",
        y=5.6,
        h=1.2,
        size=21,
    )

    optional = {}
    for filename in ("prueba-cli-v6.json", "latency-v6.json"):
        evidence = load("anexos/integracion/" + filename)
        assert evidence["passed"] is True
        assert evidence["new_training"] is False
        assert evidence["final_prediction"] is False
        assert evidence["human_demo"] == "pending"
        optional[filename] = {"saved_evidence": evidence, "business_claim": False}
    cli = optional["prueba-cli-v6.json"]["saved_evidence"]
    latency = optional["latency-v6.json"]["saved_evidence"]
    assert cli["wrapper_sha256"] == digest(root / (NAME + ".py"))
    assert cli["expected_output_sha256"] == digest(
        root / "experimento/illustrative_output.json"
    )
    assert cli["experiment_unchanged"] is True
    for key in ("probability", "threshold", "predicted", "family", "version"):
        assert (
            cli["cli_summary"][key]
            == latency["illustrative_result"][key]
            == illustration[key]
        )
    assert latency["illustrative_result"]["known_label"] is None
    assert latency["illustrative_result"]["business_approval"] is False
    assert latency["human_rehearsal"] == "pending"
    assert latency["warm_calls"] == len(latency["samples_ms"]) == 30
    assert statistics.median(latency["samples_ms"]) == latency["warm_ms"]["median"]
    assert sorted(latency["samples_ms"])[28] == latency["warm_ms"]["p95_nearest_rank"]
    assert latency["experiment_sha256_before"] == latency["experiment_sha256_after"]
    for filename, sha in latency["experiment_sha256_before"].items():
        path = root / "experimento" / filename
        assert digest(path) == sha
        sources[str(path.resolve())] = sha
    assert cli["command"][cli["command"].index("--memory") + 1] == "256m"
    integration_summary = {
        "passed": True,
        "docker_start_and_cli_seconds": cli["docker_start_and_cli_seconds"],
        "first_predict_ms": latency["first_predict_ms"],
        "warm_calls": latency["warm_calls"],
        "warm_ms": latency["warm_ms"],
        "peak_process_rss_kib": latency["peak_process_rss_kib"],
        "peak_process_rss_mib": latency["peak_process_rss_kib"] / 1024,
        "run_memory_limit": "256m",
        "scope": latency["scope"],
        "not_measured": latency["not_measured"],
        "capacity_guarantee": False,
        "human_demo": "pending",
        "human_rehearsal": "pending",
        "new_measurement_by_export": False,
    }
    item = slide()
    txt(
        item,
        "V6: web academica en demo + CLI con artefactos",
        size=28,
        color="236F69",
        bold=True,
    )
    txt(
        item,
        "Integracion web V6 en demo heredada, rutas protegidas.\nEjemplo S/20 sin datos reales ni autorizacion comercial.\nProduccion/evaluacion real siguen separadas.",
        y=2.9,
        h=1.5,
        size=25,
    )
    txt(
        item,
        "Reproduccion actual passed=true\n47 archivos / 12 RAW / 12 politicas / 5 Joblib byte a byte",
        y=4.6,
        h=0.85,
        size=22,
        bold=True,
    )
    txt(
        item,
        f"CLI Docker {cli['docker_start_and_cli_seconds']:.3f} s / predict inicial {latency['first_predict_ms']:.2f} ms\n"
        f"30 llamadas: mediana {latency['warm_ms']['median']:.2f} ms / p95 {latency['warm_ms']['p95_nearest_rank']:.2f} ms\n"
        "Incluye integridad + deserializacion; no HTTP/auth/DB/navegador.\n"
        f"RSS {latency['peak_process_rss_kib']} KiB (~{latency['peak_process_rss_kib'] / 1024:.2f} MiB), limite 256m: no garantiza capacidad.\n"
        "passed=true: preparacion tecnica probada; demo/ensayo humanos pendientes.",
        y=5.75,
        h=1.3,
        size=15,
    )

    item = slide()
    txt(item, "Ley N. 29733 / D.S. N. 016-2024-JUS", size=30, bold=True, color="236F69")
    txt(
        item,
        "Finalidad, base juridica, informacion, acceso, conservacion y ARCO.\nNo ficha privada publicada; no consentimiento inventado.",
        y=3,
        h=1.15,
        size=24,
    )
    txt(
        item,
        'Asistencia IA: prompts disponibles y vacios declarados.\n"ya hazlo todo correctamente": instruccion, no consentimiento.\n4 revisiones individuales y ensayo: pendientes, no aprobados.',
        y=4.8,
        h=1.5,
        size=24,
    )

    item = slide(True)
    txt(
        item,
        "Reproducible no significa validado en negocio",
        y=1.9,
        size=32,
        color="E3AA7A",
        bold=True,
    )
    txt(
        item,
        "29 detectados / 162 falsas alertas / 4 omisiones\nBaja precision y caida FINAL visibles. SVM FINAL mejor.",
        y=3.2,
        h=1.2,
        size=28,
    )
    txt(
        item,
        "Deuda: bloqueo. Sin historial: revision del propietario.\nSin prediccion en ambos; CLI y web V6 sinteticas.",
        y=4.65,
        h=0.95,
        size=23,
    )
    txt(
        item,
        "Riesgos PROY: piloto consentido -> nuevos datos; FN/FP + minutos -> reglas acordadas;\nadaptador CLI + QA/rollback -> integracion; ARCO/conservacion -> controles antes de operar.\nPropuestos: Cesar / Omara / Tamara / Pablo.",
        y=5.62,
        h=1.3,
        size=17,
        color="E3AA7A",
    )

    elapsed = 0
    for item in deck:
        start = elapsed
        elapsed += item["seconds"]
        color = "C8D6DF" if item["dark"] else "526572"
        txt(
            item,
            "UTP / GRUPO 2 / V6",
            x=0.65,
            y=0.25,
            w=5,
            h=0.25,
            size=10,
            color=color,
            bold=True,
        )
        txt(
            item,
            f"{item['owner']} / {start // 60:02}:{start % 60:02} - {elapsed // 60:02}:{elapsed % 60:02} / {item['number']:02}/13",
            x=7.2,
            y=0.25,
            w=5.4,
            h=0.25,
            size=10,
            color=color,
            align="right",
        )
        if item["number"] != 1:
            txt(item, item["title"], y=0.8, h=0.8, size=28, bold=True)
        txt(item, STATUS, y=7.16, h=0.2, size=9, color=color)
    assert len(deck) == 13 and elapsed == 720
    renderer.export_slides(deck, output, name=NAME, version="V6")
    native = Presentation(output / (NAME + ".pptx"))
    assert len(native.slides) == 13
    native_checks = 0
    for item, native_slide in zip(deck, native.slides, strict=True):
        assert native_slide.notes_slide.notes_text_frame.text == item["notes"]
        assert len(native_slide.shapes) == len(item["elements"])
        for element, shape in zip(item["elements"], native_slide.shapes, strict=True):
            for key, actual in (
                ("x", shape.left),
                ("y", shape.top),
                ("w", shape.width),
                ("h", shape.height),
            ):
                assert abs(actual / 914400 - element[key]) < 0.00001
            if element["kind"] == "text":
                assert shape.text == element["text"]
            elif element["kind"] == "table":
                assert [[c.text for c in row.cells] for row in shape.table.rows] == [
                    [str(v) for v in row]
                    for row in [element["headers"], *element["rows"]]
                ]
            else:
                assert hashlib.sha256(shape.image.blob).hexdigest() == digest(
                    Path(element["path"])
                )
            native_checks += 1

    timeline, elapsed = [], 0
    for note in notes:
        end = elapsed + note["seconds"]
        timeline.append(
            [
                note["number"],
                note["owner"],
                f"{elapsed // 60:02}:{elapsed % 60:02} - {end // 60:02}:{end % 60:02}",
                note["seconds"],
            ]
        )
        elapsed = end
    pages = [
        "# Guion V6 / APF3 / 12 minutos\n\n**Revision humana y ensayo pendientes. Roles propuestos, no contribuciones acreditadas.**\n\n| Integrante |"
        + text.split("| Integrante |", 1)[1].split("\n\n", 1)[0]
        + "\n\n"
        + documents.table(["Diap.", "Expositor", "Ventana", "Segundos"], timeline)
        + f"\n\n**{words} palabras habladas.** Meta editorial 1250..1450, no consigna. 720 s: 670 hablados y 50 operativos; diapositiva 9: 20+50. Preguntas fuera del cronometro. Duracion real pendiente."
    ]
    for start, end in ((0, 3), (3, 6), (6, 9), (9, 13)):
        pages.append(
            f"# Intervenciones {start + 1} a {end}\n\n"
            + "\n\n".join(
                f"## {n['number']}. {n['title']}\n\n**{n['owner']} / {n['seconds']} s.**\n\n{n['spoken']}\n\n**Apoyo no hablado:** {n['first_action']}"
                for n in notes[start:end]
            )
        )
    for index in range(3):
        pages.append(
            f"# Preguntas dificiles {index + 1}/3\n\n**Fuera de los 720 segundos.**\n\n"
            + "\n\n".join(qa[index * 6 : (index + 1) * 6])
        )
    pages.append(
        "# Demo CLI / preparacion y comando\n\n**Instrucciones, no ejecucion humana certificada.**\n\n"
        + notes[8]["notes"].split("**Acción:**", 1)[1].split("**Acción:**", 1)[0]
    )
    pages.append(
        "# Demo CLI / entrada, respaldo y limites\n\n```json\n"
        + json.dumps(entry, indent=2)
        + "\n```\n\n**Respaldo guardado:** score 0.7171978005286032; umbral 0.2; predicho 1; known_label=null; business_approval=false.\n\n**Acción:**"
        + notes[8]["notes"].split("**Acción:**", 2)[2]
        + "\n\n**Trazabilidad:** SHA-256 reales, objetos de metricas completos y seleccion en plan-sustentacion-v6.json. Reproduccion passed: 47 archivos, 12 RAW, 12 politicas y 5 Joblib identicos. No nueva inferencia en esta exportacion."
    )
    pages.append(
        "# Revision humana pendiente\n\n"
        + re.sub(r"\n(?=- \[ \])", "\n\n", review)
        + "\n\n**Asistencia IA:** la instruccion literal del usuario 'ya hazlo todo correctamente' puede citarse como asistencia, nunca como consentimiento. Prompts disponibles y vacios del historial deben conservarse honestamente. Sin firmas, aprobaciones ni revisiones inventadas."
    )
    compact = "\n\n<!-- PAGE -->\n\n".join(pages)
    (output / (GUIDE + ".md")).write_text(compact, encoding="utf-8")
    (output / "Guion_completo_con_indicaciones.md").write_text(text, encoding="utf-8")
    document_result = documents.documents(
        compact, output, name=GUIDE, expected_figures=0
    )
    html_path = output / (GUIDE + ".html")
    markup = html_path.read_text().replace(
        "APF3 - Credify - Borrador", "APF3 - Guion V6 - Revision humana pendiente"
    )
    markup = markup.replace(
        "</style>",
        "body{width:174mm;font:10pt/1.18 Arial,sans-serif}.page{display:flow-root}p{margin:0 0 6px}h1{font-size:16pt;margin:0 0 10px}h2{font-size:11.5pt;margin:10px 0 6px}th,td{padding:4px}.page:first-child h1{margin-top:0;font-size:17pt}pre{margin:6px 0;padding:6px}pre code{font-size:8pt}</style>",
    )
    html_path.write_text(markup, encoding="utf-8")
    doc = Document(output / (GUIDE + ".docx"))
    doc.core_properties.title = "APF3 Guion V6 / Revision humana pendiente"
    doc.styles["Normal"].font.size = Pt(10)
    doc.styles["Normal"].paragraph_format.space_after = Pt(4)
    for section in doc.sections:
        section.footer.paragraphs[0].runs[0].text = STATUS + " | "
    doc.save(output / (GUIDE + ".docx"))

    renders = {}
    for name, kind in ((NAME, "deck"), (GUIDE, "guide")):
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
            env=dict(os.environ, PLAYWRIGHT_MODULE_PATH=playwright_module),
            capture_output=True,
            text=True,
        )
        if process.returncode:
            raise RuntimeError(process.stderr)
        audit = json.loads(process.stdout)
        pdf = PdfReader(output / (name + ".pdf"))
        assert (
            len(pdf.pages)
            == len(audit["sections"])
            == (13 if kind == "deck" else len(pages))
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
                            index,
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
            full_text = normalize("\n".join(p.extract_text() for p in pdf.pages))
            assert all(
                normalize(p) in full_text
                for n in notes
                for p in n["spoken"].split("\n\n")
            )
            assert all(normalize(q) in full_text for q in qa)
        renders[kind] = {**audit, "pdf_pages": len(pdf.pages), "pdf_text_checked": True}
    assert all(digest(Path(path)) == sha for path, sha in sources.items()), (
        "Source changed during export"
    )
    outputs = [
        p
        for p in output.rglob("*")
        if p.is_file() and p.name != "plan-sustentacion-v6.json"
    ]
    plan = {
        "edition": "pending-v6",
        "generated_utc": datetime.now(UTC).isoformat(),
        "slides": 13,
        "planned_seconds": 720,
        "spoken_planned_seconds": 670,
        "slide_9": {"spoken_seconds": 20, "live_seconds": 50},
        "spoken_words": words,
        "word_target_editorial_not_assignment_requirement": [1250, 1450],
        "word_target_met": True,
        "question_count": len(qa),
        "human_checklist_count": 4,
        "human_review": "pending",
        "human_rehearsal": "pending",
        "roles": "proposed",
        "planned_speaker_seconds": {
            owner: sum(n["seconds"] for n in notes if n["owner"] == owner)
            for owner in dict.fromkeys(n["owner"] for n in notes)
        },
        "slides_data": [
            {
                k: n[k]
                for k in ("number", "title", "owner", "seconds", "spoken", "notes")
            }
            for n in notes
        ],
        "selection_cache": {"winner": winner, "new_selection": False},
        "metrics_cache": {
            f: {
                "raw": {s: models[f][s] for s in ("train", "oof", "final")},
                "policy": models[f]["review_policy"],
            }
            for f, _ in families
        },
        "baseline_comparison": summary["baseline_comparison"],
        "business_validated": False,
        "interpretation_cache": {
            f: models[f]["interpretation"] for f in ("tree", "svm")
        },
        "tree_path_displayed": path_lines,
        "eda": eda,
        "optional_integration_evidence": optional,
        "integration_technical_summary": integration_summary,
        "web_scope": "Authenticated synthetic V6 lab in inherited public demo; no production or comercial authorization",
        "demo": {
            "primary": "root CLI offline",
            "human_demo": "pending",
            "environment": "Python 3.12.14 and pinned requirements; prebuilt compatible Docker or clean local venv prepared beforehand",
            "new_output": "/tmp/demo-v6-NUEVA.json",
            "illustration": illustration,
            "executed_by_export": False,
        },
        "new_training": False,
        "new_predictions": False,
        "new_tuning": False,
        "runtime_generation": False,
        "raw_private_read": False,
        "private_word_copy": False,
        "report_unchanged": True,
        "source_sha256": sources,
        "source_sha256_after": {p: digest(Path(p)) for p in sources},
        "output_sha256": {str(p.relative_to(output)): digest(p) for p in outputs},
        "metric_cells_checked": 20,
        "native_elements_checked": native_checks,
        "documents": document_result,
        "render": renders,
        "native_render_caveat": "PPTX geometry/content/notes verified; Microsoft Word/PowerPoint physical rendering not executed",
    }
    (output / "plan-sustentacion-v6.json").write_text(
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
                "human_checks_pending": 4,
                "pdf_pages": {k: v["pdf_pages"] for k, v in renders.items()},
                "text_overflow": 0,
                "element_bounds_errors": 0,
                "eda": eda,
                "report_sha256": sources[
                    str((root / "experimento/pending_v6_report.json").resolve())
                ],
                "source_hashes_unchanged": True,
                "integration_technical_summary": integration_summary,
                "integration_source_sha256": {
                    filename: sources[
                        str((root / "anexos/integracion" / filename).resolve())
                    ]
                    for filename in optional
                },
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
