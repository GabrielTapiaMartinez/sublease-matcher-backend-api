# Database Docs

- [Schema](./schema.md) – entity list, constraints, and ERD for the current Postgres layout.
- [Migrations](./migrations.md) – Alembic workflow, commands, and enum guidance.

## Getting Started with SQL Storage
1. Export your Postgres connection string: `export SM_DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/sublease`.
2. Align the database with the current models and seed demo data: `make db-upgrade db-seed` (or just run `make db-reset` to drop/create/migrate/seed in one shot).
3. Run the API on SQL storage: `make run-sql` (or use `make smoke-sql` / `make smoke-sql-twice` for scripted health checks).
