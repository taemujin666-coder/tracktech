import unittest

from app.infrastructure.postgres_reader import (
    TECHNICIAN_CASES_QUERY,
    TECHNICIAN_JOBS_QUERY,
    TECHNICIAN_PROFILE_QUERY,
    TECHNICIAN_REVIEW_CASES_QUERY,
)


class TechnicianProfileQueryTest(unittest.TestCase):
    def test_profile_includes_team_and_approved_combined_rate_fields(self):
        self.assertIn("t.team", TECHNICIAN_PROFILE_QUERY)
        self.assertIn("s.complaint_rate", TECHNICIAN_PROFILE_QUERY)
        self.assertIn("s.rework_rate", TECHNICIAN_PROFILE_QUERY)
        self.assertIn("s.qc_fail_rate", TECHNICIAN_PROFILE_QUERY)
        self.assertIn("s.combined_rate", TECHNICIAN_PROFILE_QUERY)

    def test_unresolved_cases_are_excluded_from_scores_but_returned_for_review(self):
        for status in ("TECHNICIAN_CONFLICT", "JOB_REFERENCE_REQUIRES_REVIEW"):
            self.assertIn(status, TECHNICIAN_CASES_QUERY)
            self.assertIn(status, TECHNICIAN_REVIEW_CASES_QUERY)
        self.assertIn("NOT IN", TECHNICIAN_CASES_QUERY)
        self.assertIn("IN ('TECHNICIAN_CONFLICT'", TECHNICIAN_REVIEW_CASES_QUERY)

    def test_job_history_only_uses_verified_technician_identity(self):
        self.assertIn("technician_identity_status = 'VERIFIED'", TECHNICIAN_JOBS_QUERY)

    def test_case_history_exposes_service_mind_and_close_date(self):
        self.assertIn("service_mind", TECHNICIAN_CASES_QUERY)
        self.assertIn("close_date", TECHNICIAN_CASES_QUERY)


if __name__ == "__main__":
    unittest.main()
