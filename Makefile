.PHONY: install reinstall run run-src check-import fmt lint typecheck check clean db-create-dev

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

db-create-dev:
	SM_DATABASE_URL="postgresql+psycopg://$$(whoami)@localhost:5432/sublease_gab_dev" \
		python3 scripts/create_db_from_models.py
