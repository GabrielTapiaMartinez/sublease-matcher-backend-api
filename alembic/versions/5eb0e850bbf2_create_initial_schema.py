"""create initial schema

Revision ID: 5eb0e850bbf2
Revises:
Create Date: 2025-11-14 14:09:14.188192

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "5eb0e850bbf2"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

decision_t = postgresql.ENUM("LIKE", "PASS", name="decision_t")
listing_status_t = postgresql.ENUM("DRAFT", "PUBLISHED", "UNLISTED", name="listing_status_t")
match_status_t = postgresql.ENUM("PENDING", "MUTUAL", name="match_status_t")
role_t = postgresql.ENUM("SEEKER", "HOST", name="role_t")


def _enum(enum_type: postgresql.ENUM) -> postgresql.ENUM:
    """Return a clone that will not attempt to recreate the underlying type."""
    clone = enum_type.copy(create_type=False)
    clone.create_type = False
    return clone


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    for enum in (decision_t, listing_status_t, match_status_t, role_t):
        enum.create(bind=bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("first_name", sa.Text(), nullable=True),
        sa.Column("last_name", sa.Text(), nullable=True),
        sa.Column("current_role", _enum(role_t), nullable=True),
        sa.Column(
            "email_notifications_enabled",
            sa.Boolean(),
            server_default=sa.text("TRUE"),
            nullable=False,
        ),
        sa.Column("show_in_swipe", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "host_profiles",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("visible", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("house_rules", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_host_profiles_user_id"),
    )
    op.create_table(
        "seeker_profiles",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("visible", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("budget_min", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("budget_max", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("interests_csv", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.Text(), nullable=True),
        sa.Column("available_from", sa.Date(), nullable=True),
        sa.Column("available_to", sa.Date(), nullable=True),
        sa.CheckConstraint("available_to IS NULL OR available_to >= available_from", name="ck_seeker_available_dates"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_seeker_profiles_user_id"),
    )
    op.create_table(
        "host_swipes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("host_id", sa.String(length=64), nullable=False),
        sa.Column("seeker_id", sa.String(length=64), nullable=False),
        sa.Column("decision", _enum(decision_t), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["host_id"], ["host_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seeker_id"], ["seeker_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("host_id", "seeker_id", name="uq_host_swipe_seeker"),
    )
    op.create_table(
        "listings",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("host_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("price_per_month", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("available_from", sa.Date(), nullable=True),
        sa.Column("available_to", sa.Date(), nullable=True),
        sa.Column(
            "status", _enum(listing_status_t), server_default=sa.text("'DRAFT'"), nullable=False
        ),
        sa.CheckConstraint(
            "available_to IS NULL OR available_to >= available_from",
            name="ck_listing_available_dates",
        ),
        sa.CheckConstraint("price_per_month >= 0", name="ck_listing_price_non_negative"),
        sa.ForeignKeyConstraint(["host_id"], ["host_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("host_id", name="uq_listings_host_id"),
    )
    op.create_table(
        "seeker_photos",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("seeker_id", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["seeker_id"], ["seeker_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "listing_photos",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("listing_id", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "listing_roommates",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("listing_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("sleeping_habits", sa.Text(), nullable=True),
        sa.Column("interests_csv", sa.Text(), nullable=True),
        sa.Column("photo_url", sa.Text(), nullable=True),
        sa.Column("pronouns", sa.Text(), nullable=True),
        sa.Column("gender", sa.Text(), nullable=True),
        sa.Column("study_habits", sa.Text(), nullable=True),
        sa.Column("cleanliness", sa.Text(), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "matches",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("seeker_id", sa.String(length=64), nullable=False),
        sa.Column("listing_id", sa.String(length=64), nullable=False),
        sa.Column(
            "status", _enum(match_status_t), server_default=sa.text("'PENDING'"), nullable=False
        ),
        sa.Column("score", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("matched_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seeker_id"], ["seeker_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("seeker_id", "listing_id", name="uq_matches_seeker_listing"),
    )
    op.create_table(
        "seeker_swipes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("seeker_id", sa.String(length=64), nullable=False),
        sa.Column("listing_id", sa.String(length=64), nullable=False),
        sa.Column("decision", _enum(decision_t), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seeker_id"], ["seeker_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("seeker_id", "listing_id", name="uq_seeker_swipe_listing"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    op.drop_table("seeker_swipes")
    op.drop_table("matches")
    op.drop_table("listing_roommates")
    op.drop_table("listing_photos")
    op.drop_table("seeker_photos")
    op.drop_table("listings")
    op.drop_table("host_swipes")
    op.drop_table("seeker_profiles")
    op.drop_table("host_profiles")
    op.drop_table("users")
    for enum in (decision_t, listing_status_t, match_status_t, role_t):
        enum.drop(bind=bind, checkfirst=True)
