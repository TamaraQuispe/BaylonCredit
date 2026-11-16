"""No ML execution; publication tests operate exclusively on temporary fixtures."""

import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile, ZipInfo

SPEC = importlib.util.spec_from_file_location(
    'finalize_pending_v6', Path(__file__).with_name('finalize-pending-v6.py'))
FINAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FINAL)


class IntegrityTests(unittest.TestCase):
    def test_hash_bytes_not_json_semantics(self):
        with self.assertRaisesRegex(ValueError, 'SHA mismatch'):
            FINAL.check_hashes({'a.json': b'{ "a": 1 }'}, {'a.json': FINAL.sha(b'{"a":1}')})

    def test_false_hash(self):
        with self.assertRaisesRegex(ValueError, 'SHA mismatch'):
            FINAL.check_hashes({'a': b'good'}, {'a': '0' * 64})

    def test_missing_manifest_keys(self):
        with self.assertRaisesRegex(ValueError, 'Manifest keys'):
            FINAL.check_hashes({'a': b'a'}, {'a': FINAL.sha(b'a')}, {'a', 'b'})

    def test_empty_manifest(self):
        with self.assertRaisesRegex(ValueError, 'Empty hash map'):
            FINAL.check_hashes({}, {})

    def test_invalid_sha_schema(self):
        for value in (True, None, 'abc', 'A' * 64):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'Invalid SHA'):
                FINAL.check_hashes({'a': b'a'}, {'a': value})

    def test_unsafe_paths(self):
        for name in ('../a', '/a', 'a/../b', 'a\\b', './a', 'a//b', 'C:a', '', '.', 'a\x00'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                FINAL.relative(name)

    def test_json_schema_rejects_duplicate_and_nonfinite(self):
        for data in (b'{"x":1,"x":2}', b'{"x":NaN}'):
            with self.assertRaises(ValueError):
                FINAL.load(data)

    def test_checks_do_not_accept_truthy_values(self):
        for value in ({}, {'x': 1}, {'x': 'true'}, {'x': {'y': False}}):
            self.assertFalse(FINAL.all_true(value))
        self.assertTrue(FINAL.all_true({'x': True, 'y': {'z': True}}))

    def test_private_bytes_and_signatures(self):
        with patch.object(FINAL, 'PRIVATE', {FINAL.sha(b'private owner')}):
            with self.assertRaisesRegex(ValueError, 'Private owner'):
                FINAL.scan(b'private owner', 'innocent.dat')
        with self.assertRaisesRegex(ValueError, 'Secret signature'):
            FINAL.scan(b'-----BEGIN PRIVATE KEY-----', 'innocent.dat')

    def test_nested_office_secret(self):
        data = io.BytesIO()
        with ZipFile(data, 'w') as archive:
            archive.writestr('word/document.xml', b'-----BEGIN PRIVATE KEY-----')
        with self.assertRaisesRegex(ValueError, 'Secret signature'):
            FINAL.scan(data.getvalue(), 'report.docx')

    def test_symlinks_and_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / 'link').symlink_to(root / 'absent')
            with self.assertRaisesRegex(ValueError, 'Symlink'):
                FINAL.tree(root)
            with self.assertRaisesRegex(ValueError, 'Secret path'):
                FINAL.safe(root / '.env.production')

    def test_zip_inventory_sha_paths_and_symlinks(self):
        for name, content, mode in (('ROOT/a', b'wrong', 0), ('ROOT/../a', b'a', 0),
                                    ('ROOT/a', b'a', 0o120777 << 16)):
            data = io.BytesIO()
            with ZipFile(data, 'w') as archive:
                info = ZipInfo(name)
                info.external_attr = mode
                archive.writestr(info, content)
            with self.subTest(name=name, mode=mode), self.assertRaises(ValueError):
                FINAL.check_zip(data.getvalue(), {'a': FINAL.sha(b'a')}, 'ROOT/')

    def test_zip_nested_models_allowed(self):
        data = io.BytesIO()
        with ZipFile(data, 'w') as archive:
            archive.writestr('ROOT/experimento/tree.joblib', b'binary model')
        FINAL.check_zip(data.getvalue(), {'experimento/tree.joblib': FINAL.sha(b'binary model')},
                        'ROOT/')

    def test_missing_count_fails_before_any_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            package = {'version': 'pending-v6-delivery-1', 'original_experiment_path': str(root)}
            with self.assertRaisesRegex(ValueError, 'Original count'):
                FINAL.validate(root, root, root, {'manifest-paquete.json': FINAL.encoded(package)}, {})
            self.assertEqual(list(root.iterdir()), [])

    def test_actual_schema_constants_no_ml(self):
        helper = FINAL.package_helper(FINAL.REPO)
        self.assertEqual(len(helper.ARTIFACTS), 7)
        self.assertEqual(len(helper.DEV_NAMES), 12)
        self.assertEqual(len(helper.PROTO_NAMES), 10)
        self.assertIn('selected_model.joblib', helper.ARTIFACTS)
        self.assertIn('provenance.json', helper.DECISIONS)
        self.assertEqual(helper.FREEZE_FILES, helper.DECISIONS |
                         {'frozen_selection.json', 'artifact_manifest.json'})

    @unittest.skipUnless(FINAL.ROOT.is_dir(), 'Local evidence not available')
    def test_existing_evidence_readonly_validation_never_finalize(self):
        before = FINAL.hashes(FINAL.tree(FINAL.ROOT))
        original = FINAL.hashes(FINAL.tree(FINAL.ORIGINAL))
        result = FINAL.validate(FINAL.ROOT, FINAL.ORIGINAL, FINAL.REPO,
                                FINAL.tree(FINAL.ROOT), {})
        self.assertTrue(result['technical_complete'])
        self.assertEqual(result['human_status'], 'PENDIENTE')
        self.assertEqual(FINAL.hashes(FINAL.tree(FINAL.ROOT)), before)
        self.assertEqual(FINAL.hashes(FINAL.tree(FINAL.ORIGINAL)), original)


