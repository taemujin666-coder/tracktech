# TrackTech M0 M1 Scope

TrackTech is a separate local system of record for technician performance. It does not create or assign company orders and does not integrate with the enterprise order workflow in this release.

## Data ownership

| Data | Owner in this release |
| --- | --- |
| Imported Job Data and Technician Master | Reference data imported from Operations Excel |
| Complaint, Root Cause, Rework and Action | TrackTech case workflow |
| Watchlist and score snapshots | TrackTech calculation with visible reasons |
| Evidence | Link and review status only; files stay in the approved external store |

## Non negotiable data rules

- `Job No` and `Tech ID` are matching keys; an unlinked complaint must be reviewed and must not change a technician score.
- `PENDING_INVESTIGATION` is not a confirmed technician cause.
- Missing Complaint Log coverage is not a zero-complaint result.
- QC fail rate is reported only against inspected jobs, while QC coverage is displayed separately.
- A technician with fewer than 20 completed jobs is marked `INSUFFICIENT_DATA`, not ranked by a rate.
- Safety, Property Damage, or Integrity cases require escalation without waiting for the composite score.

## M0 M1 delivered in this repository

1. PostgreSQL schema and repeatable migrations for TrackTech only.
2. Excel source validation for the three approved input sheets.
3. Explainable initial scoring and watchlist rules covered by deterministic tests.
4. A local FastAPI dashboard with demo mode so the UI can be reviewed before a database is connected.

## Deferred

- Persisting a validated workbook and creating cases through the UI.
- Authentication, role permissions, and workflow audit trails.
- Uploading evidence files; links and review status are sufficient for the pilot.
- Any connection to company enterprise systems.

