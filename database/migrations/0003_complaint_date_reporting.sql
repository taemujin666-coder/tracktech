-- M1.1.1: distinguish historical order references from current-period data gaps.
-- Complaint reporting always uses complaint_date; completed_date remains context only.

UPDATE case_records
SET link_status = 'JOB_REFERENCE_REQUIRES_REVIEW'
WHERE link_status = 'JOB_NOT_FOUND';

ALTER TABLE case_records DROP CONSTRAINT IF EXISTS case_records_link_status_check;
ALTER TABLE case_records ADD CONSTRAINT case_records_link_status_check
    CHECK (link_status IN (
        'MATCHED',
        'REFERENCE_OUTSIDE_CURRENT_JOB_DATA',
        'JOB_REFERENCE_REQUIRES_REVIEW',
        'TECHNICIAN_CONFLICT'
    ));
