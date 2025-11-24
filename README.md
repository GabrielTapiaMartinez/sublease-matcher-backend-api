# Sublease Matcher API

FastAPI HTTP surface for the Sublease Matcher platform. Provides in-memory adapters, typed DTOs, and health/debug utilities so the frontend team can iterate quickly.

## Repository Layout Requirement
To run the backend successfully, backend-core and backend-api must be placed as sibling directories:
```
<root>/
  sublease-matcher-backend-core/
  sublease-matcher-backend-api/
```
The Makefile sets `PYTHONPATH_DEV := src:../sublease-matcher-backend-core/src`, which requires both repos to sit next to each other in the same parent folder. If they are not siblings, imports such as `sublease_matcher.core` will fail.

## Storage modes
- `memory` (default): in-memory storage, great for quick smoke tests; no Postgres required.
- `sqlalchemy`: Postgres-backed storage using SQLAlchemy, Alembic migrations, and the SQL unit of work.

`SM_STORAGE` selects the backend (`memory` or `sqlalchemy`). `SM_DATABASE_URL` points at your Postgres instance; the Makefile defines `DB_DEV_URL` as the default local dev database (`sublease_dev_sql`).

## Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
cp .env.example .env        # optional; adjust if needed
make install                # install API; optionally pip install -e ../sublease-matcher-backend-core
make check                  # lint + typecheck
```

## Backend quickstart
See `docs/db/README.md` for OS-specific Postgres setup and migration details.

### In-memory (no Postgres)
```bash
make run-src
curl -s http://127.0.0.1:8000/healthz
```

### SQL dev (Postgres)
```bash
createdb sublease_dev_sql          # one-time creation
make db-dev-reset-sql              # migrations + deterministic seed data
make run-sql                       # SQL-backed API (uses DB_DEV_URL)
# Optional smoke:
make db-dev-smoke-sql
```

## Choosing a backend
- Use `memory` (default) when hacking on endpoints or iterating quickly without Postgres.
- Use `sqlalchemy` when working on persistence, testing queries, or running smoke tests with real data.

## Endpoints
- Health: `GET /healthz`
- Seeker profile: `GET /seekers/me/profile`, `PUT /seekers/me/profile`, aliases `GET /profiles/me`, `PUT /profiles/me`, toggle visibility `PATCH /profiles/hide`
- Host listing: `GET /hosts/me/listing`, `PUT /hosts/me/listing`, aliases `GET /listings/mine`, `GET /listings/{id}`, publish toggle `PATCH /listings/{id}/publish`
- Swipe flows: `GET /swipe/queue/seeker`, `GET /swipe/queue/host`, `POST /swipe/swipes`, `POST /swipe/swipes/undo`
- Matches: `GET /swipe/matches/me` and alias `GET /matches`
- Debug seeds: `GET /_debug/seed_counts`

## Environment
- `.env` is optional but recommended; `CORS_ORIGINS` accepts a comma-separated list (defaults to `http://localhost:3000,http://127.0.0.1:3000`).
- Requests can impersonate users via the debug header `X-Debug-User-Id` (defaults: seekers `user-1`, hosts `user-10`).

## API Smoke Tests
- Health:
  ```bash
  curl -s http://127.0.0.1:8000/healthz | jq
  ```
- Seeker profile (with debug header):
  ```bash
  curl -s http://127.0.0.1:8000/seekers/me/profile \
    -H "X-Debug-User-Id: user-1" | jq
  ```
- Problem details examples:
  ```bash
  # 404 when host context is missing
  curl -i http://127.0.0.1:8000/swipe/queue/host \
    -H "X-Debug-User-Id: user-999"

  # 422 validation failure
  curl -i -X POST http://127.0.0.1:8000/swipe/swipes \
    -H "Content-Type: application/json" \
    -d '{"targetId":"listing-1","decision":"maybe"}'
  ```

## Frontend Integration
- React/Next dev servers can call the API without CORS issues:
  ```javascript
  fetch("http://127.0.0.1:8000/healthz")
    .then((r) => r.json())
    .then(console.log);
  ```
- Example authenticated fetch:
  ```javascript
  fetch("http://127.0.0.1:8000/seekers/me/profile", {
    headers: { "X-Debug-User-Id": "user-1" },
  });
  ```

## Tooling & Quality
- Format: `make fmt`
- Lint: `make lint`
- Type-check: `make typecheck`
- Combined quality gate: `make check`
- Clean build artifacts: `make clean`

## Troubleshooting
- Prefer `make run-src` to avoid `PYTHONPATH` issues with the src layout.
- If imports drift, reinstall with `make reinstall`.
- To confirm packaging, run `make check-import`.
