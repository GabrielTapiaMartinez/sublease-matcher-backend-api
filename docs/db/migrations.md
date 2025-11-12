# Database Migrations

Alembic manages schema changes for the SQL storage backend. The configuration lives at the repo root (`alembic.ini`) and uses the models defined under `sublease_matcher/api/adapters/sqlalchemy/models.py` as the autogenerate target metadata.

## Prerequisites
- Install the project (which now depends on `alembic`).
- Ensure Postgres is reachable and export `SM_DATABASE_URL`, e.g.:
  ```bash
  export SM_DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/sublease
  ```
- Every Alembic invocation logs `Alembic URL -> ...` so you can confirm the target database; if that line doesn't match what you expect from `echo $SM_DATABASE_URL`, stop immediately.
- All enums live in the `public` schema. List them via `psql "$SM_DATABASE_URL" -c "\dT+ decision_t listing_status_t match_status_t role_t term_t"`.

## Workflow
1. **Create a revision (autogenerate first draft):**
   ```bash
   make db-rev MSG="add seeker photos table"
   ```
   Review the generated file under `alembic/versions/` and hand-edit if needed (for example, to add data migrations or adjust constraints).
2. **Upgrade to the latest schema:**
   ```bash
   make db-upgrade
   ```
3. **Downgrade one step (useful while iterating locally):**
   ```bash
   make db-downgrade
   ```
4. **Seed data (optional for local dev):**
   ```bash
   make db-upgrade
   make db-seed
   ```
5. **Full reset (drops/recreates DB, migrates, seeds, and uses the same URL as Alembic):**
   ```bash
   make db-reset
   ```
6. **Smoke tests:**
   - `make smoke-sql` → migrate + seed + boot API and curl a few endpoints.
   - `make smoke-sql-twice` → reset, upgrade twice, seed twice, then curl endpoints to prove idempotence.

## Enum and Constraint Guidance
- Enums (`decision_t`, `listing_status_t`, `match_status_t`, `role_t`, `term_t`) are real Postgres types defined once in the initial revision. When adding/removing enum values, issue the appropriate `ALTER TYPE ... ADD VALUE` statements before updating the ORM.
- Check constraints (price non-negative, date range validation, etc.) are explicit in the initial migration. If you add new domain rules, prefer database-level constraints and make sure the migration enforces them (use `op.create_check_constraint` when autogenerate cannot infer them).
- When in doubt, run `make db-upgrade` followed by `make db-seed` to confirm the schema and demo data still agree with the API layer.

## Troubleshooting: Duplicate ENUMs
1. Ensure only Alembic owns schema creation (no `Base.metadata.create_all()` in scripts); the seed script now refuses to create tables.
2. Confirm Alembic is pointing at the correct DB (`Alembic URL -> ...` log + `echo $SM_DATABASE_URL`).
3. If you accidentally created enums in a different database/schema, use `psql "$SM_DATABASE_URL" -c "\dT+"` to inspect and `DROP TYPE ...` if needed.
4. Run `make db-reset` to drop/recreate the database, then `make smoke-sql`/`make smoke-sql-twice` to validate idempotence.
