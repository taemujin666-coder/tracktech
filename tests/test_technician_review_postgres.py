"""Real PostgreSQL lifecycle test; runs only against the dedicated CI test DB."""

import os
import unittest
from datetime import date
from urllib.parse import urlsplit


class TechnicianReviewPostgresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        url = os.getenv("TRACKTECH_DATABASE_URL", "")
        if urlsplit(url).path != "/tracktech_review_test":
            raise unittest.SkipTest("Dedicated tracktech_review_test database is required")
        import psycopg
        from app.infrastructure.technician_review_repository import (
            ReviewConflict, ReviewInvalid, TechnicianReviewRepository,
        )

        cls.psycopg = psycopg
        cls.repository = TechnicianReviewRepository(url)
        cls.ReviewConflict = ReviewConflict
        cls.ReviewInvalid = ReviewInvalid
        cls.url = url

    def setUp(self):
        with self.psycopg.connect(self.url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO import_runs (filename) VALUES ('synthetic-review-test.xlsx') RETURNING import_run_id")
                import_id = cursor.fetchone()[0]
                cursor.execute("""
                    INSERT INTO technicians (technician_id, technician_name, vendor_name)
                    VALUES ('TEST-OPS-01', 'Synthetic team', 'Synthetic vendor'),
                           ('TEST-OPS-02', 'Another synthetic team', 'Synthetic vendor')
                """)
                job_rows = (
                    ("CASE-ORDER", date(2026, 8, 5)),
                    ("MONITOR-1", date(2026, 9, 21)),
                    ("MONITOR-2", date(2026, 9, 22)),
                )
                for row_num, (job_no, installed) in enumerate(job_rows, 1):
                    cursor.execute("""
                        INSERT INTO job_records
                          (source_job_key, source_row_number, job_no, install_date, technician_id,
                           technician_identity_status, qc_result, qc_evidence_status, job_status,
                           record_hash, first_import_run_id, last_import_run_id)
                        VALUES (%s, %s, %s, %s, 'TEST-OPS-01', 'VERIFIED', 'Pass', 'RECORDED',
                                'Completed', %s, %s, %s)
                    """, (f"review-job-{row_num}", row_num, job_no, installed,
                          f"review-job-hash-{row_num}", import_id, import_id))
                cursor.execute("""
                    INSERT INTO case_records
                      (source_case_key, source_row_number, job_no, complaint_date,
                       technician_id, technician_identity_status, issue_category, issue_detail,
                       link_status, record_hash, first_import_run_id, last_import_run_id)
                    VALUES ('review-case-1', 1, 'CASE-ORDER', '2026-08-10',
                            'TEST-OPS-01', 'VERIFIED', 'Workmanship', 'Synthetic issue',
                            'MATCHED', 'review-case-hash', %s, %s)
                    RETURNING case_record_id
                """, (import_id, import_id))
                self.case_id = cursor.fetchone()[0]

    def tearDown(self):
        # The database name guard in setUpClass prevents truncating a user's DB.
        with self.psycopg.connect(self.url) as connection:
            connection.execute("""
                TRUNCATE technician_review_followup_edits, technician_review_edits,
                         technician_review_followups, technician_reviews, case_records,
                         job_records, technicians, import_runs CASCADE
            """)

    def review_values(self):
        return {
            "case_record_id": self.case_id,
            "investigation_date": date(2026, 9, 20),
            "notification_date": date(2026, 9, 20),
            "root_cause": "Technician Defect",
            "findings": "Synthetic installation finding",
            "evidence_reference": "Review record #1",
            "related_cases": None,
            "technician_statement": None,
            "agreed_action": "Verify the next two completed jobs",
            "action_owner": "Vendor Supervisor",
            "ops_reviewer": "Synthetic OPS",
            "vendor_manager": None,
            "vendor_admin": None,
            "technician_acknowledged_by": None,
            "action_level": 1,
            "monitoring_target_jobs": 2,
            "review_date": date(2026, 10, 20),
        }

    @staticmethod
    def followup_values(job_no, *, evidence_status="COMPLETE", reference="Evidence #1"):
        return {
            "job_no": job_no,
            "checklist_status": "COMPLETE",
            "evidence_status": evidence_status,
            "rework": False,
            "same_issue": False,
            "reviewer": "Synthetic OPS",
            "evidence_reference": reference,
            "note": None,
        }

    def test_review_and_followup_persist_with_verified_closure(self):
        repo = self.repository
        review = repo.create("TEST-OPS-01", self.review_values())
        review_id = review["review_id"]
        self.assertEqual(review["period_jobs"], 1)
        self.assertEqual(repo.list_for_technician("TEST-OPS-01")[0]["review_id"], review_id)
        first = repo.add_followup(review_id, self.followup_values("MONITOR-1", evidence_status="MISSING"))
        self.assertEqual(first["followups"][0]["result"], "FOLLOW_UP")
        with self.assertRaises(self.ReviewConflict):
            repo.decide(review_id, status="CLOSED", note="Premature", decided_by="Synthetic OPS")

        corrected = repo.update_followup(
            review_id, first["followups"][0]["followup_id"],
            self.followup_values("MONITOR-1"))
        self.assertEqual(corrected["followups"][0]["result"], "PASS")
        with self.assertRaises(self.ReviewConflict):
            repo.add_followup(review_id, self.followup_values("MONITOR-1"))
        with self.assertRaises(self.ReviewConflict):
            repo.decide(review_id, status="CLOSED", note="Only one job", decided_by="Synthetic OPS")

        edits = self.review_values()
        edits.pop("case_record_id")
        edits.pop("investigation_date")
        edits["agreed_action"] = "Updated corrective measure"
        edits["edited_by"] = "Synthetic OPS"
        changed = repo.update_review(review_id, edits)
        self.assertEqual(changed["agreed_action"], "Updated corrective measure")
        self.assertEqual(len(changed["edit_history"]), 1)

        repo.add_followup(review_id, self.followup_values("MONITOR-2", reference="Evidence #2"))
        self.assertTrue(repo.get(review_id)["can_close"])
        closed = repo.decide(review_id, status="CLOSED", note="Two jobs verified", decided_by="Synthetic OPS")
        self.assertEqual(closed["status"], "CLOSED")
        self.assertEqual(repo.get(review_id)["decided_by"], "Synthetic OPS")
        with self.psycopg.connect(self.url) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM technician_review_followup_edits").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT count(*) FROM performance_snapshots").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT count(*) FROM case_records").fetchone()[0], 1)

    def test_fresh_job_data_can_block_close_and_unverified_orders_cannot_be_used(self):
        repo = self.repository
        with self.assertRaises(self.ReviewInvalid):
            repo.create("TEST-OPS-02", self.review_values())
        review_id = repo.create("TEST-OPS-01", self.review_values())["review_id"]
        with self.assertRaises(self.ReviewInvalid):
            repo.add_followup(review_id, self.followup_values("NOT-A-REAL-ORDER"))
        repo.add_followup(review_id, self.followup_values("MONITOR-1"))
        repo.add_followup(review_id, self.followup_values("MONITOR-2", reference="Evidence #2"))
        with self.psycopg.connect(self.url) as connection:
            connection.execute("UPDATE job_records SET qc_result = 'Fail' WHERE job_no = 'MONITOR-2'")
        with self.assertRaises(self.ReviewConflict):
            repo.decide(review_id, status="CLOSED", note="QC changed", decided_by="Synthetic OPS")
        escalated = repo.decide(review_id, status="ESCALATED", note="QC fail after review", decided_by="Synthetic OPS")
        self.assertEqual(escalated["status"], "ESCALATED")
        with self.assertRaises(self.ReviewConflict):
            repo.add_followup(review_id, self.followup_values("MONITOR-2"))


if __name__ == "__main__":
    unittest.main()
