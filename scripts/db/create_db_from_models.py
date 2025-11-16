#!/usr/bin/env python3
"""[db-create] Recreate the SQLAlchemy schema directly from ORM models (dev only)."""

from __future__ import annotations

from sublease_matcher.api.adapters.sqlalchemy import models
from sublease_matcher.api.adapters.sqlalchemy.db import engine


def main() -> None:
    print("[db-create] Dropping tables from metadata...")
    models.Base.metadata.drop_all(bind=engine)
    print("[db-create] Creating tables from metadata...")
    models.Base.metadata.create_all(bind=engine)
    print("[db-create] Done.")


if __name__ == "__main__":
    main()
