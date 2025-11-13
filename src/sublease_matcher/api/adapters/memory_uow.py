from __future__ import annotations

from types import TracebackType
from typing import Self

from ..interfaces.uow import UnitOfWork
from .memory_repos import (
    InMemoryHostRepo,
    InMemoryListingRepo,
    InMemoryMatchRepo,
    InMemorySeekerRepo,
    InMemorySwipeRepo,
)


class InMemoryUnitOfWork(UnitOfWork):
    def __init__(
        self,
        seekers: InMemorySeekerRepo,
        hosts: InMemoryHostRepo,
        listings: InMemoryListingRepo,
        swipes: InMemorySwipeRepo,
        matches: InMemoryMatchRepo,
    ) -> None:
        self.seekers = seekers
        self.hosts = hosts
        self.listings = listings
        self.swipes = swipes
        self.matches = matches
        self._committed = False

    def __enter__(self) -> Self:
        self._committed = False
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()

    def commit(self) -> None:
        self._committed = True

    def rollback(self) -> None:
        self._committed = False
