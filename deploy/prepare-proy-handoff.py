"""Publica copias revisadas del traspaso, sin modificar sus fuentes ni modelos."""

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
from zipfile import ZipFile

ARCHIVES = {
    'APF3_Grupo2.zip': '98825722f03d17b61b6613b7cf02b96f1af69b83ad3357d5049a955b013f9f92',
    'APF3_Grupo2 (1).zip': 'dd2d5d48c46510b3fd58fb915e875e27d63b31605f5f574b78072a58095515b4',
}
GUIDE = 'Guia_Traspaso_PROY_Grupo2_Credify.docx'
GUIDE_SHA = 'f5ec8bedbac95db94650d81a8c04366083d1a2d6860acc2016bfbf878534ef7f'
DOCUMENTS = ('informe/APF3_TD_Grupo2_ML_Innovacion.pdf',
             'sustentacion/APF3_TD_Grupo2_ML_Innovacion.pptx')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def relative(name):
    path = PurePosixPath(name)
    require(name and name != '.' and not path.is_absolute() and '..' not in path.parts
            and '\\' not in name and ':' not in name and path.as_posix() == name,
            f'Ruta insegura: {name}')
    return path


def payload(data):
    files, metadata = {}, 0
    with ZipFile(io.BytesIO(data)) as archive:
        require(archive.testzip() is None, 'CRC invalido')
        require(len(archive.infolist()) < 10000
                and sum(i.file_size for i in archive.infolist()) < 512_000_000, 'ZIP excesivo')
        seen = set()
        for item in archive.infolist():
            name = item.filename.rstrip('/')
            path = relative(name)
            require(name not in seen, f'Miembro duplicado: {name}')
            seen.add(name)
            require(not stat.S_ISLNK(item.external_attr >> 16), 'Symlink no permitido')
            if item.is_dir():
                continue
            if any(p == '__MACOSX' or p == '.DS_Store' or p.startswith('._') for p in path.parts):
                metadata += 1
                continue
            require(not any(p.startswith('.env') or p.endswith(('.key', '.pem', '.dump'))
                            for p in path.parts), f'Archivo privado: {name}')
            content = archive.read(item)
            require(not re.search(rb'(?m)^-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', content),
                    f'Llave privada: {name}')
            files[name] = content
    components = list(zip(*(PurePosixPath(n).parts for n in files)))
    common = []
    for parts in components:
        if len(set(parts)) != 1:
            break
        common.append(parts[0])
    prefix = '/'.join(common) + '/'
    require(bool(common), 'Raiz comun ausente')
    return {n.removeprefix(prefix): content for n, content in files.items()}, metadata, prefix


def prepare(downloads, destination):
    source_bytes = {name: (downloads / name).read_bytes() for name in ARCHIVES}
    require(all(sha(source_bytes[n]) == value for n, value in ARCHIVES.items()), 'ZIP fuente distinto')
    variants = {name: payload(content) for name, content in source_bytes.items()}
    primary = variants['APF3_Grupo2.zip'][0]
    other = variants['APF3_Grupo2 (1).zip'][0]
    require(len(primary) == len(other) == 166 and set(primary) == set(other), 'Inventario inesperado')
    changed = sorted(name for name in primary if primary[name] != other[name])
    require(changed == sorted(DOCUMENTS), 'Diferencias no revisadas')
    records = {}
    for name, (files, metadata, prefix) in variants.items():
        expected = json.loads(files['manifiesto-entrega-actual.json'])['files']
        require(set(expected) == set(files) - {'manifiesto-entrega-actual.json'}, 'Manifiesto incompleto')
        mismatches = sorted(n for n, value in expected.items() if sha(files[n]) != value)
        require(mismatches == ([] if name == 'APF3_Grupo2.zip' else sorted(DOCUMENTS)),
                'Desajustes no revisados')
        records[name] = dict(original_sha256=ARCHIVES[name], content_files=len(files),
                             finder_metadata_members=metadata, original_common_root=prefix,
                             manifest_mismatches=mismatches,
                             official_submission_confirmed=False)
    for name in ('APF3_TD_Grupo2_ML_Innovacion.py', 'APF3_TD_Grupo2_ML_Innovacion.ipynb',
                 'APF3_V6_Final_requirements.txt'):
        require((downloads / name).read_bytes() == primary[name], f'Entrada local diferente: {name}')
    guide = (downloads / GUIDE).read_bytes()
    require(sha(guide) == GUIDE_SHA, 'Guia diferente de la revisada')
    with ZipFile(io.BytesIO(guide)) as archive:
        require(archive.testzip() is None, 'Word corrupto')
    files = {'materiales/' + name: content for name, content in primary.items()}
    files.update({'paquetes/' + name: content for name, content in source_bytes.items()})
    files[GUIDE] = guide
    files['README.md'] = (destination / 'README.md').read_bytes()
    feedback = Path(__file__).resolve().parents[1] / 'entregables/PROY_Grupo2/FEEDBACK_DOCENTE_APF3.md'
    files[feedback.name] = feedback.read_bytes()
    manifest = dict(scope='Copias integras; variantes documentales advertidas, no certificacion del envio oficial',
                    source_variants=records, normalized_payload_changed_paths=changed,
                    files={name: sha(content) for name, content in sorted(files.items())})
    additions = {n: d for n, d in files.items() if n != 'README.md'}
    additions['inventario-traspaso.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    for name in additions:
        path = destination / relative(name)
        require(not path.exists() and not path.is_symlink(), f'No sobrescribir: {path}')
    for name, content in additions.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(content)
    require(all(sha((destination / name).read_bytes()) == value
                for name, value in manifest['files'].items()), 'Copia incorrecta')
    require(all(sha((downloads / name).read_bytes()) == value for name, value in ARCHIVES.items()),
            'Fuente modificada')
    print(json.dumps({'published_files': len(manifest['files']) + 1, 'source_variants': records,
                      'guide_copied': True, 'sources_unchanged': True}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--downloads', type=Path, default=Path.home() / 'Downloads')
    parser.add_argument('--destination', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'entregables/PROY_Grupo2')
    args = parser.parse_args()
    prepare(args.downloads, args.destination)
