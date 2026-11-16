"""Read-only source checks and isolated preparation safety regression tests."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    'delivery', Path(__file__).with_name('prepare-aligned-v4-delivery.py')
)
delivery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(delivery)
TEMP = '/private/var/folders/sx/_6ljw37n2_j9hk2f_vtqplj40000gn/T/opencode'


class DeliveryTests(unittest.TestCase):
    def test_unsafe_relative_names(self):
        for name in ('../x', '/x', 'x/../y', 'x\\y', '.', 'x//y'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                delivery.relative(name)

    def test_secret_and_cache_exclusion(self):
        for name in ('src/.env', 'backend/.env.example', 'src/__pycache__/x.pyc',
                     'src/key.pem', 'public/ficha_propietario.docx', 'src/credentials.json'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                delivery.clean_source(name, b'harmless')
        with self.assertRaises(ValueError):
            delivery.clean_source('src/example.ts', b'-----BEGIN PRIVATE KEY-----')
        delivery.clean_source('backend/alembic/versions/webauthn_credentials.py', b'# migration')

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as folder:
            link = Path(folder) / 'link'
            link.symlink_to(delivery.SOURCE, target_is_directory=True)
            with self.assertRaises(ValueError):
                delivery.safe(link / 'requirements.txt')

    def test_real_copy_idempotence_and_no_overwrite(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as folder:
            root = Path(folder)
            untouched = root / 'anexos' / 'agent-sentinel.txt'
            untouched.parent.mkdir()
            with untouched.open('xb') as stream:
                stream.write(b'other agent bytes')
            first = delivery.prepare(delivery.SOURCE, root, delivery.REPO, delivery.EVIDENCE)
            second = delivery.prepare(delivery.SOURCE, root, delivery.REPO, delivery.EVIDENCE)
            self.assertEqual(first['created'], second['identical_skipped'])
            self.assertEqual(second['created'], 0)
            self.assertEqual(first['manifest_sha256'], second['manifest_sha256'])
            self.assertEqual(untouched.read_bytes(), b'other agent bytes')
            self.assertFalse((root.parent / (root.name + '.zip')).exists())
            # Simulate a human edit; the preparer must refuse, not restore its README.
            with (root / 'README.md').open('ab') as stream:
                stream.write(b'\nHuman change\n')
            before = delivery.hashes(delivery.tree(root))
            with self.assertRaisesRegex(ValueError, 'Refusing overwrite'):
                delivery.prepare(delivery.SOURCE, root, delivery.REPO, delivery.EVIDENCE)
            self.assertEqual(before, delivery.hashes(delivery.tree(root)))

    def test_refresh_requires_old_hash_and_preserves_snapshot(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as folder:
            root = Path(folder)
            first = delivery.prepare(delivery.SOURCE, root, delivery.REPO, delivery.EVIDENCE)
            snapshot = delivery.read(root / 'laboratorio/codigo_fuente_MVP_V4.zip')
            with patch.object(delivery, 'ROOT_README', delivery.ROOT_README + '\nUpdated own index\n'):
                with self.assertRaisesRegex(ValueError, 'Previous manifest SHA differs'):
                    delivery.prepare(delivery.SOURCE, root, delivery.REPO, delivery.EVIDENCE, '0' * 64)
                result = delivery.prepare(delivery.SOURCE, root, delivery.REPO, delivery.EVIDENCE,
                                          first['manifest_sha256'])
                self.assertEqual(result['refreshed'], 2)
                self.assertEqual(snapshot, delivery.read(root / 'laboratorio/codigo_fuente_MVP_V4.zip'))
                with (root / 'README.md').open('ab') as stream:
                    stream.write(b'Human change')
                with self.assertRaisesRegex(ValueError, 'Refusing overwrite'):
                    delivery.prepare(delivery.SOURCE, root, delivery.REPO, delivery.EVIDENCE,
                                     result['manifest_sha256'])
            self.assertEqual(delivery.hashes(delivery.tree(root / 'codigo')),
                             delivery.hashes(delivery.tree(delivery.SOURCE / 'codigo')))

    def test_root_wrapper_delegates_main_args_and_import_path(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as folder:
            root = Path(folder)
            runner = root / 'codigo/scripts/academic_credit_aligned_v4.py'
            runner.parent.mkdir(parents=True)
            with runner.open('x') as stream:
                stream.write('import json, sys\nprint(json.dumps([__name__, sys.argv, sys.path]))\n')
            wrapper = root / delivery.WRAPPER
            with wrapper.open('xb') as stream:
                stream.write(delivery.read(delivery.REPO / 'deploy/templates/aligned-v4-entrypoint.py'))
            result = json.loads(subprocess.check_output(
                [sys.executable, '-B', str(wrapper), '--example', 'value'], cwd=TEMP, text=True))
            self.assertEqual(result[0], '__main__')
            self.assertEqual(result[1], [str(runner), '--example', 'value'])
            self.assertEqual(result[2][0], str(root / 'codigo'))


if __name__ == '__main__':
    unittest.main()
