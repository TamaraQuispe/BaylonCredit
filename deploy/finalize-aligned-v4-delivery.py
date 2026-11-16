"""Close the prepared edition, read-only validation first; never run ML or generators.

Run only after all document agents finish and the owner authorizes publication.
Requires python-docx, python-pptx and pypdf. Absolute recorded inputs must exist.
"""

import argparse
import csv
import hashlib
import io
import json
import os
import re
import stat
import sys
import tempfile
from collections import Counter
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path('/Users/tamaraalison/Downloads/APF3_Grupo2_Entrega_V4')
ORIGINAL = Path('/Users/tamaraalison/Downloads/APF3_Grupo2_Alineado_V4')
REPO = Path(__file__).absolute().parents[1]
FINAL_SHA = '86831dabd16b66499afbea6cc7f621c6dba5827367ae2526c788396900872558'
PRIVATE_SHA = '45bc22a10ad5dccf323708b8aeabb780d8de4629ff5087cca2582c7dd055819f'
NAME = 'APF3_TD_Grupo2_ML_Innovacion'
GUIDE = 'APF3_Grupo2_Guion_12min'
CACHES = {'__pycache__', '.cache', '.pytest_cache', '.ruff_cache', '.mypy_cache', 'node_modules'}
TOOLS = ('audit-aligned-v4-data.py', 'benchmark-aligned-v4-demo.py',
         'verify-aligned-v4-entrypoint.py', 'finalize-aligned-v4-delivery.py')
DOCS = ('APF3_Anexos_Cierre_V4.md', 'APF3_Checklist_Presentacion_V4.md')
CRITERIA = ['Escala del negocio', 'Rangos/unidades', 'Consistencia l\u00f3gica/temporal',
            'Relaciones plausibles', 'Se\u00f1al ni nula ni perfecta',
            'Coherencia con APF2', 'Mezcla real+simulado']
OPEN = ['Revision individual aplicada y conformidad del grupo', 'Ensayo cronometrado y demo humana',
        'Acceso efectivo del docente y subida humana al Aula Virtual',
        'Historial IA anterior incompleto; no se certifica literalidad completa',
        'Antes de uso real: base juridica, ARCO, conservacion, costos y piloto autorizado']


def require(condition, message):
    if not condition:
        raise ValueError(message)


def relative(name):
    require(isinstance(name, str) and bool(name), 'Empty/non-string relative path')
    p = PurePosixPath(name)
    require(not p.is_absolute() and '..' not in p.parts and '\\' not in name
            and p.as_posix() == name and name != '.' and '\x00' not in name,
            f'Unsafe relative path: {name!r}')
    return name


def safe(path):
    path = Path(os.path.abspath(path))
    for part in (*reversed(path.parents), path):
        require(not part.is_symlink(), f'Symlink forbidden: {part}')
        require(not part.name.casefold().startswith('.env'), f'Environment file forbidden: {part}')
    lower = path.name.casefold()
    require(not lower.startswith('.env') and not lower.endswith(('.pem', '.key', '.bak', '~'))
            and not any(s in lower for s in ('propietario', 'id_rsa', 'secrets.', 'backup'))
            and lower not in {'credentials', 'credentials.json', 'credentials.yml'},
            f'Private/secret/backup path forbidden: {path}')
    return path


def read(path):
    path = safe(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), f'Not regular: {path}')
        data = stream.read()
    require(sha(data) != PRIVATE_SHA, f'Private owner bytes: {path}')
    require(not re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|'
                          rb'AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}|'
                          rb'sk-(?:proj-|or-v1-)[A-Za-z0-9_-]{20,}', data),
            f'Credential signature: {path}')
    return data


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=True, sort_keys=True) + '\n').encode()


def tree(root):
    require(safe(root).is_dir(), f'Missing directory: {root}')
    files = {}
    for directory, dirs, names in os.walk(root, followlinks=False):
        for name in dirs + names:
            safe(Path(directory, name))
        dirs[:] = sorted(n for n in dirs if n not in CACHES)
        for name in names:
            if name == '.DS_Store' or name.endswith(('.pyc', '.pyo')):
                continue
            path = Path(directory, name)
            files[path.relative_to(root).as_posix()] = read(path)
    return dict(sorted(files.items()))


