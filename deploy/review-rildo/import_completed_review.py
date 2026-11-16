"""Import the completed intentional V5 review without changing frozen evidence."""

import argparse
import csv
import hashlib
import html
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
DOWNLOADS = Path('/Users/tamaraalison/Downloads')
BUNDLE = DOWNLOADS / 'APF3_Revision_Rildo_V5'
OUTPUT = DOWNLOADS / 'APF3_Revision_Rildo_V5_Procesada'
V6 = DOWNLOADS / 'APF3_Grupo2_Pendiente_V6'
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W = '{' + NS['w'] + '}'
DOCX_HASH = '82d4c748b3403e8a3e45b4361b95e9da4ffaf0b0ca21e3a9ac4baedc6040f29b'
BLANK_HASH = 'f4d6eb34a69ecd4bcc5b3aacb243b7d840b8358a16f2a8b80b11defb378a95c3'
ORDINALS = [18, 19, 24, 25, 26, *range(33, 38), *range(46, 56)]
TITLE = 'Revisión parcial completada con correcciones; no aprobación global'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text(element):
    return ''.join(n.text or '' if n.tag == W + 't' else
                   '\n' if n.tag in (W + 'br', W + 'cr') else
                   '\t' if n.tag == W + 'tab' else '' for n in element.iter())


def parse_docx(path):
    counts = Counter(dict.fromkeys([
        'comments', 'commentRangeStart', 'commentRangeEnd', 'commentReference',
        'ins', 'del', 'moveFrom', 'moveTo', 'trackRevisions', 'external_relationships',
        'embedded_objects', 'altChunk', 'property_changes'], 0))
    with ZipFile(path) as archive:
        for name in archive.namelist():
            if name.endswith(('.xml', '.rels')):
                root = ET.fromstring(archive.read(name))
                for node in root.iter():
                    local = node.tag.rsplit('}', 1)[-1]
                    if local == 'comment':
                        counts['comments'] += 1
                    elif local in counts and local != 'comments':
                        counts[local] += 1
                    if local.endswith('PrChange'):
                        counts['property_changes'] += 1
                    if local == 'Relationship' and node.get('TargetMode') == 'External':
                        counts['external_relationships'] += 1
            if name.startswith(('word/embeddings/', 'word/activeX/')):
                counts['embedded_objects'] += 1
        body = ET.fromstring(archive.read('word/document.xml')).find('w:body', NS)
        paragraphs = [text(p) for p in body.findall('w:p', NS)]
        tables = [[[ '\n'.join(text(p) for p in c.findall('w:p', NS))
                     for c in r.findall('w:tc', NS)]
                   for r in t.findall('w:tr', NS)] for t in body.findall('w:tbl', NS)]
    return paragraphs, tables, dict(counts)


def markdown_tables(markdown):
    tables = []
    for line in markdown.splitlines():
        if not line.startswith('|'):
            continue
        cells = [c.strip().replace('<br>', '\n') for c in line.strip('|').split('|')]
        if all(c == '---' for c in cells):
            continue
        if cells[0] in ('Caso inventado', 'Intento inventado', 'Historia / semana desde',
                        'Supuesto: Esto se parece a lo que pasa?'):
            tables.append([])
        tables[-1].append(cells)
    return tables


