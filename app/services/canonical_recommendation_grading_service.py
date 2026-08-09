from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.database.session import SessionLocal
from app.models import (
    CanonicalRecommendationGrade,
    GameResult,
    RecommendationEpisode,
    RecommendationStream,
)
from app.models.recommendation_episode import RecommendationEpisodeStatus
from app.services.prediction_snapshot_grading_service import (
    GRADE_PENDING,
    GRADE_VOID,
    determine_grade_status,
)
from app.services.recommendation_episode_lock_service import RecommendationEpisodeLockService


TERMINAL_RESULT_STATUSES = {"FINAL", "CANCELED"}


class CanonicalRecommendationGradingError(RuntimeError):
    """Raised when canonical episode grading cannot complete atomically."""


@dataclass(frozen=True)
class SavedCanonicalRecommendationGrade:
    grade_id: UUID | None
    recommendation_episode_id: UUID
    canonical_snapshot_id: UUID | None
    game_result_id: UUID
    game_result_revision: int | None
    grade_status: str
    grading_version: int
    created: bool


class CanonicalRecommendationGradingService:
    """Grades one locked canonical episode against authoritative game truth."""

    def __init__(
        self,
        session_factory: sessionmaker[Session] = SessionLocal,
        *,
        lock_service: RecommendationEpisodeLockService | None = None,
        now_factory: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._session_factory = session_factory
        self._lock_service = lock_service or RecommendationEpisodeLockService(
            session_factory,
            now_factory=now_factory,
        )
        self._now_factory = now_factory

    def grade_for_result(
        self,
        *,
        league_code: str,
        provider_game_id: str,
        game_result_id: UUID,
        grading_version: int = 1,
    ) -> tuple[int, int, int]:
        session = self._session_factory()
        try:
            with session.begin():
                result = session.get(GameResult, game_result_id)
                if result is None:
                    raise ValueError(f"GameResult {game_result_id} does not exist.")
                matching_streams = session.execute(
                    select(RecommendationStream)
                    .where(
                        RecommendationStream.league_code == league_code.upper(),
                        RecommendationStream.provider_game_id == str(provider_game_id),
                    )
                    .with_for_update()
                ).scalars().all()

                created = reused = unmatched = 0
                for stream in matching_streams:
                    lock = self._lock_service.lock_stream_in_session(
                        session=session,
                        stream=stream,
                        result=result,
                    )
                    if lock.episode_id is None:
                        unmatched += 1
                        continue
                    saved = self.grade_episode_in_session(
                        session=session,
                        recommendation_episode_id=lock.episode_id,
                        game_result=result,
                        grading_version=grading_version,
                    )
                    if saved.grade_status == GRADE_PENDING:
                        continue
                    if saved.created:
                        created += 1
                    elif saved.grade_id is not None:
                        reused += 1
                if not matching_streams:
                    unmatched = 1
                return created, reused, unmatched
        except ValueError:
            session.rollback()
            raise
        except IntegrityError:
            session.rollback()
            return self.grade_for_result(
                league_code=league_code,
                provider_game_id=provider_game_id,
                game_result_id=game_result_id,
                grading_version=grading_version,
            )
        except SQLAlchemyError as exc:
            session.rollback()
            raise CanonicalRecommendationGradingError(
                "Canonical recommendation grading failed; no partial grade was saved."
            ) from exc
        finally:
            session.close()

    def grade_episode(
        self,
        *,
        recommendation_episode_id: UUID,
        game_result_id: UUID,
        grading_version: int = 1,
    ) -> SavedCanonicalRecommendationGrade:
        session = self._session_factory()
        try:
            with session.begin():
                result = session.get(GameResult, game_result_id)
                if result is None:
                    raise ValueError(f"GameResult {game_result_id} does not exist.")
                return self.grade_episode_in_session(
                    session=session,
                    recommendation_episode_id=recommendation_episode_id,
                    game_result=result,
                    grading_version=grading_version,
                )
        except ValueError:
            session.rollback()
            raise
        except IntegrityError:
            session.rollback()
            session = self._session_factory()
            try:
                with session.begin():
                    existing = self._find_existing(session, recommendation_episode_id)
                    if existing is not None:
                        return self._saved(existing, created=False)
                raise
            finally:
                session.close()
        except SQLAlchemyError as exc:
            session.rollback()
            raise CanonicalRecommendationGradingError(
                "Canonical recommendation grading failed; no partial grade was saved."
            ) from exc
        finally:
            session.close()

    def grade_episode_in_session(
        self,
        *,
        session: Session,
        recommendation_episode_id: UUID,
        game_result: GameResult,
        grading_version: int = 1,
    ) -> SavedCanonicalRecommendationGrade:
        if grading_version < 1:
            raise ValueError("grading_version must be at least 1.")

        episode = session.execute(
            select(RecommendationEpisode)
            .where(RecommendationEpisode.id == recommendation_episode_id)
            .with_for_update()
        ).scalar_one_or_none()
        if episode is None:
            raise ValueError(f"RecommendationEpisode {recommendation_episode_id} does not exist.")

        existing = self._find_existing(session, recommendation_episode_id)
        if existing is not None:
            return self._saved(existing, created=False)

        if episode.status == RecommendationEpisodeStatus.VOID.value:
            return self._pending_result(episode, game_result, GRADE_VOID, grading_version)
        if (
            episode.status != RecommendationEpisodeStatus.LOCKED.value
            or episode.canonical_snapshot_id is None
            or episode.canonical_snapshot is None
        ):
            return self._pending_result(episode, game_result, GRADE_PENDING, grading_version)
        if _normalize(game_result.status) not in TERMINAL_RESULT_STATUSES:
            return self._pending_result(episode, game_result, GRADE_PENDING, grading_version)

        grade_status = determine_grade_status(episode.canonical_snapshot, game_result)
        if grade_status == GRADE_PENDING:
            return self._pending_result(episode, game_result, grade_status, grading_version)
        if grade_status == GRADE_VOID:
            episode.status = RecommendationEpisodeStatus.VOID.value
            session.flush()
            return self._pending_result(episode, game_result, grade_status, grading_version)

        grade = CanonicalRecommendationGrade(
            recommendation_episode_id=episode.id,
            canonical_snapshot_id=episode.canonical_snapshot_id,
            game_result_id=game_result.id,
            game_result_revision=game_result.revision,
            grade_status=grade_status,
            graded_at=_ensure_utc(self._now_factory()),
            grading_version=grading_version,
        )
        session.add(grade)
        episode.status = RecommendationEpisodeStatus.GRADED.value
        session.flush()
        return self._saved(grade, created=True)

    @staticmethod
    def _find_existing(
        session: Session,
        recommendation_episode_id: UUID,
    ) -> CanonicalRecommendationGrade | None:
        return session.execute(
            select(CanonicalRecommendationGrade).where(
                CanonicalRecommendationGrade.recommendation_episode_id
                == recommendation_episode_id
            )
        ).scalar_one_or_none()

    @staticmethod
    def _saved(
        grade: CanonicalRecommendationGrade,
        *,
        created: bool,
    ) -> SavedCanonicalRecommendationGrade:
        return SavedCanonicalRecommendationGrade(
            grade_id=grade.id,
            recommendation_episode_id=grade.recommendation_episode_id,
            canonical_snapshot_id=grade.canonical_snapshot_id,
            game_result_id=grade.game_result_id,
            game_result_revision=grade.game_result_revision,
            grade_status=grade.grade_status,
            grading_version=grade.grading_version,
            created=created,
        )

    @staticmethod
    def _pending_result(
        episode: RecommendationEpisode,
        game_result: GameResult,
        status: str,
        grading_version: int,
    ) -> SavedCanonicalRecommendationGrade:
        return SavedCanonicalRecommendationGrade(
            grade_id=None,
            recommendation_episode_id=episode.id,
            canonical_snapshot_id=episode.canonical_snapshot_id,
            game_result_id=game_result.id,
            game_result_revision=game_result.revision,
            grade_status=status,
            grading_version=grading_version,
            created=False,
        )


def _normalize(value: object) -> str:
    return " ".join(str(value or "").strip().upper().split())


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
