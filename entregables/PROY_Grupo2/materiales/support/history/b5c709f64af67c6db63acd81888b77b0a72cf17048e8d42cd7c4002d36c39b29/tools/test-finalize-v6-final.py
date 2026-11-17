"""Stdlib tests: no experiment runner, estimator, training or inference imports."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

spec = importlib.util.spec_from_file_location('finalizer', Path(__file__).with_name('finalize-v6-final.py'))
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


class FinalizerTests(unittest.TestCase):
    def test_corrupt_manifest_and_unsafe_member(self):
        f.check_hashes({'a': b'a'}, {'a': f.sha(b'a')}, True)
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            f.check_hashes({'a': b'b'}, {'a': f.sha(b'a')})
        for name in ('../escape', '/absolute', 'a\\b', 'a/./b', '.env', 'a/key.pem', '__pycache__/x'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                f.relative(name)

    def test_tampered_metrics(self):
        metrics = f.classification([0, 0, 1, 1], [0, 1, 0, 1])
        f.compare_metrics(metrics, metrics)
        with self.assertRaisesRegex(ValueError, 'Exact metric'):
            f.compare_metrics(metrics, {**metrics, 'f2': .9})

    def test_queue_ties_unknown_capacity_and_folds(self):
        rows = [dict(loan_id=n, replica_id='R', evaluated_at='2026-04-13T20:00:00-05:00',
                     late_payment=y) for n, y in [('b', 1), ('a', None), ('c', 0)]]
        raw, policy, actions = f.evaluate(rows, [.8, .8, .9], .5,
                                         dict(daily_cap=2, minutes_per_case=2))
        self.assertEqual(actions, [0, 1, 1])
        self.assertEqual(policy['reviews_unknown'], 1)
        self.assertEqual(policy['days_over_before_cap'], 1)
        self.assertEqual(raw['confusion_matrix'], [[0, 1], [0, 1]])
        _, separate, _ = f.evaluate(rows, [.8, .8, .9], .5,
                                    dict(daily_cap=2, minutes_per_case=2), [0, 1, 0])
        self.assertEqual(separate['reviews'], 3)
        with self.assertRaisesRegex(ValueError, 'score cache'):
            f.evaluate(rows, [.8], .5, dict(daily_cap=2, minutes_per_case=2))

    def test_no_overwrite_and_preflight_transaction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            f.publish_support(root, {'existing': b'old'})
            with self.assertRaisesRegex(ValueError, 'overwrite'):
                f.publish_support(root, {'new': b'new', 'existing': b'changed'})
            self.assertFalse((root / 'new').exists())
            self.assertEqual(f.read(root / 'existing'), b'old')
            with self.assertRaisesRegex(ValueError, 'Frozen tree'):
                f.publish_support(root, {'experiment/new': b'bad'})

    def test_transaction_write_failure_rolls_back_only_own_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            f.publish_support(root, {'keep': b'original'})
            original_read = f.read
            def fail(path):
                if Path(path).name == 'second':
                    raise OSError('injected disk failure')
                return original_read(path)
            with patch.object(f, 'read', side_effect=fail), self.assertRaises(OSError):
                f.publish_support(root, {'nested/first': b'a', 'nested/second': b'b'})
            self.assertEqual(set(f.tree(root)), {'keep'})

    def test_package_blocker_creates_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            with self.assertRaisesRegex(ValueError, 'blocked'):
                f.package(root, root.parent / 'never.zip', dict(passed=False, blockers=['missing TRAIN']))
            self.assertEqual(list(root.iterdir()), [])

    def test_archive_crc_sha_inventory_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp).resolve()
            root = parent / 'delivery'
            root.mkdir()
            for folder in f.FROZEN:
                (root / folder).mkdir()
            f.publish_support(root, {'support/evidence.json': b'{}'})
            result = dict(passed=True, blockers=[], checks={'ok': True},
                          sha256={folder: {} for folder in f.FROZEN})
            archive = parent / 'delivery.zip'
            record = f.package(root, archive, result)
            self.assertEqual(record['sha256'], f.sha(f.read(archive)))
            with ZipFile(archive) as z:
                self.assertIsNone(z.testzip())
                self.assertEqual(len(z.namelist()), 2)
                for name, digest in record['every_member_sha256'].items():
                    self.assertEqual(f.sha(z.read(name)), digest)
            with self.assertRaisesRegex(ValueError, 'must be new'):
                f.package(root, archive, result)

    def test_json_duplicate_nonfinite_and_symlink(self):
        for data in (b'{"x":1,"x":2}', b'{"x":NaN}'):
            with self.assertRaises(ValueError):
                f.load(data)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / 'link').symlink_to(root)
            with self.assertRaisesRegex(ValueError, 'Symlink'):
                f.tree(root)


if __name__ == '__main__':
    unittest.main()
