#!/usr/bin/env bash
set -euo pipefail

DB_URL="${SM_DATABASE_URL:-postgresql://guli@localhost:5432/sublease}"
export SM_DATABASE_URL="$DB_URL"

eval "$(
  python - <<'PY'
import os, shlex
from urllib.parse import urlsplit

url = os.getenv("SM_DATABASE_URL", "postgresql://guli@localhost:5432/sublease")
parts = urlsplit(url)
dbname = parts.path.lstrip("/").split("?")[0] or "postgres"

def emit(key: str, value: str | None) -> None:
    if value is None:
        value = ""
    print(f"{key}={shlex.quote(value)}")

emit("PGHOST", parts.hostname or "localhost")
emit("PGPORT", str(parts.port or 5432))
emit("PGUSER", parts.username or "")
emit("PGPASSWORD", parts.password or "")
emit("DBNAME", dbname)
PY
)"

[[ -n "${PGHOST:-}" ]] && export PGHOST
[[ -n "${PGPORT:-}" ]] && export PGPORT
[[ -n "${PGUSER:-}" ]] && export PGUSER
[[ -n "${PGPASSWORD:-}" ]] && export PGPASSWORD

echo "[db-reset] Dropping ${DBNAME}..."
dropdb --if-exists "$DBNAME"

echo "[db-reset] Creating ${DBNAME}..."
createdb "$DBNAME"

echo "[db-reset] Applying migrations..."
PYTHONPATH=src python -m alembic upgrade head

echo "[db-reset] Seeding demo data..."
PYTHONPATH=src python scripts/seed_db.py

echo "[db-reset] Complete."
