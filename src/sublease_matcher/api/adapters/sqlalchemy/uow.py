from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session

from ..memory_uow import InMemoryUnitOfWork
from .repos import (
    SqlAlchemyHostRepo,
    SqlAlchemyListingRepo,
    SqlAlchemyMatchRepo,
    SqlAlchemySeekerRepo,
    SqlAlchemySwipeRepo,
)


class SqlAlchemyUnitOfWork(InMemoryUnitOfWork):
    """Unit of Work that wires SQLAlchemy-backed repositories."""

    def __init__(self, session: Session) -> None:
        self._session = session
        seekers = SqlAlchemySeekerRepo(session)
        hosts = SqlAlchemyHostRepo(session)
        listings = SqlAlchemyListingRepo(session)
        swipes = SqlAlchemySwipeRepo(session)
        matches = SqlAlchemyMatchRepo(session)
        super().__init__(seekers, hosts, listings, swipes, matches)

    def __enter__(self) -> Self:
        super().__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            super().__exit__(exc_type, exc, tb)
        finally:
            self.close()

    def _swipe_repo(self) -> SqlAlchemySwipeRepo:
        if not isinstance(self.swipes, SqlAlchemySwipeRepo):
            raise RuntimeError("Unexpected swipe repository type")
        return self.swipes

    def commit(self) -> None:
        swipe_repo = self._swipe_repo()
        swipe_repo.flush_pending()
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
        swipe_repo = self._swipe_repo()
        swipe_repo.reset_pending()

    def close(self) -> None:
        """Release the underlying session resources."""
        self._session.close()
