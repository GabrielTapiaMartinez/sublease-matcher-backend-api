#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${SM_DATABASE_URL:-}" ]]; then
  echo "SM_DATABASE_URL must be set to run the SQL smoke test." >&2
  exit 1
fi

echo "[smoke-sql] Running migrations..."
PYTHONPATH=src python -m alembic upgrade head

echo "[smoke-sql] Seeding demo data..."
PYTHONPATH=src python scripts/seed_db.py

echo "[smoke-sql] Starting API server (sqlalchemy backend)..."
SERVER_LOG="$(mktemp -t smoke-sql-XXXX.log)"
SM_STORAGE=sqlalchemy uvicorn --app-dir src sublease_matcher.api.main:app --reload >"$SERVER_LOG" 2>&1 &
SERVER_PID=$!

cleanup() {
  if kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "[smoke-sql] Waiting for server to become ready..."
for _ in {1..30}; do
  if curl -sf http://127.0.0.1:8000/healthz >/dev/null; then
    break
  fi
  sleep 1
done

sleep 1

curl -sf http://127.0.0.1:8000/healthz >/dev/null
echo "[OK] GET /healthz"

curl -sf -H "X-Debug-User-Id: user-1" http://127.0.0.1:8000/seekers/me/profile >/dev/null
echo "[OK] GET /seekers/me/profile (user-1)"

curl -sf -H "X-Debug-User-Id: user-10" http://127.0.0.1:8000/listings/mine >/dev/null
echo "[OK] GET /listings/mine (user-10)"

echo "[smoke-sql] All smoke checks passed."
