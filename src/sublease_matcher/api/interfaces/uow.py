from __future__ import annotations

from typing import Protocol, Self

from .repos import HostRepo, ListingRepo, MatchRepo, SeekerRepo, SwipeRepo


class UnitOfWork(Protocol):
    seekers: SeekerRepo
    hosts: HostRepo
    listings: ListingRepo
    swipes: SwipeRepo
    matches: MatchRepo

    def __enter__(self) -> Self: ...

    def __exit__(self, exc_type, exc, tb) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
