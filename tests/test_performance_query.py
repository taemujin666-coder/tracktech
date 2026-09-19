import unittest

from app.infrastructure.postgres_reader import SNAPSHOT_SOURCES_QUERY


class PerformanceQueryTest(unittest.TestCase):
    def test_uses_the_same_sources_as_performance_summary(self):
        self.assertIn("FROM job_records", SNAPSHOT_SOURCES_QUERY)
        self.assertIn("FROM case_records", SNAPSHOT_SOURCES_QUERY)
        self.assertIn("count(*) FILTER (WHERE rework IS TRUE) AS rework_cases", SNAPSHOT_SOURCES_QUERY)
        self.assertNotIn("count(*) FILTER (WHERE rework IS TRUE) AS rework_cases\n      FROM job_records", SNAPSHOT_SOURCES_QUERY)

    def test_excludes_unresolved_case_assignments_from_individual_scoring(self):
        self.assertIn("TECHNICIAN_CONFLICT", SNAPSHOT_SOURCES_QUERY)
        self.assertIn("JOB_REFERENCE_REQUIRES_REVIEW", SNAPSHOT_SOURCES_QUERY)


if __name__ == "__main__":
    unittest.main()
