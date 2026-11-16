"""Prepare a new delivery from frozen bytes; never finalize, run ML or publish."""

import argparse
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

REPO = Path(__file__).absolute().parents[1]
SOURCE = Path('/Users/tamaraalison/Downloads/APF3_Grupo2_Alineado_V4')
ROOT = Path('/Users/tamaraalison/Downloads/APF3_Grupo2_Entrega_V4')
# macOS /var is a system symlink; use its canonical parent, not relaxed checks.
EVIDENCE = Path('/private/var/folders/sx/_6ljw37n2_j9hk2f_vtqplj40000gn/T/opencode/v4-stack-check/credify-v4-check-1794709952020-9aaf9d76')
FINAL_SHA = '86831dabd16b66499afbea6cc7f621c6dba5827367ae2526c788396900872558'
PRIVATE_SHA = '45bc22a10ad5dccf323708b8aeabb780d8de4629ff5087cca2582c7dd055819f'
SUPPORT = (
    'requirements.txt', 'reproducir-v4.py', 'manifest-paquete.json',
    'verificacion-reproduccion.json', 'estado-artefactos.json',
    'entorno-empaquetado.json', 'entorno-reproduccion.json',
    'entorno-verificacion.json', 'comandos-reproduccion.json',
    'inferencia-original.json', 'inferencia-reproduccion.json',
    *(f'reproduccion-comando-{i}.log' for i in range(1, 4)),
)
CACHES = {'__pycache__', '.cache', '.pytest_cache', '.ruff_cache', '.mypy_cache', 'node_modules'}
CONFIGS = (
    '.dockerignore', 'Dockerfile', 'nginx.conf', 'index.html',
    'package.json', 'package-lock.json', 'vite.config.ts',
    'tsconfig.json', 'tsconfig.app.json', 'tsconfig.node.json',
    'eslint.config.js', 'postcss.config.js', 'tailwind.config.js',
    'docker-compose.demo.yml', 'docker-compose.academic-v4.yml',
    'backend/Dockerfile', 'backend/.dockerignore', 'backend/pyproject.toml',
    'backend/alembic.ini', 'deploy/Dockerfile.academic-v4',
    'deploy/requirements-academic-v4.txt', 'deploy/prepare-aligned-v4-lab.py',
    'deploy/start-demo.sh', 'deploy/smoke-aligned-v4-api.py',
    'deploy/test-aligned-v4-stack.mjs', 'deploy/test-aligned-v4-ui.mjs',
)
NEW_FILES = {
    'backend/app/api/routes/academic_ml_v4.py',
    'backend/app/services/academic_lab_v4.py',
    'backend/app/ml/owner_aligned_synthetic.py',
    'backend/scripts/academic_credit_aligned_v4.py',
    'backend/tests/test_academic_lab_v4.py',
    'backend/tests/test_aligned_v4_experiment.py',
    'backend/tests/test_owner_aligned_synthetic.py',
    'src/pages/LaboratorioAlineadoV4Page.tsx',
}
WRAPPER = 'APF3_TD_Grupo2_ML_Innovacion.py'
MANIFEST = 'manifest-preparacion-entrega.json'
REFRESHABLE = {WRAPPER, 'README.md', 'laboratorio/README.md', MANIFEST}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe(path):
    path = Path(os.path.abspath(path))
    for part in (*reversed(path.parents), path):
        require(not part.is_symlink(), f'Symlink forbidden: {part}')
    return path


def read(path):
    path = safe(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), f'Not regular: {path}')
        return stream.read()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=True, sort_keys=True) + '\n').encode()


def relative(name):
    path = PurePosixPath(name)
    require(not path.is_absolute() and '..' not in path.parts and path.as_posix() == name
            and name != '.' and '\\' not in name, f'Unsafe name: {name}')
    return name


def tree(folder):
    result = {}
    require(safe(folder).is_dir(), f'Missing directory: {folder}')
    for directory, dirs, files in os.walk(folder, followlinks=False):
        for name in dirs + files:
            safe(Path(directory, name))
        for name in files:
            path = Path(directory, name)
            result[path.relative_to(folder).as_posix()] = read(path)
    return dict(sorted(result.items()))


