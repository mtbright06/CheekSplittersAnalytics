from __future__ import annotations

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


def clamp_score(
    value: Any,
    low: float = 0.0,
    high: float = 100.0,
) -> float:
    number = safe_float(
        value,
        0.0,
    ) or 0.0

    return max(
        low,
        min(high, number),
    )


def recommendation_label(
    score: Any,
    *,
    real_market_loaded: bool = True,
) -> str:
    score_value = clamp_score(score)

    if score_value >= 86:
        recommendation = "HAMMER"
    elif score_value >= 76:
        recommendation = "BET"
    elif score_value >= 66:
        recommendation = "LEAN"
    elif score_value >= 56:
        recommendation = "WATCH"
    else:
        recommendation = "PASS"

    if (
        recommendation == "HAMMER"
        and not real_market_loaded
    ):
        return "BET"

    return recommendation


def confidence_label(
    score: Any,
) -> str:
    score_value = clamp_score(score)

    if score_value >= 90:
        return "ELITE"

    if score_value >= 82:
        return "VERY HIGH"

    if score_value >= 74:
        return "HIGH"

    if score_value >= 64:
        return "MODERATE"

    if score_value >= 54:
        return "LOW"

    return "PASS"


def stars_from_score(
    score: Any,
) -> str:
    score_value = clamp_score(score)

    if score_value >= 90:
        return "★★★★★"

    if score_value >= 80:
        return "★★★★½"

    if score_value >= 72:
        return "★★★★"

    if score_value >= 64:
        return "★★★½"

    if score_value >= 56:
        return "★★★"

    return "★★"


def unit_recommendation(
    score: Any,
    *,
    real_market_loaded: bool,
    maximum_units: float = 3.0,
) -> float:
    score_value = clamp_score(score)

    if score_value < 66:
        return 0.0

    if score_value >= 90:
        units = 3.0
    elif score_value >= 84:
        units = 2.5
    elif score_value >= 78:
        units = 2.0
    elif score_value >= 72:
        units = 1.5
    else:
        units = 1.0

    if not real_market_loaded:
        units = min(
            units,
            1.0,
        )

    return min(
        round(units, 1),
        maximum_units,
    )
