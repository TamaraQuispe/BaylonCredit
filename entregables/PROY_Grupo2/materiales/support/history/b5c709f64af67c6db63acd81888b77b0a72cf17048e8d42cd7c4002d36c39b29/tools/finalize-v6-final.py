"""Read-only, stdlib V6 Final evidence verification and fail-closed packaging.

Never imports an experiment runner, loads an estimator, or generates observations.
Support files are exclusive writes; the four frozen input trees are read only.
"""

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import os
import re
import stat
import tempfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[1]
ROOT = Path('/Users/tamaraalison/Downloads/APF3_Grupo2_V6_Final')
OLD = ROOT.with_name('APF3_Grupo2_Entrega_V6')
ORIGINAL = ROOT.with_name('APF3_Grupo2_Experimento_V6')
CODE = Path('/private/var/folders/sx/_6ljw37n2_j9hk2f_vtqplj40000gn/T/opencode/v6-academic-code')
PINS = {
    'final_manifest.json': '471e5bd3849e8ee8f2d79254823eb4dcfd7a679d67b49efc6257d467224a06cf',
    'freeze_before_final.json': '2faccb7cf2248a4eed21753b6b6dc336f82aaea5e1b19a589a912974d5837f7d',
    'revision_protocol.json': '7e489955792aab975c8ff14a95a77e70095a1c8a2ed1682847851773b8922541',
}
POLICY = '418af45fcdc1a5d952daac7aa5139bfa87d2a66ef126255f306cff3c66591f1f'
RUNNER = 'eac29527d158918b21c4a9bd88e447913ed113e902ce6f050e3246dfde2ac034'
FAMILIES = ('tree', 'svm', 'most_frequent', 'constant_1')
METRICS = ('precision', 'recall', 'f1', 'f2', 'accuracy')
FROZEN = ('experiment', 'development', 'informe', 'sustentacion')
PRIVATE = {'82d4c748b3403e8a3e45b4361b95e9da4ffaf0b0ca21e3a9ac4baedc6040f29b',
           '45bc22a10ad5dccf323708b8aeabb780d8de4629ff5087cca2582c7dd055819f'}


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def relative(name):
    require(isinstance(name, str) and name and '\\' not in name and ':' not in name
            and '\x00' not in name, f'Unsafe path: {name!r}')
    p = PurePosixPath(name)
    require(not p.is_absolute() and '..' not in p.parts and p.as_posix() == name
            and name != '.', f'Unsafe path: {name!r}')
    for part in p.parts:
        lower = part.lower()
        require(not lower.startswith('.env') and lower not in
                {'__pycache__', '.cache', '.pytest_cache', '.git', 'credentials.json',
                 'secrets.json', 'id_rsa', 'id_ed25519', '.ds_store'}
                and not lower.endswith(('.pem', '.key', '.pyc', '.pyo')),
                f'Forbidden package member: {name}')
    return name


def safe(path):
    path = Path(os.path.abspath(path))
    require(not any(p.is_symlink() for p in (path, *path.parents)), f'Symlink: {path}')
    return path


def read(path):
    path = safe(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), f'Not regular: {path}')
        return stream.read()


def load(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f'Duplicate JSON key: {key}')
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda x: require(False, f'Nonfinite JSON: {x}'))


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def tree(root):
    root = safe(root)
    require(root.is_dir(), f'Missing directory: {root}')
    result = {}
    for directory, dirs, names in os.walk(root, followlinks=False):
        for name in dirs + names:
            safe(Path(directory, name))
        for name in sorted(names):
            path = Path(directory, name)
            key = relative(path.relative_to(root).as_posix())
            result[key] = read(path)
    return result


def hashes(files):
    return {n: sha(d) for n, d in sorted(files.items())}


def check_hashes(files, expected, exact=False):
    require(bool(expected), 'Empty hash map')
    if exact:
        require(set(files) == set(expected), 'Inventory mismatch')
    for name, digest in expected.items():
        relative(name)
        require(isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest),
                f'Invalid digest: {name}')
        require(name in files and sha(files[name]) == digest, f'SHA256 mismatch: {name}')


def scan(data, name):
    relative(name)
    require(sha(data) not in PRIVATE, f'Private owner document: {name}')
    # Split signatures so this verifier can itself be included in the archive.
    forbidden = rb'-----BEGIN ' + rb'(?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----'
    require(not re.search(forbidden + rb'|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}'
                          rb'|sk-(?:proj-|or-v1-)[A-Za-z0-9_-]{20,}', data),
            f'Secret signature: {name}')
    if name.endswith(('.docx', '.pptx', '.zip')):
        with ZipFile(io.BytesIO(data)) as archive:
            require(archive.testzip() is None, f'CRC failure: {name}')
            names = [i.filename for i in archive.infolist()]
            require(len(names) == len(set(names)), f'Duplicate member: {name}')
            for item in archive.infolist():
                relative(item.filename.rstrip('/'))
                require(not stat.S_ISLNK(item.external_attr >> 16), 'Archive symlink')
                if not item.is_dir():
                    scan(archive.read(item), item.filename)


