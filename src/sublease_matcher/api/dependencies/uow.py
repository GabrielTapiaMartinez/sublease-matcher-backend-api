from __future__ import annotations

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


@lru_cache
def get_uow() -> InMemoryUnitOfWork:
    seekers_data, hosts_data, listings_data = build_seed()
    seekers = InMemorySeekerRepo(seekers_data)
    hosts = InMemoryHostRepo(hosts_data)
    listings = InMemoryListingRepo(listings_data)
    swipes = InMemorySwipeRepo()
    matches = InMemoryMatchRepo()
    return InMemoryUnitOfWork(seekers, hosts, listings, swipes, matches)