def validate_tables(tables, template, source):
    require(len(tables) == len(template) == 5, 'Expected all five tables')
    groups = ['fiados', 'fiados', 'rejections', 'weeks', 'assumptions']
    expected_sizes = [6, 6, 4, 4, 3]
    records = []
    for ti, (actual, blank, group, size) in enumerate(zip(tables, template, groups, expected_sizes, strict=True), 1):
        require(len(actual) == len(blank) == size + 1, f'Table {ti}: row count')
        require(actual[0] == blank[0], f'Table {ti}: altered header')
        response_col = 1 if ti == 5 else len(blank[0]) - 1
        refs = source['sample'][group]
        if ti in (1, 2):
            refs = refs[(ti - 1) * 6:ti * 6]
        require(len(refs) == size, f'Table {ti}: source count')
        for ri, (row, old, ref) in enumerate(zip(actual[1:], blank[1:], refs, strict=True), 1):
            require(len(row) == len(old) == len(blank[0]), f'Table {ti}: columns')
            require(row[:response_col] == old[:response_col], f'Table {ti} row {ri}: nonresponse changed')
            require(old[response_col] == '' and (ti != 5 or old[2] == ''), 'Template not blank')
            raw = row[response_col]
            require(raw in ('Habitual', 'Posible', 'no', 'posible', 'no se'), 'Blank or invalid response')
            require(raw == ref['response'], f'Table {ti} row {ri}: exact source mismatch')
            if group in ('fiados', 'rejections'):
                ids = re.findall(r'SET5-D[12]-[LA]\d{5}', row[0])
                require(ids == [ref['id']], 'ID mismatch')
                key = ref['id']
            elif group == 'weeks':
                require(row[0] == ref['world'] + '\n' + ref['week_start'], 'Week mismatch')
                require(row[2] == f"{ref['grants']} / {ref['grant_clients']}", 'Week grants mismatch')
                key = ref['world'] + '/' + ref['week_start']
            else:
                key = ref['id']
                require(bool(row[2].strip()), 'Missing assumption correction')
            records.append({'id': key, 'group': group, 'table_ordinal': ti,
                            'row_ordinal': ri + 1, 'column_ordinal': response_col + 1,
                            'raw_response': raw,
                            'classification_canonical': raw.lower().replace(' ', '_'),
                            'raw_correction': row[2] if ti == 5 else ''})
    require(len(records) == 23 and len({r['id'] for r in records}) == 23, 'Expected 23 unique responses')
    require(Counter(r['raw_response'] for r in records) ==
            {'Habitual': 9, 'Posible': 11, 'no': 1, 'posible': 2}, 'Classification count')
    for group, expected in [('fiados', 12), ('rejections', 4), ('weeks', 4), ('assumptions', 3)]:
        require(source['sample'][group + '_reviewed' if group != 'rejections' else 'rejections_reviewed']
                == expected, 'Source declared count')
    return records


def csv_crosscheck(bundle, tables, source):
    for filename, group, table_rows, key in [
        ('muestra-fiados.csv', 'fiados', tables[0][1:] + tables[1][1:], 'loan_id'),
        ('muestra-rechazos.csv', 'rejections', tables[2][1:], 'attempt_id'),
        ('muestra-semanas.csv', 'weeks', tables[3][1:], 'week_start'),
    ]:
        with (bundle / filename).open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        require(len(rows) == len(table_rows) == len(source['sample'][group]), 'CSV count mismatch')
        for row, cells, ref in zip(rows, table_rows, source['sample'][group], strict=True):
            require(row['respuesta'] == row['correccion'] == '', 'Historical CSV not blank')
            require(row[key] == ref.get('id', ref.get('week_start')), 'CSV ID mismatch')
            if group == 'fiados':
                require(cells[1] == f"{row['fecha'][:10]}\nS/{row['monto']}\nVence {row['vence']}\nSaldo antes S/{row['saldo_antes']}", 'CSV financial mismatch')
            elif group == 'weeks':
                require(cells[1:] == [f"{row['requests']} / {row['request_clients']}",
                                     f"{row['grants']} / {row['grant_clients']}", ''], 'CSV week mismatch')


def corrections(paragraphs, tables, source):
    require('15/11/2026' in paragraphs[1] and '15/11/2026' in paragraphs[45]
            and source['review_date'] == '2026-11-15', 'Review date mismatch')
    entries = []
    for ordinal in ORDINALS:
        raw = paragraphs[ordinal - 1]
        require(bool(raw.strip()), f'Missing correction P{ordinal}')
        prompt = ''
        value = raw
        if ordinal in (18, 24, 33):
            prompt, value = raw.split(':', 1)
            prompt += ':'
            value = value.lstrip('\n_')
        elif ordinal == 46:
            prompt, value = raw.split('Otra correccion: ', 1)
            prompt += 'Otra correccion: '
        entries.append({'kind': 'correction', 'source_ordinal': f'P{ordinal}',
                        'paragraph_index_zero_based': ordinal - 1, 'raw_text': raw,
                        'source_prompt': prompt, 'correction_text': value})
    values = [e['correction_text'] for e in entries] + [r[2] for r in tables[4][1:]]
    for ordinal, value in enumerate(source['correction_verbatim'], 1):
        require(value in values, f'Correction source ordinal {ordinal} not found verbatim')
    return entries


