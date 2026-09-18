import unittest

from app.domain.models import TechnicianPerformanceInput, WatchlistStatus
from app.domain.scoring import calculate_performance


class CalculatePerformanceTest(unittest.TestCase):
    def test_low_volume_is_not_ranked(self):
        result = calculate_performance(TechnicianPerformanceInput("T01", 19, 0, 0, 0, 0, 0, 0, 0))
        self.assertEqual(result.status, WatchlistStatus.INSUFFICIENT_DATA)
        self.assertIsNone(result.risk_score)
        self.assertIsNone(result.qc_fail_rate)

    def test_no_qc_inspection_is_not_assumed_clean(self):
        result = calculate_performance(TechnicianPerformanceInput("T02", 30, 0, 0, 0, 0, 0, 0, 0))
        self.assertEqual(result.qc_coverage, 0.0)
        self.assertIsNone(result.qc_fail_rate)
        self.assertIn("QC fail", " ".join(result.reasons))

    def test_repeated_issue_triggers_investigation(self):
        result = calculate_performance(TechnicianPerformanceInput("T03", 30, 1, 0, 20, 0, 0, 0, 2))
        self.assertEqual(result.status, WatchlistStatus.INVESTIGATE)

    def test_severe_case_escalates_without_waiting_for_score(self):
        result = calculate_performance(TechnicianPerformanceInput("T04", 30, 0, 0, 20, 0, 0, 0, 0, severe_case_count=1))
        self.assertEqual(result.status, WatchlistStatus.ESCALATED)


if __name__ == "__main__":
    unittest.main()
