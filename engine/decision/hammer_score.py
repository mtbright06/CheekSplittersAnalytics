from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def safe_float(
    value: Any,
    default: float | None = None,
) -> float | None:
    try:
        if value in [None, "", "None", "N/A", "-", "--"]:
            return default

        return float(value)
    except (TypeError, ValueError):
        return default


def clamp(
    value: float,
    low: float = 0.0,
    high: float = 100.0,
) -> float:
    return max(low, min(high, value))


def normalize_probability(value: Any) -> float | None:
    number = safe_float(value)

    if number is None:
        return None

    if number > 1:
        number = number / 100

    return max(0.0, min(1.0, number))


def normalize_score(
    value: Any,
    assumed_max: float = 100.0,
) -> float | None:
    number = safe_float(value)

    if number is None:
        return None

    if assumed_max <= 0:
        return None

    return clamp((number / assumed_max) * 100)


def recommendation_from_score(score: float) -> str:
    if score >= 86:
        return "HAMMER"

    if score >= 76:
        return "BET"

    if score >= 66:
        return "LEAN"

    if score >= 56:
        return "WATCH"

    return "PASS"


def confidence_label(score: float) -> str:
    if score >= 90:
        return "ELITE"

    if score >= 82:
        return "VERY HIGH"

    if score >= 74:
        return "HIGH"

    if score >= 64:
        return "MODERATE"

    if score >= 54:
        return "LOW"

    return "PASS"


def stars_from_score(score: float) -> str:
    if score >= 90:
        return "★★★★★"

    if score >= 80:
        return "★★★★½"

    if score >= 72:
        return "★★★★"

    if score >= 64:
        return "★★★½"

    if score >= 56:
        return "★★★"

    return "★★"


@dataclass
class HammerInputs:
    mlb_model_score: float | None = None
    mlb_model_probability: float | None = None
    first5_score: float | None = None
    bomb_score: float | None = None
    starter_score: float | None = None
    offense_score: float | None = None
    bullpen_score: float | None = None
    park_score: float | None = None
    weather_score: float | None = None
    market_edge_pct: float | None = None
    expected_value_pct: float | None = None
    sample_confidence: float | None = None
    module_agreement: int = 0
    contradiction_count: int = 0
    real_market_loaded: bool = False


DEFAULT_WEIGHTS = {
    "mlb_model": 0.23,
    "first5": 0.14,
    "bomb": 0.10,
    "starter": 0.13,
    "offense": 0.10,
    "bullpen": 0.07,
    "park": 0.04,
    "weather": 0.04,
    "market_edge": 0.08,
    "expected_value": 0.04,
    "sample_confidence": 0.03,
}


def market_edge_to_score(edge_pct: Any) -> float | None:
    edge = safe_float(edge_pct)

    if edge is None:
        return None

    return clamp(50 + (edge * 4.0))


def expected_value_to_score(ev_pct: Any) -> float | None:
    ev = safe_float(ev_pct)

    if ev is None:
        return None

    return clamp(50 + (ev * 3.0))


def probability_to_score(probability: Any) -> float | None:
    normalized = normalize_probability(probability)

    if normalized is None:
        return None

    return clamp(normalized * 100)


def calculate_hammer_score(
    inputs: HammerInputs,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    active_weights = {
        **DEFAULT_WEIGHTS,
        **(weights or {}),
    }

    components = {
        "mlb_model": (
            inputs.mlb_model_score
            if inputs.mlb_model_score is not None
            else probability_to_score(inputs.mlb_model_probability)
        ),
        "first5": inputs.first5_score,
        "bomb": inputs.bomb_score,
        "starter": inputs.starter_score,
        "offense": inputs.offense_score,
        "bullpen": inputs.bullpen_score,
        "park": inputs.park_score,
        "weather": inputs.weather_score,
        "market_edge": market_edge_to_score(inputs.market_edge_pct),
        "expected_value": expected_value_to_score(
            inputs.expected_value_pct
        ),
        "sample_confidence": inputs.sample_confidence,
    }

    weighted_total = 0.0
    used_weight = 0.0
    breakdown: dict[str, dict[str, Any]] = {}

    for name, raw_value in components.items():
        value = safe_float(raw_value)
        weight = safe_float(active_weights.get(name), 0.0) or 0.0

        if value is None or weight <= 0:
            breakdown[name] = {
                "available": False,
                "score": None,
                "weight": weight,
                "contribution": 0.0,
            }
            continue

        value = clamp(value)
        contribution = value * weight

        weighted_total += contribution
        used_weight += weight

        breakdown[name] = {
            "available": True,
            "score": round(value, 1),
            "weight": round(weight, 4),
            "contribution": round(contribution, 2),
        }

    if used_weight <= 0:
        base_score = 0.0
    else:
        base_score = weighted_total / used_weight

    agreement_bonus = min(max(inputs.module_agreement - 1, 0) * 2.5, 10)
    contradiction_penalty = min(inputs.contradiction_count * 5.0, 20)

    market_status_penalty = 0.0

    if not inputs.real_market_loaded:
        market_status_penalty = 2.0

    final_score = clamp(
        base_score
        + agreement_bonus
        - contradiction_penalty
        - market_status_penalty
    )

    recommendation = recommendation_from_score(final_score)

    if not inputs.real_market_loaded and recommendation == "HAMMER":
        recommendation = "BET"

    return {
        "hammer_score": round(final_score, 1),
        "base_score": round(base_score, 1),
        "agreement_bonus": round(agreement_bonus, 1),
        "contradiction_penalty": round(
            contradiction_penalty,
            1,
        ),
        "market_status_penalty": round(
            market_status_penalty,
            1,
        ),
        "recommendation": recommendation,
        "confidence": confidence_label(final_score),
        "stars": stars_from_score(final_score),
        "real_market_loaded": inputs.real_market_loaded,
        "breakdown": breakdown,
    }
