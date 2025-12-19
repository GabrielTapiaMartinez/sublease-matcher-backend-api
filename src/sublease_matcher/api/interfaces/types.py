from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, TypedDict


class SeekerDict(TypedDict, total=False):
    id: str
    user_id: str
    bio: str | None
    available_from: date | None
    available_to: date | None
    budget_min: Decimal | None
    budget_max: Decimal | None
    city: str | None
    interests_csv: str | None
    contact_email: str | None
    hidden: bool


class HostDict(TypedDict, total=False):
    id: str
    user_id: str
    bio: str | None
    house_rules: str | None
    contact_email: str | None


class ListingDict(TypedDict, total=False):
    id: str
    host_id: str
    title: str | None
    price_per_month: Decimal | None
    city: str | None
    state: str | None
    available_from: date | None
    available_to: date | None
    status: Literal["DRAFT", "PUBLISHED", "UNLISTED"]
    bio: str | None
    roommates: list[dict[str, Any]]


class SwipeDict(TypedDict):
    id: str
    user_id: str
    target_id: str
    decision: Literal["like", "pass"]
    created_at: datetime


class MatchDict(TypedDict, total=False):
    id: str
    seeker_id: str
    listing_id: str
    status: Literal["PENDING", "MUTUAL"]
    score: float | None
    matched_at: datetime | None