class PublicationTests(unittest.TestCase):
    def fixture(self, tmp):
        base = Path(tmp).resolve()
        root, original, repo = (base / n for n in ('delivery', 'original', 'repo'))
        for p in (root, original, repo / 'deploy', repo / 'docs'):
            p.mkdir(parents=True)
        (root / 'README.md').write_bytes(b'Historical README\n')
        (root / 'manifest-paquete.json').write_bytes(b'{}')
        for name in ('informe/' + FINAL.NAME + '.pdf', 'informe/' + FINAL.NAME + '.docx',
                     'sustentacion/' + FINAL.NAME + '.pptx',
                     'sustentacion/' + FINAL.NAME + '.pdf',
                     'sustentacion/' + FINAL.GUIDE + '.pdf', FINAL.NAME + '.py',
                     'requirements.txt', 'experimento/illustrative_input.json',
                     'reproducir-v6.py', 'manifest-codepack.json'):
            path = root / name
            path.parent.mkdir(exist_ok=True)
            # Deliberately not parsed: validation is mocked only for transaction tests.
            if path.suffix in ('.docx', '.pptx'):
                with ZipFile(path, 'w') as archive:
                    archive.writestr('fixture.xml', b'fixture')
            else:
                path.write_bytes(b'fixture')
        (repo / 'deploy/tool.py').write_bytes(b'# fixture\n')
        (repo / 'deploy/review-pending-v6-policy-deployment.json').write_bytes(b'{}\n')
        (repo / 'docs' / FINAL.CHECKLIST).write_bytes(b'- [ ] Human review pending\n')
        return root, original, repo

    @staticmethod
    def validation(*_args):
        return {'original_sha256': {}, 'human_status': 'PENDIENTE', 'technical_complete': True}

    def run_fixture(self, root, original, repo):
        with patch.object(FINAL, 'TOOLS', ('tool.py',)), patch.object(
                FINAL, 'validate', side_effect=self.validation):
            return FINAL.finalize(root, original, repo)

    def test_success_exact_zip_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, original, repo = self.fixture(tmp)
            result = self.run_fixture(root, original, repo)
            files = FINAL.tree(root)
            manifest = FINAL.load(files['manifest-entrega.json'])
            self.assertNotIn('manifest-entrega.json', manifest['files'])
            FINAL.check_hashes(files, manifest['files'], set(files) - {'manifest-entrega.json'})
            FINAL.check_zip(Path(result['zip']).read_bytes(), FINAL.hashes(files), root.name + '/')
            self.assertTrue(files['README.md'].startswith(b'Historical README\n'))
            self.assertEqual(files['manifest-paquete.json'], b'{}')
            with self.assertRaisesRegex(ValueError, 'Already exists'):
                self.run_fixture(root, original, repo)

    def test_existing_outputs_block_before_validation(self):
        for name in ('delivery.zip', 'delivery.zip.sha256',
                     'delivery/manifest-entrega.json', 'delivery/verificacion-entrega.json'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root, original, repo = self.fixture(tmp)
                target = Path(tmp) / name
                target.write_bytes(b'existing')
                with patch.object(FINAL, 'validate') as validate:
                    with self.assertRaisesRegex(ValueError, 'Already exists'):
                        FINAL.finalize(root, original, repo)
                    validate.assert_not_called()
                self.assertEqual(target.read_bytes(), b'existing')

    def test_refresh_preserves_history_and_previous_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, original, repo = self.fixture(tmp)
            history = root / 'historial-finalizacion-clientes-nuevos'
            history.mkdir()
            (history / 'manifest-entrega.json').write_bytes(b'historical manifest')
            previous = root.with_suffix('.zip')
            previous.write_bytes(b'previous archive')
            digest = previous.with_suffix('.zip.sha256')
            digest.write_bytes(b'previous digest')
            archive = root.parent / 'delivery-refreshed.zip'
            with patch.object(FINAL, 'TOOLS', ('tool.py',)), patch.object(
                    FINAL, 'validate', side_effect=self.validation):
                result = FINAL.finalize(root, original, repo, archive)
            files = FINAL.tree(root)
            self.assertEqual(files['historial-finalizacion-clientes-nuevos/manifest-entrega.json'],
                             b'historical manifest')
            self.assertEqual(previous.read_bytes(), b'previous archive')
            self.assertEqual(digest.read_bytes(), b'previous digest')
            FINAL.check_zip(Path(result['zip']).read_bytes(), FINAL.hashes(files), root.name + '/')

    def test_missing_checklist_does_not_mutate_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, original, repo = self.fixture(tmp)
            (repo / 'docs' / FINAL.CHECKLIST).unlink()
            before = FINAL.tree(root)
            with self.assertRaises(FileNotFoundError):
                self.run_fixture(root, original, repo)
            self.assertEqual(FINAL.tree(root), before)

    def test_zip_publication_failure_rolls_back_only_own_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, original, repo = self.fixture(tmp)
            before = FINAL.tree(root)
            link = FINAL.os.link

            def fail(source, target):
                if str(target).endswith('.zip.sha256'):
                    (root / 'concurrent.txt').write_bytes(b'not ours')
                    raise OSError('injected publication failure')
                return link(source, target)

            with patch.object(FINAL.os, 'link', side_effect=fail):
                with self.assertRaisesRegex(OSError, 'injected'):
                    self.run_fixture(root, original, repo)
            self.assertEqual(FINAL.tree(root), before | {'concurrent.txt': b'not ours'})
            self.assertFalse(root.with_suffix('.zip').exists())
            self.assertFalse((root / 'anexos').exists())


if __name__ == '__main__':
    unittest.main()
