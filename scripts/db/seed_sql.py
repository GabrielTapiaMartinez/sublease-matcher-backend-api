#!/usr/bin/env python3
"""[db-seed] Reset and seed the SQL dev database with deterministic demo data."""
# ruff: noqa: E402

from __future__ import annotations

import os
from datetime import UTC, date, datetime
from decimal import Decimal
from getpass import getuser
from typing import Any, Final

import sqlalchemy as sa
from sqlalchemy.orm import Session

DEFAULT_DB_NAME = "sublease_dev_sql"


def _default_database_url() -> str:
    user = os.environ.get("USER") or getuser()
    return f"postgresql+psycopg://{user}@localhost:5432/{DEFAULT_DB_NAME}"


def _ensure_database_url() -> str:
    database_url = os.environ.get("SM_DATABASE_URL")
    if not database_url:
        database_url = _default_database_url()
        os.environ["SM_DATABASE_URL"] = database_url
    return database_url


_ensure_database_url()

from sublease_matcher.api.adapters.sqlalchemy import models  # noqa: E402
from sublease_matcher.api.adapters.sqlalchemy.db import SessionLocal
from sublease_matcher.api.adapters.sqlalchemy.uow import SqlAlchemyUnitOfWork

TRUNCATE_TABLES: Final[tuple[str, ...]] = (
    "matches",
    "seeker_swipes",
    "host_swipes",
    "listing_roommates",
    "listing_photos",
    "seeker_photos",
    "listings",
    "host_profiles",
    "seeker_profiles",
    "users",
)


def _log(message: str) -> None:
    print(f"[db-seed] {message}")


def _truncate_tables(session: Session) -> None:
    _log("Truncating dev tables (local use only)...")
    statement = sa.text(
        "TRUNCATE TABLE " + ", ".join(TRUNCATE_TABLES) + " RESTART IDENTITY CASCADE"
    )
    session.execute(statement)


def _seed_users(uow: SqlAlchemyUnitOfWork) -> None:
    _log("Loading users...")
    user_rows: list[dict[str, Any]] = [
        {
            "id": "user-1",
            "email": "jamie.rivera@example.edu",
            "first_name": "Jamie",
            "last_name": "Rivera",
            "role": "SEEKER",
        },
        {
            "id": "user-2",
            "email": "parker.lee@example.edu",
            "first_name": "Parker",
            "last_name": "Lee",
            "role": "SEEKER",
        },
        {
            "id": "user-10",
            "email": "casey.nguyen@example.edu",
            "first_name": "Casey",
            "last_name": "Nguyen",
            "role": "HOST",
        },
    ]
    for row in user_rows:
        role_value = row.get("role")
        user = uow.users.ensure_user(str(row["id"]), role=str(role_value) if role_value else None)
        user.email = str(row["email"])
        user.first_name = row.get("first_name")
        user.last_name = row.get("last_name")


def _seed_seekers(uow: SqlAlchemyUnitOfWork) -> None:
    _log("Loading seekers, photos, and needs...")
    seeker_rows: list[dict[str, Any]] = [
        {
            "profile": {
                "id": "seeker-1",
                "user_id": "user-9",
                "bio": "Sophomore looking for quiet place",
                "term": "Fall",
                "term_year": 2025,
                "budget_min": Decimal("400"),
                "budget_max": Decimal("700"),
                "city": "Eau Claire",
                "interests_csv": "coding,swimming,reading",
                "contact_email": "s1@example.edu",
                "hidden": False,
            },
            "need_from": date(2025, 8, 1),
            "need_to": date(2025, 12, 31),
            "photos": [
                {
                    "id": "seeker-photo-1",
                    "position": 1,
                    "url": "/static/mock/seekers/seeker-1-1.jpg",
                },
                {
                    "id": "seeker-photo-2",
                    "position": 2,
                    "url": "/static/mock/seekers/seeker-1-2.jpg",
                },
            ],
        },
        {
            "profile": {
                "id": "seeker-2",
                "user_id": "user-2",
                "bio": "Exchange student hunting for spring housing",
                "term": "Spring",
                "term_year": 2026,
                "budget_min": Decimal("500"),
                "budget_max": Decimal("800"),
                "city": "Eau Claire",
                "interests_csv": "hiking,cinema",
                "contact_email": "s2@example.edu",
                "hidden": False,
            },
            "need_from": date(2026, 1, 5),
            "need_to": date(2026, 5, 20),
            "photos": [
                {
                    "id": "seeker-photo-3",
                    "position": 1,
                    "url": "/static/mock/seekers/seeker-2-1.jpg",
                }
            ],
        },
    ]
    for row in seeker_rows:
        payload = dict(row["profile"])
        record = uow.seekers.upsert(payload)
        seeker_id = record["id"]
        seeker_model = uow.session.get(models.SeekerProfile, seeker_id)
        if seeker_model:
            seeker_model.need_from = row["need_from"]
            seeker_model.need_to = row["need_to"]
            seeker_model.visible = True
        for photo in row["photos"]:
            uow.session.add(
                models.SeekerPhoto(
                    id=photo["id"],
                    seeker_id=seeker_id,
                    position=photo["position"],
                    url=photo["url"],
                )
            )


