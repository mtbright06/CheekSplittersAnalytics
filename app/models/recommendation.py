from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.game import Game
    from app.models.model_version import ModelVersion


class Recommendation(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "recommendations"

    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range",
        ),
        Index(
            "ix_recommendations_game_created",
            "game_id",
            "created_at",
        ),
        Index(
            "ix_recommendations_market_created",
            "market_type",
            "created_at",
        ),
        Index(
            "ix_recommendations_model_created",
            "model_version_id",
            "created_at",
        ),
    )

    game_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("games.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    model_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("model_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    market_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    selection: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    market_line: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 3),
        nullable=True,
    )

    projection: Mapped[Decimal] = mapped_column(
        Numeric(10, 3),
        nullable=False,
    )

    edge: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 3),
        nullable=True,
    )

    confidence: Mapped[Decimal] = mapped_column(
        Numeric(6, 5),
        nullable=False,
    )

    components: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=False,
        default=dict,
        server_default="{}",
    )

    explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="sharpstack",
        server_default="sharpstack",
        index=True,
    )

    recommendation_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    game: Mapped["Game"] = relationship(
        back_populates="recommendations",
    )

    model_version: Mapped["ModelVersion"] = relationship(
        back_populates="recommendations",
    )

    def __repr__(self) -> str:
        return (
            f"Recommendation(id={self.id!r}, "
            f"market_type={self.market_type!r}, "
            f"selection={self.selection!r}, "
            f"projection={self.projection!r})"
        )
