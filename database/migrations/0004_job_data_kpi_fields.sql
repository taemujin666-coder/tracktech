-- Job Data flags are retained for operational reconciliation. Performance
-- Summary uses Job Data for volume/QC and Complaint Log for Complaint/Rework.

ALTER TABLE job_records ADD COLUMN IF NOT EXISTS complaint boolean;
ALTER TABLE job_records ADD COLUMN IF NOT EXISTS rework boolean;
ALTER TABLE job_records ADD COLUMN IF NOT EXISTS integrity_violation boolean;

ALTER TABLE performance_snapshots ADD COLUMN IF NOT EXISTS total_jobs integer;
ALTER TABLE performance_snapshots ADD COLUMN IF NOT EXISTS complaint_cases integer;
ALTER TABLE performance_snapshots ADD COLUMN IF NOT EXISTS integrity_violations integer;
ALTER TABLE performance_snapshots ADD COLUMN IF NOT EXISTS complaint_rate numeric(7, 4);
ALTER TABLE performance_snapshots ADD COLUMN IF NOT EXISTS rework_rate numeric(7, 4);
ALTER TABLE performance_snapshots ADD COLUMN IF NOT EXISTS qc_fail_rate numeric(7, 4);
ALTER TABLE performance_snapshots ADD COLUMN IF NOT EXISTS combined_rate numeric(7, 4);
ALTER TABLE performance_snapshots ADD COLUMN IF NOT EXISTS volume_context text;
