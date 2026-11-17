"""Normaliza nombres autorizados y verifica la entrega actual sin entrenar modelos."""

import argparse
import ast
import csv
from datetime import UTC, datetime
import hashlib
import io
import json
from pathlib import Path
import re
from xml.etree import ElementTree
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = (
    ('informe/APF3_TD_Grupo2_ML_Innovacion (4).pdf',
     'informe/APF3_TD_Grupo2_ML_Innovacion.pdf',
     'f45e719ee1c069bcce7779bf2def27ad621571360a63380e42e40694f8fff405'),
    ('sustentacion/APF3_Sustentacion_Grupo2_.pptx',
     'sustentacion/APF3_TD_Grupo2_ML_Innovacion.pptx',
     'f31ca299ce1f799f2a69666bd223e2f663aa9446685d75dffcd9e32f0034316e'),
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    require(path.is_file() and not path.is_symlink(), f'Archivo no regular: {path}')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def checked_relative(name):
    path = Path(name)
    require(not path.is_absolute() and '..' not in path.parts, f'Ruta insegura: {name}')
    return path


def check_map(root, mapping):
    require(bool(mapping), 'Manifiesto vacio')
    for name, expected in mapping.items():
        require(digest(root / checked_relative(name)) == expected, f'Hash distinto: {name}')


def normalize_names():
    # Preflight de ambos documentos antes de renombrar cualquiera.
    pending = []
    for original, canonical, expected in DOCUMENTS:
        source, target = ROOT / original, ROOT / canonical
        require(not (source.exists() and target.exists()), f'Dos versiones presentes: {canonical}')
        current = source if source.exists() else target
        require(digest(current) == expected, f'Contenido del documento modificado: {current.name}')
        if current == source:
            pending.append((source, target))
    for source, target in pending:
        require(not target.exists(), f'Destino existente: {target}')
        source.rename(target)
    return {canonical: digest(ROOT / canonical) for _, canonical, _ in DOCUMENTS}


def verify():
    from pypdf import PdfReader

    document_hashes = {}
    for _, canonical, expected in DOCUMENTS:
        require(digest(ROOT / canonical) == expected, f'Documento distinto: {canonical}')
        document_hashes[canonical] = expected
    pdf = PdfReader(ROOT / DOCUMENTS[0][1])
    texts = [page.extract_text() or '' for page in pdf.pages]
    reference_page = next(i for i, text in enumerate(texts)
                          if re.search(r'^\s*Referencias\s*$', text, re.MULTILINE))
    body_pages = reference_page - 1
    require(len(pdf.pages) == 22 and body_pages <= 15, 'Extension del informe fuera de limite')
    with ZipFile(ROOT / DOCUMENTS[1][1]) as archive:
        slides = [name for name in archive.namelist()
                  if re.fullmatch(r'ppt/slides/slide\d+\.xml', name)]
        require(len(slides) == 13, 'Numero de diapositivas incorrecto')
        for name in slides:
            ElementTree.fromstring(archive.read(name))

    for folder, name in (('development', 'development_manifest.json'),
                         ('experiment', 'final_manifest.json')):
        manifest = load(ROOT / folder / name)['files']
        check_map(ROOT / folder, manifest)
        actual = {p.name for p in (ROOT / folder).iterdir()
                  if p.is_file() and p.name not in (name, '.DS_Store')}
        require(actual == set(manifest), f'Inventario experimental distinto: {folder}')
    historical = dict(load(ROOT / 'support/manifest-support.json')['files'])
    reproduction_hash = historical.pop('REPRODUCCION.md')
    require(digest(ROOT / 'anexos/historial-metadatos/REPRODUCCION-original.md') == reproduction_hash,
            'Receta historica original no preservada')
    check_map(ROOT, historical)
    dictionary = load(ROOT / 'datos/diccionario.json')
    require(len(dictionary['columns']) == 24, 'Diccionario incompleto')
    require(sum(c['predictor'] for c in dictionary['columns']) == 11, 'Predictores incorrectos')
    for name, record in dictionary['files'].items():
        copied, source = ROOT / 'datos' / checked_relative(name), ROOT / checked_relative(record['source'])
        require(digest(copied) == digest(source) == record['sha256'], f'CSV alterado: {name}')
        rows = list(csv.DictReader(io.StringIO(copied.read_text())))
        require(len(rows) == record['rows'] and all(r['origen'] == 'simulado' for r in rows),
                f'Conteos u origen incorrectos: {name}')
    script = ROOT / 'APF3_TD_Grupo2_ML_Innovacion.py'
    source = script.read_text()
    ast.parse(source)
    notebook = load(ROOT / 'APF3_TD_Grupo2_ML_Innovacion.ipynb')
    code = [''.join(c['source']) for c in notebook['cells'] if c['cell_type'] == 'code']
    guard = '\nif __name__ == "__main__":\n    main()\n'
    require(source.endswith(guard) and code[0].rstrip() == source[:-len(guard)].rstrip(),
            'Codigo notebook distinto')
    require('main([])' in code[1], 'Notebook no ejecuta el procedimiento completo')
    for cell in code:
        ast.parse(cell)
    require('matplotlib==3.11.2' in source, 'Dependencia grafica obligatoria ausente')
    annex = load(ROOT / 'anexos/manifiesto-complemento.json')
    check_map(ROOT / 'anexos', annex['output_sha256'])
    gates = load(ROOT / 'anexos/pruebas-reglas-previas.json')
    # La estructura detallada de las pruebas se conserva en el anexo, sin cargar ML.
    require(len(gates['checks']) == 7 and all(c['passed'] is True for c in gates['checks']),
            'Pruebas de reglas incompletas o fallidas')
    require(gates['source_sha256'] == digest(ROOT / gates['source']), 'Fuente de reglas distinta')
    replay_root = ROOT / 'anexos/ejecucion-codigo'
    replay = load(replay_root / 'registro-ejecucion.json')
    check_map(replay_root, replay['files'])
    require(replay['training_executed'] is True and replay['independent_evaluation'] is False,
            'Alcance incorrecto de reproduccion')
    require(replay['selected_family_threshold_params_match'] is True
            and replay['all_families_train_oof_final_classification_metrics_match'] is True,
            'Seleccion o metricas de clasificacion distintas en reproduccion')
    manifest_path = ROOT / 'manifiesto-entrega-actual.json'
    if manifest_path.exists():
        check_map(ROOT, load(manifest_path)['files'])
    return {
        'scope': 'Integridad de la carpeta actual y cobertura de archivos; no nueva validacion predictiva',
        'display_name': 'V6 Final', 'revision_id': 'v6-final-r1',
        'checks_passed': True, 'pdf_pages': len(pdf.pages), 'pdf_body_pages': body_pages,
        'slides': len(slides), 'document_content_sha256': document_hashes,
        'original_pdf_and_ppt_content_unchanged': True,
        'frozen_experiment_and_data_unchanged': True,
        'script_notebook_syntax_and_source_match': True,
        'local_replay_evidence_hashes_checked': True,
        'local_replay_has_reported_floating_point_differences': bool(replay['numerical_differences']),
        'annex_outputs_and_sources': 'Ver anotaciones de preservacion en manifiesto-complemento.json',
        'human_review_project': 'Realizada por los cuatro integrantes segun confirmacion del grupo',
        'new_supplement_review': 'Requiere cotejo final del grupo',
        'not_verified': ['Cuenta/ejecucion en Google Colab', 'Ensayo de 12 minutos',
                         'Participacion durante sustentacion', 'Carga y plazo en Aula Virtual'],
        'historical_record': 'verificacion-v6-final.json conserva el estado de una entrega anterior, no certifica los documentos actuales',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--normalizar-nombres', action='store_true')
    parser.add_argument('--registrar', action='store_true', help='Crear registro y manifiesto nuevos')
    args = parser.parse_args()
    if args.normalizar_nombres:
        print(json.dumps(normalize_names(), indent=2))
        return
    result = verify()
    if args.registrar:
        verification = ROOT / 'verificacion-entrega-actual.json'
        manifest = ROOT / 'manifiesto-entrega-actual.json'
        require(not verification.exists() and not manifest.exists(), 'Registros actuales ya existentes')
        result['recorded_utc'] = datetime.now(UTC).isoformat()
        verification.write_text(json.dumps(result, indent=2, ensure_ascii=True) + '\n')
        files = {}
        for path in sorted(ROOT.rglob('*')):
            relative = path.relative_to(ROOT)
            if path.is_file() and path != manifest and '.DS_Store' not in relative.parts:
                require('__pycache__' not in relative.parts and not path.is_symlink(),
                        f'Archivo no entregable: {relative}')
                files[relative.as_posix()] = digest(path)
        manifest.write_text(json.dumps({'scope': 'Carpeta actual completa; excluye auto-hash y Finder',
                                        'files': files}, indent=2) + '\n')
        verify()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
