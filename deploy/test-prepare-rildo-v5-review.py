"""Accounting boundaries and deterministic coverage, without model imports."""

import copy
import csv
import importlib.util
import json
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path

spec = importlib.util.spec_from_file_location('review', Path(__file__).with_name('prepare-rildo-v5-review.py'))
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class ReviewTests(unittest.TestCase):
    def loan(self):
        return {'loan_id': 'L1', 'client_id': 'C1', 'evaluated_at': '2026-09-01T09:00:00',
                'amount': '40.00', 'due_date': '2026-09-02',
                'payments': [{'payment_id': 'P1', 'at': '2026-09-03T08:00:00', 'amount': '10.00'},
                             {'payment_id': 'P2', 'at': '2026-09-03T09:00:00', 'amount': '30.00'}],
                'planned_payments': [{'at': '2026-09-02T10:00:00', 'amount': '40.00'}]}

    def test_strict_before_and_no_planned_payment(self):
        world = {'loans': [self.loan()]}
        overdue, outstanding, evidence = review.balance_before(world, 'C1', '2026-09-03T09:00:00')
        self.assertEqual((overdue, outstanding), (Decimal('30'), Decimal('30')))
        self.assertEqual(len(evidence[0]['observed_payments_before']), 1)
        world['loans'][0]['planned_payments'][0]['amount'] = '999'
        self.assertEqual(review.balance_before(world, 'C1', '2026-09-03T09:00:00')[0], Decimal('30'))

    def test_full_settlement_before_later_evaluation(self):
        self.assertEqual(review.balance_before({'loans': [self.loan()]}, 'C1', '2026-09-03T09:00:01')[0], 0)

    def test_observed_cutoff_not_future_plan(self):
        loan = self.loan()
        r = review.outcome(loan, datetime.fromisoformat('2026-09-03T08:30:00'))
        self.assertEqual(r['pending'], Decimal('30'))
        self.assertTrue(r['abonos'])
        self.assertIsNone(r['completed'])
        self.assertIsNone(r['delay'])
        self.assertEqual(r['label'], 1)
        r = review.outcome(loan, datetime.fromisoformat('2026-09-03T10:00:00'))
        self.assertEqual(r['delay'], 1)

    def test_unknown_is_not_punctual_or_planned_abonos(self):
        loan = self.loan()
        loan['payments'] = []
        r = review.outcome(loan, datetime.fromisoformat('2026-09-02T23:59:00'))
        self.assertIsNone(r['label'])
        self.assertFalse(r['abonos'])

    def test_selection_dedup_neighbor_order_and_missing(self):
        cases = []
        for i, (label, abonos) in enumerate([(0, False)] * 3 + [(0, True)] * 3 + [(1, False)] * 3 + [(1, True)] * 3 + [(None, False)] * 3):
            cases.append({'loan_id': f'L{i:02}', 'amount': str(i + 5),
                          'result': {'label': label, 'abonos': abonos}})
        chosen, log, missing = review.select_cases(cases)
        shuffled, _, _ = review.select_cases(list(reversed(cases)))
        self.assertEqual(chosen, shuffled)
        self.assertEqual(len({c['loan_id'] for c in chosen}), 12)
        self.assertEqual(missing, [])
        self.assertEqual(log[-2]['extreme_id'], 'L00')
        self.assertEqual(log[-2]['ids'], ['L02'])
        mutated = copy.deepcopy(cases)
        for c in mutated:
            c['result']['label'] = 0
        self.assertIn('unknown', review.select_cases(mutated)[2])

    def test_existing_output_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'Output must not exist'):
            review.build(review.SOURCE, Path(__file__).parent)

    @unittest.skipUnless(review.OUTPUT.exists(), 'Generated package not present')
    def test_generated_package_integrity(self):
        manifest = json.loads((review.OUTPUT / 'manifest.json').read_text())
        for name, digest in manifest['outputs'].items():
            self.assertEqual(review.sha(review.OUTPUT / name), digest)
        self.assertEqual(len(manifest['source_hashes']), 12)
        for name, digest in manifest['source_hashes'].items():
            self.assertEqual(review.sha(review.SOURCE / name), digest)
        for name, count in [('muestra-fiados.csv', 12), ('muestra-rechazos.csv', 4), ('muestra-semanas.csv', 4)]:
            with (review.OUTPUT / name).open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), count)
            self.assertTrue(all(r['respuesta'] == r['correccion'] == '' for r in rows))
        checks = json.loads((review.OUTPUT / 'verificacion.json').read_text())
        self.assertEqual(checks['actual_pdf_pages'], 5)
        self.assertEqual(checks['source_hash_before'], checks['source_hash_after'])
        self.assertEqual(checks['unavailable'], [])


if __name__ == '__main__':
    unittest.main()
