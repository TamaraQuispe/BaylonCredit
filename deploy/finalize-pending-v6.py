"""Validate existing V6 evidence and publish once, only with explicit authorization.

No training, generation, inference, Docker, submission or deployment is performed.
Requires the document venv (pypdf, python-docx, python-pptx). The sibling packager
is used only for its read-only schema/comparison functions, never its CLI.
"""

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
import re
import stat
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path('/Users/tamaraalison/Downloads/APF3_Grupo2_Entrega_V6')
ORIGINAL = Path('/Users/tamaraalison/Downloads/APF3_Grupo2_Experimento_V6')
REPO = Path(__file__).absolute().parents[1]
NAME = 'APF3_TD_Grupo2_ML_Innovacion'
GUIDE = 'APF3_Grupo2_Guion_12min'
PRIVATE = {
    '82d4c748b3403e8a3e45b4361b95e9da4ffaf0b0ca21e3a9ac4baedc6040f29b',
    '45bc22a10ad5dccf323708b8aeabb780d8de4629ff5087cca2582c7dd055819f',
}
CACHES = {'__pycache__', '.cache', '.pytest_cache', '.ruff_cache', '.mypy_cache'}
TOOLS = ('package-pending-v6.py', 'package-pending-v6-code.py',
         'verify-pending-v6-demo.py', 'finalize-pending-v6.py',
         'generate-pending-v6-report.py', 'generate-pending-v6-defense.py',
          'generate-apf3-report.py', 'generate-apf3-defense.py', 'slide-renderer.py',
          'templates/pending-v6-entrypoint.py')
CHECKLIST = 'APF3_Checklist_Presentacion_V6.md'
FINAL_NAMES = {'manifest-entrega.json', 'verificacion-entrega.json'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def relative(name):
    require(isinstance(name, str) and bool(name), 'Empty/non-string path')
    path = PurePosixPath(name)
    require(not path.is_absolute() and '..' not in path.parts and ':' not in name
            and '\\' not in name and '\x00' not in name and name != '.'
            and path.as_posix() == name, f'Unsafe path: {name!r}')
    return name


def safe(path):
    path = Path(os.path.abspath(path))
    for part in (*reversed(path.parents), path):
        require(not part.is_symlink(), f'Symlink forbidden: {part}')
        lower = part.name.casefold()
        require(not lower.startswith('.env') and lower not in
                {'credentials', 'credentials.json', 'secrets.json', 'id_rsa', 'id_ed25519'}
                and not lower.endswith(('.pem', '.key')), f'Secret path: {part}')
    return path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def scan(data, name):
    require(sha(data) not in PRIVATE, f'Private owner bytes: {name}')
    require(not re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----|'
                          rb'AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}|'
                          rb'sk-(?:proj-|or-v1-)[A-Za-z0-9_-]{20,}', data),
            f'Secret signature: {name}')
    # Scan native Office members too, not just the compressed container.
    if str(name).lower().endswith(('.docx', '.pptx', '.zip')):
        with ZipFile(io.BytesIO(data)) as archive:
            require(archive.testzip() is None, f'Archive CRC: {name}')
            for item in archive.infolist():
                relative(item.filename.rstrip('/'))
                safe(Path('/archive-scan') / item.filename)
                require(not stat.S_ISLNK(item.external_attr >> 16), 'Archive symlink')
                if not item.is_dir():
                    scan(archive.read(item), item.filename)


def read(path):
    path = safe(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), f'Not regular: {path}')
        data = stream.read()
    scan(data, path)
    return data


def tree(root):
    require(safe(root).is_dir(), f'Missing directory: {root}')
    files = {}
    for directory, dirs, names in os.walk(root, followlinks=False):
        for name in dirs + names:
            safe(Path(directory, name))
        dirs[:] = sorted(n for n in dirs if n not in CACHES)
        for name in sorted(names):
            if name == '.DS_Store' or name.endswith(('.pyc', '.pyo')):
                continue
            path = Path(directory, name)
            files[relative(path.relative_to(root).as_posix())] = read(path)
    return files


