from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class GameResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Mutable authoritative outcome record for one provider game identity."""

    __tablename__ = "game_results"

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "league_code",
            "provider_game_id",
            name="uq_game_results_provider_identity",
        ),
        CheckConstraint(
            "status IN ('SCHEDULED', 'LIVE', 'FINAL', 'POSTPONED', "
            "'SUSPENDED', 'CANCELED', 'INCOMPLETE')",
            name="valid_status",
        ),
        CheckConstraint(
            "winner_side IS NULL OR winner_side IN ('HOME', 'AWAY', 'TIE')",
            name="valid_winner_side",
        ),
        CheckConstraint(
            "away_score IS NULL OR away_score >= 0",
            name="nonnegative_away_score",
        ),
        CheckConstraint(
            "home_score IS NULL OR home_score >= 0",
            name="nonnegative_home_score",
        ),
        CheckConstraint(
            "total_score IS NULL OR "
            "(away_score IS NOT NULL AND home_score IS NOT NULL "
            "AND total_score = away_score + home_score)",
            name="consistent_total_score",
        ),
        CheckConstraint("revision >= 1", name="positive_revision"),
        Index("ix_game_results_league_status", "league_code", "status"),
        Index("ix_game_results_completion", "game_completed_at"),
    )

    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    league_code: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_game_id: Mapped[str] = mapped_column(String(150), nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    source_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    winner_side: Mapped[str | None] = mapped_column(String(10), nullable=True)
    game_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    went_extra_innings: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    source_metadata: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=False,
        default=dict,
        server_default="{}",
    )
