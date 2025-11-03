"""Infrastructure adapters live here."""

from .memory_repos import (
    InMemoryHostRepo,
    InMemoryListingRepo,
    InMemoryMatchRepo,
    InMemorySeekerRepo,
    InMemorySwipeRepo,
)
from .memory_uow import InMemoryUnitOfWork
from .match_engine_simple import SimpleMatchEngine

__all__ = [
    "InMemoryHostRepo",
    "InMemoryListingRepo",
    "InMemoryMatchRepo",
    "InMemorySeekerRepo",
    "InMemorySwipeRepo",
    "InMemoryUnitOfWork",
    "SimpleMatchEngine",
]