def hashes(files):
    return {n: sha(d) for n, d in sorted(files.items())}


def encoded(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2,
                       allow_nan=False) + '\n').encode()


def load(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f'Duplicate JSON key: {key}')
            result[key] = value
        return result

    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda value: require(False, f'Nonfinite JSON: {value}'))


def check_hashes(files, mapping, names=None):
    require(isinstance(mapping, dict) and bool(mapping), 'Empty hash map')
    if names is not None:
        require(set(mapping) == set(names), 'Manifest keys mismatch')
    for name, digest in mapping.items():
        relative(name)
        require(isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest),
                f'Invalid SHA: {name}')
        require(name in files and sha(files[name]) == digest, f'SHA mismatch: {name}')


def subset(files, folder):
    return {n.removeprefix(folder + '/'): d for n, d in files.items()
            if n.startswith(folder + '/')}


def all_true(value):
    return bool(value) and all(all_true(v) if isinstance(v, dict) else v is True
                               for v in value.values())


def package_helper(repo):
    path = repo / 'deploy/package-pending-v6.py'
    read(path)
    spec = importlib.util.spec_from_file_location('v6_readonly_schema', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize(text):
    return re.sub(r'\W+', '', unicodedata.normalize('NFKD', text)
                  .encode('ascii', 'ignore').decode()).casefold()


def pdf(data, count, width, height):
    from pypdf import PdfReader

    document = PdfReader(io.BytesIO(data))
    require(not document.is_encrypted and len(document.pages) == count, 'PDF page count')
    for page in document.pages:
        require(not page.rotation and float(page.get('/UserUnit', 1)) == 1, 'PDF rotation/scale')
        for box in (page.mediabox, page.cropbox):
            require(abs(float(box.width) - width) < 1 and abs(float(box.height) - height) < 1,
                    'PDF dimensions')
    return [page.extract_text() or '' for page in document.pages]


def check_sources(root, repo, mapping, inputs, local_alias=False):
    require(isinstance(mapping, dict) and bool(mapping), 'Missing source map')
    for name, digest in mapping.items():
        if local_alias and name.startswith('fuente-local/'):
            leaf = relative(name.removeprefix('fuente-local/'))
            path = repo / 'deploy' / leaf if leaf.endswith('.py') else root.parent / leaf
        elif Path(name).is_absolute():
            path = Path(name)
            require(path.is_relative_to(root) or path.is_relative_to(repo),
                    f'Unrecognized external source: {name}')
        else:
            path = root / relative(name)
        require(isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest)
                and sha(read(path)) == digest, f'Source SHA mismatch: {name}')
        inputs[path] = digest