def classification(labels, predictions):
    require(len(labels) == len(predictions) and bool(labels), 'Invalid metric inputs')
    cm = [[0, 0], [0, 0]]
    for y, p in zip(labels, predictions, strict=True):
        require(type(y) is int and y in (0, 1) and p in (0, 1), 'Invalid class')
        cm[y][p] += 1
    (tn, fp), (fn, tp) = cm
    return dict(n=len(labels), precision=tp / (tp + fp or 1),
                recall=tp / (tp + fn or 1), f1=2 * tp / (2 * tp + fp + fn or 1),
                f2=5 * tp / (5 * tp + fp + 4 * fn or 1), accuracy=(tn + tp) / len(labels),
                confusion_matrix=cm, confusion_labels=[0, 1])


def compare_metrics(actual, expected):
    for key, value in actual.items():
        require(expected[key] == value, f'Exact metric mismatch: {key}: {expected[key]} != {value}')


def evaluate(rows, scores, threshold, spec, assignments=None):
    require(len(rows) == len(scores) and all(type(s) in (int, float) and
            math.isfinite(s) and 0 <= s <= 1 for s in scores), 'Invalid score cache')
    require(len({r['loan_id'] for r in rows}) == len(rows), 'Duplicate loan IDs')
    known = [i for i, r in enumerate(rows) if r['late_payment'] is not None]
    raw = classification([rows[i]['late_payment'] for i in known],
                         [int(scores[i] >= threshold) for i in known])
    groups = defaultdict(list)
    require(assignments is None or len(assignments) == len(rows), 'Fold vector length')
    for i, row in enumerate(rows):
        at = datetime.fromisoformat(row['evaluated_at'])
        if at.tzinfo:
            at = at.astimezone(ZoneInfo('America/Lima'))
        groups[(assignments[i] if assignments is not None else -1,
                row['replica_id'], at.date().isoformat())].append(i)
    actions, daily = [0] * len(rows), []
    for (fold, replica, day), indices in sorted(groups.items()):
        queue = sorted((i for i in indices if scores[i] >= threshold),
                       key=lambda i: (-scores[i], rows[i]['loan_id']))
        accepted = queue[:spec['daily_cap']]
        for i in accepted:
            actions[i] = 1
        record = dict(replica_id=replica, evaluation_civil_date=day, before_cap=len(queue),
                      reviews=len(accepted), minutes_hypothetical=len(accepted) * spec['minutes_per_case'])
        if assignments is not None:
            record = {'outer_fold': fold, **record}
        daily.append(record)
    policy = dict(metrics=classification([rows[i]['late_payment'] for i in known],
                                        [actions[i] for i in known]), reviews=sum(actions),
                  reviews_known=sum(actions[i] for i in known),
                  reviews_unknown=sum(actions) - sum(actions[i] for i in known),
                  daily_max=max(d['reviews'] for d in daily),
                  days_over_before_cap=sum(d['before_cap'] > spec['daily_cap'] for d in daily),
                  capacity_respected=all(d['reviews'] <= spec['daily_cap'] for d in daily),
                  minutes_hypothetical=sum(actions) * spec['minutes_per_case'], daily=daily)
    return raw, policy, actions


def compare_evaluation(rows, scores, threshold, spec, expected, assignments=None):
    raw, policy, actions = evaluate(rows, scores, threshold, spec, assignments)
    compare_metrics(raw, expected['metrics'])
    for key, value in policy.items():
        require(value == expected['review_policy'][key], f'Exact queue mismatch: {key}')
    if assignments is None:
        per_replica = {}
        for replica in sorted({r['replica_id'] for r in rows}):
            days = [d for d in policy['daily'] if d['replica_id'] == replica]
            per_replica[replica] = dict(reviews=sum(d['reviews'] for d in days),
                daily_max=max(d['reviews'] for d in days),
                days_over_before_cap=sum(d['before_cap'] > spec['daily_cap'] for d in days),
                minutes_hypothetical=sum(d['minutes_hypothetical'] for d in days))
        require(expected['review_policy']['per_replica'] == per_replica, 'Per-replica queue mismatch')
    else:
        for fold in expected['fold_metrics']:
            indices = [i for i, number in enumerate(assignments) if number == fold['outer_fold']]
            compare_evaluation([rows[i] for i in indices], [scores[i] for i in indices],
                               threshold, spec, fold)
    return actions


def rank(entry):
    policy = entry['review_policy']
    m = policy['metrics']
    return (m['f2'], m['recall'], m['precision'], m['f1'], -policy['reviews'],
            -entry['candidate_index'], -round(abs(entry['threshold'] - .5), 12), -entry['threshold'])


