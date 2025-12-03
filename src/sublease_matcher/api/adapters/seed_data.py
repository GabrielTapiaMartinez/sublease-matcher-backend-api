from __future__ import annotations

from datetime import date
from decimal import Decimal

from ..interfaces.types import HostDict, ListingDict, SeekerDict


def build_seed() -> tuple[
    dict[str, SeekerDict],
    dict[str, HostDict],
    dict[str, ListingDict],
]:
    seekers: dict[str, SeekerDict] = {
        "seeker-1": {
            "id": "seeker-1",
            "user_id": "user-1",
            "bio": "Sophomore looking for quiet place",
            "budget_min": Decimal("400"),
            "budget_max": Decimal("700"),
            "city": "Eau Claire",
            "interests_csv": "coding,swimming,reading",
            "contact_email": "s1@example.edu",
            "available_from": date(2025, 8, 15),
            "available_to": date(2025, 12, 31),
        },
        "seeker-2": {
            "id": "seeker-2",
            "user_id": "user-2",
            "bio": "Exchange student",
            "budget_min": Decimal("500"),
            "budget_max": Decimal("800"),
            "city": "Eau Claire",
            "interests_csv": "hiking,cinema",
            "contact_email": "s2@example.edu",
            "available_from": date(2025, 1, 1),
            "available_to": date(2025, 5, 31),
        },
    }
    hosts: dict[str, HostDict] = {
        "host-1": {
            "id": "host-1",
            "user_id": "user-10",
            "bio": "2BR apartment close to campus",
            "house_rules": "no smoking",
            "contact_email": "h1@example.edu",
        }
    }
    listings: dict[str, ListingDict] = {
        "listing-1": {
            "id": "listing-1",
            "host_id": "host-1",
            "title": "Room near Water St",
            "price_per_month": Decimal("650"),
            "city": "Eau Claire",
            "state": "WI",
            "available_from": date(2025, 8, 15),
            "available_to": None,
            "status": "PUBLISHED",
        }
    }
    return seekers, hosts, listings
