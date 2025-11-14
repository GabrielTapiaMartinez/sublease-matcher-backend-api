# Database Migrations

Run Alembic commands against a Postgres database URL supplied via `SM_DATABASE_URL`.

```bash
export SM_DATABASE_URL="postgresql+psycopg://$USER@localhost:5432/sublease_gab_dev"
PYTHONPATH=src alembic upgrade head
```

or use the Make targets:

- `make db-upgrade` → upgrades to head
- `make db-downgrade` → reverts a single migration
- `make db-rev MSG="add new table"` → autogenerates a revision

## Enum policy

- Enum types (`decision_t`, `listing_status_t`, `match_status_t`, `role_t`, `term_t`) are created once per migration at the top of the script using `enum.create(bind=..., checkfirst=True)`.
- Every column must reference `enum.copy(create_type=False)` to avoid duplicate `CREATE TYPE`.
- Never allow Alembic autogenerate to inline `CREATE TYPE` statements inside table DDL.
