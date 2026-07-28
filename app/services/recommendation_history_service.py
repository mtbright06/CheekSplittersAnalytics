from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from sqlalchemy import Numeric, Select, cast, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, aliased, sessionmaker

from app.database.session import SessionLocal
from app.models import (
    Game,
    League,
    ModelRun,
    ModelVersion,
    Recommendation,
    LegacyRecommendationSettlement,
)


class RecommendationHistoryError(RuntimeError):
    """Base error for recommendation-history query failures."""


class RecommendationHistoryValidationError(RecommendationHistoryError):
    """Raised when recommendation-history filters are invalid."""


@dataclass(frozen=True, slots=True)
class RecommendationHistoryFilters:
    start_time: datetime | None = None
    end_time: datetime | None = None
    league_code: str | None = None
    sport: str | None = None
    market_type: str | None = None
    selection: str | None = None
    tier: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    outcome: str | None = None
    graded: bool | None = None
    minimum_confidence: Decimal | int | float | str | None = None
    maximum_confidence: Decimal | int | float | str | None = None
    minimum_hammer: Decimal | int | float | str | None = None
    maximum_hammer: Decimal | int | float | str | None = None


@dataclass(frozen=True, slots=True)
class ModelRunHistoryFilters:
    start_time: datetime | None = None
    end_time: datetime | None = None
    model_name: str | None = None
    model_version: str | None = None
    status: str | None = None
    source: str | None = None


@dataclass(frozen=True, slots=True)
class LatestGradeView:
    grade_id: UUID
    outcome: str
    american_odds: int | None
    stake_units: Decimal
    profit_units: Decimal
    actual_home_score: Decimal | None
    actual_away_score: Decimal | None
    graded_at: datetime
    source: str
    notes: str | None
    grade_metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RecommendationHistoryItem:
    recommendation_id: UUID
    recommendation_time: datetime

    league_code: str
    league_name: str
    sport: str

    game_id: UUID
    external_game_id: str
    scheduled_start: datetime
    game_status: str

    model_name: str
    model_version: str
    git_commit: str

    model_run_id: UUID | None
    run_label: str | None
    run_source: str | None

    market_type: str
    selection: str
    market_line: Decimal | None
    projection: Decimal
    edge: Decimal | None
    confidence: Decimal

    tier: str | None
    hammer_score: Decimal | None
    signal_combination: str | None
    real_market_loaded: bool | None

    components: dict[str, Any]
    explanation: str | None
    source: str

    latest_grade: LatestGradeView | None


@dataclass(frozen=True, slots=True)
class ModelRunHistoryItem:
    model_run_id: UUID
    model_version_id: UUID
    model_name: str
    model_version: str
    git_commit: str
    started_at: datetime
    completed_at: datetime | None
    status: str
    source: str
    run_label: str | None
    notes: str | None
    run_metadata: dict[str, Any]