def _seed_hosts_and_listings(uow: SqlAlchemyUnitOfWork) -> None:
    _log("Loading hosts, listings, photos, and roommates...")
    host_rows: list[dict[str, Any]] = [
        {
            "id": "host-1",
            "user_id": "user-10",
            "bio": "2BR apartment close to campus",
            "house_rules": "No smoking after 10pm",
            "contact_email": "h1@example.edu",
        }
    ]
    for host in host_rows:
        uow.hosts.upsert(dict(host))

    listing_rows: list[dict[str, Any]] = [
        {
            "data": {
                "id": "listing-1",
                "host_id": "host-1",
                "title": "Room near Water St",
                "price_per_month": Decimal("650"),
                "city": "Eau Claire",
                "state": "WI",
                "available_from": date(2025, 8, 15),
                "available_to": date(2026, 5, 31),
                "status": "PUBLISHED",
                "roommates": [
                    {
                        "id": "roommate-1",
                        "name": "Alex",
                        "pronouns": "they/them",
                        "sleepingHabits": "early sleeper",
                        "studyHabits": "library focused",
                        "cleanliness": "tidy",
                        "interests": ["cooking", "hiking"],
                        "bio": "Graduate assistant who enjoys morning runs.",
                        "photo_url": "/static/mock/roommates/roommate-1.jpg",
                    }
                ],
            },
            "photos": [
                {
                    "id": "listing-photo-1",
                    "position": 1,
                    "url": "/static/mock/listings/listing-1-1.jpg",
                }
            ],
        }
    ]

    for listing in listing_rows:
        payload = dict(listing["data"])
        record = uow.listings.upsert(payload)
        listing_id = record["id"]
        for photo in listing["photos"]:
            uow.session.add(
                models.ListingPhoto(
                    id=photo["id"],
                    listing_id=listing_id,
                    position=photo["position"],
                    url=photo["url"],
                )
            )


def _seed_swipes_and_matches(uow: SqlAlchemyUnitOfWork) -> None:
    _log("Loading swipes and matches...")
    swipe_timestamp = datetime(2025, 7, 1, 12, 0, tzinfo=UTC)
    uow.session.add_all(
        [
            models.SeekerSwipe(
                id="seeker-swipe-1",
                seeker_id="seeker-1",
                listing_id="listing-1",
                decision="LIKE",
                created_at=swipe_timestamp,
            ),
            models.HostSwipe(
                id="host-swipe-1",
                host_id="host-1",
                seeker_id="seeker-1",
                decision="LIKE",
                created_at=swipe_timestamp,
            ),
        ]
    )
    uow.matches.upsert(
        seeker_id="seeker-1",
        listing_id="listing-1",
        status="MUTUAL",
        score=0.95,
    )
    match_id = "seeker-1:listing-1"
    match = uow.session.get(models.Match, match_id)
    if match:
        match.matched_at = swipe_timestamp


def main() -> None:
    _log("Resetting SQL dev database...")
    database_url = os.environ.get("SM_DATABASE_URL")
    if database_url:
        _log(f"Using database URL: {database_url}")
    with SqlAlchemyUnitOfWork(SessionLocal) as uow:
        _truncate_tables(uow.session)
        _seed_users(uow)
        _seed_seekers(uow)
        _seed_hosts_and_listings(uow)
        _seed_swipes_and_matches(uow)
    _log("Done.")


if __name__ == "__main__":
    main()