def verify(root=ROOT, repo=REPO, old=OLD, original=ORIGINAL, code=CODE):
    inputs = {folder: tree(root / folder) for folder in FROZEN}
    exp, dev = inputs['experiment'], inputs['development']
    j = lambda name: load(exp[name])
    checks, blockers = {}, []
    for name, digest in PINS.items():
        require(sha(exp[name]) == digest, f'Untrusted revision: {name}')
    manifest, freeze = j('final_manifest.json'), j('freeze_before_final.json')
    check_hashes({n: d for n, d in exp.items() if n != 'final_manifest.json'}, manifest['files'], True)
    require(len(manifest['files']) == 41, 'Expected all 41 frozen files')
    check_hashes(exp, freeze['files'])
    require(freeze['final_generation_calls'] == freeze['final_prediction_calls'] == 0,
            'FINAL calls occurred before freeze')
    checks['final_manifest_all41_and_prefinal_freeze'] = True
    dm = load(dev['development_manifest.json'])
    check_hashes({n: d for n, d in dev.items() if n != 'development_manifest.json'}, dm['files'], True)
    require(dev['development_manifest.json'] == exp['development_manifest.json'], 'DEV manifest drift')
    for n in dev.keys() & exp.keys():
        require(dev[n] == exp[n], f'DEV copied evidence drift: {n}')
    checks['development_manifest_and_copied_evidence_unchanged'] = True
    provenance, prepared = j('provenance.json'), j('preparation_manifest.json')
    protocol, effective = j('revision_protocol.json'), j('effective_protocol.json')
    report, selection = j('pending_v6_report.json'), j('frozen_selection.json')
    for record in (manifest, freeze, provenance, prepared, protocol, report, selection, dm):
        require(record['revision_id'] == 'v6-final-r1' and record['display_name'] == 'V6 Final'
                and record['version'] == 'academic-owner-pending-v6', 'Revision identity')
    for record in (provenance, prepared, report, selection, dm):
        require(record['origen'] == 'simulado' and record['research_only'] is True
                and record['business_approval'] is False, 'Research-only mode')
    require(report['selection'] == selection and report['provenance'] == provenance,
            'Report binding mismatch')
    require(provenance['protocol_sha256'] == PINS['revision_protocol.json'] and
            provenance['policy_sha256'] == protocol['policy_sha256'] == POLICY, 'Policy/protocol pin')
    require(read(repo / 'docs/APF3_PENDING_V6_FINAL_PROTOCOL.json') == exp['revision_protocol.json'],
            'Repository protocol drift')
    codefiles = tree(code)
    old_manifest = load(read(old / 'manifest-entrega.json'))
    expected_code = {n.removeprefix('codigo/'): d for n, d in old_manifest['files'].items()
                     if n.startswith('codigo/')}
    require(len(expected_code) == 21, 'Expected immutable 21-file codepack')
    check_hashes(codefiles, expected_code, True)
    check_hashes(tree(old / 'codigo'), expected_code, True)
    source_paths = {}
    for name, digest in provenance['code_sha256'].items():
        if name == '/revision/academic_credit_pending_v6_final.py':
            p = repo / 'backend/scripts/academic_credit_pending_v6_final.py'
            require(digest == RUNNER, 'Frozen runner pin')
        elif name == '/revision/policy.py':
            p = repo / 'backend/app/services/academic_v6_policy.py'
            require(digest == POLICY, 'Frozen policy pin')
        else:
            require(name.startswith('/app/'), 'Unexpected provenance path')
            p = code / relative(name.removeprefix('/app/'))
        require(sha(read(p)) == digest, f'Frozen code drift: {name}')
        source_paths[name] = str(p)
    for key in ('protocol_sha256', 'source_sha256', 'code_sha256', 'policy_sha256', 'runtime'):
        require(prepared[key] == provenance[key], f'Preparation evidence drift: {key}')
    check_hashes(exp, provenance['source_sha256'])
    check_hashes(exp, j('artifact_manifest.json'))
    require(report['artifact_sha256'] == j('artifact_manifest.json'), 'Artifact report binding')
    require(sha(dev['development_manifest.json']) == provenance['development_manifest_sha256'],
            'Provenance development binding')
    require(provenance['runtime'] == protocol['runtime'] == effective['runtime'], 'Runtime metadata')
    require(protocol['development_replicas'] == prepared['development_replicas'] == [
        {'seed': 2026112601, 'prefix': 'PND6F-R1-D1'},
        {'seed': 2026112602, 'prefix': 'PND6F-R1-D2'}] and
        protocol['final_replica'] == {'seed': 2026112603, 'prefix': 'PND6F-R1-T'} and
        protocol['cv'] == {'outer_seed': 2026112604, 'inner_seed': 2026112605, 'folds': 3},
        'Fixed seeds and CV metadata')
    require(prepared['final_generated'] is False and prepared['model_fit_performed'] is False,
            'Preparation mode')
    checks['codepack21_runner_policy_sources_artifacts_preparation_bound'] = True
    worlds = [load(dev[f"{r['prefix']}_transactions.json"]) for r in protocol['development_replicas']]
    final_world = j('final_transactions.json')
    for world, spec in zip([*worlds, final_world],
                           [*protocol['development_replicas'], protocol['final_replica']], strict=True):
        require(world['seed'] == spec['seed'] and world['prefix'] == spec['prefix']
                and world['origen'] == 'simulado', 'Cohort seed/mode metadata')
    dev_clients = {c['client_id'] for w in worlds for c in w['clients']}
    final_clients = {c['client_id'] for c in final_world['clients']}
    require(not dev_clients & final_clients, 'DEV/FINAL client overlap')
    study, known = j('development_study_rows.json'), j('development_known_rows.json')
    final_rows = list(csv.DictReader(io.StringIO(exp['final_eligible.csv'].decode())))
    for r in final_rows:
        r['late_payment'] = int(r['late_payment']) if r['late_payment'] else None
    require(known == [r for r in study if r['late_payment'] is not None], 'Known-only fit rows')
    require((len(study), len(known), len(final_rows)) == (541, 534, 277), 'Population counts')
    for rows in (study, final_rows):
        require(all(float(r['paid_credits']) > 0 and all(float(r[k]) == 0 for k in
                    ('pending_current', 'pending_overdue', 'outstanding', 'utilization', 'overdue_rate'))
                    for r in rows), 'Ineligible row in model population')
    require({r['client_id'] for r in study} == dev_clients and
            {r['client_id'] for r in final_rows} == final_clients, 'Row/client roster mismatch')
    require(sum(r['late_payment'] is not None for r in final_rows) == 275, 'FINAL known labels')
    plan = j('planned_folds.json')
    outer_by_client = {}
    for group in [plan['outer'], *plan['inner_sigmoid_by_outer_train'], plan['inner_sigmoid_full_train']]:
        require(group['n_splits'] == len(group['folds']) == 3, 'Exactly three grouped folds required')
        for fold in group['folds']:
            sets = []
            for side in ('train', 'validation'):
                indices = fold[side + '_indices']
                clients = {known[i]['client_id'] for i in indices}
                require(clients == set(fold[side + '_clients']), 'Fold indices/client mismatch')
                counts = Counter(str(known[i]['late_payment']) for i in indices)
                require(dict(counts) == fold[side + '_class_counts'] and set(counts) == {'0', '1'},
                        'Fold class feasibility')
                sets.append(clients)
            require(not sets[0] & sets[1], 'Grouped fold leakage')
    for fold in plan['outer']['folds']:
        for client in fold['validation_clients']:
            require(client not in outer_by_client, 'Duplicate OOF client')
            outer_by_client[client] = fold['fold']
    require(set(outer_by_client) == dev_clients, 'Incomplete OOF clients')
    checks['seeds_modes_eligibility_known_labels_and_grouped_disjoint_clients'] = True
    # This is the only imported source: the hash-checked stdlib-only pre-model guard.
    policy_path = Path(source_paths['/revision/policy.py'])
    spec = importlib.util.spec_from_file_location('frozen_pure_policy', policy_path)
    policy = importlib.util.module_from_spec(spec)
    # Execute verified bytes without creating __pycache__ in the source tree.
    exec(compile(read(policy_path), str(policy_path), 'exec'), policy.__dict__)
    null_fields = ('probability', 'model_probabilities', 'prediction', 'predicted', 'threshold', 'family')
    caches = {f: j(f'final_cache_{f}.json') for f in FAMILIES}
    for name in ('development_routing_ledger.json', 'final_routing_before_scoring.json', 'final_routing_ledger.json'):
        ledger = j(name)
        for entry in ledger:
            decision = policy.pre_model_decision(entry['features'])
            if decision is not None:
                require(entry['decision'] == decision['decision'] and not entry['model_called']
                        and all(entry.get(k) is None for k in null_fields), 'Guarded entry has model output')
            elif name != 'final_routing_ledger.json':
                require(not entry['model_called'] and entry['probability'] is None, 'Scoring before freeze')
            elif entry['granted']:
                index = caches['svm']['score_loan_ids'].index(entry['loan_id'])
                require(entry['model_called'] is True and entry['probability'] == caches['svm']['scores'][index]
                        and entry['model_probabilities'] == {f: caches[f]['scores'][index] for f in FAMILIES},
                        'Final ledger/cache mismatch')
            else:
                require(entry['model_called'] is False and all(entry.get(k) is None for k in null_fields),
                        'Refused entry has model output')
        expected_rows = study if name.startswith('development') else final_rows
        require({e['loan_id'] for e in ledger if e['decision'] == 'model_eligible' and e['granted']}
                == {r['loan_id'] for r in expected_rows}, 'Routing/eligible population mismatch')
    illustrative = j('illustrative_input.json')
    gates = []
    for updates, expected in (({'outstanding': 30}, 'blocked_pending_balance'),
                              ({'outstanding': 10, 'paid_credits': 0}, 'blocked_pending_balance'),
                              ({'paid_credits': 0}, 'requires_owner_review'),
                              ({'paid_credits': None}, 'requires_owner_review'),
                              ({'outstanding': None}, 'requires_owner_review')):
        features = {**illustrative['features'], **updates}
        decision = policy.pre_model_decision(features)
        require(decision['decision'] == expected, 'Pure policy gate failed')
        gates.append(dict(features=features, decision=expected, model_called=False, probability=None))
    checks['all_routing_ledgers_and_debt_history_unknown_gates'] = True
    rc, calls = j('report_checks.json'), j('final_call_ledger.json')
    require(rc['final_generation_calls'] == report['final']['generation_calls'] == 1 and
            rc['final_batch_calls'] == calls and set(calls) == set(FAMILIES), 'FINAL call ledger')
    require(all(c == dict(batch_calls=1, rows_scored=277, unknown_rows_scored=2)
                for c in calls.values()), 'FINAL must be one batch per family')
    require(all(rc[k] is True for k in ('freeze_unchanged', 'development_unchanged',
                'clients_disjoint', 'capacity_respected', 'no_reseed')), 'Persisted report checks')
    checks['one_final_generation_one_batch_per_family_recorded'] = True
    search, training = j('cv_search.json'), j('training_reports.json')
    require(search['study_loan_ids'] == [r['loan_id'] for r in study], 'OOF row alignment')
    entries = []
    for candidate in [*search['candidates'], *search['baselines'].values()]:
        require(candidate['oof_prediction_counts'] == [1] * len(study), 'OOF coverage')
        require(candidate['outer_fold'] == [outer_by_client[r['client_id']] for r in study],
                'OOF grouped assignments')
        for entry in candidate['threshold_results']:
            compare_evaluation(study, candidate['oof_probabilities'], entry['threshold'],
                               effective['review_policy'], entry, candidate['outer_fold'])
            if entry['family'] in ('tree', 'svm'):
                entries.append(entry)
    for family in ('tree', 'svm'):
        require(selection['families'][family] == max((e for e in entries if e['family'] == family), key=rank),
                'Frozen family does not match full OOF ranking')
    winner = selection['global_winner']
    require(winner == max(selection['families'].values(), key=rank) and winner['family'] == 'svm'
            and winner['threshold'] == .1, 'Frozen global OOF winner')
    require(manifest['files']['selected_model.joblib'] == manifest['files']['svm.joblib'], 'Selected model bytes')
    predictions = j('final_predictions.json')
    for family in FAMILIES:
        cache, model = caches[family], report['models'][family]
        require(cache == predictions[family] and cache['metrics'] == model['final'] and
                cache['review_policy'] == model['review_policy']['final'], 'FINAL report/cache binding')
        require(cache['score_loan_ids'] == [r['loan_id'] for r in final_rows], 'FINAL score row alignment')
        actions = compare_evaluation(final_rows, cache['scores'], model['threshold'],
                                     effective['review_policy'], cache)
        by_id = {p['loan_id']: p for p in cache['predictions']}
        for i, r in enumerate(final_rows):
            p = by_id[r['loan_id']]
            require(p['actual'] == r['late_payment'] and p['probability'] == cache['scores'][i]
                    and p['predicted'] == int(cache['scores'][i] >= model['threshold'])
                    and p['review'] == actions[i] and p['threshold'] == model['threshold'],
                    'Cached FINAL prediction/action mismatch')
        choice = selection['families'].get(family, search['baselines'].get(family))
        require(model['threshold'] == training[family]['threshold'] == choice['threshold'], 'Threshold binding')
        for split in ('train', 'oof'):
            require(model[split] == training[family][split] and model['review_policy'][split]
                    == training[family]['review_policy'][split], f'{split} report binding')
            matrix = model[split]['confusion_matrix']
            labels, predicted = [], []
            for y in (0, 1):
                for p in (0, 1):
                    labels.extend([y] * matrix[y][p])
                    predicted.extend([p] * matrix[y][p])
            compare_metrics(classification(labels, predicted), model[split])
            queue = model['review_policy'][split]
            (tn, fp), (fn, tp) = queue['metrics']['confusion_matrix']
            labels = [0] * (tn + fp) + [1] * (fn + tp)
            predicted = [0] * tn + [1] * fp + [0] * fn + [1] * tp
            compare_metrics(classification(labels, predicted), queue['metrics'])
            require(queue['reviews'] == queue['reviews_known'] + queue['reviews_unknown']
                    == sum(d['reviews'] for d in queue['daily']) and
                    queue['reviews_known'] == fp + tp and
                    queue['minutes_hypothetical'] == 2 * queue['reviews'] and
                    queue['daily_max'] == max(d['reviews'] for d in queue['daily']) <= 5 and
                    queue['capacity_respected'] is True, 'TRAIN/OOF aggregate queue consistency')
        require(model['oof'] == choice['metrics'] and model['review_policy']['oof'] == choice['review_policy'],
                'Selected OOF/baseline row mismatch')
    require(report['models']['svm']['final']['confusion_matrix'] == [[166, 68], [9, 32]], 'SVM FINAL matrix')
    checks['all_candidate_oof_raw_and_capped_queues_exact'] = True
    checks['selected_family_threshold_tiebreaks_and_both_baselines_exact'] = True
    checks['all_four_final_cached_raw_matrices_metrics_and_queue_actions_exact'] = True
    checks['train_aggregate_matrices_metrics_and_report_bindings_exact'] = True
    # The frozen runner stores only TRAIN aggregates (lines 528-538), not scores.
    blockers.append('TRAIN per-row scores/actions are absent from the 41-file frozen manifest. '
                    'training_reports.json has aggregates only. TRAIN score-based RAW and capped-queue '
                    'reconstruction for all four families cannot be verified without forbidden inference '
                    'or changing frozen evidence. No scores were fabricated; no acceptance waiver assumed.')
    checks['train_cached_score_and_queue_reconstruction'] = False
    document_manifest = load(inputs['informe']['manifiesto-archivos.json'])
    combined = {f'{folder}/{n}': d for folder, files in inputs.items() for n, d in files.items()}
    check_hashes(combined, document_manifest['output_sha256'])
    for p, digest in document_manifest['source_sha256'].items():
        require(sha(read(p)) == digest, f'Document source drift: {p}')
    check_hashes({n: read(repo / n) for n in document_manifest['repository_output_sha256']},
                 document_manifest['repository_output_sha256'])
    docs = load(inputs['informe']['verificacion-documentos.json'])
    require(docs['passed'] and (docs['report_pages'], docs['report_body_pages'], docs['slides'],
            docs['guide_pages']) == (16, 12, 13, 3), 'Document verification record')
    for cell in docs['metric_cells']:
        value = report
        for key in cell['path']:
            value = value[key]
        formatted = str(value) if type(value) is int else f'{value:.8f}'
        require(cell['text'] == formatted, f"Document metric cell mismatch: {cell['path']}")
    checks['document_manifests_sources_and_recorded_16_12_13_3_layout'] = True
    historical = load(read(old / 'verificacion-entrega.json'))['original_sha256']
    require(len(historical) == 57, 'Expected historical 57 files')
    check_hashes(tree(original), historical, True)
    check_hashes(tree(old / 'experimento'), historical, True)
    checks['historical_original_and_delivery_exact57_unchanged'] = True
    deployment_bytes = read(repo / 'deploy/review-v6-final-deployment.json')
    deployment = load(deployment_bytes)
    require(deployment['status'] == 'deployed_and_publicly_verified' and
            deployment['promotion']['status'] == 'passed', 'Incomplete public deployment record')
    comparison = deployment['illustrative_probability_comparison']
    require(comparison['abs_tol'] == 1e-12 and comparison['rel_tol'] == 0 and
            comparison['frozen'] == j('illustrative_output.json')['probability'] and
            comparison['exact_numeric_match'] is False and
            math.isclose(comparison['frozen'], comparison['api_localhost_public_and_browser'],
                         abs_tol=1e-12, rel_tol=0), 'Illustrative-only tolerance record')
    require(deployment['promotion']['model_bytes_features_threshold_class_revision_metrics_exact'] is True,
            'Exact deployment evidence')
    checks['public_deployment_record_and_illustrative_only_tolerance'] = True
    after = {folder: hashes(tree(root / folder)) for folder in FROZEN}
    require(after == {folder: hashes(files) for folder, files in inputs.items()}, 'Frozen evidence changed during checks')
    checks['frozen_trees_unchanged_after_readonly_verification'] = True
    return dict(display_name='V6 Final', revision_id='v6-final-r1', passed=not blockers,
                checks=checks, blockers=blockers, training_executed=False, inference_executed=False,
                cohort_generation_executed=False, independent_training_replay=False,
                claim='Cached metric reconstruction is verification, not a second validation.',
                human_status='PENDIENTE; no signoff fabricated',
                sha256=after, codepack_sha256=expected_code, historical_sha256=historical,
                source_paths=source_paths, deployment_source_sha256=sha(deployment_bytes),
                illustrative_probability_comparison=comparison, gate_cases=gates)


