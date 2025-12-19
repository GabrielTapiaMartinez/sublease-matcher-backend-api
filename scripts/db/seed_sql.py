#!/usr/bin/env python3
"""[db-seed] Reset and seed the SQL dev database with deterministic demo data."""
# ruff: noqa: E402

from __future__ import annotations

import os
import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from getpass import getuser
from typing import Any, Final

import sqlalchemy as sa
from sqlalchemy.orm import Session

DEFAULT_DB_NAME = "sublease_dev_sql"
DEFAULT_PYTHONPATH = "src:../sublease-matcher-backend-core/src"


def _default_database_url() -> str:
    user = os.environ.get("USER") or getuser()
    return f"postgresql+psycopg://{user}@localhost:5432/{DEFAULT_DB_NAME}"


def _ensure_database_url() -> str:
    database_url = os.environ.get("SM_DATABASE_URL")
    if not database_url:
        database_url = _default_database_url()
        os.environ["SM_DATABASE_URL"] = database_url
    return database_url


def _ensure_pythonpath() -> None:
    pythonpath = os.environ.get("PYTHONPATH")
    if pythonpath:
        return
    os.environ["PYTHONPATH"] = DEFAULT_PYTHONPATH
    for path in DEFAULT_PYTHONPATH.split(":"):
        if path and path not in sys.path:
            sys.path.insert(0, path)


_ensure_pythonpath()
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
    user_rows: list[dict[str, Any]] = []
    for row in user_rows:
        role_value = row.get("role")
        user = uow.users.ensure_user(str(row["id"]), role=str(role_value) if role_value else None)
        user.email = str(row["email"])
        user.first_name = row.get("first_name")
        user.last_name = row.get("last_name")


def _seed_seekers(uow: SqlAlchemyUnitOfWork) -> None:
    _log("Loading seekers, photos, and needs...")
    seeker_rows: list[dict[str, Any]] = []
    for row in seeker_rows:
        payload = dict(row["profile"])
        record = uow.seekers.upsert(payload)
        seeker_id = record["id"]
        # Manually add photos since upsert logic might be simple or specific
        uow.session.flush()
        seeker_model = uow.session.get(models.SeekerProfile, seeker_id)
        if seeker_model:
            seeker_model.visible = True
            
        # Clear existing photos to avoid dupes if re-seeding without truncate
        # (Though we truncate tables above)
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
    host_rows: list[dict[str, Any]] = []
    for host in host_rows:
        uow.hosts.upsert(dict(host))

    listing_rows: list[dict[str, Any]] = []

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
    # Create a mutual match between seeker-1 and listing-1
    # uow.matches.upsert(
    #    seeker_id="seeker-1",
    #    listing_id="listing-1",
    #    status="MUTUAL",
    #    score=0.95,
    # )


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
