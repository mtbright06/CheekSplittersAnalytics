from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.database.session import SessionLocal
from app.models import GameResult, Recommendation, RecommendationEpisode, RecommendationStream
from app.models.recommendation_episode import (
    RecommendationEpisodeClosureReason,
    RecommendationEpisodeStatus,
)


STARTED_OR_TERMINAL_STATUSES = {"LIVE", "FINAL", "SUSPENDED", "CANCELED", "INCOMPLETE"}
TERMINAL_STATUSES = {"FINAL", "CANCELED"}
UNVERIFIED_STATUSES = {"", "SCHEDULED", "POSTPONED"}


class RecommendationEpisodeLockError(RuntimeError):
    """Raised when canonical episode locking cannot complete atomically."""


@dataclass(frozen=True)
class EpisodeLockResult:
    stream_id: UUID
    episode_id: UUID | None
    canonical_snapshot_id: UUID | None
    status: str
    locked: bool
    created: bool


class RecommendationEpisodeLockService:
    """Locks the final active actionable recommendation episode for a stream."""

    def __init__(
        self,
        session_factory: sessionmaker[Session] = SessionLocal,
        *,
        now_factory: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._session_factory = session_factory
        self._now_factory = now_factory

    def lock_stream(
        self,
        *,
        stream_id: UUID,
        game_result_id: UUID | None = None,
    ) -> EpisodeLockResult:
        session = self._session_factory()
        try:
            with session.begin():
                stream = self._locked_stream(session, stream_id)
                if stream is None:
                    raise ValueError(f"RecommendationStream {stream_id} does not exist.")
                result = session.get(GameResult, game_result_id) if game_result_id else None
                return self.lock_stream_in_session(
                    session=session,
                    stream=stream,
                    result=result,
                )
        except ValueError:
            session.rollback()
            raise
        except SQLAlchemyError as exc:
            session.rollback()
            raise RecommendationEpisodeLockError(
                "Recommendation episode locking failed; no partial lock was saved."
            ) from exc
        finally:
            session.close()

    def lock_stream_in_session(
        self,
        *,
        session: Session,
        stream: RecommendationStream,
        result: GameResult | None = None,
    ) -> EpisodeLockResult:
        existing = self._locked_or_graded_episode(session, stream.id)
        if existing is not None:
            return EpisodeLockResult(
                stream_id=stream.id,
                episode_id=existing.id,
                canonical_snapshot_id=existing.canonical_snapshot_id,
                status=existing.status,
                locked=True,
                created=False,
            )

        active = self._active_episode(session, stream.id)
        if active is None:
            return EpisodeLockResult(stream.id, None, None, "NO_ACTIONABLE_EPISODE", False, False)

        lockable, void = self._lock_state(stream, result)
        if not lockable:
            return EpisodeLockResult(stream.id, active.id, None, active.status, False, False)

        if void:
            active.status = RecommendationEpisodeStatus.VOID.value
            active.closed_at = _ensure_utc(self._now_factory())
            active.locked_at = active.closed_at
            active.closure_reason = RecommendationEpisodeClosureReason.CANCELED.value
            session.flush()
            return EpisodeLockResult(stream.id, active.id, None, active.status, True, True)

        canonical = self._latest_eligible_snapshot(session, active, stream.scheduled_start_at)
        if canonical is None:
            return EpisodeLockResult(stream.id, active.id, None, "NO_ELIGIBLE_SNAPSHOT", False, False)

        active.canonical_snapshot_id = canonical.id
        active.status = RecommendationEpisodeStatus.LOCKED.value
        active.locked_at = _ensure_utc(self._now_factory())
        active.closure_reason = RecommendationEpisodeClosureReason.GAME_LOCKED.value
        session.flush()
        return EpisodeLockResult(
            stream_id=stream.id,
            episode_id=active.id,
            canonical_snapshot_id=canonical.id,
            status=active.status,
            locked=True,
            created=True,
        )

    @staticmethod
    def _locked_stream(session: Session, stream_id: UUID) -> RecommendationStream | None:
        return session.execute(
            select(RecommendationStream)
            .where(RecommendationStream.id == stream_id)
            .with_for_update()
        ).scalar_one_or_none()

    @staticmethod
    def _locked_or_graded_episode(
        session: Session,
        stream_id: UUID,
    ) -> RecommendationEpisode | None:
        return session.execute(
            select(RecommendationEpisode)
            .where(
                RecommendationEpisode.recommendation_stream_id == stream_id,
                RecommendationEpisode.status.in_(
                    [
                        RecommendationEpisodeStatus.LOCKED.value,
                        RecommendationEpisodeStatus.GRADED.value,
                        RecommendationEpisodeStatus.VOID.value,
                    ]
                ),
            )
            .with_for_update()
            .order_by(RecommendationEpisode.locked_at.desc().nullslast())
        ).scalar_one_or_none()

    @staticmethod
    def _active_episode(session: Session, stream_id: UUID) -> RecommendationEpisode | None:
        return session.execute(
            select(RecommendationEpisode)
            .where(
                RecommendationEpisode.recommendation_stream_id == stream_id,
                RecommendationEpisode.status == RecommendationEpisodeStatus.ACTIVE.value,
            )
            .with_for_update()
        ).scalar_one_or_none()

    @staticmethod
    def _latest_eligible_snapshot(
        session: Session,
        episode: RecommendationEpisode,
        scheduled_start_at: datetime | None,
    ) -> Recommendation | None:
        if scheduled_start_at is None:
            return None
        return session.execute(
            select(Recommendation)
            .where(
                Recommendation.recommendation_episode_id == episode.id,
                Recommendation.recommendation_time < scheduled_start_at,
            )
            .order_by(Recommendation.recommendation_time.desc(), Recommendation.created_at.desc())
            .with_for_update()
        ).scalars().first()

    def _lock_state(
        self,
        stream: RecommendationStream,
        result: GameResult | None,
    ) -> tuple[bool, bool]:
        if result is not None:
            status = _normalize(result.status)
            if status == "CANCELED":
                return True, True
            if status in STARTED_OR_TERMINAL_STATUSES:
                return True, False
            if status in UNVERIFIED_STATUSES:
                return self._scheduled_start_passed(stream), False
            return False, False
        return self._scheduled_start_passed(stream), False

    def _scheduled_start_passed(self, stream: RecommendationStream) -> bool:
        if stream.scheduled_start_at is None:
            return False
        return _ensure_utc(stream.scheduled_start_at) <= _ensure_utc(self._now_factory())


def _normalize(value: object) -> str:
    return " ".join(str(value or "").strip().upper().split())


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