def hashes(files):
    return {name: sha(data) for name, data in sorted(files.items())}


def check_hashes(base, mapping, external=False, snapshot=None):
    require(isinstance(mapping, dict) and bool(mapping), f'Empty hash map: {base}')
    for name, expected in mapping.items():
        require(isinstance(expected, str) and re.fullmatch('[0-9a-f]{64}', expected)
                and expected != PRIVATE_SHA, f'Invalid/private SHA: {name}')
        path = Path(name)
        require(external or not path.is_absolute(), f'Absolute output path: {name}')
        path = path if external and path.is_absolute() else base / relative(name)
        require(sha(read(path)) == expected, f'SHA mismatch: {path}')
        if snapshot is not None:
            snapshot[safe(path)] = expected


def check_zip(data, mapping, prefix):
    with ZipFile(io.BytesIO(data)) as archive:
        expected = {prefix + relative(n): h for n, h in mapping.items()}
        require(len(archive.namelist()) == len(expected)
                and set(archive.namelist()) == set(expected), 'ZIP inventory differs')
        require(archive.testzip() is None, 'ZIP CRC failure')
        for name, digest in expected.items():
            safe(Path('/zip-inventory') / name)
            require(not stat.S_ISLNK(archive.getinfo(name).external_attr >> 16), 'ZIP symlink')
            content = archive.read(name)
            require(sha(content) != PRIVATE_SHA, f'ZIP private owner bytes: {name}')
            require(sha(content) == digest, f'ZIP SHA mismatch: {name}')


def normalize(text):
    return re.sub(r'\W+', '', text).casefold()


def pdf(data, count, width, height):
    from pypdf import PdfReader

    document = PdfReader(io.BytesIO(data))
    require(not document.is_encrypted and len(document.pages) == count, 'PDF page count/encryption')
    for page in document.pages:
        require(not page.rotation and float(page.get('/UserUnit', 1)) == 1, 'PDF scale/rotation')
        for box in (page.mediabox, page.cropbox):
            require(abs(float(box.width) - width) < 1 and abs(float(box.height) - height) < 1,
                    'PDF dimensions differ')
    return [p.extract_text() or '' for p in document.pages]


def sections(audit, texts, limit):
    require(audit['overflow'] is False and len(audit['sections']) == len(texts), 'Render sections')
    for section, text in zip(audit['sections'], texts, strict=True):
        require(section['overflow'] == [] and 0 < section['height_px'] <= limit, 'Render overflow')
        if 'title' in section:
            require(normalize(section['title']) in normalize(text), 'PDF section title missing')


