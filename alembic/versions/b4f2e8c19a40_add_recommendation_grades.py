"""add recommendation grades

Revision ID: b4f2e8c19a40
Revises: 5d535e524d31
Create Date: 2026-07-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b4f2e8c19a40"
down_revision: Union[str, Sequence[str], None] = "5d535e524d31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recommendation_grades",
        sa.Column("recommendation_id", sa.UUID(), nullable=False),
        sa.Column("outcome", sa.String(length=10), nullable=False),
        sa.Column("american_odds", sa.Integer(), nullable=True),
        sa.Column(
            "stake_units",
            sa.Numeric(precision=10, scale=3),
            server_default="1.000",
            nullable=False,
        ),
        sa.Column("profit_units", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("actual_home_score", sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column("actual_away_score", sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column(
            "graded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.String(length=100),
            server_default="manual",
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "grade_metadata",
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
        sa.CheckConstraint(
            "american_odds IS NULL OR american_odds <> 0",
            name=op.f("ck_recommendation_grades_nonzero_american_odds"),
        ),
        sa.CheckConstraint(
            "outcome IN ('WIN', 'LOSS', 'PUSH', 'VOID')",
            name=op.f("ck_recommendation_grades_valid_outcome"),
        ),
        sa.CheckConstraint(
            "stake_units > 0",
            name=op.f("ck_recommendation_grades_positive_stake_units"),
        ),
        sa.ForeignKeyConstraint(
            ["recommendation_id"],
            ["recommendations.id"],
            name=op.f(
                "fk_recommendation_grades_recommendation_id_recommendations"
            ),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation_grades")),
    )
    op.create_index(
        op.f("ix_recommendation_grades_graded_at"),
        "recommendation_grades",
        ["graded_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_recommendation_grades_outcome"),
        "recommendation_grades",
        ["outcome"],
        unique=False,
    )
    op.create_index(
        op.f("ix_recommendation_grades_recommendation_id"),
        "recommendation_grades",
        ["recommendation_id"],
        unique=False,
    )
    op.create_index(
        "ix_recommendation_grades_recommendation_graded",
        "recommendation_grades",
        ["recommendation_id", "graded_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_recommendation_grades_source"),
        "recommendation_grades",
        ["source"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_recommendation_grades_source"),
        table_name="recommendation_grades",
    )
    op.drop_index(
        "ix_recommendation_grades_recommendation_graded",
        table_name="recommendation_grades",
    )
    op.drop_index(
        op.f("ix_recommendation_grades_recommendation_id"),
        table_name="recommendation_grades",
    )
    op.drop_index(
        op.f("ix_recommendation_grades_outcome"),
        table_name="recommendation_grades",
    )
    op.drop_index(
        op.f("ix_recommendation_grades_graded_at"),
        table_name="recommendation_grades",
    )
    op.drop_table("recommendation_grades")
