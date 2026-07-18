from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.game import Game
    from app.models.league import League


class Team(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "teams"

    __table_args__ = (
        UniqueConstraint(
            "league_id",
            "code",
            name="uq_teams_league_code",
        ),
    )

    league_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("leagues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    external_team_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    league: Mapped["League"] = relationship(
        back_populates="teams",
    )

    home_games: Mapped[list["Game"]] = relationship(
        back_populates="home_team",
        foreign_keys="Game.home_team_id",
    )

    away_games: Mapped[list["Game"]] = relationship(
        back_populates="away_team",
        foreign_keys="Game.away_team_id",
    )

    def __repr__(self) -> str:
        return (
            f"Team(id={self.id!r}, code={self.code!r}, "
            f"name={self.name!r})"
        )
