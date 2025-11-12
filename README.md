# Sublease Matcher API

FastAPI HTTP surface for the Sublease Matcher platform. Provides in-memory adapters, typed DTOs, and health/debug utilities so the frontend team can iterate quickly.

## Quickstart
1. Create a Python 3.12 virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Copy environment defaults and adjust if necessary:
   ```bash
   cp .env.example .env
   ```
3. Install the API (and optionally the core package):
   ```bash
   make install
   pip install -e ../sublease-matcher-backend-core
   ```
4. Run the server (src-layout aware):
   ```bash
   make run-src
   ```

## Backend for teammates
1. `export SM_DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/sublease`
2. `make db-upgrade db-seed`
3. `make run-sql` (or `make smoke-sql` for a quick health check)

Need more details? Start with `docs/db/README.md` for schema + migration notes.

## Endpoints
- Health: `GET /healthz`
- Seeker profile: `GET /seekers/me/profile`, `PUT /seekers/me/profile`, aliases `GET /profiles/me`, `PUT /profiles/me`, toggle visibility `PATCH /profiles/hide`
- Host listings: `GET /hosts/me/listing`, `PUT /hosts/me/listing`, `POST /listings`, `PUT /listings/{id}`, `GET /listings/mine`, `GET /listings/{id}`, `PATCH /listings/{id}/publish`
- Swipe flows: `GET /swipe/queue/seeker`, `GET /swipe/queue/host`, `POST /swipe/swipes`, `POST /swipe/swipes/undo`
- Matches: `GET /swipe/matches/me` and alias `GET /matches`
- Debug seeds: `GET /_debug/seed_counts`

## Environment
- `.env` is optional but recommended; `CORS_ORIGINS` accepts a comma-separated list (defaults to `http://localhost:3000,http://127.0.0.1:3000`).
- Requests can impersonate users via the debug header `X-Debug-User-Id` (defaults: seekers `user-1`, hosts `user-10`).
- Storage backends:
  - `SM_STORAGE=memory` (default) keeps everything in the in-memory adapters.
  - `SM_STORAGE=sqlalchemy` switches to Postgres via SQLAlchemy; set `SM_DATABASE_URL` (example `postgresql+psycopg://postgres:postgres@127.0.0.1:5432/sublease`).
  - Seed the SQL database with `make db-seed` (idempotent) and run the API with `make run-sql`.

## SQL Storage
1. Ensure Postgres is running and accessible via `SM_DATABASE_URL`.
2. (One-time) run `make db-seed` to create the tables and insert the canonical demo records (`user-1` / `seeker-1`, `user-10` / `host-1`, `listing-1`).
3. Start the API with SQL storage enabled:
   ```bash
   make run-sql
   ```
4. All curl smoke tests from below work unchanged; only the persistence layer differs.

## Migrations
- Set `SM_DATABASE_URL` to your Postgres connection string before running any Alembic command.
- Create a revision (uses autogenerate): `make db-rev MSG="describe change"`.
- Apply the latest schema: `make db-upgrade`.
- Step back one revision: `make db-downgrade`.
- Migrations live under `alembic/versions`; see `docs/db/migrations.md` for workflow tips, how to read the `Alembic URL -> ...` log, and enum troubleshooting guidance.

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

## Listings Examples
- Host view (`GET /listings/mine` always returns an array that is empty or a single listing):
  ```bash
  curl -s http://127.0.0.1:8000/listings/mine \
    -H "X-Debug-User-Id: user-10" | jq
  ```
- Create and update a listing (new host `user-42`, showing roommates and negative price clamping):
  ```bash
  LISTING_ID=$(
    curl -s -X POST http://127.0.0.1:8000/listings \
      -H "Content-Type: application/json" \
      -H "X-Debug-User-Id: user-42" \
      -d '{
        "title": "Sunny Randall Park room",
        "pricePerMonth": "-50",
        "city": "Eau Claire",
        "state": "wi",
        "availableFrom": "2025-09-01",
        "contactEmail": "host42@example.edu",
        "roommates": [
          {
            "name": "Sam",
            "pronouns": "she/her",
            "sleepingHabits": "night owl",
            "studyHabits": "apartment desk",
            "interests": ["music", "movies"],
            "bio": "Creative writing major."
          }
        ]
      }' | jq -r '.id'
  )

  curl -s -X PUT http://127.0.0.1:8000/listings/$LISTING_ID \
    -H "Content-Type: application/json" \
    -H "X-Debug-User-Id: user-42" \
    -d '{
      "title": "Updated Randall Park room",
      "pricePerMonth": "725",
      "bio": "Freshly painted bedroom near campus",
      "roommates": [
        {
          "name": "Sam",
          "pronouns": "she/her",
          "sleepingHabits": "night owl",
          "studyHabits": "apartment desk",
          "interests": ["music", "movies"],
          "bio": "Creative writing major."
        },
        {
          "name": "Jordan",
          "pronouns": "he/him",
          "sleepingHabits": "early bird",
          "studyHabits": "library focused",
          "interests": ["climbing"],
          "bio": "Education major."
        }
      ]
    }' | jq
  ```
- Publish/unlist toggle (`PATCH /listings/{id}/publish`) and public view:
  ```bash
  curl -s -X PATCH http://127.0.0.1:8000/listings/$LISTING_ID/publish \
    -H "X-Debug-User-Id: user-42" | jq '.status'

  curl -s -X PATCH http://127.0.0.1:8000/listings/$LISTING_ID/publish \
    -H "X-Debug-User-Id: user-42" | jq '.status'

  curl -s http://127.0.0.1:8000/listings/$LISTING_ID | jq
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

## Tooling
- `make lint` – runs Ruff (with autofix) and then Black so imports stay sorted.
- `make typecheck` – runs `mypy src` to avoid the repository-name hyphen issue.
- `make check` – runs Ruff (no autofix) followed by `mypy src` for CI-style verification.

## Troubleshooting
- **Duplicate ENUMs**: Ensure migrations are the only schema authority. If you ever see `type "listing_status_t" already exists`:
  1. Confirm `SM_DATABASE_URL` matches the connection you're inspecting (`echo $SM_DATABASE_URL` plus the `Alembic URL -> ...` log line).
  2. Verify there is no `Base.metadata.create_all()` call (the seed script already refuses to create tables).
  3. Drop and recreate the database via `make db-reset`, then rerun `make smoke-sql` and `make smoke-sql-twice`.
  4. Inspect enums with `psql "$SM_DATABASE_URL" -c "\dT+ decision_t listing_status_t match_status_t role_t term_t"`; drop stale types if needed.

## Verification Checklist
Run these commands when validating a fresh setup:
1. `echo $SM_DATABASE_URL` → match what you expect.
2. `dropdb --if-exists sublease && createdb sublease` (adjust DB name to match your URL).
3. `PYTHONPATH=src python -m alembic upgrade head` (run twice; the second invocation should be a no-op).
4. `psql "$SM_DATABASE_URL" -c "\dT+"` → lists the five enum types in `public`.
5. `PYTHONPATH=src python -m alembic current` → shows the current revision (or `None` if brand-new).
6. `make db-reset`, `make smoke-sql`, and `make smoke-sql-twice` → exercise full migration + seed flows.
7. `uvicorn --app-dir src sublease_matcher.api.main:app --reload` → manual curls against the same DB.
## Troubleshooting
- Prefer `make run-src` to avoid `PYTHONPATH` issues with the src layout.
- If imports drift, reinstall with `make reinstall`.
- To confirm packaging, run `make check-import`.
