.PHONY: install reinstall run run-src run-sql check-import fmt lint typecheck check clean db-create-dev db-upgrade db-downgrade db-rev db-dev-reset-sql db-dev-smoke-sql smoke-sql

PY := python3
DB_DEV_URL ?= postgresql+psycopg://$$(whoami)@localhost:5432/sublease_dev_sql
PYTHONPATH_DEV := src:../sublease-matcher-backend-core/src

install:
	$(PY) -m pip install -e .

reinstall:
	$(PY) -m pip uninstall -y sublease-matcher-api || true
	rm -rf build dist *.egg-info
	$(PY) -m pip install -e .

run:
	$(PY) -m uvicorn sublease_matcher.api.main:app --reload

run-src:
	PYTHONPATH=$(PYTHONPATH_DEV) \
		$(PY) -m uvicorn --app-dir src sublease_matcher.api.main:app --reload

run-sql:
	PYTHONPATH=$(PYTHONPATH_DEV) \
		SM_DATABASE_URL="$(DB_DEV_URL)" \
		SM_STORAGE=sqlalchemy \
		$(PY) -m uvicorn --app-dir src sublease_matcher.api.main:app --reload

check-import:
	$(PY) -c "import sys,pkgutil,importlib; print('sys.path0=',sys.path[0]); print('has_pkg=', any(m.name=='sublease_matcher' for m in pkgutil.iter_modules())); m=importlib.import_module('sublease_matcher.api.main'); print('main_file=',getattr(m,'__file__','<unknown>'))"


#testing:

smoke:
	$(PY) scripts/smoke.py


fmt:
	$(PY) -m black .

lint:
	python3 -m ruff check --fix .
	python3 -m black .

typecheck:
	python3 -m mypy ./src

check:
	python3 -m ruff check .
	python3 -m mypy ./src

clean:
	rm -rf __pycache__ pycache .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info

# Database helpers: prefer overriding DB_DEV_URL/SM_DATABASE_URL from your shell instead of hard-coding usernames/hosts; avoid editing DB targets without updating docs.

db-create-dev:
	SM_DATABASE_URL="$(DB_DEV_URL)" \
		PYTHONPATH=$(PYTHONPATH_DEV) python3 scripts/db/create_db_from_models.py

db-upgrade:
	SM_DATABASE_URL="$(DB_DEV_URL)" \
		PYTHONPATH=$(PYTHONPATH_DEV) alembic upgrade head

db-downgrade:
	SM_DATABASE_URL="$(DB_DEV_URL)" \
		PYTHONPATH=$(PYTHONPATH_DEV) alembic downgrade -1

db-rev:
	SM_DATABASE_URL="$(DB_DEV_URL)" \
		PYTHONPATH=$(PYTHONPATH_DEV) alembic revision --autogenerate -m "$$(MSG)"

db-dev-reset-sql:
	SM_DATABASE_URL="$(DB_DEV_URL)" \
		PYTHONPATH=$(PYTHONPATH_DEV) python3 scripts/db/reset_and_seed_dev.py

db-dev-smoke-sql:
	SM_DATABASE_URL="$(DB_DEV_URL)" \
		SM_STORAGE=sqlalchemy \
		PYTHONPATH=$(PYTHONPATH_DEV) python3 scripts/db/smoke_sql.py

db-dev-smoke-sql-w:
	@echo "--- Running DB Smoke Test (Windows) ---"
	@echo "Note: Using default user 'postgres'. You will be prompted for the password."
	@read -s -p "Enter Password for postgres: " PGPASSWORD; \
	echo ""; \
	SM_DATABASE_URL="postgresql+psycopg://postgres@localhost:5432/sublease_dev_sql" \
		SM_STORAGE=sqlalchemy \
		SM_JWT_SECRET="smoke-test-secret-key" \
		SM_SECRET_KEY="another-secret-key" \
		PGPASSWORD="$$PGPASSWORD" \
		PYTHONPATH=$(PYTHONPATH_DEV) \
		PYTHONPATH=$(PYTHONPATH_DEV) python scripts/db/smoke_sql_w.py
smoke-sql: db-dev-smoke-sql