def validate(root, original, repo, files, inputs):
    def load(name):
        return json.loads(files[name])

    prep = load('manifest-preparacion-entrega.json')
    require(prep['version'] == 'aligned-v4-delivery-preparation-1'
            and prep['source_root'] == str(original) and prep['destination_root'] == str(root),
            'Preparation scope/schema differs')
    for name, record in prep['copied_sources'].items():
        check_hashes(root, {relative(name): record['sha256']})
        check_hashes(root, {record['source']: record['sha256']}, True, inputs)
    check_hashes(root, prep['generated_sha256'])
    original_files = tree(original)
    frozen_global = json.loads(original_files['manifest-entrega.json'])['files']
    require(len(original_files) == 150
            and set(original_files) == set(frozen_global) | {'manifest-entrega.json'},
            'Original global inventory differs')
    check_hashes(original, frozen_global, snapshot=inputs)
    inputs[original / 'manifest-entrega.json'] = sha(original_files['manifest-entrega.json'])
    package = load('manifest-paquete.json')
    require(files['manifest-paquete.json'] == original_files['manifest-paquete.json'],
            'Package drift')
    require(package['version'] == 'aligned-v4-self-contained-1', 'Package schema')
    for folder, key, count in (('codigo', 'code_sha256', 16), ('datos', 'data_sha256', 4),
                               ('experimento', 'experiment_sha256', 24)):
        actual = {n.removeprefix(folder + '/'): sha(d) for n, d in files.items()
                  if n.startswith(folder + '/')}
        require(len(actual) == count and actual == package[key] == prep['frozen_before'][folder]
                == prep['frozen_after'][folder], f'Exact frozen inventory: {folder}')
    require({n: d for n, d in files.items() if n.startswith('reproduccion/')}
            == {n: d for n, d in original_files.items() if n.startswith('reproduccion/')},
            'Reproduction source equivalence differs')
    check_hashes(root, package['support_sha256'])
    provenance = load('experimento/provenance.json')
    for key, name in package['provenance_code_paths'].items():
        require(sha(files['codigo/' + relative(name)]) == provenance['code_sha256'][key],
                f'Code provenance: {key}')
    evidence = load('verificacion-reproduccion.json')
    require(sha(files['verificacion-reproduccion.json']) == FINAL_SHA
            and evidence['passed'] is True,
            'Historical reproduction authority differs')
    for folder in ('experimento', 'reproduccion'):
        check_hashes(root / folder, load(folder + '/artifact_manifest.json'))
        check_hashes(root / folder, load(folder + '/frozen_selection.json')['decision_sha256'])
    for doc, frozen in (('APF3_ALIGNED_V4_PROTOCOL.json', 'protocol.json'),
                        ('APF3_OWNER_ANCHORS_V4.json', 'calibration.json')):
        require(read(repo / 'docs' / doc) == files['experimento/' + frozen],
                f'Protocol/anchors: {doc}')
        inputs[repo / 'docs' / doc] = sha(files['experimento/' + frozen])

    report = load('informe/verificacion-informe-entrega.json')
    manifest = load('informe/manifest-informe-entrega.json')
    require(manifest['sources'] == report['source_sha256'], 'Report source maps differ')
    require({NAME + e for e in ('.pdf', '.docx', '.html', '.md')}
            | {'verificacion-informe-entrega.json'} <= manifest['files'].keys(),
            'Report outputs omitted')
    check_hashes(root / 'informe', manifest['files'])
    check_hashes(root, manifest['sources'], True, inputs)
    check_hashes(root, report['original_package_sha256'], True, inputs)
    require(report['reproduction']['evidence_sha256'] == FINAL_SHA
            and report['reproduction']['evidence_passed'] is True
            and report['reproduction']['verified'] is True
            and report['reproduction']['status']
            == 'technical_reproduction_verified_with_binary_caveat',
            'Report reproduction authority')
    require(report['metric_cells_checked_against_json'] == 224 and report['word_tables'] == 45
            and report['embedded_figures'] == 3 and report['human_review'] == 'pending',
            'Report audit')
    for item in (report, load('sustentacion/plan-sustentacion-entrega.json')):
        require(all(item[k] is False for k in ('new_training', 'new_predictions', 'new_tuning'))
                and item['original_package_unchanged'] is True, 'Document execution invariants')
    physical = report['physical_render']
    total = len(physical['sections'])
    require(physical['body_pages'] == report['planned_body_pages'] == 15
            and physical['body_pages'] <= 15 and physical['a4'] is True
            and total == physical['pdf_total_pages'] == report['planned_total_pages']
            and total == sum(physical[k] for k in ('body_pages', 'cover_pages',
                                                 'references_pages', 'appendix_pages')),
            'Report pagination differs')
    report_texts = pdf(files[f'informe/{NAME}.pdf'], total, 595.28, 841.89)
    sections(physical, report_texts, 259 * 96 / 25.4)
    from docx import Document
    from pptx import Presentation

    word = Document(io.BytesIO(files[f'informe/{NAME}.docx']))
    require(len(word.tables) == 45 and len(word.inline_shapes) == 3, 'Native Word objects')
    require(all(abs(s.page_width.mm - 210) < 1 and abs(s.page_height.mm - 297) < 1
                for s in word.sections), 'Word A4')
    require(all('borrador' not in p.text.casefold() for s in word.sections
                for p in s.header.paragraphs), 'Borrador header remains')
    require('investigaci' in normalize('\n'.join(report_texts))
            and 'pendiente' in normalize('\n'.join(report_texts)), 'Research/human status missing')

    plan = load('sustentacion/plan-sustentacion-entrega.json')
    check_hashes(root, plan['source_sha256'], True, inputs)
    for mapping in plan['protected_sha256'].values():
        check_hashes(root, mapping, True, inputs)
    check_hashes(root / 'sustentacion', plan['output_sha256'])
    require({NAME + e for e in ('.pptx', '.pdf', '.html')}
            | {GUIDE + e for e in ('.pdf', '.docx', '.html', '.md')}
            | {'Guion_completo_con_indicaciones.md'} <= plan['output_sha256'].keys(),
            'Defense outputs omitted')
    notes = plan['slides_data']
    require(plan['edition'] == 'delivery-v4' and plan['slides'] == len(notes) == 13
            and plan['planned_seconds'] == sum(n['seconds'] for n in notes) == 720
            and plan['question_count'] == 18 and plan['spoken_words'] == 1384
            == sum(len(n['spoken'].split()) for n in notes), 'Defense counts/timing')
    require(plan['report_pages'] == {'body': 15, 'total': total}, 'Stale deck report pagination')
    require(plan['selection_cache']['winner']
            == load('experimento/frozen_selection.json')['global_winner']
            and plan['selection_cache']['new_selection'] is False, 'Deck selection cache')
    for family, cached in plan['metrics_cache'].items():
        model = load('experimento/aligned_v4_report.json')['models'][family]
        require(cached['raw_final'] == model['final'] and cached['policy_final']
                == {k: v for k, v in model['review_policy']['final'].items() if k != 'daily'},
                f'Deck metric cache differs: {family}')
    require(plan['human_review'] == plan['human_rehearsal'] == 'pending', 'Human status differs')
    require(plan['spoken_planned_seconds'] == 670
            and plan['slide_9'] == {'spoken_seconds': 20, 'live_seconds': 50}, 'Live demo timing')
    require(plan['demo_readiness']['root_wrapper_sha256'] == sha(files[NAME + '.py']),
            'Deck wrapper')
    owners = Counter()
    full_notes = files['sustentacion/Guion_completo_con_indicaciones.md'].decode()
    for n in notes:
        owners[n['owner']] += n['seconds']
        require(n['notes'] in full_notes and n['spoken_words'] == len(n['spoken'].split()),
                'Notes/word count differ')
    require(dict(owners) == plan['planned_speaker_seconds'], 'Speaker timing')
    require([n['number'] for n in notes] == list(range(1, 14)), 'Notes order')
    require(len(re.findall(r'(?m)^\*\*\u00bf', full_notes)) == 18, 'Expected 18 actual questions')
    deck_texts = pdf(files[f'sustentacion/{NAME}.pdf'], 13, 960, 540)
    guide_texts = pdf(files[f'sustentacion/{GUIDE}.pdf'], 11, 595.28, 841.89)
    for question in re.findall(r'(?m)^\*\*\u00bf[^\n]+', full_notes):
        require(normalize(question) in normalize('\n'.join(guide_texts)), 'Guide question missing')
    for key, texts, limit in (('deck', deck_texts, 720), ('guide', guide_texts, 973)):
        audit = plan['render'][key]
        require(audit['offline'] is True and audit['external_requests'] == []
                and audit['pdf_pages'] == len(texts), 'Defense render audit')
        sections(audit, texts, limit)
    deck = Presentation(io.BytesIO(files[f'sustentacion/{NAME}.pptx']))
    require(len(deck.slides) == 13 and abs(deck.slide_width / 914400 * 72 - 960) < 1
            and abs(deck.slide_height / 914400 * 72 - 540) < 1, 'PPTX slide count/canvas')
    for slide, note, text in zip(deck.slides, notes, deck_texts, strict=True):
        require(slide.has_notes_slide and slide.notes_slide.notes_text_frame.text == note['notes'],
                'PPTX exact notes differ')
        native = []
        for shape in slide.shapes:
            require(shape.left >= 0 and shape.top >= 0
                    and shape.left + shape.width <= deck.slide_width + 2
                    and shape.top + shape.height <= deck.slide_height + 2, 'PPTX bounds')
            if shape.has_text_frame:
                native.extend(p.text for p in shape.text_frame.paragraphs if p.text.strip())
            if shape.has_table:
                native.extend(c.text for row in shape.table.rows
                              for c in row.cells if c.text.strip())
        require(len(native) >= 3 and all(normalize(t) in normalize(text) for t in native),
                'Editable PPTX/PDF text differs')
        require(normalize(note['spoken']) in normalize('\n'.join(guide_texts)),
                'Guide speech missing')

    quality = load('anexos/datos/calidad-dev-v4.json')
    require(quality['source_sha256_before'] == quality['source_sha256_after']
            and quality['frozen_unchanged'] is True, 'Data audit source drift')
    check_hashes(root, quality['source_sha256_before'], True, inputs)
    require([r['criterion'] for r in quality['coherence_criteria']] == CRITERIA,
            'Seven exact criteria')
    relations = quality['relationships']
    require([(r['late'], r['n']) for r in relations['first']] == [(8, 218), (60, 334)]
            and [r['median_sales'] for r in relations['second']] == [8, 13, 21],
            'EDA relationships')
    dictionary = list(csv.DictReader(io.StringIO(
        files['anexos/datos/diccionario-datos.csv'].decode())))
    require(len(dictionary) == 24, 'Dictionary columns')
    check_hashes(repo / 'deploy', {'audit-aligned-v4-data.py': quality['script_sha256']},
                 snapshot=inputs)
    bundle = {n.removeprefix('laboratorio/artefactos/'): d for n, d in files.items()
              if n.startswith('laboratorio/artefactos/')}
    stack = load('anexos/integracion/evidence-stack-v4.json')
    require(len(bundle) == 6 and hashes(bundle) == stack['bundle_before'] == stack['bundle_after']
            and stack['status'] == 'passed', 'Tested six-file bundle')
    check_hashes(root / 'laboratorio/artefactos', json.loads(bundle['web_manifest.json'])['files'])
    mvp_map = {**prep['mvp_source_sha256'], **prep['mvp_generated_sha256']}
    require(len(mvp_map) == 222, 'MVP snapshot count')
    check_zip(files['laboratorio/codigo_fuente_MVP_V4.zip'], mvp_map, 'codigo_fuente_MVP_V4/')
    expected = load('experimento/illustrative_output.json')
    for name, tool in (('latencia-v4.json', 'benchmark-aligned-v4-demo.py'),
                       ('prueba-cli-v4.json', 'verify-aligned-v4-entrypoint.py')):
        record = load('anexos/integracion/' + name)
        require(record['status'] == 'passed' and record['new_training'] is False
                and record['final_inference'] is False, f'Cached evidence: {name}')
        check_hashes(repo / 'deploy', {tool: record['tool_sha256']}, snapshot=inputs)
        result = record.get('result', record)
        require(all(result[k] == expected[k] for k in (
            'probability', 'threshold', 'predicted', 'known_label',
            'research_only', 'business_approval')),
                f'Illustrative result: {name}')
        if name == 'latencia-v4.json':
            require(record['warm_service_calls'] == len(record['samples_ms']) == 30
                    and record['case_id'] == 'illustrative-v4'
                    and record['runtime'] == provenance['runtime']
                    and record['bundle_sha256'] == hashes(bundle), 'Benchmark scope/runtime/bundle')
        else:
            require(record['entrypoint_sha256'] == sha(files[NAME + '.py'])
                    and record['expected_output_sha256']
                    == sha(files['experimento/illustrative_output.json']),
                    'CLI wrapper/output hash')
    return {'report_body_pages': 15, 'report_pdf_pages': total, 'slides': 13,
            'guide_pdf_pages': 11, 'spoken_words': 1384, 'original_files': len(original_files)}


