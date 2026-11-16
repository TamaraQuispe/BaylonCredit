"""Isolated helper tests only. Never call finalize/main or read the delivery roots."""

import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile, ZipInfo

SPEC = importlib.util.spec_from_file_location(
    'final_delivery', Path(__file__).with_name('finalize-aligned-v4-delivery.py'))
delivery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(delivery)
TEMP = '/private/var/folders/sx/_6ljw37n2_j9hk2f_vtqplj40000gn/T/opencode'


class FinalDeliveryTests(unittest.TestCase):
    def test_unsafe_relative_paths(self):
        for name in ('', '.', '..', '../x', '/x', 'x/../y', 'x\\y', 'x//y', './x', 'x/', 'x\x00'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                delivery.relative(name)
        self.assertEqual(delivery.relative('informe/file.pdf'), 'informe/file.pdf')

    def test_hash_map_checks_actual_bytes_and_missing_inputs(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as directory:
            root = Path(directory)
            path = root / 'source.txt'
            path.write_bytes(b'original')
            snapshot = {}
            mapping = {'source.txt': delivery.sha(b'original')}
            delivery.check_hashes(root, mapping, snapshot=snapshot)
            self.assertEqual(snapshot, {path: mapping['source.txt']})
            path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'SHA mismatch'):
                delivery.check_hashes(root, mapping)
            path.unlink()
            with self.assertRaises(OSError):
                delivery.check_hashes(root, mapping)

    def test_external_sources_are_explicit_and_verified(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as directory:
            path = Path(directory) / 'input.json'
            path.write_bytes(b'{}')
            mapping = {str(path): delivery.sha(b'{}')}
            with self.assertRaisesRegex(ValueError, 'Absolute output'):
                delivery.check_hashes(Path(directory), mapping)
            delivery.check_hashes(Path(directory), mapping, external=True)

    def test_bad_hash_maps_and_traversal(self):
        for mapping in ({}, {'x': 'bad'}, {'../x': '0' * 64}, {'x': delivery.PRIVATE_SHA}):
            with self.subTest(mapping=mapping), self.assertRaises(ValueError):
                delivery.check_hashes(Path(TEMP), mapping)

    def test_symlink_including_parent_is_refused(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as directory:
            root = Path(directory)
            (root / 'real').mkdir()
            (root / 'real/file').write_bytes(b'bytes')
            (root / 'link').symlink_to(root / 'real', target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'Symlink'):
                delivery.read(root / 'link/file')
            with self.assertRaisesRegex(ValueError, 'Symlink'):
                delivery.tree(root)

    def test_private_secret_backup_paths_refused_before_open(self):
        for name in ('.env', '.env.example', '.env/nested', 'credentials.json', 'id_rsa',
                     'APF3_Ficha_Propietario_Baylon.docx', 'x.bak', 'backup.zip', 'private.pem'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                delivery.read(Path(TEMP) / name)

    def test_credential_content_refused(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as directory:
            path = Path(directory) / 'content.txt'
            path.write_bytes(b'-----BEGIN PRIVATE KEY-----')
            with self.assertRaisesRegex(ValueError, 'Credential'):
                delivery.read(path)

    def test_inventory_excludes_only_caches(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as directory:
            root = Path(directory)
            (root / '__pycache__').mkdir()
            (root / '__pycache__/cached.pyc').write_bytes(b'cached')
            (root / '.DS_Store').write_bytes(b'metadata')
            (root / 'evidence.json').write_bytes(b'{}')
            self.assertEqual(delivery.tree(root), {'evidence.json': b'{}'})

    def test_zip_crc_inventory_sha_and_symlink(self):
        def archive(entries):
            buffer = io.BytesIO()
            with ZipFile(buffer, 'w') as z:
                for name, data in entries:
                    z.writestr(name, data)
            return buffer.getvalue()

        mapping = {'file.txt': delivery.sha(b'evidence')}
        valid = archive([('root/file.txt', b'evidence')])
        delivery.check_zip(valid, mapping, 'root/')
        for data in (archive([('root/file.txt', b'tampered')]),
                     archive([('elsewhere/file.txt', b'evidence')]),
                     archive([('root/file.txt', b'evidence'), ('extra', b'x')])):
            with self.subTest(data=data), self.assertRaises(ValueError):
                delivery.check_zip(data, mapping, 'root/')
        info = ZipInfo('root/file.txt')
        info.external_attr = 0o120777 << 16
        with self.assertRaisesRegex(ValueError, 'symlink'):
            delivery.check_zip(archive([(info, b'evidence')]), mapping, 'root/')
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            delivery.check_zip(valid, {'../file.txt': mapping['file.txt']}, 'root/')

    def test_render_sections_reject_overflow_and_missing_title(self):
        audit = {'overflow': False,
                 'sections': [{'title': 'Title', 'height_px': 100, 'overflow': []}]}
        delivery.sections(audit, ['Title body'], 973)
        with self.assertRaises(ValueError):
            delivery.sections(audit, ['different'], 973)
        audit['sections'][0]['height_px'] = 974
        with self.assertRaisesRegex(ValueError, 'overflow'):
            delivery.sections(audit, ['Title'], 973)

    def test_json_encoding_and_global_manifest_excludes_self(self):
        files = {'evidence.json': b'{}'}
        manifest = {'files': delivery.hashes(files), 'excludes_self': 'manifest-entrega.json'}
        decoded = json.loads(delivery.encoded(manifest))
        self.assertNotIn('manifest-entrega.json', decoded['files'])
        self.assertEqual(decoded['files']['evidence.json'], delivery.sha(b'{}'))


if __name__ == '__main__':
    unittest.main()
