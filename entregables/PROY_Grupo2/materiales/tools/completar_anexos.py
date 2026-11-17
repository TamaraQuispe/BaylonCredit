"""Complemento descriptivo posterior al congelamiento; nunca entrena ni edita originales."""

import csv
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import statistics
import sys
import tempfile
from datetime import datetime, timezone
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
PROTECTED = ('experiment', 'development', 'sources', 'revision', 'datos',
             'codigo-base', 'support', 'ejemplos', 'informe', 'sustentacion')
USER_REQUEST = 'ya corrige y has lo que falta lo unico que no tienes que cambiar es el informe y la ppt si se tiene que cambiar el nombre del archivo en si eso si lo puedes cambiar pero el contenido no'
DOCUMENT_ALIASES = (
    ('informe/APF3_TD_Grupo2_ML_Innovacion (4).pdf',
     'informe/APF3_TD_Grupo2_ML_Innovacion.pdf',
     'f45e719ee1c069bcce7779bf2def27ad621571360a63380e42e40694f8fff405'),
    ('sustentacion/APF3_Sustentacion_Grupo2_.pptx',
     'sustentacion/APF3_TD_Grupo2_ML_Innovacion.pptx',
     'f31ca299ce1f799f2a69666bd223e2f663aa9446685d75dffcd9e32f0034316e'),
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(relative):
    return json.loads((ROOT / relative).read_text())


def snapshot():
    return {str(p.relative_to(ROOT)): sha(p) for d in PROTECTED
            for p in sorted((ROOT / d).rglob('*')) if p.is_file()}


def encoded(value):
    return (json.dumps(value, ensure_ascii=True, indent=2) + '\n').encode()


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                      '| ' + ' | '.join(['---'] * len(headers)) + ' |']
                     + ['| ' + ' | '.join(map(str, row)) + ' |' for row in rows])


def quantile(values, p):
    ordered = sorted(values)
    position = (len(ordered) - 1) * p
    lo = math.floor(position)
    hi = math.ceil(position)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo)


