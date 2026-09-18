from __future__ import annotations

import os


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
                    """
                    SELECT
                      (SELECT count(*) FROM job_records) AS jobs,
                      (SELECT count(*) FROM case_records) AS complaint_cases,
                      (SELECT count(*) FROM actions WHERE status NOT IN ('CLOSED', 'CANCELLED')) AS open_actions,
                      (SELECT count(*) FROM evidence WHERE review_status = 'PENDING') AS pending_evidence
                    """
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
        return {"mode": "live", "summary": summary, "technicians": technicians}

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
        return dict(row) if row else None
