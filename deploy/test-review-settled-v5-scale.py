"""Weekly scale accounting uses granted credits, never scheduled requests."""

import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "scale_review", Path(__file__).with_name("review-settled-v5-scale.py")
)
REVIEW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REVIEW)


class WeeklyScaleTests(unittest.TestCase):
    def weeks(self):
        return [
            {"week_start": str(i), "requests": 12, "request_clients": 9,
             "grants": 10 if i % 2 else 12, "grant_clients": 8 if i % 2 else 9}
            for i in range(24)
        ]

    def test_means_and_frequency_count_grants_not_requests(self):
        result = REVIEW.weekly_summary(self.weeks())
        self.assertEqual(result["mean_requests"], 12)
        self.assertEqual(result["mean_grants"], 11)
        self.assertEqual(result["mean_grant_recipients"], 8.5)
        self.assertEqual(result["grants_frequency"], {10: 12, 12: 12})

    def test_unmentioned_counts_remain_visible(self):
        weeks = self.weeks()
        weeks[0].update(grants=9, grant_clients=7)
        result = REVIEW.weekly_summary(weeks)
        self.assertEqual(result["grants_frequency"][9], 1)
        self.assertIn({"grants": 9, "recipients": 7, "weeks": 1}, result["joint_frequency"])

    def test_duplicate_week_or_impossible_count_is_rejected(self):
        weeks = self.weeks()
        weeks[1]["week_start"] = weeks[0]["week_start"]
        with self.assertRaises(AssertionError):
            REVIEW.weekly_summary(weeks)
        weeks = self.weeks()
        weeks[0]["grants"] = 13
        with self.assertRaises(AssertionError):
            REVIEW.weekly_summary(weeks)


if __name__ == "__main__":
    unittest.main()