def main():
    sys.dont_write_bytecode = True
    before = snapshot()
    out = ROOT / 'anexos'
    manifest_path = out / 'manifiesto-complemento.json'
    generator_hash = sha(Path(__file__))
    requirements_hash = sha(ROOT / 'tools/requirements-anexos.txt')
    owned = {}
    accepted_aliases = []
    if manifest_path.exists():
        previous = load('anexos/manifiesto-complemento.json')
        for name, digest in previous['output_sha256'].items():
            path = out / name
            if path.parent != out or path.is_symlink() or not path.is_file() or sha(path) != digest:
                raise RuntimeError(f'Salida ajena o modificada: {name}; no se sobrescribe')
        if (previous['generator_sha256'] == generator_hash
                and previous.get('requirements_sha256') == requirements_hash
                and previous['protected_before'] == before):
            print('Salidas propias verificadas; ejecucion idempotente sin sobrescrituras.')
            return
        old_inputs = previous['protected_before'].copy()
        for old, canonical, digest in DOCUMENT_ALIASES:
            if old in old_inputs:
                if (old_inputs[old] != digest or canonical in old_inputs or old in before
                        or before.get(canonical) != digest):
                    raise RuntimeError(f'Renombre no autorizado o contenido distinto: {old}')
                old_inputs[canonical] = old_inputs.pop(old)
                accepted_aliases.append(dict(original=old, canonical=canonical, sha256=digest))
        if old_inputs != before or previous['protected_before'] != previous['protected_after']:
            raise RuntimeError('Cambio de fuentes: conservar evidencia anterior; no sobrescribir')
        owned = previous['output_sha256'] | {manifest_path.name: sha(manifest_path)}

    started = datetime.now(timezone.utc).isoformat()
    protocol = load('experiment/APF3_PENDING_V6_MODEL_PROTOCOL.json')
    features = protocol['feature_names']
    with (ROOT / 'development/development_known.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 534 and len(features) == 11
    classes = {i: sum(int(row['late_payment']) == i for row in rows) for i in (0, 1)}
    assert classes == {0: 448, 1: 86}
    stats = []
    for name in features + ['late_payment']:
        values = [float(row[name]) for row in rows if row[name] != '']
        stats.append([name, len(values), len(rows) - len(values), len(set(values)),
                      statistics.mean(values), statistics.stdev(values), min(values),
                      quantile(values, .25), statistics.median(values), quantile(values, .75), max(values)])
    buffer = io.StringIO(newline='')
    writer = csv.writer(buffer)
    headers = ['variable', 'n', 'missing', 'unique', 'mean', 'sample_std', 'min', 'q25', 'median', 'q75', 'max']
    writer.writerow(headers)
    writer.writerows(stats)
    outputs = {'estadisticas-dev.csv': buffer.getvalue().encode()}
    outputs['balance-clases-dev.csv'] = ('late_payment,n,percentage\n' + ''.join(
        f'{i},{classes[i]},{100 * classes[i] / len(rows):.12f}\n' for i in (0, 1))).encode()
    x = [float(row['tenure_days']) for row in rows]
    y = [float(row['completed_sales']) for row in rows]
    correlation = statistics.correlation(x, y)
    groups = []
    for prior in (False, True):
        group = [row for row in rows if (float(row['paid_late']) > 0) == prior]
        late = sum(int(row['late_payment']) for row in group)
        groups.append(dict(prior_paid_late=prior, n=len(group), late=late,
                           on_time=len(group) - late, rate=late / len(group)))
    difference = 100 * (groups[1]['rate'] - groups[0]['rate'])
    association = dict(population='DEV conocido elegible; post hoc tras congelamiento',
                       n=534, pearson_tenure_completed_sales=correlation,
                       prior_late_groups=groups, difference_percentage_points=difference,
                       no_causal_or_independent_inference=True)
    outputs['relaciones-dev.json'] = encoded(association)

    # Import only the pure policy module. No model artifacts or ML runner are loaded.
    policy_path = ROOT / 'revision/policy.py'
    spec = importlib.util.spec_from_file_location('annex_pure_policy', policy_path)
    policy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(policy)
    base = dict(completed_sales=3, paid_credits=3, paid_late=1, pending_overdue=0,
                pending_current=0, outstanding=0, utilization=0, requested_ratio=.25,
                tenure_days=60, punctuality_rate=2 / 3, overdue_rate=0)
    cases = [
        ('deuda_vigente', dict(pending_current=1, outstanding=20, utilization=.25), 'blocked_pending_balance'),
        ('deuda_vencida', dict(pending_overdue=1, outstanding=20, utilization=.25, overdue_rate=.25), 'blocked_pending_balance'),
        ('saldo_parcial', dict(pending_current=1, outstanding=5, utilization=.0625), 'blocked_pending_balance'),
        ('deuda_prioritaria_sin_historial', dict(completed_sales=0, paid_credits=0, paid_late=0,
              punctuality_rate=None, pending_current=1, outstanding=20, utilization=.25), 'blocked_pending_balance'),
        ('sin_historial', dict(completed_sales=0, paid_credits=0, paid_late=0,
              punctuality_rate=None), 'requires_owner_review'),
        ('saldo_desconocido', dict(pending_current=None, pending_overdue=None, outstanding=None,
              utilization=None, overdue_rate=None), 'requires_owner_review'),
        ('elegible', {}, None),
    ]
    tests = []
    for name, changes, expected in cases:
        data = base | changes
        original = data.copy()
        result = policy.pre_model_decision(data)
        assert data == original
        assert set(data) == set(features)
        if expected is None:
            assert result is None
        else:
            assert set(result) == {'decision', 'reason', 'requires_manual_review'}
            assert result['decision'] == expected and isinstance(result['reason'], str) and result['reason']
            assert result['requires_manual_review'] is (expected == 'requires_owner_review')
        tests.append(dict(case=name, features=data, expected=expected, result=result, passed=True))
    assert not any(name.split('.')[0] in {'sklearn', 'joblib'} for name in sys.modules)
    outputs['pruebas-reglas-previas.json'] = encoded(dict(
        status='nueva ejecucion complementaria; no restaura evidencia historica ausente',
        started_at_utc=started, finished_at_utc=datetime.now(timezone.utc).isoformat(),
        source='revision/policy.py', source_sha256=sha(policy_path),
        tested_function='pre_model_decision', checks=tests, passed=7, failed=0,
        ml_calls_in_these_checks=0,
        scope='Solo siete llamadas al helper puro; no prueba ni cuenta llamadas del entrenamiento completo'))

    training = load('experiment/training_reports.json')
    cached = {name: load(f'experiment/final_cache_{name}.json')
              for name in ('svm', 'most_frequent', 'constant_1')}
    metric_rows = []
    for name in cached:
        oof = training[name]['review_policy']['oof']
        final = cached[name]['review_policy']
        metric_rows.append([name, f"{oof['metrics']['f2']:.12f}", f"{final['metrics']['f2']:.12f}",
                            oof['daily_max'], final['daily_max'],
                            str(oof['capacity_respected'] and final['capacity_respected'])])
    technical_pass = (all(cached['svm']['review_policy']['metrics']['f2'] > cached[n]['review_policy']['metrics']['f2']
                          for n in ('most_frequent', 'constant_1'))
                      and cached['svm']['review_policy']['capacity_respected'])
    assert technical_pass
    errors = sorted(cached['svm']['error_cases'], key=lambda item: item['loan_id'])[:3]
    assert [item['loan_id'].split('-')[-1] for item in errors] == ['L00051', 'L00054', 'L00058']
    hypotheses = [
        'Cuatro creditos anteriores puntuales pueden aportar una senal insuficiente del proximo atraso. '
        'La representacion y aproximacion del modelo producen un score bajo el umbral; no se conoce la causa del atraso.',
        'Un atraso entre tres creditos anteriores puede inducir sobrealerta en esta representacion; '
        'el score supera el umbral aunque el desenlace es puntual.',
        'Cuatro creditos anteriores puntuales tampoco garantizan puntualidad posterior; '
        'historial escaso y aproximacion del modelo son hipotesis de senal insuficiente, no causas demostradas.',
    ]
    # Verify existing PDF evidence without producing anything inside informe/.
    from pypdf import PdfReader
    pdfs = list((ROOT / 'informe').glob('*.pdf'))
    assert len(pdfs) == 1
    reader = PdfReader(pdfs[0])
    pdf_text = '\n'.join(page.extract_text() or '' for page in reader.pages)
    cited = {item['loan_id']: item['loan_id'].split('-')[-1] in pdf_text for item in errors}
    assert all(cited.values()), 'El PDF existente no permite confirmar todos los casos'
    outputs['errores-cache-final.json'] = encoded(dict(
        source='experiment/final_cache_svm.json', source_sha256=sha(ROOT / 'experiment/final_cache_svm.json'),
        selection='Tres primeros errores por loan_id; sin nueva inferencia',
        cases=[dict(case=item, hypothesis=h) for item, h in zip(errors, hypotheses)],
        existing_pdf_sha256=sha(pdfs[0]), existing_pdf_pages=len(reader.pages), already_cited=cited))

    with tempfile.TemporaryDirectory(prefix='apf3-annex-') as temporary:
        stage = Path(temporary)
        os.environ['MPLCONFIGDIR'] = str(stage / 'matplotlib')
        os.environ['MPLBACKEND'] = 'Agg'
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        plt.rcParams.update({'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False})
        plots = [
            ('relacion-antiguedad-ventas.png', 'Antiguedad y ventas previas: DEV conocido'),
            ('relacion-atraso-previo-observado.png', 'Antecedente tardio y atraso observado: DEV'),
            ('balance-clases-dev.png', 'Balance de clases: DEV conocido (n=534)'),
        ]
        for index, (name, title) in enumerate(plots):
            fig, ax = plt.subplots(figsize=(8, 4.5), layout='constrained')
            if index == 0:
                ax.scatter(x, y, s=17, alpha=.35, color='#236f69')
                ax.set(xlabel='Antiguedad (dias)', ylabel='Ventas al credito previas',
                       title=f'{title}\nPearson r = {correlation:.4f}; no causal')
            elif index == 1:
                rates = [100 * group['rate'] for group in groups]
                ax.bar(['Sin atraso previo', 'Con atraso previo'], rates, color=['#236f69', '#b26739'])
                for i, group in enumerate(groups):
                    ax.text(i, rates[i] + .6, f"{group['late']}/{group['n']} = {rates[i]:.2f}%", ha='center')
                ax.set(ylabel='Atraso observado (%)', ylim=(0, max(rates) + 6), title=title)
            else:
                ax.bar(['0: puntual', '1: atraso'], list(classes.values()), color=['#236f69', '#b26739'])
                for i, count in classes.items():
                    ax.text(i, count + 7, f'{count} ({100 * count / 534:.2f}%)', ha='center')
                ax.set(ylabel='Fiados sinteticos', ylim=(0, 510), title=title)
            fig.savefig(stage / name, dpi=170, metadata={'Software': 'Complemento descriptivo DEV'})
            plt.close(fig)
            outputs[name] = (stage / name).read_bytes()

        text = f"""# Complemento generado para revision final

Documento independiente del informe (cuerpo de 15 paginas) y de la presentacion. No modifica su contenido ni afirma revision previa del grupo sobre este complemento. Analisis descriptivo post hoc de DEV, posterior al congelamiento del modelo: no selecciona variables, parametros, umbrales ni disena FINAL.

## 1. Poblacion y estadisticas

Fuente: development/development_known.csv, SHA-256 {sha(ROOT / 'development/development_known.csv')}. Son 534 fiados simulados elegibles con desenlace conocido; no son 534 clientes independientes. Los siete desenlaces desconocidos de DEV elegible no se imputan ni entran aqui. Las replicas son historias alternativas, no volumen real sumable.

estadisticas-dev.csv conserva las once variables y el objetivo binario, con n, faltantes, valores unicos, media, desviacion muestral (n-1), minimo, cuartiles interpolados linealmente (posicion (n-1)p), mediana y maximo. Para el objetivo, la media es la proporcion de clase 1, no una magnitud continua. balance-clases-dev.csv conserva los conteos y porcentajes exactos.

{table(['Clase', 'n', '%'], [[i, classes[i], f'{100 * classes[i] / 534:.6f}'] for i in (0, 1)])}

![Balance de clases](balance-clases-dev.png)

Las cinco variables de deuda son constantes cero por elegibilidad: pending_overdue, pending_current, outstanding, utilization y overdue_rate. completed_sales coincide con paid_credits; representa ventas al credito ligadas al historial, no ventas al contado ni dos senales independientes. No se altera el contrato de once campos.

{table(['Variable', 'Media', 'DE', 'Min', 'Mediana', 'Max'], [[s[0]] + [f'{s[i]:.6f}' for i in (4, 5, 6, 8, 10)] for s in stats])}

## 2. Relaciones descriptivas DEV

Relacion 1: antiguedad frente a ventas al credito previas. Pearson r = {correlation:.12f}, calculado con statistics de la biblioteca estandar sobre las 534 filas. La asociacion no demuestra que la antiguedad cause ventas: ambas evolucionan con el historial simulado y hay observaciones repetidas por cliente. No se calculan p-valores ni intervalos que supongan independencia.

![Antiguedad y ventas](relacion-antiguedad-ventas.png)

Relacion 2: paid_late > 0 frente al desenlace late_payment observado del nuevo fiado.

{table(['Antecedente tardio', 'n', 'Puntuales', 'Atrasos', 'Tasa %'], [['Si' if g['prior_paid_late'] else 'No', g['n'], g['on_time'], g['late'], f"{100 * g['rate']:.6f}"] for g in groups])}

Diferencia (con antecedente menos sin antecedente): {difference:.6f} puntos porcentuales. En estos datos la tasa es {'mayor' if difference > 0 else 'menor o igual'} con antecedente. No es una regla determinista, efecto causal, validacion real ni evidencia independiente por transaccion. No cambia el modelo congelado.

![Antecedente y desenlace](relacion-atraso-previo-observado.png)

## 3. Criterio tecnico predeclarado

Fuente original: experiment/APF3_PENDING_V6_MODEL_PROTOCOL.json, success_proposal. Su texto tecnico literal es: {protocol['success_proposal']['technical']}. La revision experiment/revision_protocol.json hereda el protocolo y conserva seleccion F2 OOF, baselines y cola. No se confunden las antiguas cifras DEV del protocolo historico con las 534 filas de esta revision V6 Final.

La seleccion fue por F2 de acciones OOF con capacidad de cinco alertas por replica y dia; el exito tecnico predeclarado se evalua en FINAL, superando estrictamente ambos Dummy con capacidad respetada. Los resultados siguientes se COPIAN de caches y reportes guardados, sin predicciones nuevas.

{table(['Politica', 'F2 OOF', 'F2 FINAL', 'Max/dia OOF', 'Max/dia FINAL', 'Capacidad respetada'], metric_rows)}

Se satisface la propuesta tecnica sintetica, no una meta comercial. SVM fue seleccionado en DEV con umbral 0.1; aunque otro modelo tenga mejor FINAL, no se cambia el ganador. OOF se reutilizo para seleccion y es optimista; las colas OOF son por fold, no una cola desplegable de toda la cohorte. Dos minutos por alerta y capacidad cinco son supuestos no cronometrados. F2 pondera recall por decision del equipo, no por costos reales medidos.

## 4. Nueva propuesta de meta de negocio

La referencia declarada por el propietario es aproximadamente 14 solicitudes, 12 creditos y nueve clientes por semana y 25-35 minutos semanales de revision. Es autorreporte aproximado, no cronometraje ni prueba de ahorro. Las referencias de volumen y tiempo no son una linea base instrumental medida.

PROPUESTA NUEVA DEL EQUIPO para un futuro piloto autorizado: reducir al menos 10% la mediana de minutos semanales de revision normalizados por volumen de solicitudes frente a una linea base medida, sin aprobaciones automaticas. No era una meta inicial predeclarada; no esta aceptada por el propietario y NO se ha demostrado alcanzada con los datos existentes. No se utiliza para juzgar FINAL retrospectivamente.

Antes del piloto, acordar con el propietario duracion y periodos comparables, procedimiento de cronometraje, volumen de referencia Vref y tolerancias de errores y costos. Registrar por semana minutos reales T y solicitudes N; para N>0 usar Tnorm = T * Vref / N. Comparar medianas de Tnorm en linea base y piloto: reduccion = 1 - mediana(piloto) / mediana(base), exigiendo >=0.10. Definir antes como tratar semanas N=0, estacionalidad y cambios de carga. Medir tambien tiempos de revision obligatoria, correcciones y uso del sistema, no solo alertas ML.

Monitorear atrasos omitidos (FN), falsas alertas (FP), errores operativos y sus consecuencias con desenlaces maduros. El propietario debe acordar ANTES del piloto tolerancias y reglas de pausa; no se inventan costos ni umbrales de seguridad ya aceptados. La meta de tiempo no puede compensar incumplir esas tolerancias. Todas las decisiones de credito siguen siendo humanas; elegibilidad o score bajo nunca significan aprobacion automatica.

## 5. Tres errores ya citados en el PDF

Se verifico por extraccion de texto que el PDF existente ya cita L00051, L00054 y L00058. Se conservan sin modificar sus paginas. Fuente: experiment/final_cache_svm.json; tres primeros errores por ID. No se ejecuta el modelo ni se produce una nueva evaluacion FINAL.

"""
        for item, hypothesis in zip(errors, hypotheses):
            f = item['features']
            text += (f"### {item['loan_id']} ({item['policy_error']})\n\n"
                     f"Real={item['actual']}; predicho={item['predicted']}; score={item['probability']:.12f}; "
                     f"umbral={item['threshold']}. Historial: {f['paid_credits']:g} pagados, "
                     f"{f['paid_late']:g} tardios, puntualidad={f['punctuality_rate']:.6f}, "
                     f"antiguedad={f['tenure_days']:g} dias y solicitud/cupo={f['requested_ratio']:.6f}. "
                     f"Deuda previa cero. {hypothesis}\n\n")
        text += """Las explicaciones son hipotesis sobre representacion, umbral y aproximacion del modelo; no causas estadisticamente confirmadas. No se atribuyen problemas de liquidez ni eventos financieros no observados.

## 6. Pruebas complementarias de reglas previas

pruebas-reglas-previas.json registra SIETE ejecuciones nuevas del helper puro revision/policy.py mediante importlib: deuda vigente, vencida, saldo parcial, deuda prioritaria aun sin historial, sin historial, saldo desconocido y elegible (None). Se comprueban ruta, razon no vacia, indicador de revision manual, contrato de once campos e inmutabilidad del diccionario de entrada. Se copia el SHA-256 de la fuente; no se modifica ni se carga joblib.

Cero llamadas ML corresponde EXCLUSIVAMENTE a estos siete checks: no es una auditoria de las llamadas del entrenamiento completo. El JSON es evidencia nueva con horas reales de esta ejecucion, no restauracion de un archivo historico faltante. Las pruebas son unitarias del enrutamiento, no certificacion del validador numerico ni de integracion completa. None significa elegible para evaluacion, no credito aprobado.

## 7. Prompts, IA y revision

prompts-complemento.md conserva literalmente la solicitud del usuario que autoriza completar lo faltante sin cambiar el contenido del informe ni de la presentacion. Las instrucciones operativas del complemento se documentan aparte como resumen, no como cita literal del usuario. No se reconstruyen supuestos prompts historicos ni se afirma que sean todos los usados en el proyecto. Se mantiene el contexto de declaracion de IA del proyecto existente.

Segun confirmacion del usuario, el Anexo C existente fue revisado por el mismo grupo. Esa confirmacion NO se extiende a este material nuevo: complemento generado para revision final, pendiente de lectura y aprobacion del grupo. No se atribuye validacion al propietario ni al docente.

## 8. Checklist de cobertura y pendientes

| Evidencia / accion | Estado y limite |
| --- | --- |
| Estadisticas de once features y clases DEV | Generadas en CSV; 534 conocidos; sin modificar fuentes |
| Dos relaciones y balance de clases | Tres PNG y calculos descriptivos reproducibles |
| Meta tecnica original y baselines | Recuperada del protocolo; resultados copiados de caches |
| Meta de negocio cuantitativa | Propuesta futura >=10%; no aceptada ni demostrada |
| Tres errores FINAL | Cache reutilizado; casos ya citados en PDF; hipotesis prudentes |
| Siete reglas previas | Nueva ejecucion unitaria; no evidencia historica restaurada |
| Prompts y declaracion IA | Solicitud actual literal y resumen operativo; no historia completa |
| Revision de este complemento por el grupo | Pendiente; no se afirma completada |
| Cuenta y ejecucion real en Colab | No verificadas en vivo; requiere comprobacion humana |
| Ensayo de sustentacion de 12 minutos | No verificado; requiere ensayo cronometrado |
| Aula y entrega academica | Estado desconocido; no se acceso a la cuenta |
| Piloto y aceptacion del propietario | Pendientes; no autorizacion de produccion |

Documentos de entrega: informe/APF3_TD_Grupo2_ML_Innovacion.pdf y sustentacion/APF3_TD_Grupo2_ML_Innovacion.pptx. Este generador no renombra ni edita ningun archivo de esas carpetas. Esta cobertura complementaria no certifica requisitos de la consigna no disponibles para cotejo ni acceso a cuentas, demo publica o GitHub.

## 9. Reproduccion y preservacion

Desde la raiz del proyecto, crear y activar un entorno aislado con Python 3.11 o superior. En macOS/Linux: python3 -m venv /tmp/apf3-anexos-venv y luego source /tmp/apf3-anexos-venv/bin/activate. En Windows puede usarse una ubicacion temporal equivalente y su script de activacion. Instalar las versiones fijadas con python -m pip install -r tools/requirements-anexos.txt; ejecutar python -B tools/completar_anexos.py. No es necesario instalar las dependencias ML del proyecto para este complemento.

El directorio de trabajo temporal se obtiene mediante tempfile.TemporaryDirectory(), respetando la configuracion temporal del sistema (por ejemplo TMPDIR), sin rutas locales fijas. Matplotlib usa Agg y configuracion temporal; PDF independiente mediante ReportLab. No hay entrenamiento, tuning, nuevas inferencias, diseno FINAL, acceso publico ni cambios en archivos originales.

manifiesto-complemento.json conserva SHA-256 de salidas, generador, dependencias y fuentes protegidas antes/despues; verificacion-complemento.json registra comprobaciones de esta ejecucion. Una segunda ejecucion con fuentes y salidas intactas verifica los hashes y no sobrescribe nada. Al actualizar el generador solo se regeneran salidas propias cuyo hash anterior siga intacto. Se admiten exclusivamente los dos renombres documentales conocidos con contenido identico; cualquier otro cambio de fuentes o salida ajena/modificada detiene la generacion.
"""
        outputs['complemento-consigna.md'] = text.encode()
        outputs['prompts-complemento.md'] = (
            '# Prompts de este complemento\n\nComplemento generado para revision final. '
            'No es un historial completo del proyecto.\n\n## Solicitud literal del usuario\n\n'
            '```text\n' + USER_REQUEST + '\n```\n\n## Instrucciones operativas resumidas\n\n'
            'Examinar fuentes antes de editar; cambios minimos mediante apply_patch; preservar cambios ajenos. '
            'Trabajar solo en el nuevo generador y anexos. No editar informe, presentacion, protocolo, '
            'experimento ni fuentes. Preparar estadisticas y relaciones descriptivas DEV posteriores al '
            'congelamiento, recuperar resultados de caches sin entrenar ni hacer inferencias nuevas, '
            'distinguir la meta tecnica original de la propuesta futura de negocio y ejecutar siete '
            'pruebas del helper puro. Documentar dependencias aisladas y verificar hashes e idempotencia. '
            'Verificar resultados y declarar limites; no inventar aprobaciones '
            'ni ejecuciones historicas. Este parrafo es un resumen, no cita literal de instrucciones.\n\n'
            'Se conserva la declaracion de IA del proyecto. El usuario confirmo revision del Anexo C '
            'existente por el mismo grupo; este complemento nuevo sigue pendiente de revision.\n').encode()

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
        styles = getSampleStyleSheet()
        styles['BodyText'].fontSize = 9
        styles['BodyText'].leading = 13
        story = []
        lines = text.splitlines()
        index = 0
        while index < len(lines):
            line = lines[index]
            if line.startswith('|'):
                data = []
                while index < len(lines) and lines[index].startswith('|'):
                    cells = [cell.strip() for cell in lines[index].strip('|').split('|')]
                    if not all(cell == '---' for cell in cells):
                        data.append([Paragraph(escape(cell), styles['BodyText']) for cell in cells])
                    index += 1
                widths = [475 / len(data[0])] * len(data[0])
                if len(data[0]) == 6:
                    widths = ([120] + [71] * 5 if data[0][0].getPlainText() == 'Variable'
                              else [95, 100, 100, 60, 60, 60])
                tab = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
                tab.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                         ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5efed')),
                                         ('LINEBELOW', (0, 0), (-1, 0), .5, colors.grey),
                                         ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
                story.extend([tab, Spacer(1, 10)])
                continue
            if line.startswith('!['):
                name = line.split('](')[1].rstrip(')')
                story.append(Image(str(stage / name), width=475, height=267))
            elif line.strip():
                level = len(line) - len(line.lstrip('#'))
                style = styles[f'Heading{min(level, 3)}'] if level else styles['BodyText']
                story.append(Paragraph(escape(line.lstrip('# ').strip()), style))
                space = Spacer(1, 6)
                space.keepWithNext = bool(level)
                story.append(space)
            index += 1

        def footer(canvas, doc):
            canvas.setFont('Helvetica', 8)
            canvas.drawString(54, 28, 'Complemento independiente / revision final pendiente')
            canvas.drawRightString(A4[0] - 54, 28, str(doc.page))

        pdf = stage / 'complemento-consigna.pdf'
        SimpleDocTemplate(str(pdf), pagesize=A4, rightMargin=54, leftMargin=54,
                          topMargin=45, bottomMargin=45, title='Complemento descriptivo DEV y consigna',
                          author='Grupo 2', invariant=1).build(story, onFirstPage=footer, onLaterPages=footer)
        generated_pdf = PdfReader(pdf)
        generated_text = '\n'.join(page.extract_text() or '' for page in generated_pdf.pages)
        assert all(term in generated_text for term in ('10%', 'L00051', 'L00054', 'L00058', 'Checklist'))
        outputs[pdf.name] = pdf.read_bytes()

    after = snapshot()
    assert before == after, 'Cambio concurrente en fuentes protegidas; no se publican salidas'
    outputs['verificacion-complemento.json'] = encoded(dict(
        checked_at_utc=datetime.now(timezone.utc).isoformat(), protected_hashes_unchanged=before == after,
        accepted_document_aliases=accepted_aliases,
        dev_n=534, class_counts=classes, statistics_rows=12, graphs=3,
        gate_checks_passed=7, technical_success_from_saved_metrics=technical_pass,
        existing_pdf_cases_confirmed=cited, existing_pdf_pages=len(reader.pages),
        standalone_pdf_pages=len(generated_pdf.pages), standalone_pdf_text_checks=True,
        external_accounts_checked=False, full_training_executed=False,
        imports_ml_or_joblib=False, no_new_final_inference=True))
    # Preflight every destination before creating anything in anexos/.
    for name in list(outputs) + [manifest_path.name]:
        if (out / name).exists() or (out / name).is_symlink():
            if ((out / name).is_symlink() or name not in owned or sha(out / name) != owned[name]):
                raise FileExistsError(f'No se sobrescribe salida ajena o modificada: {out / name}')
    if out.is_symlink():
        raise RuntimeError('anexos no puede ser un enlace simbolico')
    out.mkdir(exist_ok=True)
    for name, content in outputs.items():
        if name in owned and sha(out / name) != owned[name]:
            raise RuntimeError(f'Salida modificada durante la ejecucion: {name}')
        with (out / name).open('wb' if name in owned else 'xb') as stream:
            stream.write(content)
    assert snapshot() == before
    manifest = dict(generator_sha256=generator_hash, requirements_sha256=requirements_hash,
                    accepted_document_aliases=accepted_aliases,
                    generated_at_utc=datetime.now(timezone.utc).isoformat(),
                    output_sha256={name: sha(out / name) for name in outputs},
                    protected_before=before, protected_after=after, protected_unchanged=True)
    if manifest_path.name in owned and sha(manifest_path) != owned[manifest_path.name]:
        raise RuntimeError('Manifiesto modificado durante la ejecucion')
    with manifest_path.open('wb' if manifest_path.name in owned else 'xb') as stream:
        stream.write(encoded(manifest))
    print(json.dumps(dict(outputs=list(outputs) + [manifest_path.name], association=association,
                          metrics=metric_rows, protected_unchanged=True), indent=2))


if __name__ == '__main__':
    main()
