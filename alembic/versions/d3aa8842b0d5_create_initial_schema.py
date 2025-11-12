"""create initial schema"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as psql

# Revision identifiers, used by Alembic.
revision = "d3aa8842b0d5"
down_revision = None
branch_labels = None
depends_on = None

# Global PG ENUM singletons (created once; columns must use .copy(create_type=False))
listing_status = psql.ENUM("DRAFT", "PUBLISHED", "UNLISTED", name="listing_status_t")
match_status = psql.ENUM("PENDING", "MUTUAL", name="match_status_t")
decision_enum = psql.ENUM("LIKE", "PASS", name="decision_t")
role_enum = psql.ENUM("SEEKER", "HOST", name="role_t")
term_enum = psql.ENUM("Fall", "Spring", "Summer", name="term_t")


def upgrade() -> None:
    bind = op.get_bind()

    # Create ENUM types once, idempotently.
    for enum in (listing_status, match_status, decision_enum, role_enum, term_enum):
        enum.create(bind=bind, checkfirst=True)

    # Sanity ping so failures surface early.
    op.execute(sa.text("SELECT 1"))

    # USERS
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("current_role", role_enum.copy(create_type=False), nullable=True),
        sa.Column(
            "email_notifications_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "show_in_swipe",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="users_email_key"),
    )

    # HOST_PROFILES
    op.create_table(
        "host_profiles",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("visible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("house_rules", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="host_profiles_user_id_key"),
    )

    # SEEKER_PROFILES
    op.create_table(
        "seeker_profiles",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("visible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("term", term_enum.copy(create_type=False), nullable=True),
        sa.Column("term_year", sa.Integer(), nullable=True),
        sa.Column("budget_min", sa.Numeric(10, 2), nullable=True),
        sa.Column("budget_max", sa.Numeric(10, 2), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("interests_csv", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="seeker_profiles_user_id_key"),
        sa.CheckConstraint(
            "(budget_min IS NULL OR budget_min >= 0) AND (budget_max IS NULL OR budget_max >= 0)",
            name="seeker_profiles_budget_non_negative",
        ),
        sa.CheckConstraint(
            "budget_min IS NULL OR budget_max IS NULL OR budget_max >= budget_min",
            name="seeker_profiles_budget_order",
        ),
    )

    # LISTINGS
    op.create_table(
        "listings",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("host_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("price_per_month", sa.Numeric(10, 2), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("state", sa.String(length=2), nullable=True),
        sa.Column("available_from", sa.Date(), nullable=True),
        sa.Column("available_to", sa.Date(), nullable=True),
        sa.Column(
            "status",
            listing_status.copy(create_type=False),
            nullable=False,
            server_default=sa.text("'DRAFT'"),
        ),
        sa.ForeignKeyConstraint(["host_id"], ["host_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("host_id", name="listings_host_id_key"),
        sa.CheckConstraint("price_per_month IS NULL OR price_per_month >= 0", name="listings_price_non_negative"),
        sa.CheckConstraint(
            "available_to IS NULL OR available_from IS NULL OR available_to >= available_from",
            name="listings_available_dates_check",
        ),
    )

    # LISTING_PHOTOS
    op.create_table(
        "listing_photos",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("listing_id", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("url", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # LISTING_ROOMMATES
    op.create_table(
        "listing_roommates",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("listing_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("sleeping_habits", sa.String(length=120), nullable=True),
        sa.Column("interests_csv", sa.Text(), nullable=True),
        sa.Column("photo_url", sa.Text(), nullable=True),
        sa.Column("pronouns", sa.String(length=60), nullable=True),
        sa.Column("gender", sa.String(length=60), nullable=True),
        sa.Column("study_habits", sa.String(length=120), nullable=True),
        sa.Column("cleanliness", sa.String(length=120), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # SEEKER_PHOTOS
    op.create_table(
        "seeker_photos",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("seeker_id", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("url", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["seeker_id"], ["seeker_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # HOST_SWIPES
    op.create_table(
        "host_swipes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("host_id", sa.String(length=64), nullable=False),
        sa.Column("seeker_id", sa.String(length=64), nullable=False),
        sa.Column("decision", decision_enum.copy(create_type=False), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["host_id"], ["host_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seeker_id"], ["seeker_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("host_id", "seeker_id", name="host_swipes_unique_pair"),
    )

    # SEEKER_SWIPES
    op.create_table(
        "seeker_swipes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("seeker_id", sa.String(length=64), nullable=False),
        sa.Column("listing_id", sa.String(length=64), nullable=False),
        sa.Column("decision", decision_enum.copy(create_type=False), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seeker_id"], ["seeker_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("seeker_id", "listing_id", name="seeker_swipes_unique_pair"),
    )

    # MATCHES
    op.create_table(
        "matches",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("seeker_id", sa.String(length=64), nullable=False),
        sa.Column("listing_id", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            match_status.copy(create_type=False),
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
        sa.Column("score", sa.Numeric(3, 2), nullable=True),
        sa.Column("matched_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seeker_id"], ["seeker_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("seeker_id", "listing_id", name="matches_unique_pair"),
    )


def downgrade() -> None:
    # Drop tables first (FKs depend on them)
    op.drop_table("matches")
    op.drop_table("seeker_swipes")
    op.drop_table("host_swipes")
    op.drop_table("seeker_photos")
    op.drop_table("listing_roommates")
    op.drop_table("listing_photos")
    op.drop_table("listings")
    op.drop_table("seeker_profiles")
    op.drop_table("host_profiles")
    op.drop_table("users")

    # Then drop ENUM types (reverse order is safe)
    bind = op.get_bind()
    for enum in (term_enum, role_enum, decision_enum, match_status, listing_status):
        enum.drop(bind=bind, checkfirst=True)
