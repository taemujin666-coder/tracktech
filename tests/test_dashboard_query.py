import unittest

from app.infrastructure.postgres_reader import DASHBOARD_SUMMARY_QUERY


class DashboardSummaryQueryTest(unittest.TestCase):
    def test_ytd_summary_uses_approved_metric_sources(self):
        self.assertIn("FROM job_records", DASHBOARD_SUMMARY_QUERY)
        self.assertIn("FROM case_records", DASHBOARD_SUMMARY_QUERY)
        self.assertIn("AND rework IS TRUE", DASHBOARD_SUMMARY_QUERY)
        self.assertIn("qc_result, '')) = 'fail'", DASHBOARD_SUMMARY_QUERY)
        self.assertIn("complaint_date >= starts_on", DASHBOARD_SUMMARY_QUERY)
        self.assertIn("install_date >= starts_on", DASHBOARD_SUMMARY_QUERY)

    def test_rates_are_derived_from_matching_ytd_counts(self):
        self.assertIn("complaint_cases::numeric / nullif(jobs, 0)", DASHBOARD_SUMMARY_QUERY)
        self.assertIn("rework_cases::numeric / nullif(jobs, 0)", DASHBOARD_SUMMARY_QUERY)
        self.assertIn("qc_fail_cases::numeric / nullif(jobs, 0)", DASHBOARD_SUMMARY_QUERY)


if __name__ == "__main__":
    unittest.main()