def render_summary(output, pages):
    from docx import Document
    from docx.shared import Mm, Pt
    from pypdf import PdfReader

    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.top_margin = section.bottom_margin = Mm(20)
    doc.styles['Normal'].font.size = Pt(11)
    chunks = []
    for index, (heading, paragraphs) in enumerate(pages):
        if index:
            doc.add_page_break()
        doc.add_heading(heading, 1)
        for paragraph in paragraphs:
            doc.add_paragraph(paragraph)
        chunks.append('<section><h1>' + html.escape(heading) + '</h1>' +
                      ''.join('<p>' + html.escape(p) + '</p>' for p in paragraphs) + '</section>')
    doc.save(output / 'resumen.docx')
    require(len(Document(output / 'resumen.docx').paragraphs) > 10, 'DOCX reopening failed')
    (output / 'resumen.html').write_text('<!doctype html><html lang="es"><meta charset="utf-8"><style>'
        '@page{size:A4;margin:0}*{box-sizing:border-box}body{margin:0;font:11pt Arial;color:#17212b}'
        'section{width:210mm;height:297mm;padding:20mm;break-after:page}'
        'section:last-child{break-after:auto}h1{font-size:20pt;line-height:1.2}'
        'p{line-height:1.4;margin:0 0 5mm}</style><body>' + ''.join(chunks) + '</body></html>')
    renderer = """import {pathToFileURL} from 'node:url';
const {chromium}=await import(pathToFileURL(process.argv[2]).href);
const browser=await chromium.launch({headless:true});
try {
const page=await browser.newPage();
await page.route('**/*',r=>r.request().url().startsWith('file:')?r.continue():r.abort());
await page.goto(pathToFileURL(process.argv[3]).href);
await page.emulateMedia({media:'print'});
const checks=await page.locator('section').evaluateAll(ss=>ss.map(s=>({
overflow:[...s.children].some(n=>n.getBoundingClientRect().bottom>s.getBoundingClientRect().bottom-50),
minFont:Math.min(...[...s.querySelectorAll('p')].map(p=>parseFloat(getComputedStyle(p).fontSize)))})));
await page.pdf({path:process.argv[4],preferCSSPageSize:true,printBackground:true});
console.log(JSON.stringify(checks));
} finally {await browser.close();}
"""
    (output / 'render-local.mjs').write_text(renderer)
    module = Path('/var/folders/sx/_6ljw37n2_j9hk2f_vtqplj40000gn/T/opencode/apf3-render/node_modules/playwright/index.mjs')
    run = subprocess.run(['node', str(output / 'render-local.mjs'), str(module),
                          str(output / 'resumen.html'), str(output / 'resumen.pdf')],
                         capture_output=True, text=True, check=True)
    checks = json.loads(run.stdout)
    pdf = PdfReader(output / 'resumen.pdf')
    require(len(pdf.pages) == 2 and all(not c['overflow'] and c['minFont'] >= 14 for c in checks), 'PDF layout failed')
    require(all(' '.join(heading.split()) in ' '.join(page.extract_text().split())
                for (heading, _), page in zip(pages, pdf.pages, strict=True)), 'PDF text failed')
    return {'pdf_pages': len(pdf.pages), 'layout': checks, 'docx_reopened': True, 'network': 'blocked'}


