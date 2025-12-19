# Updating Your Local Database

Since we've added a new `major` column (and potentially other schema changes), you'll need to update your local database to match the new schema.

## 1. Prerequisites

Make sure your backend virtual environment is activated and dependencies are installed.

```bash
cd sublease-matcher-backend-api
source .venv/bin/activate  # or just ensure you are using the correct python env
make install
```

## 2. Run the Migration

Run the following command in the `sublease-matcher-backend-api` directory to apply the latest changes (including the new `major` column):

```bash
make db-upgrade
```

This command runs `alembic upgrade head` for you, while ensuring necessary environment variables (like `PYTHONPATH` and `SM_DATABASE_URL`) are correctly set.

## 3. Verify the Update

Run the smoke test to ensure your database is reachable and functioning correctly:

```bash
make smoke-sql
```

If this command completes without error, your database is correctly configured and accessible by the application.

## Troubleshooting

If you encounter errors like "Target database is not up to date", it usually means your local database is behind. `alembic upgrade head` handles this.

If you see errors about "Multiple heads", you may need to merge heads, but for a simple column addition, `upgrade head` is typically all you need.
