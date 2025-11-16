# AGENTS.md — Sublease Matcher API Codex Guide

## Mission
Generate production-ready FastAPI code with strict typing and Pydantic v2 models.
Keep this repo as the API + adapters layer; never put core logic here.

## Repository map
src/sublease_matcher/api/
│
├── main.py — app entrypoint
├── config.py — pydantic-settings configuration
├── dependencies/ — FastAPI dependencies
├── routers/ — HTTP route handlers
├── adapters/ — implementations of ports (in-memory or DB)
├── interfaces/ — temporary Protocols before core ports
└── services/ — light coordination code

## Conventions
- All functions must have type hints.
- Return errors via the shared `Problem` model (`application/problem+json`).
- Decimal for money, date for dates.
- One router per resource, with OpenAPI examples.
- Use pydantic-settings env prefix `SM_`.
- Linting: ruff + black + mypy (strict).
- No framework imports in the core repo.

## Review checklist
✅ Starts with `uvicorn sublease_matcher.api.main:app --reload`  
✅ `/healthz` returns 200  
✅ All code typed  
✅ README accurate (storage modes, DB docs, Makefile targets)

## How to use Codex here
- Guardrails: only modify files under `src/sublease_matcher/api/*` plus docs/config when requested.
- See runs 1–6 for history: bootstrapped FastAPI, packaging fixes, interface protocols, in-memory adapters/UoW, profile & listing routers, swipe/match flows, CORS and tooling.
- Prompts must keep typing strict and avoid leaking framework code into the shared core repo.
- Add new HTTP endpoints under `routers/`, wiring through adapters/services as needed; add new infrastructure or seed data under `adapters/`; define shared contracts in `interfaces/`.
- Storage modes: `SM_STORAGE=memory` (default) or `sqlalchemy` with `SM_DATABASE_URL`; dev defaults live in the Makefile (`DB_DEV_URL`).
- DB docs live in `docs/db/`; keep README/dev guides aligned when changing DB helpers or Makefile targets.
