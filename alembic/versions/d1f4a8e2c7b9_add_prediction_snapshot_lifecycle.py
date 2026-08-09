"""add prediction snapshot lifecycle

Revision ID: d1f4a8e2c7b9
Revises: c0f6e12d9a41
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d1f4a8e2c7b9"
down_revision: Union[str, Sequence[str], None] = "c0f6e12d9a41"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("model_runs", sa.Column("logical_run_key", sa.String(64), nullable=True))
    op.create_index("ix_model_runs_logical_run_key", "model_runs", ["logical_run_key"], unique=True, postgresql_where=sa.text("logical_run_key IS NOT NULL"))

    op.add_column("recommendations", sa.Column("idempotency_key", sa.String(64), nullable=True))
    op.add_column("recommendations", sa.Column("provider_game_id", sa.String(150), nullable=True))
    op.add_column("recommendations", sa.Column("league_code", sa.String(20), nullable=True))
    op.add_column("recommendations", sa.Column("sport", sa.String(50), nullable=True))
    op.add_column("recommendations", sa.Column("scheduled_start_at_prediction", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("recommendations", "game_id", existing_type=sa.UUID(), nullable=True)
    op.alter_column("recommendations", "projection", existing_type=sa.Numeric(10, 3), nullable=True)
    op.alter_column("recommendations", "confidence", existing_type=sa.Numeric(6, 5), nullable=True)
    op.create_index("ix_recommendations_idempotency_key", "recommendations", ["idempotency_key"], unique=True, postgresql_where=sa.text("idempotency_key IS NOT NULL"))
    op.create_index("ix_recommendations_provider_game_id", "recommendations", ["provider_game_id"], unique=False)
    op.create_index("ix_recommendations_league_code", "recommendations", ["league_code"], unique=False)

    op.create_table(
        "active_recommendation_slots",
        sa.Column("provider_game_id", sa.String(150), nullable=False),
        sa.Column("league_code", sa.String(20), nullable=False),
        sa.Column("market_type", sa.String(50), nullable=False),
        sa.Column("active_recommendation_id", sa.UUID(), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["active_recommendation_id"], ["recommendations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_game_id", "league_code", "market_type", name="uq_active_recommendation_slots_identity"),
    )
    op.create_index("ix_active_recommendation_slots_active_recommendation_id", "active_recommendation_slots", ["active_recommendation_id"], unique=False)

    op.create_table(
        "recommendation_activation_events",
        sa.Column("provider_game_id", sa.String(150), nullable=False),
        sa.Column("league_code", sa.String(20), nullable=False),
        sa.Column("market_type", sa.String(50), nullable=False),
        sa.Column("model_run_id", sa.UUID(), nullable=False),
        sa.Column("prior_recommendation_id", sa.UUID(), nullable=True),
        sa.Column("new_recommendation_id", sa.UUID(), nullable=True),
        sa.Column("logical_run_key", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_metadata", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["model_run_id"], ["model_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["prior_recommendation_id"], ["recommendations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["new_recommendation_id"], ["recommendations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recommendation_activation_events_model_run_id", "recommendation_activation_events", ["model_run_id"], unique=False)
    op.create_index("ix_recommendation_activation_events_logical_run_key", "recommendation_activation_events", ["logical_run_key"], unique=False)
    op.create_index("ix_recommendation_activation_events_occurred_at", "recommendation_activation_events", ["occurred_at"], unique=False)
    op.create_index("ix_recommendation_activation_events_slot_time", "recommendation_activation_events", ["provider_game_id", "league_code", "market_type", "occurred_at"], unique=False)


def downgrade() -> None:
    op.drop_table("recommendation_activation_events")
    op.drop_table("active_recommendation_slots")
    op.drop_index("ix_recommendations_league_code", table_name="recommendations")
    op.drop_index("ix_recommendations_provider_game_id", table_name="recommendations")
    op.drop_index("ix_recommendations_idempotency_key", table_name="recommendations")
    op.drop_column("recommendations", "scheduled_start_at_prediction")
    op.drop_column("recommendations", "sport")
    op.drop_column("recommendations", "league_code")
    op.drop_column("recommendations", "provider_game_id")
    op.drop_column("recommendations", "idempotency_key")
    op.drop_index("ix_model_runs_logical_run_key", table_name="model_runs")
    op.drop_column("model_runs", "logical_run_key")
