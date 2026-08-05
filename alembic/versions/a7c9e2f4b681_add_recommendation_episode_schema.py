"""add recommendation episode schema

Revision ID: a7c9e2f4b681
Revises: f2c8a1e6d4b7
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7c9e2f4b681"
down_revision: Union[str, Sequence[str], None] = "f2c8a1e6d4b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recommendation_streams",
        sa.Column("sport", sa.String(length=50), nullable=False),
        sa.Column("league_code", sa.String(length=20), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("provider_game_id", sa.String(length=150), nullable=False),
        sa.Column("market", sa.String(length=50), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("model_version_id", sa.UUID(), nullable=True),
        sa.Column("scheduled_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation_streams")),
        sa.UniqueConstraint(
            "sport",
            "league_code",
            "provider",
            "provider_game_id",
            "market",
            "model_version",
            name="uq_recommendation_streams_identity",
        ),
    )
    op.create_index(op.f("ix_recommendation_streams_model_version_id"), "recommendation_streams", ["model_version_id"])
    op.create_index(
        "ix_recommendation_streams_lookup",
        "recommendation_streams",
        ["league_code", "provider_game_id", "market", "model_version"],
    )

    op.create_table(
        "recommendation_episodes",
        sa.Column("recommendation_stream_id", sa.UUID(), nullable=False),
        sa.Column("selection", sa.String(length=150), nullable=False),
        sa.Column("selection_side", sa.String(length=10), server_default="", nullable=False),
        sa.Column("market_line", sa.Numeric(10, 3), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closure_reason", sa.String(length=50), nullable=True),
        sa.Column("canonical_snapshot_id", sa.UUID(), nullable=True),
        sa.Column("superseded_by_episode_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'SUPERSEDED', 'WITHDRAWN', 'LOCKED', 'GRADED', 'VOID')",
            name=op.f("ck_recommendation_episodes_valid_recommendation_episode_status"),
        ),
        sa.CheckConstraint(
            "closure_reason IS NULL OR closure_reason IN ("
            "'SELECTION_CHANGED', 'MARKET_LINE_CHANGED', "
            "'RECOMMENDATION_WITHDRAWN_PASS', 'GAME_LOCKED', "
            "'POSTPONED', 'CANCELED', "
            "'INVALID_UNVERIFIED_ELIGIBILITY')",
            name=op.f("ck_recommendation_episodes_valid_recommendation_episode_closure_reason"),
        ),
        sa.ForeignKeyConstraint(["recommendation_stream_id"], ["recommendation_streams.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["canonical_snapshot_id"], ["recommendations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["superseded_by_episode_id"], ["recommendation_episodes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation_episodes")),
        sa.UniqueConstraint(
            "recommendation_stream_id",
            "selection",
            "selection_side",
            "opened_at",
            name="uq_recommendation_episodes_identity",
        ),
    )
    op.create_index(op.f("ix_recommendation_episodes_recommendation_stream_id"), "recommendation_episodes", ["recommendation_stream_id"])
    op.create_index(op.f("ix_recommendation_episodes_status"), "recommendation_episodes", ["status"])
    op.create_index("ix_recommendation_episodes_canonical_snapshot", "recommendation_episodes", ["canonical_snapshot_id"])
    op.create_index(
        "ix_recommendation_episodes_stream_status",
        "recommendation_episodes",
        ["recommendation_stream_id", "status", "opened_at"],
    )
    op.create_index(
        "uq_recommendation_episodes_one_active_per_stream",
        "recommendation_episodes",
        ["recommendation_stream_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.create_table(
        "canonical_recommendation_grades",
        sa.Column("recommendation_episode_id", sa.UUID(), nullable=False),
        sa.Column("canonical_snapshot_id", sa.UUID(), nullable=False),
        sa.Column("game_result_id", sa.UUID(), nullable=False),
        sa.Column("game_result_revision", sa.Integer(), nullable=False),
        sa.Column("grade_status", sa.String(length=20), nullable=False),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("grading_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "grade_status IN ('WIN', 'LOSS', 'PUSH', 'VOID', 'UNGRADEABLE')",
            name=op.f("ck_canonical_recommendation_grades_valid_canonical_recommendation_grade_status"),
        ),
        sa.CheckConstraint(
            "grading_version >= 1",
            name=op.f("ck_canonical_recommendation_grades_positive_grading_version"),
        ),
        sa.ForeignKeyConstraint(["recommendation_episode_id"], ["recommendation_episodes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["canonical_snapshot_id"], ["recommendations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["game_result_id"], ["game_results.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_canonical_recommendation_grades")),
        sa.UniqueConstraint(
            "recommendation_episode_id",
            name="uq_canonical_recommendation_grades_episode",
        ),
    )
    op.create_index(op.f("ix_canonical_recommendation_grades_recommendation_episode_id"), "canonical_recommendation_grades", ["recommendation_episode_id"])
    op.create_index(op.f("ix_canonical_recommendation_grades_canonical_snapshot_id"), "canonical_recommendation_grades", ["canonical_snapshot_id"])
    op.create_index(op.f("ix_canonical_recommendation_grades_game_result_id"), "canonical_recommendation_grades", ["game_result_id"])
    op.create_index(op.f("ix_canonical_recommendation_grades_grade_status"), "canonical_recommendation_grades", ["grade_status"])
    op.create_index(
        "ix_canonical_recommendation_grades_snapshot_result",
        "canonical_recommendation_grades",
        ["canonical_snapshot_id", "game_result_id", "game_result_revision"],
    )


def downgrade() -> None:
    op.drop_index("ix_canonical_recommendation_grades_snapshot_result", table_name="canonical_recommendation_grades")
    op.drop_index(op.f("ix_canonical_recommendation_grades_grade_status"), table_name="canonical_recommendation_grades")
    op.drop_index(op.f("ix_canonical_recommendation_grades_game_result_id"), table_name="canonical_recommendation_grades")
    op.drop_index(op.f("ix_canonical_recommendation_grades_canonical_snapshot_id"), table_name="canonical_recommendation_grades")
    op.drop_index(op.f("ix_canonical_recommendation_grades_recommendation_episode_id"), table_name="canonical_recommendation_grades")
    op.drop_table("canonical_recommendation_grades")
    op.drop_index("uq_recommendation_episodes_one_active_per_stream", table_name="recommendation_episodes")
    op.drop_index("ix_recommendation_episodes_stream_status", table_name="recommendation_episodes")
    op.drop_index("ix_recommendation_episodes_canonical_snapshot", table_name="recommendation_episodes")
    op.drop_index(op.f("ix_recommendation_episodes_status"), table_name="recommendation_episodes")
    op.drop_index(op.f("ix_recommendation_episodes_recommendation_stream_id"), table_name="recommendation_episodes")
    op.drop_table("recommendation_episodes")
    op.drop_index("ix_recommendation_streams_lookup", table_name="recommendation_streams")
    op.drop_index(op.f("ix_recommendation_streams_model_version_id"), table_name="recommendation_streams")
    op.drop_table("recommendation_streams")