def publish_support(root, files):
    """Validate everything before writing; rollback only files created by this call."""
    root = safe(root)
    require(root.is_dir(), 'Support root missing')
    for name, data in files.items():
        relative(name)
        require(PurePosixPath(name).parts[0] not in FROZEN, 'Frozen tree write forbidden')
        scan(data, name)
        path = safe(root / name)
        require(not path.exists(), f'Refusing overwrite: {path}')
    created, directories = [], []
    try:
        for name, data in files.items():
            path = root / name
            missing = []
            parent = path.parent
            while not parent.exists():
                missing.append(parent)
                parent = parent.parent
            for parent in reversed(missing):
                parent.mkdir()
                directories.append(parent)
            with path.open('xb') as stream:
                created.append(path)
                stream.write(data)
            require(read(path) == data, f'Support write mismatch: {name}')
    except BaseException:
        for path in reversed(created):
            path.unlink()
        for path in reversed(directories):
            path.rmdir()
        raise


def support_files(result, root, repo, code):
    files = {'verificacion-v6-final.json': encoded(result)}
    for name, data in tree(code).items():
        files['codigo-base/' + name] = data
    for original, local in result['source_paths'].items():
        if original.startswith('/revision/'):
            files[original.lstrip('/')] = read(local)
    for name in load(read(root / 'experiment/provenance.json'))['source_sha256']:
        files['sources/' + name] = read(root / 'experiment' / name)
    files['sources/APF3_PENDING_V6_FINAL_PROTOCOL.json'] = read(root / 'experiment/revision_protocol.json')
    for name in ('generate-v6-final-documents.py', 'prepare-v6-final-lab.py',
                 'prepare-aligned-v6-lab.py', 'generate-apf3-report.py',
                 'generate-pending-v6-defense.py', 'generate-apf3-defense.py',
                 'slide-renderer.py', 'finalize-v6-final.py', 'test-finalize-v6-final.py'):
        files['tools/' + name] = read(repo / 'deploy' / name)
    files['sources/APF3_RESULTADOS_V6_FINAL.md'] = read(repo / 'docs/APF3_RESULTADOS_V6_FINAL.md')
    deployment = load(read(repo / 'deploy/review-v6-final-deployment.json'))
    # Whitelist public evidence only; omit host paths, commands, account and DB fingerprints.
    sanitized = {k: deployment[k] for k in ('status', 'display_name', 'revision_id', 'version',
                 'url', 'public_demo_updated', 'reason', 'illustrative_probability_comparison',
                 'observations', 'credentials_or_tokens_recorded')}
    sanitized['promotion'] = {k: deployment['promotion'][k] for k in
        ('status', 'scope', 'final_summary', 'cases', 'api_verified_utc',
         'model_bytes_features_threshold_class_revision_metrics_exact',
         'all_four_families_raw_and_policy_metrics_exact_against_frozen_report')}
    sanitized['source_record_sha256'] = result['deployment_source_sha256']
    sanitized['sanitization'] = 'Whitelist; no commands, host paths, credentials or database fingerprints'
    files['support/review-v6-final-deployment-sanitized.json'] = encoded(sanitized)
    files['requirements.txt'] = ("scikit-learn==1.9.1\nnumpy==2.5.3\nscipy==1.18.1\n"
                                 "joblib==1.6.0\nthreadpoolctl==3.7.0\nSQLAlchemy==2.0.54\n").encode()
    files['Dockerfile'] = b'''FROM python:3.12.14-slim
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY codigo-base /app
COPY revision /revision
COPY tools/reproduce.py /tools/reproduce.py
ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1
WORKDIR /results
ENTRYPOINT ["python", "/tools/reproduce.py"]
'''
    files['tools/reproduce.py'] = b'''"""Explicit future replay/predict harness. Not executed during finalization."""
import argparse
import subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('mode', choices=['replay', 'predict3'])
a = p.parse_args()
base = ['python', '/revision/academic_credit_pending_v6_final.py']
policy = ['--policy-source', '/revision/policy.py']
output = Path('/results/reproduccion' if a.mode == 'replay' else '/results/predict3')
output.mkdir(exist_ok=False)
if a.mode == 'replay':
    protocol = ['--protocol', '/sources/APF3_PENDING_V6_FINAL_PROTOCOL.json',
                '--protocol-sha256', '7e489955792aab975c8ff14a95a77e70095a1c8a2ed1682847851773b8922541']
    subprocess.run(base + ['prepare-dev'] + policy + protocol + ['--sources', '/sources',
                   '--output-dir', str(output / 'development')], check=True)
    subprocess.run(base + ['train-evaluate'] + policy + protocol +
                   ['--development-dir', str(output / 'development'),
                    '--output-dir', str(output / 'experiment')], check=True)
else:
    for case in ('saldo-pendiente', 'sin-historial', 'ilustrativo'):
        subprocess.run(base + ['predict'] + policy + ['--artifact-dir', '/evidence',
                       '--input-json', '/examples/' + case + '.json',
                       '--output-json', str(output / (case + '.json'))], check=True)
'''
    features = load(read(root / 'experiment/illustrative_input.json'))['features']
    for name, updates, decision in (
            ('saldo-pendiente', {'outstanding': 30, 'pending_current': 1}, 'blocked_pending_balance'),
            ('sin-historial', {'paid_credits': 0}, 'requires_owner_review'),
            ('ilustrativo', {}, 'eligible; frozen class 1, threshold 0.1')):
        files[f'ejemplos/{name}.json'] = encoded({'features': {**features, **updates}})
        files[f'ejemplos/{name}-expected.json'] = encoded(dict(
            decision=decision, illustrative_only=True, executed_during_finalization=False,
            model_called_expected=name == 'ilustrativo',
            note='Manual source example, not a cohort row or newly executed inference'))
    files['REPRODUCCION.md'] = b'''# V6 Final: portable recipe, not an executed replay

Finalization uses Python stdlib and cached JSON only. No new training, inference,
cohort generation or independent validation was executed. Human review is pending.
The frozen runner and original 21-file codepack are byte-for-byte preserved.
The pure policy enforces debt before history. Illustrative probability alone has
authorized abs_tol=1e-12, rel_tol=0; no exact numeric inference claim is made.

From this delivery root, with Docker and an EXISTING empty external output directory:

```sh
docker build -t apf3-v6-final .
docker run --rm --network none --read-only --tmpfs /tmp -v "$PWD/sources:/sources:ro" -v "/absolute/new-output:/results" apf3-v6-final replay
docker run --rm --network none --read-only --tmpfs /tmp -v "$PWD/experiment:/evidence:ro" -v "$PWD/ejemplos:/examples:ro" -v "/absolute/new-output:/results" apf3-v6-final predict3
```

Replay creates NEW /results/reproduccion/development and experiment. Predict3 creates
NEW /results/predict3. Both refuse existing targets. Never mount original evidence
writable. Keep /app and /revision paths: future predict verifies those absolute
provenance paths. /sources is read only; /results is the only output mount.
Fixed-seed replay checks reproducibility only, not a second independent validation.
These commands are a recipe, not evidence that an independent replay was performed.
Dependency resolver transitive packages are not claimed fully locked; six direct
requirements and the Python image version are pinned, not an image digest.

Read verificacion-v6-final.json before packaging. A missing TRAIN score cache is a
release blocker, not permission to infer or to modify the frozen experiment.
Document layout is verified against the existing signed-by-hash generation record;
no fresh Word, PowerPoint or PDF rendering is claimed by this stdlib verifier.
'''
    files['support/manifest-support.json'] = encoded(dict(files=hashes(files), self_hash_excluded=True))
    return files


