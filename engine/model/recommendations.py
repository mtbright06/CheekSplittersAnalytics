from __future__ import annotations

import math
from typing import Any


def recommendation(edge, confidence):
    """Legacy edge-based recommendation contract for non-MLB callers."""
    edge = edge or 0
    confidence = confidence or 0

    if edge >= 10 and confidence >= 70:
        return "🔥 CHEEK RIPPER"

    if edge >= 7 and confidence >= 65:
        return "✅ STRONG PLAY"

    if edge >= 5 and confidence >= 55:
        return "🟡 PLAYABLE"

    if edge >= 2 and confidence >= 50:
        return "LEAN"

    return "PASS"


def mlb_moneyline_conviction_recommendation(
    model_probability: Any,
    confidence: Any,
) -> str:
    """Classify MLB moneyline conviction independently of market price."""
    probability = _number(model_probability)
    confidence_value = _number(confidence)

    if probability is None or confidence_value is None:
        return "PASS"

    if probability >= 63.0 and confidence_value >= 85.0:
        return "🔥 CHEEK RIPPER"

    if probability >= 59.0 and confidence_value >= 78.0:
        return "✅ STRONG PLAY"

    if probability >= 56.5 and confidence_value >= 74.0:
        return "🟡 PLAYABLE"

    if probability >= 52.0 and confidence_value >= 65.0:
        return "LEAN"

    return "PASS"


MLB_MONEYLINE_V2_TIERS = (
    ("STRONG PLAY", 17.4),
    ("PLAY", 12.0),
    ("PLAYABLE", 8.7),
    ("LEAN", 2.6),
)

MLB_MONEYLINE_V2_CANDIDATE_TIERS = (
    ("STRONG PLAY", 8.0),
    ("PLAY", 6.0),
    ("PLAYABLE", 3.0),
    ("LEAN", 1.0),
)

MLB_MONEYLINE_V2_RANKS = {
    "PASS": 0,
    "LEAN": 1,
    "PLAYABLE": 2,
    "PLAY": 3,
    "STRONG PLAY": 4,
}