class RecommendationHistoryService:
    """
    Database-backed read service for immutable recommendation history.

    The service returns stable dataclass views rather than exposing live ORM
    records to CLI, reporting, API, or future dashboard consumers.

    Recommendation grades are append-only. When multiple grades exist for one
    recommendation, the latest grade is selected by:

    1. graded_at descending,
    2. created_at descending,
    3. id descending.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session] = SessionLocal,
    ) -> None:
        self._session_factory = session_factory

    def list_recommendations(
        self,
        *,
        filters: RecommendationHistoryFilters | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[RecommendationHistoryItem, ...]:
        normalized_filters = self._normalize_recommendation_filters(
            filters or RecommendationHistoryFilters()
        )
        self._validate_pagination(limit=limit, offset=offset)

        statement = self._build_recommendation_statement(
            filters=normalized_filters,
            limit=limit,
            offset=offset,
        )

        session = self._session_factory()

        try:
            rows = session.execute(statement).all()

            return tuple(
                self._to_recommendation_history_item(
                    recommendation=recommendation,
                    game=game,
                    league=league,
                    model_version=model_version,
                    model_run=model_run,
                    latest_grade=latest_grade,
                )
                for (
                    recommendation,
                    game,
                    league,
                    model_version,
                    model_run,
                    latest_grade,
                ) in rows
            )

        except SQLAlchemyError as exc:
            raise RecommendationHistoryError(
                "Database operation failed while querying recommendation history."
            ) from exc

        finally:
            session.close()

    def list_model_runs(
        self,
        *,
        filters: ModelRunHistoryFilters | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[ModelRunHistoryItem, ...]:
        normalized_filters = self._normalize_model_run_filters(
            filters or ModelRunHistoryFilters()
        )
        self._validate_pagination(limit=limit, offset=offset)

        statement = (
            select(ModelRun, ModelVersion)
            .join(
                ModelVersion,
                ModelVersion.id == ModelRun.model_version_id,
            )
            .order_by(
                ModelRun.started_at.desc(),
                ModelRun.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        if normalized_filters.start_time is not None:
            statement = statement.where(
                ModelRun.started_at >= normalized_filters.start_time
            )

        if normalized_filters.end_time is not None:
            statement = statement.where(
                ModelRun.started_at < normalized_filters.end_time
            )

        if normalized_filters.model_name is not None:
            statement = statement.where(
                func.upper(ModelVersion.model_name)
                == normalized_filters.model_name
            )

        if normalized_filters.model_version is not None:
            statement = statement.where(
                ModelVersion.version == normalized_filters.model_version
            )

        if normalized_filters.status is not None:
            statement = statement.where(
                func.upper(ModelRun.status) == normalized_filters.status
            )

        if normalized_filters.source is not None:
            statement = statement.where(
                func.upper(ModelRun.source) == normalized_filters.source
            )

        session = self._session_factory()

        try:
            rows = session.execute(statement).all()

            return tuple(
                ModelRunHistoryItem(
                    model_run_id=model_run.id,
                    model_version_id=model_version.id,
                    model_name=model_version.model_name,
                    model_version=model_version.version,
                    git_commit=model_version.git_commit,
                    started_at=model_run.started_at,
                    completed_at=model_run.completed_at,
                    status=model_run.status,
                    source=model_run.source,
                    run_label=model_run.run_label,
                    notes=model_run.notes,
                    run_metadata=dict(model_run.run_metadata or {}),
                )
                for model_run, model_version in rows
            )

        except SQLAlchemyError as exc:
            raise RecommendationHistoryError(
                "Database operation failed while querying model-run history."
            ) from exc

        finally:
            session.close()

    @classmethod
    def _build_recommendation_statement(
        cls,
        *,
        filters: RecommendationHistoryFilters,
        limit: int,
        offset: int,
    ) -> Select[Any]:
        ranked_grades = (
            select(
                LegacyRecommendationSettlement.id.label("grade_id"),
                LegacyRecommendationSettlement.recommendation_id.label(
                    "recommendation_id"
                ),
                func.row_number()
                .over(
                    partition_by=LegacyRecommendationSettlement.recommendation_id,
                    order_by=(
                        LegacyRecommendationSettlement.graded_at.desc(),
                        LegacyRecommendationSettlement.created_at.desc(),
                        LegacyRecommendationSettlement.id.desc(),
                    ),
                )
                .label("grade_rank"),
            )
            .subquery("ranked_recommendation_grades")
        )

        latest_grade = aliased(
                LegacyRecommendationSettlement,
            name="latest_recommendation_grade",
        )

        statement = (
            select(
                Recommendation,
                Game,
                League,
                ModelVersion,
                ModelRun,
                latest_grade,
            )
            .join(
                Game,
                Game.id == Recommendation.game_id,
            )
            .join(
                League,
                League.id == Game.league_id,
            )
            .join(
                ModelVersion,
                ModelVersion.id == Recommendation.model_version_id,
            )
            .outerjoin(
                ModelRun,
                ModelRun.id == Recommendation.model_run_id,
            )
            .outerjoin(
                ranked_grades,
                (
                    ranked_grades.c.recommendation_id
                    == Recommendation.id
                )
                & (ranked_grades.c.grade_rank == 1),
            )
            .outerjoin(
                latest_grade,
                latest_grade.id == ranked_grades.c.grade_id,
            )
            .order_by(
                Recommendation.recommendation_time.desc(),
                Recommendation.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        if filters.start_time is not None:
            statement = statement.where(
                Recommendation.recommendation_time >= filters.start_time
            )

        if filters.end_time is not None:
            statement = statement.where(
                Recommendation.recommendation_time < filters.end_time
            )

        if filters.league_code is not None:
            statement = statement.where(
                func.upper(League.code) == filters.league_code
            )

        if filters.sport is not None:
            statement = statement.where(
                func.upper(League.sport) == filters.sport
            )

        if filters.market_type is not None:
            statement = statement.where(
                func.upper(Recommendation.market_type)
                == filters.market_type
            )

        if filters.selection is not None:
            statement = statement.where(
                func.upper(Recommendation.selection)
                == filters.selection
            )

        if filters.model_name is not None:
            statement = statement.where(
                func.upper(ModelVersion.model_name)
                == filters.model_name
            )

        if filters.model_version is not None:
            statement = statement.where(
                ModelVersion.version == filters.model_version
            )

        if filters.outcome is not None:
            statement = statement.where(
                latest_grade.outcome == filters.outcome
            )

        if filters.graded is True:
            statement = statement.where(
                latest_grade.id.is_not(None)
            )

        if filters.graded is False:
            statement = statement.where(
                latest_grade.id.is_(None)
            )

        if filters.minimum_confidence is not None:
            statement = statement.where(
                Recommendation.confidence
                >= filters.minimum_confidence
            )

        if filters.maximum_confidence is not None:
            statement = statement.where(
                Recommendation.confidence
                <= filters.maximum_confidence
            )

        tier_expression = func.upper(
            func.coalesce(
                Recommendation.components["tier"].as_string(),
                Recommendation.components[
                    "recommendation_tier"
                ].as_string(),
                Recommendation.components[
                    "recommendation"
                ].as_string(),
            )
        )

        if filters.tier is not None:
            statement = statement.where(
                tier_expression == filters.tier
            )

        hammer_expression = cast(
            func.coalesce(
                Recommendation.components[
                    "hammer_score"
                ].as_string(),
                Recommendation.components["hammer"].as_string(),
                Recommendation.components[
                    "hammer_rating"
                ].as_string(),
            ),
            Numeric(10, 3),
        )

        if filters.minimum_hammer is not None:
            statement = statement.where(
                hammer_expression >= filters.minimum_hammer
            )

        if filters.maximum_hammer is not None:
            statement = statement.where(
                hammer_expression <= filters.maximum_hammer
            )

        return statement

    @classmethod
    def _to_recommendation_history_item(
        cls,
        *,
        recommendation: Recommendation,
        game: Game,
        league: League,
        model_version: ModelVersion,
        model_run: ModelRun | None,
        latest_grade: LegacyRecommendationSettlement | None,
    ) -> RecommendationHistoryItem:
        components = dict(recommendation.components or {})

        grade_view = None

        if latest_grade is not None:
            grade_view = LatestGradeView(
                grade_id=latest_grade.id,
                outcome=latest_grade.outcome,
                american_odds=latest_grade.american_odds,
                stake_units=latest_grade.stake_units,
                profit_units=latest_grade.profit_units,
                actual_home_score=latest_grade.actual_home_score,
                actual_away_score=latest_grade.actual_away_score,
                graded_at=latest_grade.graded_at,
                source=latest_grade.source,
                notes=latest_grade.notes,
                grade_metadata=dict(
                    latest_grade.grade_metadata or {}
                ),
            )

        return RecommendationHistoryItem(
            recommendation_id=recommendation.id,
            recommendation_time=recommendation.recommendation_time,
            league_code=league.code,
            league_name=league.name,
            sport=league.sport,
            game_id=game.id,
            external_game_id=game.external_game_id,
            scheduled_start=game.scheduled_start,
            game_status=game.status,
            model_name=model_version.model_name,
            model_version=model_version.version,
            git_commit=model_version.git_commit,
            model_run_id=(
                model_run.id
                if model_run is not None
                else recommendation.model_run_id
            ),
            run_label=(
                model_run.run_label
                if model_run is not None
                else None
            ),
            run_source=(
                model_run.source
                if model_run is not None
                else None
            ),
            market_type=recommendation.market_type,
            selection=recommendation.selection,
            market_line=recommendation.market_line,
            projection=recommendation.projection,
            edge=recommendation.edge,
            confidence=recommendation.confidence,
            tier=cls._extract_tier(components),
            hammer_score=cls._extract_hammer_score(components),
            signal_combination=cls._extract_optional_string(
                components,
                "signal_combination",
                "signal_combo",
                "signals",
            ),
            real_market_loaded=cls._extract_optional_bool(
                components,
                "real_market_loaded",
            ),
            components=components,
            explanation=recommendation.explanation,
            source=recommendation.source,
            latest_grade=grade_view,
        )

    @classmethod
    def _normalize_recommendation_filters(
        cls,
        filters: RecommendationHistoryFilters,
    ) -> RecommendationHistoryFilters:
        start_time = cls._normalize_optional_datetime(
            filters.start_time,
            "start_time",
        )
        end_time = cls._normalize_optional_datetime(
            filters.end_time,
            "end_time",
        )

        if (
            start_time is not None
            and end_time is not None
            and end_time <= start_time
        ):
            raise RecommendationHistoryValidationError(
                "end_time must be later than start_time."
            )

        minimum_confidence = cls._normalize_optional_decimal(
            filters.minimum_confidence,
            "minimum_confidence",
        )
        maximum_confidence = cls._normalize_optional_decimal(
            filters.maximum_confidence,
            "maximum_confidence",
        )
        minimum_hammer = cls._normalize_optional_decimal(
            filters.minimum_hammer,
            "minimum_hammer",
        )
        maximum_hammer = cls._normalize_optional_decimal(
            filters.maximum_hammer,
            "maximum_hammer",
        )

        if (
            minimum_confidence is not None
            and (
                minimum_confidence < Decimal("0")
                or minimum_confidence > Decimal("1")
            )
        ):
            raise RecommendationHistoryValidationError(
                "minimum_confidence must be between 0 and 1."
            )

        if (
            maximum_confidence is not None
            and (
                maximum_confidence < Decimal("0")
                or maximum_confidence > Decimal("1")
            )
        ):
            raise RecommendationHistoryValidationError(
                "maximum_confidence must be between 0 and 1."
            )

        if (
            minimum_confidence is not None
            and maximum_confidence is not None
            and maximum_confidence < minimum_confidence
        ):
            raise RecommendationHistoryValidationError(
                "maximum_confidence must be greater than or equal to "
                "minimum_confidence."
            )

        if (
            minimum_hammer is not None
            and maximum_hammer is not None
            and maximum_hammer < minimum_hammer
        ):
            raise RecommendationHistoryValidationError(
                "maximum_hammer must be greater than or equal to "
                "minimum_hammer."
            )

        outcome = cls._normalize_optional_upper(
            filters.outcome
        )

        if outcome is not None and outcome not in {
            "WIN",
            "LOSS",
            "PUSH",
            "VOID",
        }:
            raise RecommendationHistoryValidationError(
                "outcome must be WIN, LOSS, PUSH, or VOID."
            )

        return RecommendationHistoryFilters(
            start_time=start_time,
            end_time=end_time,
            league_code=cls._normalize_optional_upper(
                filters.league_code
            ),
            sport=cls._normalize_optional_upper(filters.sport),
            market_type=cls._normalize_optional_upper(
                filters.market_type
            ),
            selection=cls._normalize_optional_upper(
                filters.selection
            ),
            tier=cls._normalize_optional_upper(filters.tier),
            model_name=cls._normalize_optional_upper(
                filters.model_name
            ),
            model_version=cls._normalize_optional_string(
                filters.model_version
            ),
            outcome=outcome,
            graded=filters.graded,
            minimum_confidence=minimum_confidence,
            maximum_confidence=maximum_confidence,
            minimum_hammer=minimum_hammer,
            maximum_hammer=maximum_hammer,
        )

    @classmethod
    def _normalize_model_run_filters(
        cls,
        filters: ModelRunHistoryFilters,
    ) -> ModelRunHistoryFilters:
        start_time = cls._normalize_optional_datetime(
            filters.start_time,
            "start_time",
        )
        end_time = cls._normalize_optional_datetime(
            filters.end_time,
            "end_time",
        )

        if (
            start_time is not None
            and end_time is not None
            and end_time <= start_time
        ):
            raise RecommendationHistoryValidationError(
                "end_time must be later than start_time."
            )

        return ModelRunHistoryFilters(
            start_time=start_time,
            end_time=end_time,
            model_name=cls._normalize_optional_upper(
                filters.model_name
            ),
            model_version=cls._normalize_optional_string(
                filters.model_version
            ),
            status=cls._normalize_optional_upper(
                filters.status
            ),
            source=cls._normalize_optional_upper(
                filters.source
            ),
        )

    @staticmethod
    def _validate_pagination(
        *,
        limit: int,
        offset: int,
    ) -> None:
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise RecommendationHistoryValidationError(
                "limit must be an integer."
            )

        if isinstance(offset, bool) or not isinstance(offset, int):
            raise RecommendationHistoryValidationError(
                "offset must be an integer."
            )

        if limit < 1 or limit > 1000:
            raise RecommendationHistoryValidationError(
                "limit must be between 1 and 1000."
            )

        if offset < 0:
            raise RecommendationHistoryValidationError(
                "offset must be zero or greater."
            )

    @staticmethod
    def _normalize_optional_datetime(
        value: datetime | None,
        field_name: str,
    ) -> datetime | None:
        if value is None:
            return None

        if value.tzinfo is None or value.utcoffset() is None:
            raise RecommendationHistoryValidationError(
                f"{field_name} must include timezone information."
            )

        return value.astimezone(UTC)

    @staticmethod
    def _normalize_optional_decimal(
        value: Decimal | int | float | str | None,
        field_name: str,
    ) -> Decimal | None:
        if value is None:
            return None

        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise RecommendationHistoryValidationError(
                f"{field_name} must be numeric."
            ) from exc

    @staticmethod
    def _normalize_optional_string(
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        cleaned = value.strip()

        return cleaned or None

    @classmethod
    def _normalize_optional_upper(
        cls,
        value: str | None,
    ) -> str | None:
        cleaned = cls._normalize_optional_string(value)

        return cleaned.upper() if cleaned is not None else None

    @classmethod
    def _extract_tier(
        cls,
        components: dict[str, Any],
    ) -> str | None:
        value = cls._extract_optional_string(
            components,
            "tier",
            "recommendation_tier",
            "recommendation",
        )

        return value.upper() if value is not None else None

    @staticmethod
    def _extract_hammer_score(
        components: dict[str, Any],
    ) -> Decimal | None:
        for key in (
            "hammer_score",
            "hammer",
            "hammer_rating",
        ):
            value = components.get(key)

            if value is None:
                continue

            try:
                return Decimal(str(value))
            except (InvalidOperation, TypeError, ValueError):
                return None

        return None

    @staticmethod
    def _extract_optional_string(
        components: dict[str, Any],
        *keys: str,
    ) -> str | None:
        for key in keys:
            value = components.get(key)

            if value is None:
                continue

            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned:
                    return cleaned
                continue

            if isinstance(value, (list, tuple, set)):
                cleaned_values = [
                    str(item).strip()
                    for item in value
                    if str(item).strip()
                ]

                if cleaned_values:
                    return " + ".join(cleaned_values)

                continue

            cleaned = str(value).strip()

            if cleaned:
                return cleaned

        return None

    @staticmethod
    def _extract_optional_bool(
        components: dict[str, Any],
        *keys: str,
    ) -> bool | None:
        for key in keys:
            value = components.get(key)

            if isinstance(value, bool):
                return value

            if isinstance(value, str):
                normalized = value.strip().lower()

                if normalized in {"true", "yes", "1"}:
                    return True

                if normalized in {"false", "no", "0"}:
                    return False

            if isinstance(value, int) and value in {0, 1}:
                return bool(value)

        return None
