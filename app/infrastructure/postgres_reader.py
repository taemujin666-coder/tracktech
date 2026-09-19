from __future__ import annotations

import json
import os
from datetime import date

from app.application.performance_snapshot import TechnicianSnapshotSource, calculate_snapshots


SNAPSHOT_SOURCES_QUERY = """
    WITH jobs_by_technician AS (
      SELECT technician_id,
        count(*) AS total_jobs,
        count(*) FILTER (WHERE job_status = 'Completed') AS completed_jobs,
        count(*) FILTER (WHERE integrity_violation IS TRUE) AS integrity_violations,
        count(*) FILTER (
          WHERE qc_evidence_status = 'RECORDED'
        ) AS qc_inspected_jobs,
        count(*) FILTER (
          WHERE lower(coalesce(qc_result, '')) = 'fail'
        ) AS qc_fail_cases
      FROM job_records
      WHERE technician_id IS NOT NULL
        AND technician_identity_status = 'VERIFIED'
      GROUP BY technician_id
    ),
    cases_by_technician AS (
      SELECT technician_id,
        count(*) AS complaint_cases,
        count(*) FILTER (WHERE rework IS TRUE) AS rework_cases
      FROM case_records
      WHERE technician_id IS NOT NULL
        AND technician_identity_status = 'VERIFIED'
        AND link_status NOT IN ('TECHNICIAN_CONFLICT', 'JOB_REFERENCE_REQUIRES_REVIEW')
      GROUP BY technician_id
    )
    SELECT t.technician_id, t.vendor_name,
      coalesce(j.total_jobs, 0)::integer AS total_jobs,
      coalesce(j.completed_jobs, 0)::integer AS completed_jobs,
      coalesce(c.complaint_cases, 0)::integer AS complaint_cases,
      coalesce(c.rework_cases, 0)::integer AS rework_cases,
      coalesce(j.qc_inspected_jobs, 0)::integer AS qc_inspected_jobs,
      coalesce(j.qc_fail_cases, 0)::integer AS qc_fail_cases,
      coalesce(j.integrity_violations, 0)::integer AS integrity_violations
    FROM technicians t
    LEFT JOIN jobs_by_technician j ON j.technician_id = t.technician_id
    LEFT JOIN cases_by_technician c ON c.technician_id = t.technician_id
    ORDER BY t.technician_id
"""


DASHBOARD_SUMMARY_QUERY = """
    WITH reporting_period AS (
      SELECT date_trunc('year', current_date)::date AS starts_on,
             (date_trunc('year', current_date) + interval '1 year')::date AS ends_on
    ), totals AS (
      SELECT
        extract(year from starts_on)::integer AS reporting_year,
        (SELECT count(*) FROM job_records
         WHERE install_date >= starts_on AND install_date < ends_on)::integer AS jobs,
        (SELECT count(*) FROM case_records
         WHERE complaint_date >= starts_on AND complaint_date < ends_on)::integer AS complaint_cases,
        (SELECT count(*) FROM case_records
         WHERE complaint_date >= starts_on AND complaint_date < ends_on
           AND rework IS TRUE)::integer AS rework_cases,
        (SELECT count(*) FROM job_records
         WHERE install_date >= starts_on AND install_date < ends_on
           AND lower(coalesce(qc_result, '')) = 'fail')::integer AS qc_fail_cases,
        (SELECT count(*) FROM actions
         WHERE status NOT IN ('CLOSED', 'CANCELLED'))::integer AS open_actions,
        (SELECT count(*) FROM evidence
         WHERE review_status = 'PENDING')::integer AS pending_evidence
      FROM reporting_period
    )
    SELECT *,
      round(complaint_cases::numeric / nullif(jobs, 0), 4) AS complaint_rate,
      round(rework_cases::numeric / nullif(jobs, 0), 4) AS rework_rate,
      round(qc_fail_cases::numeric / nullif(jobs, 0), 4) AS qc_fail_rate
    FROM totals
"""


