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
    tier: float = 1000.0
    model_probability: float = 100.0
    model_confidence: float = 10.0
    hammer_score: float = 1.0


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


def recommendation_tier_score(
    value: Any,
) -> float:
    label = str(value or "").upper()

    if "HAMMER" in label or "CHEEK RIPPER" in label:
        return 5.0

    if "STRONG" in label or label == "BET":
        return 4.0

    if label == "PLAY":
        return 3.5

    if "PLAYABLE" in label:
        return 3.0

    if "LEAN" in label:
        return 2.0

    if label == "PASS" or "NO PLAY" in label:
        return 0.0

    return 1.0


def model_probability_score(
    recommendation: Recommendation,
) -> float:
    probability = recommendation.model_win_strength

    if probability is None:
        probability = recommendation.model_probability

    if probability is None:
        probability = recommendation.components.get("model_win_strength")

    if probability is None:
        probability = recommendation.components.get("model_probability")

    if probability is None:
        probability = recommendation.components.get(
            "outcome_probability"
        )

    number = safe_float(
        probability,
        0.0,
    )

    if number > 1:
        number /= 100.0

    return clamp(
        number * 100.0
    )


def model_confidence_score(
    recommendation: Recommendation,
) -> float:
    # Fallback order is intentionally model-first:
    # 1. explicit numeric model confidence on the Recommendation contract
    # 2. explicit numeric model confidence in components/source signals
    # 3. generic numeric confidence retained by older model contracts
    # 4. non-Hammer compatibility label on Recommendation.confidence
    # 5. neutral fallback
    # Hammer confidence, edge, EV, odds, price, and market quality are not
    # authoritative model-confidence inputs.
    for value in (
        recommendation.model_confidence,
        recommendation.components.get("model_confidence"),
        recommendation.source_signals.get("model_confidence")
        if isinstance(recommendation.source_signals, dict)
        else None,
        recommendation.components.get("confidence"),
    ):
        score = safe_float(
            value,
            None,
        )
        if score is not None:
            if score <= 1:
                score *= 100.0
            return clamp(score)

    label_scores = {
        "ELITE": 95.0,
        "VERY HIGH": 88.0,
        "HIGH": 80.0,
        "MODERATE": 68.0,
        "LOW": 56.0,
        "PASS": 0.0,
    }

    if recommendation.hammer_confidence:
        return 50.0

    return label_scores.get(
        str(recommendation.confidence or "").upper(),
        50.0,
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
        recommendation_tier_score(
            recommendation.recommendation
        )
        * active.tier
    )

    score += (
        model_probability_score(
            recommendation
        )
        * active.model_probability
    )

    score += (
        model_confidence_score(
            recommendation
        )
        * active.model_confidence
    )

    score += (
        recommendation.hammer_score
        * active.hammer_score
    )

    return round(score, 2)


def stable_ranking_identity(
    recommendation: Recommendation,
) -> tuple[str, str, str, str, str]:
    return (
        str(
            recommendation.scheduled_start_at
            or recommendation.event_time
            or ""
        ),
        str(recommendation.league or ""),
        str(recommendation.market or ""),
        str(recommendation.event_id or ""),
        str(recommendation.selection or ""),
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
            recommendation_tier_score(
                row.recommendation
            ),
            model_probability_score(row),
            model_confidence_score(row),
            row.hammer_score,
            stable_ranking_identity(row),
        ),
        reverse=True,
    )

    if limit is not None:
        return rows[:limit]

    return rows
