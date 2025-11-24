#!/usr/bin/env python3
"""[db-create] Recreate the SQLAlchemy schema directly from ORM models (dev only)."""
# ruff: noqa: E402

from __future__ import annotations

import os
import sys
from getpass import getuser

DEFAULT_DB_NAME = "sublease_dev_sql"
DEFAULT_PYTHONPATH = "src:../sublease-matcher-backend-core/src"


def _default_database_url() -> str:
    user = os.environ.get("USER") or getuser()
    return f"postgresql+psycopg://{user}@localhost:5432/{DEFAULT_DB_NAME}"


def _ensure_database_url() -> str:
    database_url = os.environ.get("SM_DATABASE_URL")
    if not database_url:
        database_url = _default_database_url()
        os.environ["SM_DATABASE_URL"] = database_url
    return database_url


def _ensure_pythonpath() -> None:
    pythonpath = os.environ.get("PYTHONPATH")
    if pythonpath:
        return
    os.environ["PYTHONPATH"] = DEFAULT_PYTHONPATH
    for path in DEFAULT_PYTHONPATH.split(":"):
        if path and path not in sys.path:
            sys.path.insert(0, path)


_ensure_pythonpath()
_ensure_database_url()

from sublease_matcher.api.adapters.sqlalchemy import models
from sublease_matcher.api.adapters.sqlalchemy.db import engine


def main() -> None:
    database_url = os.environ.get("SM_DATABASE_URL")
    if database_url:
        print(f"[db-create] Using database URL: {database_url}")
    print("[db-create] Dropping tables from metadata...")
    models.Base.metadata.drop_all(bind=engine)
    print("[db-create] Creating tables from metadata...")
    models.Base.metadata.create_all(bind=engine)
    print("[db-create] Done.")


if __name__ == "__main__":
    main()
