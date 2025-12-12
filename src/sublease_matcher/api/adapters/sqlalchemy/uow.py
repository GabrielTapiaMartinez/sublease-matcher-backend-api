from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session, sessionmaker

from ...interfaces.uow import UnitOfWork
from .repos import (
    SqlAlchemyHostRepo,
    SqlAlchemyListingRepo,
    SqlAlchemyMatchRepo,
    SqlAlchemySeekerRepo,
    SqlAlchemySwipeRepo,
    SqlAlchemyUserRepo,
)


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self.session = self._session_factory()
        self.users = SqlAlchemyUserRepo(self.session)
        self.seekers = SqlAlchemySeekerRepo(self.session, self.users)
        self.hosts = SqlAlchemyHostRepo(self.session, self.users)
        self.listings = SqlAlchemyListingRepo(self.session)
        self.swipes = SqlAlchemySwipeRepo(self.session)
        self.matches = SqlAlchemyMatchRepo(self.session)

    def __enter__(self) -> Self:
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
            try:
                self.commit()
            except Exception:
                self.rollback()
                raise
        self.close()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def close(self) -> None:
        self.session.close()