def finalize(root=ROOT, original=ORIGINAL, repo=REPO):
    root, original, repo = map(safe, (root, original, repo))
    require(not root.is_relative_to(original) and not original.is_relative_to(root)
            and not root.is_relative_to(repo) and not repo.is_relative_to(root),
            'Overlapping roots')
    target = root.parent / (root.name + '.zip')
    checksum_path = target.with_suffix('.zip.sha256')
    for path in (target, checksum_path, root / 'manifest-entrega.json',
                 root / 'verificacion-entrega.json'):
        require(not os.path.lexists(path), f'Refusing overwrite: {path}')
    files, inputs = tree(root), {}
    initial = hashes(files)
    counts = validate(root, original, repo, files, inputs)
    original_snapshot = {p.relative_to(original).as_posix(): h for p, h in inputs.items()
                         if p.is_relative_to(original)}
    additions = {}
    for source, destination in (
        *((repo / 'deploy' / n, 'herramientas/' + n) for n in TOOLS),
        *((repo / 'docs' / n, 'anexos/revision/' + n) for n in DOCS),
    ):
        additions[destination] = read(source)
        inputs[source] = sha(additions[destination])
    additions['README.md'] = (
        '# APF3 Grupo 2: Entrega V4\n\n'
        'Edicion preparada y tecnicamente verificada. HUMAN_PENDING: no es cumplimiento integral, '
        'revision aplicada, ensayo ni entrega al docente.\n\n'
        f'- [Informe PDF](informe/{NAME}.pdf) y [Word](informe/{NAME}.docx): '
        f"15 paginas de cuerpo; {counts['report_pdf_pages']} A4 totales.\n"
        f'- [Presentacion editable](sustentacion/{NAME}.pptx) y [PDF](sustentacion/{NAME}.pdf).\n'
        f'- [Guion](sustentacion/{GUIDE}.pdf): 11 A4, 13 intervenciones, 18 preguntas.\n'
        '- [CLI principal y web secundaria](laboratorio/README.md).\n'
        f'- [Wrapper raiz]({NAME}.py) y [dependencias exactas](requirements.txt).\n'
        '- [Fuentes MVP: snapshot secundario](laboratorio/codigo_fuente_MVP_V4.zip).\n'
        '- [Checklist humano](anexos/revision/APF3_Checklist_Presentacion_V4.md).\n'
        '- [Manifiesto global](manifest-entrega.json), '
        '[verificacion](verificacion-entrega.json).\n\n'
        'Entregar archivos por Aula Virtual: subida y acceso docente pendientes, no realizados. '
        'No requiere GitHub publico; no se hizo push ni despliegue.\n'
        'Datos sinteticos, solo investigacion; no aprobacion crediticia ni validacion real. '
        'Historial IA anterior incompleto, sin afirmar registro literal completo.\n'
        'codigo/ conserva 16 originales exactos; datos/ 4, experimento/ 24 y reproduccion/ '
        'son equivalentes a la fuente congelada. No ejecutar reproduccion sobre esta evidencia. '
        'La evidencia historica paso con cinco estados iguales pero Joblib binarios distintos, '
        'tres timestamps y dos hashes derivados exceptuados. No se cargo Joblib ni reejecuto ML.\n'
        'herramientas/ conserva fuentes de auditoria, benchmark y verificacion; no es un bundle '
        'documental portable: rutas originales y dependencias externas siguen siendo necesarias. '
        'El ZIP MVP es snapshot historico veraz, no incluye necesariamente '
        'estas herramientas nuevas.\n'
    ).encode()
    additions['laboratorio/README.md'] = files['laboratorio/README.md'] + (
        '\n## Cierre Tecnico De Esta Edicion\n\n'
        'La prueba CLI guardada paso usando el wrapper raiz exacto; benchmark de 30 llamadas '
        'calientes solo del caso ilustrativo, no HTTP ni SLA. El stack guardado paso; no se '
        'reinicio en el cierre. Demo humana y ensayo siguen pendientes.\n'
        f'Comando desde la raiz: `python -B {NAME}.py --predict-artifact-dir experimento '
        '--input-json experimento/illustrative_input.json '
        '--output-json /tmp/apf3-demo-NUEVA.json`. '
        'Elegir salida inexistente. Requiere Python 3.12.14 y requirements.txt exactos, o Docker '
        'con imagen compatible previamente construida. Imagenes, wheels y venv NO estan en el ZIP. '
        'La web y el ZIP de fuentes MVP son secundarios; no un despliegue publico.\n'
    ).encode()
    overlays = {n: {'old_sha256': initial[n], 'new_sha256': sha(additions[n])}
                for n in ('README.md', 'laboratorio/README.md')}
    for name, data in additions.items():
        require(name in overlays or name not in files or files[name] == data,
                f'Foreign output: {name}')
    publication = {**files, **additions}
    verification = {'version': 'aligned-v4-delivery-finalization-1', 'passed': True,
                    'technical_complete': True, 'human_status': 'HUMAN_PENDING',
                    'human_review': 'pending', 'human_rehearsal': 'pending',
                    'human_demo': 'pending',
                    'aula_virtual_upload': 'pending', 'ai_history_complete': False, 'open': OPEN,
                    'counts': counts, 'final_evidence_sha256': FINAL_SHA, 'overlays': overlays,
                    'ml_executed': False, 'joblib_loaded': False, 'cached_evidence_only': True,
                    'source_zip_scope': 'Historical snapshot, not a fresh export of current repo',
                    'reproduction_caveats': json.loads(files['verificacion-reproduccion.json'])[
                        'methods']['excluded_time_fields'],
                    'derived_hash_exceptions': json.loads(files['verificacion-reproduccion.json'])[
                        'methods']['derived_hash_exceptions'],
                    'joblib_binary_equal': False, 'learned_states_equal': 5,
                    'limits': 'Native Office rendering and human/legal acceptance not certified',
                    'inputs_sha256': {str(p): h for p, h in sorted(inputs.items())}}
    publication['verificacion-entrega.json'] = encoded(verification)
    publication['manifest-entrega.json'] = encoded({
        'version': 'aligned-v4-delivery-finalization-1', 'algorithm': 'sha256',
        'files': hashes(publication), 'excludes_self': 'manifest-entrega.json',
        'technical_complete': True, 'human_status': 'HUMAN_PENDING', 'overlays': overlays,
        'historical_manifests_unchanged': True,
        'excluded': sorted(CACHES) + ['.DS_Store', '*.pyc', '*.pyo'],
    })
    with tempfile.TemporaryDirectory(prefix='.finalize-delivery-', dir=root.parent) as temporary:
        stage = Path(temporary)
        for name, data in publication.items():
            if name in additions or name in ('manifest-entrega.json', 'verificacion-entrega.json'):
                path = stage / relative(name)
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('xb') as stream:
                    stream.write(data)
        candidate = stage / 'delivery.zip'
        with ZipFile(candidate, 'x', ZIP_DEFLATED, compresslevel=9) as archive:
            for name, data in sorted(publication.items()):
                archive.writestr(root.name + '/' + relative(name), data)
        check_zip(read(candidate), hashes(publication), root.name + '/')
        digest = sha(read(candidate))
        with (stage / 'delivery.sha256').open('xb') as stream:
            stream.write(f'{digest}  {target.name}\n'.encode('ascii'))
        require(hashes(tree(root)) == initial, 'Delivery changed during staging')
        check_hashes(root, {str(p): h for p, h in inputs.items()}, True)
        require(hashes(tree(original)) == original_snapshot,
                'Original inventory changed during staging')
        created, replaced = [], []
        try:
            for name in (*additions, 'verificacion-entrega.json', 'manifest-entrega.json'):
                destination = safe(root / name)
                if name in overlays:
                    require(sha(read(destination)) == initial[name],
                            f'Owned README changed: {name}')
                    backup = stage / ('old-' + name.replace('/', '-'))
                    os.link(destination, backup)
                    os.replace(stage / name, destination)
                    replaced.append((destination, backup))
                elif name not in files:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    os.link(stage / name, destination)
                    created.append(destination)
                else:
                    require(read(destination) == publication[name],
                            f'Existing copy changed: {name}')
            require(hashes(tree(root)) == hashes(publication), 'Published root readback differs')
            after_inputs = {str(p): overlays[p.relative_to(root).as_posix()]['new_sha256']
                            if p.is_relative_to(root) and p.relative_to(root).as_posix() in overlays
                            else h for p, h in inputs.items()}
            check_hashes(root, after_inputs, True)
            require(hashes(tree(original)) == original_snapshot, 'Original inventory changed')
            os.link(stage / 'delivery.sha256', checksum_path)
            created.append(checksum_path)
            os.link(candidate, target)
        except BaseException:
            for path in reversed(created):
                path.unlink()
            for destination, backup in reversed(replaced):
                os.replace(backup, destination)
            raise
    return {'zip': str(target), 'sha256': digest, 'files': len(publication),
            'technical_complete': True, 'human_status': 'HUMAN_PENDING'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--original', type=Path, default=ORIGINAL)
    parser.add_argument('--repo', type=Path, default=REPO)
    args = parser.parse_args()
    try:
        print(json.dumps(finalize(args.root, args.original, args.repo), indent=2))
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        print(f'Finalization refused: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
