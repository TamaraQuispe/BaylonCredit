"""Stdlib tests: no experiment runner, estimator, training or inference imports."""

import importlib.util
from copy import deepcopy
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
                f.package(root, root.parent / 'never.zip', dict(passed=False, blockers=['required OOF failure']))
            self.assertEqual(list(root.iterdir()), [])

    def test_archive_crc_sha_inventory_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp).resolve()
            root = parent / 'delivery'
            root.mkdir()
            for folder in f.FROZEN:
                (root / folder).mkdir()
            f.publish_support(root, {'support/evidence.json': b'{}'})
            result = dict(passed=True, blockers=[],
                          release_required_checks=dict.fromkeys(f.RELEASE_REQUIRED, True),
                          optional_coverage={'train': {'per_score_reconstruction': 'not_available',
                                                      'per_score_queue_reconstruction': 'not_available'}},
                          coverage_limitations=['TRAIN fitted scores not persisted; aggregates checked'],
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

    def test_tampered_oof_or_final_prevents_release_despite_optional_train(self):
        rows = [dict(loan_id=str(i), replica_id='R', evaluated_at='2026-04-13T20:00:00-05:00',
                     late_payment=y) for i, y in enumerate([0, 1, None])]
        scores, policy_spec = [.1, .9, .8], dict(daily_cap=2, minutes_per_case=2)
        metrics, policy, _ = f.evaluate(rows, scores, .5, policy_spec)
        policy['per_replica'] = {'R': dict(reviews=2, daily_max=2, days_over_before_cap=0,
                                         minutes_hypothetical=4)}
        expected = dict(metrics=metrics, review_policy=policy)
        f.compare_evaluation(rows, scores, .5, policy_spec, expected)
        for split in ('oof', 'final'):
            with self.subTest(split=split), tempfile.TemporaryDirectory() as tmp:
                parent = Path(tmp).resolve()
                root = parent / 'delivery'
                root.mkdir()
                for folder in f.FROZEN:
                    (root / folder).mkdir()
                cache = f.encoded(expected)
                (root / 'experiment' / (split + '.json')).write_bytes(cache)
                result = dict(passed=True, blockers=[],
                              release_required_checks=dict.fromkeys(f.RELEASE_REQUIRED, True),
                              optional_coverage={'train': {'per_score_reconstruction': 'not_available'}},
                              sha256={folder: f.hashes(f.tree(root / folder)) for folder in f.FROZEN})
                changed = deepcopy(expected)
                changed['metrics']['f2'] = .123
                with self.assertRaisesRegex(ValueError, 'Exact metric'):
                    f.compare_evaluation(rows, scores, .5, policy_spec, changed)
                (root / 'experiment' / (split + '.json')).write_bytes(f.encoded(changed))
                target = parent / 'delivery.zip'
                with self.assertRaisesRegex(ValueError, 'Frozen tree changed'):
                    f.package(root, target, result)
                self.assertFalse(target.exists())
                result['release_required_checks']['all_candidate_oof_raw_and_capped_queues_exact'
                    if split == 'oof' else 'all_four_final_cached_raw_matrices_metrics_and_queue_actions_exact'] = False
                with self.assertRaisesRegex(ValueError, 'blocked'):
                    f.package(root, target, result)

    def test_missing_required_check_is_not_vacuous_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            result = dict(passed=True, blockers=[], release_required_checks={})
            with self.assertRaisesRegex(ValueError, 'blocked'):
                f.package(root, root.parent / 'never.zip', result)

    def test_generated_refresh_preserves_history_and_rejects_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            files = {'verificacion-v6-final.json': b'{"passed":false}'}
            manifest = f.encoded(dict(files=f.hashes(files), self_hash_excluded=True))
            f.publish_support(root, {**files, 'support/manifest-support.json': manifest})
            updated = {'verificacion-v6-final.json': b'{"passed":true}'}
            updated['support/manifest-support.json'] = f.encoded(dict(files=f.hashes(updated)))
            f.refresh_support(root, updated)
            history = root / 'support/history' / f.sha(manifest) / 'verificacion-v6-final.json'
            self.assertEqual(f.read(history), files['verificacion-v6-final.json'])
            self.assertEqual(f.read(root / 'verificacion-v6-final.json'), updated['verificacion-v6-final.json'])
            f.check_hashes(f.tree(root), f.load(f.read(root / 'support/manifest-support.json'))['files'])
            (root / 'verificacion-v6-final.json').write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError, 'SHA256'):
                f.refresh_support(root, updated)

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
