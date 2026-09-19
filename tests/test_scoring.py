import unittest

from app.domain.models import TechnicianPerformanceInput, WatchlistStatus
from app.domain.scoring import calculate_performance


class CalculatePerformanceTest(unittest.TestCase):
    def test_low_volume_is_ranked_but_marked_rate_sensitive(self):
        result = calculate_performance(TechnicianPerformanceInput("T01", 32, 1, 1, 32, 1))
        self.assertEqual(result.status, WatchlistStatus.REVIEW)
        self.assertEqual(result.risk_score, 9.38)
        self.assertIn("rate-sensitive", " ".join(result.reasons))

    def test_review_uses_the_existing_component_thresholds(self):
        complaint_review = calculate_performance(TechnicianPerformanceInput("T02", 100, 3, 0, 100, 0))
        rework_review = calculate_performance(TechnicianPerformanceInput("T03", 100, 0, 3, 100, 0))
        qc_fail_review = calculate_performance(TechnicianPerformanceInput("T04", 100, 0, 0, 100, 5))
        normal = calculate_performance(TechnicianPerformanceInput("T05", 100, 2, 2, 100, 4))

        self.assertEqual(complaint_review.status, WatchlistStatus.REVIEW)
        self.assertEqual(rework_review.status, WatchlistStatus.REVIEW)
        self.assertEqual(qc_fail_review.status, WatchlistStatus.REVIEW)
        self.assertEqual(normal.status, WatchlistStatus.NORMAL)

    def test_zero_jobs_stays_unrated(self):
        result = calculate_performance(TechnicianPerformanceInput("T06", 0, 0, 0, 0, 0))
        self.assertEqual(result.status, WatchlistStatus.INSUFFICIENT_DATA)
        self.assertIsNone(result.risk_score)


if __name__ == "__main__":
    unittest.main()
