"""Pruebas aisladas; no modifican la entrega ni ejecutan entrenamiento."""

import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('verificador', Path(__file__).with_name('verificar_entrega_actual.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class VerificationTests(unittest.TestCase):
    def test_unsafe_relative_paths(self):
        for name in ('/absolute', '../outside', 'a/../../outside'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                module.checked_relative(name)

    def test_hash_map_detects_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / 'data.csv'
            path.write_bytes(b'one\n')
            expected = {'data.csv': module.digest(path)}
            module.check_map(root, expected)
            path.write_bytes(b'two\n')
            with self.assertRaises(ValueError):
                module.check_map(root, expected)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'original').write_bytes(b'data')
            (root / 'link').symlink_to(root / 'original')
            with self.assertRaises(ValueError):
                module.digest(root / 'link')

    def test_authorized_rename_preserves_bytes_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content = b'original document bytes'
            (root / 'old.pdf').write_bytes(content)
            expected = hashlib.sha256(content).hexdigest()
            docs = (('old.pdf', 'new.pdf', expected),)
            with patch.object(module, 'ROOT', root), patch.object(module, 'DOCUMENTS', docs):
                self.assertEqual(module.normalize_names(), {'new.pdf': expected})
                self.assertEqual(module.normalize_names(), {'new.pdf': expected})
            self.assertEqual((root / 'new.pdf').read_bytes(), content)

    def test_rename_collision_never_overwrites(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'old.pdf').write_bytes(b'old')
            (root / 'new.pdf').write_bytes(b'new')
            with patch.object(module, 'ROOT', root), patch.object(
                    module, 'DOCUMENTS', (('old.pdf', 'new.pdf', module.digest(root / 'old.pdf')),)):
                with self.assertRaises(ValueError):
                    module.normalize_names()
            self.assertEqual((root / 'new.pdf').read_bytes(), b'new')

    def test_all_renames_are_preflighted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'first.pdf').write_bytes(b'first')
            (root / 'second.pptx').write_bytes(b'second')
            docs = (('first.pdf', 'final.pdf', module.digest(root / 'first.pdf')),
                    ('second.pptx', 'final.pptx', '0' * 64))
            with patch.object(module, 'ROOT', root), patch.object(module, 'DOCUMENTS', docs):
                with self.assertRaises(ValueError):
                    module.normalize_names()
            self.assertTrue((root / 'first.pdf').exists())
            self.assertFalse((root / 'final.pdf').exists())


if __name__ == '__main__':
    unittest.main()
