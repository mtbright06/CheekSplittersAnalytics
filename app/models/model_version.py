from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.model_run import ModelRun
    from app.models.recommendation import Recommendation


class ModelVersion(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "model_versions"

    __table_args__ = (
        UniqueConstraint(
            "model_name",
            "version",
            "git_commit",
            name="uq_model_versions_identity",
        ),
    )

    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    git_commit: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    model_runs: Mapped[list["ModelRun"]] = relationship(
        back_populates="model_version",
    )

    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="model_version",
    )

    def __repr__(self) -> str:
        return (
            f"ModelVersion("
            f"id={self.id!r}, "
            f"model_name={self.model_name!r}, "
            f"version={self.version!r}, "
            f"git_commit={self.git_commit!r}"
            f")"
        )
