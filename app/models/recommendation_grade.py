from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, event, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.game_result import GameResult
    from app.models.recommendation import Recommendation


class RecommendationGrade(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Immutable evaluation of one prediction snapshot against game truth."""

    __tablename__ = "prediction_snapshot_grades"

    __table_args__ = (
        CheckConstraint(
            "grade_status IN ('PENDING', 'WIN', 'LOSS', 'PUSH', 'VOID', "
            "'UNGRADEABLE')",
            name="valid_grade_status",
        ),
        CheckConstraint("grading_version >= 1", name="positive_grading_version"),
        CheckConstraint("game_result_revision >= 1", name="positive_result_revision"),
        UniqueConstraint(
            "prediction_snapshot_id",
            "game_result_id",
            "game_result_revision",
            name="uq_prediction_snapshot_grades_evaluation",
        ),
        Index(
            "ix_prediction_snapshot_grades_snapshot_graded",
            "prediction_snapshot_id",
            "graded_at",
        ),
        Index(
            "ix_prediction_snapshot_grades_result_revision",
            "game_result_id",
            "game_result_revision",
        ),
    )

    prediction_snapshot_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("recommendations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    game_result_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("game_results.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    game_result_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    grade_status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    graded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    grading_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    prediction_snapshot: Mapped["Recommendation"] = relationship(
        back_populates="prediction_grades",
    )
    game_result: Mapped["GameResult"] = relationship(
        back_populates="recommendation_grades",
    )


@event.listens_for(RecommendationGrade, "before_update")
@event.listens_for(RecommendationGrade, "before_delete")
def _reject_grade_mutation(mapper, connection, target) -> None:
    raise TypeError("RecommendationGrade records are immutable; create a new grade.")
