"""Export V6 Final documents from persisted evidence, without an ML runtime."""

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from docx import Document
from pptx import Presentation
from pypdf import PdfReader

REPO = Path(__file__).resolve().parents[1]
ROOT = Path('/Users/tamaraalison/Downloads/APF3_Grupo2_V6_Final')
TEMP = '/var/folders/sx/_6ljw37n2_j9hk2f_vtqplj40000gn/T/opencode'
PLAYWRIGHT = TEMP + '/apf3-render/node_modules/playwright/index.mjs'
STATUS = 'Datos simulados / V6 Final r1 / Revision humana pendiente'
FAMILIES = ('svm', 'tree', 'most_frequent', 'constant_1')
LABELS = ('SVM elegida', 'Arbol', 'Dummy mayoria', 'Dummy positivo')
METRICS = ('precision', 'recall', 'f1', 'f2', 'accuracy')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def normalized(text):
    return re.sub(r'\W+', '', text).lower()


def generate(root, playwright):
    # Hash entire input trees, including serialized artifacts, without loading models.
    inputs = [p for folder in ('experiment', 'development')
              for p in (root / folder).rglob('*') if p.is_file()]
    sources = {str(p): sha(p) for p in inputs}

    def load(name):
        return json.loads((root / 'experiment' / name).read_text())

    def helper(name):
        path = REPO / 'deploy' / name
        sources[str(path)] = sha(path)
        return module(path)

    documents = helper('generate-apf3-report.py')
    renderer = helper('slide-renderer.py')
    browser = helper('generate-pending-v6-defense.py').BROWSER
    table, plt = documents.table, documents.plt
    sources[str(Path(__file__).resolve())] = sha(Path(__file__).resolve())
    report = load('pending_v6_report.json')
    selection = load('frozen_selection.json')
    protocol = load('revision_protocol.json')
    checks = load('report_checks.json')
    study = load('development_study_rows.json')
    known = load('development_known_rows.json')
    illustration = load('illustrative_output.json')
    models = report['models']
    winner = selection['global_winner']
    assert report['selection'] == selection
    assert winner['family'] == 'svm' and winner['threshold'] == 0.1
    assert report['revision_id'] == 'v6-final-r1'
    assert checks['clients_disjoint'] and checks['freeze_unchanged']
    for filename, expected in load('artifact_manifest.json').items():
        assert sha(root / 'experiment' / filename) == expected
    assert len(study) == 541 and len(known) == 534
    assert Counter(r['late_payment'] for r in known) == {0: 448, 1: 86}
    with (root / 'experiment/final_eligible.csv').open(newline='') as stream:
        final_rows = list(csv.DictReader(stream))
    assert len(final_rows) == 277
    assert Counter(r['late_payment'] for r in final_rows) == {'0': 234, '1': 41, '': 2}
    assert not {r['client_id'] for r in study} & {r['client_id'] for r in final_rows}
    assert illustration['known_label'] is None and illustration['distinctness_pass']
    assert illustration['features'] == load('illustrative_input.json')['features']
    for rows in (study, final_rows):
        assert all(any(float(r[f]) != illustration['features'][f] for f in report['feature_names']) for r in rows)
    fold_plan = load('planned_folds.json')
    fold_groups = [fold_plan['outer'], *fold_plan['inner_sigmoid_by_outer_train'], fold_plan['inner_sigmoid_full_train']]
    fold_checks = 0
    for group in fold_groups:
        assert len(group['folds']) == 3
        for fold in group['folds']:
            assert not set(fold['train_clients']) & set(fold['validation_clients'])
            assert all(fold[key][label] > 0 for key in ('train_class_counts', 'validation_class_counts') for label in ('0', '1'))
            fold_checks += 1
    assert models['svm']['final']['confusion_matrix'] == [[166, 68], [9, 32]]
    for family in FAMILIES:
        cache = load('final_cache_' + family + '.json')
        assert cache['metrics'] == models[family]['final']
        assert cache['review_policy'] == models[family]['review_policy']['final']
        for split in ('train', 'oof', 'final'):
            for metrics in (models[family][split], models[family]['review_policy'][split]['metrics']):
                (tn, fp), (fn, tp) = metrics['confusion_matrix']
                assert tn + fp + fn + tp == metrics['n']
                calculated = dict(precision=tp / (tp + fp) if tp + fp else 0,
                    recall=tp / (tp + fn) if tp + fn else 0,
                    f1=2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0,
                    f2=5 * tp / (5 * tp + fp + 4 * fn) if 5 * tp + fp + 4 * fn else 0,
                    accuracy=(tn + tp) / metrics['n'])
                assert all(abs(metrics[k] - v) < 1e-12 for k, v in calculated.items())
            queue = models[family]['review_policy'][split]
            assert queue['reviews'] == queue['reviews_known'] + queue['reviews_unknown']
            assert queue['minutes_hypothetical'] == 2 * queue['reviews']
            assert queue['capacity_respected'] and queue['daily_max'] <= 5

    out, defense = root / 'informe', root / 'sustentacion'
    for folder in (out, defense, out / 'figuras', defense / 'vistas'):
        folder.mkdir(parents=True, exist_ok=True)

    def dump(path, data):
        path.write_text(json.dumps(data, ensure_ascii=True, indent=2, allow_nan=False) + '\n')

    # Execute only the frozen, pure pre-model guard. No estimator or runner import.
    policy_path = REPO / 'backend/app/services/academic_v6_policy.py'
    sources[str(policy_path)] = sha(policy_path)
    assert sha(policy_path) == protocol['policy_sha256']
    policy = module(policy_path)
    gate_cases = [
        ('Deuda vigente', {'pending_current': 1, 'outstanding': 30}, 'blocked_pending_balance'),
        ('Saldo parcial', {'outstanding': 10}, 'blocked_pending_balance'),
        ('Deuda y sin historial: deuda primero', {'outstanding': 10, 'paid_credits': 0}, 'blocked_pending_balance'),
        ('Sin fiados liquidados', {'paid_credits': 0}, 'requires_owner_review'),
        ('Historial no confirmado', {'paid_credits': None}, 'requires_owner_review'),
        ('Deuda no confirmada', {'outstanding': None}, 'requires_owner_review'),
        ('Deuda cero e historial confirmado', {}, 'model_eligible'),
    ]
    gates = []
    for name, updates, expected in gate_cases:
        features = {**illustration['features'], **updates}
        decision = policy.pre_model_decision(features)
        actual = decision['decision'] if decision else 'model_eligible'
        assert actual == expected
        gates.append(dict(case=name, features=features, expected=expected, actual=actual,
                          passed=True, model_called=False, probability=None))
    dump(out / 'pruebas-reglas-previas.json', gates)

    dev, final = report['development'], report['final']
    for part, attempts, blocked, eligible, n, unknown in (
        (dev, 586, 45, 541, 534, 7), (final, 292, 15, 277, 275, 2)
    ):
        assert (part['study_attempts'], part['routing']['blocked_pending_balance'],
                part['routing']['model_eligible'], part['known_rows'], part['unknown_rows']) == (
                    attempts, blocked, eligible, n, unknown)
        assert part['routing']['requires_owner_review'] == 0
        assert all(a['hard_constraints_pass'] and not a['coherence_accepted'] for a in part['audits'])
    constants = [f for f in report['feature_names'] if len({r[f] for r in known}) == 1]
    assert len(constants) == 5 and all(r['completed_sales'] == r['paid_credits'] for r in known)
    counts = Counter(r['late_payment'] for r in known)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.1), layout='constrained')
    fig.patch.set_facecolor('#F6F3EB')
    axes[0].bar(['Puntual (0)', 'Atraso (1)'], [counts[0], counts[1]], color=['#236F69', '#A85632'])
    for i, v in enumerate((counts[0], counts[1])):
        axes[0].text(i, v + 4, str(v), ha='center')
    axes[0].set_title('DEV conocido: balance de clases')
    axes[1].scatter([r['tenure_days'] for r in known], [r['completed_sales'] for r in known],
                    s=10, alpha=0.35, color='#236F69')
    axes[1].set(xlabel='Antiguedad (dias)', ylabel='Ventas de credito completadas', title='EDA solo DEV')
    fig.savefig(out / 'figuras/eda-dev.png', dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(6.8, 2.8), layout='constrained')
    matrix = models['svm']['final']['confusion_matrix']
    ax.imshow(matrix, cmap='Blues')
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(matrix[i][j]), ha='center', va='center',
                    color='white' if matrix[i][j] > 100 else 'black', fontsize=16)
    ax.set(xticks=[0, 1], yticks=[0, 1], xlabel='Predicho (0 puntual / 1 alerta)', ylabel='Real (0 / 1)',
           title='SVM FINAL / 275 etiquetas conocidas')
    fig.savefig(out / 'figuras/confusion-final.png', dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 2.5), layout='constrained')
    ax.axis('off')
    grid = ax.table(cellText=[['Arbol', 'depth 2/3/4; leaf 8/16; peso +/-', '12'],
                             ['SVM lineal', 'C 0.1/1/10; peso +/-; sigmoid grupos', '6'],
                             ['Umbrales', '0.1 / 0.2 / 0.3 / 0.4 / 0.5 / 0.6 / 0.7', '126 pares']],
                    colLabels=['Familia', 'Grilla congelada', 'Cantidad'], loc='center', colWidths=[.18, .65, .17])
    grid.auto_set_font_size(False)
    grid.set_fontsize(10)
    grid.scale(1, 2)
    fig.savefig(out / 'figuras/metodo-grilla.png', dpi=160)
    plt.close(fig)

    # Each printed numeric metric cell retains its exact JSON path and formatting.
    printed = []

    def metric_rows(mode, splits):
        rows = []
        for family, label in zip(FAMILIES, LABELS, strict=True):
            for split in splits:
                path = ['models', family, split] if mode == 'RAW' else ['models', family, 'review_policy', split, 'metrics']
                value = report
                for key in path:
                    value = value[key]
                cells = [f'{value[k]:.8f}' for k in METRICS]
                for k, cell in zip(METRICS, cells, strict=True):
                    printed.append(dict(path=path + [k], text=cell))
                rows.append([label, split, *cells])
        return rows

    headers = ['Modelo', 'Particion', 'Precision', 'Recall', 'F1', 'F2', 'Accuracy']
    raw_final = metric_rows('RAW', ('final',))
    policy_final = metric_rows('POLICY', ('final',))
    training = metric_rows('RAW', ('train', 'oof'))
    oof_policy = metric_rows('POLICY', ('oof',))
    queues = []
    for family, label in zip(FAMILIES, LABELS, strict=True):
        q = models[family]['review_policy']['final']
        fields = ('reviews', 'reviews_known', 'reviews_unknown', 'daily_max', 'days_over_before_cap', 'minutes_hypothetical')
        for k in fields:
            printed.append(dict(path=['models', family, 'review_policy', 'final', k], text=str(q[k])))
        queues.append([label, *[q[k] for k in fields]])
    queue_headers = ['Politica', 'Total', 'Conocidas', 'Sin label', 'Max/dia', 'Dias sobre antes', 'Min hip.']
    svm_q, dummy_q = (models[f]['review_policy']['final'] for f in ('svm', 'constant_1'))
    delta = dummy_q['reviews'] - svm_q['reviews']
    assert delta == 174 and svm_q['reviews'] == 100 and dummy_q['reviews'] == 274
    s, t = selection['families']['svm'], selection['families']['tree']
    f2s = s['metrics']['f2']
    f2t = t['metrics']['f2']
    summary = (f"SVM elegida por F2 OOF de politica {f2s:.8f}, frente al arbol {f2t:.8f}. "
               f"FINAL SVM: F2 {models['svm']['final']['f2']:.8f}, precision {models['svm']['final']['precision']:.8f}, "
               f"recall {models['svm']['final']['recall']:.8f} (32/41). "
               f"El arbol logra F2 FINAL {models['tree']['final']['f2']:.8f}; no se reselecciona con el test.")
    burden = (f"SVM: {svm_q['reviews']} revisiones frente a {dummy_q['reviews']} de Dummy positivo limitado. "
              f"{delta} menos x 2 minutos = {delta * 2} minutos HIPOTETICOS, no ahorro observado. "
              'Los FN pasan de 0 en Dummy limitado a 9 en SVM; 68 FP tambien consumen tiempo. No hay ganancias garantizadas.')
    pages = []

    def page(title, body):
        pages.append('# ' + title + '\n\n' + body)

    page('V6 Final | Evidencia para priorizar, no aprobar',
         'Cerveceria Baylon / Credify / APF3 Grupo 2. Informe de investigacion academica.\n\n'
         'Continuidad APF1: problema del registro y evaluacion del fiado a un dia. APF2: MVP de clientes, evaluacion, fiados y pagos. '
         'APF3: clasificacion supervisada para orientar revision humana, no decision crediticia automatica.\n\n'
         '**Edicion V6 Final, revision v6-final-r1.** Se conserva V6 historico. Esta revision prospectiva fue declarada '
         'despues de consultar resultados anteriores; no se presenta como un diseno ciego a esa experiencia. '
         'Nuevas semillas y nuevos clientes ficticios, mismo simulador y supuestos.\n\n'
         + summary + '\n\n' + STATUS + '. Sin firmas ni roles confirmados. Produccion intacta. '
         'Esta exportacion solo lee evidencia experimental persistida y prueba reglas puras; no entrena, predice ni simula datos.')
    page('1. Problema, objetivo y alcance',
         'Cada fila representa un fiado otorgado, no una persona independiente. La variable late_payment vale 1 si hay atraso '
         'desde el vencimiento contractual y 0 si la liquidacion completa ocurre hasta el vencimiento inclusive. '
         'La gracia no cambia atraso a puntualidad; atraso no equivale a perdida definitiva. Etiquetas inmaduras quedan desconocidas, '
         'nunca se imputan a cero.\n\n'
         'Objetivo: clasificar atraso entre solicitudes elegibles para priorizar revision del propietario. F2 pondera recall '
         '(beta=2, decision academica), no un costo monetario aprobado. Se reportan precision, recall, F1, F2 y accuracy; '
         'accuracy sola oculta el desbalance. Ningun score concede fiado ni confirma solvencia.\n\n'
         'El MVP conserva el flujo cliente > evaluacion > fiado > pagos. Las once entradas son snapshots anteriores a evaluar; '
         'IDs, fechas, escenario, saldo al corte y pagos futuros son metadatos excluidos. completed_sales aqui solo incluye ventas '
         'ligadas a credito, no toda venta al contado del negocio.\n\n'
         'Se evalua transferencia a clientes sinteticos disjuntos del mismo simulador, no validacion real ni temporal prospectiva. '
         'No se consulta la base real actual ni se publican archivos privados del propietario.')
    counts_table = table(['Fase estudio', 'Intentos', 'Bloqueos', 'Manual', 'Elegibles', 'Conocidos', 'Clases 0/1', '?'], [
        ['DEV', dev['study_attempts'], dev['routing']['blocked_pending_balance'], 0, dev['study_rows'], dev['known_rows'], '448/86', dev['unknown_rows']],
        ['FINAL', final['study_attempts'], final['routing']['blocked_pending_balance'], 0, final['study_rows'], final['known_rows'], '234/41', final['unknown_rows']]])
    page('2. Poblaciones y denominadores', counts_table + '\n\n'
         'Bloqueos y derivaciones humanas no son clase 0 ni clase 1, aciertos ni errores del modelo. '
         'Las metricas se condicionan a elegibilidad y desenlace conocido. Los siete desconocidos DEV y dos FINAL '
         'pueden competir por la cola pero no ajustan, calibran ni puntuan metricas supervisadas.\n\n'
         'Cero derivaciones manuales en estudio no significa que la regla se retiro. Los primeros fiados sin historial '
         'pertenecen al warmup: decisiones simuladas autorizadas por propietario, fuera de aprendizaje y evaluacion. '
         'Sus liquidaciones observadas pueden aportar historial posterior legitimo.\n\n' + table(
             ['Historia', 'Clientes ejemplo', 'Warmup fiados', 'Fiados estudio', 'Hard pass', 'Aceptacion global'],
             [[label, a['clients'], a['warmup_loans'], a['study_loans'], a['hard_constraints_pass'], a['coherence_accepted']]
              for label, a in zip(('DEV D1', 'DEV D2', 'FINAL'), [*dev['audits'], *final['audits']], strict=True)]) + '\n\n'
         'Las historias son mundos alternativos de un negocio, no sucursales simultaneas ni volumen real sumable. '
         'Doce clientes constituyen un roster de ejemplo, no una poblacion real fija; pueden cambiar semana a semana.')
    page('3. Dos reglas antes del modelo',
         'Primero: cualquier saldo positivo bloquea, incluso vigente, parcial o con acuerdo. Solo la liquidacion completa '
         'observada estrictamente antes de evaluar restablece elegibilidad, nunca aprobacion automatica.\n\n'
         'Segundo: deuda cero no confirmada o ausencia de fiados totalmente pagados confirmados deriva a revision del propietario. '
         'La deuda positiva tiene prioridad sobre falta de historial. Ambos estados evitan consultar el modelo y no producen score.\n\n'
         + table(['Prueba independiente', 'Resultado verificado', 'Modelo llamado'], [[g['case'], g['actual'], 'false'] for g in gates])
         + '\n\nEstas siete pruebas ejecutan solo la funcion pura pre_model_decision cuyo hash coincide con el protocolo. '
         'No cargan artefactos ni ejecutan inferencia. El caso elegible solo verifica que el gate permita continuar; tampoco llama al modelo. '
         'No son prueba de despliegue, CLI o reproduccion experimental. Evidencia: pruebas-reglas-previas.json.')
    page('4. Fuente y coherencia acotada',
         'Rildo reviso 23 elementos intencionales V5: 12 fiados, cuatro rechazos, cuatro semanas y tres supuestos. '
         'No reviso todas las nuevas filas ni aprobo rendimiento predictivo. Los agregados declarados proceden de recuerdo y '
         'revision parcial de cuaderno: 48 anotaciones, 45 evaluables, ocho tardias y tres desconocidas; no son entrenamiento.\n\n'
         'La referencia aproximada de 12 fiados a nueve clientes por semana no obliga a un volumen fijo. '
         'La precision de montos enteros o .50 y horarios variados procede de la aclaracion; precios exactos tambien se permiten. '
         'La mezcla 75/25, distribuciones latentes, rotacion finita, warmup y corte exacto 20:00 siguen siendo supuestos del equipo.\n\n'
         'El simulador no cambio: montos S/5..50, cupo supuesto S/80, lognormal truncada y heterogeneidad Beta, '
         'abonos supuestos 10/48 y fraccion 0.5, pagos en ventanas 08:00..12:00 y 16:00..20:00. '
         'Planes finitos de liquidacion no estiman perdida permanente. No se cambia semilla para mejorar resultados.\n\n'
         '**Hard constraints pass=true no equivale a aceptacion global. coherence_accepted=false se conserva en las tres historias.** '
         'Las restricciones verifican rangos, integridad temporal y cero otorgamientos con saldo previo; no validez externa. '
         'Los controles no convierten datos simulados en datos reales ni sustituyen revision humana.')
    page('5. EDA y contrato de entradas',
         '![Balance y antiguedad frente a ventas completadas: solo 534 filas DEV conocidas.](figuras/eda-dev.png)\n\n'
         f"Atraso DEV: {counts[1]}/{len(known)} = {100 * counts[1] / len(known):.4f} %. "
         'El desbalance exige comparar Dummy y deteccion de clase minoritaria. Antiguedad e historial muestran asociaciones '
         'del simulador, no efectos causales ni evidencia de clientes reales.\n\n'
         'Cinco entradas constantes por elegibilidad: ' + ', '.join(constants) + '. '
         'completed_sales = paid_credits; no son dos senales independientes. Se preserva contrato sin fabricar variacion.\n\n'
         + table(['Entradas', 'Sentido y preparacion'], [
             ['completed_sales, paid_credits, paid_late', 'Conteos previos; historial de liquidacion y atraso'],
             ['pending_overdue/current, outstanding, utilization, overdue_rate', 'Pendientes/exposicion: cero en elegibles'],
             ['requested_ratio', 'Monto solicitado / cupo supuesto 80'],
             ['tenure_days, punctuality_rate', 'Dias desde alta; (pagados - tardios) / pagados']]))
    page('6. Metodo y seleccion congelada',
         'Pipeline por pliegue: mediana y StandardScaler ajustados solo en entrenamiento conocido. Once variables numericas; '
         'sin one-hot ni sobremuestreo. SVM requiere escalado; se conserva procedimiento comparable en arbol y Dummy.\n\n'
         'Tres folds externos StratifiedGroupKFold por client_id y tres internos para calibracion sigmoid SVM, ensemble=false. '
         'El SVC lineal usa probability=false. Los folds internos permanecen dentro del entrenamiento externo. '
         'Clientes disjuntos y ambas clases en cada subconjunto; unknowns no calibran.\n\n'
         '![Grilla heredada: 18 configuraciones por siete umbrales; sin ajuste posterior.](figuras/metodo-grilla.png)\n\n'
         'Se maximiza F2 OOF de politica con capacidad; desempates: recall, precision, F1, menos revisiones, orden de grilla, '
         'cercania a 0.5 y menor umbral. Dummy usa 0.5. No precision minima predeclarada.\n\n'
         'OOF se reutiliza para elegir configuracion y umbral: hay optimismo de seleccion. Calibracion interna agrupada '
         'no es evaluacion anidada independiente de toda la busqueda. FINAL se genero una vez tras congelar seleccion y hashes; '
         'un lote por cada familia sobre 277 elegibles, incluidos dos desconocidos, segun report_checks.json.')
    page('7. Ganador y comparacion OOF', summary + '\n\n'
         f"SVM: {json.dumps(s['params'], sort_keys=True)}; umbral {s['threshold']}. "
         f"Arbol comparador: {json.dumps(t['params'], sort_keys=True)}; umbral {t['threshold']}.\n\n"
         + table(headers, oof_policy) + '\n\n'
         'La diferencia OOF entre familias es pequena y no establece superioridad estadistica. La cola OOF se forma '
         'por fold, replica y fecha, no como competencia conjunta bajo un unico modelo desplegado.\n\n'
         'Semillas nuevas DEV: ' + ', '.join(str(r['seed']) for r in protocol['development_replicas'])
         + '; FINAL: ' + str(protocol['final_replica']['seed']) + '; CV externa/interna: '
         + str(protocol['cv']['outer_seed']) + '/' + str(protocol['cv']['inner_seed']) + '. '
         'Los prefijos PND6F-R1-D1/D2/T identifican clientes nuevos. Esta revision dentro de V6 no borra ni reemplaza evidencia historica.')
    page('8. FINAL: RAW y politica',
         'RAW aplica umbral sin limite diario; POLICY aplica la cola limitada. Positiva=atraso, n=275 conocidos. '
         'Precision indefinida se informa como cero. No se incluyen los dos desconocidos como puntuales.\n\n'
         '## RAW FINAL\n\n' + table(headers, raw_final) + '\n\n## POLICY FINAL\n\n' + table(headers, policy_final)
         + '\n\n' + summary + '\n\n'
         'Dummy mayoritario puede tener accuracy alta sin detectar atrasos. Dummy positivo RAW y limitado no son la misma '
         'decision ni el mismo numero de revisiones. Se conservan ambos baselines, incluso cuando la precision de SVM es baja. '
         'No hay intervalos de confianza independientes por transaccion: son fiados repetidos por cliente sintetico.')
    errors = sorted(models['svm']['error_cases'], key=lambda e: e['loan_id'])[:3]
    for error in errors:
        index = models['svm']['error_cases'].index(error)
        printed.append(dict(path=['models', 'svm', 'error_cases', index, 'probability'],
                            text=f"{error['probability']:.8f}"))
    page('9. Errores e interpretacion prudente',
         '![Matriz SVM FINAL: filas reales, columnas predichas, orden 0/1.](figuras/confusion-final.png)\n\n'
         '166 TN, 68 FP, nueve FN y 32 TP. Detectar 32 de 41 atrasos no oculta nueve omisiones. '
         'Las falsas alertas generan trabajo; un score bajo no garantiza puntualidad.\n\n'
         + table(['Caso (primeros por ID)', 'Tipo RAW/POLICY', 'Real/predicho', 'Score'], [
             [e['loan_id'], e['raw_error'] + '/' + e['policy_error'], f"{e['actual']}/{e['predicted']}", f"{e['probability']:.8f}"] for e in errors])
         + '\n\nUn historial puntual puede preceder un atraso y uno tardio puede preceder un pago puntual; '
         'son hipotesis interpretativas, no causas probadas. Se usan tres errores deterministas del cache, no otra prediccion. '
         'Coeficientes estandarizados SVM describen el margen, no probabilidades ni impactos causales; calibracion convierte '
         'margen a score y no demuestra calibracion en poblacion real. El anexo conserva todos los coeficientes.')
    page('10. Cola y utilidad no demostrada',
         'Umbral > ordenar score descendente > desempate por ID ficticio > hasta cinco alertas por replica y dia civil Lima. '
         'Dos minutos por caso y cinco/dia son hipotesis no medidas, no capacidad aprobada.\n\n'
         + table(queue_headers, queues) + '\n\n' + burden + '\n\n'
         'La cola cuenta alertas sobre fiados otorgados elegibles, no todo el trabajo del negocio. Bloqueos, '
         'revision obligatoria del primer fiado, cobranza y otras tareas no se consideran gratuitas ni aciertos. '
         'Dos desconocidos FINAL quedan fuera de alertas SVM; la tabla conserva su participacion en otras politicas.\n\n'
         'Antes de recomendar uso: medir tiempos ANTES/DESPUES en periodos comparables, obtener desenlaces maduros, '
         'registrar FN/FP y consecuencias, acordar costos y tolerancias con el propietario. No se demuestra reduccion de '
         'perdidas, aumento de ventas ni ahorro operativo real.')
    page('11. Ejemplo e integracion: evidencia guardada',
         'Ejemplo ficticio distinto de los vectores de estudio, etiqueta desconocida. Solicitud S/20 sobre cupo S/80, '
         'deuda cero, seis fiados pagados y uno tardio. Solo se muestra la salida ya persistida.\n\n'
         + table(['Campo guardado', 'Valor'], [[k, str(illustration[k])] for k in
                 ('family', 'probability', 'threshold', 'predicted', 'known_label', 'business_approval', 'review_policy_applied')])
         + '\n\nScore superior al umbral: candidato a revision, no aprobacion ni acierto demostrado. '
         'Una solicitud aislada no ejecuta la cola diaria; known_label=null impide afirmar correccion. '
         'No se repite inferencia para confeccionar este informe.\n\n'
         '**Estado tecnico consultable en manifiesto.** Esta edicion no acredita nuevo despliegue, reproduccion independiente, '
         'latencia ni ensayo humano de V6 Final. La demo historica no prueba instalacion de estos artefactos. '
         'Produccion intacta: no se modifican servicios, runners ni paquetes.\n\n'
         'Integracion propuesta para PROY: snapshot validado > dos gates > artefacto confiable versionado > score > '
         'cola compartida > decision humana y auditoria. Requiere pruebas transaccionales, autenticacion, rollback y '
         'piloto real autorizado antes de operar; Joblib solo desde origen confiable.')
    page('12. Riesgos, gobernanza y cierre',
         'Ley N. 29733 y D.S. N. 016-2024-JUS: marco documental de privacidad, no certificacion juridica actualizada. '
         'Antes de clientes reales: finalidad y base juridica, informacion/consentimiento aplicable, minimizacion, '
         'accesos, conservacion, seguridad y derechos ARCO. Solo se leen fuentes agregadas sanitizadas, no documentos '
         'privados, identidades de clientes ni firmas.\n\n'
         + table(['Riesgo', 'Control propuesto; responsable por confirmar'], [
             ['Generalizacion sintetica limitada', 'Piloto real consentido y test prospectivo nuevo; no retocar este FINAL'],
             ['Nueve FN y 68 FP', 'Acordar tolerancias y medir consecuencias/minutos'],
             ['Integracion y version incorrecta', 'QA de contrato, hashes, gates y rollback'],
             ['Privacidad y aceptacion incompleta', 'Revision legal y grupal antes de operar']]) + '\n\n'
         'Conclusiones: V6 Final selecciona SVM en DEV y conserva la ventaja del arbol en FINAL sin reseleccion. '
         'La evidencia permite estudiar priorizacion, no aprobar creditos. Hard pass y menor cola no implican '
         'coherencia global aceptada, utilidad real ni autorizacion comercial. El simulador y sus limitaciones permanecen.\n\n'
         'Cuatro revisiones individuales pendientes: Omara Baylon, Tamara Covenas, Cesar Paredes y Pablo Yman. '
         'Asignacion de exposicion y ensayo pendientes; no se inventan firmas, aportes confirmados ni autorizaciones. '
         'Asistencia IA: redaccion y exportacion automatizada; verificacion humana de contenido y entrega aun pendiente.')
    body_pages = len(pages) - 1
    assert body_pages <= 15
    page('Referencias y trazabilidad',
         'Grupo 2 (2026). APF1/APF2, continuidad del problema y MVP, segun documentacion heredada. '
         'No se adjuntan fuentes privadas ni se atribuye nueva auditoria a esos documentos.\n\n'
         'Protocolo v6-final-r1: revision_protocol.json. Protocolo heredado de datos/modelado: '
         'APF3_PENDING_V6_DATA_PROTOCOL.json y APF3_PENDING_V6_MODEL_PROTOCOL.json. '
         'Fuentes agregadas: APF3_OWNER_ANCHORS_V4.json y APF3_OWNER_REVIEW_V5.json.\n\n'
         'Resultados primarios: pending_v6_report.json, frozen_selection.json, final_cache_*.json, '
         'illustrative_output.json y report_checks.json, todos bajo experiment/. '
         'Plan de folds y congelacion: planned_folds.json y freeze_before_final.json.\n\n'
         'Pedregosa et al. (2011). Scikit-learn: Machine Learning in Python. JMLR 12, 2825-2830. '
         'Congreso del Peru (2011). Ley N. 29733. MINJUSDH (2024). D.S. N. 016-2024-JUS.\n\n'
         'El manifiesto documental registra hashes de entradas y salidas, verificaciones de texto PDF y geometria. '
         'No equivale a certificacion experimental o revision humana. Estado tecnico consultable en manifiesto.')
    page('Anexo A. Ajuste aparente frente a OOF', table(headers, training) + '\n\n'
         'Train es ajuste aparente, no evaluacion independiente. Las diferencias train/OOF permiten examinar sobreajuste '
         'sin concluir causalidad ni cambiar umbral. OOF usado en seleccion tiene optimismo. '
         'Arbol limita profundidad y hoja; SVM regulariza con C y calibra dentro de grupos. '
         'Los valores son exactamente los persistidos; no se ajusta ningun estimador al exportar.')
    coeff = models['svm']['interpretation']['standardized_coefficients']
    for feature, value in coeff.items():
        printed.append(dict(path=['models', 'svm', 'interpretation', 'standardized_coefficients', feature],
                            text=f'{value:.8f}'))
    page('Anexo B. Entradas, margen y ejemplo',
         table(['Variable', 'Coeficiente SVM estandarizado', 'Entrada ilustrativa'], [
             [f, f'{coeff[f]:.8f}', illustration['features'][f]] for f in report['feature_names']]) + '\n\n'
         'Puntualidad negativa y paid_late positivo describen asociaciones del margen dentro del simulador; no efectos '
         'de cambiar el comportamiento. Coeficientes de variables duplicadas reparten contribucion; constantes no '
         'tienen capacidad explicativa. El score ilustrativo proviene del artefacto seleccionado ya ejecutado y guardado.\n\n'
         'Los errores completos, once entradas de cada caso y metricas integrales permanecen en experiment/. '
         'No se copian archivos privados ni se alteran artefactos para presentar resultados.')

    name = 'APF3_Informe_V6_Final'
    text = '\n\n<!-- PAGE -->\n\n'.join(pages) + '\n'
    (out / (name + '.md')).write_text(text)
    doc_result = documents.documents(text, out, name=name, expected_figures=3)

    def finish_document(folder, stem, count):
        html_path = folder / (stem + '.html')
        markup = html_path.read_text().replace('APF3 - Credify - Borrador', 'APF3 - V6 Final')
        # Fixed A4 content boxes make the offline bounds checks meaningful.
        markup = markup.replace('</style>',
            '.page{height:259mm;position:relative;display:flow-root;padding-bottom:10mm}'
            '.page:after{content:"' + STATUS + '";position:absolute;bottom:1mm;left:0;font-size:8pt;color:#526572}'
            'body{width:174mm} .page:first-child h1{margin-top:12mm}'
            'h1{color:#10283F}th{background:#E1ECE6}img{max-height:78mm}'
            '</style>')
        html_path.write_text(markup)
        doc = Document(folder / (stem + '.docx'))
        doc.core_properties.title = stem + ' / ' + STATUS
        for section in doc.sections:
            section.footer.paragraphs[0].runs[0].text = STATUS + ' | '
        doc.save(folder / (stem + '.docx'))
        return render(folder, stem, 'guide', count)

    renders = {}

    def render(folder, stem, kind, count):
        result = subprocess.run(['node', '--input-type=module', '-e', browser,
            str(folder / (stem + '.html')), str(folder / (stem + '.pdf')), kind,
            str(defense / 'vistas')], env=dict(os.environ, PLAYWRIGHT_MODULE_PATH=playwright),
            capture_output=True, text=True, check=False)
        if result.returncode:
            raise RuntimeError(result.stderr)
        audit = json.loads(result.stdout)
        pdf = PdfReader(folder / (stem + '.pdf'))
        assert len(pdf.pages) == len(audit['sections']) == count
        return {**audit, 'pdf_pages': count}

    renders['report'] = finish_document(out, name, len(pages))
    # Reuse the same evidence rows in native editable tables, not screenshots.
    deck = []
    notes = []

    def slide(title, spoken, lines=(), data=None, image=None, dark=False):
        number = len(deck) + 1
        item = dict(number=number, title=title, dark=dark, notes=spoken, elements=[])
        def txt(value, x, y, w, h, size, **style):
            item['elements'].append(dict(kind='text', text=value, x=x, y=y, w=w, h=h, size=size, **style))
        txt('UTP / GRUPO 2 / V6 FINAL r1', .65, .24, 10, .25, 10)
        txt(title, .65, .8, 12, .9, 29, bold=True)
        if data:
            heads, rows, widths = data
            item['elements'].append(dict(kind='table', headers=heads, rows=rows, widths=widths,
                x=.65, y=1.95, w=12, h=.64 * (len(rows) + 1), row_height=.64, size=16))
        if image:
            item['elements'].append(dict(kind='image', path=str(out / 'figuras' / image),
                                         x=.65, y=1.9, w=12, h=3.8))
        start = 5.4 if data or image else 2.1
        for i, line in enumerate(lines):
            txt(line, .65, start + i * .58, 12, .52, 20)
        txt(STATUS + f' / {number:02}/13', .65, 7.16, 12, .2, 9)
        deck.append(item)
        notes.append('## ' + str(number) + '. ' + title + '\n\n' + spoken)

    slide('Fiado a un dia: evidencia, no aprobacion',
          'El problema de APF1 continua en el MVP de APF2. APF3 estudia priorizacion humana con datos simulados. '
          'Esta es V6 Final r1, no otra version numerada. Se preserva V6 historico; no se toca produccion.',
          ['Cerveceria Baylon / Credify / APF3', 'V6 Final: revision prospectiva r1 dentro del mismo nombre',
           'V6 historico preservado / cuatro revisiones humanas pendientes'], dark=True)
    slide('Elegibilidad antes de cualquier score',
          'Cualquier saldo bloquea, vigente o parcial. Sin historial pagado confirmado, revision del propietario. '
          'La deuda tiene prioridad. Siete pruebas de la funcion pura pasan sin llamar al modelo. Bloqueos no son aciertos.',
          ['Saldo positivo -> bloqueo, aunque no haya vencido', 'Deuda no confirmada o sin historial -> revision humana',
           'Deuda cero + historial confirmado -> puede evaluar, no aprobar', '7 pruebas independientes / 0 llamadas al modelo'])
    slide('Poblaciones: no mezclar denominadores',
          'DEV estudio registra 586 intentos y FINAL 292. Cero manuales no elimina el gate: los primeros fiados estan '
          'en warmup. Desconocidos compiten en cola, no se imputan ni entran a metricas.',
          ['Manual=0 por warmup, no por eliminar la regla', 'Bloqueos fuera de accuracy; desconocidos nunca son clase 0'],
          data=(['Estudio', 'Intentos', 'Bloqueos', 'Elegibles', 'Conocidos', '?'],
                [['DEV', 586, 45, 541, 534, 7], ['FINAL', 292, 15, 277, 275, 2]], [2, 2, 2, 2, 2, 2]))
    slide('EDA DEV: senal sintetica, no causalidad',
          'Hay 448 puntuales y 86 atrasos conocidos. Son fiados repetidos por cliente, no personas independientes. '
          'Cinco entradas son cero y ventas completadas duplica fiados pagados. No fabricamos variacion.',
          ['448 puntuales / 86 atrasos / 7 etiquetas desconocidas', '5 constantes cero; completed_sales = paid_credits'], image='eda-dev.png')
    slide('Metodo: grupos, calibracion y grilla fija',
          'Tres folds externos por cliente y tres internos de calibracion sigmoid. Mediana y escalado se ajustan solo '
          'dentro de entrenamiento. Hay 126 pares. OOF selecciona: conserva optimismo, no es evaluacion anidada completa.',
          ['3 folds externos por cliente + calibracion interna agrupada', 'OOF reutilizado para seleccion: optimismo explicito'], image='metodo-grilla.png')
    slide('Seleccion OOF: SVM, umbral 0.1',
          summary + ' SVM C uno, balanced, lineal, probability false; sigmoid interno. '
          'El arbol comparador tiene profundidad tres, hoja dieciseis y sin ponderacion. No cambiamos con FINAL.',
          [f'SVM F2 OOF politica {f2s:.8f}', f'Arbol F2 OOF politica {f2t:.8f}',
           'SVM: C=1 / balanced / lineal / sigmoid interno', 'Umbral 0.1 congelado antes de FINAL'], dark=True)
    slide('Comparacion RAW FINAL',
          'Se muestran las cinco metricas para SVM, arbol y ambos Dummy. Accuracy sola no sirve para detectar atrasos. '
          'El arbol logra mejor F2 FINAL; observarlo no autoriza reseleccion.',
          ['275 conocidos / 234 puntuales y 41 atrasos', 'Arbol FINAL mejor: se informa, no se reselecciona'],
          data=(['RAW FINAL', *headers[2:]], [[r[0], *r[2:]] for r in raw_final], [2.8, 1.84, 1.84, 1.84, 1.84, 1.84]))
    slide('Comparacion POLICY FINAL',
          'La politica limita cinco por replica y fecha. Son decisiones distintas de RAW en general. '
          'Los desconocidos compiten sin etiqueta. Se conservan los dos baselines y la carga completa en el informe.',
          ['Cinco/dia es hipotesis; no capacidad validada', 'Unknowns fuera de metricas; pueden consumir cola'],
          data=(['POLICY', *headers[2:]], [[r[0], *r[2:]] for r in policy_final], [2.8, 1.84, 1.84, 1.84, 1.84, 1.84]))
    slide('Matriz SVM: errores visibles',
          'SVM detecta 32 de 41 atrasos, pero omite nueve. Produce 68 falsas alertas. Precision 0.32; '
          'un pasado puntual no garantiza el siguiente pago. Los primeros errores por ID se conservan en el informe.',
          ['166 TN / 68 FP / 9 FN / 32 TP', 'Precision 0.32; recall 32/41; F2 0.60606061'], image='confusion-final.png')
    slide('Menor cola no significa ahorro',
          burden + ' Los dos minutos por caso son una hipotesis. Necesitamos tiempos reales comparables y costos de omitir atrasos.',
          ['SVM 100 revisiones / Dummy positivo limitado 274', '174 menos x 2 = 348 minutos HIPOTETICOS',
           'FN: 9 frente a 0 / FP SVM: 68', 'No ahorro medido; no ganancias garantizadas'])
    slide('Ejemplo: salida guardada del artefacto',
          f"Ejemplo S/20, seis pagados, uno tarde. Score persistido {illustration['probability']}, umbral 0.1. "
          'Etiqueta desconocida: no demuestra acierto. No corremos inferencia en la exposicion documental. '
          'La cola requiere lote; no se aplica a este ejemplo aislado.',
          [f"SVM score {illustration['probability']} > {illustration['threshold']}",
           'predicted=1 / known_label=null / business_approval=false',
           'Salida persistida; no nueva inferencia ni demo certificada'])
    slide('Alcance tecnico y revision de fuente',
          'Rildo reviso 23 elementos V5, no todas las filas nuevas. Doce clientes son un ejemplo. '
          'Hard pass no significa coherence accepted: sigue falso. Estado tecnico consultable en manifiesto; '
          'esta exportacion no certifica despliegue ni reproduccion de V6 Final.',
          ['23 items V5 revisados, no filas nuevas aprobadas', 'Hard pass=true / coherence_accepted=false',
           'Mismo simulador; nuevas semillas y clientes ficticios', 'Estado tecnico consultable en manifiesto; produccion intacta'])
    slide('Cierre: antes de operar, medir y revisar',
          'No hay autorizacion comercial ni firmas inventadas. Las cuatro revisiones individuales y ensayo siguen pendientes. '
          'Para PROY hacen falta piloto real autorizado, privacidad conforme a Ley 29733, QA de integracion y costos acordados. '
          'La seleccion se conserva, incluidos sus nueve FN; evidencia academica no es validacion empresarial.',
          ['Piloto real autorizado + tiempos/FN/FP y consecuencias', 'Privacidad, QA transaccional y decision humana',
           '4 revisiones individuales + ensayo: pendientes'], dark=True)
    assert len(deck) == 13
    stem = 'APF3_Sustentacion_V6_Final'
    renderer.export_slides(deck, defense, name=stem, version='V6 Final r1')
    native = Presentation(defense / (stem + '.pptx'))
    native_checks = 0
    for item, slide_native in zip(deck, native.slides, strict=True):
        assert item['notes'] == slide_native.notes_slide.notes_text_frame.text
        assert len(item['elements']) == len(slide_native.shapes)
        for element, shape in zip(item['elements'], slide_native.shapes, strict=True):
            for key, actual in [('x', shape.left), ('y', shape.top), ('w', shape.width), ('h', shape.height)]:
                assert abs(actual / 914400 - element[key]) < .00001
            if element['kind'] == 'text':
                assert shape.text == element['text']
            elif element['kind'] == 'table':
                assert [[c.text for c in row.cells] for row in shape.table.rows] == [
                    [str(v) for v in row] for row in [element['headers'], *element['rows']]]
            else:
                assert hashlib.sha256(shape.image.blob).hexdigest() == sha(Path(element['path']))
            native_checks += 1
    renders['deck'] = render(defense, stem, 'deck', 13)
    guide_pages = ['# Guion conciso V6 Final\n\n' + STATUS + '\n\n'
                   'Guion de apoyo, no ensayo certificado. Distribucion de expositores por confirmar. '
                   'No se ejecuta entrenamiento, inferencia ni simulacion. Propuesta: 10-12 minutos, duracion real pendiente.\n\n'
                   + '\n\n'.join(notes[:4]),
                   '# Guion: metodo y resultados\n\n' + '\n\n'.join(notes[4:9]),
                   '# Guion: utilidad, limites y cierre\n\n' + '\n\n'.join(notes[9:]) + '\n\n'
                   'Revision pendiente: Omara Baylon, Tamara Covenas, Cesar Paredes y Pablo Yman. '
                   'No hay firmas ni roles confirmados. Si preguntan por despliegue/reproduccion: estado tecnico consultable '
                   'en manifiesto, sin afirmar exito no verificado.']
    guide = '\n\n<!-- PAGE -->\n\n'.join(guide_pages)
    guide_name = 'APF3_Guion_V6_Final'
    (defense / (guide_name + '.md')).write_text(guide + '\n')
    documents.documents(guide, defense, name=guide_name, expected_figures=0)
    renders['guide'] = finish_document(defense, guide_name, 3)

    # Check full PDF text blocks and every native/PDF metric table cell.
    report_pdf = PdfReader(out / (name + '.pdf'))
    for source_page, pdf_page in zip(pages, report_pdf.pages, strict=True):
        extracted = normalized(pdf_page.extract_text())
        for block in source_page.split('\n\n'):
            if block.startswith('!['):
                continue
            if block.startswith('|'):
                for line in block.splitlines()[2:]:
                    for cell in line.strip('|').split('|'):
                        assert normalized(cell) in extracted, cell
            else:
                plain = re.sub(r'(?m)^#+ ', '', block).replace('**', '').replace('`', '')
                assert normalized(plain) in extracted, plain
    report_text = normalized('\n'.join(p.extract_text() for p in report_pdf.pages))
    for cell in printed:
        value = report
        for key in cell['path']:
            value = value[key]
        expected = f'{value:.8f}' if isinstance(value, float) else str(value)
        assert cell['text'] == expected and normalized(expected) in report_text
    deck_pdf = PdfReader(defense / (stem + '.pdf'))
    for item, pdf_page in zip(deck, deck_pdf.pages, strict=True):
        extracted = normalized(pdf_page.extract_text())
        for element in item['elements']:
            if element['kind'] == 'text':
                assert normalized(element['text']) in extracted, element['text']
            elif element['kind'] == 'table':
                assert all(normalized(str(v)) in extracted for row in [element['headers'], *element['rows']] for v in row)
    guide_pdf = normalized('\n'.join(p.extract_text() for p in PdfReader(defense / (guide_name + '.pdf')).pages))
    assert all(normalized(item['notes']) in guide_pdf for item in deck)
    for folder, document_name, source_pages in ((out, name, pages), (defense, guide_name, guide_pages)):
        word = Document(folder / (document_name + '.docx'))
        word_text = normalized(''.join(word.element.xpath('.//w:t/text()')))
        assert len(word.element.xpath('.//w:br[@w:type="page"]')) == len(source_pages) - 1
        for source_page in source_pages:
            for block in source_page.split('\n\n'):
                if block.startswith('!['):
                    continue
                if block.startswith('|'):
                    assert all(normalized(cell) in word_text for line in block.splitlines()[2:]
                               for cell in line.strip('|').split('|'))
                else:
                    plain = re.sub(r'(?m)^#+ ', '', block).replace('**', '').replace('`', '')
                    assert normalized(plain) in word_text, plain
    assert not any(n.startswith(('sklearn', 'joblib')) for n in __import__('sys').modules)
    assert all(sha(Path(p)) == digest for p, digest in sources.items()), 'Input changed during export'
    result_md = ('# APF3 Resultados V6 Final\n\n' + summary + '\n\n' + counts_table + '\n\n'
                 + burden + '\n\nV6 Final r1 es revision prospectiva tras consultar V6 historico, que se conserva. '
                 'Simulador y supuestos sin cambios; semillas nuevas 2026112601/02/03 y clientes disjuntos. '
                 'Sin targets desconocidos imputados a cero. Gates separados de accuracy; cero manuales de estudio por warmup. '
                 'Siete pruebas independientes de gates sin llamada al modelo.\n\n'
                 + table(headers, raw_final) + '\n\n## Politica FINAL\n\n' + table(headers, policy_final)
                 + '\n\nMatriz SVM [[166,68],[9,32]]. OOF seleccionado conserva optimismo; calibracion interna agrupada '
                 'no es evaluacion anidada de toda la seleccion. coherence_accepted=false; revision de 23 elementos V5 '
                 'no equivale a aprobacion de filas nuevas. Doce clientes son roster de ejemplo.\n\n'
                 f'Informe: {len(pages)} paginas PDF, portada + {body_pages} cuerpo + referencias + 2 anexos. '
                 'Sustentacion: 13 diapositivas editables y 13 paginas PDF; guion: 3 paginas PDF. '
                 'Texto y bounds offline verificados. Contenido Word/PPTX, saltos Word y geometria PPTX verificados; '
                 'no renderizados por Microsoft Office.\n\n'
                 'Estado tecnico consultable en manifiesto. No se acredita nuevo despliegue ni reproduccion; '
                 'produccion intacta. Revision de cuatro integrantes y ensayo pendientes, sin roles ni firmas confirmados.\n\n'
                 'Salidas: /Users/tamaraalison/Downloads/APF3_Grupo2_V6_Final/informe y sustentacion. '
                 'Verificacion: informe/verificacion-documentos.json; SHA-256: informe/manifiesto-archivos.json.\n\n'
                 'Comando desde la raiz del repositorio:\n\n```bash\n'
                 + TEMP + '/apf3-informe-venv/bin/python deploy/generate-v6-final-documents.py\n```\n')
    result_path = REPO / 'docs/APF3_RESULTADOS_V6_FINAL.md'
    result_path.write_text(result_md)
    verification = dict(display_name='V6 Final', revision_id='v6-final-r1',
        generated_utc=datetime.now(UTC).isoformat(), passed=True, report_pages=len(pages),
        report_body_pages=body_pages, report_cover_pages=1, references_pages=1, appendix_pages=2,
        slides=13, guide_pages=3, metric_table_cells_checked=len(printed), metric_cells=printed,
        native_elements_checked=native_checks, native_word_text_and_page_breaks_checked=True,
        render=renders, pdf_text_checked=True,
        new_training=False, new_predictions=False, new_simulation=False, ml_runtime_imported=False,
        raw_private_files_read=False, pure_gate_tests=len(gates), grouped_folds_checked=fold_checks,
        metric_objects_recomputed_from_confusion=24, source_hashes_unchanged=True,
        technical_status='Estado tecnico consultable en manifiesto; no nuevo despliegue o reproduccion acreditados por esta exportacion',
        production_touched=False, human_reviews_pending=4, human_rehearsal='pending', roles='unconfirmed',
        source_sha256=sources, source_sha256_after={p: sha(Path(p)) for p in sources},
        caveat='PDF rendered offline with Chromium; native Word/PowerPoint application rendering not executed')
    dump(out / 'verificacion-documentos.json', verification)
    output_paths = [p for folder in (out, defense) for p in folder.rglob('*')
                    if p.is_file() and p.name != 'manifiesto-archivos.json']
    dump(out / 'manifiesto-archivos.json', dict(
        display_name='V6 Final', source_sha256=sources,
        output_sha256={str(p.relative_to(root)): sha(p) for p in output_paths},
        repository_output_sha256={str(result_path.relative_to(REPO)): sha(result_path)},
        self_hash_excluded=True, deployment_or_reproduction_claim=False))
    print(json.dumps({k: verification[k] for k in ('passed', 'report_pages', 'report_body_pages', 'slides',
                      'guide_pages', 'metric_table_cells_checked', 'pure_gate_tests', 'source_hashes_unchanged')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', type=Path, default=ROOT)
    parser.add_argument('--playwright-module', default=PLAYWRIGHT)
    args = parser.parse_args()
    generate(args.root.resolve(), args.playwright_module)