def hashes(files):
    return {name: sha(data) for name, data in sorted(files.items())}


def clean_source(name, data):
    parts = PurePosixPath(relative(name)).parts
    lower = name.casefold()
    require(not any(p in CACHES or p.startswith('.env') for p in parts), f'Excluded: {name}')
    require(not lower.endswith(('.pyc', '.pyo', '.pem', '.key', '.sqlite', '.db', '.docx', '.pdf'))
            and not any(word in lower for word in ('ficha_propietario', 'id_rsa', 'secrets.'))
            and parts[-1].casefold() not in {'credentials', 'credentials.json', 'credentials.yml'},
            f'Private/cache file: {name}')
    require(sha(data) != PRIVATE_SHA, f'Private owner bytes: {name}')
    require(not re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|'
                          rb'AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}|'
                          rb'sk-(?:proj-|or-v1-)[A-Za-z0-9_-]{20,}', data),
            f'Credential signature: {name}')


def prepare(source, root, repo, evidence, previous_manifest_sha256=None):
    source, root, repo, evidence = map(safe, (source, root, repo, evidence))
    require(source.is_dir() and root.is_dir() and repo.is_dir() and evidence.is_dir(),
            'All parent/source/destination directories must already exist')
    require(not root.is_relative_to(source) and not source.is_relative_to(root)
            and not root.is_relative_to(repo) and not repo.is_relative_to(root), 'Overlapping roots')
    previous = None
    if previous_manifest_sha256 is not None:
        previous_bytes = read(root / MANIFEST)
        require(sha(previous_bytes) == previous_manifest_sha256, 'Previous manifest SHA differs')
        previous = json.loads(previous_bytes)
        require(previous['version'] == 'aligned-v4-delivery-preparation-1'
                and previous['destination_root'] == str(root)
                and previous['source_root'] == str(source), 'Previous preparation scope differs')
    package_bytes = read(source / 'manifest-paquete.json')
    package = json.loads(package_bytes)
    require(package['version'] == 'aligned-v4-self-contained-1', 'Wrong package')
    original = {folder: tree(source / folder)
                for folder in ('codigo', 'datos', 'experimento', 'reproduccion')}
    before = {folder: hashes(files) for folder, files in original.items()}
    require(len(package['experiment_sha256']) == 24, 'Expected 24 frozen files')
    for folder, key in (('codigo', 'code_sha256'), ('datos', 'data_sha256'),
                        ('experimento', 'experiment_sha256')):
        require(before[folder] == package[key], f'Frozen inventory differs: {folder}')
    provenance = json.loads(original['experimento']['provenance.json'])
    for key, name in package['provenance_code_paths'].items():
        require(before['codigo'][relative(name)] == provenance['code_sha256'][key],
                f'Original code provenance differs: {key}')
    support = {name: read(source / name) for name in SUPPORT}
    for name, expected in package['support_sha256'].items():
        require(name in support and sha(support[name]) == expected, f'Support SHA: {name}')
    require(sha(support['verificacion-reproduccion.json']) == FINAL_SHA
            and json.loads(support['verificacion-reproduccion.json'])['passed'] is True,
            'Final reproduction evidence differs')
    require(all('==' in line for line in support['requirements.txt'].decode().splitlines()
                if line and not line.startswith('#')), 'Requirements not pinned')

    outputs, source_records, generated = {}, {}, {}

    def copy(path, name, data=None):
        relative(name)
        data = read(path) if data is None else data
        require(name not in outputs, f'Duplicate output: {name}')
        outputs[name] = data
        source_records[name] = {'source': str(path), 'sha256': sha(data)}

    def generate(name, data):
        require(name not in outputs, f'Duplicate generated output: {name}')
        outputs[name] = data.encode() if isinstance(data, str) else data
        generated[name] = sha(outputs[name])

    for folder, files in original.items():
        for name, data in files.items():
            copy(source / folder / name, f'{folder}/{name}', data)
    for name, data in support.items():
        copy(source / name, name, data)
    for old, new in (('evidence.json', 'evidence-stack-v4.json'),
                     ('desktop.png', 'desktop-stack-v4.png'), ('mobile.png', 'mobile-stack-v4.png')):
        copy(evidence / old, f'anexos/integracion/{new}')
    stack = json.loads(outputs['anexos/integracion/evidence-stack-v4.json'])
    bundle = tree(repo / 'academic/v4')
    require(len(bundle) == 6 and hashes(bundle) == stack['bundle_before'] == stack['bundle_after'],
            'Expected exact six-file tested runtime bundle')
    web_manifest = json.loads(bundle['web_manifest.json'])
    require(web_manifest['files'] == {name: before['experimento'][name] for name in bundle
                                    if name != 'web_manifest.json'}, 'Web/frozen hashes differ')
    for name, data in bundle.items():
        copy(repo / 'academic/v4' / name, f'laboratorio/artefactos/{name}', data)
    for name in CONFIGS:
        copy(repo / name, 'laboratorio/' + name)
    copy(repo / 'deploy/templates/aligned-v4-entrypoint.py', WRAPPER)

    # A refresh retains the already delivered ZIP snapshot, never exports concurrent work.
    if previous is not None:
        zip_name = 'laboratorio/codigo_fuente_MVP_V4.zip'
        zip_bytes = read(root / zip_name)
        require(sha(zip_bytes) == previous['generated_sha256'][zip_name], 'MVP ZIP changed')
        baseline = previous['mvp_baseline_commit']
        source_inventory = previous['mvp_source_sha256']
        with ZipFile(io.BytesIO(zip_bytes)) as archive:
            require(archive.testzip() is None, 'Snapshot ZIP CRC failure')
            expected = {**source_inventory, **previous['mvp_generated_sha256']}
            require(len(archive.namelist()) == len(expected)
                    and set(archive.namelist()) == {'codigo_fuente_MVP_V4/' + name for name in expected},
                    'Snapshot ZIP inventory differs')
            source_code = {}
            for name, expected_sha in expected.items():
                relative(name)
                data = archive.read('codigo_fuente_MVP_V4/' + name)
                require(sha(data) == expected_sha, f'Snapshot SHA differs: {name}')
                source_code[name] = data
        archive_readme = source_code['README-ENTREGA-V4.md']
    else:
        zip_bytes, baseline, source_inventory, source_code, archive_readme = build_source_zip(repo, bundle)
    generate('laboratorio/codigo_fuente_MVP_V4.zip', zip_bytes)
    generate('laboratorio/README.md', LAB_README)
    generate('README.md', ROOT_README)
    manifest = {
        'version': 'aligned-v4-delivery-preparation-1', 'stage': 'preparation-only',
        'source_root': str(source), 'destination_root': str(root),
        'copied_sources': source_records, 'generated_sha256': generated,
        'mvp_baseline_commit': baseline, 'mvp_source_sha256': source_inventory,
        'mvp_generated_sha256': {'README-ENTREGA-V4.md': sha(archive_readme)},
        'mvp_source_paths': (previous['mvp_source_paths'] if previous is not None else
                             {name: str(repo / name) for name in source_inventory}),
        'frozen_before': before, 'frozen_after': before,
        'academic_code_exact_original_inventory': True,
        'original_manifest_unchanged': True, 'original_provenance_checked': True,
        'web_bundle_exact_six_files': True, 'source_zip_crc_and_bytes_checked': True,
        'final_zip_created': False, 'ml_executed': False, 'human_review': 'pending',
        'global_manifest_created': False,
        'scope': 'Own copied/generated files only; report, defense and other agents excluded',
    }
    generate(MANIFEST, encoded(manifest))
    # Only explicitly owned outputs may refresh, and only from recorded old bytes.
    old_hashes = {} if previous is None else {
        **{name: record['sha256'] for name, record in previous['copied_sources'].items()},
        **previous['generated_sha256'], MANIFEST: previous_manifest_sha256,
    }
    for folder in original:
        if (root / folder).exists():
            actual = hashes(tree(root / folder))
            require(all(before[folder].get(name) == digest for name, digest in actual.items()),
                    f'Destination original inventory differs: {folder}')
    existing = {}
    for name, data in outputs.items():
        destination = safe(root / relative(name))
        if destination.exists():
            existing[name] = read(destination)
            require(existing[name] == data or (name in REFRESHABLE
                    and sha(existing[name]) == old_hashes.get(name)),
                    f'Refusing overwrite: {destination}')
        parent = destination.parent
        while not parent.exists():
            parent = parent.parent
        require(parent.is_dir(), f'Not a parent directory: {parent}')
    created = skipped = refreshed = 0
    for name, data in outputs.items():
        destination = safe(root / name)
        if name in existing:
            require(read(destination) == existing[name], f'Destination changed: {name}')
            if existing[name] == data:
                skipped += 1
                continue
            with destination.open('wb') as stream:
                stream.write(data)
            refreshed += 1
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('xb') as stream:
                stream.write(data)
            created += 1
        require(read(destination) == data, f'Copy readback differs: {name}')
    for folder in original:
        require(hashes(tree(source / folder)) == before[folder], f'Frozen source changed: {folder}')
        require(hashes(tree(root / folder)) == before[folder], f'Destination inventory differs: {folder}')
    require(read(source / 'manifest-paquete.json') == package_bytes, 'Source manifest changed')
    for name, data in support.items():
        require(read(source / name) == data, f'Source support changed: {name}')
    for record in source_records.values():
        require(sha(read(record['source'])) == record['sha256'], 'Copy source changed during preparation')
    if previous is None:
        for name, expected in source_inventory.items():
            require(sha(read(repo / name)) == expected, f'MVP source changed during preparation: {name}')
    return {'root': str(root), 'created': created, 'refreshed': refreshed, 'identical_skipped': skipped,
            'owned_files': len(outputs), 'copied_files': len(source_records),
            'mvp_zip_files': len(source_code), 'owned_bytes': sum(map(len, outputs.values())),
            'frozen_files_checked_before_after': 24, 'academic_code_files': len(before['codigo']),
            'final_zip_created': False, 'manifest_sha256': sha(outputs[MANIFEST])}


