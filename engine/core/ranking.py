from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.core.recommendation import (
    Recommendation,
)


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        if value in [
            None,
            "",
            "None",
            "N/A",
            "-",
            "--",
        ]:
            return default

        return float(value)
    except (TypeError, ValueError):
        return default


def clamp(
    value: float,
    low: float = 0.0,
    high: float = 100.0,
) -> float:
    return max(
        low,
        min(high, value),
    )


@dataclass
class RankingWeights:
    hammer_score: float = 0.60
    consensus_score: float = 0.18
    edge_score: float = 0.10
    expected_value_score: float = 0.07
    market_quality: float = 0.05


def edge_to_score(
    edge_pct: Any,
) -> float:
    edge = safe_float(
        edge_pct
    )

    return clamp(
        50 + edge * 4
    )


def expected_value_to_score(
    expected_value_pct: Any,
) -> float:
    ev = safe_float(
        expected_value_pct
    )

    return clamp(
        50 + ev * 3
    )


def market_quality_score(
    recommendation: Recommendation,
) -> float:
    if (
        recommendation.real_market_loaded
        and recommendation.market_quote.odds
        is not None
    ):
        return 100.0

    if recommendation.market_probability is not None:
        return 60.0

    return 20.0


def extract_consensus_score(
    recommendation: Recommendation,
) -> float:
    consensus = (
        recommendation.source_signals.get(
            "consensus"
        )
        if isinstance(
            recommendation.source_signals,
            dict,
        )
        else None
    )

    if not isinstance(
        consensus,
        dict,
    ):
        return 50.0

    return clamp(
        safe_float(
            consensus.get(
                "consensus_score"
            ),
            50.0,
        )
    )


def calculate_ranking_score(
    recommendation: Recommendation,
    weights: RankingWeights | None = None,
) -> float:
    active = (
        weights
        or RankingWeights()
    )

    score = (
        recommendation.hammer_score
        * active.hammer_score
    )

    score += (
        extract_consensus_score(
            recommendation
        )
        * active.consensus_score
    )

    score += (
        edge_to_score(
            recommendation.edge_pct
        )
        * active.edge_score
    )

    score += (
        expected_value_to_score(
            recommendation.expected_value_pct
        )
        * active.expected_value_score
    )

    score += (
        market_quality_score(
            recommendation
        )
        * active.market_quality
    )

    if recommendation.recommendation == "HAMMER":
        score += 3.0
    elif recommendation.recommendation == "BET":
        score += 1.5
    elif recommendation.recommendation == "PASS":
        score -= 4.0

    return round(
        clamp(score),
        2,
    )


def ranked_recommendations(
    recommendations: list[
        Recommendation
    ],
    *,
    actionable_only: bool = False,
    real_market_only: bool = False,
    limit: int | None = None,
    weights: RankingWeights | None = None,
) -> list[Recommendation]:
    rows = list(
        recommendations
    )

    if actionable_only:
        rows = [
            row
            for row in rows
            if row.actionable
        ]

    if real_market_only:
        rows = [
            row
            for row in rows
            if row.real_market_loaded
        ]

    rows.sort(
        key=lambda row: (
            calculate_ranking_score(
                row,
                weights,
            ),
            row.hammer_score,
            row.edge_pct
            if row.edge_pct is not None
            else -999,
        ),
        reverse=True,
    )

    if limit is not None:
        return rows[:limit]

    return rows
