from __future__ import annotations

import os
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.application.technician_reviews import can_close_review, evaluate_monitored_job


def _audit_values(values: dict) -> Jsonb:
    return Jsonb({key: value.isoformat() if hasattr(value, "isoformat") else value
                  for key, value in values.items()})


class ReviewNotFound(Exception):
    pass


class ReviewConflict(Exception):
    pass


class ReviewInvalid(Exception):
    pass


class TechnicianReviewRepository:
    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.environ["TRACKTECH_DATABASE_URL"]

    def _connect(self):
        import psycopg
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def list_for_technician(self, technician_id: str) -> list[dict]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM technicians WHERE technician_id = %s", (technician_id,))
            if not cursor.fetchone():
                raise ReviewNotFound("ไม่พบ Tech ID นี้")
            cursor.execute("""
                SELECT r.*, c.job_no, c.complaint_date, c.issue_detail,
                       (SELECT count(*) FROM technician_review_followups f
                        WHERE f.review_id = r.review_id)::integer AS followed_jobs,
                       (SELECT count(*) FROM technician_review_followups f
                        WHERE f.review_id = r.review_id AND f.result = 'PASS')::integer AS passed_jobs
                FROM technician_reviews r JOIN case_records c ON c.case_record_id = r.case_record_id
                WHERE r.technician_id = %s ORDER BY r.created_at DESC
            """, (technician_id,))
            return [dict(row) for row in cursor.fetchall()]

    def create(self, technician_id: str, values: dict) -> dict:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""
                SELECT case_record_id, issue_category, complaint_date FROM case_records
                WHERE case_record_id = %s AND technician_id = %s
                  AND technician_identity_status = 'VERIFIED'
                  AND link_status NOT IN ('TECHNICIAN_CONFLICT', 'JOB_REFERENCE_REQUIRES_REVIEW')
            """, (values["case_record_id"], technician_id))
            case = cursor.fetchone()
            if not case:
                raise ReviewInvalid("เคสนี้ยังไม่ยืนยันว่าเป็นของช่างรายนี้ หรือกำลังรอตรวจข้อมูล")
            complaint_date = case["complaint_date"]
            period_month = complaint_date.replace(day=1) if complaint_date else None
            period_jobs = None
            if period_month:
                cursor.execute("""
                    SELECT count(*)::integer AS jobs FROM job_records
                    WHERE technician_id = %s AND technician_identity_status = 'VERIFIED'
                      AND install_date >= %s AND install_date < (%s::date + interval '1 month')
                """, (technician_id, period_month, period_month))
                count = cursor.fetchone()["jobs"]
                period_jobs = count if count else None  # No imported job evidence for this month.
            fields = ("case_record_id", "investigation_date", "notification_date", "root_cause", "findings",
                      "evidence_reference", "related_cases", "technician_statement",
                      "agreed_action", "action_owner", "ops_reviewer", "vendor_manager",
                      "vendor_admin", "technician_acknowledged_by", "action_level",
                      "monitoring_target_jobs", "review_date")
            cursor.execute(f"""
                INSERT INTO technician_reviews
                    (technician_id, issue_category, period_month, period_jobs, {', '.join(fields)})
                VALUES (%s, %s, %s, %s, {', '.join(['%s'] * len(fields))})
                RETURNING review_id
            """, (technician_id, case["issue_category"] or "ยังไม่ระบุ", period_month, period_jobs,
                  *(values[field] for field in fields)))
            review_id = cursor.fetchone()["review_id"]
        return self.get(review_id)

    def get(self, review_id: UUID) -> dict:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""
                SELECT r.*, t.technician_name, t.vendor_name, c.job_no AS case_job_no,
                       c.complaint_date, c.issue_detail, c.root_cause_status,
                       c.root_cause_type AS source_root_cause
                FROM technician_reviews r
                JOIN technicians t ON t.technician_id = r.technician_id
                JOIN case_records c ON c.case_record_id = r.case_record_id
                WHERE r.review_id = %s
            """, (review_id,))
            row = cursor.fetchone()
            if not row:
                raise ReviewNotFound("ไม่พบรายการทบทวนนี้")
            cursor.execute("""
                SELECT * FROM technician_review_followups WHERE review_id = %s
                ORDER BY job_date NULLS LAST, created_at, job_no
            """, (review_id,))
            followups = [dict(followup) for followup in cursor.fetchall()]
            cursor.execute("""
                SELECT edited_by, edited_at FROM technician_review_edits
                WHERE review_id = %s ORDER BY edited_at DESC
            """, (review_id,))
            edits = [dict(edit) for edit in cursor.fetchall()]
        return {**dict(row), "followups": followups,
                "edit_history": edits,
                "can_close": can_close_review(followups, row["monitoring_target_jobs"])}

    def update_review(self, review_id: UUID, values: dict) -> dict:
        fields = ("notification_date", "root_cause", "findings", "evidence_reference", "related_cases",
                  "technician_statement", "agreed_action", "action_owner", "ops_reviewer",
                  "vendor_manager", "vendor_admin", "technician_acknowledged_by",
                  "action_level", "monitoring_target_jobs", "review_date")
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT * FROM technician_reviews WHERE review_id = %s FOR UPDATE", (review_id,))
            current = cursor.fetchone()
            if not current:
                raise ReviewNotFound("ไม่พบรายการทบทวนนี้")
            if current["status"] != "MONITORING":
                raise ReviewConflict("รายการนี้ปิดหรือยกระดับแล้ว")
            if values["review_date"] < current["investigation_date"]:
                raise ReviewInvalid("วันทบทวนต้องไม่ก่อนวัน Investigation")
            before = {field: current[field] for field in fields}
            after = {field: values[field] for field in fields}
            cursor.execute(f"""
                UPDATE technician_reviews SET {', '.join(f'{field} = %s' for field in fields)},
                    updated_at = now() WHERE review_id = %s
            """, (*after.values(), review_id))
            cursor.execute("""
                INSERT INTO technician_review_edits (review_id, edited_by, before_values, after_values)
                VALUES (%s, %s, %s, %s)
            """, (review_id, values["edited_by"], _audit_values(before), _audit_values(after)))
        return self.get(review_id)

    def add_followup(self, review_id: UUID, values: dict) -> dict:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""
                SELECT technician_id, investigation_date, status FROM technician_reviews
                WHERE review_id = %s FOR UPDATE
            """, (review_id,))
            review = cursor.fetchone()
            if not review:
                raise ReviewNotFound("ไม่พบรายการทบทวนนี้")
            if review["status"] != "MONITORING":
                raise ReviewConflict("รายการนี้ปิดหรือยกระดับแล้ว")
            job_date, qc_result, result = self._job_outcome(cursor, review, values)
            cursor.execute("""
                INSERT INTO technician_review_followups
                    (review_id, job_no, job_date, checklist_status, evidence_status,
                     qc_result, rework, same_issue, reviewer, evidence_reference, note, result)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (review_id, job_no) DO NOTHING RETURNING followup_id
            """, (review_id, values["job_no"], job_date, values["checklist_status"],
                  values["evidence_status"], qc_result, values["rework"], values["same_issue"],
                  values["reviewer"], values["evidence_reference"], values["note"], result))
            if not cursor.fetchone():
                raise ReviewConflict("Order No. นี้ถูกบันทึกในรายการติดตามแล้ว")
        return self.get(review_id)

    @staticmethod
    def _job_outcome(cursor, review: dict, values: dict):
        cursor.execute("""
            SELECT install_date, qc_result, job_status FROM job_records
            WHERE job_no = %s AND technician_id = %s
              AND technician_identity_status = 'VERIFIED'
        """, (values["job_no"], review["technician_id"]))
        try:
            return evaluate_monitored_job(cursor.fetchall(), review["investigation_date"], values)
        except ValueError as error:
            raise ReviewInvalid(str(error)) from error

    def update_followup(self, review_id: UUID, followup_id: UUID, values: dict) -> dict:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""
                SELECT technician_id, investigation_date, status FROM technician_reviews
                WHERE review_id = %s FOR UPDATE
            """, (review_id,))
            review = cursor.fetchone()
            if not review:
                raise ReviewNotFound("ไม่พบรายการทบทวนนี้")
            if review["status"] != "MONITORING":
                raise ReviewConflict("รายการนี้ปิดหรือยกระดับแล้ว")
            cursor.execute("""
                SELECT * FROM technician_review_followups
                WHERE review_id = %s AND followup_id = %s FOR UPDATE
            """, (review_id, followup_id))
            followup = cursor.fetchone()
            if not followup:
                raise ReviewNotFound("ไม่พบงานติดตามนี้")
            if values["job_no"] != followup["job_no"]:
                cursor.execute("""
                    SELECT 1 FROM technician_review_followups
                    WHERE review_id = %s AND job_no = %s
                """, (review_id, values["job_no"]))
                if cursor.fetchone():
                    raise ReviewConflict("Order No. นี้มีอยู่ในรายการติดตามแล้ว")
            job_date, qc_result, result = self._job_outcome(cursor, review, values)
            changed = {"job_no": values["job_no"], "job_date": job_date,
                       "checklist_status": values["checklist_status"],
                       "evidence_status": values["evidence_status"], "qc_result": qc_result,
                       "rework": values["rework"], "same_issue": values["same_issue"],
                       "reviewer": values["reviewer"], "evidence_reference": values["evidence_reference"],
                       "note": values["note"], "result": result}
            cursor.execute("""
                UPDATE technician_review_followups SET job_no = %s, job_date = %s,
                    checklist_status = %s, evidence_status = %s, qc_result = %s,
                    rework = %s, same_issue = %s, reviewer = %s,
                    evidence_reference = %s, note = %s, result = %s
                WHERE review_id = %s AND followup_id = %s
            """, (*changed.values(), review_id, followup_id))
            cursor.execute("""
                INSERT INTO technician_review_followup_edits
                    (followup_id, edited_by, before_values, after_values)
                VALUES (%s, %s, %s, %s)
            """, (followup_id, values["reviewer"],
                  _audit_values({field: followup[field] for field in changed}), _audit_values(changed)))
        return self.get(review_id)

    def decide(self, review_id: UUID, *, status: str, note: str, decided_by: str) -> dict:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""
                SELECT status, monitoring_target_jobs, technician_id, investigation_date FROM technician_reviews
                WHERE review_id = %s FOR UPDATE
            """, (review_id,))
            review = cursor.fetchone()
            if not review:
                raise ReviewNotFound("ไม่พบรายการทบทวนนี้")
            if review["status"] != "MONITORING":
                raise ReviewConflict("รายการนี้ตัดสินผลไปแล้ว")
            if status == "CLOSED":
                cursor.execute("SELECT * FROM technician_review_followups WHERE review_id = %s FOR UPDATE",
                               (review_id,))
                followups = cursor.fetchall()
                evaluated = []
                for row in followups:
                    job_date, qc_result, result = self._job_outcome(cursor, review, row)
                    if (job_date, qc_result, result) != (row["job_date"], row["qc_result"], row["result"]):
                        cursor.execute("""
                            UPDATE technician_review_followups
                            SET job_date = %s, qc_result = %s, result = %s WHERE followup_id = %s
                        """, (job_date, qc_result, result, row["followup_id"]))
                        cursor.execute("""
                            INSERT INTO technician_review_followup_edits
                                (followup_id, edited_by, before_values, after_values)
                            VALUES (%s, %s, %s, %s)
                        """, (row["followup_id"], "SYSTEM: Job Data refresh",
                              _audit_values({"job_date": row["job_date"], "qc_result": row["qc_result"], "result": row["result"]}),
                              _audit_values({"job_date": job_date, "qc_result": qc_result, "result": result})))
                    evaluated.append({"job_no": row["job_no"], "result": result})
                if not can_close_review(evaluated, review["monitoring_target_jobs"]):
                    raise ReviewConflict("ยังติดตามงานไม่ครบหรือมีงานที่ยังไม่ผ่าน ต้องตรวจและบันทึกผลก่อนปิด")
            cursor.execute("""
                UPDATE technician_reviews SET status = %s, decision_note = %s,
                    decided_by = %s, decided_at = now(), updated_at = now()
                WHERE review_id = %s
            """, (status, note, decided_by, review_id))
        return self.get(review_id)
