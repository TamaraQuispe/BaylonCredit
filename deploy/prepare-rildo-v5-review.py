"""Build a small, offline, reproducible owner review from frozen V5 DEV only."""

import argparse
import csv
import hashlib
import html
import json
import statistics
import subprocess
from collections import Counter
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

SEED = 2026111601
ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('/Users/tamaraalison/Downloads/APF3_Grupo2_Liquidacion_V5')
OUTPUT = Path('/Users/tamaraalison/Downloads/APF3_Revision_Rildo_V5')
FOOTER = 'Solo datos inventados | Revision de Rildo pendiente'
OPTIONS = 'Rildo: habitual / posible / no / no se'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True, default=str) + '\n')


def observed(loan, cutoff):
    return sorted((p for p in loan['payments'] if datetime.fromisoformat(p['at']) <= cutoff),
                  key=lambda p: (p['at'], p['payment_id']))


def outcome(loan, cutoff):
    payments = observed(loan, cutoff)
    amount = Decimal(loan['amount'])
    total = Decimal('0')
    completed = None
    for payment in payments:
        total += Decimal(payment['amount'])
        if total >= amount and completed is None:
            completed = date.fromisoformat(payment['at'][:10])
    assert total <= amount
    due = date.fromisoformat(loan['due_date'])
    delay = max(0, (completed - due).days) if completed else None
    label = int(delay > 0) if completed else (1 if cutoff.date() > due else None)
    return {'payments': payments, 'paid': total, 'pending': amount - total,
            'completed': completed, 'delay': delay, 'label': label,
            'abonos': len(payments) >= 2 or Decimal('0') < total < amount}


def balance_before(world, client, evaluated_at):
    """Payments at exactly the evaluation instant do not establish prior settlement."""
    at = datetime.fromisoformat(evaluated_at)
    overdue = Decimal('0')
    outstanding = Decimal('0')
    evidence = []
    for loan in world['loans']:
        if loan['client_id'] != client or loan['evaluated_at'] >= evaluated_at:
            continue
        payments = [p for p in loan['payments'] if datetime.fromisoformat(p['at']) < at]
        paid = sum((Decimal(p['amount']) for p in payments), Decimal('0'))
        pending = Decimal(loan['amount']) - paid
        assert pending >= 0
        outstanding += pending
        if loan['due_date'] < at.date().isoformat() and pending > 0:
            overdue += pending
            evidence.append({'loan_id': loan['loan_id'], 'due_date': loan['due_date'],
                             'amount': loan['amount'], 'observed_payments_before': payments,
                             'paid_before': paid, 'overdue_remaining': pending})
    return overdue, outstanding, evidence


def select_cases(cases):
    selected, log, unavailable = [], [], []
    # Fixed ordering is intentional coverage, not a probability sample.
    strata = [(f'{label}_{kind}', 2, lambda c, l=label, a=abonos:
               c['result']['label'] == l and c['result']['abonos'] == a)
              for label in (0, 1) for kind, abonos in [('un_pago', False), ('abonos', True)]]
    strata += [('unknown', 2, lambda c: c['result']['label'] is None)]
    for name, count, predicate in strata:
        pool = sorted((c for c in cases if predicate(c)), key=lambda c: c['loan_id'])
        available = [c for c in pool if c['loan_id'] not in {x['loan_id'] for x in selected}]
        picks = available[:count]
        selected.extend(picks)
        log.append({'stratum': name, 'available': len(pool), 'ids': [c['loan_id'] for c in picks]})
        if len(picks) < count:
            unavailable.append(name)
    for name, reverse in [('min_amount', False), ('max_amount', True)]:
        pool = sorted(cases, key=lambda c: (Decimal(c['amount']), c['loan_id']), reverse=reverse)
        target = pool[0]
        pick = next((c for c in pool if c['loan_id'] not in {x['loan_id'] for x in selected}), None)
        if pick:
            selected.append(pick)
        else:
            unavailable.append(name)
        log.append({'stratum': name, 'extreme_id': target['loan_id'],
                    'overlap': target in selected[:-1],
                    'ids': [pick['loan_id']] if pick else [],
                    'replacement_rule': 'Next unused neighbor in amount/ID order; max reverses both.'})
    assert len({c['loan_id'] for c in selected}) == len(selected)
    return selected, log, unavailable


