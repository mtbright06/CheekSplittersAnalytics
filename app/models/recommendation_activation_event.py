from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class RecommendationActivationEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "recommendation_activation_events"

    __table_args__ = (
        Index("ix_recommendation_activation_events_slot_time", "provider_game_id", "league_code", "market_type", "occurred_at"),
    )

    provider_game_id: Mapped[str] = mapped_column(String(150), nullable=False)
    league_code: Mapped[str] = mapped_column(String(20), nullable=False)
    market_type: Mapped[str] = mapped_column(String(50), nullable=False)
    model_run_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("model_runs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    prior_recommendation_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("recommendations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    new_recommendation_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("recommendations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    logical_run_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB), nullable=False, default=dict, server_default="{}"
    )
