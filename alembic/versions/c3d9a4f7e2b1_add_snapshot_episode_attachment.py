"""add snapshot episode attachment

Revision ID: c3d9a4f7e2b1
Revises: a7c9e2f4b681
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d9a4f7e2b1"
down_revision: Union[str, Sequence[str], None] = "a7c9e2f4b681"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recommendations",
        sa.Column("recommendation_episode_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_recommendations_episode",
        "recommendations",
        "recommendation_episodes",
        ["recommendation_episode_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_recommendations_recommendation_episode_id"),
        "recommendations",
        ["recommendation_episode_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_recommendations_recommendation_episode_id"),
        table_name="recommendations",
    )
    op.drop_constraint(
        "fk_recommendations_episode",
        "recommendations",
        type_="foreignkey",
    )
    op.drop_column("recommendations", "recommendation_episode_id")