def table(headers, rows):
    return ('table', headers, rows)


def render(pages, output):
    from docx import Document
    from docx.shared import Pt, Mm
    from pypdf import PdfReader

    doc = Document()
    section = doc.sections[0]
    section.page_height, section.page_width = Mm(297), Mm(210)
    section.top_margin = section.bottom_margin = Mm(15)
    section.left_margin = section.right_margin = Mm(14)
    style = doc.styles['Normal']
    style.font.name, style.font.size = 'Arial', Pt(10)
    style.paragraph_format.space_after = Pt(5)
    section.footer.paragraphs[0].text = FOOTER
    chunks, markdown = [], []
    for index, (title, blocks) in enumerate(pages):
        if index:
            doc.add_page_break()
        doc.add_heading(title, 1)
        body = '<h1>' + html.escape(title) + '</h1>'
        markdown += ['# ' + title, '']
        for block in blocks:
            if isinstance(block, str):
                doc.add_paragraph(block)
                body += '<p>' + html.escape(block) + '</p>'
                markdown += [block, '']
            else:
                _, headers, rows = block
                t = doc.add_table(rows=1, cols=len(headers))
                t.style = 'Table Grid'
                for cell, text in zip(t.rows[0].cells, headers):
                    cell.text = text
                body += '<table><thead><tr>' + ''.join('<th>' + html.escape(h) + '</th>' for h in headers) + '</tr></thead><tbody>'
                markdown += ['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |']
                for row in rows:
                    for cell, text in zip(t.add_row().cells, row):
                        cell.text = str(text)
                    body += '<tr>' + ''.join('<td>' + html.escape(str(c)).replace('\n', '<br>') + '</td>' for c in row) + '</tr>'
                    markdown += ['| ' + ' | '.join(str(c).replace('\n', '<br>') for c in row) + ' |']
                body += '</tbody></table>'
        chunks.append('<section>' + body + '<footer>' + FOOTER + '</footer></section>')
    doc.save(output / 'Revision_Rildo_V5.docx')
    reopened = Document(output / 'Revision_Rildo_V5.docx')
    assert len(reopened.tables) == sum(isinstance(b, tuple) for _, blocks in pages for b in blocks)
    response_cells = []
    for t, block in zip(reopened.tables, (b for _, blocks in pages for b in blocks if isinstance(b, tuple))):
        response_columns = [i for i, h in enumerate(block[1]) if h in (OPTIONS, 'Correccion')]
        response_cells.extend(row.cells[i].text for row in t.rows[1:] for i in response_columns)
    assert len(response_cells) == 26 and all(text == '' for text in response_cells)
    md = '\n'.join(markdown) + '\n'
    (output / 'Revision_Rildo_V5.md').write_text(md)
    (ROOT / 'docs/APF3_Revision_Muestral_Rildo_V5.md').write_text(md)
    css = '''@page{size:A4;margin:0}*{box-sizing:border-box}body{margin:0;font:10.5pt Arial;color:#17212b}section{width:210mm;height:297mm;padding:15mm 14mm 19mm;position:relative;break-after:page}section:last-child{break-after:auto}h1{font-size:18pt;margin:0 0 7mm}p{line-height:1.3;margin:0 0 4mm}table{border-collapse:collapse;width:100%;table-layout:fixed;margin:3mm 0 5mm;font-size:10pt}th,td{border:1px solid #9ba8b3;padding:2.5mm;vertical-align:top;overflow-wrap:anywhere}th{background:#edf1f3;text-align:left}footer{position:absolute;bottom:10mm;font-size:10pt;color:#4a535c}'''
    (output / 'Revision_Rildo_V5.html').write_text('<!doctype html><html lang="es"><meta charset="utf-8"><style>' + css + '</style><body>' + ''.join(chunks) + '</body></html>')
    renderer = r'''import {pathToFileURL} from 'node:url';
const {chromium}=await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE_PATH).href);
const browser=await chromium.launch({headless:true});
try {
const page=await browser.newPage();
await page.route('**/*', route => route.request().url().startsWith('file:') ? route.continue() : route.abort());
await page.goto(pathToFileURL(process.argv[2]).href);
await page.emulateMedia({media:'print'});
const checks=await page.locator('section').evaluateAll(sections=>sections.map(s=>{
 const footer=s.querySelector('footer').getBoundingClientRect();
 const nodes=[...s.querySelectorAll('h1,p,table')];
 return {overflow:nodes.some(n=>n.getBoundingClientRect().bottom>footer.top),
 minFont:Math.min(...[...s.querySelectorAll('p,td,th,footer')].map(n=>parseFloat(getComputedStyle(n).fontSize)))};
}));
await page.pdf({path:process.argv[3],preferCSSPageSize:true,printBackground:true});
await page.screenshot({path:process.argv[4],fullPage:true});
console.log(JSON.stringify(checks));
} finally {await browser.close();}'''
    (output / 'render-local.mjs').write_text(renderer)
    run = subprocess.run(['node', str(output / 'render-local.mjs'), str(output / 'Revision_Rildo_V5.html'),
                          str(output / 'Revision_Rildo_V5.pdf'), str(output / 'vista-previa.png')],
                         check=True, capture_output=True, text=True)
    checks = json.loads(run.stdout)
    pdf = PdfReader(output / 'Revision_Rildo_V5.pdf')
    assert len(pdf.pages) == len(pages) <= 6
    assert all(not c['overflow'] and c['minFont'] >= 10 * 96 / 72 - 0.01 for c in checks)
    assert all(title in page.extract_text() for (title, _), page in zip(pages, pdf.pages))
    return {'actual_pdf_pages': len(pdf.pages), 'layout': checks, 'docx_reopened': True,
            'docx_blank_response_correction_cells_checked': len(response_cells)}


