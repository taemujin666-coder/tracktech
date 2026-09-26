import unittest
from datetime import date

from app.application.demo_data import dashboard_demo
from app.infrastructure.postgres_reader import fill_dashboard_months


class DashboardMonthlyTest(unittest.TestCase):
    def test_empty_months_are_kept_between_imported_periods(self):
        rows = [
            {"month": date(2026, 1, 1), "jobs": 5, "complaint_cases": 1,
             "rework_cases": 1, "qc_fail_cases": 0},
            {"month": date(2026, 3, 1), "jobs": 7, "complaint_cases": 2,
             "rework_cases": 0, "qc_fail_cases": 1},
        ]
        result = fill_dashboard_months(rows, 2026)
        self.assertEqual([item["month"] for item in result],
                         ["2026-01-01", "2026-02-01", "2026-03-01"])
        self.assertEqual(result[1]["jobs"], 0)
        self.assertEqual(sum(item["jobs"] for item in result), 12)
        self.assertEqual(sum(item["complaint_cases"] for item in result), 3)

    def test_demo_does_not_invent_monthly_trends(self):
        self.assertEqual(fill_dashboard_months([], 2026), [])
        self.assertEqual(dashboard_demo()["monthly"], [])


if __name__ == "__main__":
    unittest.main()
