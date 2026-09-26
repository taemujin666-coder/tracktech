# TrackTech

TrackTech is a local technician performance and case tracker for Operations. It is separate from DDE and starts from existing Excel data rather than company order integration.

## Workflow

`Excel -> evidence preview -> incremental import -> performance history -> watchlist -> action -> evidence review`

M1.1 reads the real workbook layout (`Job Data`, `Complaint Log`, and `Technician Master`). It keeps every Job Data row because one Order No. can contain several products. Complaint Log is the only complaint-case truth source.

Evidence-first rules:

- Missing data is never converted to Pass, Fail, or “no complaint”.
- Complaint totals and time periods always use `Complaint Date`; installation/completion dates are context only.
- A blank QC outcome on `Cancel` or `Not Complete` is not labelled “not inspected”; it is stored as not applicable for that job status.
- `PWS1` and `PWS51` job volume is retained, but no technician profile or individual score is created.
- Tech IDs missing from Technician Master stay `PENDING_MASTER_MATCH`.
- A Complaint/Job Tech ID conflict stays `TECHNICIAN_CONFLICT` for human review and is not auto-scored.
- Re-importing the same file is idempotent. New cases are inserted, changed cases are updated, and omitted historical cases are never deleted.
- Customer names are deliberately not persisted by this milestone.

## Local setup on macOS

For the dashboard and Import Preview, no database is required:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.api.main:app --reload
```

Open `http://127.0.0.1:8000`. Demo mode allows the complete evidence preview but intentionally blocks the final database write.

For live import, create a PostgreSQL database named `tracktech` alongside, but separate from, `dde`. Copy `.env.example` to `.env`, export its values, and run migrations:

```bash
set -a; source .env; set +a
python -m app.infrastructure.migrations
```

Then switch `TRACKTECH_DEMO_MODE=false` and run:

```bash
uvicorn app.api.main:app --reload
```

The import endpoint commits the workbook in one transaction and records filename, content hash, timestamp, inserted/updated/skipped counts, conflicts, and unmatched cases. The source workbook itself is never copied into the repository or database.

## Tests

The live Dashboard renders a monthly Jobs/Rework combo chart from PostgreSQL.
Jobs and QC Fail follow `Job Data` install dates; Complaints and Rework follow
`Complaint Log` complaint dates. Source recency is shown beside the chart; a
partially observed month is labelled preliminary. Technician profile signal
bars continue to use Complaint Log counts from the imported snapshot and are
cumulative, independently of the monthly Watchlist pilot.

### Monthly Watchlist pilot

The Watchlist page uses August 2026 as its initial trial month. It counts jobs by
`Job Data` install date and Complaint, Rework, and QC Fail by `Complaint Log`
complaint date for each verified technician. Combined Rate is the sum of those
three case counts divided by jobs in that month, matching Technician Tracker.

- T3 Critical: Combined Rate is strictly greater than 10%, at any job volume.
- T2 Watchlist: at least three distinct complaint `Order No.` values in the month.
- With no jobs in the month, the rate is N/A; three distinct problem orders
  still qualify for T2. One case with multiple signals counts as one order.

The monthly tier identifies teams to follow up. Technician profiles and the YTD
dashboard continue to show cumulative history. Confirmed Root Cause and Action
Level remain separate decisions based on case evidence.

```bash
python -m unittest discover -s tests -v
```

Tests generate synthetic workbooks only. Production Excel files, database dumps, and exports are ignored by Git.

## Repository structure

```text
app/domain          Business entities and scoring rules
app/application     Import and dashboard use cases
app/ports           Interfaces between rules and infrastructure
app/infrastructure  PostgreSQL and migration adapters
app/api             FastAPI HTTP adapter
database            SQL migrations
static              Local browser UI
tests               Deterministic business and import tests
```

## Milestones

- M0/M1: clean-architecture bootstrap, demo dashboard, explainable scoring rules
- M1.1: evidence-first preview and idempotent PostgreSQL import
- Next: imported-data reconciliation queue and performance snapshot calculation
