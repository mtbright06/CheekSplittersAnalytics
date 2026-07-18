from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.league import League
    from app.models.recommendation import Recommendation
    from app.models.team import Team


class Game(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "games"

    __table_args__ = (
        UniqueConstraint(
            "league_id",
            "external_game_id",
            name="uq_games_league_external_game",
        ),
        CheckConstraint(
            "home_team_id <> away_team_id",
            name="different_teams",
        ),
        Index(
            "ix_games_league_start_time",
            "league_id",
            "scheduled_start",
        ),
    )

    league_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("leagues.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    external_game_id: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )

    scheduled_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    home_team_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    away_team_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="scheduled",
        server_default="scheduled",
        index=True,
    )

    venue: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    league: Mapped["League"] = relationship(
        back_populates="games",
    )

    home_team: Mapped["Team"] = relationship(
        back_populates="home_games",
        foreign_keys=[home_team_id],
    )

    away_team: Mapped["Team"] = relationship(
        back_populates="away_games",
        foreign_keys=[away_team_id],
    )

    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="game",
    )

    def __repr__(self) -> str:
        return (
            f"Game(id={self.id!r}, external_game_id="
            f"{self.external_game_id!r}, scheduled_start="
            f"{self.scheduled_start!r})"
        )