def validate_documents(root, repo, files, inputs):
    from docx import Document
    from pptx import Presentation

    report = load(files['informe/verificacion-informe-v6.json'])
    manifest = load(files['informe/manifest-informe-v6.json'])
    require(manifest['source_read_sha256'] == report['source_read_sha256'], 'Report source maps')
    check_hashes(files, manifest['files'])
    check_sources(root, repo, manifest['source_read_sha256'], inputs, True)
    require(report['passed'] is True and report['body_pages'] == 15
            and report['total_pages'] == report['planned_pages'] == 33
            and report['tables_metric_cells_checked'] == 312
            and report['integration_measurement_cells_checked'] == 30
            and report['negative_control_metric_detected'] is True
            and report['all_native_tables_equal_markdown'] is True
            and report['integration_sources_unchanged'] is True
            and report['experiment_unchanged'] is True
            and report['private_word_copied'] is False
            and report['fit_calls'] == report['predict_calls'] ==
            report['dataset_generation_calls'] == 0, 'Report audit')
    base = 'informe/' + NAME
    require(sha(files[base + '.md']) == manifest['source_markdown_sha256'], 'Markdown SHA')
    texts = pdf(files[base + '.pdf'], 33, 595.28, 841.89)
    require(len(report['layout']) == 33, 'Report layout count')
    for section, text in zip(report['layout'], texts, strict=True):
        require(section['text_overflow'] == [] and 0 < section['height'] <= 940
                and normalize(section['title']) in normalize(text), 'Report overflow/title')
    word = Document(io.BytesIO(files[base + '.docx']))
    require(len(word.tables) == report['documents']['word_tables']
            and len(word.inline_shapes) == report['documents']['embedded_figures'] == 3,
            'Native report tables/figures')
    require(all('borrador' not in normalize(p.text) for s in word.sections
                for p in s.header.paragraphs), 'Draft header')
    markdown = files[base + '.md'].decode()
    md_tables = []
    for block in markdown.split('\n\n'):
        lines = block.strip().splitlines()
        if len(lines) >= 2 and lines[0].startswith('|') and re.match(r'^\|[ :|-]+\|$', lines[1]):
            md_tables.append([[normalize(c.strip()) for c in line.strip('|').split('|')]
                              for line in [lines[0], *lines[2:]]])
    require([[[normalize(c.text) for c in row.cells] for row in t.rows]
             for t in word.tables] == md_tables, 'Native tables differ from Markdown')
    pdf_text = normalize('\n'.join(texts))
    require(all(normalize(c.text) in pdf_text for t in word.tables
                for row in t.rows for c in row.cells), 'Report PDF table cells')

    plan = load(files['sustentacion/plan-sustentacion-v6.json'])
    spoken_words = sum(len(note['spoken'].split()) for note in plan['slides_data'])
    require(type(plan['spoken_words']) is int and plan['spoken_words'] == spoken_words
            and 1250 <= spoken_words <= 1450, 'Defense spoken word count/range')
    require(plan['edition'] == 'pending-v6' and plan['slides'] == 13
            and plan['planned_seconds'] == 720
            and plan['question_count'] == 18 and plan['human_checklist_count'] == 4
            and plan['human_review'] == plan['human_rehearsal'] == 'pending'
            and plan['roles'] == 'proposed' and plan['business_validated'] is False
            and plan['demo']['human_demo'] == 'pending'
            and all(plan[k] is False for k in ('new_training', 'new_predictions', 'new_tuning',
                                              'runtime_generation', 'private_word_copy')),
            'Defense plan/human scope')
    require(plan['source_sha256'] == plan['source_sha256_after'], 'Defense source drift')
    check_sources(root, repo, plan['source_sha256'], inputs)
    check_hashes(subset(files, 'sustentacion'), plan['output_sha256'],
                 set(subset(files, 'sustentacion')) - {'plan-sustentacion-v6.json'})
    deck = Presentation(io.BytesIO(files['sustentacion/' + NAME + '.pptx']))
    require(len(deck.slides) == 13 and len(plan['slides_data']) == 13, 'Native slide count')
    require(abs(deck.slide_width / 9525 - 1280) < 1
            and abs(deck.slide_height / 9525 - 720) < 1, 'PPTX dimensions')
    slide_texts = pdf(files['sustentacion/' + NAME + '.pdf'], 13, 960, 540)
    guide_texts = pdf(files['sustentacion/' + GUIDE + '.pdf'], 11, 595.28, 841.89)
    require(sum(n['seconds'] for n in plan['slides_data']) == 720, 'Timing sum')
    for slide, note, text in zip(deck.slides, plan['slides_data'], slide_texts, strict=True):
        require(slide.notes_slide.notes_text_frame.text == note['notes'], 'PPTX notes mismatch')
        native_texts = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                native_texts.append(shape.text)
            if shape.has_table:
                native_texts.extend(c.text for row in shape.table.rows for c in row.cells)
        require(native_texts and all(normalize(t) in normalize(text) for t in native_texts),
                'Editable native slide text/table differs from PDF')
        require(all(normalize(p) in normalize('\n'.join(guide_texts))
                    for p in note['spoken'].split('\n\n')), 'Guide spoken content')
    for kind, count in (('deck', 13), ('guide', 11)):
        render = plan['render'][kind]
        require(render['pdf_pages'] == count and len(render['sections']) == count,
                'Defense render count')
        require(render['text_overflow'] == render['element_bounds_errors'] == 0
                and render['external_requests'] == [] and render['offline'] is True,
                'Defense overflow/offline')
        for section in render['sections']:
            require(section['errors'] == [], 'Defense text overflow')
    require(files['sustentacion/Guion_completo_con_indicaciones.md'] ==
            read(repo / 'docs/APF3_Guion_Sustentacion_V6.md'), 'Full defense source/notes')
    model_report = load(files['experimento/pending_v6_report.json'])
    require(plan['selection_cache'] == {'winner': model_report['selection']['global_winner'],
                                        'new_selection': False}, 'Defense winner cache')
    for family, metrics in plan['metrics_cache'].items():
        require(metrics == {'raw': {s: model_report['models'][family][s]
                                    for s in ('train', 'oof', 'final')},
                            'policy': model_report['models'][family]['review_policy']},
                'Defense metrics cache')
    return {'report_pages': 33, 'body_pages': 15, 'slides': 13, 'guide_pages': 11}


