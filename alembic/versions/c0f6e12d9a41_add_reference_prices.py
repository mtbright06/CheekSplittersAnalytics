"""add immutable SharpStack reference prices

Revision ID: c0f6e12d9a41
Revises: b4f2e8c19a40
Create Date: 2026-07-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c0f6e12d9a41"
down_revision: Union[str, Sequence[str], None] = "b4f2e8c19a40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reference_prices",
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("provider_event_id", sa.String(length=150), nullable=False),
        sa.Column("league", sa.String(length=20), nullable=False),
        sa.Column("market", sa.String(length=50), nullable=False),
        sa.Column("selection", sa.String(length=150), nullable=False),
        sa.Column("reference_price", sa.Numeric(10, 3), nullable=False),
        sa.Column(
            "reference_implied_probability",
            sa.Numeric(10, 6),
            nullable=False,
        ),
        sa.Column("reference_book", sa.String(length=150), nullable=False),
        sa.Column("reference_captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "reference_minutes_before_start",
            sa.Numeric(10, 3),
            nullable=False,
        ),
        sa.Column("reference_policy_version", sa.String(length=50), nullable=False),
        sa.Column("scheduled_start_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("slate_date", sa.Date(), nullable=False),
        sa.Column(
            "reference_status",
            sa.String(length=50),
            server_default="LOCKED",
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reference_prices")),
        sa.UniqueConstraint(
            "provider",
            "league",
            "provider_event_id",
            "market",
            "selection",
            "scheduled_start_utc",
            name="uq_reference_prices_identity",
        ),
    )
    op.create_index(
        "ix_reference_prices_event",
        "reference_prices",
        ["league", "provider_event_id", "market"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_reference_prices_event", table_name="reference_prices")
    op.drop_table("reference_prices")
