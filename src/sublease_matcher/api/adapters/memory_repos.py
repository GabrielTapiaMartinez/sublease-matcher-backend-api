from __future__ import annotations

import secrets
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from ..interfaces.repos import (
    HostRepo,
    ListingRepo,
    MatchRepo,
    SeekerRepo,
    SessionProtocol,
    SessionRepo,
    SwipeRepo,
    UserProtocol,
    UserRepo,
)
from ..interfaces.types import HostDict, ListingDict, MatchDict, SeekerDict, SwipeDict


@dataclass
class InMemoryUser:
    id: str
    email: str
    password_hash: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    current_role: str | None = None
    show_in_swipe: bool = True
    email_notifications_enabled: bool = True


class InMemoryUserRepo(UserRepo):
    def __init__(self, data: dict[str, InMemoryUser] | None = None) -> None:
        self._data: dict[str, InMemoryUser] = data or {}

    def get(self, user_id: str) -> UserProtocol | None:
        return self._data.get(user_id)

    def get_by_email(self, email: str) -> UserProtocol | None:
        for user in self._data.values():
            if user.email == email:
                return user
        return None

    def create(self, user_id: str, email: str, password_hash: str, **kwargs) -> UserProtocol:
        user = InMemoryUser(
            id=user_id,
            email=email,
            password_hash=password_hash,
            first_name=kwargs.get("first_name"),
            last_name=kwargs.get("last_name"),
            current_role=kwargs.get("role"), # Map role arg to current_role
        )
        self._data[user_id] = user
        return user

    def ensure_user(self, user_id: str, *, role: str | None = None) -> UserProtocol:
        user = self._data.get(user_id)
        if user is None:
            user = InMemoryUser(id=user_id, email=f"{user_id}@example.edu")
            self._data[user_id] = user
        if role:
            user.current_role = role.upper()
        return user


@dataclass
class InMemorySession:
    id: str
    user_id: str
    expires_at: datetime | None


class InMemorySessionRepo(SessionRepo):
    def __init__(self, data: dict[str, InMemorySession] | None = None) -> None:
        self._data: dict[str, InMemorySession] = data or {}

    def create(self, user_id: str) -> str:
        token = secrets.token_hex(32)
        session = InMemorySession(
            id=token,
            user_id=user_id,
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        self._data[token] = session
        return token

    def get(self, token: str) -> SessionProtocol | None:
        return self._data.get(token)

    def delete(self, token: str) -> None:
        self._data.pop(token, None)


class InMemorySeekerRepo(SeekerRepo):
    def __init__(self, data: dict[str, SeekerDict] | None = None) -> None:
        self._data: dict[str, SeekerDict] = data or {}

    def get(self, seeker_id: str) -> SeekerDict | None:
        return self._data.get(seeker_id)

    def get_by_user(self, user_id: str) -> SeekerDict | None:
        for seeker in self._data.values():
            if seeker.get("user_id") == user_id:
                return seeker
        return None

    def upsert(self, seeker: SeekerDict) -> SeekerDict:
        seeker_id = seeker.get("id") or str(uuid4())
        seeker["id"] = seeker_id
        self._data[seeker_id] = seeker
        return seeker

    def queue_for_host(self, host_id: str) -> Sequence[SeekerDict]:
        return [seeker for seeker in self._data.values() if not seeker.get("hidden")]


class InMemoryHostRepo(HostRepo):
    def __init__(self, data: dict[str, HostDict] | None = None) -> None:
        self._data: dict[str, HostDict] = data or {}

    def get(self, host_id: str) -> HostDict | None:
        return self._data.get(host_id)

    def get_by_user(self, user_id: str) -> HostDict | None:
        for host in self._data.values():
            if host.get("user_id") == user_id:
                return host
        return None

    def upsert(self, host: HostDict) -> HostDict:
        host_id = host.get("id") or str(uuid4())
        host["id"] = host_id
        self._data[host_id] = host
        return host


class InMemoryListingRepo(ListingRepo):
    def __init__(self, data: dict[str, ListingDict] | None = None) -> None:
        self._data: dict[str, ListingDict] = data or {}

    def get(self, listing_id: str) -> ListingDict | None:
        return self._data.get(listing_id)

    def get_by_host(self, host_id: str) -> ListingDict | None:
        for listing in self._data.values():
            if listing.get("host_id") == host_id:
                return listing
        return None

    def upsert(self, listing: ListingDict) -> ListingDict:
        listing_id = listing.get("id") or str(uuid4())
        listing["id"] = listing_id
        self._data[listing_id] = listing
        return listing

    def search(
        self,
        city: str | None = None,
        max_price: Decimal | None = None,
    ) -> Sequence[ListingDict]:
        results: list[ListingDict] = list(self._data.values())
        if city:
            results = [listing for listing in results if listing.get("city") == city]
        if max_price is not None:
            filtered: list[ListingDict] = []
            for listing in results:
                price = listing.get("price_per_month")
                if price is not None and price <= max_price:
                    filtered.append(listing)
            results = filtered
        return results

    def queue_for_seeker(self, seeker_id: str) -> Sequence[ListingDict]:
        return [listing for listing in self._data.values() if listing.get("status") == "PUBLISHED"]


class InMemorySwipeRepo(SwipeRepo):
    def __init__(
        self,
        data: dict[str, SwipeDict] | None = None,
        by_user_stack: dict[str, list[SwipeDict]] | None = None,
    ) -> None:
        self._data: dict[str, SwipeDict] = data or {}
        self._by_user_stack: dict[str, list[SwipeDict]] = by_user_stack or {}

    def record_swipe(self, swiper_id: str, target_id: str, decision: str) -> SwipeDict:
        swipe: SwipeDict = {
            "id": str(uuid4()),
            "user_id": swiper_id,
            "target_id": target_id,
            "decision": "like" if decision == "like" else "pass",
            "created_at": datetime.utcnow(),
        }
        self._data[swipe["id"]] = swipe
        self._by_user_stack.setdefault(swiper_id, []).append(swipe)
        return swipe

    def undo_last(self, user_id: str) -> SwipeDict | None:
        history = self._by_user_stack.get(user_id) or []
        if not history:
            return None
        last_swipe = history.pop()
        self._data.pop(last_swipe["id"], None)
        return last_swipe


class InMemoryMatchRepo(MatchRepo):
    def __init__(self, data: dict[str, MatchDict] | None = None) -> None:
        self._data: dict[str, MatchDict] = data or {}

    def list_for_seeker(self, seeker_id: str) -> Sequence[MatchDict]:
        return [match for match in self._data.values() if match.get("seeker_id") == seeker_id]

    def list_for_host(self, host_id: str) -> Sequence[MatchDict]:
        return list(self._data.values())

    def upsert(
        self,
        seeker_id: str,
        listing_id: str,
        status: str,
        score: float | None,
    ) -> MatchDict:
        key = f"{seeker_id}:{listing_id}"
        if status == "PENDING":
            status_literal: Literal["PENDING", "MUTUAL"] = "PENDING"
        elif status == "MUTUAL":
            status_literal = "MUTUAL"
        else:
            raise ValueError(f"Unsupported match status: {status}")
        existing = next(
            (
                match
                for match in self._data.values()
                if match.get("seeker_id") == seeker_id and match.get("listing_id") == listing_id
            ),
            None,
        )
        if existing:
            existing["status"] = status_literal
            existing["score"] = score
            return existing
        new_match: MatchDict = {
            "id": key,
            "seeker_id": seeker_id,
            "listing_id": listing_id,
            "status": status_literal,
            "score": score,
            "matched_at": None,
        }
        self._data[key] = new_match
        return new_match
