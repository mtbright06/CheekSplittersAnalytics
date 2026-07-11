from __future__ import annotations

from typing import Any


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value in [None, "", "-", "--", "N/A"]:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def american_to_implied_probability(odds: Any) -> float | None:
    """
    Converts American odds into implied probability.

    -110 -> 0.5238
    +150 -> 0.4000
    """
    american = safe_float(odds)

    if american is None or american == 0:
        return None

    if american < 0:
        probability = abs(american) / (abs(american) + 100)
    else:
        probability = 100 / (american + 100)

    return round(clamp(probability), 6)


def implied_probability_to_american(probability: Any) -> int | None:
    probability = safe_float(probability)

    if probability is None or probability <= 0 or probability >= 1:
        return None

    if probability >= 0.5:
        odds = -(probability / (1 - probability)) * 100
    else:
        odds = ((1 - probability) / probability) * 100

    return int(round(odds))


def remove_two_way_vig(
    side_a_odds: Any,
    side_b_odds: Any,
) -> dict[str, float | None]:
    """
    Normalizes two implied probabilities so they sum to 1.0.
    """
    side_a_raw = american_to_implied_probability(side_a_odds)
    side_b_raw = american_to_implied_probability(side_b_odds)

    if side_a_raw is None or side_b_raw is None:
        return {
            "side_a_raw": side_a_raw,
            "side_b_raw": side_b_raw,
            "side_a_no_vig": None,
            "side_b_no_vig": None,
            "hold": None,
        }

    total = side_a_raw + side_b_raw

    if total <= 0:
        return {
            "side_a_raw": side_a_raw,
            "side_b_raw": side_b_raw,
            "side_a_no_vig": None,
            "side_b_no_vig": None,
            "hold": None,
        }

    return {
        "side_a_raw": round(side_a_raw, 6),
        "side_b_raw": round(side_b_raw, 6),
        "side_a_no_vig": round(side_a_raw / total, 6),
        "side_b_no_vig": round(side_b_raw / total, 6),
        "hold": round(total - 1.0, 6),
    }


def decimal_return(american_odds: Any) -> float | None:
    american = safe_float(american_odds)

    if american is None or american == 0:
        return None

    if american > 0:
        return round(1 + (american / 100), 6)

    return round(1 + (100 / abs(american)), 6)


def expected_value(
    model_probability: Any,
    american_odds: Any,
) -> float | None:
    """
    Expected return per $1 staked.

    0.08 = positive 8% expected value.
    """
    probability = safe_float(model_probability)
    decimal = decimal_return(american_odds)

    if probability is None or decimal is None:
        return None

    ev = (probability * decimal) - 1

    return round(ev, 6)


def edge_percentage(
    model_probability: Any,
    market_probability: Any,
) -> float | None:
    model = safe_float(model_probability)
    market = safe_float(market_probability)

    if model is None or market is None:
        return None

    return round((model - market) * 100, 2)


def format_american(odds: Any) -> str:
    american = safe_float(odds)

    if american is None:
        return "N/A"

    integer = int(round(american))

    if integer > 0:
        return f"+{integer}"

    return str(integer)
