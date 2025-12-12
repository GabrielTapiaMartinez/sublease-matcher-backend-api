from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

from .repos import HostRepo, ListingRepo, MatchRepo, SeekerRepo, SessionRepo, SwipeRepo, UserRepo


class UnitOfWork(Protocol):
    seekers: SeekerRepo
    hosts: HostRepo
    listings: ListingRepo
    swipes: SwipeRepo
    listings: ListingRepo
    swipes: SwipeRepo
    matches: MatchRepo
    users: UserRepo
    sessions: SessionRepo

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
