from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ActiveRecommendationSlot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "active_recommendation_slots"

    __table_args__ = (
        UniqueConstraint(
            "provider_game_id",
            "league_code",
            "market_type",
            name="uq_active_recommendation_slots_identity",
        ),
    )

    provider_game_id: Mapped[str] = mapped_column(String(150), nullable=False)
    league_code: Mapped[str] = mapped_column(String(20), nullable=False)
    market_type: Mapped[str] = mapped_column(String(50), nullable=False)
    active_recommendation_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("recommendations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
