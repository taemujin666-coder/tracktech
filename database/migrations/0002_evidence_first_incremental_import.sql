-- M1.1: source rows are retained separately from legacy M1 tables.
-- Job No is intentionally not unique because one order can contain several products/services.

ALTER TABLE import_runs ADD COLUMN IF NOT EXISTS content_hash text;
ALTER TABLE import_runs ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'COMPLETED';
ALTER TABLE import_runs ADD COLUMN IF NOT EXISTS completed_at timestamptz;
ALTER TABLE import_runs ADD COLUMN IF NOT EXISTS inserted_count integer NOT NULL DEFAULT 0;
ALTER TABLE import_runs ADD COLUMN IF NOT EXISTS updated_count integer NOT NULL DEFAULT 0;
ALTER TABLE import_runs ADD COLUMN IF NOT EXISTS skipped_count integer NOT NULL DEFAULT 0;
ALTER TABLE import_runs ADD COLUMN IF NOT EXISTS conflict_count integer NOT NULL DEFAULT 0;
ALTER TABLE import_runs ADD COLUMN IF NOT EXISTS unmatched_count integer NOT NULL DEFAULT 0;

ALTER TABLE technicians ADD COLUMN IF NOT EXISTS team text;
ALTER TABLE technicians ADD COLUMN IF NOT EXISTS source_status text;
ALTER TABLE technicians ADD COLUMN IF NOT EXISTS area text;

CREATE TABLE IF NOT EXISTS job_records (
    job_record_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_job_key text NOT NULL UNIQUE,
    source_row_number integer NOT NULL,
    job_no text NOT NULL,
    install_date date,
    product_model text,
    source_tech_code text,
    technician_id text REFERENCES technicians(technician_id),
    technician_identity_status text NOT NULL,
    project_name text,
    vendor_name text,
    qc_date date,
    qc_result text,
    qc_evidence_status text NOT NULL,
    job_status text,
    record_hash text NOT NULL,
    first_import_run_id uuid NOT NULL REFERENCES import_runs(import_run_id),
    last_import_run_id uuid NOT NULL REFERENCES import_runs(import_run_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (technician_identity_status IN ('VERIFIED', 'MISSING_TECHNICIAN_ID', 'UNVERIFIED_TECHNICIAN_IDENTITY', 'PENDING_MASTER_MATCH')),
    CHECK (qc_evidence_status IN ('RECORDED', 'NOT_APPLICABLE_NOT_COMPLETE', 'NOT_APPLICABLE_CANCELLED', 'MISSING_SOURCE_VALUE'))
);

CREATE TABLE IF NOT EXISTS case_records (
    case_record_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_case_key text NOT NULL UNIQUE,
    source_row_number integer NOT NULL,
    job_no text NOT NULL,
    completed_date date,
    complaint_date date,
    source_tech_code text,
    technician_id text REFERENCES technicians(technician_id),
    technician_identity_status text NOT NULL,
    issue_category text,
    issue_detail text,
    qc_result text,
    root_cause_status text,
    root_cause_type text,
    root_cause_detail text,
    immediate_action text,
    preventive_action text,
    rework boolean,
    service_mind boolean,
    owner_name text,
    case_status text,
    close_date date,
    link_status text NOT NULL,
    record_hash text NOT NULL,
    first_import_run_id uuid NOT NULL REFERENCES import_runs(import_run_id),
    last_import_run_id uuid NOT NULL REFERENCES import_runs(import_run_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (technician_identity_status IN ('VERIFIED', 'MISSING_TECHNICIAN_ID', 'UNVERIFIED_TECHNICIAN_IDENTITY', 'PENDING_MASTER_MATCH')),
    CHECK (link_status IN ('MATCHED', 'JOB_NOT_FOUND', 'TECHNICIAN_CONFLICT'))
);

CREATE INDEX IF NOT EXISTS idx_job_records_job_no ON job_records (job_no);
CREATE INDEX IF NOT EXISTS idx_job_records_technician ON job_records (technician_id, install_date);
CREATE INDEX IF NOT EXISTS idx_case_records_job_no ON case_records (job_no);
CREATE INDEX IF NOT EXISTS idx_case_records_technician ON case_records (technician_id, complaint_date);
CREATE INDEX IF NOT EXISTS idx_case_records_link_status ON case_records (link_status);