def package(root, destination, result):
    require(result['passed'] is True and not result['blockers'] and
            all(v is True for v in result['checks'].values()), 'Packaging blocked by verification')
    root, destination = safe(root), safe(destination)
    require(not destination.exists() and destination.parent.is_dir(), 'Archive must be new; parent must exist')
    require(not destination.is_relative_to(root), 'Archive cannot be inside delivery')
    files = tree(root)
    for folder in FROZEN:
        require(hashes({n.removeprefix(folder + '/'): d for n, d in files.items()
                       if n.startswith(folder + '/')}) == result['sha256'][folder],
                'Frozen tree changed before packaging')
    for name, data in files.items():
        scan(data, name)
    inventory = hashes(files)
    require('manifest-v6-final.json' not in files, 'Existing package manifest')
    files['manifest-v6-final.json'] = encoded(dict(files=inventory, self_hash_excluded=True,
        scope='All delivery files including docs, provenance, support code and sanitized deployment evidence'))
    fd, temp = tempfile.mkstemp(prefix='.v6-final-', suffix='.zip', dir=destination.parent)
    os.close(fd)
    try:
        with ZipFile(temp, 'w', ZIP_DEFLATED) as archive:
            for name, data in sorted(files.items()):
                archive.writestr(root.name + '/' + relative(name), data)
        with ZipFile(temp) as archive:
            require(archive.testzip() is None, 'ZIP CRC failure')
            expected = {root.name + '/' + n: sha(d) for n, d in files.items()}
            require(len(archive.namelist()) == len(expected) and set(archive.namelist()) == set(expected),
                    'ZIP inventory mismatch')
            for member, digest in expected.items():
                relative(member)
                require(sha(archive.read(member)) == digest, f'ZIP SHA mismatch: {member}')
        require(hashes(tree(root)) == inventory, 'Delivery changed during packaging')
        digest = sha(read(temp))
        # Atomic no-clobber publication on the same filesystem; no partial public ZIP.
        os.link(temp, destination)
        return dict(path=str(destination), sha256=digest, members=len(files),
                    crc_all_passed=True, every_member_sha256=expected)
    finally:
        Path(temp).unlink(missing_ok=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--write-support', action='store_true')
    p.add_argument('--package', action='store_true')
    args = p.parse_args()
    try:
        result = verify(args.root)
        if args.write_support:
            publish_support(args.root, support_files(result, args.root, REPO, CODE))
        if args.package:
            result['archive'] = package(args.root, args.root.with_suffix('.zip'), result)
        print(json.dumps({k: v for k, v in result.items() if k not in
                         ('sha256', 'codepack_sha256', 'historical_sha256', 'source_paths', 'gate_cases')}, indent=2))
        if not result['passed']:
            p.exit(2, 'Release blocked; see verification output. No ZIP published.\n')
    except (ValueError, OSError, KeyError, TypeError) as exc:
        p.exit(1, f'Finalization refused: {exc}\n')


if __name__ == '__main__':
    main()
