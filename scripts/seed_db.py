from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from sublease_matcher.api.adapters.sqlalchemy.db import configure_engine
from sublease_matcher.api.adapters.sqlalchemy.models import (
    HostProfile,
    Listing,
    ListingPhoto,
    ListingRoommate,
    SeekerProfile,
    User,
)
from sublease_matcher.api.config import Settings


def _upsert_user(session: Session, *, user_id: str, email: str, role: str) -> User:
    user = session.get(User, user_id)
    if user is None:
        user = User(
            id=user_id,
            email=email,
            first_name=None,
            last_name=None,
            current_role=role,
            email_notifications_enabled=True,
            show_in_swipe=True,
        )
        session.add(user)
    else:
        user.email = email
        user.current_role = role
    return user


def _upsert_seeker_profile(session: Session, *, user_id: str) -> SeekerProfile:
    seeker = session.get(SeekerProfile, "seeker-1")
    if seeker is None:
        seeker = SeekerProfile(
            id="seeker-1",
            user_id=user_id,
            visible=True,
        )
        session.add(seeker)
    seeker.bio = "Sophomore looking for quiet place"
    seeker.term = "Fall"
    seeker.term_year = 2025
    seeker.budget_min = Decimal("400")
    seeker.budget_max = Decimal("700")
    seeker.city = "Eau Claire"
    seeker.interests_csv = "coding,swimming,reading"
    seeker.contact_email = "s1@example.edu"
    return seeker


def _upsert_host_profile(session: Session, *, user_id: str) -> HostProfile:
    host = session.get(HostProfile, "host-1")
    if host is None:
        host = HostProfile(
            id="host-1",
            user_id=user_id,
            visible=True,
        )
        session.add(host)
    host.bio = "2BR apartment close to campus"
    host.house_rules = "no smoking"
    host.contact_email = "h1@example.edu"
    return host


def _upsert_listing(session: Session, *, host_id: str) -> Listing:
    listing = session.get(Listing, "listing-1")
    if listing is None:
        listing = Listing(
            id="listing-1",
            host_id=host_id,
            status="PUBLISHED",
        )
        session.add(listing)
    listing.title = "Room near Water St"
    listing.price_per_month = Decimal("650")
    listing.city = "Eau Claire"
    listing.state = "WI"
    listing.available_from = date(2025, 8, 15)
    listing.available_to = None
    listing.status = "PUBLISHED"
    return listing


def _upsert_roommate(session: Session, *, listing_id: str) -> ListingRoommate:
    roommate = session.get(ListingRoommate, "roommate-1")
    if roommate is None:
        roommate = ListingRoommate(id="roommate-1", listing_id=listing_id)
        session.add(roommate)
    roommate.name = "Alex"
    roommate.pronouns = "they/them"
    roommate.sleeping_habits = "early sleeper"
    roommate.study_habits = "library focused"
    roommate.cleanliness = "tidy"
    roommate.interests_csv = "cooking,hiking"
    roommate.bio = "Graduate assistant who enjoys morning runs."
    return roommate


def _upsert_photo(session: Session, *, listing_id: str) -> ListingPhoto:
    photo = session.get(ListingPhoto, "listing-photo-1")
    if photo is None:
        photo = ListingPhoto(
            id="listing-photo-1",
            listing_id=listing_id,
            position=0,
            url="https://example.com/listing-1/photo.jpg",
        )
        session.add(photo)
    else:
        photo.listing_id = listing_id
        photo.url = "https://example.com/listing-1/photo.jpg"
        photo.position = 0
    return photo


def seed() -> None:
    settings = Settings()
    if not settings.database_url:
        raise SystemExit("SM_DATABASE_URL must be set to run the seed script")

    engine, session_factory = configure_engine(settings.database_url)
    # Schema must already exist (run Alembic migrations first); no create_all() here.
    session = session_factory()
    try:
        _upsert_user(session, user_id="user-1", email="s1@example.edu", role="SEEKER")
        _upsert_user(session, user_id="user-10", email="h1@example.edu", role="HOST")

        seeker = _upsert_seeker_profile(session, user_id="user-1")
        host = _upsert_host_profile(session, user_id="user-10")
        listing = _upsert_listing(session, host_id=host.id)
        _upsert_roommate(session, listing_id=listing.id)
        _upsert_photo(session, listing_id=listing.id)

        session.commit()
        print(
            f"Seed complete: seekers={seeker.id}, hosts={host.id}, listing={listing.id}",  # noqa: T201
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed()
