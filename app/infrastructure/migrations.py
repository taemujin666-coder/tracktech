from __future__ import annotations

import os
from pathlib import Path


def apply_migrations(database_url: str | None = None) -> None:
    import psycopg

    url = database_url or os.environ["TRACKTECH_DATABASE_URL"]
    migration_dir = Path(__file__).resolve().parents[2] / "database" / "migrations"
    with psycopg.connect(url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (filename text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
            )
            cursor.execute("SELECT filename FROM schema_migrations")
            applied = {row[0] for row in cursor.fetchall()}
            for migration in sorted(migration_dir.glob("*.sql")):
                if migration.name in applied:
                    continue
                cursor.execute(migration.read_text())
                cursor.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (migration.name,))
                print(f"Applied {migration.name}")


if __name__ == "__main__":
    apply_migrations()

