"""Explicit future replay/predict harness. Not executed during finalization."""
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
