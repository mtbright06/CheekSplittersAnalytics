from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.database.session import SessionLocal
from app.models import (
    CanonicalRecommendationGrade,
    GameResult,
    ModelRun,
    ModelVersion,
    Recommendation,
    RecommendationEpisode,
    RecommendationStream,
)
from app.models.recommendation_episode import RecommendationEpisodeStatus


class CanonicalRecommendationReadError(RuntimeError):
    """Raised when canonical recommendation records cannot be loaded."""


@dataclass(frozen=True, slots=True)
class CanonicalRecommendationRecord:
    episode_id: UUID
    stream_id: UUID
    sport: str
    league_code: str
    provider: str
    provider_game_id: str
    market: str
    selection: str
    selection_side: str
    canonical_snapshot_id: UUID
    canonical_snapshot_time: datetime
    canonical_market_line: Decimal | None
    recommendation_tier: str | None
    confidence: Decimal | None
    hammer_score: Decimal | None
    model_probability: Decimal | None
    opened_at: datetime
    locked_at: datetime | None
    graded_at: datetime
    canonical_grade_id: UUID
    grade_status: str
    game_result_id: UUID
    game_result_revision: int
    result_status: str
    winner_side: str | None
    total_score: int | None
    model_version: str
    model_name: str | None
    git_commit: str | None
    model_run_id: UUID | None
    run_source: str | None
    components: dict[str, Any]
    explanation: str | None
    source: str


@dataclass(frozen=True, slots=True)
class RecommendationTimelineSnapshot:
    snapshot_id: UUID
    recommendation_time: datetime
    selection: str
    market_line: Decimal | None
    recommendation_tier: str | None
    confidence: Decimal | None
    hammer_score: Decimal | None


class CanonicalRecommendationReadModel:
    """Shared read model for official episode-based analytics."""

    def __init__(self, session_factory: sessionmaker[Session] = SessionLocal) -> None:
        self._session_factory = session_factory

    def list_graded_records(self) -> tuple[CanonicalRecommendationRecord, ...]:
        statement = (
            select(
                RecommendationEpisode,
                RecommendationStream,
                Recommendation,
                CanonicalRecommendationGrade,
                GameResult,
                ModelVersion,
                ModelRun,
            )
            .join(
                RecommendationStream,
                RecommendationStream.id
                == RecommendationEpisode.recommendation_stream_id,
            )
            .join(
                Recommendation,
                Recommendation.id == RecommendationEpisode.canonical_snapshot_id,
            )
            .join(
                CanonicalRecommendationGrade,
                CanonicalRecommendationGrade.recommendation_episode_id
                == RecommendationEpisode.id,
            )
            .join(
                GameResult,
                GameResult.id == CanonicalRecommendationGrade.game_result_id,
            )
            .outerjoin(
                ModelVersion,
                ModelVersion.id == Recommendation.model_version_id,
            )
            .outerjoin(
                ModelRun,
                ModelRun.id == Recommendation.model_run_id,
            )
            .where(RecommendationEpisode.status == RecommendationEpisodeStatus.GRADED.value)
            .order_by(RecommendationEpisode.locked_at.desc(), RecommendationEpisode.id.desc())
        )
        session = self._session_factory()
        try:
            rows = session.execute(statement).all()
        except SQLAlchemyError as exc:
            raise CanonicalRecommendationReadError(
                "Canonical recommendation read-model query failed."
            ) from exc
        finally:
            session.close()

        return tuple(
            _to_record(
                episode=episode,
                stream=stream,
                snapshot=snapshot,
                grade=grade,
                result=result,
                model_version=model_version,
                model_run=model_run,
            )
            for episode, stream, snapshot, grade, result, model_version, model_run in rows
        )

    def list_episode_timeline(
        self,
        episode_id: UUID,
    ) -> tuple[RecommendationTimelineSnapshot, ...]:
        statement = (
            select(Recommendation)
            .where(Recommendation.recommendation_episode_id == episode_id)
            .order_by(Recommendation.recommendation_time.asc(), Recommendation.id.asc())
        )
        session = self._session_factory()
        try:
            snapshots = session.execute(statement).scalars().all()
        except SQLAlchemyError as exc:
            raise CanonicalRecommendationReadError(
                "Canonical recommendation timeline query failed."
            ) from exc
        finally:
            session.close()
        return tuple(_to_timeline_snapshot(snapshot) for snapshot in snapshots)


def _to_record(
    *,
    episode: RecommendationEpisode,
    stream: RecommendationStream,
    snapshot: Recommendation,
    grade: CanonicalRecommendationGrade,
    result: GameResult,
    model_version: ModelVersion | None,
    model_run: ModelRun | None,
) -> CanonicalRecommendationRecord:
    components = dict(snapshot.components or {})
    return CanonicalRecommendationRecord(
        episode_id=episode.id,
        stream_id=stream.id,
        sport=stream.sport,
        league_code=stream.league_code,
        provider=stream.provider,
        provider_game_id=stream.provider_game_id,
        market=stream.market,
        selection=episode.selection,
        selection_side=episode.selection_side,
        canonical_snapshot_id=snapshot.id,
        canonical_snapshot_time=snapshot.recommendation_time,
        canonical_market_line=snapshot.market_line,
        recommendation_tier=_extract_tier(components),
        confidence=snapshot.confidence,
        hammer_score=_extract_decimal(components, "hammer_score", "hammer", "hammer_rating"),
        model_probability=snapshot.projection,
        opened_at=episode.opened_at,
        locked_at=episode.locked_at,
        graded_at=grade.graded_at,
        canonical_grade_id=grade.id,
        grade_status=grade.grade_status,
        game_result_id=result.id,
        game_result_revision=grade.game_result_revision,
        result_status=result.status,
        winner_side=result.winner_side,
        total_score=result.total_score,
        model_version=stream.model_version,
        model_name=model_version.model_name if model_version is not None else None,
        git_commit=model_version.git_commit if model_version is not None else None,
        model_run_id=snapshot.model_run_id,
        run_source=model_run.source if model_run is not None else None,
        components=components,
        explanation=snapshot.explanation,
        source=snapshot.source,
    )


def _to_timeline_snapshot(snapshot: Recommendation) -> RecommendationTimelineSnapshot:
    components = dict(snapshot.components or {})
    return RecommendationTimelineSnapshot(
        snapshot_id=snapshot.id,
        recommendation_time=snapshot.recommendation_time,
        selection=snapshot.selection,
        market_line=snapshot.market_line,
        recommendation_tier=_extract_tier(components),
        confidence=snapshot.confidence,
        hammer_score=_extract_decimal(components, "hammer_score", "hammer", "hammer_rating"),
    )


def _extract_tier(components: dict[str, Any]) -> str | None:
    prediction = components.get("prediction")
    if isinstance(prediction, dict):
        for key in ("conviction_tier", "model_recommendation", "recommendation"):
            if prediction.get(key):
                return str(prediction[key])
    for key in ("tier", "recommendation_tier", "recommendation"):
        if components.get(key):
            return str(components[key])
    return None


def _extract_decimal(components: dict[str, Any], *keys: str) -> Decimal | None:
    for key in keys:
        value = components.get(key)
        if value not in (None, ""):
            try:
                return Decimal(str(value))
            except Exception:
                return None
    prediction = components.get("prediction")
    if isinstance(prediction, dict):
        value = prediction.get("hammer_score")
        if value not in (None, ""):
            try:
                return Decimal(str(value))
            except Exception:
                return None
    return None
