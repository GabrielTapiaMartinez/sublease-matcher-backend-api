from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sublease_matcher.api.config import get_settings

settings = get_settings()
if not settings.database_url:
    raise RuntimeError("SM_DATABASE_URL must be set for SQLAlchemy dev setup")

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
