from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, TypedDict


class SeekerDict(TypedDict, total=False):
    id: str
    user_id: str
    bio: str | None
    term: str | None
    term_year: int | None
    budget_min: Decimal | None
    budget_max: Decimal | None
    city: str | None
    interests_csv: str | None
    contact_email: str | None
    hidden: bool


class HostDict(TypedDict, total=False):
    id: str
    user_id: str
    bio: str
    house_rules: str
    contact_email: str


class ListingDict(TypedDict, total=False):
    id: str
    host_id: str
    title: str
    price_per_month: Decimal | None
    city: str
    state: str
    available_from: date
    available_to: date | None
    status: Literal["DRAFT", "PUBLISHED", "UNLISTED"]


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
