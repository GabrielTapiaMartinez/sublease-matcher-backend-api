from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import Protocol

from .types import HostDict, ListingDict, MatchDict, SeekerDict, SwipeDict


class SeekerRepo(Protocol):
    def get(self, seeker_id: str) -> SeekerDict | None: ...

    def get_by_user(self, user_id: str) -> SeekerDict | None: ...

    def upsert(self, seeker: SeekerDict) -> SeekerDict: ...

    def queue_for_host(self, host_id: str) -> Sequence[SeekerDict]: ...


class HostRepo(Protocol):
    def get(self, host_id: str) -> HostDict | None: ...

    def get_by_user(self, user_id: str) -> HostDict | None: ...

    def upsert(self, host: HostDict) -> HostDict: ...


class ListingRepo(Protocol):
    def get(self, listing_id: str) -> ListingDict | None: ...

    def get_by_host(self, host_id: str) -> ListingDict | None: ...

    def upsert(self, listing: ListingDict) -> ListingDict: ...

    def search(
        self,
        city: str | None = None,
        max_price: Decimal | None = None,
    ) -> Sequence[ListingDict]: ...

    def queue_for_seeker(self, seeker_id: str) -> Sequence[ListingDict]: ...


class SwipeRepo(Protocol):
    def record_swipe(self, swiper_id: str, target_id: str, decision: str) -> SwipeDict: ...

    def undo_last(self, user_id: str) -> SwipeDict | None: ...


class MatchRepo(Protocol):
    def list_for_seeker(self, seeker_id: str) -> Sequence[MatchDict]: ...

    def list_for_host(self, host_id: str) -> Sequence[MatchDict]: ...

    def upsert(
        self,
        seeker_id: str,
        listing_id: str,
        status: str,
        score: float | None,
    ) -> MatchDict: ...


class UserProtocol(Protocol):
    id: str
    email: str
    first_name: str | None
    last_name: str | None
    current_role: str | None
    show_in_swipe: bool
    email_notifications_enabled: bool
    password_hash: str | None


class UserRepo(Protocol):
    def get(self, user_id: str) -> UserProtocol | None: ...
    def get_by_email(self, email: str) -> UserProtocol | None: ...
    def create(self, user_id: str, email: str, password_hash: str, **kwargs) -> UserProtocol: ...
    def ensure_user(self, user_id: str, *, role: str | None = None) -> UserProtocol: ...


class SessionProtocol(Protocol):
    id: str  # The token
    user_id: str
    expires_at: datetime | None


class SessionRepo(Protocol):
    def create(self, user_id: str) -> str: ...
    def get(self, token: str) -> SessionProtocol | None: ...
    def delete(self, token: str) -> None: ...
