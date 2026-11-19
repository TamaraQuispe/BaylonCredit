"""Pruebas de publicacion; no ejecutan entrenamiento ni servicios."""

import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from xml.etree import ElementTree
from zipfile import ZipFile, ZipInfo

SPEC = importlib.util.spec_from_file_location('handoff', Path(__file__).with_name('prepare-proy-handoff.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def archive_bytes(files):
    stream = io.BytesIO()
    with ZipFile(stream, 'w') as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return stream.getvalue()


class HandoffTests(unittest.TestCase):
    def test_unsafe_paths(self):
        for name in ('../escape', '/absolute', 'a/../b', 'a\\b', '.', '', 'C:a'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                MODULE.relative(name)

    def test_metadata_filter_and_nested_root_preserve_bytes(self):
        data = archive_bytes({'A/A/README.md': b'content', 'A/A/data.csv': b'x\n1\n',
                              'A/__MACOSX/A/._README.md': b'metadata',
                              'A/A/.DS_Store': b'metadata'})
        files, ignored, root = MODULE.payload(data)
        self.assertEqual(files, {'README.md': b'content', 'data.csv': b'x\n1\n'})
        self.assertEqual((ignored, root), (2, 'A/A/'))

    def test_symlink_and_private_files_rejected(self):
        stream = io.BytesIO()
        with ZipFile(stream, 'w') as archive:
            item = ZipInfo('A/link')
            item.external_attr = 0o120777 << 16
            archive.writestr(item, 'outside')
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            MODULE.payload(stream.getvalue())
        for name in ('A/.env', 'A/key.pem', 'A/database.dump'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                MODULE.payload(archive_bytes({name: b'private'}))

    def test_wrong_source_hash_does_not_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, target = root / 'source', root / 'target'
            source.mkdir()
            target.mkdir()
            (target / 'README.md').write_bytes(b'keep')
            for name in MODULE.ARCHIVES:
                (source / name).write_bytes(b'not the reviewed ZIP')
            with self.assertRaisesRegex(ValueError, 'ZIP fuente distinto'):
                MODULE.prepare(source, target)
            self.assertEqual(list(target.iterdir()), [target / 'README.md'])
            self.assertEqual((target / 'README.md').read_bytes(), b'keep')

    def test_real_published_inventory_and_document_caveat(self):
        root = Path(__file__).resolve().parents[1] / 'entregables/PROY_Grupo2'
        if not (root / 'inventario-traspaso.json').is_file():
            self.skipTest('Material de traspaso no disponible')
        manifest = json.loads((root / 'inventario-traspaso.json').read_bytes())
        self.assertEqual(len(manifest['files']), 170)
        for name, expected in manifest['files'].items():
            self.assertEqual(MODULE.sha((root / name).read_bytes()), expected, name)
        variants = manifest['source_variants']
        self.assertEqual(variants['APF3_Grupo2.zip']['manifest_mismatches'], [])
        self.assertEqual(sorted(variants['APF3_Grupo2 (1).zip']['manifest_mismatches']),
                         sorted(MODULE.DOCUMENTS))
        self.assertTrue(all(v['official_submission_confirmed'] is False for v in variants.values()))

    def test_guide_requires_all_workshop_models_without_rewriting_apf3(self):
        root = Path(__file__).resolve().parents[1] / 'entregables/PROY_Grupo2'
        guide = root / MODULE.GUIDE
        if not guide.is_file():
            self.skipTest('Guia no disponible')
        self.assertEqual(MODULE.sha(guide.read_bytes()), MODULE.GUIDE_SHA)
        with ZipFile(guide) as archive:
            self.assertIsNone(archive.testzip())
            document = ElementTree.fromstring(archive.read('word/document.xml'))
        text = '\n'.join(t.text or '' for t in document.iter(
            '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))
        for required in ('SVM', 'KNN', 'Arbol de decision', 'AdaBoost', 'P0-05', 'T26',
                         'k=1,3,5,7,9', '50 frente a 400',
                         'No basta con reutilizar la metodologia', 'APF3 YA FUE ENVIADO'):
            self.assertIn(required, text)
        self.assertEqual(len(document.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tbl')), 19)
        amendment = json.loads((root / 'inventario-traspaso.json').read_bytes())['guide_amendment']
        self.assertEqual(amendment['required_models'], ['SVM', 'KNN', 'Arbol de decision', 'AdaBoost'])
        self.assertIs(amendment['apf3_evidence_changed'], False)


if __name__ == '__main__':
    unittest.main()
