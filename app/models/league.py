from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.game import Game
    from app.models.team import Team


class League(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "leagues"

    code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    sport: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    teams: Mapped[list["Team"]] = relationship(
        back_populates="league",
        cascade="all, delete-orphan",
    )

    games: Mapped[list["Game"]] = relationship(
        back_populates="league",
    )

    def __repr__(self) -> str:
        return (
            f"League(id={self.id!r}, code={self.code!r}, "
            f"name={self.name!r})"
        )
