from __future__ import annotations

import json
import os
from dataclasses import astuple

from app.domain.import_models import ImportCommitResult, WorkbookPreview


class PostgresImportRepository:
    """Transactional, idempotent persistence for evidence-first workbook imports."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.environ["TRACKTECH_DATABASE_URL"]

    @staticmethod
    def _is_active(source_status: str | None) -> bool:
        return (source_status or "").strip().casefold() == "active"

    @staticmethod
    def _existing_hashes(cursor, table: str, key_column: str, keys: list[str]) -> dict[str, str]:
        if not keys:
            return {}
        cursor.execute(f"SELECT {key_column}, record_hash FROM {table} WHERE {key_column} = ANY(%s)", (keys,))
        return dict(cursor.fetchall())

    @staticmethod
    def _counts(existing: dict[str, str], records, key_name: str) -> tuple[int, int, int]:
        inserted = updated = unchanged = 0
        for record in records:
            key = getattr(record, key_name)
            old_hash = existing.get(key)
            if old_hash is None:
                inserted += 1
            elif old_hash == record.record_hash:
                unchanged += 1
            else:
                updated += 1
        return inserted, updated, unchanged

    def commit(self, preview: WorkbookPreview, imported_by: str | None = None) -> ImportCommitResult:
        import psycopg

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO import_runs (filename, imported_by, content_hash, status, validation_summary)
                    VALUES (%s, %s, %s, 'PROCESSING', %s::jsonb)
                    RETURNING import_run_id
                    """,
                    (preview.filename, imported_by, preview.content_hash, json.dumps(preview.summary, ensure_ascii=False)),
                )
                import_run_id = str(cursor.fetchone()[0])

                technician_ids = [record.technician_id for record in preview.technicians]
                cursor.execute(
                    """
                    SELECT technician_id, technician_name, team, vendor_name, source_status, area, active
                    FROM technicians WHERE technician_id = ANY(%s)
                    """,
                    (technician_ids,),
                )
                existing_technicians = {row[0]: tuple(row[1:]) for row in cursor.fetchall()}
                tech_inserted = tech_updated = tech_unchanged = 0
                for record in preview.technicians:
                    current = existing_technicians.get(record.technician_id)
                    incoming = astuple(record)[1:] + (self._is_active(record.source_status),)
                    if current is None:
                        tech_inserted += 1
                    elif current == incoming:
                        tech_unchanged += 1
                    else:
                        tech_updated += 1
                cursor.executemany(
                    """
                    INSERT INTO technicians
                      (technician_id, technician_name, team, vendor_name, source_status, area, active, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (technician_id) DO UPDATE SET
                      technician_name = EXCLUDED.technician_name, team = EXCLUDED.team,
                      vendor_name = EXCLUDED.vendor_name, source_status = EXCLUDED.source_status,
                      area = EXCLUDED.area, active = EXCLUDED.active, updated_at = now()
                    WHERE (technicians.technician_name, technicians.team, technicians.vendor_name,
                           technicians.source_status, technicians.area, technicians.active)
                          IS DISTINCT FROM
                          (EXCLUDED.technician_name, EXCLUDED.team, EXCLUDED.vendor_name,
                           EXCLUDED.source_status, EXCLUDED.area, EXCLUDED.active)
                    """,
                    [astuple(record) + (self._is_active(record.source_status),) for record in preview.technicians],
                )

                existing_jobs = self._existing_hashes(cursor, "job_records", "source_job_key", [r.source_job_key for r in preview.jobs])
                jobs_inserted, jobs_updated, jobs_unchanged = self._counts(existing_jobs, preview.jobs, "source_job_key")
                cursor.executemany(
                    """
                    INSERT INTO job_records
                      (source_job_key, source_row_number, job_no, install_date, product_model,
                       source_tech_code, technician_id, technician_identity_status, project_name,
                       vendor_name, qc_date, qc_result, qc_evidence_status, job_status, record_hash,
                       first_import_run_id, last_import_run_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source_job_key) DO UPDATE SET
                      source_row_number = EXCLUDED.source_row_number, job_no = EXCLUDED.job_no,
                      install_date = EXCLUDED.install_date, product_model = EXCLUDED.product_model,
                      source_tech_code = EXCLUDED.source_tech_code, technician_id = EXCLUDED.technician_id,
                      technician_identity_status = EXCLUDED.technician_identity_status,
                      project_name = EXCLUDED.project_name, vendor_name = EXCLUDED.vendor_name,
                      qc_date = EXCLUDED.qc_date, qc_result = EXCLUDED.qc_result,
                      qc_evidence_status = EXCLUDED.qc_evidence_status, job_status = EXCLUDED.job_status,
                      record_hash = EXCLUDED.record_hash, last_import_run_id = EXCLUDED.last_import_run_id,
                      updated_at = now()
                    WHERE job_records.record_hash IS DISTINCT FROM EXCLUDED.record_hash
                    """,
                    [astuple(record) + (import_run_id, import_run_id) for record in preview.jobs],
                )

                existing_cases = self._existing_hashes(cursor, "case_records", "source_case_key", [r.source_case_key for r in preview.cases])
                cases_inserted, cases_updated, cases_unchanged = self._counts(existing_cases, preview.cases, "source_case_key")
                cursor.executemany(
                    """
                    INSERT INTO case_records
                      (source_case_key, source_row_number, job_no, completed_date, complaint_date,
                       source_tech_code, technician_id, technician_identity_status, issue_category,
                       issue_detail, qc_result, root_cause_status, root_cause_type, root_cause_detail,
                       immediate_action, preventive_action, rework, service_mind, owner_name,
                       case_status, close_date, link_status, record_hash, first_import_run_id, last_import_run_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source_case_key) DO UPDATE SET
                      source_row_number = EXCLUDED.source_row_number, job_no = EXCLUDED.job_no,
                      completed_date = EXCLUDED.completed_date, complaint_date = EXCLUDED.complaint_date,
                      source_tech_code = EXCLUDED.source_tech_code, technician_id = EXCLUDED.technician_id,
                      technician_identity_status = EXCLUDED.technician_identity_status,
                      issue_category = EXCLUDED.issue_category, issue_detail = EXCLUDED.issue_detail,
                      qc_result = EXCLUDED.qc_result, root_cause_status = EXCLUDED.root_cause_status,
                      root_cause_type = EXCLUDED.root_cause_type, root_cause_detail = EXCLUDED.root_cause_detail,
                      immediate_action = EXCLUDED.immediate_action, preventive_action = EXCLUDED.preventive_action,
                      rework = EXCLUDED.rework, service_mind = EXCLUDED.service_mind,
                      owner_name = EXCLUDED.owner_name, case_status = EXCLUDED.case_status,
                      close_date = EXCLUDED.close_date, link_status = EXCLUDED.link_status,
                      record_hash = EXCLUDED.record_hash, last_import_run_id = EXCLUDED.last_import_run_id,
                      updated_at = now()
                    WHERE case_records.record_hash IS DISTINCT FROM EXCLUDED.record_hash
                    """,
                    [astuple(record) + (import_run_id, import_run_id) for record in preview.cases],
                )

                case_keys = [record.source_case_key for record in preview.cases]
                cursor.execute(
                    """
                    WITH reconciled AS (
                      SELECT c.source_case_key,
                        CASE
                          WHEN NOT EXISTS (SELECT 1 FROM job_records j WHERE j.job_no = c.job_no)
                            THEN 'JOB_NOT_FOUND'
                          WHEN c.source_tech_code IS NOT NULL
                               AND EXISTS (SELECT 1 FROM job_records j WHERE j.job_no = c.job_no AND j.source_tech_code IS NOT NULL)
                               AND NOT EXISTS (SELECT 1 FROM job_records j WHERE j.job_no = c.job_no AND j.source_tech_code = c.source_tech_code)
                            THEN 'TECHNICIAN_CONFLICT'
                          ELSE 'MATCHED'
                        END AS desired_link_status
                      FROM case_records c WHERE c.source_case_key = ANY(%s)
                    )
                    UPDATE case_records c SET link_status = r.desired_link_status, updated_at = now()
                    FROM reconciled r
                    WHERE c.source_case_key = r.source_case_key
                      AND c.link_status IS DISTINCT FROM r.desired_link_status
                    """,
                    (case_keys,),
                )
                cursor.execute(
                    """
                    SELECT
                      count(*) FILTER (WHERE link_status = 'TECHNICIAN_CONFLICT'),
                      count(*) FILTER (WHERE link_status = 'JOB_NOT_FOUND')
                    FROM case_records WHERE source_case_key = ANY(%s)
                    """,
                    (case_keys,),
                )
                conflicts, unmatched = cursor.fetchone()
                cursor.execute(
                    """
                    UPDATE import_runs SET status = 'COMPLETED', completed_at = now(),
                      inserted_count = %s, updated_count = %s, skipped_count = %s,
                      conflict_count = %s, unmatched_count = %s
                    WHERE import_run_id = %s
                    """,
                    (
                        tech_inserted + jobs_inserted + cases_inserted,
                        tech_updated + jobs_updated + cases_updated,
                        tech_unchanged + jobs_unchanged + cases_unchanged,
                        conflicts,
                        unmatched,
                        import_run_id,
                    ),
                )

        return ImportCommitResult(
            import_run_id, tech_inserted, tech_updated, tech_unchanged,
            jobs_inserted, jobs_updated, jobs_unchanged,
            cases_inserted, cases_updated, cases_unchanged, conflicts,
        )
