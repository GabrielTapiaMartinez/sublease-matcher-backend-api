#!/usr/bin/env python3
"""Dev helper to recreate the SQLAlchemy schema from the ORM models."""

from __future__ import annotations

from sublease_matcher.api.adapters.sqlalchemy import models
from sublease_matcher.api.adapters.sqlalchemy.db import engine


def main() -> None:
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    main()
