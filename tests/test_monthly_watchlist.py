import unittest

from app.application.monthly_watchlist import classify_monthly_watchlist
from app.infrastructure.postgres_reader import MONTHLY_WATCHLIST_QUERY


class MonthlyWatchlistTest(unittest.TestCase):
    def test_over_ten_percent_is_critical_even_with_few_jobs(self):
        result = classify_monthly_watchlist(
            jobs=8, affected_orders=1, complaints=1, rework=0, qc_fail=0
        )
        self.assertEqual(result["status"], "CRITICAL")
        self.assertEqual(result["combined_rate"], 0.125)

    def test_exactly_ten_percent_is_not_critical(self):
        result = classify_monthly_watchlist(
            jobs=30, affected_orders=2, complaints=1, rework=1, qc_fail=1
        )
        self.assertEqual(result["status"], "NORMAL")

    def test_one_order_with_three_overlapping_signals_is_not_three_cases(self):
        result = classify_monthly_watchlist(
            jobs=78, affected_orders=1, complaints=1, rework=1, qc_fail=1
        )
        self.assertEqual(result["status"], "NORMAL")

    def test_three_orders_with_no_jobs_are_watchlisted_but_have_no_rate(self):
        result = classify_monthly_watchlist(
            jobs=0, affected_orders=3, complaints=3, rework=2, qc_fail=3
        )
        self.assertEqual(result["status"], "WATCHLIST")
        self.assertIsNone(result["combined_rate"])

    def test_monthly_sources_use_complaint_and_install_dates_separately(self):
        self.assertIn("j.install_date >= p.starts_on", MONTHLY_WATCHLIST_QUERY)
        self.assertIn("c.complaint_date >= p.starts_on", MONTHLY_WATCHLIST_QUERY)
        self.assertIn("count(DISTINCT c.job_no) AS affected_orders", MONTHLY_WATCHLIST_QUERY)
        self.assertNotIn("link_status NOT IN", MONTHLY_WATCHLIST_QUERY)


if __name__ == "__main__":
    unittest.main()
