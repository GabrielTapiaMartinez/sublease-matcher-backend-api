from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from ..adapters.memory_repos import (
    InMemoryHostRepo,
    InMemoryListingRepo,
    InMemoryMatchRepo,
    InMemorySeekerRepo,
    InMemorySwipeRepo,
)
from ..adapters.memory_uow import InMemoryUnitOfWork
from ..adapters.seed_data import build_seed
from ..adapters.sqlalchemy.db import get_sessionmaker
from ..adapters.sqlalchemy.uow import SqlAlchemyUnitOfWork
from .settings import get_settings


@lru_cache
def _memory_uow() -> InMemoryUnitOfWork:
    seekers_data, hosts_data, listings_data = build_seed()
    seekers = InMemorySeekerRepo(seekers_data)
    hosts = InMemoryHostRepo(hosts_data)
    listings = InMemoryListingRepo(listings_data)
    swipes = InMemorySwipeRepo()
    matches = InMemoryMatchRepo()
    return InMemoryUnitOfWork(seekers, hosts, listings, swipes, matches)


def get_uow() -> Iterator[InMemoryUnitOfWork]:
    settings = get_settings()
    if settings.storage_backend == "sqlalchemy":
        database_url = settings.database_url
        if not database_url:
            raise RuntimeError("SM_DATABASE_URL is required for the SQL storage backend")
        session_factory = get_sessionmaker(database_url)
        session = session_factory()
        uow = SqlAlchemyUnitOfWork(session)
        try:
            yield uow
            uow.commit()
        except Exception:
            uow.rollback()
            raise
        finally:
            uow.close()
    else:
        yield _memory_uow()
