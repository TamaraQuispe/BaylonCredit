"""Copia evidencia de una ejecucion local verificada, sin entrenar ni cargar modelos."""

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NAMES = (
    'execution.json', 'runtime.json', 'published_comparison.json',
    'guard_cases.json', 'new_example.json', 'new_example_input.json',
    'comparison.csv', 'eda_dev.json', 'eda_dev_descriptives.csv',
    'eda_dev_target_counts.csv', 'eda_dev_relationships.csv', 'eda_dev_relationships.json',
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('outputs', type=Path)
    args = parser.parse_args()
    source = args.outputs.resolve(strict=True)
    manifest = json.loads((source / 'replay_manifest.json').read_bytes())
    for name, digest in manifest['files'].items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Ruta insegura en evidencia')
        path = source / relative
        if path.is_symlink() or sha(path.read_bytes()) != digest:
            raise ValueError(f'Evidencia modificada: {name}')
    execution = json.loads((source / 'execution.json').read_bytes())
    assert execution['training_executed'] is True and execution['independent_evaluation'] is False
    report = json.loads((source / 'experiment/pending_v6_report.json').read_bytes())
    original = json.loads((ROOT / 'experiment/pending_v6_report.json').read_bytes())
    winner, expected = report['selection']['global_winner'], original['selection']['global_winner']
    selection_equal = all(winner[k] == expected[k] for k in ('family', 'params', 'threshold'))
    classifier_equal = all(
        report['models'][family][split][metric] == original['models'][family][split][metric]
        for family in ('tree', 'svm', 'most_frequent', 'constant_1')
        for split in ('train', 'oof', 'final')
        for metric in ('precision', 'recall', 'f1', 'f2', 'accuracy', 'confusion_matrix'))
    assert selection_equal and classifier_equal
    files = {name: (source / name).read_bytes() for name in NAMES}
    record = {
        'incorporated_utc': datetime.now(UTC).isoformat(),
        'scope': 'Evidencia resumida de reproduccion local; no sesion de Google Colab',
        'source_replay_manifest_sha256': sha((source / 'replay_manifest.json').read_bytes()),
        'source_replay_files_all_verified': True,
        'full_replay_tree_attached': False,
        'training_executed': True, 'independent_evaluation': False,
        'selected_family_threshold_params_match': selection_equal,
        'all_families_train_oof_final_classification_metrics_match': classifier_equal,
        'numerical_differences': json.loads(files['published_comparison.json'])['differences'],
        'note': 'Se conservan diferencias de coma flotante; no se afirma igualdad binaria ni se retoco el modelo.',
        'files': {name: sha(data) for name, data in files.items()},
    }
    files['registro-ejecucion.json'] = (json.dumps(record, indent=2) + '\n').encode()
    files['README.md'] = b'''# Evidencia De Ejecucion Local

Resumen de una ejecucion completa del procedimiento fijo V6 Final con Python
3.12.14 y dependencias aisladas. No se uso el FINAL publicado para entrenar.
Las tablas y modelos de experiment/ originales se conservan sin modificar.

registro-ejecucion.json verifica la cadena del run y los archivos aqui copiados.
Familia, parametros, umbral y metricas de clasificacion TRAIN/OOF/FINAL coinciden.
published_comparison.json conserva diferencias numericas de scores agregados,
incluido Brier; no se afirma igualdad binaria entre plataformas.
El campo selection_matches del comparador historico compara todo el registro OOF,
incluidos valores Brier sensibles a redondeo. El registro-ejecucion.json distingue
la igualdad de familia, parametros y umbral de la igualdad numerica completa.

No se adjunta el arbol completo del replay ni se presenta como nueva validacion
independiente. El codigo principal permite repetir el procedimiento en salida nueva.
No acredita acceso a una cuenta Colab, ensayo ni entrega en Aula Virtual.
'''
    destination = ROOT / 'anexos/ejecucion-codigo'
    if destination.exists():
        raise ValueError('La evidencia de ejecucion ya existe; no se sobrescribe')
    destination.mkdir()
    for name, data in files.items():
        with (destination / name).open('xb') as stream:
            stream.write(data)
    print(json.dumps({'source_chain_verified': True, 'copied_files': len(files),
                      'selection_match': selection_equal, 'classification_metrics_match': classifier_equal}))


if __name__ == '__main__':
    main()