def build(output=OUTPUT, resume=False):
    require(output.resolve() == OUTPUT and output.parent.is_dir(), 'Fixed output only; parent must exist')
    if output.exists():
        partial = {'responses.json', 'rawentries.csv', 'corrections.md', 'resumen.md',
                   'resumen.docx', 'resumen.html', 'resumen.pdf', 'render-local.mjs'}
        if (output / 'manifest.json').exists():
            prior = json.loads((output / 'manifest.json').read_text())['outputs']
            require({p.name for p in output.iterdir()} == set(prior) | {'manifest.json'}
                    and all(sha(output / n) == h for n, h in prior.items()), 'Processed output changed')
            partial |= {'audit.json', 'manifest.json'}
        require(resume and {p.name for p in output.iterdir()} <= partial,
                'Output exists; explicit resume required, unknown files forbidden')
    source_path = ROOT / 'docs/APF3_OWNER_REVIEW_V5.json'
    source = json.loads(source_path.read_text())
    manifest = json.loads((BUNDLE / 'manifest.json').read_text())
    original_files = sorted(p for p in BUNDLE.iterdir() if p.is_file())
    require({p.name for p in original_files} == set(manifest['outputs']) | {'manifest.json'}, 'Bundle membership mismatch')
    before = {p.name: sha(p) for p in original_files}
    require(before['Revision_Rildo_V5.docx'] == source['source_docx_sha256'] == DOCX_HASH, 'Unexpected completed DOCX')
    require(manifest['outputs']['Revision_Rildo_V5.docx'] == BLANK_HASH, 'Unexpected blank template hash')
    checked = {n: {'expected': h, 'actual': before[n], 'unchanged': before[n] == h}
               for n, h in manifest['outputs'].items() if not n.endswith('.docx')}
    require(all(c['unchanged'] for c in checked.values()), 'Historical bundle changed')
    # Hash all frozen inputs and modules before rendering, including their manifests.
    protected = original_files + [source_path, Path(__file__),
        ROOT / 'backend/app/ml/owner_pending_synthetic.py',
        ROOT / 'backend/app/ml/owner_aligned_synthetic.py',
        ROOT / 'backend/app/ml/owner_settled_synthetic.py']
    protected += sorted((ROOT / 'docs').glob('APF3_*.json'))
    for folder in [V6, DOWNLOADS / 'APF3_Grupo2_Liquidacion_V5', DOWNLOADS / 'APF3_Grupo2_Alineado_V4']:
        protected += [p for p in folder.rglob('*') if p.is_file()]
    protected_before = {str(p): sha(p) for p in protected}
    paragraphs, tables, xml_counts = parse_docx(BUNDLE / 'Revision_Rildo_V5.docx')
    require(not any(xml_counts.values()), 'Comments, revisions or external/embedded content detected')
    template = markdown_tables((BUNDLE / 'Revision_Rildo_V5.md').read_text())
    records = validate_tables(tables, template, source)
    csv_crosscheck(BUNDLE, template, source)
    entries = corrections(paragraphs, tables, source)
    report = json.loads((V6 / 'data_revision_report.json').read_text())
    require([report[k] for k in ('study_rows', 'known_rows', 'class_0', 'class_1', 'unknown_rows')]
            == [545, 541, 454, 87, 4], 'V6 report counts changed')
    require(not report['coherence_accepted'] and not report['models_trained'] and not report['final_generated'], 'V6 stage changed')
    output.mkdir(exist_ok=resume)
    def dump(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n')
    dump('responses.json', {'status': TITLE, 'review_date': source['review_date'], 'responses': records,
                           'raw_counts': dict(Counter(r['raw_response'] for r in records)),
                           'canonical_counts': dict(Counter(r['classification_canonical'] for r in records)),
                           'corrections': entries,
                           'additional_source_responses': [
                               {'source_ordinal': f'additional_responses_verbatim[{i}]', 'raw_text': value,
                                'origin': 'latest JSON source, not present in completed DOCX'}
                               for i, value in enumerate(source['additional_responses_verbatim'], 1)]})
    with (output / 'rawentries.csv').open('w', newline='') as stream:
        fields = ['kind', 'source_ordinal', 'id', 'raw_text', 'classification_canonical', 'source_prompt']
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for r in records:
            location = f"T{r['table_ordinal']}/R{r['row_ordinal']}/C{r['column_ordinal']}"
            writer.writerow({'kind': 'response', 'source_ordinal': location, 'id': r['id'],
                             'raw_text': r['raw_response'], 'classification_canonical': r['classification_canonical']})
            if r['raw_correction']:
                writer.writerow({'kind': 'correction', 'source_ordinal': location.rsplit('/', 1)[0] + '/C3',
                                 'id': r['id'], 'raw_text': r['raw_correction']})
        for e in entries:
            writer.writerow({k: e[k] for k in ('kind', 'source_ordinal', 'raw_text', 'source_prompt')})
    correction_md = '# Correcciones del Word completado\n\nOrdinales P desde 1; raw_text conserva el prompt y texto exactos. No se copia el Word ni contactos.\n\n'
    for e in entries:
        correction_md += f"## {e['source_ordinal']} (indice Python {e['paragraph_index_zero_based']})\n\n{e['raw_text']}\n\n"
    for r in records[-3:]:
        correction_md += f"## T5/R{r['row_ordinal']}/C3: {r['id']}\n\n{r['raw_correction']}\n\n"
    (output / 'corrections.md').write_text(correction_md)
    pages = [
        (TITLE, [
            'Fecha de revisión: 15/11/2026. Revisión intencional de situaciones inventadas; no es un acta firmada ni una auditoría de clientes reales.',
            'Se importaron 23 respuestas: 12 fiados, 4 rechazos, 4 semanas y 3 supuestos. Habitual: 9 (3 fiados, 4 rechazos, 2 semanas). Posible: 11 (9 fiados, 2 semanas). Además: no: 1 y posible: 2, conservando las minúsculas originales.',
            'Los ejemplos parecen razonables con correcciones. No se aprobaron las 540 filas V5 ni las 545 filas nuevas V6. No se midió precisión predictiva ni se autorizó producción.',
            'Cualquier saldo pendiente bloquea otro fiado, aunque la deuda todavía no venza. En el ejemplo de S/30, pagar S/20 deja S/10 pendientes: no habilita un nuevo fiado. Un acuerdo tampoco reemplaza la cancelación completa.',
            'Cancelar toda la deuda permite evaluar una nueva solicitud; no obliga a aprobarla. El pago debe observarse antes de la evaluación, no después ni simultáneamente.',
            'Los casos 9 y 10 permanecen sin resultado conocido al corte simulado del 30/09/2026: vencían el 01/10/2026. Esa es la referencia temporal, no la fecha posterior de esta revisión.',
            'Pagar después del vencimiento es atraso. Los tres días de gracia comercial no convierten el pago en puntual.',
        ]),
        ('Correcciones e impacto en V6', [
            'Montos: son comunes los soles completos o terminados en S/0.50. Se pueden conservar importes exactos cuando corresponden al precio de los productos. No hay una frecuencia real medida.',
            'Horarios: pueden variar, normalmente entre 08:00–12:00 y 16:00–20:00. No se confirmó una hora fija real de pago ni de vencimiento.',
            'Clientes: 12 se acepta como grupo de ejemplo, no como población real fija. Los clientes pueden rotar cada semana. Alrededor de 12 fiados a 9 clientes es habitual, no una cantidad constante; 8/7 es posible y menos habitual que 11 o 12 fiados.',
            'V6 ya generado es únicamente DEV sintético: 545 filas, 541 con resultado conocido (454 puntuales y 87 con atraso), y 4 desconocidas. Rildo NO revisó estas nuevas filas. El informe conserva coherence_accepted=false; no hay modelo nuevo ni prueba final.',
            'SUPUESTOS DEL EQUIPO, no mediciones ni aprobación de Rildo: mezcla 75% redondeados / 25% precios exactos; corte contractual duro a las 20:00; calendario sintético de rotación y distribuciones. La hora real exacta de vencimiento queda sin confirmar.',
            'Los modelos públicos y la aplicación local siguen usando evidencia V4 anterior. Sus métricas no corresponden a V6. Esta importación no despliega ni altera modelos, protocolos o datos congelados.',
            'Siguiente condición: revisar la adecuación de DEV y predeclarar por separado la selección y evaluación antes de cualquier modelo adicional. Sin aprobación global, sin autorización de producción y sin ajustar semillas para mejorar resultados.',
            'Evidencia: responses.json, rawentries.csv, corrections.md y audit.json. El MD/PDF original en blanco es histórico, no la revisión completada actual. El Word original se conserva sin duplicarlo.',
        ]),
    ]
    summary = '\n\n'.join('# ' + heading + '\n\n' + '\n\n'.join(ps) for heading, ps in pages) + '\n'
    (output / 'resumen.md').write_text(summary)
    layout = render_summary(output, pages)
    protected_after = {p: sha(Path(p)) for p in protected_before}
    require(protected_before == protected_after, 'Frozen source changed during import')
    audit = {'docx_hash_before': before['Revision_Rildo_V5.docx'],
             'docx_hash_after': sha(BUNDLE / 'Revision_Rildo_V5.docx'),
             'template_blank_hash_from_manifest': BLANK_HASH,
             'expected_exception': 'DOCX intentionally completed, not source corruption',
             'bundle_total_files_actual': len(original_files), 'other_manifest_outputs_verified': checked,
             'manifest_hash_before': before['manifest.json'], 'manifest_hash_after': sha(BUNDLE / 'manifest.json'),
             'count_note': '12 total bundle files, not 12 OTHER outputs: 10 other outputs plus manifest and DOCX',
             'xml_counts_all_zip_parts': xml_counts, 'all_5_tables_nonresponse_cells_match_md': True,
             'csv_sample_crosscheck': True, 'responses_exact_source_matches': len(records),
             'source_json_sha256': sha(source_path), 'source_ordinal_base': 1,
             'correction_paragraph_ordinals': ORDINALS, 'correction_verbatim_matches': 11,
             'additional_json_verbatim_count': 3, 'not_global_approval': True,
             'protected_hashes_before': protected_before, 'protected_hashes_after': protected_after,
             'sources_intact': True, **layout}
    dump('audit.json', audit)
    dump('manifest.json', {'outputs': {p.name: sha(p) for p in sorted(output.iterdir())
                                     if p.is_file() and p.name != 'manifest.json'}})
    print(json.dumps({'output': str(output), 'responses': len(records), 'sources_intact': True, **layout}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--resume', action='store_true', help='Resume this importer incomplete output only')
    args = parser.parse_args()
    build(args.output, args.resume)
