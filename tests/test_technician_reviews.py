import unittest
from datetime import date

from app.application.technician_reviews import can_close_review, evaluate_monitored_job, followup_result


class TechnicianReviewsTest(unittest.TestCase):
    def test_unknown_or_incomplete_evidence_never_passes(self):
        base = dict(checklist_status="COMPLETE", evidence_status="COMPLETE",
                    qc_result="PASS", rework=False, same_issue=False,
                    evidence_reference="Photo set #A-101")
        self.assertEqual(followup_result(**base), "PASS")
        for change in (dict(rework=None), dict(same_issue=None), dict(qc_result="PENDING"),
                       dict(qc_result="FAIL"), dict(evidence_status="MISSING"),
                       dict(evidence_reference="  "), dict(same_issue=True)):
            with self.subTest(change=change):
                self.assertEqual(followup_result(**(base | change)), "FOLLOW_UP")

    def test_close_requires_distinct_target_jobs_all_pass(self):
        passed = [{"job_no": "ORDER-1", "result": "PASS"},
                  {"job_no": "ORDER-2", "result": "PASS"}]
        self.assertTrue(can_close_review(passed, target_jobs=2))
        self.assertFalse(can_close_review(passed, target_jobs=3))
        self.assertFalse(can_close_review([passed[0], passed[0]], target_jobs=2))
        self.assertFalse(can_close_review([passed[0], {"job_no": "ORDER-2", "result": "FOLLOW_UP"}], 2))

    def test_multiple_products_under_order_need_all_completed_and_qc_pass(self):
        item = {"install_date": date(2026, 9, 22), "qc_result": "Pass", "job_status": "Completed"}
        evidence = {"checklist_status": "COMPLETE", "evidence_status": "COMPLETE",
                    "rework": False, "same_issue": False, "evidence_reference": "Evidence-42"}
        self.assertEqual(evaluate_monitored_job([item, item], date(2026, 9, 20), evidence)[1:],
                         ("PASS", "PASS"))
        self.assertEqual(evaluate_monitored_job([item, item | {"qc_result": None}], date(2026, 9, 20), evidence)[1:],
                         ("PENDING", "FOLLOW_UP"))
        self.assertEqual(evaluate_monitored_job([item, item | {"qc_result": "Fail"}], date(2026, 9, 20), evidence)[1:],
                         ("FAIL", "FOLLOW_UP"))
        self.assertEqual(evaluate_monitored_job([item | {"job_status": "Cancel"}], date(2026, 9, 20), evidence)[1:],
                         ("PENDING", "FOLLOW_UP"))
        with self.assertRaises(ValueError):
            evaluate_monitored_job([item | {"install_date": date(2026, 9, 18)}], date(2026, 9, 20), evidence)


if __name__ == "__main__":
    unittest.main()
