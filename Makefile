.PHONY: install reinstall run run-src run-sql db-seed db-rev db-upgrade db-downgrade db-reset smoke-sql smoke-sql-twice check-import fmt lint typecheck check clean

PY := python3

install:
	$(PY) -m pip install -e .

reinstall:
	$(PY) -m pip uninstall -y sublease-matcher-api || true
	rm -rf build dist *.egg-info
	$(PY) -m pip install -e .

run:
	uvicorn sublease_matcher.api.main:app --reload

run-src:
	uvicorn --app-dir src sublease_matcher.api.main:app --reload

run-sql:
	SM_STORAGE=sqlalchemy uvicorn --app-dir src sublease_matcher.api.main:app --reload

db-seed:
	$(PY) scripts/seed_db.py

db-rev:
	alembic revision --autogenerate -m "$(MSG)"

db-upgrade:
	alembic upgrade head

db-downgrade:
	alembic downgrade -1

db-reset:
	bash scripts/db_reset.sh

smoke-sql:
	bash scripts/smoke_sql.sh

smoke-sql-twice:
	bash scripts/smoke_migrate_twice.sh

check-import:
	$(PY) -c "import sys,pkgutil,importlib; print('sys.path0=',sys.path[0]); print('has_pkg=', any(m.name=='sublease_matcher' for m in pkgutil.iter_modules())); m=importlib.import_module('sublease_matcher.api.main'); print('main_file=',getattr(m,'__file__','<unknown>'))"

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
