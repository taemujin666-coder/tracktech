import unittest

from app.infrastructure.postgres_reader import (
    SNAPSHOT_SOURCES_QUERY,
    TECHNICIAN_CASES_QUERY,
)


class PerformanceQueryTest(unittest.TestCase):
    def test_uses_the_same_sources_as_performance_summary(self):
        self.assertIn("FROM job_records", SNAPSHOT_SOURCES_QUERY)
        self.assertIn("FROM case_records", SNAPSHOT_SOURCES_QUERY)
        self.assertIn("count(*) FILTER (WHERE rework IS TRUE) AS rework_cases", SNAPSHOT_SOURCES_QUERY)
        self.assertNotIn("count(*) FILTER (WHERE rework IS TRUE) AS rework_cases\n      FROM job_records", SNAPSHOT_SOURCES_QUERY)
        self.assertIn("lower(coalesce(qc_result, '')) = 'fail'", SNAPSHOT_SOURCES_QUERY)
        self.assertIn("coalesce(c.qc_fail_cases, 0)::integer AS qc_fail_cases", SNAPSHOT_SOURCES_QUERY)

    def test_rate_counts_known_technician_cases_even_when_order_link_needs_review(self):
        cases_query = SNAPSHOT_SOURCES_QUERY.split("cases_by_technician AS (", 1)[1].split(")\n    SELECT", 1)[0]
        self.assertIn("technician_identity_status = 'VERIFIED'", cases_query)
        self.assertNotIn("link_status NOT IN", cases_query)

    def test_case_root_cause_analysis_still_excludes_cases_pending_review(self):
        self.assertIn("TECHNICIAN_CONFLICT", TECHNICIAN_CASES_QUERY)
        self.assertIn("JOB_REFERENCE_REQUIRES_REVIEW", TECHNICIAN_CASES_QUERY)


if __name__ == "__main__":
    unittest.main()
