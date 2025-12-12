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
from ..dependencies.settings import get_settings
from ..interfaces.uow import UnitOfWork


@lru_cache
def _build_memory_uow() -> InMemoryUnitOfWork:
    seekers_data, hosts_data, listings_data = build_seed()
    seekers = InMemorySeekerRepo(seekers_data)
    hosts = InMemoryHostRepo(hosts_data)
    listings = InMemoryListingRepo(listings_data)
    swipes = InMemorySwipeRepo()
    matches = InMemoryMatchRepo()
    return InMemoryUnitOfWork(seekers, hosts, listings, swipes, matches)


def get_uow() -> Iterator[UnitOfWork]:
    settings = get_settings()
    if settings.storage == "sqlalchemy":
        from ..adapters.sqlalchemy.db import SessionLocal
        from ..adapters.sqlalchemy.uow import SqlAlchemyUnitOfWork

        with SqlAlchemyUnitOfWork(SessionLocal) as uow:
            yield uow
    else:
        yield _build_memory_uow()
