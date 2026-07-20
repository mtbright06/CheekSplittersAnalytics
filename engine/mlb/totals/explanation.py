from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.mlb.bullpen.game_adjustment import (
    GameBullpenAdjustment,
)
from engine.mlb.totals.expected_runs import (
    TeamRunProjection,
)
from engine.mlb.totals.market import (
    MarketEdge,
    MarketTotal,
)
from engine.mlb.totals.park_factors import (
    ParkFactorResult,
)
from engine.mlb.totals.recommendation import (
    TotalsRecommendation,
)


@dataclass(frozen=True)
class ExplanationItem:
    id: str
    category: str
    title: str
    detail: str
    impact: str
    direction: str = "NEUTRAL"

    metric: str | None = None
    value: float | None = None
    unit: str | None = None
    confidence: float | None = None
    evidence_score: float | None = None
    priority: int = 100

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
    ) -> "ExplanationItem":
        return cls(
            id=str(payload["id"]),
            category=str(payload["category"]),
            title=str(payload["title"]),
            detail=str(payload["detail"]),
            impact=str(payload["impact"]),
            direction=str(
                payload.get(
                    "direction",
                    "NEUTRAL",
                )
            ),
            metric=payload.get("metric"),
            value=payload.get("value"),
            unit=payload.get("unit"),
            confidence=payload.get("confidence"),
            evidence_score=payload.get(
                "evidence_score"
            ),
            priority=int(
                payload.get(
                    "priority",
                    100,
                )
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "metric": self.metric,
            "value": (
                None
                if self.value is None
                else round(
                    self.value,
                    3,
                )
            ),
            "unit": self.unit,
            "detail": self.detail,
            "impact": self.impact,
            "direction": self.direction,
            "confidence": (
                None
                if self.confidence is None
                else round(
                    self.confidence,
                    1,
                )
            ),
            "evidence_score": (
                None
                if self.evidence_score is None
                else round(
                    self.evidence_score,
                    1,
                )
            ),
            "priority": self.priority,
        }


@dataclass(frozen=True)
class TotalsExplanation:
    summary: str
    strengths: list[ExplanationItem] = field(
        default_factory=list
    )
    risks: list[ExplanationItem] = field(
        default_factory=list
    )
    market: list[ExplanationItem] = field(
        default_factory=list
    )
    context: list[ExplanationItem] = field(
        default_factory=list
    )

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
    ) -> "TotalsExplanation":
        def load_section(
            name: str,
        ) -> list[ExplanationItem]:
            items = payload.get(
                name,
                [],
            )

            if not isinstance(items, list):
                raise TypeError(
                    f"Explanation section "
                    f"{name!r} must be a list."
                )

            return [
                ExplanationItem.from_dict(item)
                for item in items
            ]

        return cls(
            summary=str(
                payload.get(
                    "summary",
                    "",
                )
            ),
            strengths=load_section(
                "strengths"
            ),
            risks=load_section(
                "risks"
            ),
            market=load_section(
                "market"
            ),
            context=load_section(
                "context"
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "strengths": [
                item.to_dict()
                for item in sorted(
                    self.strengths,
                    key=lambda item: item.priority,
                )
            ],
            "risks": [
                item.to_dict()
                for item in sorted(
                    self.risks,
                    key=lambda item: item.priority,
                )
            ],
            "market": [
                item.to_dict()
                for item in sorted(
                    self.market,
                    key=lambda item: item.priority,
                )
            ],
            "context": [
                item.to_dict()
                for item in sorted(
                    self.context,
                    key=lambda item: item.priority,
                )
            ],
        }


def build_totals_explanation(
    *,
    away_projection: TeamRunProjection,
    home_projection: TeamRunProjection,
    starter_based_total: float,
    bullpen_adjustment: GameBullpenAdjustment,
    projected_total: float,
    park: ParkFactorResult,
    market: MarketTotal,
    market_edge: MarketEdge,
    recommendation: TotalsRecommendation,
    data_points: int,
) -> TotalsExplanation:
    strengths: list[ExplanationItem] = []
    risks: list[ExplanationItem] = []
    market_items: list[ExplanationItem] = []
    context: list[ExplanationItem] = []

    direction = recommendation.selection

    summary = _build_summary(
        projected_total=projected_total,
        market=market,
        market_edge=market_edge,
        recommendation=recommendation,
    )

    strengths.append(
        ExplanationItem(
            id="starter_projection",
            category="STARTING_PITCHING",
            title="Starter-based projection",
            detail=(
                f"{away_projection.team} projects for "
                f"{away_projection.expected_runs:.2f} runs "
                f"and {home_projection.team} projects for "
                f"{home_projection.expected_runs:.2f}, "
                f"producing a starter-based total of "
                f"{starter_based_total:.2f}."
            ),
            impact="HIGH",
            direction=_projection_direction(
                starter_based_total,
                market,
            ),
            metric="Starter-based total",
            value=starter_based_total,
            unit="runs",
            evidence_score=_starter_evidence_score(
                away_projection=away_projection,
                home_projection=home_projection,
            ),
            priority=20,
        )
    )

    bullpen_direction = (
        "OVER"
        if bullpen_adjustment.combined_adjustment > 0
        else "UNDER"
        if bullpen_adjustment.combined_adjustment < 0
        else "NEUTRAL"
    )

    bullpen_item = ExplanationItem(
        id="bullpen_adjustment",
        category="BULLPEN",
        title="Bullpen adjustment",
        detail=(
            f"The bullpens adjust the projection by "
            f"{bullpen_adjustment.combined_adjustment:+.2f} "
            f"runs. Bullpen data status is "
            f"{bullpen_adjustment.status} with "
            f"{bullpen_adjustment.confidence:.1f} confidence."
        ),
        impact=_impact_from_run_value(
            abs(
                bullpen_adjustment.combined_adjustment
            )
        ),
        direction=bullpen_direction,
        metric="Bullpen adjustment",
        value=bullpen_adjustment.combined_adjustment,
        unit="runs",
        confidence=bullpen_adjustment.confidence,
        evidence_score=bullpen_adjustment.confidence,
        priority=30,
    )

    if (
        direction in {"OVER", "UNDER"}
        and bullpen_direction == direction
    ):
        strengths.append(bullpen_item)
    elif bullpen_direction == "NEUTRAL":
        context.append(bullpen_item)
    else:
        risks.append(bullpen_item)

    park_direction = (
        "OVER"
        if park.factor > 1.0
        else "UNDER"
        if park.factor < 1.0
        else "NEUTRAL"
    )

    park_item = ExplanationItem(
        id="park_environment",
        category="PARK",
        title="Park environment",
        detail=(
            f"{park.team} has a park factor of "
            f"{park.factor:.3f} from {park.source}."
        ),
        impact=_park_impact(
            park.factor
        ),
        direction=park_direction,
        metric="Park factor",
        value=park.factor,
        unit="factor",
        evidence_score=_park_evidence_score(
            park
        ),
        priority=40,
    )

    if (
        direction in {"OVER", "UNDER"}
        and park_direction == direction
    ):
        strengths.append(park_item)
    elif park_direction == "NEUTRAL":
        context.append(park_item)
    else:
        risks.append(park_item)

    context.append(
        ExplanationItem(
            id="projection_inputs",
            category="DATA_QUALITY",
            title="Projection inputs",
            detail=(
                f"The projection uses {data_points} unique "
                f"offense, starter and park inputs."
            ),
            impact=(
                "HIGH"
                if data_points >= 11
                else "MEDIUM"
                if data_points >= 8
                else "LOW"
            ),
            direction="NEUTRAL",
            metric="Input count",
            value=float(
                data_points
            ),
            unit="inputs",
            evidence_score=_data_evidence_score(
                data_points
            ),
            priority=70,
        )
    )

    risks.append(
        ExplanationItem(
            id="missing_weather_and_lineups",
            category="MISSING_INPUTS",
            title="Inputs not yet included",
            detail=(
                "Weather and confirmed lineups are not yet "
                "included in the projection."
            ),
            impact="MEDIUM",
            direction="NEUTRAL",
            evidence_score=100.0,
            priority=60,
        )
    )

    if (
        market.available
        and market.total is not None
        and market_edge.edge is not None
    ):
        market_items.append(
            ExplanationItem(
                id="market_edge",
                category="MARKET_EDGE",
                title="Model versus market",
                detail=(
                    f"The market total is "
                    f"{market.total:.2f}, while the model "
                    f"projects {projected_total:.2f}. "
                    f"The resulting edge is "
                    f"{market_edge.edge:+.2f} runs."
                ),
                impact=_impact_from_run_value(
                    abs(
                        market_edge.edge
                    )
                ),
                direction=market_edge.direction,
                metric="Market edge",
                value=market_edge.edge,
                unit="runs",
                evidence_score=_market_evidence_score(
                    market=market,
                    market_edge=market_edge,
                ),
                priority=10,
            )
        )

        market_items.append(
            ExplanationItem(
                id="betting_recommendation",
                category="RECOMMENDATION",
                title=recommendation.recommendation,
                detail=(
                    f"Recommendation score: "
                    f"{recommendation.recommendation_score:.1f}; "
                    f"betting confidence: "
                    f"{recommendation.confidence}; "
                    f"rating: {recommendation.stars}."
                ),
                impact=_recommendation_impact(
                    recommendation.recommendation_score
                ),
                direction=direction,
                metric="Recommendation score",
                value=(
                    recommendation.recommendation_score
                ),
                unit="score",
                evidence_score=(
                    recommendation.recommendation_score
                ),
                priority=5,
            )
        )
    else:
        risks.append(
            ExplanationItem(
                id="market_unavailable",
                category="MARKET_AVAILABILITY",
                title="No sportsbook total available",
                detail=(
                    "The model cannot produce an actionable "
                    "wager without a sportsbook total."
                ),
                impact="HIGH",
                direction="NEUTRAL",
                evidence_score=100.0,
                priority=1,
            )
        )

    return TotalsExplanation(
        summary=summary,
        strengths=strengths,
        risks=risks,
        market=market_items,
        context=context,
    )


def _build_summary(
    *,
    projected_total: float,
    market: MarketTotal,
    market_edge: MarketEdge,
    recommendation: TotalsRecommendation,
) -> str:
    if (
        not market.available
        or market.total is None
        or market_edge.edge is None
    ):
        return (
            f"The model projects {projected_total:.2f} runs, "
            "but no sportsbook total is available."
        )

    if recommendation.recommendation == "PASS":
        return (
            f"The model projects {projected_total:.2f} runs "
            f"against a market total of {market.total:.2f}, "
            f"but the {market_edge.edge:+.2f}-run edge does "
            "not meet the threshold for an actionable play."
        )

    return (
        f"{recommendation.recommendation}: the model projects "
        f"{projected_total:.2f} runs against a market total "
        f"of {market.total:.2f}, creating a "
        f"{market_edge.edge:+.2f}-run edge."
    )


def _projection_direction(
    projection: float,
    market: MarketTotal,
) -> str:
    if not market.available or market.total is None:
        return "NEUTRAL"

    if projection > market.total:
        return "OVER"

    if projection < market.total:
        return "UNDER"

    return "NEUTRAL"


def _impact_from_run_value(
    value: float,
) -> str:
    if value >= 1.25:
        return "HIGH"

    if value >= 0.50:
        return "MEDIUM"

    return "LOW"


def _park_impact(
    factor: float,
) -> str:
    distance = abs(
        factor - 1.0
    )

    if distance >= 0.08:
        return "HIGH"

    if distance >= 0.03:
        return "MEDIUM"

    return "LOW"


def _starter_evidence_score(
    *,
    away_projection: TeamRunProjection,
    home_projection: TeamRunProjection,
) -> float:
    combined_points = (
        away_projection.data_points
        + home_projection.data_points
    )

    return min(
        100.0,
        combined_points * 8.0,
    )


def _park_evidence_score(
    park: ParkFactorResult,
) -> float:
    if not park.available:
        return 0.0

    if park.source == "STATIC_V1":
        return 65.0

    return 80.0


def _data_evidence_score(
    data_points: int,
) -> float:
    return min(
        100.0,
        data_points * 8.0,
    )


def _market_evidence_score(
    *,
    market: MarketTotal,
    market_edge: MarketEdge,
) -> float:
    if (
        not market.available
        or market.total is None
        or market_edge.edge is None
    ):
        return 0.0

    return 100.0


def _recommendation_impact(
    score: float,
) -> str:
    if score >= 82:
        return "HIGH"

    if score >= 64:
        return "MEDIUM"

    return "LOW"
