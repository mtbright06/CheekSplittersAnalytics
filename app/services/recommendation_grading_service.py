from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.database.session import SessionLocal
from app.models import Recommendation, RecommendationGrade


VALID_OUTCOMES = frozenset({"WIN", "LOSS", "PUSH", "VOID"})


class RecommendationGradingError(RuntimeError):
    """Base error for recommendation grading failures."""


class RecommendationGradingValidationError(RecommendationGradingError):
    """Raised when a grade request is invalid."""


@dataclass(frozen=True, slots=True)
class GradeInput:
    recommendation_id: UUID
    outcome: str
    american_odds: int | None = None
    stake_units: Decimal | int | float | str = Decimal("1")
    actual_home_score: Decimal | int | float | str | None = None
    actual_away_score: Decimal | int | float | str | None = None
    graded_at: datetime | None = None
    source: str = "manual"
    notes: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SavedGrade:
    grade_id: UUID
    recommendation_id: UUID
    outcome: str
    american_odds: int | None
    stake_units: Decimal
    profit_units: Decimal
    graded_at: datetime


def calculate_profit_units(
    *,
    outcome: str,
    american_odds: int | None,
    stake_units: Decimal | int | float | str = Decimal("1"),
) -> Decimal:
    """Return net profit in units for one settled wager.

    WIN uses American-odds payout, LOSS returns negative stake, and PUSH/VOID
    return zero. Odds are required only for a win.
    """

    normalized_outcome = outcome.strip().upper()
    if normalized_outcome not in VALID_OUTCOMES:
        raise RecommendationGradingValidationError(
            f"Unsupported outcome {outcome!r}. Expected WIN, LOSS, PUSH, or VOID."
        )

    stake = _to_decimal(stake_units, "stake_units")
    if stake <= 0:
        raise RecommendationGradingValidationError("stake_units must be positive.")

    if normalized_outcome == "LOSS":
        return (-stake).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    if normalized_outcome in {"PUSH", "VOID"}:
        return Decimal("0.0000")

    if american_odds is None or american_odds == 0:
        raise RecommendationGradingValidationError(
            "american_odds is required and cannot be zero for a winning grade."
        )

    if american_odds > 0:
        profit = stake * Decimal(american_odds) / Decimal("100")
    else:
        profit = stake * Decimal("100") / Decimal(abs(american_odds))

    return profit.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


class RecommendationGradingService:
    """Adds append-only settlement records to recommendation history."""

    def __init__(
        self,
        session_factory: sessionmaker[Session] = SessionLocal,
    ) -> None:
        self._session_factory = session_factory

    def grade(self, grade_input: GradeInput) -> SavedGrade:
        outcome = grade_input.outcome.strip().upper()
        stake_units = _to_decimal(grade_input.stake_units, "stake_units")
        source = grade_input.source.strip()
        if not source:
            raise RecommendationGradingValidationError("source is required.")

        graded_at = _ensure_aware_datetime(grade_input.graded_at or datetime.now(UTC))
        home_score = _to_optional_decimal(grade_input.actual_home_score, "actual_home_score")
        away_score = _to_optional_decimal(grade_input.actual_away_score, "actual_away_score")

        session = self._session_factory()
        try:
            recommendation = session.execute(
                select(Recommendation).where(
                    Recommendation.id == grade_input.recommendation_id
                )
            ).scalar_one_or_none()

            if recommendation is None:
                raise RecommendationGradingValidationError(
                    f"Recommendation {grade_input.recommendation_id} does not exist."
                )

            american_odds = grade_input.american_odds
            if american_odds is None:
                american_odds = _extract_american_odds(recommendation.components)

            profit_units = calculate_profit_units(
                outcome=outcome,
                american_odds=american_odds,
                stake_units=stake_units,
            )

            grade = RecommendationGrade(
                recommendation_id=recommendation.id,
                outcome=outcome,
                american_odds=american_odds,
                stake_units=stake_units,
                profit_units=profit_units,
                actual_home_score=home_score,
                actual_away_score=away_score,
                graded_at=graded_at,
                source=source,
                notes=_clean_optional(grade_input.notes),
                grade_metadata=dict(grade_input.metadata),
            )
            session.add(grade)
            session.commit()

            return SavedGrade(
                grade_id=grade.id,
                recommendation_id=grade.recommendation_id,
                outcome=grade.outcome,
                american_odds=grade.american_odds,
                stake_units=grade.stake_units,
                profit_units=grade.profit_units,
                graded_at=grade.graded_at,
            )

        except RecommendationGradingError:
            session.rollback()
            raise
        except SQLAlchemyError as exc:
            session.rollback()
            raise RecommendationGradingError(
                "Database operation failed while grading recommendation."
            ) from exc
        except Exception as exc:
            session.rollback()
            raise RecommendationGradingError(
                "Unexpected failure while grading recommendation."
            ) from exc
        finally:
            session.close()


def _extract_american_odds(components: dict[str, Any] | None) -> int | None:
    if not isinstance(components, dict):
        return None

    candidates = [
        components.get("american_odds"),
        (components.get("odds_snapshot") or {}).get("american_odds")
        if isinstance(components.get("odds_snapshot"), dict)
        else None,
        (components.get("market_edge_snapshot") or {}).get("american_odds")
        if isinstance(components.get("market_edge_snapshot"), dict)
        else None,
    ]

    for candidate in candidates:
        if candidate in (None, ""):
            continue
        try:
            value = int(candidate)
        except (TypeError, ValueError):
            continue
        if value != 0:
            return value

    return None


def _to_decimal(value: Decimal | int | float | str, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise RecommendationGradingValidationError(
            f"{field_name} must be numeric."
        ) from exc


def _to_optional_decimal(
    value: Decimal | int | float | str | None,
    field_name: str,
) -> Decimal | None:
    if value is None:
        return None
    return _to_decimal(value, field_name)


def _ensure_aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise RecommendationGradingValidationError(
            "graded_at must include timezone information."
        )
    return value


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
