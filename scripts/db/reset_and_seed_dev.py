#!/usr/bin/env python3
"""[db-reset] Apply Alembic migrations and seed the local SQL dev database."""

from __future__ import annotations

import os
import subprocess
import sys
from getpass import getuser
from pathlib import Path

DEFAULT_DB_NAME = "sublease_dev_sql"
DEFAULT_PYTHONPATH = "src:../sublease-matcher-backend-core/src"


def _log(message: str) -> None:
    print(f"[db-reset] {message}")


def _default_database_url() -> str:
    user = os.environ.get("USER") or getuser()
    return f"postgresql+psycopg://{user}@localhost:5432/{DEFAULT_DB_NAME}"


def _ensure_database_url(env: dict[str, str]) -> str:
    database_url = env.get("SM_DATABASE_URL")
    if not database_url:
        database_url = _default_database_url()
        env["SM_DATABASE_URL"] = database_url
    return database_url


def _run(cmd: list[str], env: dict[str, str]) -> None:
    subprocess.run(cmd, check=True, env=env)


def main() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = env.get("PYTHONPATH", DEFAULT_PYTHONPATH)
    database_url = _ensure_database_url(env)
    _log(f"Using database URL: {database_url}")
    _log("Running Alembic migrations...")
    _run([sys.executable, "-m", "alembic", "upgrade", "head"], env=env)
    seed_script = Path(__file__).with_name("seed_sql.py")
    _log("Running seed script...")
    _run([sys.executable, str(seed_script)], env=env)
    _log("Local SQL dev database reset and seeded.")


if __name__ == "__main__":
    main()
