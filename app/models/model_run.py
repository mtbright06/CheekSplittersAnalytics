from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.model_version import ModelVersion
    from app.models.recommendation import Recommendation


class ModelRun(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """
    Represents one execution of a SharpStack prediction model.

    A single run may generate recommendations for multiple games.
    Grouping recommendations by run allows SharpStack to distinguish
    morning, afternoon, post-lineup, or other model executions.
    """

    __tablename__ = "model_runs"

    __table_args__ = (
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="completed_after_started",
        ),
        Index(
            "ix_model_runs_model_started",
            "model_version_id",
            "started_at",
        ),
        Index(
            "ix_model_runs_status_started",
            "status",
            "started_at",
        ),
    )

    model_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "model_versions.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="running",
        server_default="running",
        index=True,
    )

    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="sharpstack",
        server_default="sharpstack",
        index=True,
    )

    run_label: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    run_metadata: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=False,
        default=dict,
        server_default="{}",
    )

    logical_run_key: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
        index=True,
    )

    model_version: Mapped["ModelVersion"] = relationship(
        back_populates="model_runs",
    )

    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="model_run",
    )

    def __repr__(self) -> str:
        return (
            f"ModelRun("
            f"id={self.id!r}, "
            f"model_version_id={self.model_version_id!r}, "
            f"started_at={self.started_at!r}, "
            f"status={self.status!r}"
            f")"
        )
