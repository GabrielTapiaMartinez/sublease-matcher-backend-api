"""Infrastructure adapters live here."""

from .match_engine_simple import SimpleMatchEngine
from .memory_repos import (
    InMemoryHostRepo,
    InMemoryListingRepo,
    InMemoryMatchRepo,
    InMemorySeekerRepo,
    InMemorySwipeRepo,
)
from .memory_uow import InMemoryUnitOfWork
from .sqlalchemy.uow import SqlAlchemyUnitOfWork

__all__ = [
    "InMemoryHostRepo",
    "InMemoryListingRepo",
    "InMemoryMatchRepo",
    "InMemorySeekerRepo",
    "InMemorySwipeRepo",
    "InMemoryUnitOfWork",
    "SqlAlchemyUnitOfWork",
    "SimpleMatchEngine",
]
