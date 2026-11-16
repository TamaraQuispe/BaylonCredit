"""Check return-unit accounting without generating data or importing ML."""

import importlib.util
import unittest
from datetime import date
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "coherence", Path(__file__).with_name("audit-rildo-source-coherence.py")
)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class ReturnAccountingTests(unittest.TestCase):
    def test_warmup_predecessor_is_included_but_not_warmup_only_pairs(self):
        events = [
            {"client_id": "fictional", "evaluated_at": at}
            for at in ("2026-03-01T09:00:00", "2026-03-20T09:00:00", "2026-04-04T09:00:00")
        ]
        result = AUDIT.gaps(events, date(2026, 4, 1), 3, 14)
        self.assertEqual(result["n"], 1)
        self.assertEqual(result["outside_source_range"], 1)
        self.assertEqual(result["max"], 15)

    def test_clients_are_not_pooled_and_boundaries_are_inclusive(self):
        events = [
            {"client_id": client, "evaluated_at": at}
            for client, at in (
                ("a", "2026-04-01T09:00:00"), ("b", "2026-04-02T09:00:00"),
                ("a", "2026-04-15T09:00:00"), ("b", "2026-04-05T09:00:00"),
            )
        ]
        result = AUDIT.gaps(events, date(2026, 4, 1), 3, 14)
        self.assertEqual(result["n"], 2)
        self.assertEqual((result["min"], result["max"]), (3, 14))
        self.assertEqual(result["outside_source_range"], 0)

    def test_no_return_is_not_treated_as_zero_days(self):
        result = AUDIT.gaps(
            [{"client_id": "a", "evaluated_at": "2026-04-01T09:00:00"}],
            date(2026, 4, 1), 3, 14,
        )
        self.assertEqual(result["n"], 0)
        self.assertIsNone(result["mean"])


if __name__ == "__main__":
    unittest.main()
