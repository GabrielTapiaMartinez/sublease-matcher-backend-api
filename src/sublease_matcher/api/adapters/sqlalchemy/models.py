from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


decision_t = PGEnum(
    "LIKE",
    "PASS",
    name="decision_t",
    metadata=Base.metadata,
    create_type=True,
)
listing_status_t = PGEnum(
    "DRAFT",
    "PUBLISHED",
    "UNLISTED",
    name="listing_status_t",
    metadata=Base.metadata,
    create_type=True,
)
match_status_t = PGEnum(
    "PENDING",
    "MUTUAL",
    name="match_status_t",
    metadata=Base.metadata,
    create_type=True,
)
role_t = PGEnum(
    "SEEKER",
    "HOST",
    name="role_t",
    metadata=Base.metadata,
    create_type=True,
)



class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(sa.String(length=64), primary_key=True)
    email: Mapped[str] = mapped_column(sa.Text, unique=True, nullable=False)
    first_name: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    last_name: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    current_role: Mapped[str | None] = mapped_column(role_t, nullable=True)
    email_notifications_enabled: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("TRUE"),
    )
    show_in_swipe: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("TRUE"),
    )
    password_hash: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    seeker_profile: Mapped[SeekerProfile] = relationship(
        "SeekerProfile",
        back_populates="user",
        uselist=False,
    )
    host_profile: Mapped[HostProfile] = relationship(
        "HostProfile",
        back_populates="user",
        uselist=False,
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(sa.String(length=64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        sa.String(length=64),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[User] = relationship("User")


class SeekerProfile(Base):
    __tablename__ = "seeker_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_seeker_profiles_user_id"),
        CheckConstraint(
            "available_to IS NULL OR available_to >= available_from",
            name="ck_seeker_available_dates",
        ),
    )

    id: Mapped[str] = mapped_column(sa.String(length=64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        sa.String(length=64),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    visible: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("TRUE"),
    )
    bio: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    budget_min: Mapped[Decimal | None] = mapped_column(
        sa.Numeric(10, 2),
        nullable=True,
    )
    budget_max: Mapped[Decimal | None] = mapped_column(
        sa.Numeric(10, 2),
        nullable=True,
    )
    city: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    interests_csv: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    available_from: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    available_to: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    major: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="seeker_profile")
    photos: Mapped[list[SeekerPhoto]] = relationship(
        "SeekerPhoto",
        back_populates="seeker",
        cascade="all, delete-orphan",
    )
    seeker_swipes: Mapped[list[SeekerSwipe]] = relationship(
        "SeekerSwipe",
        back_populates="seeker",
        cascade="all, delete-orphan",
    )
    host_swipes: Mapped[list[HostSwipe]] = relationship(
        "HostSwipe",
        back_populates="seeker",
        cascade="all, delete-orphan",
    )
    matches: Mapped[list[Match]] = relationship(
        "Match",
        back_populates="seeker",
        cascade="all, delete-orphan",
    )


class SeekerPhoto(Base):
    __tablename__ = "seeker_photos"

    id: Mapped[str] = mapped_column(sa.String(length=64), primary_key=True)
    seeker_id: Mapped[str] = mapped_column(
        sa.String(length=64),
        ForeignKey("seeker_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    url: Mapped[str] = mapped_column(sa.Text, nullable=False)

    seeker: Mapped[SeekerProfile] = relationship("SeekerProfile", back_populates="photos")


class HostProfile(Base):
    __tablename__ = "host_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_host_profiles_user_id"),)

    id: Mapped[str] = mapped_column(sa.String(length=64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        sa.String(length=64),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    visible: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("TRUE"),
    )
    bio: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    house_rules: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="host_profile")
    listings: Mapped[list[Listing]] = relationship(
        "Listing",
        back_populates="host",
        cascade="all, delete-orphan",
    )
    swipes: Mapped[list[HostSwipe]] = relationship(
        "HostSwipe",
        back_populates="host",
        cascade="all, delete-orphan",
    )


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        UniqueConstraint("host_id", name="uq_listings_host_id"),
        CheckConstraint("price_per_month >= 0", name="ck_listing_price_non_negative"),
        CheckConstraint(
            "available_to IS NULL OR available_to >= available_from",
            name="ck_listing_available_dates",
        ),
    )

    id: Mapped[str] = mapped_column(sa.String(length=64), primary_key=True)
    host_id: Mapped[str] = mapped_column(
        sa.String(length=64),
        ForeignKey("host_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    price_per_month: Mapped[Decimal | None] = mapped_column(
        sa.Numeric(10, 2),
        nullable=True,
    )
    city: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    state: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    available_from: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    available_to: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    status: Mapped[str] = mapped_column(
        listing_status_t,
        nullable=False,
        server_default=sa.text("'DRAFT'"),
    )

    host: Mapped[HostProfile] = relationship("HostProfile", back_populates="listings")
    photos: Mapped[list[ListingPhoto]] = relationship(
        "ListingPhoto",
        back_populates="listing",
        cascade="all, delete-orphan",
    )
    roommates: Mapped[list[ListingRoommate]] = relationship(
        "ListingRoommate",
        back_populates="listing",
        cascade="all, delete-orphan",
    )
    seeker_swipes: Mapped[list[SeekerSwipe]] = relationship(
        "SeekerSwipe",
        back_populates="listing",
        cascade="all, delete-orphan",
    )
    matches: Mapped[list[Match]] = relationship(
        "Match",
        back_populates="listing",
        cascade="all, delete-orphan",
    )


class ListingPhoto(Base):
    __tablename__ = "listing_photos"

    id: Mapped[str] = mapped_column(sa.String(length=64), primary_key=True)
    listing_id: Mapped[str] = mapped_column(
        sa.String(length=64),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    url: Mapped[str] = mapped_column(sa.Text, nullable=False)

    listing: Mapped[Listing] = relationship("Listing", back_populates="photos")


class ListingRoommate(Base):
    __tablename__ = "listing_roommates"

    id: Mapped[str] = mapped_column(sa.String(length=64), primary_key=True)
    listing_id: Mapped[str] = mapped_column(
        sa.String(length=64),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    sleeping_habits: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    interests_csv: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    pronouns: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    gender: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    study_habits: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    cleanliness: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    major: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    listing: Mapped[Listing] = relationship("Listing", back_populates="roommates")


class SeekerSwipe(Base):
    __tablename__ = "seeker_swipes"
    __table_args__ = (UniqueConstraint("seeker_id", "listing_id", name="uq_seeker_swipe_listing"),)

    id: Mapped[str] = mapped_column(sa.String(length=64), primary_key=True)
    seeker_id: Mapped[str] = mapped_column(
        sa.String(length=64),
        ForeignKey("seeker_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    listing_id: Mapped[str] = mapped_column(
        sa.String(length=64),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(decision_t, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )

    seeker: Mapped[SeekerProfile] = relationship("SeekerProfile", back_populates="seeker_swipes")
    listing: Mapped[Listing] = relationship("Listing", back_populates="seeker_swipes")


class HostSwipe(Base):
    __tablename__ = "host_swipes"
    __table_args__ = (UniqueConstraint("host_id", "seeker_id", name="uq_host_swipe_seeker"),)

    id: Mapped[str] = mapped_column(sa.String(length=64), primary_key=True)
    host_id: Mapped[str] = mapped_column(
        sa.String(length=64),
        ForeignKey("host_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    seeker_id: Mapped[str] = mapped_column(
        sa.String(length=64),
        ForeignKey("seeker_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(decision_t, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )

    host: Mapped[HostProfile] = relationship("HostProfile", back_populates="swipes")
    seeker: Mapped[SeekerProfile] = relationship("SeekerProfile", back_populates="host_swipes")


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("seeker_id", "listing_id", name="uq_matches_seeker_listing"),
    )

    id: Mapped[str] = mapped_column(sa.String(length=64), primary_key=True)
    seeker_id: Mapped[str] = mapped_column(
        sa.String(length=64),
        ForeignKey("seeker_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    listing_id: Mapped[str] = mapped_column(
        sa.String(length=64),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        match_status_t,
        nullable=False,
        server_default=sa.text("'PENDING'"),
    )
    score: Mapped[Decimal | None] = mapped_column(sa.Numeric(3, 2), nullable=True)
    matched_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )

    seeker: Mapped[SeekerProfile] = relationship("SeekerProfile", back_populates="matches")
    listing: Mapped[Listing] = relationship("Listing", back_populates="matches")
