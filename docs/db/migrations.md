# Database Migrations

Run Alembic commands against a Postgres database URL supplied via `SM_DATABASE_URL`.

```bash
export DB_DEV_URL="postgresql+psycopg://$USER@localhost:5432/sublease_dev_sql"
export SM_DATABASE_URL="$DB_DEV_URL"
PYTHONPATH=src:../sublease-matcher-backend-core/src SM_DATABASE_URL="$DB_DEV_URL" python3 -m alembic current
PYTHONPATH=src:../sublease-matcher-backend-core/src SM_DATABASE_URL="$DB_DEV_URL" python3 -m alembic upgrade head
PYTHONPATH=src:../sublease-matcher-backend-core/src SM_DATABASE_URL="$DB_DEV_URL" python3 -m alembic downgrade -1
PYTHONPATH=src:../sublease-matcher-backend-core/src SM_DATABASE_URL="$DB_DEV_URL" python3 -m alembic revision --autogenerate -m "message"
```

or use the Make targets:

- `make db-upgrade` → upgrades to head
- `make db-downgrade` → reverts a single migration
- `make db-rev MSG="add new table"` → autogenerates a revision
- `make db-dev-reset-sql` → run migrations + dev seed flow (local only)

After upgrading in dev, rerun the seed flow (`make db-dev-reset-sql` or `scripts/db/seed_sql.py`) to refresh deterministic data.

## Enum policy

- Enum types (`decision_t`, `listing_status_t`, `match_status_t`, `role_t`, `term_t`) live in the `public` schema; the initial migration creates them once.
- If enum values change, add them with `ALTER TYPE` migrations; avoid drop-and-recreate unless absolutely necessary.
- Every column must reference `enum.copy(create_type=False)` to avoid duplicate `CREATE TYPE`. Autogenerate should never inline `CREATE TYPE` inside table DDL.
