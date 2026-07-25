from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class ReferencePrice(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Immutable SharpStack Reference Price for one market selection."""

    __tablename__ = "reference_prices"

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "league",
            "provider_event_id",
            "market",
            "selection",
            "scheduled_start_utc",
            name="uq_reference_prices_identity",
        ),
        Index(
            "ix_reference_prices_event",
            "league",
            "provider_event_id",
            "market",
        ),
    )

    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(150), nullable=False)
    league: Mapped[str] = mapped_column(String(20), nullable=False)
    market: Mapped[str] = mapped_column(String(50), nullable=False)
    selection: Mapped[str] = mapped_column(String(150), nullable=False)
    reference_price: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    reference_implied_probability: Mapped[Decimal] = mapped_column(
        Numeric(10, 6),
        nullable=False,
    )
    reference_book: Mapped[str] = mapped_column(String(150), nullable=False)
    reference_captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    reference_minutes_before_start: Mapped[Decimal] = mapped_column(
        Numeric(10, 3),
        nullable=False,
    )
    reference_policy_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    scheduled_start_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    slate_date: Mapped[date] = mapped_column(Date, nullable=False)
    reference_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="LOCKED",
        server_default="LOCKED",
    )