def build_source_zip(repo, bundle):
    tracked = set(subprocess.check_output(['git', 'ls-files', '-z'], cwd=repo).decode().split('\0')) - {''}
    prefixes = ('backend/app/', 'backend/scripts/', 'backend/tests/', 'backend/alembic/', 'src/', 'public/')
    selected = {name for name in tracked if name.startswith(prefixes)} | set(CONFIGS) | NEW_FILES
    # Only this V4 fixture tree is accepted untracked, never arbitrary repo files.
    fixture = repo / 'backend/tests/fixtures'
    if fixture.is_dir():
        selected.update('backend/tests/fixtures/' + name for name in tree(fixture)
                        if name.endswith('.json'))
    source_code = {}
    for name in sorted(selected):
        data = read(repo / relative(name))
        clean_source(name, data)
        source_code[name] = data
    for name, data in bundle.items():
        source_code['academic/v4/' + name] = data
    baseline = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    source_inventory = hashes(source_code)
    archive_readme = (
        '# Codigo fuente MVP con integracion V4\n\n'
        f'Baseline del repositorio: {baseline}. Snapshot de trabajo, no commit publicado.\n'
        'Incluye app backend completa, migraciones, frontend, tests y configuracion local.\n'
        'No requiere GitHub publico. No incluye .env, dependencias instaladas, DB ni imagenes.\n'
        'El modelo operativo v1 versionado se conserva solo como dependencia del MVP;\n'
        'no es el modelo academico V4 ni evidencia de entrenamiento V4.\n'
        'Los scripts historicos versionados son contexto del MVP, no resultados V4.\n'
        'Para iniciar V4 seguir laboratorio/README.md de la entrega.\n'
    ).encode()
    source_code['README-ENTREGA-V4.md'] = archive_readme
    buffer = io.BytesIO()
    with ZipFile(buffer, 'w', ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(source_code.items()):
            info = ZipInfo('codigo_fuente_MVP_V4/' + name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    with ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        require(archive.testzip() is None, 'Internal source ZIP CRC failure')
        require(len(archive.namelist()) == len(source_code), 'Source ZIP inventory differs')
        for name, data in source_code.items():
            require(archive.read('codigo_fuente_MVP_V4/' + name) == data, f'ZIP mismatch: {name}')
    return buffer.getvalue(), baseline, source_inventory, source_code, archive_readme


ROOT_README = '''# APF3 Grupo 2: Entrega V4

Estado: SOLO PREPARACION. Revision humana, ensayo y demo humana pendientes.
No se ha creado el ZIP final ni un manifiesto global de cierre.

## Indice Principal

- [Informe PDF](informe/APF3_TD_Grupo2_ML_Innovacion.pdf) y [Word](informe/APF3_TD_Grupo2_ML_Innovacion.docx): generacion/revision documental pendiente por su agente.
- [Sustentacion](sustentacion/): preparacion/revision por su agente, no certificada aqui.
- [Anexos](anexos/): datos y documentos a cargo de sus agentes; no modificados por esta preparacion salvo las tres copias de integracion.
- [Demo local CLI y web](laboratorio/README.md).
- [Codigo completo del MVP V4](laboratorio/codigo_fuente_MVP_V4.zip), accesible sin GitHub publico.
- [Entrypoint academico](APF3_TD_Grupo2_ML_Innovacion.py).
- [Verificacion historica de reproduccion](verificacion-reproduccion.json).
- [Manifiesto original](manifest-paquete.json) y [preparacion](manifest-preparacion-entrega.json).

## Alcance Y Entrega

Entregar archivos directamente por Aula Virtual; no se necesita publicar una URL nueva.
Las referencias GitHub anteriores corresponden solo a CV3, no a esta version actual.
La demo principal es CLI local con Python 3.12.14 y dependencias exactas instaladas;
tambien se documenta una alternativa Docker offline con imagen preparada. La web necesita iniciar
su stack; las capturas son evidencia de una prueba anterior ya detenida, no de un
servicio ejecutandose ahora. No se realizo despliegue publico ni push.

codigo/, datos/, experimento/ y reproduccion/ preservan los bytes originales;
el wrapper esta fuera de codigo/, en la raiz. codigo/ conserva exactamente sus
16 archivos originales y reproducir-v4.py verify no necesita excepciones de inventario.
El manifiesto original NO se reescribe. Volver a ejecutar verify requiere el entorno
Docker/venv original y puede actualizar evidencias: usar una copia de trabajo.
Para una nueva reproduccion usar otra copia de trabajo sin salidas
previas, nunca la fuente congelada ni esta evidencia de entrega.

Datos 100% sinteticos; solo investigacion, no validacion real ni aprobacion crediticia.
No se distribuye el formulario privado del propietario. Los hashes verifican
integridad, no identidad del publicador. Los Joblib solo deben cargarse si se confia
en su procedencia. Cinco estados aprendidos coinciden en la verificacion historica,
pero sus binarios Joblib difieren; se conservan las tres excepciones de tiempo y
los dos hashes derivados documentados en la evidencia, sin recalcular ML.
'''

LAB_README = '''# Laboratorio V4

## Demo Principal: CLI Local

Desde la raiz de la entrega, usar Python 3.12.14 y un entorno virtual aislado con
todas las dependencias de requirements.txt instaladas en sus versiones exactas.
La evidencia original se obtuvo en Linux ARM64; otra plataforma no queda certificada.

```sh
python3.12 -m venv /tmp/apf3-v4-demo-venv
/tmp/apf3-v4-demo-venv/bin/python -m pip install -r requirements.txt
/tmp/apf3-v4-demo-venv/bin/python -B APF3_TD_Grupo2_ML_Innovacion.py --help
/tmp/apf3-v4-demo-venv/bin/python -B APF3_TD_Grupo2_ML_Innovacion.py --predict-artifact-dir experimento --input-json experimento/illustrative_input.json --output-json /tmp/apf3-v4-inferencia-nueva.json
```

Elegir un output-json inexistente. El wrapper delega todos los argumentos al runner
original y no entrena salvo que se invoque explicitamente su modo de entrenamiento.
La preparacion no ejecuta esta inferencia ni instala dependencias. Para trabajar
offline preparar previamente wheels compatibles y usar pip --no-index --find-links.
No se incluyen wheels, interprete, imagenes Docker ni caches de compilacion.
requirements.txt conserva las versiones fijadas originales, incluido pip.

## Alternativa CLI: Docker Offline

Requiere la imagen API V4 ya construida localmente (credify-demo-academic-api:v4),
Python 3.12.14 y dependencias cientificas exactas en esa imagen. No descarga nada:
--pull never impide pulls y --network none desactiva la red. La imagen contiene app,
pero NO el runner academico. Se ejecuta el runner original montado desde la entrega;
PYTHONPATH apunta al codigo aislado, no al inicializador operativo de /app.
Desde la raiz, elegir previamente una carpeta de salida nueva:

```sh
mkdir /tmp/apf3-v4-cli-output
docker run --rm --pull never --network none --read-only --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp:rw,noexec,nosuid --env PYTHONDONTWRITEBYTECODE=1 --env PYTHONPATH=/package/codigo --workdir /package/codigo --mount "type=bind,src=$PWD/codigo,dst=/package/codigo,readonly" --mount "type=bind,src=$PWD/experimento,dst=/package/experimento,readonly" --mount type=bind,src=/tmp/apf3-v4-cli-output,dst=/output --entrypoint python credify-demo-academic-api:v4 -B /package/codigo/scripts/academic_credit_aligned_v4.py --predict-artifact-dir /package/experimento --input-json /package/experimento/illustrative_input.json --output-json /output/inferencia.json
```

La inferencia carga solo artefactos confiables y no entrena. No se ha ejecutado
esta alternativa durante la preparacion ni se certifica una demo humana realizada.

## Web Secundaria

Descomprimir codigo_fuente_MVP_V4.zip en una carpeta nueva. Incluye el backend app
completo con alembic/pyproject, frontend src y puntos de entrada, pruebas, Docker,
Compose y el bundle academic/v4 (seis archivos exactos). No son fragmentos aislados.
Los archivos sueltos de configuracion en laboratorio/ son referencias byte exactas;
el contexto de build es la carpeta completa extraida, no laboratorio/.

Desde codigo_fuente_MVP_V4/ extraido:

```sh
export JWT_SECRET_KEY="$(openssl rand -hex 32)"
docker compose -p apf3-v4-local -f docker-compose.demo.yml -f docker-compose.academic-v4.yml up --build -d
```

Acceder a http://localhost:8081, docente@example.com / DemoAPF2-2026! (credenciales
ficticias locales del demo). Liberar el puerto antes o elegir otro proyecto/puerto
mediante una configuracion local; no detener servicios ajenos. Para detener solo
este proyecto usar los mismos -p y -f con down. No ejecutar contra produccion.
Las imagenes/dependencias necesitan preparacion y red inicial; caches e imagenes
existentes pueden ahorrar build, pero no se garantiza su disponibilidad al docente.
La app conserva el modelo operativo v1 versionado por dependencia de imports del
MVP; no se usa como modelo V4. La ruta V4 carga el modelo academico separado.

## Evidencia Y Limites

anexos/integracion/ contiene evidence-stack-v4.json, desktop-stack-v4.png y
mobile-stack-v4.png, copiados de la prueba real original sin alterar sus bytes.
Sus rutas absolutas internas y URL efimera son historicas, no una URL publicada.
La prueba original registra limpieza de sus recursos; no se afirma que siga activa.
Esta preparacion no inicia Docker, navegador, servidor, ML ni nuevas pruebas E2E.
Revision humana y demo en vivo pendientes. No requiere GitHub publico.
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--repo', type=Path, default=REPO)
    parser.add_argument('--evidence', type=Path, default=EVIDENCE)
    parser.add_argument('--previous-manifest-sha256', help='Authorize own-output refresh from this exact manifest SHA')
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.source, args.root, args.repo, args.evidence,
                                 args.previous_manifest_sha256), indent=2))
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print(f'Preparation refused: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
