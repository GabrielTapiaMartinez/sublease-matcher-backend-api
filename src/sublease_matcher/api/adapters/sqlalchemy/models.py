from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ENUM as PGEnum


class Base(DeclarativeBase):
    """Declarative base for all ORM mappings."""


decision_t = PGEnum("LIKE", "PASS", name="decision_t", create_type=False)
listing_status_t = PGEnum("DRAFT", "PUBLISHED", "UNLISTED", name="listing_status_t", create_type=False)
match_status_t = PGEnum("PENDING", "MUTUAL", name="match_status_t", create_type=False)
role_t = PGEnum("SEEKER", "HOST", name="role_t", create_type=False)
term_t = PGEnum("Fall", "Spring", "Summer", name="term_t", create_type=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    current_role: Mapped[str | None] = mapped_column(role_t, nullable=True)
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_in_swipe: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    seeker_profile: Mapped[SeekerProfile] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    host_profile: Mapped[HostProfile] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )

class SeekerProfile(Base):
    __tablename__ = "seeker_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    bio: Mapped[str | None] = mapped_column(Text)
    term: Mapped[str | None] = mapped_column(term_t, nullable=True)
    term_year: Mapped[int | None] = mapped_column(Integer)
    budget_min: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    budget_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    city: Mapped[str | None] = mapped_column(String(120))
    interests_csv: Mapped[str | None] = mapped_column(Text)
    contact_email: Mapped[str | None] = mapped_column(String(255))

    user: Mapped[User] = relationship(back_populates="seeker_profile")
    photos: Mapped[list[SeekerPhoto]] = relationship(
        back_populates="seeker",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("user_id", name="seeker_profiles_user_id_key"),
    )


class SeekerPhoto(Base):
    __tablename__ = "seeker_photos"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    seeker_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("seeker_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)

    seeker: Mapped[SeekerProfile] = relationship(back_populates="photos")


class HostProfile(Base):
    __tablename__ = "host_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    bio: Mapped[str | None] = mapped_column(Text)
    house_rules: Mapped[str | None] = mapped_column(Text)
    contact_email: Mapped[str | None] = mapped_column(String(255))

    user: Mapped[User] = relationship(back_populates="host_profile")
    listing: Mapped[Listing] = relationship(
        back_populates="host",
        cascade="all, delete-orphan",
        uselist=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", name="host_profiles_user_id_key"),
    )


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    host_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("host_profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    title: Mapped[str | None] = mapped_column(String(255))
    price_per_month: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    city: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(2))
    available_from: Mapped[date | None] = mapped_column(Date)
    available_to: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(listing_status_t, default="DRAFT", nullable=False)

    host: Mapped[HostProfile] = relationship(back_populates="listing")
    photos: Mapped[list[ListingPhoto]] = relationship(
        back_populates="listing",
        cascade="all, delete-orphan",
    )
    roommates: Mapped[list[ListingRoommate]] = relationship(
        back_populates="listing",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("price_per_month >= 0", name="listings_price_non_negative"),
        CheckConstraint(
            "available_to IS NULL OR available_to >= available_from",
            name="listings_available_dates_check",
        ),
    )


class ListingPhoto(Base):
    __tablename__ = "listing_photos"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    listing_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)

    listing: Mapped[Listing] = relationship(back_populates="photos")


class ListingRoommate(Base):
    __tablename__ = "listing_roommates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    listing_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(String(120))
    sleeping_habits: Mapped[str | None] = mapped_column(String(120))
    interests_csv: Mapped[str | None] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(Text)
    pronouns: Mapped[str | None] = mapped_column(String(60))
    gender: Mapped[str | None] = mapped_column(String(60))
    study_habits: Mapped[str | None] = mapped_column(String(120))
    cleanliness: Mapped[str | None] = mapped_column(String(120))
    bio: Mapped[str | None] = mapped_column(Text)

    listing: Mapped[Listing] = relationship(back_populates="roommates")


class SeekerSwipe(Base):
    __tablename__ = "seeker_swipes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    seeker_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("seeker_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    listing_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(decision_t, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("seeker_id", "listing_id", name="seeker_swipes_unique_pair"),
    )


class HostSwipe(Base):
    __tablename__ = "host_swipes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    host_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("host_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    seeker_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("seeker_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(decision_t, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("host_id", "seeker_id", name="host_swipes_unique_pair"),
    )


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    seeker_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("seeker_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    listing_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(match_status_t, nullable=False, default="PENDING")
    score: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    matched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("seeker_id", "listing_id", name="matches_unique_pair"),
    )
