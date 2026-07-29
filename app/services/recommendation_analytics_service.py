"""Read-only model-health analytics derived from immutable persistence data."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Callable, Iterable, Protocol

from sqlalchemy import and_, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.database.session import SessionLocal
from app.models import Recommendation, RecommendationGrade


GRADE_STATUSES = frozenset(
    {"WIN", "LOSS", "PUSH", "VOID", "PENDING", "UNGRADEABLE"}
)


@dataclass(frozen=True, slots=True)
class SettledResult:
    outcome: str
    stake_units: Decimal
    profit_units: Decimal


@dataclass(frozen=True, slots=True)
class PerformanceSummary:
    graded: int
    wins: int
    losses: int
    pushes: int
    voids: int
    decisions: int
    win_percentage: Decimal | None
    stake_units: Decimal
    profit_units: Decimal
    roi_percentage: Decimal | None


def summarize_performance(results: Iterable[SettledResult]) -> PerformanceSummary:
    """Legacy settlement summary retained outside Sprint 66 model health."""

    rows = list(results)
    outcomes = [row.outcome.strip().upper() for row in rows]
    wins = outcomes.count("WIN")
    losses = outcomes.count("LOSS")
    pushes = outcomes.count("PUSH")
    voids = outcomes.count("VOID")
    decisions = wins + losses
    stake_units = sum(
        (row.stake_units for row in rows if row.outcome.strip().upper() != "VOID"),
        Decimal("0"),
    )
    profit_units = sum((row.profit_units for row in rows), Decimal("0"))
    win_percentage = (
        (Decimal(wins) / Decimal(decisions) * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if decisions
        else None
    )
    roi_percentage = (
        (profit_units / stake_units * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if stake_units > 0
        else None
    )
    return PerformanceSummary(
        graded=len(rows),
        wins=wins,
        losses=losses,
        pushes=pushes,
        voids=voids,
        decisions=decisions,
        win_percentage=win_percentage,
        stake_units=stake_units.quantize(Decimal("0.001")),
        profit_units=profit_units.quantize(Decimal("0.0001")),
        roi_percentage=roi_percentage,
    )


class RecommendationAnalyticsError(RuntimeError):
    """Raised when read-only model-health analytics cannot be loaded."""


@dataclass(frozen=True, slots=True)
class ModelHealthBucket:
    league: str
    market: str
    recommendation_tier: str
    sample_size: int
    wins: int
    losses: int
    pushes: int
    voids: int
    pending: int
    ungradeable: int
    win_percentage: float | None
    decision_rate: float
    first_prediction: datetime | None
    last_prediction: datetime | None


@dataclass(frozen=True, slots=True)
class ModelHealthReport:
    generated_at: datetime
    buckets: tuple[ModelHealthBucket, ...]


@dataclass(frozen=True, slots=True)
class ModelHealthSummary:
    recommendations: int
    resolved: int
    pending: int
    overall_win_percentage: float | None


@dataclass(frozen=True, slots=True)
class _AnalyticsRecord:
    league: str | None
    market: str | None
    recommendation_tier: str | None
    recommendation_time: datetime | None
    grade_status: str | None
    is_prediction_snapshot: bool


class _AnalyticsRecordLoader(Protocol):
    def __call__(self) -> Iterable[_AnalyticsRecord]: ...


class RecommendationAnalyticsService:
    """Builds transient model-health summaries from persisted snapshots."""

    def __init__(
        self,
        session_factory: sessionmaker[Session] = SessionLocal,
        *,
        record_loader: _AnalyticsRecordLoader | None = None,
        now_factory: Callable[[], datetime] = lambda: datetime.now(UTC),
        include_legacy: bool = False,
    ) -> None:
        self._session_factory = session_factory
        self._record_loader = record_loader
        self._now_factory = now_factory
        self._include_legacy = include_legacy

    def model_health(self) -> ModelHealthReport:
        records = (
            tuple(self._record_loader())
            if self._record_loader is not None
            else self._load_records()
        )
        included_records = (
            records
            if self._include_legacy
            else tuple(record for record in records if record.is_prediction_snapshot)
        )
        return ModelHealthReport(
            generated_at=_as_utc(self._now_factory()),
            buckets=_aggregate(included_records),
        )

    def _load_records(self) -> tuple[_AnalyticsRecord, ...]:
        latest_grade_revision = (
            select(
                RecommendationGrade.prediction_snapshot_id.label("snapshot_id"),
                func.max(RecommendationGrade.game_result_revision).label("revision"),
            )
            .group_by(RecommendationGrade.prediction_snapshot_id)
            .subquery()
        )
        statement = (
            select(Recommendation, RecommendationGrade.grade_status)
            .outerjoin(
                latest_grade_revision,
                latest_grade_revision.c.snapshot_id == Recommendation.id,
            )
            .outerjoin(
                RecommendationGrade,
                and_(
                    RecommendationGrade.prediction_snapshot_id == Recommendation.id,
                    RecommendationGrade.game_result_revision
                    == latest_grade_revision.c.revision,
                ),
            )
            .order_by(Recommendation.recommendation_time, Recommendation.id)
        )
        session = self._session_factory()
        try:
            rows = session.execute(statement).all()
        except SQLAlchemyError as exc:
            raise RecommendationAnalyticsError(
                "Model-health analytics query failed."
            ) from exc
        finally:
            session.close()

        return tuple(
            _AnalyticsRecord(
                league=recommendation.league_code,
                market=recommendation.market_type,
                recommendation_tier=_recommendation_tier(recommendation.components),
                recommendation_time=recommendation.recommendation_time,
                grade_status=grade_status,
                is_prediction_snapshot=(
                    recommendation.idempotency_key is not None
                    and recommendation.model_run_id is not None
                ),
            )
            for recommendation, grade_status in rows
        )


def _aggregate(records: Iterable[_AnalyticsRecord]) -> tuple[ModelHealthBucket, ...]:
    grouped: dict[tuple[str, str, str], list[_AnalyticsRecord]] = defaultdict(list)
    for record in records:
        key = (
            _label(record.league, "UNKNOWN"),
            _label(record.market, "UNKNOWN"),
            _label(_canonical_tier(record.recommendation_tier), "UNSPECIFIED"),
        )
        grouped[key].append(record)

    buckets: list[ModelHealthBucket] = []
    for (league, market, tier), rows in sorted(grouped.items()):
        statuses = [_grade_status(row.grade_status) for row in rows]
        counts = {status: statuses.count(status) for status in GRADE_STATUSES}
        decision_count = counts["WIN"] + counts["LOSS"] + counts["PUSH"]
        win_loss_count = counts["WIN"] + counts["LOSS"]
        timestamps = sorted(
            timestamp for row in rows if (timestamp := row.recommendation_time) is not None
        )
        sample_size = len(rows)
        buckets.append(
            ModelHealthBucket(
                league=league,
                market=market,
                recommendation_tier=tier,
                sample_size=sample_size,
                wins=counts["WIN"],
                losses=counts["LOSS"],
                pushes=counts["PUSH"],
                voids=counts["VOID"],
                pending=counts["PENDING"],
                ungradeable=counts["UNGRADEABLE"],
                win_percentage=(counts["WIN"] / win_loss_count * 100)
                if win_loss_count
                else None,
                decision_rate=decision_count / sample_size * 100 if sample_size else 0.0,
                first_prediction=timestamps[0] if timestamps else None,
                last_prediction=timestamps[-1] if timestamps else None,
            )
        )
    return tuple(buckets)


def filter_model_health_buckets(
    report: ModelHealthReport,
    *,
    leagues: Iterable[str] | None = None,
    markets: Iterable[str] | None = None,
) -> tuple[ModelHealthBucket, ...]:
    """Filter an already-derived report without querying or recalculating data."""

    league_filter = _normalized_filter(leagues)
    market_filter = _normalized_filter(markets)
    return tuple(
        bucket
        for bucket in report.buckets
        if (not league_filter or bucket.league in league_filter)
        and (not market_filter or bucket.market in market_filter)
    )


def summarize_model_health(
    buckets: Iterable[ModelHealthBucket],
) -> ModelHealthSummary:
    """Summarize already-derived buckets for presentation consumers."""

    rows = tuple(buckets)
    recommendations = sum(row.sample_size for row in rows)
    wins = sum(row.wins for row in rows)
    losses = sum(row.losses for row in rows)
    pending = sum(row.pending for row in rows)
    resolved = recommendations - pending
    win_loss_count = wins + losses
    return ModelHealthSummary(
        recommendations=recommendations,
        resolved=resolved,
        pending=pending,
        overall_win_percentage=(wins / win_loss_count * 100)
        if win_loss_count
        else None,
    )


def _recommendation_tier(components: object) -> str | None:
    if not isinstance(components, dict):
        return None
    prediction = components.get("prediction")
    if not isinstance(prediction, dict):
        return None
    return _canonical_tier(
        prediction.get("conviction_tier")
        or prediction.get("model_recommendation")
        or prediction.get("recommendation")
    )


def _canonical_tier(value: object) -> str | None:
    text = " ".join(str(value or "").upper().split())
    if "NO PLAY" in text:
        return "PASS"
    for tier in ("CHEEK RIPPER", "STRONG PLAY", "PLAYABLE", "LEAN", "PASS"):
        if tier in text:
            return tier
    # BET is a deliberate MLB totals tier, not a MONEYLINE PLAYABLE alias.
    for tier in ("STRONG BET", "HAMMER", "BET"):
        if tier in text:
            return tier
    return text or None


def _grade_status(value: object) -> str:
    status = _label(value, "PENDING")
    return status if status in GRADE_STATUSES else "PENDING"


def _label(value: object, fallback: str) -> str:
    text = " ".join(str(value or "").upper().split())
    return text or fallback


def _normalized_filter(values: Iterable[str] | None) -> frozenset[str]:
    return frozenset(_label(value, "") for value in (values or ()) if _label(value, ""))


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
