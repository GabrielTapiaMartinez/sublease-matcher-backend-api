# Database Onboarding

Local dev can run with the in-memory backend or Postgres. SQL storage uses Postgres + SQLAlchemy + Alembic + the SQL unit of work. See `docs/db/schema.md` for table notes and `docs/db/migrations.md` for Alembic commands.

## Local SQL dev workflow

### Prerequisites
- Postgres installed locally.
- `psql`, `createdb`, and `dropdb` available on your shell PATH.
- macOS: `brew install postgresql@16` (or Postgres.app), then `brew services start postgresql@16`.
- Windows: install Postgres via the official installer; start the `postgresql` service from Services or pgAdmin; ensure `psql` works in your terminal.

### Commands
```bash
createdb sublease_dev_sql            # one-time dev DB creation
make db-dev-reset-sql                # migrations + deterministic seed data
make db-dev-smoke-sql                # optional: /healthz + sample seeker/listing checks
make run-sql                         # API with SQL backend (uses DB_DEV_URL)
```

## Seed data (dev only)
- Deterministic IDs: seeker (`user-1` / `seeker-1`), host (`user-10` / `host-1` / `listing-1`).
- Relative photo paths: `/static/mock/seekers/...`, `/static/mock/listings/...`, `/static/mock/roommates/...`.
- Dev-only: `db-dev-reset-sql` truncates/wipes local dev data. Do not point dev helpers at shared or production databases.
We support two storage backends:

- `memory` (default): no Postgres required.
- `sqlalchemy`: Postgres with SQLAlchemy + Alembic. The HTTP API is identical; only persistence differs.

## Environment
- `SM_STORAGE`: `memory` (default) or `sqlalchemy`. Unset/`memory` uses the in-memory UoW; `sqlalchemy` uses the SQLAlchemy UoW.
- `SM_DATABASE_URL`: Postgres SQLAlchemy URL, e.g. `postgresql+psycopg://$USER@localhost:5432/sublease_dev_sql`.
- Standard dev DB name: `sublease_dev_sql`.
- Standard dev URL: `postgresql+psycopg://$USER@localhost:5432/sublease_dev_sql`.

## Mac setup
1. Install Postgres: `brew install postgresql@16` (or use Postgres.app).
2. Start the server: `brew services start postgresql@16` (or start from Postgres.app UI).
3. Verify:
   ```bash
   createdb sublease_dev_sql  # no error if it already exists
   psql "postgresql://$USER@localhost:5432/sublease_dev_sql" -c "SELECT 1;"
   ```

## Windows setup
- **Recommended (WSL2 + Ubuntu):** install WSL, install `postgresql` inside the distro, and run both Postgres and the backend inside WSL using `localhost:5432`.
- **Native installer:** install Postgres from the official Windows installer, ensure `psql` is on PATH, then create the DB with `createdb sublease_dev_sql` and verify with `psql ... -c "SELECT 1;"`.

## Dev workflows
- In-memory:
  - No Postgres required; leave `SM_STORAGE` unset or `memory`.
  - Start server: `make run-src`
- SQL:
  - `createdb sublease_dev_sql` (once).
  - `make db-dev-reset-sql` (applies migrations and seeds deterministic data).
  - `make db-dev-smoke-sql` (optional; runs /healthz, seeker profile, listings).
  - `SM_STORAGE=sqlalchemy SM_DATABASE_URL=postgresql+psycopg://$USER@localhost:5432/sublease_dev_sql make run-sql`
    to run the API against Postgres.

## Seed references
- Deterministic IDs: `user-1`/`seeker-1`, `user-2`/`seeker-2`, `user-10`/`host-1`, `listing-1`.
- Relative photo paths used by seeds:
  - Seeker photos: `/static/mock/seekers/<seeker_id>-<n>.jpg`
  - Listing photos: `/static/mock/listings/<listing_id>-<n>.jpg`
  - Roommate photos: `/static/mock/roommates/<roommate_id>.jpg`
