# TrackTech

TrackTech is a local technician performance and case tracker for Operations. It is separate from DDE and starts from existing Excel data rather than company order integration.

## Initial workflow

`Excel import -> validation -> performance history -> watchlist -> case action -> evidence review`

The first release keeps `Job No` and `Tech ID` as matching keys. It does not assume that missing Complaint or QC data means good performance.

## Local setup on macOS

Create a PostgreSQL database named `tracktech` alongside, but separate from, `dde`. Then copy `.env.example` to `.env`, install the requirements in a Python virtual environment, and run migrations:

```bash
python -m app.infrastructure.migrations
```

Run the local application:

```bash
uvicorn app.api.main:app --reload
```

Open `http://localhost:8000`. The default demo mode is intentional: it lets the Operations team approve the screen and import contract before production data is loaded. Set `TRACKTECH_DEMO_MODE=false` after applying migrations and importing data.

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

## GitHub

This environment cannot access GitHub CLI. After copying this folder to the development Mac, create the portfolio repository and push the current `main` branch. Never commit `.env`, imported production workbooks, evidence links, or live database backups.

