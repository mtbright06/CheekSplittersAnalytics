from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.database.session import SessionLocal
from app.models import GameResult, Recommendation, RecommendationGrade


GRADE_PENDING = "PENDING"
GRADE_WIN = "WIN"
GRADE_LOSS = "LOSS"
GRADE_PUSH = "PUSH"
GRADE_VOID = "VOID"
GRADE_UNGRADEABLE = "UNGRADEABLE"


class PredictionSnapshotGradingError(RuntimeError):
    """Raised when an immutable prediction evaluation cannot be persisted."""


@dataclass(frozen=True)
class SavedPredictionSnapshotGrade:
    grade_id: UUID
    prediction_snapshot_id: UUID
    game_result_id: UUID
    game_result_revision: int
    grade_status: str
    grading_version: int
    created: bool


class PredictionSnapshotGradingService:
    """Grades a persisted snapshot against one authoritative GameResult revision."""

    def __init__(
        self,
        session_factory: sessionmaker[Session] = SessionLocal,
        *,
        now_factory: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._session_factory = session_factory
        self._now_factory = now_factory

    def grade(
        self,
        *,
        prediction_snapshot_id: UUID,
        game_result_id: UUID,
        grading_version: int = 1,
    ) -> SavedPredictionSnapshotGrade:
        if grading_version < 1:
            raise ValueError("grading_version must be at least 1.")

        session = self._session_factory()
        try:
            with session.begin():
                snapshot = session.get(Recommendation, prediction_snapshot_id)
                result = session.get(GameResult, game_result_id)
                if snapshot is None:
                    raise ValueError(f"PredictionSnapshot {prediction_snapshot_id} does not exist.")
                if result is None:
                    raise ValueError(f"GameResult {game_result_id} does not exist.")

                existing = self._find_existing(
                    session,
                    prediction_snapshot_id=prediction_snapshot_id,
                    game_result_id=game_result_id,
                    game_result_revision=result.revision,
                )
                if existing is not None:
                    return self._saved(existing, created=False)

                grade = RecommendationGrade(
                    prediction_snapshot_id=prediction_snapshot_id,
                    game_result_id=game_result_id,
                    game_result_revision=result.revision,
                    grade_status=determine_grade_status(snapshot, result),
                    graded_at=_ensure_utc(self._now_factory()),
                    grading_version=grading_version,
                )
                session.add(grade)
                session.flush()
                return self._saved(grade, created=True)
        except ValueError:
            session.rollback()
            raise
        except SQLAlchemyError as exc:
            session.rollback()
            raise PredictionSnapshotGradingError(
                "PredictionSnapshot grading failed; no partial grade was saved."
            ) from exc
        finally:
            session.close()

    @staticmethod
    def _find_existing(
        session: Session,
        *,
        prediction_snapshot_id: UUID,
        game_result_id: UUID,
        game_result_revision: int,
    ) -> RecommendationGrade | None:
        return session.execute(
            select(RecommendationGrade).where(
                RecommendationGrade.prediction_snapshot_id == prediction_snapshot_id,
                RecommendationGrade.game_result_id == game_result_id,
                RecommendationGrade.game_result_revision == game_result_revision,
            )
        ).scalar_one_or_none()

    @staticmethod
    def _saved(
        grade: RecommendationGrade,
        *,
        created: bool,
    ) -> SavedPredictionSnapshotGrade:
        return SavedPredictionSnapshotGrade(
            grade_id=grade.id,
            prediction_snapshot_id=grade.prediction_snapshot_id,
            game_result_id=grade.game_result_id,
            game_result_revision=grade.game_result_revision,
            grade_status=grade.grade_status,
            grading_version=grade.grading_version,
            created=created,
        )


def determine_grade_status(snapshot: Recommendation, result: GameResult) -> str:
    """Evaluate only immutable prediction fields against objective game truth."""

    selection = _normalized(snapshot.selection)
    if selection in {"", "NONE"}:
        return GRADE_UNGRADEABLE

    result_status = _normalized(result.status)
    if result_status in {"POSTPONED", "CANCELED"}:
        return GRADE_VOID
    if result_status != "FINAL":
        return GRADE_PENDING

    market = _normalized(snapshot.market_type)
    if market in {"MONEYLINE", "MONEY LINE", "ML"}:
        return _grade_moneyline(_selection_side(snapshot), _normalized(result.winner_side))
    if market in {"TOTAL", "TOTALS"}:
        return _grade_total(selection, snapshot.market_line, result.total_score)
    return GRADE_UNGRADEABLE


def _selection_side(snapshot: Recommendation) -> str:
    selection = _normalized(snapshot.selection)
    if selection in {"HOME", "AWAY"}:
        return selection
    components = snapshot.components if isinstance(snapshot.components, dict) else {}
    identity = components.get("identity") if isinstance(components, dict) else None
    side = identity.get("selection_side") if isinstance(identity, dict) else None
    return _normalized(side)


def _grade_moneyline(selection: str, winner_side: str) -> str:
    if selection not in {"HOME", "AWAY"}:
        return GRADE_UNGRADEABLE
    if winner_side == selection:
        return GRADE_WIN
    if winner_side in {"HOME", "AWAY"}:
        return GRADE_LOSS
    if winner_side == "TIE":
        return GRADE_PUSH
    return GRADE_UNGRADEABLE


def _grade_total(
    selection: str,
    market_line: Decimal | None,
    total_score: int | None,
) -> str:
    direction = selection.split(" ", 1)[0]
    if direction not in {"OVER", "UNDER"} or market_line is None or total_score is None:
        return GRADE_UNGRADEABLE
    try:
        line = Decimal(str(market_line))
    except (InvalidOperation, TypeError, ValueError):
        return GRADE_UNGRADEABLE

    total = Decimal(total_score)
    if total == line:
        return GRADE_PUSH
    if direction == "OVER":
        return GRADE_WIN if total > line else GRADE_LOSS
    return GRADE_WIN if total < line else GRADE_LOSS


def _normalized(value: object) -> str:
    return " ".join(str(value or "").strip().upper().split())


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
