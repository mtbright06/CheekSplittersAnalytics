"""add authoritative game results

Revision ID: e7b6c9d4f2a1
Revises: d1f4a8e2c7b9
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e7b6c9d4f2a1"
down_revision: Union[str, Sequence[str], None] = "d1f4a8e2c7b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "game_results",
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("league_code", sa.String(length=20), nullable=False),
        sa.Column("provider_game_id", sa.String(length=150), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("source_status", sa.String(length=100), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("total_score", sa.Integer(), nullable=True),
        sa.Column("winner_side", sa.String(length=10), nullable=True),
        sa.Column("game_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("went_extra_innings", sa.Boolean(), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "source_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('SCHEDULED', 'LIVE', 'FINAL', 'POSTPONED', "
            "'SUSPENDED', 'CANCELED', 'INCOMPLETE')",
            name=op.f("ck_game_results_valid_status"),
        ),
        sa.CheckConstraint(
            "winner_side IS NULL OR winner_side IN ('HOME', 'AWAY', 'TIE')",
            name=op.f("ck_game_results_valid_winner_side"),
        ),
        sa.CheckConstraint(
            "away_score IS NULL OR away_score >= 0",
            name=op.f("ck_game_results_nonnegative_away_score"),
        ),
        sa.CheckConstraint(
            "home_score IS NULL OR home_score >= 0",
            name=op.f("ck_game_results_nonnegative_home_score"),
        ),
        sa.CheckConstraint(
            "total_score IS NULL OR "
            "(away_score IS NOT NULL AND home_score IS NOT NULL "
            "AND total_score = away_score + home_score)",
            name=op.f("ck_game_results_consistent_total_score"),
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name=op.f("ck_game_results_positive_revision"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_game_results")),
        sa.UniqueConstraint(
            "provider",
            "league_code",
            "provider_game_id",
            name="uq_game_results_provider_identity",
        ),
    )
    op.create_index(
        op.f("ix_game_results_status"),
        "game_results",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_game_results_league_status",
        "game_results",
        ["league_code", "status"],
        unique=False,
    )
    op.create_index(
        "ix_game_results_completion",
        "game_results",
        ["game_completed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_game_results_completion", table_name="game_results")
    op.drop_index("ix_game_results_league_status", table_name="game_results")
    op.drop_index(op.f("ix_game_results_status"), table_name="game_results")
    op.drop_table("game_results")