class PostgresPerformanceReader:
    """Read model adapter. Domain code never imports psycopg."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.environ["TRACKTECH_DATABASE_URL"]

    def dashboard(self) -> dict:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    DASHBOARD_SUMMARY_QUERY
                )
                summary = dict(cursor.fetchone())
                cursor.execute(
                    """
                    SELECT technician_id, vendor_name AS vendor, watchlist_status AS status,
                           risk_score, qc_coverage, status_reason AS reasons
                    FROM performance_snapshots
                    WHERE snapshot_date = (SELECT max(snapshot_date) FROM performance_snapshots)
                    ORDER BY risk_score DESC NULLS LAST, technician_id
                    LIMIT 25
                    """
                )
                technicians = [dict(row) for row in cursor.fetchall()]
                for technician in technicians:
                    reasons = technician.get("reasons")
                    if isinstance(reasons, str):
                        try:
                            technician["reasons"] = json.loads(reasons)
                        except json.JSONDecodeError:
                            technician["reasons"] = [reasons]
        return {"mode": "live", "summary": summary, "technicians": technicians}

    def refresh_snapshot(self, snapshot_date: date | None = None) -> dict:
        """Persist the approved Combined Rate snapshot from Performance Summary sources."""
        import psycopg
        from psycopg.rows import dict_row

        as_of = snapshot_date or date.today()
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(SNAPSHOT_SOURCES_QUERY)
                sources = [TechnicianSnapshotSource(**dict(row)) for row in cursor.fetchall()]
                snapshots = calculate_snapshots(sources)
                cursor.executemany(
                    """
                    INSERT INTO performance_snapshots (
                      snapshot_date, technician_id, vendor_name, completed_jobs, total_jobs,
                      technician_attributable_cases, rework_cases, qc_inspected_jobs,
                      qc_fail_cases, complaint_cases, integrity_violations, complaint_rate,
                      rework_rate, qc_fail_rate, combined_rate, volume_context, qc_coverage,
                      risk_score, watchlist_status, status_reason
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                              %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (snapshot_date, technician_id) DO UPDATE SET
                      vendor_name = EXCLUDED.vendor_name,
                      completed_jobs = EXCLUDED.completed_jobs,
                      total_jobs = EXCLUDED.total_jobs,
                      technician_attributable_cases = EXCLUDED.technician_attributable_cases,
                      rework_cases = EXCLUDED.rework_cases,
                      qc_inspected_jobs = EXCLUDED.qc_inspected_jobs,
                      qc_fail_cases = EXCLUDED.qc_fail_cases,
                      complaint_cases = EXCLUDED.complaint_cases,
                      integrity_violations = EXCLUDED.integrity_violations,
                      complaint_rate = EXCLUDED.complaint_rate,
                      rework_rate = EXCLUDED.rework_rate,
                      qc_fail_rate = EXCLUDED.qc_fail_rate,
                      combined_rate = EXCLUDED.combined_rate,
                      volume_context = EXCLUDED.volume_context,
                      qc_coverage = EXCLUDED.qc_coverage,
                      risk_score = EXCLUDED.risk_score,
                      watchlist_status = EXCLUDED.watchlist_status,
                      status_reason = EXCLUDED.status_reason,
                      created_at = now()
                    """,
                    [
                        (
                            as_of,
                            snapshot.source.technician_id,
                            snapshot.source.vendor_name,
                            snapshot.source.completed_jobs,
                            snapshot.source.total_jobs,
                            snapshot.source.complaint_cases,
                            snapshot.source.rework_cases,
                            snapshot.source.qc_inspected_jobs,
                            snapshot.source.qc_fail_cases,
                            snapshot.source.complaint_cases,
                            snapshot.source.integrity_violations,
                            snapshot.performance.technician_issue_rate,
                            snapshot.performance.rework_rate,
                            snapshot.performance.qc_fail_rate,
                            (snapshot.performance.risk_score or 0) / 100,
                            snapshot.volume_context,
                            snapshot.performance.qc_coverage,
                            snapshot.performance.risk_score,
                            snapshot.performance.status.value,
                            json.dumps(snapshot.status_reasons, ensure_ascii=False),
                        )
                        for snapshot in snapshots
                    ],
                )
        return {"snapshot_date": as_of.isoformat(), "technicians": len(snapshots)}

    def reconciliation_queue(self) -> dict:
        """Return only cases requiring a human decision, without exposing customers."""
        import psycopg
        from psycopg.rows import dict_row

        review_statuses = ("TECHNICIAN_CONFLICT", "JOB_REFERENCE_REQUIRES_REVIEW")
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT link_status, count(*)::integer AS case_count
                    FROM case_records
                    GROUP BY link_status
                    """
                )
                counts = {row["link_status"]: row["case_count"] for row in cursor.fetchall()}
                cursor.execute(
                    """
                    SELECT job_no, complaint_date, source_tech_code, technician_id,
                           issue_category, case_status, root_cause_status, link_status
                    FROM case_records
                    WHERE link_status = ANY(%s)
                    ORDER BY complaint_date NULLS LAST, job_no
                    """,
                    (list(review_statuses),),
                )
                cases = [dict(row) for row in cursor.fetchall()]
        return {
            "summary": {
                "needs_human_review": sum(counts.get(status, 0) for status in review_statuses),
                "technician_conflicts": counts.get("TECHNICIAN_CONFLICT", 0),
                "unmatched_current_period_orders": counts.get("JOB_REFERENCE_REQUIRES_REVIEW", 0),
                "historical_reference_cases_counted": counts.get("REFERENCE_OUTSIDE_CURRENT_JOB_DATA", 0),
            },
            "cases": cases,
        }

    def technician_profile(self, technician_id: str) -> dict | None:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT t.technician_id, t.technician_name, t.vendor_name, t.active,
                           s.watchlist_status, s.risk_score, s.qc_coverage, s.status_reason
                    FROM technicians t
                    LEFT JOIN LATERAL (
                      SELECT * FROM performance_snapshots p
                      WHERE p.technician_id = t.technician_id
                      ORDER BY p.snapshot_date DESC LIMIT 1
                    ) s ON TRUE
                    WHERE t.technician_id = %s
                    """,
                    (technician_id,),
                )
                row = cursor.fetchone()
        profile = dict(row) if row else None
        if profile and isinstance(profile.get("status_reason"), str):
            try:
                profile["status_reason"] = json.loads(profile["status_reason"])
            except json.JSONDecodeError:
                profile["status_reason"] = [profile["status_reason"]]
        return profile