def validate(root, original, repo, files, inputs):
    package = load(files['manifest-paquete.json'])
    require(package['version'] == 'pending-v6-delivery-1'
            and package['original_experiment_path'] == str(original), 'Package schema/path')
    original_files = tree(original)
    require(len(original_files) == 57, 'Original count must be 57')
    check_hashes(original_files, package['original_experiment_sha256'], original_files)
    require(subset(files, 'experimento') == original_files, 'Original/experiment bytes')
    counts = {'experimento': 57, 'codigo': 21, 'datos': 3,
              'fuentes-dev': 12, 'protocolo-modelado': 10}
    require(set(package['folders']) == set(counts), 'Package folder keys')
    for folder, count in counts.items():
        actual = subset(files, folder)
        require(len(actual) == count, f'Frozen folder count: {folder}')
        check_hashes(actual, package['folders'][folder], actual)
    for folder in ('fuentes-dev', 'protocolo-modelado'):
        actual = subset(files, folder)
        check_hashes(actual, load(actual['manifest.json'])['files'], set(actual) - {'manifest.json'})
    support = {'manifest-codepack.json', 'requirements.txt', 'reproducir-v6.py',
               NAME + '.py', 'resumen-v6.json'}
    support_without_wrapper = {k: v for k, v in package['support_sha256'].items()
                               if k != NAME + '.py'}
    check_hashes(files, support_without_wrapper, support_without_wrapper)
    # The delivery entry point is deliberately overlaid with input-domain validation.
    # It is bound to the current trusted inference evidence below, not to the old stub.
    original_wrapper_sha256 = package['support_sha256'][NAME + '.py']
    require(re.fullmatch(r'[0-9a-f]{64}', original_wrapper_sha256), 'Wrapper overlay record')
    for source, target in ((repo / 'deploy/templates/pending-v6-entrypoint.py', NAME + '.py'),
                           (repo / 'backend/app/services/academic_v6_policy.py', 'v6_policy.py')):
        content = read(source)
        inputs[source] = sha(content)
        require(files[target] == content, f'Pre-model policy source mismatch: {target}')
    codepack = load(files['manifest-codepack.json'])
    check_hashes(subset(files, 'codigo'), codepack['files'], subset(files, 'codigo'))
    check_sources(repo / 'backend', repo, codepack['source_sha256'], inputs)
    helper = package_helper(repo)
    require(sha(files['codigo/scripts/academic_credit_pending_v6.py']) == helper.RUNNER_SHA,
            'Frozen runner drift')
    for folder in ('experimento', 'reproduccion'):
        actual = subset(files, folder)
        require(len(actual) == 57, f'Experiment count: {folder}')
        # Complete maps are checked independently before the packager's semantic checks.
        check_hashes(actual, load(actual['artifact_manifest.json']), helper.ARTIFACTS)
        check_hashes(actual, load(actual['frozen_selection.json'])['decision_sha256'],
                     helper.DECISIONS)
        check_hashes(actual, load(actual['freeze_before_final.json'])['files'], helper.FREEZE_FILES)
        helper.validate_artifacts(root / folder)
        provenance = load(actual['provenance.json'])
        check_hashes(subset(files, 'codigo'), provenance['code_sha256'])
    evidence = load(files['verificacion-reproduccion.json'])
    require(sha(files['verificacion-reproduccion.json']) ==
            '1cf558dae08b71b7eafa9a603b60d9be0279bd48dd0a5e0c43dbe6d971f0a61d'
            and evidence['passed'] is True and all_true(evidence['checks'])
            and evidence['joblib_binary_equal'] is True
            and evidence['binary_serialization_caveat'] is False, 'Reproduction checks')
    require(len(evidence['checks']['exact_file_sha256']) == 47
            and len(evidence['checks']['raw']) == len(evidence['checks']['policy']) == 12,
            'Reproduction comparison counts')
    deterministic = set(original_files) - helper.VOLATILE - {
        m + '.joblib' for m in (*helper.MODELS, 'selected_model')}
    require(set(evidence['checks']['exact_file_sha256']) == deterministic,
            'Exact deterministic comparison keys')
    for name in evidence['checks']['exact_file_sha256']:
        require(files['experimento/' + relative(name)] == files['reproduccion/' + name],
                f'Deterministic bytes differ: {name}')
    for model in (*helper.MODELS, 'selected_model'):
        name = model + '.joblib'
        require(files['experimento/' + name] == files['reproduccion/' + name], 'Model bytes differ')
        record = evidence['artifact_serialization'][model]
        require(record['binary_equal'] is True and record['binary_sha256'] ==
                [sha(files['experimento/' + name])] * 2, 'Recorded serialization SHA')
    expected = load(files['experimento/pending_v6_report.json'])
    actual = load(files['reproduccion/pending_v6_report.json'])
    require(all_true(helper.compare_reports(expected, actual)), 'Actual report/metric comparison')
    helper.validate_environment(evidence['environment'], expected['provenance']['runtime'])
    for name in ('entorno-reproduccion.json', 'entorno-verificacion.json'):
        helper.validate_environment(load(files[name]), expected['provenance']['runtime'])
    example = load(files['experimento/illustrative_output.json'])
    cli_example = {k: v for k, v in example.items()
                   if k not in ('distinctness_pass', 'requested_amount_pen')}
    for name in ('inferencia-original.json', 'inferencia-reproduccion.json'):
        require(load(files[name]) == cli_example, 'Actual illustrative JSON differs')
    require(example['probability'] == 0.7171978005286032 and example['threshold'] == 0.2
            and example['predicted'] == 1 and example['known_label'] is None
            and example['business_approval'] is False, 'Illustrative scope')
    summary = load(files['resumen-v6.json'])
    require(all(expected['selection']['global_winner'][k] == v
                for k, v in summary['global_winner'].items()), 'Winner cache')
    for family in helper.MODELS:
        for split in helper.SPLITS:
            require(summary['models'][family]['raw'][split] == expected['models'][family][split],
                    'Summary raw metrics')
            cached = summary['models'][family]['policy'][split]
            require(all(expected['models'][family]['review_policy'][split][k] == v
                        for k, v in cached.items()), 'Summary policy metrics')
    final = expected['models']['tree']['review_policy']['final']
    require(final['metrics']['f2'] == 0.44891640866873067 and final['reviews'] == 193
            and final['reviews_known'] == 191 and final['reviews_unknown'] == 2
            and final['metrics']['confusion_matrix'] == [[81, 162], [4, 29]]
            and final['daily_max'] == 5 and final['days_over_before_cap'] == 0
            and expected['models']['constant_1']['review_policy']['final']['metrics']['f2']
            == 0.4074074074074074, 'Frozen final outcome')
    require(load(files['experimento/final_call_ledger.json']) ==
            {m: {'batch_calls': 1, 'rows_scored': 280, 'unknown_rows_scored': 4}
             for m in helper.MODELS}, 'External final batch ledger')
    dictionary = load(files['anexos/datos/diccionario-v6.json'])
    require(len(dictionary['header']) == len(dictionary['columns']) == 24
            and [c['variable'] for c in dictionary['columns']] == dictionary['header'],
            'Dictionary schema/count')
    for name, total, zero, one in (('desarrollo.csv', 545, 454, 87), ('final.csv', 280, 243, 33)):
        reader = csv.DictReader(io.StringIO(files['datos/' + name].decode()))
        rows = list(reader)
        require(reader.fieldnames == dictionary['header'] and len(rows) == total
                and Counter(r['late_payment'] for r in rows) == {'0': zero, '1': one, '': 4},
                'CSV schema/counts/classes')
        require(all(r['origen'] == 'simulado' and all(float(r[k]) == 0 for k in
                    ('pending_overdue', 'pending_current', 'outstanding', 'utilization',
                     'overdue_rate')) for r in rows), 'CSV simulated/pending scope')
    review = load(files['experimento/owner_review.json'])
    require([review['sample'][k] for k in ('fiados_reviewed', 'rejections_reviewed',
                                         'weeks_reviewed', 'assumptions_reviewed')] == [12, 4, 4, 3]
            and review['not_business_model_approval'] is True, 'Owner sample scope')
    cli = load(files['anexos/integracion/prueba-cli-v6.json'])
    latency = load(files['anexos/integracion/latency-v6.json'])
    require(cli['passed'] is latency['passed'] is True
            and cli['tool_sha256'] == sha(read(repo / 'deploy/verify-pending-v6-demo.py'))
            and cli['wrapper_sha256'] == sha(files[NAME + '.py'])
            and cli['policy_sha256'] == sha(files['v6_policy.py'])
            and cli['pre_model_guards_verified'] is True
            and cli['expected_output_sha256'] == sha(files['experimento/illustrative_output.json'])
            and cli['human_demo'] == 'pending' and cli['experiment_unchanged'] is True,
            'CLI evidence/schema/tool')
    require(latency['warm_calls'] == len(latency['samples_ms']) == 30
            and latency['illustrative_result'] == cli_example
            and all(v['new_training'] is False and v['final_prediction'] is False
                    for v in (cli, latency)), 'Latency scope')
    require(latency['experiment_sha256_before'] == latency['experiment_sha256_after']
            == hashes(original_files), 'Integration frozen inventory')
    documents = validate_documents(root, repo, files, inputs)
    return {'technical_complete': True, 'scope': 'artefacts and existing fixed-procedure reproduction',
            'entrypoint_overlay': {'historical_sha256': original_wrapper_sha256,
                                   'current_sha256': sha(files[NAME + '.py']),
                                    'reason': 'Adds tested input validation and shared pre-model debt/history guards; frozen runner, models and experiment unchanged'},
            'human_status': 'PENDIENTE', 'business_approval': False,
            'submission': False, 'commit': False, 'push': False, 'public_deployment': False,
            'new_fit_calls': 0, 'new_generation_calls': 0, 'new_prediction_calls': 0,
            'original_sha256': hashes(original_files), 'documents': documents,
            'limits': ['Owner review: 23 intentional V5 sample items, not all 545 V6 rows',
                        'V6 CLI and authenticated synthetic web lab are not commercial validation',
                       'Latency and process RSS are local illustrations, not an SLA',
                       'Technical hashes do not certify model quality or human acceptance']}


