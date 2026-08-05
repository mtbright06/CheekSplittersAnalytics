from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.model_version import ModelVersion
    from app.models.recommendation import Recommendation


class RecommendationEpisodeStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    WITHDRAWN = "WITHDRAWN"
    LOCKED = "LOCKED"
    GRADED = "GRADED"
    VOID = "VOID"


class RecommendationEpisodeClosureReason(StrEnum):
    SELECTION_CHANGED = "SELECTION_CHANGED"
    MARKET_LINE_CHANGED = "MARKET_LINE_CHANGED"
    RECOMMENDATION_WITHDRAWN_PASS = "RECOMMENDATION_WITHDRAWN_PASS"
    GAME_LOCKED = "GAME_LOCKED"
    POSTPONED = "POSTPONED"
    CANCELED = "CANCELED"
    INVALID_UNVERIFIED_ELIGIBILITY = "INVALID_UNVERIFIED_ELIGIBILITY"


EPISODE_STATUS_VALUES = tuple(
    item.value
    for item in RecommendationEpisodeStatus
)

CLOSURE_REASON_VALUES = tuple(
    item.value
    for item in RecommendationEpisodeClosureReason
)


def stream_identity_key(
    *,
    sport: str,
    league_code: str,
    provider: str,
    provider_game_id: str,
    market: str,
    model_version: str,
) -> str:
    return "|".join(
        _identity_part(value)
        for value in (
            sport,
            league_code,
            provider,
            provider_game_id,
            market,
            model_version,
        )
    )


def episode_identity_key(
    *,
    stream_identity: str,
    selection: str,
    selection_side: str | None,
    opened_at: datetime,
) -> str:
    return "|".join(
        [
            stream_identity,
            _identity_part(selection),
            _identity_part(selection_side or ""),
            opened_at.isoformat(),
        ]
    )


def _identity_part(value: object) -> str:
    return " ".join(
        str(value or "")
        .strip()
        .upper()
        .split()
    )


class RecommendationStream(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recommendation_streams"

    __table_args__ = (
        UniqueConstraint(
            "sport",
            "league_code",
            "provider",
            "provider_game_id",
            "market",
            "model_version",
            name="uq_recommendation_streams_identity",
        ),
        Index(
            "ix_recommendation_streams_lookup",
            "league_code",
            "provider_game_id",
            "market",
            "model_version",
        ),
    )

    sport: Mapped[str] = mapped_column(String(50), nullable=False)
    league_code: Mapped[str] = mapped_column(String(20), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_game_id: Mapped[str] = mapped_column(String(150), nullable=False)
    market: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("model_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scheduled_start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    model_version_record: Mapped["ModelVersion | None"] = relationship()
    episodes: Mapped[list["RecommendationEpisode"]] = relationship(
        back_populates="stream",
        foreign_keys="RecommendationEpisode.recommendation_stream_id",
    )

    @property
    def identity_key(self) -> str:
        return stream_identity_key(
            sport=self.sport,
            league_code=self.league_code,
            provider=self.provider,
            provider_game_id=self.provider_game_id,
            market=self.market,
            model_version=self.model_version,
        )


class RecommendationEpisode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recommendation_episodes"

    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'SUPERSEDED', 'WITHDRAWN', "
            "'LOCKED', 'GRADED', 'VOID')",
            name="valid_recommendation_episode_status",
        ),
        CheckConstraint(
            "closure_reason IS NULL OR closure_reason IN ("
            "'SELECTION_CHANGED', 'MARKET_LINE_CHANGED', "
            "'RECOMMENDATION_WITHDRAWN_PASS', 'GAME_LOCKED', "
            "'POSTPONED', 'CANCELED', "
            "'INVALID_UNVERIFIED_ELIGIBILITY')",
            name="valid_recommendation_episode_closure_reason",
        ),
        UniqueConstraint(
            "recommendation_stream_id",
            "selection",
            "selection_side",
            "opened_at",
            name="uq_recommendation_episodes_identity",
        ),
        Index(
            "uq_recommendation_episodes_one_active_per_stream",
            "recommendation_stream_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
            sqlite_where=text("status = 'ACTIVE'"),
        ),
        Index(
            "ix_recommendation_episodes_stream_status",
            "recommendation_stream_id",
            "status",
            "opened_at",
        ),
        Index(
            "ix_recommendation_episodes_canonical_snapshot",
            "canonical_snapshot_id",
        ),
    )

    recommendation_stream_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("recommendation_streams.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    selection: Mapped[str] = mapped_column(String(150), nullable=False)
    selection_side: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="",
        server_default="",
    )
    market_line: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closure_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    canonical_snapshot_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("recommendations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    superseded_by_episode_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("recommendation_episodes.id", ondelete="SET NULL"),
        nullable=True,
    )

    stream: Mapped[RecommendationStream] = relationship(
        back_populates="episodes",
        foreign_keys=[recommendation_stream_id],
    )
    canonical_snapshot: Mapped["Recommendation | None"] = relationship(
        foreign_keys=[canonical_snapshot_id],
    )
    superseded_by_episode: Mapped["RecommendationEpisode | None"] = relationship(
        remote_side="RecommendationEpisode.id",
        foreign_keys=[superseded_by_episode_id],
    )
    canonical_grade: Mapped["CanonicalRecommendationGrade | None"] = relationship(
        back_populates="episode",
        uselist=False,
    )

    @property
    def identity_key(self) -> str:
        return episode_identity_key(
            stream_identity=self.stream.identity_key,
            selection=self.selection,
            selection_side=self.selection_side,
            opened_at=self.opened_at,
        )


class CanonicalRecommendationGrade(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "canonical_recommendation_grades"

    __table_args__ = (
        CheckConstraint(
            "grade_status IN ('WIN', 'LOSS', 'PUSH', 'VOID', "
            "'UNGRADEABLE')",
            name="valid_canonical_recommendation_grade_status",
        ),
        CheckConstraint("grading_version >= 1", name="positive_grading_version"),
        UniqueConstraint(
            "recommendation_episode_id",
            name="uq_canonical_recommendation_grades_episode",
        ),
        Index(
            "ix_canonical_recommendation_grades_snapshot_result",
            "canonical_snapshot_id",
            "game_result_id",
            "game_result_revision",
        ),
    )

    recommendation_episode_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("recommendation_episodes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    canonical_snapshot_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("recommendations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    game_result_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("game_results.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    game_result_revision: Mapped[int] = mapped_column(nullable=False)
    grade_status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    graded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    grading_version: Mapped[int] = mapped_column(nullable=False, default=1, server_default="1")

    episode: Mapped[RecommendationEpisode] = relationship(
        back_populates="canonical_grade",
        foreign_keys=[recommendation_episode_id],
    )
    canonical_snapshot: Mapped["Recommendation"] = relationship(
        foreign_keys=[canonical_snapshot_id],
    )