def build(source, output):
    assert source.resolve() == SOURCE.resolve(), 'Only the frozen DEV V5 directory is allowed'
    assert output.parent.is_dir() and not output.exists(), 'Output must not exist'
    assert not output.resolve().is_relative_to(source.resolve())
    files = sorted(source.iterdir())
    assert len(files) == 12 and all(p.is_file() for p in files)
    before = {p.name: sha(p) for p in files}
    manifest = json.loads((source / 'manifest.json').read_text())['files']
    assert set(manifest) == set(before) - {'manifest.json'}
    assert all(before[n] == h for n, h in manifest.items())
    output.mkdir()
    plan = {'seed': SEED, 'method': 'Intentional predefined coverage; deterministic ID sort, not probability sampling',
            'saved_before_selection': True, 'sources': before,
            'strata': ['2 punctual single', '2 punctual abonos', '2 late single', '2 late abonos',
                       '2 unknown', '1 minimum amount', '1 maximum amount'],
            'overlap_rule': 'Deduplicate; next unused amount/ID neighbor (descending for max)',
            'reject_rule': '2 study overdue refusals per replica, distinct clients within replica, attempt ID order',
            'weeks_rule': '12/9, 11/8..9, 10/8..9, 8/7 or 9/8; minimize combined grants+clients, then replica/date',
            'unavailable_rule': 'Flag missing strata, never fabricate or silently fill',
            'time_estimate_minutes': [15, 25], 'time_measured': False}
    dump(output / 'plan-seleccion.json', plan)
    worlds = [json.loads((source / f'SET5-D{i}_transactions.json').read_text()) for i in (1, 2)]
    rows = list(csv.DictReader((source / 'desarrollo.csv').open()))
    rowmap = {r['loan_id']: r for r in rows}
    cases, rejects, snapshots = [], [], []
    all_loans = []
    for world in worlds:
        cutoff = datetime.combine(date.fromisoformat(world['observed_on']), time.max)
        for loan in world['loans']:
            result = outcome(loan, cutoff)
            all_loans.append({**loan, 'result': result})
            if loan['phase'] != 'study':
                continue
            row = rowmap[loan['loan_id']]
            assert row['late_payment'] == ('' if result['label'] is None else str(result['label']))
            assert Decimal(row['pending_at_cutoff']) == result['pending']
            overdue, outstanding, _ = balance_before(world, loan['client_id'], loan['evaluated_at'])
            assert overdue == 0 and Decimal(row['pending_overdue']) == 0
            assert outstanding == Decimal(row['outstanding'])
            assert Decimal('5') <= Decimal(loan['amount']) <= Decimal('50')
            assert outstanding + Decimal(loan['amount']) <= Decimal('80')
            snapshots.append({'loan_id': loan['loan_id'], 'overdue_before': overdue, 'outstanding_before': outstanding})
            cases.append({**loan, 'result': result, 'outstanding_before': outstanding})
        seen = set()
        for attempt in sorted(world['attempts'], key=lambda a: a['attempt_id']):
            if (attempt['phase'] != 'study' or attempt['granted'] or
                    attempt['refusal_reason'] != 'overdue_balance_not_fully_settled' or attempt['client_id'] in seen):
                continue
            overdue, outstanding, evidence = balance_before(world, attempt['client_id'], attempt['evaluated_at'])
            assert overdue > 0 and evidence
            rejects.append({**attempt, 'overdue_before': overdue, 'outstanding_before': outstanding, 'evidence': evidence})
            seen.add(attempt['client_id'])
            if len(seen) == 2:
                break
    assert len(cases) == len(rows) == 540
    counts = Counter(c['result']['label'] for c in cases)
    assert counts == {0: 434, 1: 96, None: 10}
    selected, log, unavailable = select_cases(cases)
    if len(rejects) != 4:
        unavailable.append('4 rejects / distinct clients')
    audits = json.loads((source / 'development_audits.json').read_text())
    weeks = []
    for audit, world in zip(audits, worlds):
        for week in audit['weekly_stats']:
            attempts = [a for a in world['attempts'] if a['phase'] == 'study' and a['week_start'] == week['week_start']]
            grants = [a for a in attempts if a['granted']]
            actual = {'requests': len(attempts), 'request_clients': len({a['client_id'] for a in attempts}),
                      'grants': len(grants), 'grant_clients': len({a['client_id'] for a in grants})}
            assert all(week[k] == v for k, v in actual.items())
            weeks.append({**week, 'replica_id': world['replica_id']})
    chosen_weeks = []
    for name, predicate in [('habitual', lambda w: (w['grants'], w['grant_clients']) == (12, 9)),
                            ('menor_11', lambda w: w['grants'] == 11 and w['grant_clients'] in (8, 9)),
                            ('menor_10', lambda w: w['grants'] == 10 and w['grant_clients'] in (8, 9)),
                            ('baja_rara', lambda w: (w['grants'], w['grant_clients']) in ((8, 7), (9, 8)))]:
        pool = sorted((w for w in weeks if predicate(w)), key=lambda w: (w['grants'] + w['grant_clients'], w['replica_id'], w['week_start']))
        if pool:
            chosen_weeks.append({**pool[0], 'coverage': name})
        else:
            unavailable.append(name)
    def stats(values):
        return {'min': min(values), 'median': statistics.median(values), 'max': max(values)}
    summary = {'study': len(cases), 'known': counts[0] + counts[1], 'punctual': counts[0],
               'late': counts[1], 'unknown': counts[None],
               'original_late_percent': Decimal(8) / 45 * 100,
               'simulated_late_percent': Decimal(counts[1]) / (counts[0] + counts[1]) * 100,
               'amount_study': stats([Decimal(c['amount']) for c in cases]),
               'amount_all_dev_including_warmup': stats([Decimal(c['amount']) for c in all_loans]),
               'observed_abonos_study': sum(c['result']['abonos'] for c in cases),
               'late_completed_delay_days': stats([c['result']['delay'] for c in cases if c['result']['delay'] is not None and c['result']['delay'] > 0]),
               'weekly_joint_counts': dict(sorted(Counter(f"{w['grants']}/{w['grant_clients']}" for w in weeks).items()))}
    def write_csv(name, records):
        assert all(r['respuesta'] == r['correccion'] == '' for r in records)
        with (output / name).open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    accepted_rows = []
    for c in selected:
        r = c['result']
        accepted_rows.append({'loan_id': c['loan_id'], 'client_id': c['client_id'], 'replica_id': c['replica_id'],
            'fecha': c['evaluated_at'], 'monto': c['amount'], 'vence': c['due_date'],
            'saldo_antes': c['outstanding_before'], 'vencido_antes': '0.00',
            'pagos_observados': '; '.join(p['at'] + ' S/' + p['amount'] for p in r['payments']) or 'Ninguno al corte',
            'pagado': r['paid'], 'pendiente': r['pending'], 'atraso_dias_completo': r['delay'],
            'resultado': 'sin conocer aun' if r['label'] is None else ('tarde' if r['label'] else 'puntual'),
            'abonos_observados': r['abonos'], 'corte': '2026-09-30', 'respuesta': '', 'correccion': ''})
    reject_rows = [{'attempt_id': a['attempt_id'], 'client_id': a['client_id'], 'replica_id': a['replica_id'],
                   'fecha': a['evaluated_at'], 'queria': a['requested_amount'], 'debia_vencido': a['overdue_before'],
                   'evidencia': json.dumps(a['evidence'], default=str), 'respuesta': '', 'correccion': ''} for a in rejects]
    week_rows = [{**w, 'respuesta': '', 'correccion': ''} for w in chosen_weeks]
    write_csv('muestra-fiados.csv', accepted_rows)
    write_csv('muestra-rechazos.csv', reject_rows)
    write_csv('muestra-semanas.csv', week_rows)
    anchors = json.loads((source / 'APF3_OWNER_ANCHORS_V4.json').read_text())
    assert (anchors['late'], anchors['evaluable']) == (8, 45)
    a, b = summary['amount_study'], summary['amount_all_dev_including_warmup']
    pages = [('Revision de situaciones inventadas', [
        'Para Rildo | Fecha de revision: ____________________',
        'Tiempo orientativo: 15-25 minutos, no medido con cronometro. Son 12 fiados, 4 solicitudes rechazadas y 4 semanas; no hace falta leer las 540 filas.',
        'Son posibles situaciones ficticias de negocio: dos historias alternativas (D1 y D2), no operaciones ni pagos reales. Los codigos identifican clientes inventados.',
        'Que se revisa: si estas situaciones se parecen a lo que pasa. No se pide aprobar todos los datos ni autorizar nuevos fiados. Una correccion tambien es una respuesta util.',
        f'Los 540 fiados de estudio tienen 434 pagos puntuales, 96 con atraso y 10 resultados aun desconocidos al 30/09/2026. Entre los 530 conocidos: {summary["simulated_late_percent"]:.2f}% con atraso.',
        f'Referencia declarada por Rildo: 8 de 45 anotaciones evaluables con atraso ({summary["original_late_percent"]:.2f}%). Es recuerdo y revision parcial, no auditoria completa. No se ajustaron los datos para igualar ese porcentaje.',
        f'Montos de estudio (S/): minimo {a["min"]}, mediana {a["median"]}, maximo {a["max"]}. Todo DEV, incluido inicio previo: {b["min"]} / {b["median"]} / {b["max"]}. Limites: S/5-50 por fiado y S/80 de exposicion por cliente.',
        f'Hay {summary["observed_abonos_study"]} fiados de estudio con abonos observados (dos pagos o un pago parcial con saldo). Atraso de los completados tarde: minimo {summary["late_completed_delay_days"]["min"]}, mediana {summary["late_completed_delay_days"]["median"]} y maximo {summary["late_completed_delay_days"]["max"]} dias. No se cuentan planes futuros como pagos.',
        'Un fiado vence al dia siguiente; atraso significa completar despues del vencimiento, separado de los 3 dias de gracia comercial. Un resultado desconocido no es un pago puntual.',
        'Confirmado previamente, no respuesta nueva: la referencia es unos 12 fiados otorgados a 9 clientes distintos por semana; volver entre 3 y 14 dias es volver a SOLICITAR, no intervalo entre fiados otorgados.',
        'Regla previa confirmada: antes de evaluar otro fiado debe haberse pagado toda la deuda vencida. Abonar o acordar no basta. Liquidar permite revisar de nuevo, no aprobar automaticamente.',
        'Fuentes previas: APF3_OWNER_ANCHORS_V4.json y APF3_OWNER_SETTLEMENT_CLARIFICATION.json del manifiesto V5. Las respuestas de esta nueva revision estan todas en blanco.'
    ])]
    for offset in (0, 6):
        blocks = ['Pagos y resultados SOLO de la historia inventada al 30/09/2026. Antes de cada fiado: deuda vencida S/0. Las fechas de pago no son promesas futuras.',
                  'Esto se parece a lo que pasa? Escriba habitual / posible / no / no se en la ultima columna; puede dejarlo en blanco.']
        cells = []
        for i, r in enumerate(accepted_rows[offset:offset + 6], offset + 1):
            cells.append([f'{i}. {r["loan_id"]}\n{r["client_id"]}',
                          f'{r["fecha"][:10]}\nS/{r["monto"]}\nVence {r["vence"]}\nSaldo antes S/{r["saldo_antes"]}',
                          f'{r["pagos_observados"]}\n{r["resultado"]}; pendiente S/{r["pendiente"]}\nDias tarde al completar: {r["atraso_dias_completo"] if r["atraso_dias_completo"] is not None else "no completado"}', ''])
        blocks += [table(['Caso inventado', 'Monto y antes', 'Pagos observados y resultado', OPTIONS], cells),
                   'Correccion (numero de caso y que cambiaria):\n____________________________________________________________\n____________________________________________________________']
        pages.append((f'Fiados inventados {offset + 1} a {min(offset + 6, len(selected))}', blocks))
    reject_cells = []
    for a in rejects:
        evidence = '\n'.join(f'{e["loan_id"]}: S/{e["amount"]}, vence {e["due_date"]}; pagado antes S/{e["paid_before"]}; queda vencido S/{e["overdue_remaining"]}. Pagos: ' +
                             ('; '.join(p['at'] + ' S/' + p['amount'] for p in e['observed_payments_before']) or 'ninguno') for e in a['evidence'])
        reject_cells.append([f'{a["attempt_id"]}\n{a["client_id"]}\n{a["evaluated_at"]}',
                             f'Queria S/{a["requested_amount"]} pero debia vencido S/{a["overdue_before"]}; no se le fio.\n{evidence}', ''])
    pages.append(('Cuatro solicitudes sin nuevo fiado', [
        'Intentos que existen en estas historias inventadas, no clientes reales. Dos por historia y clientes distintos dentro de cada una.',
        'El saldo se reconstruye con pagos observados estrictamente ANTES de evaluar la solicitud; no usa pagos planeados ni posteriores.',
        'Esto se parece a lo que pasa? habitual / posible / no / no se.',
        table(['Intento inventado', 'Que paso y de donde sale el saldo', OPTIONS], reject_cells),
        'Correccion (intento y cambio):\n____________________________________________________________\n____________________________________________________________'
    ]))
    pages.append(('Semanas y supuestos por revisar', [
        'Conteos reales del archivo simulado, comprobados contra los intentos y la auditoria. NO son declaraciones de Rildo ni semanas ya validadas. Fiados y clientes se cuentan por separado.',
        'Esto se parece a lo que pasa? habitual / posible / no / no se.',
        table(['Historia / semana desde', 'Solicitudes / clientes', 'Fiados / clientes', OPTIONS],
              [[w['replica_id'] + '\n' + w['week_start'], f'{w["requests"]} / {w["request_clients"]}', f'{w["grants"]} / {w["grant_clients"]}', ''] for w in chosen_weeks]),
        'No se ocultan los bajos: frecuencias fiados/clientes en las 48 semanas completas: ' + ', '.join(f'{k}: {v}' for k, v in summary['weekly_joint_counts'].items()) + '. Se incluye la combinacion mas baja disponible (8/7 antes que 9/8).',
        'Cada historia usa un grupo fijo de 12 clientes inventados. No se ha medido la poblacion real, la forma de las distribuciones, la variacion entre clientes ni las ventas al contado.',
        table(['Supuesto: Esto se parece a lo que pasa?', OPTIONS, 'Correccion'],
              [['Un grupo fijo de 12 clientes para construir cada historia alternativa', '', ''],
               ['Estos montos, abonos y fechas como situaciones posibles', '', ''],
               ['Estas diferencias entre semanas, incluida la baja de 8/7', '', '']]),
        'La seleccion es intencional para cubrir situaciones distintas, no una muestra probabilistica. Revisar estos ejemplos no valida las 540 filas ni mide precision. No se muestran puntajes ni se entrena ningun modelo.',
        'Fecha de revision: ____________________\nOtra correccion: ______________________________________________',
        'No es acta firmada ni consentimiento de clientes. No hay respuestas nuevas atribuidas a Rildo. Categorias no disponibles: ' + (', '.join(unavailable) or 'ninguna') + '.'
    ]))
    render_checks = render(pages, output)
    after = {p.name: sha(p) for p in files}
    assert before == after
    blank = all(r['respuesta'] == r['correccion'] == '' for r in accepted_rows + reject_rows + week_rows)
    assert blank
    verification = {'seed': SEED, 'plan_sha256': sha(output / 'plan-seleccion.json'),
                    'plan_saved_before_selection': True, 'selection_method': plan, 'selected_strata': log,
                    'selected_ids': [c['loan_id'] for c in selected], 'unavailable': unavailable,
                    'reject_ids': [a['attempt_id'] for a in rejects], 'reject_evidence': rejects,
                    'selected_weeks': chosen_weeks, 'all_weekly_audit_counts_recomputed': True,
                    'computed_summary': summary, 'snapshots_accepted_no_overdue': snapshots,
                    'source_hash_before': before, 'source_hash_after': after,
                    'responses_and_corrections_blank': blank, 'new_review_date_blank': True,
                    'no_models_or_final': True, 'tool_sha256': sha(Path(__file__)), **render_checks}
    dump(output / 'verificacion.json', verification)
    dump(output / 'manifest.json', {'source_hashes': before,
         'outputs': {p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file()},
         'generated_repo_doc': {'path': 'docs/APF3_Revision_Muestral_Rildo_V5.md',
                               'sha256': sha(ROOT / 'docs/APF3_Revision_Muestral_Rildo_V5.md')}})
    print(json.dumps({'output': str(output), 'cases': len(selected), 'rejects': len(rejects),
                      'weeks': len(chosen_weeks), 'summary': summary, **render_checks}, default=str, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    build(args.source, args.output)
