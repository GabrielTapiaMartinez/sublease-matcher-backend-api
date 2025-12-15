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
            "name": "Jane Doe",
            "age": 20,
            "bio": "Sophomore looking for quiet place",
            "budget_min": Decimal("400"),
            "budget_max": Decimal("700"),
            "city": "Eau Claire",
            "interests_csv": "coding,swimming,reading",
            "contact_email": "s1@example.edu",
            "contact_phone": "555-0101",
            "available_from": date(2025, 8, 15),
            "available_to": date(2025, 12, 31),
        },
        "seeker-2": {
            "id": "seeker-2",
            "user_id": "user-2",
            "name": "John Smith",
            "age": 21,
            "bio": "Exchange student",
            "budget_min": Decimal("500"),
            "budget_max": Decimal("800"),
            "city": "Eau Claire",
            "interests_csv": "hiking,cinema",
            "contact_email": "s2@example.edu",
            "contact_phone": "555-0102",
            "available_from": date(2025, 1, 1),
            "available_to": date(2025, 5, 31),
        },
        "seeker-3": {
            "id": "seeker-3",
            "user_id": "user-3",
            "name": "Alice Walker",
            "age": 24,
            "bio": "Grad student, very quiet",
            "budget_min": Decimal("600"),
            "budget_max": Decimal("900"),
            "city": "Eau Claire",
            "interests_csv": "research,reading",
            "contact_email": "s3@example.edu",
            "contact_phone": "555-0103",
            "available_from": date(2025, 9, 1),
            "available_to": date(2026, 5, 31),
        },
    }
    listing_1 = {
        "id": "listing-1",
        "host_id": "host-1",
        "title": "Room near Water St",
        "price_per_month": Decimal("650"),
        "city": "Eau Claire",
        "state": "WI",
        "available_from": date(2025, 8, 15),
        "available_to": None,
        "status": "PUBLISHED",
        "photos": ["/House1.jpg"],
    }
    listing_2 = {
        "id": "listing-2",
        "host_id": "host-2",
        "title": "Luxury Downtown Loft",
        "price_per_month": Decimal("1200"),
        "city": "Eau Claire",
        "state": "WI",
        "available_from": date(2025, 9, 1),
        "available_to": None,
        "status": "PUBLISHED",
        "photos": ["/House1.jpg"],
    }
    listing_3 = {
        "id": "listing-3",
        "host_id": "host-3",
        "title": "Cozy Studio near Campus",
        "price_per_month": Decimal("500"),
        "city": "Eau Claire",
        "state": "WI",
        "available_from": date(2025, 8, 20),
        "available_to": None,
        "status": "PUBLISHED",
        "photos": ["/House1.jpg"],
    }
    listing_4 = {
        "id": "listing-4",
        "host_id": "host-4",
        "title": "Sunny Room with View",
        "price_per_month": Decimal("750"),
        "city": "Eau Claire",
        "state": "WI",
        "available_from": date(2025, 9, 1),
        "available_to": None,
        "status": "PUBLISHED",
        "photos": ["/House1.jpg"],
    }
    listing_5 = {
        "id": "listing-5",
        "host_id": "host-5",
        "title": "Modern Studio - All Inclusive",
        "price_per_month": Decimal("950"),
        "city": "Eau Claire",
        "state": "WI",
        "available_from": date(2025, 8, 1),
        "available_to": None,
        "status": "PUBLISHED",
        "photos": ["/House1.jpg"],
    }

    listings: dict[str, ListingDict] = {
        "listing-1": listing_1,
        "listing-2": listing_2,
        "listing-3": listing_3,
        "listing-4": listing_4,
        "listing-5": listing_5,
    }

    hosts: dict[str, HostDict] = {
        "host-1": {
            "id": "host-1",
            "user_id": "user-10",
            "bio": "2BR apartment close to campus",
            "house_rules": "no smoking",
            "contact_email": "h1@example.edu",
            "contact_phone": "555-0201",
        },
        "host-2": {
            "id": "host-2",
            "user_id": "user-11",
            "bio": "Modern living in downtown",
            "house_rules": "pets allowed",
            "contact_email": "h2@example.edu",
            "contact_phone": "555-0202",
        },
        "host-3": {
            "id": "host-3",
            "user_id": "user-12",
            "bio": "Quiet study atmosphere",
            "house_rules": "quiet hours 10pm",
            "contact_email": "h3@example.edu",
            "contact_phone": "555-0203",
        },
        "host-4": {
            "id": "host-4",
            "user_id": "user-13",
            "bio": "Friendly house",
            "house_rules": "no parties",
            "contact_email": "h4@example.edu",
            "contact_phone": "555-0204",
        },
        "host-5": {
            "id": "host-5",
            "user_id": "user-14",
            "bio": "Professional managed",
            "house_rules": "none",
            "contact_email": "h5@example.edu",
            "contact_phone": "555-0205",
        },
    }
    return seekers, hosts, listings