def check_zip(data, mapping, prefix):
    relative(prefix.rstrip('/'))
    with ZipFile(io.BytesIO(data)) as archive:
        expected = {prefix + relative(n): h for n, h in mapping.items()}
        require(len(archive.namelist()) == len(expected)
                and set(archive.namelist()) == set(expected), 'ZIP inventory mismatch')
        require(archive.testzip() is None, 'ZIP CRC failure')
        for item in archive.infolist():
            relative(item.filename)
            safe(Path('/zip-scan') / item.filename)
            require(not stat.S_ISLNK(item.external_attr >> 16), 'ZIP symlink')
            content = archive.read(item)
            scan(content, item.filename)
            require(sha(content) == expected[item.filename], 'ZIP SHA mismatch')


def finalize(root=ROOT, original=ORIGINAL, repo=REPO, archive_path=None):
    root, original, repo = (safe(p) for p in (root, original, repo))
    require(not root.is_relative_to(original) and not original.is_relative_to(root), 'Overlapping roots')
    archive_path = safe(archive_path) if archive_path is not None else root.parent / (root.name + '.zip')
    digest_path = archive_path.with_suffix('.zip.sha256')
    for path in (archive_path, digest_path, *(root / n for n in FINAL_NAMES)):
        require(not safe(path).exists(), f'Already exists: {path}')
    before = tree(root)
    inputs = {}
    verification = validate(root, original, repo, before, inputs)
    additions = {}
    for tool in TOOLS:
        source = repo / 'deploy' / tool
        data = read(source)
        inputs[source] = sha(data)
        additions['anexos/herramientas/' + tool] = data
    checklist = read(repo / 'docs' / CHECKLIST)
    inputs[repo / 'docs' / CHECKLIST] = sha(checklist)
    additions['anexos/revision/' + CHECKLIST] = checklist
    deployment_source = repo / 'deploy/review-pending-v6-policy-deployment.json'
    deployment = read(deployment_source)
    inputs[deployment_source] = sha(deployment)
    additions['anexos/integracion/despliegue-reglas-v6.json'] = deployment
    require(not set(additions) & set(before), 'Overlay would overwrite existing files')
    links = [('Informe PDF', 'informe/' + NAME + '.pdf'),
             ('Informe editable', 'informe/' + NAME + '.docx'),
             ('Presentacion editable', 'sustentacion/' + NAME + '.pptx'),
             ('Presentacion PDF', 'sustentacion/' + NAME + '.pdf'),
             ('Guion de 12 minutos', 'sustentacion/' + GUIDE + '.pdf'),
             ('Entrada CLI local', NAME + '.py'), ('Dependencias', 'requirements.txt'),
             ('Ejemplo ficticio', 'experimento/illustrative_input.json'),
             ('Reproduccion documentada', 'reproducir-v6.py'),
             ('Codigo academico', 'manifest-codepack.json'),
             ('Checklist humano pendiente', 'anexos/revision/' + CHECKLIST)]
    block = '\n\n## Entrega tecnica V6; revision humana PENDIENTE\n\n'
    block += '\n'.join(f'- [{label}]({path})' for label, path in links)
    block += ('\n\nCierre tecnico de artefactos y reproduccion existente, no aceptacion humana, '
               'validacion empresarial ni envio. Demo web V6 sintetica; produccion comercial sin cambios. '
              'Herramientas documentales copiadas como fuentes, sin afirmar portabilidad completa. '
              'No se entreno, genero ni predijo al finalizar.\n')
    additions['README.md'] = before['README.md'] + block.encode()
    verification['readme_overlay'] = {'old_sha256': sha(before['README.md']),
                                      'new_sha256': sha(additions['README.md']),
                                      'historical_manifest_preserved': True}
    additions['verificacion-entrega.json'] = encoded(verification)
    expected = before | additions
    manifest = {'version': 'pending-v6-final-delivery-1', 'human_status': 'PENDIENTE',
                'technical_complete': True, 'files': hashes(expected),
                'excludes': ['manifest-entrega.json', 'caches and Python bytecode'],
                'historical_package_manifest_sha256': sha(before['manifest-paquete.json'])}
    additions['manifest-entrega.json'] = encoded(manifest)
    expected |= additions
    for _, path in links:
        require(path in expected, f'Missing index target: {path}')

    # Stage every byte, including the verified ZIP, before touching delivery files.
    created = []
    directories = []
    readme_replaced = False
    with tempfile.TemporaryDirectory(prefix='.pending-v6-stage-', dir=root.parent) as temp:
        stage = Path(temp)
        for index, data in enumerate(additions.values()):
            (stage / str(index)).write_bytes(data)
        zipped = io.BytesIO()
        with ZipFile(zipped, 'w', ZIP_DEFLATED) as archive:
            for name, data in sorted(expected.items()):
                archive.writestr(root.name + '/' + relative(name), data)
        archive_bytes = zipped.getvalue()
        check_zip(archive_bytes, hashes(expected), root.name + '/')
        (stage / 'archive').write_bytes(archive_bytes)
        (stage / 'digest').write_bytes((sha(archive_bytes) + '  ' + archive_path.name + '\n').encode())
        (stage / 'old-readme').write_bytes(before['README.md'])

        def unchanged():
            require(hashes(tree(original)) == verification['original_sha256'], 'Original changed')
            for path, digest in inputs.items():
                require(sha(read(path)) == digest, f'Input changed: {path}')

        unchanged()
        require(tree(root) == before, 'Delivery changed during staging')
        try:
            for index, (name, data) in enumerate(additions.items()):
                target = safe(root / relative(name))
                missing = []
                parent = target.parent
                while not parent.exists():
                    missing.append(parent)
                    parent = parent.parent
                for parent in reversed(missing):
                    parent.mkdir()
                    directories.append(parent)
                if name == 'README.md':
                    require(read(target) == before[name], 'README concurrently changed')
                    os.replace(stage / str(index), target)
                    readme_replaced = True
                else:
                    os.link(stage / str(index), target)
                    created.append((target, data))
            require(tree(root) == expected, 'Published directory differs from staged bytes')
            unchanged()
            for source, target, data in ((stage / 'archive', archive_path, archive_bytes),
                                         (stage / 'digest', digest_path, (stage / 'digest').read_bytes())):
                os.link(source, safe(target))  # Atomic, fails if another writer created the destination.
                created.append((target, data))
            unchanged()
        except BaseException:
            for path, data in reversed(created):
                if path.exists() and not path.is_symlink() and read(path) == data:
                    path.unlink()
            if readme_replaced and read(root / 'README.md') == additions['README.md']:
                os.replace(stage / 'old-readme', root / 'README.md')
            for directory in reversed(directories):
                try:
                    directory.rmdir()
                except OSError:
                    pass
            raise
    return {'zip': str(archive_path), 'sha256': sha(archive_bytes), 'human_status': 'PENDIENTE'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--original', type=Path, default=ORIGINAL)
    parser.add_argument('--repo', type=Path, default=REPO)
    parser.add_argument('--archive-path', type=Path,
                        help='Write only a new authorized archive; never overwrites an existing one')
    parser.add_argument('--authorized-finalize', action='store_true',
                        help='Use only after explicit human authorization')
    args = parser.parse_args()
    if not args.authorized_finalize:
        parser.error('Explicit authorization required')
    print(json.dumps(finalize(args.root, args.original, args.repo,
                              args.archive_path), indent=2))


if __name__ == '__main__':
    main()
