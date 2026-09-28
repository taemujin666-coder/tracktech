-- Operational reviews reference imported Complaint Log records. They are
-- deliberately separate from KPI snapshots and the older service_cases table.
CREATE TABLE IF NOT EXISTS technician_reviews (
    review_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    technician_id text NOT NULL REFERENCES technicians(technician_id),
    case_record_id uuid NOT NULL REFERENCES case_records(case_record_id),
    investigation_date date NOT NULL,
    notification_date date,
    period_month date,
    period_jobs integer,
    issue_category text NOT NULL,
    root_cause text,
    findings text NOT NULL,
    evidence_reference text,
    related_cases text,
    technician_statement text,
    agreed_action text NOT NULL,
    action_owner text NOT NULL,
    ops_reviewer text NOT NULL,
    vendor_manager text,
    vendor_admin text,
    technician_acknowledged_by text,
    action_level integer CHECK (action_level BETWEEN 1 AND 4),
    monitoring_target_jobs integer NOT NULL DEFAULT 5 CHECK (monitoring_target_jobs > 0),
    review_date date NOT NULL,
    status text NOT NULL DEFAULT 'MONITORING'
        CHECK (status IN ('MONITORING', 'CLOSED', 'ESCALATED')),
    decision_note text,
    decided_by text,
    decided_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_technician_reviews_technician ON technician_reviews (technician_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_technician_reviews_case ON technician_reviews (case_record_id);

CREATE TABLE IF NOT EXISTS technician_review_edits (
    edit_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id uuid NOT NULL REFERENCES technician_reviews(review_id),
    edited_by text NOT NULL,
    before_values jsonb NOT NULL,
    after_values jsonb NOT NULL,
    edited_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS technician_review_followups (
    followup_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id uuid NOT NULL REFERENCES technician_reviews(review_id),
    job_no text NOT NULL,
    job_date date,
    checklist_status text NOT NULL CHECK (checklist_status IN ('COMPLETE', 'INCOMPLETE', 'NOT_CHECKED')),
    evidence_status text NOT NULL CHECK (evidence_status IN ('COMPLETE', 'MISSING', 'NOT_CHECKED')),
    qc_result text NOT NULL CHECK (qc_result IN ('PASS', 'FAIL', 'PENDING')),
    rework boolean,
    same_issue boolean,
    reviewer text NOT NULL,
    evidence_reference text,
    note text,
    result text NOT NULL CHECK (result IN ('PASS', 'FOLLOW_UP')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (review_id, job_no)
);

CREATE INDEX IF NOT EXISTS idx_review_followups_review ON technician_review_followups (review_id, created_at);

CREATE TABLE IF NOT EXISTS technician_review_followup_edits (
    edit_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    followup_id uuid NOT NULL REFERENCES technician_review_followups(followup_id),
    edited_by text NOT NULL,
    before_values jsonb NOT NULL,
    after_values jsonb NOT NULL,
    edited_at timestamptz NOT NULL DEFAULT now()
);
