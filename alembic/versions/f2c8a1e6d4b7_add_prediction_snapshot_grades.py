"""add immutable prediction snapshot grades

Revision ID: f2c8a1e6d4b7
Revises: e7b6c9d4f2a1
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2c8a1e6d4b7"
down_revision: Union[str, Sequence[str], None] = "e7b6c9d4f2a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prediction_snapshot_grades",
        sa.Column("prediction_snapshot_id", sa.UUID(), nullable=False),
        sa.Column("game_result_id", sa.UUID(), nullable=False),
        sa.Column("game_result_revision", sa.Integer(), nullable=False),
        sa.Column("grade_status", sa.String(length=20), nullable=False),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("grading_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "grade_status IN ('PENDING', 'WIN', 'LOSS', 'PUSH', 'VOID', "
            "'UNGRADEABLE')",
            name=op.f("ck_prediction_snapshot_grades_valid_grade_status"),
        ),
        sa.CheckConstraint(
            "grading_version >= 1",
            name=op.f("ck_prediction_snapshot_grades_positive_grading_version"),
        ),
        sa.CheckConstraint(
            "game_result_revision >= 1",
            name=op.f("ck_prediction_snapshot_grades_positive_result_revision"),
        ),
        sa.ForeignKeyConstraint(
            ["prediction_snapshot_id"],
            ["recommendations.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["game_result_id"],
            ["game_results.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prediction_snapshot_grades")),
        sa.UniqueConstraint(
            "prediction_snapshot_id",
            "game_result_id",
            "game_result_revision",
            name="uq_prediction_snapshot_grades_evaluation",
        ),
    )
    op.create_index(
        op.f("ix_prediction_snapshot_grades_prediction_snapshot_id"),
        "prediction_snapshot_grades",
        ["prediction_snapshot_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_prediction_snapshot_grades_game_result_id"),
        "prediction_snapshot_grades",
        ["game_result_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_prediction_snapshot_grades_grade_status"),
        "prediction_snapshot_grades",
        ["grade_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_prediction_snapshot_grades_graded_at"),
        "prediction_snapshot_grades",
        ["graded_at"],
        unique=False,
    )
    op.create_index(
        "ix_prediction_snapshot_grades_snapshot_graded",
        "prediction_snapshot_grades",
        ["prediction_snapshot_id", "graded_at"],
        unique=False,
    )
    op.create_index(
        "ix_prediction_snapshot_grades_result_revision",
        "prediction_snapshot_grades",
        ["game_result_id", "game_result_revision"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_prediction_snapshot_grades_result_revision", table_name="prediction_snapshot_grades")
    op.drop_index("ix_prediction_snapshot_grades_snapshot_graded", table_name="prediction_snapshot_grades")
    op.drop_index(op.f("ix_prediction_snapshot_grades_graded_at"), table_name="prediction_snapshot_grades")
    op.drop_index(op.f("ix_prediction_snapshot_grades_grade_status"), table_name="prediction_snapshot_grades")
    op.drop_index(op.f("ix_prediction_snapshot_grades_game_result_id"), table_name="prediction_snapshot_grades")
    op.drop_index(op.f("ix_prediction_snapshot_grades_prediction_snapshot_id"), table_name="prediction_snapshot_grades")
    op.drop_table("prediction_snapshot_grades")
