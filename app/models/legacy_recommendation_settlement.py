from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.recommendation import Recommendation


class LegacyRecommendationSettlement(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Legacy wager-settlement record retained for existing history consumers."""

    __tablename__ = "recommendation_grades"

    __table_args__ = (
        CheckConstraint(
            "outcome IN ('WIN', 'LOSS', 'PUSH', 'VOID')",
            name="valid_outcome",
        ),
        CheckConstraint("stake_units > 0", name="positive_stake_units"),
        CheckConstraint(
            "american_odds IS NULL OR american_odds <> 0",
            name="nonzero_american_odds",
        ),
        Index(
            "ix_recommendation_grades_recommendation_graded",
            "recommendation_id",
            "graded_at",
        ),
    )

    recommendation_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("recommendations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    outcome: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    american_odds: Mapped[int | None] = mapped_column(nullable=True)
    stake_units: Mapped[Decimal] = mapped_column(
        Numeric(10, 3),
        nullable=False,
        default=Decimal("1.000"),
        server_default="1.000",
    )
    profit_units: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    actual_home_score: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 3),
        nullable=True,
    )
    actual_away_score: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 3),
        nullable=True,
    )
    graded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="manual",
        server_default="manual",
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    grade_metadata: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=False,
        default=dict,
        server_default="{}",
    )

    recommendation: Mapped["Recommendation"] = relationship(back_populates="grades")