def mlb_moneyline_v2_recommendation(
    sharpscore_gap: Any,
    reliability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Shadow-mode MLB moneyline V2 authority.

    V2 uses SharpScore gap as the single model-strength authority. Reliability
    checks may cap the tier only when they introduce independent input-quality
    evidence.
    """
    gap = _number(sharpscore_gap)
    reliability = reliability or {}

    if gap is None:
        base_tier = "PASS"
    else:
        base_tier = "PASS"
        for tier, threshold in MLB_MONEYLINE_V2_TIERS:
            if gap >= threshold:
                base_tier = tier
                break

    cap = str(reliability.get("tier_cap") or "STRONG PLAY").upper()
    if cap not in MLB_MONEYLINE_V2_RANKS:
        cap = "STRONG PLAY"

    final_tier = _cap_mlb_moneyline_v2_tier(base_tier, cap)

    return {
        "version": "mlb_moneyline_v2_shadow",
        "authoritative_signal": "sharpscore_gap",
        "sharpscore_gap": gap,
        "base_recommendation": base_tier,
        "recommendation": final_tier,
        "tier_cap": cap,
        "reliability": reliability,
        "changed_by_reliability": final_tier != base_tier,
    }


def mlb_moneyline_v2_candidate_recommendation(
    sharpscore_gap: Any,
    reliability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Candidate V2 baseline using diagnostic SharpScore gap bands."""
    return _mlb_moneyline_v2_from_gap(
        sharpscore_gap,
        reliability,
        tiers=MLB_MONEYLINE_V2_CANDIDATE_TIERS,
        version="mlb_moneyline_v2_candidate_shadow",
    )


def _mlb_moneyline_v2_from_gap(
    sharpscore_gap: Any,
    reliability: dict[str, Any] | None,
    *,
    tiers: tuple[tuple[str, float], ...],
    version: str,
) -> dict[str, Any]:
    gap = _number(sharpscore_gap)
    reliability = reliability or {}

    if gap is None:
        base_tier = "PASS"
    else:
        base_tier = "PASS"
        for tier, threshold in tiers:
            if gap >= threshold:
                base_tier = tier
                break

    cap = str(reliability.get("tier_cap") or "STRONG PLAY").upper()
    if cap not in MLB_MONEYLINE_V2_RANKS:
        cap = "STRONG PLAY"

    final_tier = _cap_mlb_moneyline_v2_tier(base_tier, cap)

    return {
        "version": version,
        "authoritative_signal": "sharpscore_gap",
        "sharpscore_gap": gap,
        "base_recommendation": base_tier,
        "recommendation": final_tier,
        "tier_cap": cap,
        "reliability": reliability,
        "changed_by_reliability": final_tier != base_tier,
    }


def _cap_mlb_moneyline_v2_tier(
    tier: str,
    cap: str,
) -> str:
    tier_rank = MLB_MONEYLINE_V2_RANKS.get(tier, 0)
    cap_rank = MLB_MONEYLINE_V2_RANKS.get(cap, 4)

    if tier_rank <= cap_rank:
        return tier

    for label, rank in MLB_MONEYLINE_V2_RANKS.items():
        if rank == cap_rank:
            return label

    return "PASS"


def market_value_classification(
    edge: Any,
) -> tuple[str, str]:
    """Classify an existing SSRP edge without changing its numeric value."""
    value = _number(edge)

    if value is None:
        return "VALUE UNAVAILABLE", "unavailable"

    if value >= 7.0:
        return "ELITE VALUE", "elite_value"

    if value >= 4.0:
        return "STRONG VALUE", "strong_value"

    if value >= 1.0:
        return "POSITIVE VALUE", "positive_value"

    if value > -1.0:
        return "FAIR PRICE", "fair_price"

    if value > -5.0:
        return "MARKET PREMIUM", "market_premium"

    return "HEAVY PREMIUM", "heavy_premium"


def mlb_moneyline_explanation(
    *,
    team: str,
    recommendation: str,
    market_value_label: str,
    market_value_tone: str,
) -> dict[str, Any]:
    """Structured explanation contract for MLB conviction and SSRP value."""
    conviction_summaries = {
        "🔥 CHEEK RIPPER": "One of the model's strongest win projections.",
        "STRONG PLAY": "One of the model's strongest win projections.",
        "✅ STRONG PLAY": f"The model has high conviction in {team}.",
        "PLAY": f"The model has high conviction in {team}.",
        "🟡 PLAYABLE": f"The model supports {team} as a bet.",
        "PLAYABLE": f"The model supports {team} as a bet.",
        "LEAN": f"The model gives {team} a modest projected edge.",
        "PASS": f"The model does not clear a conviction tier for {team}.",
    }
    market_summaries = {
        "ELITE VALUE": "The available price is exceptionally favorable relative to the model.",
        "STRONG VALUE": "The available price is strongly favorable relative to the model.",
        "POSITIVE VALUE": "The available price is favorable relative to the model.",
        "FAIR PRICE": "The available price is close to the model projection.",
        "MARKET PREMIUM": "We like the team, but you are paying for it.",
        "HEAVY PREMIUM": "The market price is expensive relative to our projection.",
        "VALUE UNAVAILABLE": "No valid SSRP edge is available for market-value classification.",
    }

    return {
        "schema_version": "mlb_moneyline_v1",
        "conviction": {
            "label": recommendation,
            "source": "model_probability_and_confidence",
            "summary": conviction_summaries[recommendation],
        },
        "market_value": {
            "label": market_value_label,
            "tone": market_value_tone,
            "source": "ssrp_edge",
            "summary": market_summaries[market_value_label],
        },
    }


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    return number if math.isfinite(number) else None


def grade_label(edge):
    if edge is None:
        return "NO DATA"
    if edge >= 10:
        return "CHEEK RIPPER 🔥"
    if edge >= 7:
        return "STRONG PLAY"
    if edge >= 5:
        return "PLAYABLE"
    if edge >= 2:
        return "LEAN"
    return "PASS"
