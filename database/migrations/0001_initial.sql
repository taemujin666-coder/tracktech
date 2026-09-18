CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS import_runs (
    import_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    filename text NOT NULL,
    imported_at timestamptz NOT NULL DEFAULT now(),
    imported_by text,
    validation_summary jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS technicians (
    technician_id text PRIMARY KEY,
    technician_name text,
    vendor_name text,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS jobs (
    job_no text PRIMARY KEY,
    technician_id text REFERENCES technicians(technician_id),
    project_name text,
    vendor_name text,
    completed_at date,
    qc_result text,
    import_run_id uuid REFERENCES import_runs(import_run_id),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS service_cases (
    case_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_no text NOT NULL REFERENCES jobs(job_no),
    technician_id text REFERENCES technicians(technician_id),
    issue_category text,
    root_cause_category text,
    root_cause_status text NOT NULL DEFAULT 'PENDING_INVESTIGATION',
    rework boolean,
    case_status text NOT NULL DEFAULT 'OPEN',
    opened_at date,
    closed_at date,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (root_cause_category IS NULL OR root_cause_category IN ('TECHNICIAN', 'PRODUCT', 'SITE', 'CUSTOMER', 'PENDING_INVESTIGATION')),
    CHECK (case_status IN ('OPEN', 'PENDING', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'))
);

CREATE TABLE IF NOT EXISTS actions (
    action_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id uuid NOT NULL REFERENCES service_cases(case_id),
    action_type text NOT NULL,
    action_detail text NOT NULL,
    owner_name text NOT NULL,
    due_date date,
    status text NOT NULL DEFAULT 'OPEN',
    closed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_no text NOT NULL REFERENCES jobs(job_no),
    evidence_url text NOT NULL,
    submitted_by text,
    review_status text NOT NULL DEFAULT 'PENDING',
    reviewed_by text,
    reviewed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (review_status IN ('PENDING', 'ACCEPTED', 'REJECTED'))
);

CREATE TABLE IF NOT EXISTS performance_snapshots (
    snapshot_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_date date NOT NULL,
    technician_id text NOT NULL REFERENCES technicians(technician_id),
    vendor_name text,
    completed_jobs integer NOT NULL,
    technician_attributable_cases integer NOT NULL,
    rework_cases integer NOT NULL,
    qc_inspected_jobs integer NOT NULL,
    qc_fail_cases integer NOT NULL,
    qc_coverage numeric(7, 4),
    risk_score numeric(7, 2),
    watchlist_status text NOT NULL,
    status_reason text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (snapshot_date, technician_id)
);

CREATE INDEX IF NOT EXISTS idx_jobs_technician_id ON jobs (technician_id);
CREATE INDEX IF NOT EXISTS idx_cases_job_no ON service_cases (job_no);
CREATE INDEX IF NOT EXISTS idx_cases_technician_id ON service_cases (technician_id);
CREATE INDEX IF NOT EXISTS idx_actions_case_id ON actions (case_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_technician_date ON performance_snapshots (technician_id, snapshot_date DESC);
